import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.models.database import Base

class Pond(Base):
    __tablename__ = "ponds"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    species = Column(String, default="Nile Tilapia")
    fish_count = Column(Integer, default=0)
    avg_weight_g = Column(Float, default=0.0)
    feeding_rate_pct = Column(Float, default=2.5)
    feed_price_per_kg = Column(Float, default=68.0)
    
    # Dimensions & Volume
    shape = Column(String, default="rectangular")
    length_m = Column(Float, nullable=True)
    width_m = Column(Float, nullable=True)
    diameter_m = Column(Float, nullable=True)
    surface_area_m2 = Column(Float, nullable=True)
    depth_m = Column(Float, default=1.5)
    volume_m3 = Column(Float, default=0.0)
    volume_litres = Column(Float, default=0.0)
    
    # Calculated Biomass & Feeding values
    biomass_kg = Column(Float, default=0.0)
    daily_feed_kg = Column(Float, default=0.0)
    daily_cost = Column(Float, default=0.0)
    cost_30_days = Column(Float, default=0.0)
    
    status = Column(String, default="Optimal")  # Optimal, Caution, Critical
    is_demo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    feed_estimates = relationship("FeedEstimate", back_populates="pond", cascade="all, delete-orphan")
    water_readings = relationship("WaterReading", back_populates="pond", cascade="all, delete-orphan")
    alerts = relationship("AlertRecord", back_populates="pond", cascade="all, delete-orphan")
    thresholds = relationship("SensorThreshold", back_populates="pond", uselist=False, cascade="all, delete-orphan")


class FeedEstimate(Base):
    __tablename__ = "feed_estimates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pond_id = Column(String, ForeignKey("ponds.id", ondelete="CASCADE"), nullable=False)
    fish_count = Column(Integer, nullable=False)
    avg_weight_g = Column(Float, nullable=False)
    feeding_rate_pct = Column(Float, nullable=False)
    feed_price_per_kg = Column(Float, nullable=False)
    biomass_kg = Column(Float, nullable=False)
    daily_feed_kg = Column(Float, nullable=False)
    daily_cost = Column(Float, nullable=False)
    cost_30_days = Column(Float, nullable=False)
    notes = Column(String, nullable=True)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

    pond = relationship("Pond", back_populates="feed_estimates")


class WaterReading(Base):
    __tablename__ = "water_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pond_id = Column(String, ForeignKey("ponds.id", ondelete="CASCADE"), nullable=False)
    temperature_c = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    dissolved_oxygen_mg_l = Column(Float, nullable=True)
    salinity_ppt = Column(Float, nullable=True)
    ammonia_mg_l = Column(Float, nullable=True)
    source = Column(String, default="simulated")  # live, simulated, demo, manual
    status = Column(String, default="optimal")   # optimal, caution, critical
    is_stale = Column(Boolean, default=False)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

    pond = relationship("Pond", back_populates="water_readings")


class AlertRecord(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pond_id = Column(String, ForeignKey("ponds.id", ondelete="CASCADE"), nullable=False)
    parameter = Column(String, nullable=False)  # "Dissolved Oxygen", "pH", etc.
    severity = Column(String, default="warning") # critical, warning, info
    message = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    is_acknowledged = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    pond = relationship("Pond", back_populates="alerts")


class FishDetection(Base):
    __tablename__ = "fish_detections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pond_id = Column(String, ForeignKey("ponds.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    annotated_url = Column(String, nullable=False)
    detected_count = Column(Integer, nullable=False)
    confirmed_count = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=False)
    bounding_boxes_json = Column(Text, default="[]")
    is_held_out_eval = Column(Boolean, default=False)
    status = Column(String, default="detected")  # detected, confirmed, rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SensorThreshold(Base):
    __tablename__ = "sensor_thresholds"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pond_id = Column(String, ForeignKey("ponds.id", ondelete="CASCADE"), unique=True, nullable=False)
    min_temp = Column(Float, default=24.0)
    max_temp = Column(Float, default=32.0)
    min_ph = Column(Float, default=6.5)
    max_ph = Column(Float, default=8.5)
    min_do = Column(Float, default=5.0)   # Dissolved Oxygen min safe (mg/L)
    max_ammonia = Column(Float, default=0.05) # Ammonia max safe (mg/L)
    min_salinity = Column(Float, default=0.0)
    max_salinity = Column(Float, default=35.0)

    pond = relationship("Pond", back_populates="thresholds")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="operator")  # admin, supervisor, operator
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
