import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.db_models import SeoAuditLog, SeoKeyword, SeoPage
from backend.app.services.search_integrations import (
    get_integrations_status,
    sync_bing_webmaster_metrics,
    sync_google_search_console,
)
from backend.app.services.seo_engine import (
    generate_sitemap_xml,
    import_keywords_csv,
    run_maintenance,
    sync_catalog_to_seo,
)

router = APIRouter(prefix="/api/seo", tags=["Programmatic SEO Engine"])


def verify_admin_or_cron(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    key: Optional[str] = Query(None),
) -> bool:
    if settings.ENVIRONMENT.lower() in {"production", "prod"}:
        if settings.CRON_SECRET and authorization == f"Bearer {settings.CRON_SECRET}":
            return True
        if settings.ADMIN_KEY:
            token = x_admin_key or key
            if not token or token != settings.ADMIN_KEY:
                raise HTTPException(status_code=403, detail="Unauthorized: Invalid admin or cron key")
    return True


class KeywordCsvImportPayload(BaseModel):
    csv_text: str = Field(min_length=5)
    source: str = Field(default="csv_import", max_length=40)


class PageStatusPayload(BaseModel):
    status: str = Field(pattern="^(published|draft|rejected|archived)$")


def _serialize_page(page: SeoPage, include_content: bool = False) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "page_id": page.page_id,
        "slug": page.slug,
        "page_type": page.page_type,
        "target_keyword": page.target_keyword,
        "secondary_keywords": json.loads(page.secondary_keywords or "[]"),
        "location": page.location,
        "search_intent": page.search_intent,
        "seo_title": page.seo_title,
        "meta_description": page.meta_description,
        "h1": page.h1,
        "status": page.status,
        "quality_score": page.quality_score,
        "quality_issues": json.loads(page.quality_issues or "[]"),
        "canonical_url": page.canonical_url,
        "is_indexable": page.is_indexable,
        "impressions": page.impressions,
        "clicks": page.clicks,
        "ctr": page.ctr,
        "avg_position": page.avg_position,
        "last_updated": page.last_updated.isoformat() if page.last_updated else None,
    }
    if include_content:
        data["content"] = json.loads(page.content_json or "{}")
    return data


@router.get("/pages")
def list_published_seo_pages(db: Session = Depends(get_db)):
    if db.query(SeoPage).count() == 0:
        sync_catalog_to_seo(db)
    pages = (
        db.query(SeoPage)
        .filter(SeoPage.status == "published", SeoPage.is_indexable.is_(True))
        .order_by(SeoPage.page_type.asc(), SeoPage.slug.asc())
        .all()
    )
    return {"count": len(pages), "pages": [_serialize_page(p) for p in pages]}


@router.get("/pages/{slug:path}")
def get_seo_page_detail(slug: str, db: Session = Depends(get_db)):
    if db.query(SeoPage).count() == 0:
        sync_catalog_to_seo(db)
    normalized = "/" + slug.strip("/")
    candidates = [normalized, f"{normalized}/"]
    page = db.query(SeoPage).filter(SeoPage.slug.in_(candidates), SeoPage.status == "published").first()
    if not page:
        raise HTTPException(status_code=404, detail="SEO page not found")
    return _serialize_page(page, include_content=True)


@router.get("/sitemap.xml", include_in_schema=False)
def get_dynamic_sitemap(db: Session = Depends(get_db)):
    if db.query(SeoPage).count() == 0:
        sync_catalog_to_seo(db)
    xml_body = generate_sitemap_xml(db)
    return Response(content=xml_body, media_type="application/xml")


@router.get("/admin/overview")
def get_seo_admin_overview(
    _: bool = Depends(verify_admin_or_cron),
    db: Session = Depends(get_db),
):
    if db.query(SeoPage).count() == 0:
        sync_catalog_to_seo(db)

    pages = db.query(SeoPage).order_by(SeoPage.page_type.asc(), SeoPage.slug.asc()).all()
    keywords = db.query(SeoKeyword).order_by(SeoKeyword.opportunity_score.desc()).limit(100).all()
    audits = db.query(SeoAuditLog).order_by(SeoAuditLog.created_at.desc()).limit(10).all()

    published_count = sum(1 for p in pages if p.status == "published")
    top_pages = sorted(pages, key=lambda p: (p.clicks, p.impressions), reverse=True)[:5]
    underperforming_pages = [
        p for p in pages if p.status == "published" and (p.quality_score < 100.0 or (p.impressions >= 50 and p.ctr < 0.02))
    ][:5]

    return {
        "summary": {
            "total_pages": len(pages),
            "published_pages": published_count,
            "draft_or_flagged_pages": len(pages) - published_count,
            "total_keywords": db.query(SeoKeyword).count(),
            "unmapped_keywords": db.query(SeoKeyword).filter(SeoKeyword.mapped_page_slug.is_(None)).count(),
        },
        "integrations": get_integrations_status(),
        "pages": [_serialize_page(p) for p in pages],
        "keywords": [
            {
                "id": k.id,
                "keyword": k.keyword,
                "category": k.category,
                "intent": k.intent,
                "location": k.location,
                "search_volume": k.search_volume,
                "keyword_difficulty": k.keyword_difficulty,
                "impressions": k.impressions,
                "clicks": k.clicks,
                "ctr": k.ctr,
                "avg_position": k.avg_position,
                "mapped_page_slug": k.mapped_page_slug,
                "opportunity_score": k.opportunity_score,
                "data_source": k.data_source,
            }
            for k in keywords
        ],
        "top_performing_pages": [_serialize_page(p) for p in top_pages],
        "underperforming_pages": [_serialize_page(p) for p in underperforming_pages],
        "audit_logs": [
            {
                "id": a.id,
                "run_type": a.run_type,
                "status": a.status,
                "summary": a.summary,
                "recommendations": json.loads(a.recommendations_json or "[]"),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in audits
        ],
    }


@router.post("/admin/sync-catalog")
def trigger_catalog_sync(
    _: bool = Depends(verify_admin_or_cron),
    db: Session = Depends(get_db),
):
    return sync_catalog_to_seo(db)


@router.post("/admin/keywords/import-csv")
def import_keyword_research_csv(
    payload: KeywordCsvImportPayload,
    _: bool = Depends(verify_admin_or_cron),
    db: Session = Depends(get_db),
):
    return import_keywords_csv(db, payload.csv_text, source=payload.source)


@router.patch("/admin/pages/{page_id}/status")
def update_seo_page_status(
    page_id: str,
    payload: PageStatusPayload,
    _: bool = Depends(verify_admin_or_cron),
    db: Session = Depends(get_db),
):
    page = db.query(SeoPage).filter(SeoPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="SEO page not found")
    if payload.status == "published" and page.quality_score < 75.0:
        raise HTTPException(
            status_code=422,
            detail=f"Page failed quality validation (score {page.quality_score}): {page.quality_issues}",
        )
    page.status = payload.status
    page.is_indexable = payload.status == "published"
    db.commit()
    return _serialize_page(page)


@router.post("/admin/integrations/sync")
async def trigger_search_integrations_sync(
    _: bool = Depends(verify_admin_or_cron),
    db: Session = Depends(get_db),
):
    gsc = await sync_google_search_console(db)
    bing = await sync_bing_webmaster_metrics(db)
    return {"google_search_console": gsc, "bing_webmaster_tools": bing}


@router.api_route("/admin/maintenance/run", methods=["GET", "POST"])
def trigger_seo_maintenance(
    cadence: str = Query("daily", pattern="^(daily|weekly|monthly|manual)$"),
    _: bool = Depends(verify_admin_or_cron),
    db: Session = Depends(get_db),
):
    return run_maintenance(db, cadence=cadence)
