import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import httpx
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.db_models import SeoKeyword, SeoPage, SeoSearchMetric

logger = logging.getLogger(__name__)


def get_integrations_status() -> Dict[str, Any]:
    """Report configuration status of GSC, Bing Webmaster Tools, and GA4 without exposing secrets."""
    return {
        "google_search_console": {
            "configured": bool(settings.GSC_SITE_URL and settings.GOOGLE_SERVICE_ACCOUNT_JSON),
            "site_url": settings.GSC_SITE_URL or None,
            "required_env": ["GSC_SITE_URL", "GOOGLE_SERVICE_ACCOUNT_JSON"],
        },
        "bing_webmaster_tools": {
            "configured": bool(settings.BING_WEBMASTER_API_KEY),
            "site_url": settings.SITE_URL,
            "required_env": ["BING_WEBMASTER_API_KEY"],
        },
        "google_analytics_4": {
            "configured": bool(settings.GA4_PROPERTY_ID and settings.GOOGLE_SERVICE_ACCOUNT_JSON),
            "property_id": settings.GA4_PROPERTY_ID or None,
            "required_env": ["GA4_PROPERTY_ID", "GOOGLE_SERVICE_ACCOUNT_JSON"],
        },
    }


def _apply_metric_to_records(
    db: Session,
    page_url: str | None,
    query: str | None,
    clicks: int,
    impressions: int,
    ctr: float,
    position: float | None,
) -> None:
    if page_url:
        normalized_path = "/" + page_url.replace(settings.SITE_URL, "").strip("/") + "/"
        if normalized_path == "//":
            normalized_path = "/"
        page = (
            db.query(SeoPage)
            .filter((SeoPage.canonical_url == page_url) | (SeoPage.slug == normalized_path))
            .first()
        )
        if page:
            page.clicks = clicks
            page.impressions = impressions
            page.ctr = ctr
            if position is not None:
                page.avg_position = position

    if query:
        kw = (
            db.query(SeoKeyword)
            .filter(SeoKeyword.normalized_keyword == " ".join(query.lower().split()))
            .first()
        )
        if kw:
            kw.clicks = clicks
            kw.impressions = impressions
            kw.ctr = ctr
            if position is not None:
                kw.avg_position = position


async def sync_bing_webmaster_metrics(db: Session) -> Dict[str, Any]:
    """Fetch query and page performance from Bing Webmaster Tools API when BING_WEBMASTER_API_KEY is set."""
    api_key = settings.BING_WEBMASTER_API_KEY
    if not api_key:
        return {"status": "not_configured", "message": "Set BING_WEBMASTER_API_KEY to enable Bing Webmaster sync."}

    site_url = f"{settings.SITE_URL}/"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    imported = 0

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            q_res = await client.get(
                "https://ssl.bing.com/webmaster/api.svc/json/GetQueryStats",
                params={"apikey": api_key, "siteUrl": site_url},
            )
            if q_res.status_code == 200:
                payload = q_res.json()
                rows: List[Dict[str, Any]] = payload.get("d", []) if isinstance(payload, dict) else []
                for row in rows[:200]:
                    query = str(row.get("Query", "")).strip()
                    clicks = int(row.get("Clicks", 0) or 0)
                    impressions = int(row.get("Impressions", 0) or 0)
                    pos = float(row.get("AvgImpressionPosition")) if row.get("AvgImpressionPosition") else None
                    ctr = round(clicks / impressions, 4) if impressions > 0 else 0.0
                    db.add(
                        SeoSearchMetric(
                            date=today,
                            source="bing",
                            query=query,
                            clicks=clicks,
                            impressions=impressions,
                            ctr=ctr,
                            position=pos,
                        )
                    )
                    _apply_metric_to_records(db, None, query, clicks, impressions, ctr, pos)
                    imported += 1

            p_res = await client.get(
                "https://ssl.bing.com/webmaster/api.svc/json/GetPageStats",
                params={"apikey": api_key, "siteUrl": site_url},
            )
            if p_res.status_code == 200:
                payload = p_res.json()
                rows = payload.get("d", []) if isinstance(payload, dict) else []
                for row in rows[:200]:
                    page_url = str(row.get("Query", "")).strip()
                    clicks = int(row.get("Clicks", 0) or 0)
                    impressions = int(row.get("Impressions", 0) or 0)
                    pos = float(row.get("AvgImpressionPosition")) if row.get("AvgImpressionPosition") else None
                    ctr = round(clicks / impressions, 4) if impressions > 0 else 0.0
                    db.add(
                        SeoSearchMetric(
                            date=today,
                            source="bing",
                            page_url=page_url,
                            clicks=clicks,
                            impressions=impressions,
                            ctr=ctr,
                            position=pos,
                        )
                    )
                    _apply_metric_to_records(db, page_url, None, clicks, impressions, ctr, pos)
                    imported += 1

        db.commit()
        return {"status": "connected", "imported_records": imported}
    except Exception as exc:
        logger.warning("Bing Webmaster API sync failed: %s", exc)
        return {"status": "error", "message": str(exc)}


async def sync_google_search_console(db: Session) -> Dict[str, Any]:
    """
    Prepare Google Search Console Search Analytics sync.
    Uses service account JSON when GOOGLE_SERVICE_ACCOUNT_JSON + GSC_SITE_URL are configured.
    """
    if not (settings.GSC_SITE_URL and settings.GOOGLE_SERVICE_ACCOUNT_JSON):
        return {
            "status": "not_configured",
            "message": "Set GSC_SITE_URL and GOOGLE_SERVICE_ACCOUNT_JSON to enable Google Search Console sync.",
        }

    try:
        sa_info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
    except json.JSONDecodeError:
        return {"status": "error", "message": "GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON."}

    try:
        from google.oauth2 import service_account  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
    except ImportError:
        return {
            "status": "dependency_missing",
            "message": "Install google-auth to enable live GSC OAuth2 token exchange, or import GSC CSV exports via /api/seo/admin/keywords/import-csv.",
        }

    try:
        creds = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        creds.refresh(Request())
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=28)
        encoded_site = settings.GSC_SITE_URL.replace(":", "%3A").replace("/", "%2F")
        url = f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query"

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                url,
                headers={"Authorization": f"Bearer {creds.token}"},
                json={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "dimensions": ["query", "page"],
                    "rowLimit": 250,
                },
            )
        if res.status_code != 200:
            return {"status": "error", "message": f"GSC API returned HTTP {res.status_code}"}

        rows = res.json().get("rows", [])
        imported = 0
        for row in rows:
            keys = row.get("keys", [])
            query = keys[0] if len(keys) > 0 else None
            page_url = keys[1] if len(keys) > 1 else None
            clicks = int(row.get("clicks", 0) or 0)
            impressions = int(row.get("impressions", 0) or 0)
            ctr = float(row.get("ctr", 0.0) or 0.0)
            position = float(row.get("position")) if row.get("position") is not None else None
            db.add(
                SeoSearchMetric(
                    date=end_date.isoformat(),
                    source="gsc",
                    page_url=page_url,
                    query=query,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=ctr,
                    position=position,
                )
            )
            _apply_metric_to_records(db, page_url, query, clicks, impressions, ctr, position)
            imported += 1
        db.commit()
        return {"status": "connected", "imported_records": imported}
    except Exception as exc:
        logger.warning("GSC sync failed: %s", exc)
        return {"status": "error", "message": str(exc)}
