from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ai.agent import VaaniAgent
from app.database.dependencies import get_db
from app.integrations.google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    update_calendar_event,
)
from app.memory.session_memory import clear_session, get_session, update_session
from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate
from app.schemas.chat import ChatRequest
from app.services.appointment_service import (
    cancel_appointment,
    create_appointment,
    get_appointment,
    get_conflicting_appointment,
    normalize_appointment_slot,
    reschedule_appointment,
    update_appointment,
    update_calendar_event_id,
)

router = APIRouter()
agent = VaaniAgent()


class AdminAppointmentUpdate(BaseModel):
    """Fields an admin may edit.

    Database ID and appointment_code are intentionally excluded.
    """

    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    status: Optional[str] = None
    calendar_event_id: Optional[str] = None


def serialize_appointment(appointment: Appointment) -> dict:
    return {
        "id": appointment.id,
        "appointment_code": appointment.appointment_code,
        "customer_name": appointment.customer_name,
        "phone_number": appointment.phone_number,
        "appointment_date": appointment.appointment_date,
        "appointment_time": appointment.appointment_time,
        "status": appointment.status,
        "calendar_event_id": appointment.calendar_event_id,
        "created_at": (
            appointment.created_at.isoformat()
            if appointment.created_at
            else None
        ),
        "updated_at": (
            appointment.updated_at.isoformat()
            if appointment.updated_at
            else None
        ),
    }


@router.get("/health")
def health():
    return {"status": "healthy"}


@router.get("/appointments")
def list_appointments(
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Appointment)

    if status and status != "all":
        query = query.filter(Appointment.status == status)

    if search and search.strip():
        search_value = f"%{search.strip()}%"

        query = query.filter(
            or_(
                Appointment.appointment_code.ilike(search_value),
                Appointment.customer_name.ilike(search_value),
                Appointment.phone_number.ilike(search_value),
            )
        )

    appointments = query.order_by(Appointment.id.desc()).all()

    return {
        "appointments": [
            serialize_appointment(appointment)
            for appointment in appointments
        ],
        "total": len(appointments),
    }


@router.post("/appointments")
def create_new_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
):
    appointment_data = appointment.model_dump()

    appointment_date = appointment_data.get("appointment_date")
    appointment_time = appointment_data.get("appointment_time")
    status = appointment_data.get("status") or "confirmed"

    if appointment_date and appointment_time and status in {
        "confirmed",
        "rescheduled",
    }:
        try:
            normalized_date, normalized_time, _ = normalize_appointment_slot(
                appointment_date,
                appointment_time,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

        conflict = get_conflicting_appointment(
            db,
            normalized_date,
            normalized_time,
        )

        if conflict:
            raise HTTPException(
                status_code=409,
                detail=(
                    "That slot conflicts with appointment "
                    f"{conflict.appointment_code}."
                ),
            )

    created = create_appointment(db, appointment)
    return serialize_appointment(created)


@router.get("/admin/customers/{phone_number}")
def get_admin_customer_history(
    phone_number: str,
    db: Session = Depends(get_db),
):
    appointments = (
        db.query(Appointment)
        .filter(Appointment.phone_number == phone_number)
        .order_by(Appointment.id.desc())
        .all()
    )

    if not appointments:
        raise HTTPException(
            status_code=404,
            detail="No customer found for that phone number.",
        )

    latest = appointments[0]

    return {
        "customer": {
            "customer_name": latest.customer_name,
            "phone_number": latest.phone_number,
        },
        "appointments": [
            serialize_appointment(appointment)
            for appointment in appointments
        ],
        "total": len(appointments),
    }


@router.patch("/appointments/{appointment_id}")
def admin_update_appointment(
    appointment_id: int,
    changes: AdminAppointmentUpdate,
    db: Session = Depends(get_db),
):
    appointment = get_appointment(db, appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    update_data = changes.model_dump(exclude_unset=True)

    # Prevent blank strings from being stored for optional external IDs.
    if "calendar_event_id" in update_data:
        update_data["calendar_event_id"] = (
            update_data["calendar_event_id"] or None
        )

    new_date = update_data.get(
        "appointment_date",
        appointment.appointment_date,
    )
    new_time = update_data.get(
        "appointment_time",
        appointment.appointment_time,
    )
    new_status = update_data.get(
        "status",
        appointment.status,
    )

    allowed_statuses = {
        "confirmed",
        "rescheduled",
        "cancelled",
        "on_hold",
    }

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=422,
            detail="Invalid appointment status.",
        )

    if new_date and new_time:
        try:
            normalized_date, normalized_time, _ = normalize_appointment_slot(
                new_date,
                new_time,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

        update_data["appointment_date"] = normalized_date
        update_data["appointment_time"] = normalized_time

        if new_status in {"confirmed", "rescheduled"}:
            conflict = get_conflicting_appointment(
                db,
                normalized_date,
                normalized_time,
                exclude_appointment_id=appointment_id,
            )

            if conflict:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "That slot conflicts with appointment "
                        f"{conflict.appointment_code}."
                    ),
                )

    updated = update_appointment(
        db,
        appointment_id,
        **update_data,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    return {
        "status": "success",
        "appointment": serialize_appointment(updated),
    }


@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """Legacy text-chat endpoint.

    Voice calls use the dedicated voice call flow. This route is kept for
    compatibility with the existing text client.
    """

    agent_response = agent.process(request.message)
    entities = agent_response.get("entities") or {}
    session = get_session(request.session_id) or {}

    update_data = {
        "intent": (
            agent_response.get("intent")
            if agent_response.get("intent") != "unknown"
            else session.get("intent")
        ),
        "date": entities.get("date") or session.get("date"),
        "time": entities.get("time") or session.get("time"),
        "appointment_id": (
            entities.get("appointment_id")
            or session.get("appointment_id")
        ),
        "customer_name": (
            getattr(request, "customer_name", None)
            or entities.get("customer_name")
            or session.get("customer_name")
        ),
        "phone_number": (
            getattr(request, "phone_number", None)
            or entities.get("phone_number")
            or session.get("phone_number")
        ),
    }

    session = update_session(request.session_id, update_data)
    intent = session.get("intent")

    if intent == "cancel_appointment":
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
            try:
                delete_calendar_event(appointment.calendar_event_id)
            except Exception:
                # Database cancellation should still proceed if calendar sync fails.
                pass

        cancelled = cancel_appointment(db, int(appointment_id))
        clear_session(request.session_id)

        return {
            "status": "success",
            "message": f"Appointment {appointment_id} has been cancelled.",
            "appointment_id": cancelled.id,
            "appointment": serialize_appointment(cancelled),
        }

    if intent == "reschedule_appointment":
        appointment_id = session.get("appointment_id")
        date = session.get("date")
        time = session.get("time")

        missing_fields = [
            field
            for field, value in {
                "appointment_id": appointment_id,
                "date": date,
                "time": time,
            }.items()
            if not value
        ]

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

        try:
            normalized_date, normalized_time, _ = normalize_appointment_slot(
                date,
                time,
            )
        except ValueError as exc:
            return {
                "status": "error",
                "message": str(exc),
            }

        conflict = get_conflicting_appointment(
            db,
            normalized_date,
            normalized_time,
            exclude_appointment_id=appointment.id,
        )

        if conflict:
            return {
                "status": "slot_unavailable",
                "message": (
                    "That slot conflicts with appointment "
                    f"{conflict.appointment_code}."
                ),
            }

        updated = reschedule_appointment(
            db,
            appointment.id,
            new_date=normalized_date,
            new_time=normalized_time,
        )

        if appointment.calendar_event_id:
            try:
                update_calendar_event(
                    appointment.calendar_event_id,
                    normalized_date,
                    normalized_time,
                )
            except Exception:
                pass

        clear_session(request.session_id)

        return {
            "status": "success",
            "message": "Appointment rescheduled successfully.",
            "appointment_id": updated.id,
            "appointment": serialize_appointment(updated),
        }

    if intent == "get_appointment":
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
            "appointment": serialize_appointment(appointment),
        }

    if intent == "book_appointment":
        required_values = {
            "date": session.get("date"),
            "time": session.get("time"),
            "customer_name": session.get("customer_name"),
            "phone_number": session.get("phone_number"),
        }

        missing_fields = [
            field
            for field, value in required_values.items()
            if not value
        ]

        if missing_fields:
            return {
                "status": "needs_information",
                "missing_fields": missing_fields,
                "message": f"Please provide: {', '.join(missing_fields)}",
                "session": session,
            }

        try:
            normalized_date, normalized_time, _ = normalize_appointment_slot(
                session["date"],
                session["time"],
            )
        except ValueError as exc:
            return {
                "status": "error",
                "message": str(exc),
            }

        conflict = get_conflicting_appointment(
            db,
            normalized_date,
            normalized_time,
        )

        if conflict:
            return {
                "status": "slot_unavailable",
                "message": (
                    "That slot conflicts with appointment "
                    f"{conflict.appointment_code}."
                ),
            }

        appointment_data = AppointmentCreate(
            customer_name=session["customer_name"],
            phone_number=session["phone_number"],
            appointment_date=normalized_date,
            appointment_time=normalized_time,
            status="confirmed",
        )

        created = create_appointment(db, appointment_data)

        try:
            calendar_event = create_calendar_event(
                summary=f"Appointment with {created.customer_name}",
                start_datetime=f"{normalized_date} {normalized_time}",
            )

            calendar_event_id = calendar_event.get("id")

            if calendar_event_id:
                update_calendar_event_id(
                    db,
                    created.id,
                    calendar_event_id,
                )
        except Exception:
            calendar_event = {}

        clear_session(request.session_id)

        return {
            "status": "success",
            "message": "Appointment booked successfully.",
            "appointment_id": created.id,
            "calendar_event_link": calendar_event.get("htmlLink"),
            "calendar_event_id": calendar_event.get("id"),
            "appointment": serialize_appointment(created),
        }

    return agent_response