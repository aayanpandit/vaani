from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.agent import VaaniAgent
from app.database.dependencies import get_db
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import create_appointment
from app.schemas.chat import ChatRequest

router = APIRouter()

agent = VaaniAgent()


@router.get("/health")
def health():
    return {"status": "healthy"}


@router.post("/appointments")
def create_new_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
):
    return create_appointment(db, appointment)


@router.post("/chat")
def chat(request: ChatRequest):
    return agent.process(request.message)