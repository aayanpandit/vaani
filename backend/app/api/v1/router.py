from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.agent import VaaniAgent
from app.database.dependencies import get_db
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import create_appointment
from app.schemas.chat import ChatRequest
from app.schemas.appointment import AppointmentCreate

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
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    agent_response = agent.process(request.message)

    if agent_response["intent"] == "book_appointment":
        entities = agent_response["entities"]

        if request.customer_name and request.phone_number and "date" in entities and "time" in entities:
            appointment = AppointmentCreate(
                customer_name=request.customer_name,
                phone_number=request.phone_number,
                appointment_time=f'{entities["date"]} {entities["time"]}',
            )

            created_appointment = create_appointment(db, appointment)

            return {
                "status": "success",
                "message": "Appointment booked successfully",
                "appointment_id": created_appointment.id,
                "appointment": {
                    "customer_name": created_appointment.customer_name,
                    "phone_number": created_appointment.phone_number,
                    "appointment_time": created_appointment.appointment_time,
                    "status": created_appointment.status,
                },
            }

    return agent_response