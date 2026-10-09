import os
import datetime
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import engine, Base, get_db
from app.seed import seed_database
from app.api.endpoints_ponds import router as ponds_router
from app.api.endpoints_calculator import router as calc_router
from app.api.endpoints_sensors import router as sensors_router
from app.api.endpoints_ai import router as ai_router
from app.api.endpoints_reports import router as reports_router
from app.api.endpoints_alerts import router as alerts_router
from app.api.endpoints_auth import router as auth_router

# Create SQLite tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AquaSmart AI — Precision Aquaculture Feeding & Water Telemetry Backend"
)

# CORS Middleware (Phase 08 - Security & Connectivity)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local Vite dev and staging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Uploads directory for fish images & annotated bounding boxes
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(ponds_router, prefix=settings.API_V1_STR)
app.include_router(calc_router, prefix=settings.API_V1_STR)
app.include_router(sensors_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)

# Health & Readiness checks (Phase 10 - Monitoring)
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AquaSmart AI Core Engine",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "database": "sqlite/persistent",
        "version": "1.0.0"
    }

@app.get("/api/ready")
def readiness_check(db: Session = Depends(get_db)):
    from app.models.entities import Pond
    count = db.query(Pond).count()
    return {
        "status": "ready",
        "ponds_loaded": count,
        "database_connected": True
    }

@app.post("/api/reset-demo-data")
def reset_demo_data(db: Session = Depends(get_db)):
    """
    UI-06: Reset demo data button restores original canonical demo values.
    """
    from app.models.entities import Pond, FeedEstimate, WaterReading, AlertRecord, SensorThreshold, User
    db.query(AlertRecord).delete()
    db.query(WaterReading).delete()
    db.query(FeedEstimate).delete()
    db.query(SensorThreshold).delete()
    db.query(Pond).delete()
    db.query(User).delete()
    db.commit()
    seed_database(db)
    return {"status": "success", "message": "Demo data reset to initial baseline."}

# Auto seed on start
with next(get_db()) as db_session:
    seed_database(db_session)
