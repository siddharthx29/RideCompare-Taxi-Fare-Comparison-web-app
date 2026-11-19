import hashlib
import math
from datetime import datetime, timedelta
from statistics import mean, pstdev
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.app.models.db_models import (
    CommunityVote,
    FareObservation,
    FareSubmission,
    FareVerification,
    HistoricalFare,
)
from ml.inference.predictor import FareIntelligenceEngine


SUPPORTED_PROVIDERS = {"uber", "ola", "rapido"}
VOTE_TYPES = {"CONFIRM", "MISMATCH", "OUTDATED", "SUSPICIOUS"}
PUBLISHED_STATUSES = {"VERIFIED", "CORROBORATED", "COMMUNITY_REPORTED", "UNDER_REVIEW"}
_fare_engine = FareIntelligenceEngine()


def route_fingerprint(pickup_lat: float, pickup_lng: float, destination_lat: float, destination_lng: float) -> str:
    rounded = "|".join(f"{value:.3f}" for value in (pickup_lat, pickup_lng, destination_lat, destination_lng))
    return hashlib.sha256(rounded.encode("utf-8")).hexdigest()


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    lat_delta = math.radians(lat2 - lat1)
    lng_delta = math.radians(lng2 - lng1)
    a = math.sin(lat_delta / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(lng_delta / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _reference_fares(db: Session, submission: FareSubmission) -> List[float]:
    cutoff = submission.quotation_timestamp - timedelta(days=30)
    observations = (
        db.query(FareObservation.observed_fare)
        .filter(
            FareObservation.route_fingerprint == submission.route_fingerprint,
            FareObservation.provider == submission.provider,
            FareObservation.vehicle_category == submission.vehicle_category,
            FareObservation.verification_status.in_({"VERIFIED", "CORROBORATED"}),
            FareObservation.observation_timestamp >= cutoff,
        )
        .all()
    )
    historical = (
        db.query(HistoricalFare.actual_fare)
        .filter(
            HistoricalFare.provider.ilike(submission.provider),
            HistoricalFare.vehicle_type.ilike(submission.vehicle_category),
            HistoricalFare.distance_km.between(
                max(0.1, submission.estimated_distance_km * 0.8),
                submission.estimated_distance_km * 1.2,
            ),
        )
        .order_by(HistoricalFare.created_at.desc())
        .limit(100)
        .all()
    )
    return [float(row[0]) for row in observations + historical if row[0] is not None and float(row[0]) > 0]


def _duplicate_submission(db: Session, submission: FareSubmission) -> bool:
    window_start = submission.created_at - timedelta(hours=24)
    return (
        db.query(FareSubmission.id)
        .filter(
            FareSubmission.device_fingerprint == submission.device_fingerprint,
            FareSubmission.route_fingerprint == submission.route_fingerprint,
            FareSubmission.provider == submission.provider,
            FareSubmission.vehicle_category == submission.vehicle_category,
            FareSubmission.submitted_fare == submission.submitted_fare,
            FareSubmission.created_at >= window_start,
            FareSubmission.id != submission.id,
        )
        .first()
        is not None
    )


def assess_submission(db: Session, submission: FareSubmission) -> FareVerification:
    fares = _reference_fares(db, submission)
    ml_result = _fare_engine.predict_provider_fare({
        "provider": submission.provider,
        "vehicle_type": submission.vehicle_category,
        "distance_km": submission.estimated_distance_km,
        "duration_min": submission.estimated_duration_min,
        "actual_fare": submission.submitted_fare,
        "surge_multiplier": submission.surge_multiplier or 1.0,
    })
    historical_predicted = round(mean(fares), 2) if fares else None
    predicted = historical_predicted if historical_predicted is not None else ml_result.get("predicted_fare")
    deviation = abs(submission.submitted_fare - predicted) / predicted if predicted else 0.0
    duplicate = _duplicate_submission(db, submission)
    suspicious_reasons: List[str] = []

    if duplicate:
        suspicious_reasons.append("This matches a recent submission from the same anonymous device.")
    if submission.estimated_distance_km <= 0 or submission.estimated_duration_min <= 0:
        suspicious_reasons.append("Distance and duration must be positive.")
    if submission.submitted_fare / max(submission.estimated_distance_km, 0.1) > 500:
        suspicious_reasons.append("Fare per kilometre is unusually high for the submitted route.")
    if predicted is not None and deviation > 0.5:
        suspicious_reasons.append("The fare differs materially from comparable verified observations.")
    if ml_result.get("is_anomaly"):
        suspicious_reasons.append("The anomaly model flagged this fare for additional review.")

    if duplicate or len(suspicious_reasons) >= 2:
        status = "UNDER_REVIEW"
    elif not fares:
        status = "COMMUNITY_REPORTED"
    elif deviation <= 0.12 and len(fares) >= 3:
        status = "CORROBORATED"
    else:
        status = "COMMUNITY_REPORTED"

    evidence_count = len(fares)
    confidence = min(0.95, 0.25 + min(evidence_count, 10) * 0.05)
    if status == "UNDER_REVIEW":
        confidence = min(confidence, 0.4)
    if submission.screenshot_reference:
        confidence = min(0.98, confidence + 0.05)

    explanation = (
        f"{evidence_count} comparable reference observation(s) were found. "
        "A model or statistical match is an assessment, not proof of authenticity."
    )
    if historical_predicted is None:
        explanation = "No independent live or verified historical fare was available; this remains a community report."
        explanation += " An ML estimate is shown for context only and is not evidence of provider verification."
    if suspicious_reasons:
        explanation += " Review flags: " + " ".join(suspicious_reasons)

    return FareVerification(
        submission_id=submission.id,
        verification_method="verified_history_and_rule_checks" if fares else "rule_checks_only",
        reference_fare=predicted,
        predicted_fare=predicted,
        confidence_score=round(confidence, 3),
        anomaly_score=round(min(1.0, deviation), 3) if predicted is not None else None,
        verification_status=status,
        verification_explanation=explanation,
        evidence_count=evidence_count,
    )


def vote_totals(db: Session, submission_id: int) -> Dict[str, int]:
    rows = (
        db.query(CommunityVote.vote_type)
        .filter(CommunityVote.submission_id == submission_id)
        .all()
    )
    totals = {vote: 0 for vote in VOTE_TYPES}
    for (vote_type,) in rows:
        if vote_type in totals:
            totals[vote_type] += 1
    return totals


def serialize_submission(
    submission: FareSubmission,
    verification: Optional[FareVerification],
    votes: Optional[Dict[str, int]] = None,
) -> Dict:
    votes = votes or {}
    return {
        "id": submission.id,
        "provider": submission.provider,
        "pickupLocation": submission.pickup_location,
        "destinationLocation": submission.destination_location,
        "vehicleCategory": submission.vehicle_category,
        "submittedFare": submission.submitted_fare,
        "currency": submission.currency,
        "quotationTimestamp": submission.quotation_timestamp.isoformat(),
        "estimatedDistanceKm": submission.estimated_distance_km,
        "estimatedDurationMin": submission.estimated_duration_min,
        "surgeMultiplier": submission.surge_multiplier,
        "additionalFees": submission.additional_fees,
        "hasScreenshot": bool(submission.screenshot_reference),
        "status": verification.verification_status if verification else submission.submission_status,
        "confidenceScore": verification.confidence_score if verification else 0,
        "predictedFare": verification.predicted_fare if verification else None,
        "referenceFare": verification.reference_fare if verification else None,
        "anomalyScore": verification.anomaly_score if verification else None,
        "explanation": verification.verification_explanation if verification else "Awaiting verification.",
        "evidenceCount": verification.evidence_count if verification else 0,
        "votes": votes,
        "createdAt": submission.created_at.isoformat(),
    }
