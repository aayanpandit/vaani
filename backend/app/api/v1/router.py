from app.memory.session_memory import get_session, update_session, clear_session
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

    session = get_session(request.session_id)

    update_data = {
        "intent": agent_response["intent"] if agent_response["intent"] != "unknown" else session.get("intent"),
        "date": agent_response["entities"].get("date"),
        "time": agent_response["entities"].get("time"),
        "customer_name": request.customer_name,
        "phone_number": request.phone_number,
    }

    session = update_session(request.session_id, update_data)

    if session.get("intent") == "book_appointment":
        missing_fields = []

        if not session["date"]:
            missing_fields.append("date")

        if not session["time"]:
            missing_fields.append("time")

        if not session["customer_name"]:
            missing_fields.append("customer_name")

        if not session["phone_number"]:
            missing_fields.append("phone_number")

        if missing_fields:
            return {
                "status": "needs_information",
                "missing_fields": missing_fields,
                "message": f"Please provide: {', '.join(missing_fields)}",
                "session": session,
            }

        appointment = AppointmentCreate(
            customer_name=session["customer_name"],
            phone_number=session["phone_number"],
            appointment_time=f'{session["date"]} {session["time"]}',
        )

        created_appointment = create_appointment(db, appointment)

        clear_session(request.session_id)

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