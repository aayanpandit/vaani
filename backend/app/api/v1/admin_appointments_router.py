import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.admin import Admin
from app.models.appointment import Appointment
from app.models.appointment_audit_log import AppointmentAuditLog
from app.schemas.admin import AdminAppointmentUpdate
from app.services.admin_auth_service import get_current_admin
from app.services.appointment_service import (
    get_appointment,
    get_conflicting_appointment,
    normalize_appointment_slot,
    update_appointment,
)

router = APIRouter(prefix="/admin", tags=["Admin appointments"])
ALLOWED_STATUSES = {"confirmed", "rescheduled", "cancelled", "on_hold"}


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
        "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
        "updated_at": appointment.updated_at.isoformat() if appointment.updated_at else None,
    }


@router.get("/appointments")
def list_admin_appointments(
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    query = db.query(Appointment)
    if status and status != "all":
        query = query.filter(Appointment.status == status)
    if search and search.strip():
        value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Appointment.appointment_code.ilike(value),
                Appointment.customer_name.ilike(value),
                Appointment.phone_number.ilike(value),
            )
        )
    appointments = query.order_by(Appointment.id.desc()).all()
    return {
        "appointments": [serialize_appointment(item) for item in appointments],
        "total": len(appointments),
    }


@router.get("/customers/{phone_number}")
def get_admin_customer_history(
    phone_number: str,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    appointments = (
        db.query(Appointment)
        .filter(Appointment.phone_number == phone_number)
        .order_by(Appointment.id.desc())
        .all()
    )
    if not appointments:
        raise HTTPException(status_code=404, detail="No customer found for that phone number.")
    latest = appointments[0]
    appointment_ids = [item.id for item in appointments]
    audit_logs = (
        db.query(AppointmentAuditLog)
        .filter(AppointmentAuditLog.appointment_id.in_(appointment_ids))
        .order_by(AppointmentAuditLog.id.desc())
        .all()
    )
    return {
        "customer": {
            "customer_name": latest.customer_name,
            "phone_number": latest.phone_number,
        },
        "appointments": [serialize_appointment(item) for item in appointments],
        "audit_logs": [
            {
                "id": log.id,
                "appointment_id": log.appointment_id,
                "admin_id": log.admin_id,
                "action": log.action,
                "old_values": json.loads(log.old_values) if log.old_values else None,
                "new_values": json.loads(log.new_values) if log.new_values else None,
                "reason": log.reason,
                "created_at": log.created_at.isoformat(),
            }
            for log in audit_logs
        ],
        "total": len(appointments),
    }


@router.patch("/appointments/{appointment_id}")
def secure_admin_update_appointment(
    appointment_id: int,
    changes: AdminAppointmentUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    update_data = changes.model_dump(exclude={"reason"}, exclude_unset=True)
    reason = changes.reason.strip()
    old_values = serialize_appointment(appointment)

    new_status = update_data.get("status", appointment.status)
    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid appointment status.")

    new_date = update_data.get("appointment_date", appointment.appointment_date)
    new_time = update_data.get("appointment_time", appointment.appointment_time)

    if new_date and new_time:
        try:
            normalized_date, normalized_time, _ = normalize_appointment_slot(new_date, new_time)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
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
                    detail=f"That slot conflicts with appointment {conflict.appointment_code}.",
                )

    if "calendar_event_id" in update_data:
        update_data["calendar_event_id"] = update_data["calendar_event_id"] or None

    updated = update_appointment(db, appointment_id, **update_data)
    new_values = serialize_appointment(updated)
    changed_fields = [key for key in update_data if old_values.get(key) != new_values.get(key)]
    if not changed_fields:
        raise HTTPException(status_code=400, detail="No appointment values were changed.")

    db.add(
        AppointmentAuditLog(
            appointment_id=appointment_id,
            admin_id=admin.id,
            action="appointment_updated",
            old_values=json.dumps(old_values),
            new_values=json.dumps(new_values),
            reason=reason,
        )
    )
    db.commit()
    return {
        "status": "success",
        "changed_fields": changed_fields,
        "appointment": new_values,
    }
