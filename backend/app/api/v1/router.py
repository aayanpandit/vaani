from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.agent import VaaniAgent
from app.database.dependencies import get_db
from app.memory.session_memory import get_session, update_session, clear_session
from app.schemas.appointment import AppointmentCreate
from app.schemas.chat import ChatRequest

from app.services.appointment_service import (
    create_appointment,
    cancel_appointment,
    reschedule_appointment,
    get_appointment,
    update_calendar_event_id,
)

from app.integrations.google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    update_calendar_event,
)

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
    entities = agent_response["entities"]
    session = get_session(request.session_id)

    update_data = {
        "intent": agent_response["intent"]
        if agent_response["intent"] != "unknown"
        else session.get("intent"),

        "date": entities.get("date") or session.get("date"),
        "time": entities.get("time") or session.get("time"),
        "appointment_id": entities.get("appointment_id") or session.get("appointment_id"),

        # UPDATED: now supports name/phone from voice transcript too
        "customer_name": request.customer_name
        or entities.get("customer_name")
        or session.get("customer_name"),

        "phone_number": request.phone_number
        or entities.get("phone_number")
        or session.get("phone_number"),
    }

    session = update_session(request.session_id, update_data)

    # CANCEL APPOINTMENT
    if session.get("intent") == "cancel_appointment":
        appointment_id = session.get("appointment_id")

        if not appointment_id:
            return {
                "status": "needs_information",
                "missing_fields": ["appointment_id"],
                "message": "Please provide the appointment ID you want to cancel.",
                "session": session,
            }

        appointment = get_appointment(db, int(appointment_id))

        if not appointment:
            return {
                "status": "error",
                "message": f"No appointment found with ID {appointment_id}.",
            }

        if appointment.calendar_event_id:
            delete_calendar_event(appointment.calendar_event_id)

        cancelled_appointment = cancel_appointment(db, int(appointment_id))
        clear_session(request.session_id)

        return {
            "status": "success",
            "message": f"Appointment {appointment_id} has been cancelled.",
            "appointment_id": cancelled_appointment.id,
            "appointment": {
                "customer_name": cancelled_appointment.customer_name,
                "phone_number": cancelled_appointment.phone_number,
                "appointment_time": cancelled_appointment.appointment_time,
                "status": cancelled_appointment.status,
            },
        }

    # RESCHEDULE APPOINTMENT
    if session.get("intent") == "reschedule_appointment":
        appointment_id = session.get("appointment_id")
        date = session.get("date")
        time = session.get("time")

        missing_fields = []

        if not appointment_id:
            missing_fields.append("appointment_id")
        if not date:
            missing_fields.append("date")
        if not time:
            missing_fields.append("time")

        if missing_fields:
            return {
                "status": "needs_information",
                "missing_fields": missing_fields,
                "message": f"Please provide: {', '.join(missing_fields)}",
                "session": session,
            }

        appointment = get_appointment(db, int(appointment_id))

        if not appointment:
            return {
                "status": "error",
                "message": "Appointment not found.",
            }

        if appointment.calendar_event_id:
            update_calendar_event(
                appointment.calendar_event_id,
                f"{date} {time}",
            )

        updated_appointment = reschedule_appointment(
            db,
            int(appointment_id),
            f"{date} {time}",
        )

        clear_session(request.session_id)

        return {
            "status": "success",
            "message": "Appointment rescheduled successfully.",
            "appointment_id": updated_appointment.id,
            "appointment": {
                "customer_name": updated_appointment.customer_name,
                "phone_number": updated_appointment.phone_number,
                "appointment_time": updated_appointment.appointment_time,
                "status": updated_appointment.status,
            },
        }

    # GET APPOINTMENT
    if session.get("intent") == "get_appointment":
        appointment_id = session.get("appointment_id")

        if not appointment_id:
            return {
                "status": "needs_information",
                "missing_fields": ["appointment_id"],
                "message": "Please provide the appointment ID.",
                "session": session,
            }

        appointment = get_appointment(db, int(appointment_id))

        if not appointment:
            return {
                "status": "error",
                "message": "Appointment not found.",
            }

        clear_session(request.session_id)

        return {
            "status": "success",
            "appointment": {
                "id": appointment.id,
                "customer_name": appointment.customer_name,
                "phone_number": appointment.phone_number,
                "appointment_time": appointment.appointment_time,
                "status": appointment.status,
                "calendar_event_id": appointment.calendar_event_id,
            },
        }

    # BOOK APPOINTMENT
    if session.get("intent") == "book_appointment":
        missing_fields = []

        if not session.get("date"):
            missing_fields.append("date")
        if not session.get("time"):
            missing_fields.append("time")
        if not session.get("customer_name"):
            missing_fields.append("customer_name")
        if not session.get("phone_number"):
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

        calendar_event = create_calendar_event(
            summary=f"Appointment with {created_appointment.customer_name}",
            start_datetime=f"{session['date']} {session['time']}",
        )

        update_calendar_event_id(
            db,
            created_appointment.id,
            calendar_event.get("id"),
        )

        clear_session(request.session_id)

        return {
            "status": "success",
            "message": "Appointment booked successfully.",
            "appointment_id": created_appointment.id,
            "calendar_event_link": calendar_event.get("htmlLink"),
            "calendar_event_id": calendar_event.get("id"),
            "appointment": {
                "customer_name": created_appointment.customer_name,
                "phone_number": created_appointment.phone_number,
                "appointment_time": created_appointment.appointment_time,
                "status": created_appointment.status,
            },
        }

    return agent_response