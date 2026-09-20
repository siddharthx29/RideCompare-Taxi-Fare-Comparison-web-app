"""
Analytics Router & Booking Redirect Logger (Python Implementation)
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.db_models import Search, Analytics

router = APIRouter(tags=["Analytics"])


class RedirectPayload(BaseModel):
    searchId: Optional[int] = None
    provider: str
    fare: Optional[float] = 0.0
    ride_type: Optional[str] = None
    pickup: Optional[str] = None
    drop: Optional[str] = None
    city: Optional[str] = None


@router.post("/redirect")
async def record_booking_redirect(payload: RedirectPayload, db: Session = Depends(get_db)):
    try:
        # Update search record with selected provider
        if payload.searchId:
            search_item = db.query(Search).filter(Search.id == payload.searchId).first()
            if search_item:
                search_item.selected_provider = payload.provider
                db.commit()

        # Update or insert into analytics ledger for today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        analytic_item = db.query(Analytics).filter(
            Analytics.provider == payload.provider,
            Analytics.created_at >= today_start
        ).first()

        if analytic_item:
            analytic_item.clicks = (analytic_item.clicks or 0) + 1
            analytic_item.redirects = (analytic_item.redirects or 0) + 1
            analytic_item.fare = (analytic_item.fare or 0.0) + (payload.fare or 0.0)
        else:
            new_item = Analytics(
                provider=payload.provider,
                clicks=1,
                redirects=1,
                fare=payload.fare or 0.0
            )
            db.add(new_item)

        db.commit()

        # Generate default redirect URL based on provider
        p_lower = payload.provider.lower()
        if "uber" in p_lower:
            redirect_url = "https://m.uber.com/looking"
        elif "ola" in p_lower:
            redirect_url = "https://www.olacabs.com/"
        elif "rapido" in p_lower:
            redirect_url = "https://www.rapido.bike/"
        else:
            redirect_url = "https://www.google.com/search?q=taxi+booking"

        return {
            "success": True,
            "redirect_url": redirect_url,
            "provider": payload.provider
        }
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record booking redirect: {str(err)}")


@router.get("/analytics")
async def get_aggregated_analytics(db: Session = Depends(get_db)):
    try:
        # 1. Total searches & average savings
        total_searches = db.query(Search).count()
        avg_savings_val = db.query(func.coalesce(func.avg(Search.savings), 0.0)).scalar()
        avg_savings = round(float(avg_savings_val))

        # 2. Top 5 Popular Routes
        popular_routes_rows = db.query(
            Search.source,
            Search.destination,
            func.count(Search.id).label("count")
        ).group_by(Search.source, Search.destination).order_by(func.count(Search.id).desc()).limit(5).all()

        popular_routes = [
            {"source": r.source, "destination": r.destination, "count": int(r.count)}
            for r in popular_routes_rows
        ]

        # 3. Provider Shares (Clicks, Redirects, Fare)
        provider_shares_rows = db.query(
            Analytics.provider,
            func.sum(Analytics.clicks).label("clicks"),
            func.sum(Analytics.redirects).label("redirects"),
            func.sum(Analytics.fare).label("total_fare")
        ).group_by(Analytics.provider).order_by(func.sum(Analytics.clicks).desc()).all()

        provider_shares = [
            {
                "provider": r.provider,
                "clicks": int(r.clicks or 0),
                "redirects": int(r.redirects or 0),
                "total_fare": float(r.total_fare or 0.0)
            }
            for r in provider_shares_rows
        ]

        # 4. 7-Day Daily Trends
        now = datetime.utcnow()
        daily_trends = []
        for i in range(6, -1, -1):
            day_date = (now - timedelta(days=i)).date()
            day_start = datetime.combine(day_date, datetime.min.time())
            day_end = datetime.combine(day_date, datetime.max.time())
            
            day_count = db.query(Search).filter(
                Search.created_at >= day_start,
                Search.created_at <= day_end
            ).count()

            daily_trends.append({
                "date": day_date.strftime("%Y-%m-%d"),
                "count": day_count
            })

        # 5. Cheapest Provider Selection Rates
        cheapest_rows = db.query(
            Search.cheapest_provider.label("provider"),
            func.count(Search.id).label("times_cheapest"),
            func.count(case((Search.selected_provider == Search.cheapest_provider, 1))).label("times_selected")
        ).filter(Search.cheapest_provider != None).group_by(Search.cheapest_provider).all()

        cheapest_provider_selections = [
            {
                "provider": r.provider,
                "times_cheapest": int(r.times_cheapest or 0),
                "times_selected": int(r.times_selected or 0)
            }
            for r in cheapest_rows
        ]

        # Selection percentage
        total_with_sel = db.query(Search).filter(Search.selected_provider != None).count()
        cheapest_selections = db.query(Search).filter(
            Search.selected_provider != None,
            Search.selected_provider == Search.cheapest_provider
        ).count()
        
        selection_rate = round((cheapest_selections / total_with_sel) * 100) if total_with_sel > 0 else 0

        return {
            "totalSearches": total_searches,
            "averageSavings": avg_savings,
            "avgSavings": avg_savings,
            "topRoutes": popular_routes,
            "popularRoutes": popular_routes,
            "providerClickShare": provider_shares,
            "providerShares": provider_shares,
            "dailyTrends": daily_trends,
            "cheapestProviderSelections": cheapest_provider_selections,
            "cheapestSelectionRate": selection_rate
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analytics: {str(err)}")
