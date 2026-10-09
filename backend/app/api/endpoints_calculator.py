from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.entities import FeedEstimate, Pond
from app.models.schemas import FeedEstimateCreate, FeedEstimateResponse
from app.services.calculator import (
    calculate_feeding,
    calculate_pond_volume,
    FeedingCalculationInput,
    FeedingCalculationResult,
    PondVolumeInput,
    PondVolumeResult
)

router = APIRouter(tags=["Calculations"])

@router.post("/feeding-estimate", response_model=FeedingCalculationResult)
def estimate_feeding(inputs: FeedingCalculationInput):
    """
    POST /feeding-estimate — Core API calculation endpoint (FR-02, CALC-01..16)
    Calculates Biomass, Daily Feed Requirement, Daily Cost, and 30-Day Projection.
    """
    return calculate_feeding(inputs)

@router.post("/volume-estimate", response_model=PondVolumeResult)
def estimate_volume(inputs: PondVolumeInput):
    """
    POST /volume-estimate — Pond water-volume calculation endpoint (VOL-01..10)
    Supports rectangular, circular, and irregular pond shapes.
    """
    return calculate_pond_volume(inputs)

@router.post("/feeding-history", response_model=FeedEstimateResponse, status_code=status.HTTP_201_CREATED)
def save_feeding_estimate(est_in: FeedEstimateCreate, db: Session = Depends(get_db)):
    # Calculate
    calc = calculate_feeding({
        "fish_count": est_in.fish_count,
        "avg_weight_g": est_in.avg_weight_g,
        "feeding_rate_pct": est_in.feeding_rate_pct,
        "feed_price_per_kg": est_in.feed_price_per_kg
    })
    
    rec = FeedEstimate(
        pond_id=est_in.pond_id,
        fish_count=est_in.fish_count,
        avg_weight_g=est_in.avg_weight_g,
        feeding_rate_pct=est_in.feeding_rate_pct,
        feed_price_per_kg=est_in.feed_price_per_kg,
        biomass_kg=calc.biomass_kg,
        daily_feed_kg=calc.daily_feed_kg,
        daily_cost=calc.daily_cost,
        cost_30_days=calc.cost_30_days,
        notes=est_in.notes
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

@router.get("/feeding-history", response_model=List[FeedEstimateResponse])
def get_feeding_history(pond_id: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(FeedEstimate)
    if pond_id and pond_id != "all":
        q = q.filter(FeedEstimate.pond_id == pond_id)
    return q.order_by(FeedEstimate.recorded_at.desc()).limit(limit).all()
