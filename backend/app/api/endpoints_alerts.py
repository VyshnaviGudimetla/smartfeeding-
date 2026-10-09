import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.entities import AlertRecord
from app.models.schemas import AlertResponse, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    pond_id: Optional[str] = None,
    unresolved_only: bool = False,
    db: Session = Depends(get_db)
):
    q = db.query(AlertRecord)
    if pond_id and pond_id != "all":
        q = q.filter(AlertRecord.pond_id == pond_id)
    if unresolved_only:
        q = q.filter(AlertRecord.is_resolved == False)
    return q.order_by(AlertRecord.triggered_at.desc()).all()

@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found.")
    a.is_acknowledged = True
    db.commit()
    db.refresh(a)
    return a

@router.put("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found.")
    a.is_resolved = True
    a.resolved_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(a)
    return a
