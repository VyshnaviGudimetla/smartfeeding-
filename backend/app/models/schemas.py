import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

# ----------------- Pond Schemas -----------------
class PondBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    species: str = Field(default="Nile Tilapia")
    fish_count: int = Field(default=0, ge=0, le=10_000_000)
    avg_weight_g: float = Field(default=0.0, ge=0.0, le=100_000.0)
    feeding_rate_pct: float = Field(default=2.5, ge=0.0, le=15.0)
    feed_price_per_kg: float = Field(default=68.0, ge=0.0, le=100_000.0)
    shape: str = Field(default="rectangular")
    length_m: Optional[float] = Field(None, ge=0.0, le=10_000.0)
    width_m: Optional[float] = Field(None, ge=0.0, le=10_000.0)
    diameter_m: Optional[float] = Field(None, ge=0.0, le=10_000.0)
    surface_area_m2: Optional[float] = Field(None, ge=0.0)
    depth_m: float = Field(default=1.5, ge=0.0, le=100.0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Pond name cannot be empty.")
        return v.strip()

    @field_validator("fish_count", mode="before")
    @classmethod
    def validate_fish_count(cls, v):
        if v is None:
            raise ValueError("Fish count is required.")
        if isinstance(v, float) and not v.is_integer():
            raise ValueError("Fish count represents individual fish and cannot be a decimal.")
        try:
            val = int(v)
            if val < 0:
                raise ValueError("Fish count cannot be negative.")
            return val
        except (ValueError, TypeError) as e:
            if "Fish count" in str(e):
                raise
            raise ValueError("Fish count must be an integer.")

    @field_validator("avg_weight_g", mode="before")
    @classmethod
    def validate_avg_weight(cls, v):
        try:
            val = float(v)
            if val < 0:
                raise ValueError("Average weight cannot be negative.")
            return val
        except (ValueError, TypeError) as e:
            if "Average weight" in str(e):
                raise
            raise ValueError("Average weight must be a valid number.")

    @field_validator("feed_price_per_kg", mode="before")
    @classmethod
    def validate_feed_price(cls, v):
        try:
            val = float(v)
            if val < 0:
                raise ValueError("Feed price cannot be negative.")
            return val
        except (ValueError, TypeError) as e:
            if "Feed price" in str(e):
                raise
            raise ValueError("Feed price must be a valid number.")

class PondCreate(PondBase):
    id: Optional[str] = None
    is_demo: bool = True

class PondUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    fish_count: Optional[int] = None
    avg_weight_g: Optional[float] = None
    feeding_rate_pct: Optional[float] = None
    feed_price_per_kg: Optional[float] = None
    shape: Optional[str] = None
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    diameter_m: Optional[float] = None
    surface_area_m2: Optional[float] = None
    depth_m: Optional[float] = None
    status: Optional[str] = None

class PondResponse(PondBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    volume_m3: float
    volume_litres: float
    biomass_kg: float
    daily_feed_kg: float
    daily_cost: float
    cost_30_days: float
    status: str
    is_demo: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


# ----------------- Feed Estimate Schemas -----------------
class FeedEstimateCreate(BaseModel):
    pond_id: str
    fish_count: int = Field(..., ge=0)
    avg_weight_g: float = Field(..., ge=0.0)
    feeding_rate_pct: float = Field(..., ge=0.0, le=15.0)
    feed_price_per_kg: float = Field(..., ge=0.0)
    notes: Optional[str] = None

class FeedEstimateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pond_id: str
    fish_count: int
    avg_weight_g: float
    feeding_rate_pct: float
    feed_price_per_kg: float
    biomass_kg: float
    daily_feed_kg: float
    daily_cost: float
    cost_30_days: float
    notes: Optional[str] = None
    recorded_at: datetime.datetime


# ----------------- Water Reading Schemas -----------------
class WaterReadingCreate(BaseModel):
    pond_id: str
    temperature_c: Optional[float] = Field(None, ge=-10.0, le=60.0, description="Valid water temp: -10 to 60°C")
    ph: Optional[float] = Field(None, ge=0.0, le=14.0, description="Valid pH range: 0 to 14")
    dissolved_oxygen_mg_l: Optional[float] = Field(None, ge=0.0, le=25.0, description="Valid DO range: 0 to 25 mg/L")
    salinity_ppt: Optional[float] = Field(None, ge=0.0, le=100.0, description="Valid salinity: 0 to 100 ppt")
    ammonia_mg_l: Optional[float] = Field(None, ge=0.0, le=10.0, description="Valid ammonia: 0 to 10 mg/L")
    source: str = Field(default="live")

class WaterReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pond_id: str
    temperature_c: Optional[float]
    ph: Optional[float]
    dissolved_oxygen_mg_l: Optional[float]
    salinity_ppt: Optional[float]
    ammonia_mg_l: Optional[float]
    source: str
    status: str
    is_stale: bool
    recorded_at: datetime.datetime


# ----------------- Sensor Calibration Schemas -----------------
class SensorCalibrationRequest(BaseModel):
    sensor_type: str = Field(..., description="e.g. 'ph', 'dissolved_oxygen', 'temperature'")
    reference_value: float = Field(..., description="Certified standard buffer or reference reading")
    measured_raw_value: float = Field(..., description="Raw instrument measurement")
    notes: Optional[str] = None

class SensorCalibrationResponse(BaseModel):
    sensor_type: str
    offset_applied: float
    calibrated_value: float
    reference_value: float
    tolerance_pct: float
    status: str
    message: str


# ----------------- Alert Schemas -----------------
class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pond_id: str
    parameter: str
    severity: str
    message: str
    value: float
    threshold: float
    is_acknowledged: bool
    is_resolved: bool
    triggered_at: datetime.datetime
    resolved_at: Optional[datetime.datetime] = None

class AlertUpdate(BaseModel):
    is_acknowledged: Optional[bool] = None
    is_resolved: Optional[bool] = None


# ----------------- Threshold Schemas -----------------
class SensorThresholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pond_id: str
    min_temp: float
    max_temp: float
    min_ph: float
    max_ph: float
    min_do: float
    max_ammonia: float
    min_salinity: float
    max_salinity: float

class SensorThresholdUpdate(BaseModel):
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    min_ph: Optional[float] = None
    max_ph: Optional[float] = None
    min_do: Optional[float] = None
    max_ammonia: Optional[float] = None
    min_salinity: Optional[float] = None
    max_salinity: Optional[float] = None


# ----------------- AI Vision Schemas -----------------
class FishBoundingBox(BaseModel):
    id: int
    x: int
    y: int
    width: int
    height: int
    confidence: float
    label: str = "fish"

class FishDetectionResponse(BaseModel):
    id: int
    pond_id: Optional[str] = None
    filename: str
    image_url: str
    annotated_url: str
    detected_count: int
    confirmed_count: Optional[int] = None
    confidence_score: float
    bounding_boxes: List[FishBoundingBox] = []
    status: str
    created_at: datetime.datetime
    disclaimer: str = "Detected count represents visible fish in the surface/frame, not total pond population. Calibrated density estimation required for complete pond census."

class FishConfirmCountRequest(BaseModel):
    confirmed_count: int = Field(..., ge=0)
    apply_to_pond_id: Optional[str] = None
    notes: Optional[str] = None


# ----------------- User & Auth Schemas -----------------
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6)
    role: str = Field(default="operator")

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ----------------- Dashboard Summary -----------------
class DashboardSummary(BaseModel):
    active_ponds_count: int
    total_biomass_kg: float
    daily_feed_kg: float
    daily_cost: float
    monthly_cost_estimate: float
    optimal_ponds: int
    caution_ponds: int
    critical_ponds: int
    active_alerts_count: int
    backend_status: str = "connected"
    demo_mode: bool = True
    server_time: datetime.datetime
