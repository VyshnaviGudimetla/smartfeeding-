from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import PondResponse, PondCreate, PondUpdate
from app.services import pond_service

router = APIRouter(prefix="/ponds", tags=["Ponds"])

@router.get("", response_model=List[PondResponse])
def list_ponds(
    search: Optional[str] = Query(None, description="Search ponds by name, id, or species"),
    species: Optional[str] = Query(None, description="Filter by fish species"),
    db: Session = Depends(get_db)
):
    return pond_service.get_ponds(db, search=search, species=species)

@router.get("/{pond_id}", response_model=PondResponse)
def get_pond(pond_id: str, db: Session = Depends(get_db)):
    pond = pond_service.get_pond_by_id(db, pond_id)
    if not pond:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Pond '{pond_id}' not found.")
    return pond

@router.post("", response_model=PondResponse, status_code=status.HTTP_201_CREATED)
def create_pond(pond_in: PondCreate, db: Session = Depends(get_db)):
    return pond_service.create_pond(db, pond_in)

@router.put("/{pond_id}", response_model=PondResponse)
def update_pond(pond_id: str, pond_in: PondUpdate, db: Session = Depends(get_db)):
    return pond_service.update_pond(db, pond_id, pond_in)

@router.delete("/{pond_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pond(pond_id: str, db: Session = Depends(get_db)):
    pond_service.delete_pond(db, pond_id)
    return None
