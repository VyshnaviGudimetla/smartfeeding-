import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.entities import Pond, SensorThreshold, FeedEstimate
from app.models.schemas import PondCreate, PondUpdate
from app.services.calculator import calculate_feeding, calculate_pond_volume

def get_ponds(db: Session, search: Optional[str] = None, species: Optional[str] = None) -> List[Pond]:
    query = db.query(Pond)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter((Pond.name.ilike(s)) | (Pond.species.ilike(s)) | (Pond.id.ilike(s)))
    if species and species != "all":
        query = query.filter(Pond.species.ilike(f"%{species.strip()}%"))
    return query.order_by(Pond.id.asc()).all()

def get_pond_by_id(db: Session, pond_id: str) -> Optional[Pond]:
    return db.query(Pond).filter(Pond.id == pond_id).first()

def create_pond(db: Session, pond_in: PondCreate) -> Pond:
    # POND-10: Duplicate pond name check
    existing = db.query(Pond).filter(Pond.name.ilike(pond_in.name.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A pond with name '{pond_in.name}' already exists. Pond names must be unique across the facility."
        )

    pond_id = pond_in.id or f"pond-{uuid.uuid4().hex[:6]}"
    
    # Calculate volume based on shape
    vol_res = calculate_pond_volume({
        "shape": pond_in.shape,
        "length_m": pond_in.length_m,
        "width_m": pond_in.width_m,
        "diameter_m": pond_in.diameter_m,
        "surface_area_m2": pond_in.surface_area_m2,
        "depth_m": pond_in.depth_m
    })

    # Calculate biomass and feed
    feed_res = calculate_feeding({
        "fish_count": pond_in.fish_count,
        "avg_weight_g": pond_in.avg_weight_g,
        "feeding_rate_pct": pond_in.feeding_rate_pct,
        "feed_price_per_kg": pond_in.feed_price_per_kg
    })

    pond = Pond(
        id=pond_id,
        name=pond_in.name,
        species=pond_in.species,
        fish_count=pond_in.fish_count,
        avg_weight_g=pond_in.avg_weight_g,
        feeding_rate_pct=pond_in.feeding_rate_pct,
        feed_price_per_kg=pond_in.feed_price_per_kg,
        shape=pond_in.shape,
        length_m=pond_in.length_m,
        width_m=pond_in.width_m,
        diameter_m=pond_in.diameter_m,
        surface_area_m2=pond_in.surface_area_m2,
        depth_m=pond_in.depth_m,
        volume_m3=vol_res.volume_m3,
        volume_litres=vol_res.volume_litres,
        biomass_kg=feed_res.biomass_kg,
        daily_feed_kg=feed_res.daily_feed_kg,
        daily_cost=feed_res.daily_cost,
        cost_30_days=feed_res.cost_30_days,
        status="Optimal",
        is_demo=pond_in.is_demo
    )
    db.add(pond)

    # Initialize default thresholds for this pond
    threshold = SensorThreshold(
        pond_id=pond_id,
        min_temp=24.0,
        max_temp=32.0,
        min_ph=6.5,
        max_ph=8.5,
        min_do=5.0,
        max_ammonia=0.05,
        min_salinity=0.0 if "shrimp" not in pond_in.species.lower() else 10.0,
        max_salinity=35.0
    )
    db.add(threshold)
    db.commit()
    db.refresh(pond)
    return pond

def update_pond(db: Session, pond_id: str, pond_in: PondUpdate) -> Pond:
    pond = get_pond_by_id(db, pond_id)
    if not pond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pond '{pond_id}' not found.")

    if pond_in.name and pond_in.name.strip().lower() != pond.name.lower():
        existing = db.query(Pond).filter(Pond.name.ilike(pond_in.name.strip())).first()
        if existing and existing.id != pond_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A pond with name '{pond_in.name}' already exists."
            )
        pond.name = pond_in.name.strip()

    if pond_in.species is not None:
        pond.species = pond_in.species
    if pond_in.fish_count is not None:
        pond.fish_count = pond_in.fish_count
    if pond_in.avg_weight_g is not None:
        pond.avg_weight_g = pond_in.avg_weight_g
    if pond_in.feeding_rate_pct is not None:
        pond.feeding_rate_pct = pond_in.feeding_rate_pct
    if pond_in.feed_price_per_kg is not None:
        pond.feed_price_per_kg = pond_in.feed_price_per_kg
    if pond_in.shape is not None:
        pond.shape = pond_in.shape
    if pond_in.length_m is not None:
        pond.length_m = pond_in.length_m
    if pond_in.width_m is not None:
        pond.width_m = pond_in.width_m
    if pond_in.diameter_m is not None:
        pond.diameter_m = pond_in.diameter_m
    if pond_in.surface_area_m2 is not None:
        pond.surface_area_m2 = pond_in.surface_area_m2
    if pond_in.depth_m is not None:
        pond.depth_m = pond_in.depth_m
    if pond_in.status is not None:
        pond.status = pond_in.status

    # Recalculate volume
    vol_res = calculate_pond_volume({
        "shape": pond.shape,
        "length_m": pond.length_m,
        "width_m": pond.width_m,
        "diameter_m": pond.diameter_m,
        "surface_area_m2": pond.surface_area_m2,
        "depth_m": pond.depth_m
    })
    pond.volume_m3 = vol_res.volume_m3
    pond.volume_litres = vol_res.volume_litres

    # Recalculate biomass & feed
    feed_res = calculate_feeding({
        "fish_count": pond.fish_count,
        "avg_weight_g": pond.avg_weight_g,
        "feeding_rate_pct": pond.feeding_rate_pct,
        "feed_price_per_kg": pond.feed_price_per_kg
    })
    pond.biomass_kg = feed_res.biomass_kg
    pond.daily_feed_kg = feed_res.daily_feed_kg
    pond.daily_cost = feed_res.daily_cost
    pond.cost_30_days = feed_res.cost_30_days

    db.commit()
    db.refresh(pond)
    return pond

def delete_pond(db: Session, pond_id: str) -> bool:
    pond = get_pond_by_id(db, pond_id)
    if not pond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pond '{pond_id}' not found.")
    db.delete(pond)
    db.commit()
    return True
