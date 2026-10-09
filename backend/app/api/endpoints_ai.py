import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.entities import FishDetection
from app.models.schemas import (
    FishDetectionResponse,
    FishConfirmCountRequest,
    FishBoundingBox
)
from app.services import ai_vision

router = APIRouter(prefix="/ai", tags=["AI Fish Counting"])

@router.post("/detect", response_model=FishDetectionResponse)
async def upload_and_detect_fish(
    file: UploadFile = File(...),
    pond_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    POST /ai/detect — Real computer vision fish detection pipeline (AI-01..14)
    Returns detected visible count, confidence metrics, and annotated bounding boxes.
    """
    return ai_vision.analyze_fish_image(db, file, pond_id=pond_id)

@router.post("/confirm/{detection_id}", response_model=FishDetectionResponse)
def confirm_and_apply_count(
    detection_id: int,
    req: FishConfirmCountRequest,
    db: Session = Depends(get_db)
):
    """
    AI-09: User manual correction & confirmation. Updates pond fish count if requested.
    """
    return ai_vision.confirm_fish_count(
        db,
        detection_id=detection_id,
        confirmed_count=req.confirmed_count,
        apply_to_pond_id=req.apply_to_pond_id
    )

@router.get("/evaluation", status_code=status.HTTP_200_OK)
def get_held_out_evaluation_metrics():
    """
    AI-11 & AI-12: Precision, recall, and counting error on held-out dataset + limitations notice.
    """
    return ai_vision.evaluate_held_out_dataset()

@router.get("/history", response_model=List[FishDetectionResponse])
def get_detection_history(limit: int = 20, db: Session = Depends(get_db)):
    detections = db.query(FishDetection).order_by(FishDetection.created_at.desc()).limit(limit).all()
    results = []
    for d in detections:
        boxes = json.loads(d.bounding_boxes_json or "[]")
        results.append(FishDetectionResponse(
            id=d.id,
            pond_id=d.pond_id,
            filename=d.filename,
            image_url=d.image_url,
            annotated_url=d.annotated_url,
            detected_count=d.detected_count,
            confirmed_count=d.confirmed_count,
            confidence_score=d.confidence_score,
            bounding_boxes=[FishBoundingBox(**b) for b in boxes],
            status=d.status,
            created_at=d.created_at
        ))
    return results
