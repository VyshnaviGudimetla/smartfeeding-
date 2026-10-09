import datetime
import random
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.entities import WaterReading, AlertRecord, SensorThreshold, Pond
from app.models.schemas import WaterReadingCreate, SensorCalibrationRequest, SensorCalibrationResponse
from app.core.config import settings

# Physical validity boundaries
VALID_RANGES = {
    "temperature_c": (-10.0, 60.0),
    "ph": (0.0, 14.0),
    "dissolved_oxygen_mg_l": (0.0, 25.0),
    "salinity_ppt": (0.0, 100.0),
    "ammonia_mg_l": (0.0, 10.0)
}

# In-memory calibration calibration offsets
CALIBRATION_OFFSETS: Dict[str, float] = {
    "ph": 0.0,
    "dissolved_oxygen": 0.0,
    "temperature": 0.0
}

def validate_sensor_reading(data: Dict[str, Any]):
    for field, (low, high) in VALID_RANGES.items():
        val = data.get(field)
        if val is not None:
            if not isinstance(val, (int, float)):
                raise ValueError(f"Value for {field} must be a numeric reading, received: {val}")
            if val < low or val > high:
                raise ValueError(f"Value for {field} ({val}) is outside physical sensor limits [{low}, {high}].")

def check_reading_staleness(recorded_at: datetime.datetime) -> bool:
    if not recorded_at:
        return True
    now = datetime.datetime.utcnow()
    diff = (now - recorded_at).total_seconds() / 60.0
    return diff > settings.STALE_DATA_TIMEOUT_MINUTES

def process_water_reading(db: Session, reading_in: WaterReadingCreate) -> WaterReading:
    # Validate physical ranges (WQ-04)
    dump = reading_in.model_dump()
    validate_sensor_reading(dump)

    pond = db.query(Pond).filter(Pond.id == reading_in.pond_id).first()
    if not pond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pond '{reading_in.pond_id}' not found.")

    # Apply calibration offsets if applicable
    ph_val = reading_in.ph
    if ph_val is not None and "ph" in CALIBRATION_OFFSETS:
        ph_val = round(ph_val + CALIBRATION_OFFSETS["ph"], 2)

    do_val = reading_in.dissolved_oxygen_mg_l
    if do_val is not None and "dissolved_oxygen" in CALIBRATION_OFFSETS:
        do_val = round(do_val + CALIBRATION_OFFSETS["dissolved_oxygen"], 2)

    temp_val = reading_in.temperature_c
    if temp_val is not None and "temperature" in CALIBRATION_OFFSETS:
        temp_val = round(temp_val + CALIBRATION_OFFSETS["temperature"], 2)

    # Determine status and trigger threshold alerts
    threshold = db.query(SensorThreshold).filter(SensorThreshold.pond_id == reading_in.pond_id).first()
    reading_status = "optimal"
    alerts_to_create = []

    if threshold:
        # Check Dissolved Oxygen (Critical biological parameter)
        if do_val is not None:
            if do_val < 3.0:
                reading_status = "critical"
                alerts_to_create.append({
                    "parameter": "Dissolved Oxygen",
                    "severity": "critical",
                    "message": f"HYPOXIA DANGER: DO level dropped to {do_val} mg/L (Minimum threshold: {threshold.min_do} mg/L). Turn on emergency aerator!",
                    "value": do_val,
                    "threshold": threshold.min_do
                })
            elif do_val < threshold.min_do:
                if reading_status != "critical":
                    reading_status = "caution"
                alerts_to_create.append({
                    "parameter": "Dissolved Oxygen",
                    "severity": "warning",
                    "message": f"Low Dissolved Oxygen: {do_val} mg/L (Below configured target {threshold.min_do} mg/L).",
                    "value": do_val,
                    "threshold": threshold.min_do
                })

        # Check pH
        if ph_val is not None:
            if ph_val < threshold.min_ph or ph_val > threshold.max_ph:
                if reading_status != "critical":
                    reading_status = "caution"
                alerts_to_create.append({
                    "parameter": "pH",
                    "severity": "warning",
                    "message": f"pH drift: {ph_val} (Safe boundary: {threshold.min_ph} - {threshold.max_ph}).",
                    "value": ph_val,
                    "threshold": threshold.min_ph if ph_val < threshold.min_ph else threshold.max_ph
                })

        # Check Temperature
        if temp_val is not None:
            if temp_val < threshold.min_temp or temp_val > threshold.max_temp:
                if reading_status != "critical":
                    reading_status = "caution"
                alerts_to_create.append({
                    "parameter": "Temperature",
                    "severity": "warning",
                    "message": f"Temperature anomaly: {temp_val}°C (Optimal: {threshold.min_temp}°C - {threshold.max_temp}°C).",
                    "value": temp_val,
                    "threshold": threshold.min_temp if temp_val < threshold.min_temp else threshold.max_temp
                })

        # Check Ammonia
        if reading_in.ammonia_mg_l is not None and reading_in.ammonia_mg_l > threshold.max_ammonia:
            reading_status = "critical"
            alerts_to_create.append({
                "parameter": "Ammonia",
                "severity": "critical",
                "message": f"Ammonia toxicity risk: {reading_in.ammonia_mg_l} mg/L exceeds safe cap {threshold.max_ammonia} mg/L.",
                "value": reading_in.ammonia_mg_l,
                "threshold": threshold.max_ammonia
            })

    # Save Reading
    reading = WaterReading(
        pond_id=reading_in.pond_id,
        temperature_c=temp_val,
        ph=ph_val,
        dissolved_oxygen_mg_l=do_val,
        salinity_ppt=reading_in.salinity_ppt,
        ammonia_mg_l=reading_in.ammonia_mg_l,
        source=reading_in.source,
        status=reading_status,
        is_stale=False,
        recorded_at=datetime.datetime.utcnow()
    )
    db.add(reading)
    pond.status = reading_status.capitalize()

    # Trigger alerts without duplicates if existing active alert is unacknowledged
    for alt in alerts_to_create:
        existing_alert = db.query(AlertRecord).filter(
            AlertRecord.pond_id == reading_in.pond_id,
            AlertRecord.parameter == alt["parameter"],
            AlertRecord.is_resolved == False
        ).first()
        if not existing_alert:
            db.add(AlertRecord(
                pond_id=reading_in.pond_id,
                parameter=alt["parameter"],
                severity=alt["severity"],
                message=alt["message"],
                value=alt["value"],
                threshold=alt["threshold"],
                is_acknowledged=False,
                is_resolved=False,
                triggered_at=datetime.datetime.utcnow()
            ))

    # If reading returned to normal, resolve active alerts for those parameters (WQ-09)
    if reading_status == "optimal":
        active_alerts = db.query(AlertRecord).filter(
            AlertRecord.pond_id == reading_in.pond_id,
            AlertRecord.is_resolved == False
        ).all()
        for a in active_alerts:
            a.is_resolved = True
            a.resolved_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(reading)
    return reading

def calibrate_sensor(req: SensorCalibrationRequest) -> SensorCalibrationResponse:
    # WQ-12: Compare sensor with reference instrument
    stype = req.sensor_type.lower().strip()
    if stype not in ["ph", "dissolved_oxygen", "temperature"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported sensor type '{req.sensor_type}'. Supported: 'ph', 'dissolved_oxygen', 'temperature'."
        )

    # Offset = Reference - Measured
    offset = req.reference_value - req.measured_raw_value
    CALIBRATION_OFFSETS[stype] = offset
    calibrated_val = req.measured_raw_value + offset
    
    # Calculate error tolerance percentage
    error_pct = (abs(offset) / req.reference_value * 100.0) if req.reference_value != 0 else 0.0

    return SensorCalibrationResponse(
        sensor_type=stype,
        offset_applied=round(offset, 4),
        calibrated_value=round(calibrated_val, 4),
        reference_value=req.reference_value,
        tolerance_pct=round(error_pct, 2),
        status="calibrated",
        message=f"Sensor '{stype}' successfully calibrated with offset {offset:+.4f} against standard buffer {req.reference_value}."
    )

def generate_simulated_readings_for_all(db: Session):
    ponds = db.query(Pond).all()
    for pond in ponds:
        # Generate biologically realistic fluctuations
        is_shrimp = "shrimp" in pond.species.lower()
        
        # In Pond 03 or critical pond scenario, simulate DO drop for demo
        if "03" in pond.id:
            do = round(random.uniform(2.4, 3.8), 2)  # Low DO scenario
            temp = round(random.uniform(28.5, 30.2), 1)
            ph = round(random.uniform(7.8, 8.2), 2)
            sal = 15.0 if is_shrimp else round(random.uniform(0.1, 0.4), 1)
            amm = round(random.uniform(0.04, 0.08), 3)
        else:
            do = round(random.uniform(5.5, 7.8), 2)  # Healthy DO
            temp = round(random.uniform(26.0, 29.0), 1)
            ph = round(random.uniform(7.2, 7.8), 2)
            sal = 18.0 if is_shrimp else round(random.uniform(0.1, 0.3), 1)
            amm = round(random.uniform(0.01, 0.03), 3)

        process_water_reading(db, WaterReadingCreate(
            pond_id=pond.id,
            temperature_c=temp,
            ph=ph,
            dissolved_oxygen_mg_l=do,
            salinity_ppt=sal,
            ammonia_mg_l=amm,
            source="simulated"
        ))
