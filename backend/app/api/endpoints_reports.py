import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.entities import Pond, FeedEstimate, WaterReading, AlertRecord
from app.models.schemas import DashboardSummary
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])

@router.get("/dashboard-summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    ponds = db.query(Pond).all()
    active_count = len(ponds)
    total_biomass = sum(p.biomass_kg for p in ponds)
    total_daily_feed = sum(p.daily_feed_kg for p in ponds)
    total_daily_cost = sum(p.daily_cost for p in ponds)
    monthly_cost = total_daily_cost * 30.0

    optimal = sum(1 for p in ponds if p.status == "Optimal")
    caution = sum(1 for p in ponds if p.status == "Caution")
    critical = sum(1 for p in ponds if p.status == "Critical")

    active_alerts = db.query(AlertRecord).filter(AlertRecord.is_resolved == False).count()

    return DashboardSummary(
        active_ponds_count=active_count,
        total_biomass_kg=round(total_biomass, 2),
        daily_feed_kg=round(total_daily_feed, 2),
        daily_cost=round(total_daily_cost, 2),
        monthly_cost_estimate=round(monthly_cost, 2),
        optimal_ponds=optimal,
        caution_ponds=caution,
        critical_ponds=critical,
        active_alerts_count=active_alerts,
        backend_status="Connected (FastAPI 0.143)",
        demo_mode=True,
        server_time=datetime.datetime.utcnow()
    )

@router.get("/feeding-trends")
def get_feeding_trends(pond_id: Optional[str] = None, days: int = 14, db: Session = Depends(get_db)):
    return report_service.get_feeding_trends(db, pond_id=pond_id, days=days)

@router.get("/water-trends")
def get_water_trends(pond_id: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    return report_service.get_water_quality_trends(db, pond_id=pond_id, limit=limit)

@router.get("/export-feeding-csv")
def export_feeding_csv(
    pond_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    csv_data = report_service.export_feeding_history_csv(db, pond_id=pond_id, start_date=start_date, end_date=end_date)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aquasmart_feeding_history.csv"}
    )

@router.get("/export-water-csv")
def export_water_csv(pond_id: Optional[str] = None, db: Session = Depends(get_db)):
    csv_data = report_service.export_water_readings_csv(db, pond_id=pond_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aquasmart_water_telemetry.csv"}
    )
