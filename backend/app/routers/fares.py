from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.db_models import (
    CommunityVote,
    FareObservation,
    FareSubmission,
    FareVerification,
    HistoricalFare,
)
from backend.app.services.fare_verification import (
    SUPPORTED_PROVIDERS,
    VOTE_TYPES,
    assess_submission,
    route_fingerprint,
    serialize_submission,
    vote_totals,
)


router = APIRouter(prefix="/fares", tags=["Fare Intelligence"])
SCREENSHOT_DIR = Path(__file__).resolve().parents[2] / "uploads" / "fare-evidence"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class FareSubmissionPayload(BaseModel):
    provider: str
    pickupLocation: str = Field(min_length=2, max_length=500)
    destinationLocation: str = Field(min_length=2, max_length=500)
    pickupCoordinates: tuple[float, float]
    destinationCoordinates: tuple[float, float]
    vehicleCategory: str = Field(min_length=2, max_length=50)
    submittedFare: float = Field(gt=0, le=100000)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    quotationTimestamp: datetime
    estimatedDistanceKm: float = Field(gt=0, le=1000)
    estimatedDurationMin: float = Field(gt=0, le=1440)
    surgeMultiplier: Optional[float] = Field(default=None, gt=0, le=10)
    additionalFees: float = Field(default=0, ge=0, le=100000)
    screenshotReference: Optional[str] = Field(default=None, max_length=500)
    deviceFingerprint: str = Field(min_length=16, max_length=128)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_PROVIDERS:
            raise ValueError("provider must be Uber, Ola, or Rapido")
        return normalized.title()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("pickupCoordinates", "destinationCoordinates")
    @classmethod
    def validate_coordinates(cls, value: tuple[float, float]) -> tuple[float, float]:
        lat, lng = value
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError("coordinates are outside valid latitude/longitude ranges")
        return value


class FareVotePayload(BaseModel):
    voteType: str
    deviceFingerprint: str = Field(min_length=16, max_length=128)

    @field_validator("voteType")
    @classmethod
    def validate_vote(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in VOTE_TYPES:
            raise ValueError(f"voteType must be one of {sorted(VOTE_TYPES)}")
        return normalized


@router.post("/screenshot", status_code=201)
async def upload_screenshot(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, or WebP screenshots are supported.")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Screenshot must be 5 MB or smaller.")
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "screenshot").suffix.lower()
    stored_name = f"{secrets.token_urlsafe(18)}{suffix if suffix in {'.jpg', '.jpeg', '.png', '.webp'} else '.img'}"
    (SCREENSHOT_DIR / stored_name).write_bytes(content)
    return {"reference": stored_name}


def _find_verification(db: Session, submission_id: int) -> Optional[FareVerification]:
    return (
        db.query(FareVerification)
        .filter(FareVerification.submission_id == submission_id)
        .order_by(FareVerification.verified_at.desc())
        .first()
    )


def _get_submission_or_404(db: Session, submission_id: int) -> FareSubmission:
    submission = db.query(FareSubmission).filter(FareSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Fare submission not found")
    return submission


@router.post("/submit", status_code=201)
async def submit_fare(payload: FareSubmissionPayload, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    quotation_timestamp = payload.quotationTimestamp
    if quotation_timestamp.tzinfo is not None:
        quotation_timestamp = quotation_timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    recent_count = (
        db.query(FareSubmission)
        .filter(
            FareSubmission.device_fingerprint == payload.deviceFingerprint,
            FareSubmission.created_at >= now - timedelta(hours=1),
        )
        .count()
    )
    if recent_count >= 10:
        raise HTTPException(status_code=429, detail="Submission limit reached. Please try again later.")
    if quotation_timestamp > now + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Quotation time cannot be in the future.")
    if quotation_timestamp < now - timedelta(days=30):
        raise HTTPException(status_code=422, detail="Quotation time must be within the last 30 days.")

    pickup_lat, pickup_lng = payload.pickupCoordinates
    destination_lat, destination_lng = payload.destinationCoordinates
    submission = FareSubmission(
        device_fingerprint=payload.deviceFingerprint,
        provider=payload.provider,
        pickup_location=payload.pickupLocation.strip(),
        destination_location=payload.destinationLocation.strip(),
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        destination_lat=destination_lat,
        destination_lng=destination_lng,
        vehicle_category=payload.vehicleCategory.strip(),
        submitted_fare=payload.submittedFare,
        currency=payload.currency,
        quotation_timestamp=quotation_timestamp,
        estimated_distance_km=payload.estimatedDistanceKm,
        estimated_duration_min=payload.estimatedDurationMin,
        surge_multiplier=payload.surgeMultiplier,
        additional_fees=payload.additionalFees,
        screenshot_reference=payload.screenshotReference,
        route_fingerprint=route_fingerprint(pickup_lat, pickup_lng, destination_lat, destination_lng),
        submission_status="COMMUNITY_REPORTED",
        created_at=now,
    )
    db.add(submission)
    db.flush()

    verification = assess_submission(db, submission)
    submission.submission_status = verification.verification_status
    db.add(verification)
    if verification.verification_status in {"CORROBORATED", "VERIFIED"}:
        db.add(FareObservation(
            submission_id=submission.id,
            provider=submission.provider,
            route_fingerprint=submission.route_fingerprint,
            vehicle_category=submission.vehicle_category,
            observed_fare=submission.submitted_fare,
            observation_timestamp=submission.quotation_timestamp,
            evidence_type="community_submission",
            verification_status=verification.verification_status,
        ))
    db.commit()
    db.refresh(submission)
    return serialize_submission(submission, verification)


@router.get("/mine")
async def get_my_submissions(
    device_fingerprint: str = Query(min_length=16, max_length=128),
    db: Session = Depends(get_db),
):
    submissions = (
        db.query(FareSubmission)
        .filter(FareSubmission.device_fingerprint == device_fingerprint)
        .order_by(FareSubmission.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "submissions": [
            serialize_submission(item, _find_verification(db, item.id), vote_totals(db, item.id))
            for item in submissions
        ]
    }


@router.delete("/{submission_id}")
async def remove_my_submission(
    submission_id: int,
    device_fingerprint: str = Query(min_length=16, max_length=128),
    db: Session = Depends(get_db),
):
    submission = _get_submission_or_404(db, submission_id)
    if submission.device_fingerprint != device_fingerprint:
        raise HTTPException(status_code=403, detail="Only the submitting device can remove this report.")
    db.query(CommunityVote).filter(CommunityVote.submission_id == submission_id).delete(synchronize_session=False)
    db.query(FareObservation).filter(FareObservation.submission_id == submission_id).delete(synchronize_session=False)
    db.query(FareVerification).filter(FareVerification.submission_id == submission_id).delete(synchronize_session=False)
    db.delete(submission)
    db.commit()
    return {"deleted": True, "submissionId": submission_id}


@router.get("/verification/{submission_id}")
async def get_verification(submission_id: int, db: Session = Depends(get_db)):
    submission = _get_submission_or_404(db, submission_id)
    return serialize_submission(submission, _find_verification(db, submission_id), vote_totals(db, submission_id))


@router.get("/community")
async def get_community_reports(
    provider: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(FareSubmission).order_by(FareSubmission.created_at.desc())
    if provider:
        query = query.filter(FareSubmission.provider == provider.strip().title())
    if status:
        query = query.filter(FareSubmission.submission_status == status.upper())
    submissions = query.limit(limit).all()
    return {
        "reports": [
            serialize_submission(item, _find_verification(db, item.id), vote_totals(db, item.id))
            for item in submissions
        ],
        "notice": "Community reports are not live provider quotations.",
    }


@router.post("/verification/{submission_id}/vote")
async def vote_on_submission(
    submission_id: int,
    payload: FareVotePayload,
    db: Session = Depends(get_db),
):
    submission = _get_submission_or_404(db, submission_id)
    existing = (
        db.query(CommunityVote)
        .filter(
            CommunityVote.submission_id == submission_id,
            CommunityVote.device_fingerprint == payload.deviceFingerprint,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This anonymous device has already voted on this submission.")
    db.add(CommunityVote(
        submission_id=submission.id,
        device_fingerprint=payload.deviceFingerprint,
        vote_type=payload.voteType,
    ))
    db.commit()
    return {"submissionId": submission.id, "votes": vote_totals(db, submission.id)}


@router.get("/estimate")
async def estimate_fare(
    provider: str,
    vehicle_category: str,
    distance_km: float = Query(gt=0, le=1000),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(FareObservation.observed_fare)
        .filter(
            FareObservation.provider == provider.strip().title(),
            FareObservation.vehicle_category == vehicle_category,
            FareObservation.verification_status.in_({"VERIFIED", "CORROBORATED"}),
        )
        .all()
    )
    if not rows:
        rows = (
            db.query(HistoricalFare.actual_fare)
            .filter(
                HistoricalFare.provider.ilike(provider.strip()),
                HistoricalFare.vehicle_type.ilike(vehicle_category),
                HistoricalFare.distance_km.between(distance_km * 0.8, distance_km * 1.2),
            )
            .limit(100)
            .all()
        )
    fares = [float(row[0]) for row in rows if row[0] is not None]
    if not fares:
        return {"available": False, "message": "Insufficient verified data for this provider and vehicle category."}
    average = sum(fares) / len(fares)
    spread = max(10.0, average * 0.15)
    return {
        "available": True,
        "provider": provider.strip().title(),
        "vehicleCategory": vehicle_category,
        "historicalAverage": round(average, 2),
        "estimatedFareRange": {"min": round(max(0, average - spread), 2), "max": round(average + spread, 2)},
        "supportingObservations": len(fares),
        "isLiveProviderQuote": False,
    }


@router.get("/history")
async def fare_history(
    route: str = Query(min_length=1),
    provider: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(FareSubmission).filter(
        FareSubmission.submission_status.in_(("VERIFIED", "CORROBORATED")),
        FareSubmission.pickup_location.ilike(f"%{route}%") | FareSubmission.destination_location.ilike(f"%{route}%"),
    )
    if provider:
        query = query.filter(FareSubmission.provider == provider.strip().title())
    rows = query.order_by(FareSubmission.quotation_timestamp.desc()).limit(100).all()
    return {
        "observations": [
            serialize_submission(item, _find_verification(db, item.id), vote_totals(db, item.id))
            for item in rows
        ],
        "notice": "Historical observations are not current provider quotations.",
    }


@router.get("/model-status")
async def model_status(db: Session = Depends(get_db)):
    verified_count = db.query(FareSubmission).filter(FareSubmission.submission_status.in_(("VERIFIED", "CORROBORATED"))).count()
    return {
        "status": "baseline" if verified_count < 50 else "ready_for_training",
        "verifiedObservations": verified_count,
        "trainingExecuted": False,
        "message": "Transparent statistical baselines remain active until a versioned model is trained and evaluated.",
    }
