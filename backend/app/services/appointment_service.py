from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Optional

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate


ACTIVE_STATUSES = {
    "confirmed",
    "rescheduled",
}

SLOT_DURATION_MINUTES = 15

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _appointment_column(*names: str):
    """Return the first matching SQLAlchemy model column."""

    for name in names:
        column = getattr(Appointment, name, None)

        if column is not None:
            return column

    raise AttributeError(
        "Appointment model does not contain any of these fields: "
        f"{', '.join(names)}"
    )


def _get_name_prefix(
    customer_name: Optional[str],
) -> str:
    if not customer_name:
        return "OH"

    cleaned_name = re.sub(
        r"[^A-Za-z]",
        "",
        customer_name,
    ).upper()

    if len(cleaned_name) >= 2:
        return cleaned_name[:2]

    if len(cleaned_name) == 1:
        return f"{cleaned_name}X"

    return "OH"


def generate_appointment_code(
    db: Session,
    customer_name: Optional[str],
) -> str:
    """
    Generate IDs such as:

    Aayan -> AA001
    Rohit -> RO001
    Missing name -> OH001
    """

    prefix = _get_name_prefix(customer_name)

    matching_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.appointment_code.like(
                f"{prefix}%"
            )
        )
        .all()
    )

    highest_number = 0

    for appointment in matching_appointments:
        code = appointment.appointment_code or ""

        match = re.fullmatch(
            rf"{re.escape(prefix)}(\d+)",
            code,
        )

        if not match:
            continue

        highest_number = max(
            highest_number,
            int(match.group(1)),
        )

    return f"{prefix}{highest_number + 1:03d}"


def _parse_appointment_date(
    date_value: str,
    *,
    reference: Optional[datetime] = None,
) -> date:
    """Convert natural date input into a Python date."""

    if not date_value or not date_value.strip():
        raise ValueError("Appointment date is required.")

    reference = reference or datetime.now()

    cleaned = re.sub(
        r"\s+",
        " ",
        date_value.strip().lower(),
    )

    if cleaned == "today":
        return reference.date()

    if cleaned == "tomorrow":
        return (
            reference + timedelta(days=1)
        ).date()

    if cleaned == "day after tomorrow":
        return (
            reference + timedelta(days=2)
        ).date()

    next_weekday_match = re.fullmatch(
        r"next\s+([a-z]+)",
        cleaned,
    )

    if next_weekday_match:
        weekday_name = next_weekday_match.group(1)

        if weekday_name in WEEKDAYS:
            target_weekday = WEEKDAYS[weekday_name]

            days_ahead = (
                target_weekday
                - reference.weekday()
            ) % 7

            if days_ahead == 0:
                days_ahead = 7

            return (
                reference
                + timedelta(days=days_ahead)
            ).date()

    if cleaned in WEEKDAYS:
        target_weekday = WEEKDAYS[cleaned]

        days_ahead = (
            target_weekday
            - reference.weekday()
        ) % 7

        return (
            reference
            + timedelta(days=days_ahead)
        ).date()

    try:
        parsed = date_parser.parse(
            date_value,
            dayfirst=True,
            fuzzy=True,
            default=reference.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            ),
        )
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Could not understand date: {date_value}"
        ) from exc

    return parsed.date()


def _parse_appointment_time(
    time_value: str,
) -> time:
    """Convert spoken or typed time into a Python time."""

    if not time_value or not time_value.strip():
        raise ValueError("Appointment time is required.")

    cleaned = re.sub(
        r"\s+",
        " ",
        time_value.strip().upper(),
    )

    formats = (
        "%I:%M %p",
        "%I %p",
        "%H:%M",
        "%H",
    )

    for time_format in formats:
        try:
            parsed = datetime.strptime(
                cleaned,
                time_format,
            )

            return parsed.time().replace(
                second=0,
                microsecond=0,
            )
        except ValueError:
            continue

    try:
        parsed = date_parser.parse(
            cleaned,
            fuzzy=True,
        )
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Could not understand time: {time_value}"
        ) from exc

    return parsed.time().replace(
        second=0,
        microsecond=0,
    )


def normalize_appointment_slot(
    appointment_date: str,
    appointment_time: str,
) -> tuple[str, str, datetime]:
    """
    Normalize an appointment slot.

    Returns:
        ("2026-07-22", "18:30", datetime(...))
    """

    parsed_date = _parse_appointment_date(
        appointment_date
    )

    parsed_time = _parse_appointment_time(
        appointment_time
    )

    if parsed_time.minute % SLOT_DURATION_MINUTES != 0:
        raise ValueError(
            "Appointments must begin at a 15-minute "
            "interval, such as 6:00, 6:15, 6:30, or 6:45."
        )

    slot_start = datetime.combine(
        parsed_date,
        parsed_time,
    )

    return (
        parsed_date.isoformat(),
        parsed_time.strftime("%H:%M"),
        slot_start,
    )


def _appointment_start_datetime(
    appointment: Appointment,
) -> Optional[datetime]:
    appointment_date = getattr(
        appointment,
        "appointment_date",
        None,
    )

    appointment_time = getattr(
        appointment,
        "appointment_time",
        None,
    )

    if not appointment_date or not appointment_time:
        return None

    try:
        _, _, start_datetime = (
            normalize_appointment_slot(
                appointment_date,
                appointment_time,
            )
        )

        return start_datetime
    except ValueError:
        return None


def get_conflicting_appointment(
    db: Session,
    appointment_date: str,
    appointment_time: str,
    *,
    exclude_appointment_id: Optional[int] = None,
) -> Optional[Appointment]:
    """
    Return an appointment that overlaps the requested
    15-minute slot, or None if the slot is free.
    """

    _, _, requested_start = normalize_appointment_slot(
        appointment_date,
        appointment_time,
    )

    requested_end = requested_start + timedelta(
        minutes=SLOT_DURATION_MINUTES
    )

    query = db.query(Appointment).filter(
        Appointment.status.in_(ACTIVE_STATUSES)
    )

    if exclude_appointment_id is not None:
        query = query.filter(
            Appointment.id != exclude_appointment_id
        )

    for appointment in query.all():
        existing_start = _appointment_start_datetime(
            appointment
        )

        if existing_start is None:
            continue

        existing_end = existing_start + timedelta(
            minutes=SLOT_DURATION_MINUTES
        )

        overlaps = (
            existing_start < requested_end
            and existing_end > requested_start
        )

        if overlaps:
            return appointment

    return None


def is_slot_available(
    db: Session,
    appointment_date: str,
    appointment_time: str,
    *,
    exclude_appointment_id: Optional[int] = None,
) -> bool:
    return (
        get_conflicting_appointment(
            db,
            appointment_date,
            appointment_time,
            exclude_appointment_id=(
                exclude_appointment_id
            ),
        )
        is None
    )


def find_next_available_slots(
    db: Session,
    appointment_date: str,
    appointment_time: str,
    *,
    exclude_appointment_id: Optional[int] = None,
    number_of_slots: int = 3,
    maximum_checks: int = 96,
) -> list[dict[str, str]]:
    """
    Find the next available 15-minute slots.

    Ninety-six checks represent the next 24 hours.
    """

    _, _, requested_start = normalize_appointment_slot(
        appointment_date,
        appointment_time,
    )

    suggestions: list[dict[str, str]] = []

    candidate = requested_start + timedelta(
        minutes=SLOT_DURATION_MINUTES
    )

    for _ in range(maximum_checks):
        candidate_date = candidate.date().isoformat()
        candidate_time = candidate.strftime("%H:%M")

        if is_slot_available(
            db,
            candidate_date,
            candidate_time,
            exclude_appointment_id=(
                exclude_appointment_id
            ),
        ):
            suggestions.append(
                {
                    "date": candidate_date,
                    "time": candidate_time,
                    "display": candidate.strftime(
                        "%d %B %Y at %I:%M %p"
                    ),
                }
            )

            if len(suggestions) >= number_of_slots:
                break

        candidate += timedelta(
            minutes=SLOT_DURATION_MINUTES
        )

    return suggestions


def create_appointment(
    db: Session,
    appointment: AppointmentCreate,
):
    appointment_data = appointment.model_dump()

    appointment_date = appointment_data.get(
        "appointment_date"
    )

    appointment_time = appointment_data.get(
        "appointment_time"
    )

    if appointment_date and appointment_time:
        normalized_date, normalized_time, _ = (
            normalize_appointment_slot(
                appointment_date,
                appointment_time,
            )
        )

        appointment_data["appointment_date"] = (
            normalized_date
        )

        appointment_data["appointment_time"] = (
            normalized_time
        )

    appointment_code = generate_appointment_code(
        db,
        appointment_data.get("customer_name"),
    )

    db_appointment = Appointment(
        **appointment_data,
        appointment_code=appointment_code,
    )

    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)

    return db_appointment


def get_appointment(
    db: Session,
    appointment_id: int,
) -> Optional[Appointment]:
    return (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id
        )
        .first()
    )


def get_appointment_by_code(
    db: Session,
    appointment_code: str,
) -> Optional[Appointment]:
    cleaned_code = appointment_code.strip().upper()

    return (
        db.query(Appointment)
        .filter(
            Appointment.appointment_code
            == cleaned_code
        )
        .first()
    )


def get_appointments_by_phone(
    db: Session,
    phone_number: str,
    include_cancelled: bool = False,
) -> list[Appointment]:
    query = db.query(Appointment).filter(
        Appointment.phone_number == phone_number
    )

    if not include_cancelled:
        query = query.filter(
            Appointment.status != "cancelled"
        )

    return query.order_by(
        Appointment.id.desc()
    ).all()


def get_active_appointments_by_phone(
    db: Session,
    phone_number: str,
) -> list[Appointment]:
    return (
        db.query(Appointment)
        .filter(
            Appointment.phone_number
            == phone_number,
            Appointment.status.in_(
                ACTIVE_STATUSES
            ),
        )
        .order_by(
            Appointment.id.desc()
        )
        .all()
    )


def get_latest_appointment_by_phone(
    db: Session,
    phone_number: str,
) -> Optional[Appointment]:
    appointments = get_active_appointments_by_phone(
        db,
        phone_number,
    )

    return appointments[0] if appointments else None


def get_on_hold_appointment_by_code(
    db: Session,
    appointment_code: str,
) -> Optional[Appointment]:
    cleaned_code = appointment_code.strip().upper()

    return (
        db.query(Appointment)
        .filter(
            Appointment.appointment_code
            == cleaned_code,
            Appointment.status == "on_hold",
        )
        .first()
    )


def update_appointment(
    db: Session,
    appointment_id: int,
    **changes,
) -> Optional[Appointment]:
    appointment = get_appointment(
        db,
        appointment_id,
    )

    if not appointment:
        return None

    allowed_fields = {
        "customer_name",
        "phone_number",
        "appointment_date",
        "appointment_time",
        "status",
        "calendar_event_id",
    }

    for field, value in changes.items():
        if field not in allowed_fields:
            continue

        if hasattr(appointment, field):
            setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)

    return appointment


def cancel_appointment(
    db: Session,
    appointment_id: int,
) -> Optional[Appointment]:
    return update_appointment(
        db,
        appointment_id,
        status="cancelled",
    )


def reschedule_appointment(
    db: Session,
    appointment_id: int,
    new_date: str,
    new_time: str,
) -> Optional[Appointment]:
    normalized_date, normalized_time, _ = (
        normalize_appointment_slot(
            new_date,
            new_time,
        )
    )

    return update_appointment(
        db,
        appointment_id,
        appointment_date=normalized_date,
        appointment_time=normalized_time,
        status="rescheduled",
    )


def update_calendar_event_id(
    db: Session,
    appointment_id: int,
    calendar_event_id: str,
) -> Optional[Appointment]:
    return update_appointment(
        db,
        appointment_id,
        calendar_event_id=calendar_event_id,
    )