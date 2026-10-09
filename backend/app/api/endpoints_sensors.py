from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.entities import WaterReading, SensorThreshold, Pond
from app.models.schemas import (
    WaterReadingCreate,
    WaterReadingResponse,
    SensorCalibrationRequest,
    SensorCalibrationResponse,
    SensorThresholdResponse,
    SensorThresholdUpdate
)
from app.services import sensor_service

router = APIRouter(prefix="/sensors", tags=["Sensors & Water Quality"])

@router.get("/latest", response_model=List[WaterReadingResponse])
def get_latest_readings_all_ponds(db: Session = Depends(get_db)):
    """
    Returns latest water reading for every pond, marking stale readings (>15 mins without update).
    """
    ponds = db.query(Pond).all()
    results = []
    for pond in ponds:
        latest = db.query(WaterReading).filter(WaterReading.pond_id == pond.id).order_by(WaterReading.recorded_at.desc()).first()
        if latest:
            latest.is_stale = sensor_service.check_reading_staleness(latest.recorded_at)
            results.append(latest)
    return results

@router.get("/readings/{pond_id}", response_model=List[WaterReadingResponse])
def get_pond_readings(pond_id: str, limit: int = 20, db: Session = Depends(get_db)):
    readings = db.query(WaterReading).filter(WaterReading.pond_id == pond_id).order_by(WaterReading.recorded_at.desc()).limit(limit).all()
    for r in readings:
        r.is_stale = sensor_service.check_reading_staleness(r.recorded_at)
    return readings

@router.post("/readings", response_model=WaterReadingResponse, status_code=status.HTTP_201_CREATED)
def record_sensor_telemetry(reading_in: WaterReadingCreate, db: Session = Depends(get_db)):
    """
    Ingest live hardware reading or telemetry packet (WQ-01..14)
    """
    return sensor_service.process_water_reading(db, reading_in)

@router.post("/calibrate", response_model=SensorCalibrationResponse)
def calibrate_probe(req: SensorCalibrationRequest):
    """
    Calibrate pH, DO or Temperature sensor probe against certified laboratory standard buffer (WQ-12)
    """
    return sensor_service.calibrate_sensor(req)

@router.get("/thresholds/{pond_id}", response_model=SensorThresholdResponse)
def get_pond_thresholds(pond_id: str, db: Session = Depends(get_db)):
    t = db.query(SensorThreshold).filter(SensorThreshold.pond_id == pond_id).first()
    if not t:
        # Create default
        t = SensorThreshold(pond_id=pond_id)
        db.add(t)
        db.commit()
        db.refresh(t)
    return t

@router.put("/thresholds/{pond_id}", response_model=SensorThresholdResponse)
def update_pond_thresholds(pond_id: str, update_in: SensorThresholdUpdate, db: Session = Depends(get_db)):
    t = db.query(SensorThreshold).filter(SensorThreshold.pond_id == pond_id).first()
    if not t:
        t = SensorThreshold(pond_id=pond_id)
        db.add(t)

    for field, val in update_in.model_dump(exclude_unset=True).items():
        setattr(t, field, val)

    db.commit()
    db.refresh(t)
    return t

@router.post("/simulate", status_code=status.HTTP_200_OK)
def trigger_telemetry_simulation(db: Session = Depends(get_db)):
    """
    Generate dynamic biophysical drift simulation for all active ponds (FR-08)
    """
    sensor_service.generate_simulated_readings_for_all(db)
    return {"status": "success", "message": "Simulation tick generated for all ponds."}
