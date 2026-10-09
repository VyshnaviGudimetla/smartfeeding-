import io
import csv
import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.entities import Pond, FeedEstimate, WaterReading, AlertRecord

def get_feeding_trends(db: Session, pond_id: Optional[str] = None, days: int = 14) -> List[Dict[str, Any]]:
    # Generate daily feeding and cost timeline
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    query = db.query(FeedEstimate).filter(FeedEstimate.recorded_at >= cutoff)
    if pond_id and pond_id != "all":
        query = query.filter(FeedEstimate.pond_id == pond_id)
    
    estimates = query.order_by(FeedEstimate.recorded_at.asc()).all()
    results = []
    for est in estimates:
        results.append({
            "id": est.id,
            "pond_id": est.pond_id,
            "date": est.recorded_at.strftime("%Y-%m-%d"),
            "timestamp": est.recorded_at.isoformat(),
            "biomass_kg": round(est.biomass_kg, 2),
            "daily_feed_kg": round(est.daily_feed_kg, 2),
            "daily_cost": round(est.daily_cost, 2),
            "cost_30_days": round(est.cost_30_days, 2),
            "fish_count": est.fish_count,
            "avg_weight_g": est.avg_weight_g
        })
    return results

def get_water_quality_trends(db: Session, pond_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    query = db.query(WaterReading)
    if pond_id and pond_id != "all":
        query = query.filter(WaterReading.pond_id == pond_id)
    
    readings = query.order_by(WaterReading.recorded_at.desc()).limit(limit).all()
    readings.reverse() # Chronological order

    results = []
    for r in readings:
        results.append({
            "id": r.id,
            "pond_id": r.pond_id,
            "time": r.recorded_at.strftime("%H:%M"),
            "timestamp": r.recorded_at.isoformat(),
            "temperature_c": r.temperature_c,
            "ph": r.ph,
            "dissolved_oxygen_mg_l": r.dissolved_oxygen_mg_l,
            "salinity_ppt": r.salinity_ppt,
            "ammonia_mg_l": r.ammonia_mg_l,
            "status": r.status,
            "source": r.source
        })
    return results

def export_feeding_history_csv(db: Session, pond_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """
    REP-07 & REP-08: RFC-4180 Compliant CSV Export with proper escaping of quotes & commas
    """
    query = db.query(FeedEstimate)
    if pond_id and pond_id != "all":
        query = query.filter(FeedEstimate.pond_id == pond_id)
    if start_date:
        query = query.filter(FeedEstimate.recorded_at >= datetime.datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(FeedEstimate.recorded_at <= datetime.datetime.fromisoformat(end_date))

    records = query.order_by(FeedEstimate.recorded_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Headers
    writer.writerow([
        "Record ID",
        "Pond ID",
        "Timestamp (UTC)",
        "Fish Count",
        "Average Weight (g)",
        "Feeding Rate (%)",
        "Feed Price per kg (INR)",
        "Total Biomass (kg)",
        "Daily Feed Required (kg)",
        "Daily Feed Cost (INR)",
        "30-Day Cost Estimate (INR)",
        "Notes & Observations"
    ])

    for r in records:
        writer.writerow([
            r.id,
            r.pond_id,
            r.recorded_at.isoformat(),
            r.fish_count,
            f"{r.avg_weight_g:.2f}",
            f"{r.feeding_rate_pct:.2f}%",
            f"{r.feed_price_per_kg:.2f}",
            f"{r.biomass_kg:.2f}",
            f"{r.daily_feed_kg:.2f}",
            f"{r.daily_cost:.2f}",
            f"{r.cost_30_days:.2f}",
            r.notes or "Standard biological calculation"
        ])

    return output.getvalue()

def export_water_readings_csv(db: Session, pond_id: Optional[str] = None) -> str:
    query = db.query(WaterReading)
    if pond_id and pond_id != "all":
        query = query.filter(WaterReading.pond_id == pond_id)
    
    records = query.order_by(WaterReading.recorded_at.desc()).limit(200).all()

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "Reading ID",
        "Pond ID",
        "Timestamp (UTC)",
        "Temperature (°C)",
        "pH",
        "Dissolved Oxygen (mg/L)",
        "Salinity (ppt)",
        "Ammonia NH3/NH4 (mg/L)",
        "Health Status",
        "Telemetry Source"
    ])

    for r in records:
        writer.writerow([
            r.id,
            r.pond_id,
            r.recorded_at.isoformat(),
            f"{r.temperature_c:.1f}" if r.temperature_c is not None else "N/A",
            f"{r.ph:.2f}" if r.ph is not None else "N/A",
            f"{r.dissolved_oxygen_mg_l:.2f}" if r.dissolved_oxygen_mg_l is not None else "N/A",
            f"{r.salinity_ppt:.1f}" if r.salinity_ppt is not None else "N/A",
            f"{r.ammonia_mg_l:.3f}" if r.ammonia_mg_l is not None else "N/A",
            r.status.upper(),
            r.source
        ])

    return output.getvalue()
