from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import create_appointment

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "healthy"}


@router.post("/appointments")
def create_new_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
):
    return create_appointment(db, appointment)