import math
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator

# Configurable limits
MAX_FISH_COUNT = 10_000_000
MAX_AVG_WEIGHT_G = 100_000.0  # 100 kg
MAX_FEEDING_RATE_PCT = 15.0   # 15% body weight daily max biological limit
MAX_FEED_PRICE = 100_000.0
MAX_POND_DIMENSION_M = 10_000.0

class FeedingCalculationInput(BaseModel):
    fish_count: int = Field(..., ge=0, le=MAX_FISH_COUNT, description="Count of individual fish (integer >= 0)")
    avg_weight_g: float = Field(..., ge=0.0, le=MAX_AVG_WEIGHT_G, description="Average fish weight in grams")
    feeding_rate_pct: float = Field(..., ge=0.0, le=MAX_FEEDING_RATE_PCT, description="Daily feeding rate % of biomass")
    feed_price_per_kg: float = Field(..., ge=0.0, le=MAX_FEED_PRICE, description="Feed price per kg in currency (₹)")
    currency: str = Field(default="₹", description="Currency symbol")

    @field_validator("fish_count", mode="before")
    @classmethod
    def validate_fish_count_is_int(cls, v):
        if v is None:
            raise ValueError("Fish count is required.")
        if isinstance(v, float) and not v.is_integer():
            raise ValueError("Fish count represents individual fish and cannot be a decimal.")
        try:
            val = int(v)
            if val < 0:
                raise ValueError("Fish count cannot be negative.")
            return val
        except (TypeError, ValueError) as e:
            if "Fish count" in str(e):
                raise
            raise ValueError("Fish count must be a valid integer.")

    @field_validator("avg_weight_g", mode="before")
    @classmethod
    def validate_avg_weight(cls, v):
        if v is None:
            raise ValueError("Average weight is required.")
        try:
            val = float(v)
            if val < 0:
                raise ValueError("Average weight cannot be negative.")
            return val
        except (TypeError, ValueError) as e:
            if "Average weight" in str(e):
                raise
            raise ValueError("Average weight must be a valid number.")

    @field_validator("feeding_rate_pct", mode="before")
    @classmethod
    def validate_feeding_rate(cls, v):
        if v is None:
            raise ValueError("Feeding rate is required.")
        try:
            val = float(v)
            if val < 0:
                raise ValueError("Feeding rate cannot be negative.")
            if val > MAX_FEEDING_RATE_PCT:
                raise ValueError(f"Feeding rate cannot exceed maximum biological threshold of {MAX_FEEDING_RATE_PCT}%.")
            return val
        except (TypeError, ValueError) as e:
            if "Feeding rate" in str(e):
                raise
            raise ValueError("Feeding rate must be a valid number.")

    @field_validator("feed_price_per_kg", mode="before")
    @classmethod
    def validate_feed_price(cls, v):
        if v is None:
            raise ValueError("Feed price is required.")
        try:
            val = float(v)
            if val < 0:
                raise ValueError("Feed price cannot be negative.")
            return val
        except (TypeError, ValueError) as e:
            if "Feed price" in str(e):
                raise
            raise ValueError("Feed price must be a valid number.")

class FeedingCalculationResult(BaseModel):
    fish_count: int
    avg_weight_g: float
    feeding_rate_pct: float
    feed_price_per_kg: float
    currency: str
    
    # Exact full-precision internal numbers
    biomass_kg: float
    daily_feed_kg: float
    daily_cost: float
    cost_30_days: float
    
    # Formatted display strings
    display_biomass_kg: str
    display_daily_feed_kg: str
    display_daily_cost: str
    display_cost_30_days: str
    
    warnings: list[str] = []
    is_user_selected_estimate: bool = True
    disclaimer: str = "Feed rates are user-selected estimates. Biological consumption varies by dissolved oxygen and ambient temperature."

def calculate_feeding(inputs: Union[FeedingCalculationInput, dict]) -> FeedingCalculationResult:
    if isinstance(inputs, dict):
        validated = FeedingCalculationInput(**inputs)
    else:
        validated = inputs

    warnings = []
    if validated.fish_count == 0:
        warnings.append("Fish count is 0. Biomass and feeding requirements are zero.")
    if validated.avg_weight_g == 0:
        warnings.append("Average fish weight is 0g. Biomass is zero.")
    if validated.feed_price_per_kg == 0:
        warnings.append("Feed price is ₹0/kg. Calculated feeding cost will be zero.")
    if validated.feeding_rate_pct == 0:
        warnings.append("Feeding rate is 0%. Daily feed and cost are zero.")

    # Core mathematical formulas (preserving double precision)
    # Biomass (kg) = fish count × average weight in grams ÷ 1,000
    biomass_kg = (float(validated.fish_count) * float(validated.avg_weight_g)) / 1000.0

    # Daily feed (kg) = biomass × feeding rate percentage ÷ 100
    daily_feed_kg = (biomass_kg * float(validated.feeding_rate_pct)) / 100.0

    # Daily cost (₹) = daily feed × feed price per kg
    daily_cost = daily_feed_kg * float(validated.feed_price_per_kg)

    # 30-day estimate (₹) = daily cost × 30
    cost_30_days = daily_cost * 30.0

    # Formatting helper: show adequate precision for micro-quantities while rounding nicely for normal values
    def fmt_qty(val: float, unit: str = "") -> str:
        if val == 0:
            return f"0.00 {unit}".strip()
        if val < 0.01:
            return f"{val:.5f} {unit}".strip()
        return f"{val:,.2f} {unit}".strip()

    def fmt_currency(val: float, curr: str) -> str:
        if val == 0:
            return f"{curr}0.00"
        if val < 0.01:
            return f"{curr}{val:.4f}"
        return f"{curr}{val:,.2f}"

    return FeedingCalculationResult(
        fish_count=validated.fish_count,
        avg_weight_g=validated.avg_weight_g,
        feeding_rate_pct=validated.feeding_rate_pct,
        feed_price_per_kg=validated.feed_price_per_kg,
        currency=validated.currency,
        biomass_kg=biomass_kg,
        daily_feed_kg=daily_feed_kg,
        daily_cost=daily_cost,
        cost_30_days=cost_30_days,
        display_biomass_kg=fmt_qty(biomass_kg, "kg"),
        display_daily_feed_kg=fmt_qty(daily_feed_kg, "kg/day"),
        display_daily_cost=fmt_currency(daily_cost, validated.currency),
        display_cost_30_days=fmt_currency(cost_30_days, validated.currency),
        warnings=warnings,
        is_user_selected_estimate=True
    )


class PondVolumeInput(BaseModel):
    shape: str = Field(..., description="Pond shape: 'rectangular', 'circular', or 'irregular'")
    length_m: Optional[float] = Field(None, ge=0.0, le=MAX_POND_DIMENSION_M, description="Length in meters (rectangular)")
    width_m: Optional[float] = Field(None, ge=0.0, le=MAX_POND_DIMENSION_M, description="Width in meters (rectangular)")
    diameter_m: Optional[float] = Field(None, ge=0.0, le=MAX_POND_DIMENSION_M, description="Diameter in meters (circular)")
    surface_area_m2: Optional[float] = Field(None, ge=0.0, description="Surface area in m² (irregular)")
    depth_m: float = Field(..., ge=0.0, le=100.0, description="Average depth in meters")
    unit_system: str = Field(default="metric", description="Unit system: 'metric' (meters/litres) or 'imperial' (feet/gallons)")

    @model_validator(mode="before")
    @classmethod
    def validate_shape_dimensions(cls, data: Any):
        if not isinstance(data, dict):
            return data
        shape = data.get("shape", "").lower().strip()
        data["shape"] = shape
        if shape not in ["rectangular", "circular", "irregular"]:
            raise ValueError(f"Unsupported pond shape '{shape}'. Supported shapes: 'rectangular', 'circular', 'irregular'.")

        depth = data.get("depth_m")
        if depth is None:
            raise ValueError("Pond depth is required.")
        if float(depth) < 0:
            raise ValueError("Pond depth cannot be negative.")

        if shape == "rectangular":
            length = data.get("length_m")
            width = data.get("width_m")
            if length is None or width is None:
                raise ValueError("Rectangular pond requires length and width dimensions.")
            if float(length) < 0 or float(width) < 0:
                raise ValueError("Pond dimensions cannot be negative.")

        elif shape == "circular":
            diameter = data.get("diameter_m")
            if diameter is None:
                raise ValueError("Circular pond requires diameter dimension.")
            if float(diameter) < 0:
                raise ValueError("Diameter cannot be negative.")

        elif shape == "irregular":
            area = data.get("surface_area_m2")
            if area is None:
                raise ValueError("Irregular pond requires surface area dimension.")
            if float(area) < 0:
                raise ValueError("Surface area cannot be negative.")

        return data

class PondVolumeResult(BaseModel):
    shape: str
    volume_m3: float
    volume_litres: float
    volume_gallons: float
    depth_m: float
    warnings: list[str] = []
    display_volume_m3: str
    display_volume_litres: str
    display_volume_gallons: str

def calculate_pond_volume(inputs: Union[PondVolumeInput, dict]) -> PondVolumeResult:
    if isinstance(inputs, dict):
        validated = PondVolumeInput(**inputs)
    else:
        validated = inputs

    shape = validated.shape.lower().strip()
    depth = float(validated.depth_m)
    warnings = []

    if depth == 0:
        warnings.append("Pond depth is 0m. Water volume is 0.")

    volume_m3: float = 0.0

    if shape == "rectangular":
        l = float(validated.length_m or 0)
        w = float(validated.width_m or 0)
        volume_m3 = l * w * depth

    elif shape == "circular":
        d = float(validated.diameter_m or 0)
        r = d / 2.0
        volume_m3 = math.pi * (r ** 2) * depth

    elif shape == "irregular":
        area = float(validated.surface_area_m2 or 0)
        volume_m3 = area * depth

    volume_litres = volume_m3 * 1000.0
    volume_gallons = volume_litres * 0.264172052

    return PondVolumeResult(
        shape=shape,
        volume_m3=volume_m3,
        volume_litres=volume_litres,
        volume_gallons=volume_gallons,
        depth_m=depth,
        warnings=warnings,
        display_volume_m3=f"{volume_m3:,.3f} m³",
        display_volume_litres=f"{round(volume_litres):,} L",
        display_volume_gallons=f"{round(volume_gallons):,} gal"
    )
