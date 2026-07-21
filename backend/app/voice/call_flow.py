from __future__ import annotations

import inspect
import logging
import re
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.ai.agent import VaaniAgent
from app.integrations.google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    update_calendar_event,
)
from app.memory.session_memory import clear_session, get_session, update_session
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import (
    cancel_appointment,
    create_appointment,
    find_next_available_slots,
    get_latest_appointment_by_phone,
    is_slot_available,
    normalize_appointment_slot,
    reschedule_appointment,
    update_calendar_event_id,
)

logger = logging.getLogger("vaani.call_flow")


class Intent(str, Enum):
    BOOK = "book"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    LOOKUP = "lookup"


class Stage(str, Enum):
    GREETING = "greeting"
    COLLECT_INTENT = "collect_intent"
    COLLECT_DATE = "collect_date"
    COLLECT_TIME = "collect_time"
    COLLECT_NAME = "collect_name"
    COLLECT_PHONE = "collect_phone"
    COLLECT_APPOINTMENT_ID = "collect_appointment_id"
    CONFIRM_FINAL = "confirm_final"
    EXECUTE = "execute"
    END = "end"


REQUIRED_FIELDS: Dict[Intent, list[str]] = {
    Intent.BOOK: ["date", "time", "customer_name", "phone_number"],
    Intent.RESCHEDULE: ["phone_number", "date", "time"],
    Intent.CANCEL: ["phone_number"],
    Intent.LOOKUP: ["phone_number"],
}

FIELD_TO_STAGE: Dict[str, Stage] = {
    "date": Stage.COLLECT_DATE,
    "time": Stage.COLLECT_TIME,
    "customer_name": Stage.COLLECT_NAME,
    "phone_number": Stage.COLLECT_PHONE,
    "appointment_id": Stage.COLLECT_APPOINTMENT_ID,
}

PURE_GREETINGS = {
    "hi",
    "hii",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}

YES_WORDS = {
    "yes",
    "yeah",
    "yep",
    "yup",
    "correct",
    "confirm",
    "confirmed",
    "sure",
    "ok",
    "okay",
    "proceed",
}

NO_WORDS = {"no", "nope", "nah", "wrong", "incorrect"}

YES_PHRASES = {
    "go ahead",
    "book it",
    "please book",
    "please proceed",
    "sounds good",
    "do it",
}

NO_PHRASES = {
    "do not book",
    "don't book",
    "not correct",
    "change it",
    "cancel that",
}


# A single reusable agent instance is enough for this module.
agent = VaaniAgent()


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _is_pure_greeting(text: str) -> bool:
    cleaned = re.sub(r"[^a-z\s]", "", _clean_text(text).lower()).strip()
    return cleaned in PURE_GREETINGS


def _classify_yes_no(text: str) -> Optional[bool]:
    lowered = _clean_text(text).lower()
    tokens = set(re.findall(r"[a-z']+", lowered))

    if any(phrase in lowered for phrase in NO_PHRASES):
        return False
    if tokens & NO_WORDS:
        return False
    if any(phrase in lowered for phrase in YES_PHRASES):
        return True
    if tokens & YES_WORDS:
        return True
    return None


def _normalize_intent(value: Any) -> Optional[Intent]:
    if isinstance(value, Intent):
        return value
    if value is None:
        return None

    text = str(value).strip().lower()
    mapping = {
        "book": Intent.BOOK,
        "booking": Intent.BOOK,
        "schedule": Intent.BOOK,
        "create": Intent.BOOK,
        "reschedule": Intent.RESCHEDULE,
        "rescheduling": Intent.RESCHEDULE,
        "move": Intent.RESCHEDULE,
        "postpone": Intent.RESCHEDULE,
        "cancel": Intent.CANCEL,
        "cancellation": Intent.CANCEL,
        "lookup": Intent.LOOKUP,
        "look_up": Intent.LOOKUP,
        "check": Intent.LOOKUP,
        "find": Intent.LOOKUP,
        "status": Intent.LOOKUP,
    }
    return mapping.get(text)


def _normalize_stage(value: Any) -> Stage:
    if isinstance(value, Stage):
        return value
    if not value:
        return Stage.GREETING

    text = str(value).strip().lower()
    aliases = {
        "intent": Stage.COLLECT_INTENT,
        "collect_intent": Stage.COLLECT_INTENT,
        "greeting": Stage.GREETING,
        "collect_date": Stage.COLLECT_DATE,
        "collect_time": Stage.COLLECT_TIME,
        "collect_name": Stage.COLLECT_NAME,
        "collect_phone": Stage.COLLECT_PHONE,
        "collect_appointment_id": Stage.COLLECT_APPOINTMENT_ID,
        "confirm": Stage.CONFIRM_FINAL,
        "confirm_identity": Stage.CONFIRM_FINAL,
        "confirm_final": Stage.CONFIRM_FINAL,
        "execute": Stage.EXECUTE,
        "end": Stage.END,
    }
    return aliases.get(text, Stage.GREETING)


def _safe_session(session_id: str) -> Dict[str, Any]:
    raw = get_session(session_id) or {}
    return {
        "session_id": session_id,
        "stage": _normalize_stage(raw.get("stage")).value,
        "intent": _normalize_intent(raw.get("intent")).value
        if _normalize_intent(raw.get("intent"))
        else None,
        "date": raw.get("date"),
        "time": raw.get("time"),
        "customer_name": raw.get("customer_name") or raw.get("name"),
        "phone_number": raw.get("phone_number") or raw.get("phone"),
        "appointment_id": raw.get("appointment_id"),
        "awaiting_change": bool(raw.get("awaiting_change", False)),
    }


def _save(session_id: str, **changes: Any) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in changes.items():
        if isinstance(value, Enum):
            cleaned[key] = value.value
        else:
            cleaned[key] = value
    update_session(session_id, cleaned)
    return _safe_session(session_id)


def _response(
    session_id: str,
    message: str,
    *,
    status: str = "in_progress",
    end_call: bool = False,
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": status,
        "end_call": end_call,
        "message": message,
        "session": _safe_session(session_id),
    }
    payload.update(extra)
    return payload


def _extract_with_agent(message: str, session: Dict[str, Any]) -> Dict[str, Any]:
    """Use the existing VaaniAgent while tolerating small API differences."""

    result: Any = None

    # Try the most common method names and signatures used in agent wrappers.
    candidate_calls = [
        ("process", (message,), {"context": session}),
        ("process", (message, session), {}),
        ("analyze", (message,), {"context": session}),
        ("analyze", (message, session), {}),
        ("extract", (message,), {"context": session}),
        ("extract", (message, session), {}),
        ("detect_intent_and_entities", (message,), {"context": session}),
        ("detect_intent_and_entities", (message, session), {}),
    ]

    for method_name, args, kwargs in candidate_calls:
        method = getattr(agent, method_name, None)
        if not callable(method):
            continue
        try:
            result = method(*args, **kwargs)
            break
        except TypeError:
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("VaaniAgent.%s failed: %s", method_name, exc)
            break

    if result is None and callable(agent):
        try:
            result = agent(message, session)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Callable VaaniAgent failed: %s", exc)

    if hasattr(result, "model_dump"):
        result = result.model_dump()
    elif hasattr(result, "dict"):
        result = result.dict()

    if not isinstance(result, dict):
        result = {}

    entities = result.get("entities") or result.get("extracted_entities") or result

    intent = (
        result.get("intent")
        or result.get("detected_intent")
        or entities.get("intent")
    )

    extracted = {
        "intent": _normalize_intent(intent),
        "date": entities.get("date") or entities.get("appointment_date"),
        "time": entities.get("time") or entities.get("appointment_time"),
        "customer_name": (
            entities.get("customer_name")
            or entities.get("name")
            or entities.get("full_name")
        ),
        "phone_number": (
            entities.get("phone_number")
            or entities.get("phone")
            or entities.get("mobile")
        ),
        "appointment_id": (
            entities.get("appointment_id")
            or entities.get("booking_id")
            or entities.get("id")
        ),
    }

    fallback = _fallback_extract(message)
    for key, value in fallback.items():
        if extracted.get(key) in (None, ""):
            extracted[key] = value

    return extracted

def _extract_natural_date(message: str) -> Optional[str]:
    text = _clean_text(message)
    lowered = text.lower()

    relative_dates = (
        "day after tomorrow",
        "tomorrow",
        "today",
    )

    for relative_date in relative_dates:
        if relative_date in lowered:
            return relative_date

    # Matches:
    # 21 July
    # 21st July
    # July 21
    # July 21st
    # 21 July 2026
    month_names = (
        "january|february|march|april|may|june|"
        "july|august|september|october|november|december|"
        "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
    )

    date_patterns = [
        rf"\b(\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{month_names})(?:\s+\d{{4}})?)\b",
        rf"\b((?:{month_names})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,\s*|\s+)?(?:\d{{4}})?)\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(1).strip()

    weekdays = (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )

    for weekday in weekdays:
        if f"next {weekday}" in lowered:
            return f"next {weekday}"

        if weekday in lowered:
            return weekday

    return None

def _extract_spoken_phone_number(message: str) -> Optional[str]:
    """Extract an Indian ten-digit mobile number from digits or spoken digits."""

    text = _clean_text(message).lower()

    digit_words = {
        "zero": "0", "oh": "0", "o": "0",
        "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8",
        "nine": "9",
    }

    # First try ordinary digits, allowing spaces, hyphens and country code.
    compact = re.sub(r"[^0-9+]", "", text)
    compact = re.sub(r"^\+?91", "", compact)
    digit_match = re.search(r"([6-9]\d{9})", compact)
    if digit_match:
        return digit_match.group(1)

    # Then convert spoken digits such as "nine eight seven...".
    tokens = re.findall(r"[a-z]+|\d", text)
    spoken_digits = "".join(
        token if token.isdigit() else digit_words.get(token, "")
        for token in tokens
    )

    if spoken_digits.startswith("91") and len(spoken_digits) >= 12:
        spoken_digits = spoken_digits[2:]

    spoken_match = re.search(r"([6-9]\d{9})", spoken_digits)
    return spoken_match.group(1) if spoken_match else None


def _extract_name_response(message: str) -> Optional[str]:
    """Normalize a short name reply without accepting commands as names."""

    original = _clean_text(message)
    lowered = original.lower()

    # Never treat appointment commands or refusals as a person's name.
    blocked_words = {
        "appointment", "book", "booking", "schedule", "reschedule",
        "cancel", "lookup", "phone", "number", "date", "time",
    }
    words = set(re.findall(r"[a-z]+", lowered))
    if words & blocked_words or _is_required_detail_refusal(original):
        return None

    text = re.sub(
        r"^(?:it\s*['’]?s|its|i am|i['’]?m|my name is|this is|name is)\s+",
        "",
        original,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[^A-Za-z\s'-]", "", text).strip()
    text = re.sub(r"\s+", " ", text)

    if not text:
        return None

    name_words = text.split()
    if not 1 <= len(name_words) <= 4:
        return None

    # A valid name reply should contain letters only and should not be a sentence.
    if any(word.lower() in blocked_words for word in name_words):
        return None

    return text.title()


def _fallback_extract(message: str) -> Dict[str, Any]:
    """Deterministically extract simple appointment fields from user speech."""

    text = _clean_text(message)
    lowered = text.lower()
    result: Dict[str, Any] = {
        "intent": None,
        "date": None,
        "time": None,
        "customer_name": None,
        "phone_number": None,
        "appointment_id": None,
    }

    if "cancel" in lowered:
        result["intent"] = Intent.CANCEL
    elif any(phrase in lowered for phrase in ("reschedule", "postpone", "move my appointment")):
        result["intent"] = Intent.RESCHEDULE
    elif any(
        phrase in lowered
        for phrase in (
            "lookup",
            "look up",
            "check appointment",
            "check my appointment",
            "find appointment",
            "appointment status",
        )
    ):
        result["intent"] = Intent.LOOKUP
    elif any(word in lowered for word in ("book", "schedule", "appointment")):
        result["intent"] = Intent.BOOK

    result["phone_number"] = _extract_spoken_phone_number(message)

    appointment_patterns = [
        r"\b(?:appointment|booking)\s*(?:id|number|no\.?|#)?\s*(?:is|:)?\s*([A-Za-z]*[-_]?\d+)\b",
        r"\bid\s*(?:is|:)?\s*([A-Za-z]*[-_]?\d+)\b",
        r"\b(APT[-_]?\d+)\b",
        r"#(\d+)\b",
    ]
    for pattern in appointment_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_id = match.group(1).strip()
            result["appointment_id"] = int(raw_id) if raw_id.isdigit() else raw_id.upper()
            break

    result["customer_name"] = _extract_name_response(message)

    result["date"] = _extract_natural_date(message)

    normalized_time_text = lowered.replace(".", "")
    normalized_time_text = re.sub(r"\s+", " ", normalized_time_text).strip()

    normalized_time_text = re.sub(
        r"\b([ap])\s+m\b",
        r"\1m",
        normalized_time_text,
        flags=re.IGNORECASE,
    )

    minute_phrases = {
        "forty five": "45",
        "forty-five": "45",
        "quarter past": "15",
        "fifteen": "15",
        "thirty": "30",
        "forty": "40",
    }

    for phrase, number in minute_phrases.items():
        normalized_time_text = re.sub(
            rf"\b{re.escape(phrase)}\b",
            number,
            normalized_time_text,
            flags=re.IGNORECASE,
        )

    hour_words = {
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
    }

    for word, number in hour_words.items():
        normalized_time_text = re.sub(
            rf"\b{word}\b",
            number,
            normalized_time_text,
            flags=re.IGNORECASE,
        )

    normalized_time_text = re.sub(
        r"\b(\d{1,2})\s+(15|30|45)\s*(am|pm)\b",
        r"\1:\2 \3",
        normalized_time_text,
        flags=re.IGNORECASE,
    )

    normalized_time_text = re.sub(
        r"\b(\d{1,2})\s+(15|30|45)\b",
        r"\1:\2",
        normalized_time_text,
        flags=re.IGNORECASE,
    )

    time_patterns = [
        r"\b(\d{1,2}:\d{2}\s*(?:am|pm))\b",
        r"\b(\d{1,2}\s*(?:am|pm))\b",
        r"\b(?:at|around|by)\s+(\d{1,2}:\d{2})\b",
        r"^\s*(\d{1,2}:\d{2})\s*$",
        r"^\s*(\d{1,2})\s*$",
    ]

    for pattern in time_patterns:
        time_match = re.search(pattern, normalized_time_text, re.IGNORECASE)
        if not time_match:
            continue

        parsed_time = re.sub(
            r"\s+",
            " ",
            time_match.group(1).strip(),
        ).upper()

        hour_match = re.match(r"(\d{1,2})", parsed_time)
        if not hour_match:
            continue

        hour = int(hour_match.group(1))
        minute_match = re.search(r":(\d{2})", parsed_time)
        minute = int(minute_match.group(1)) if minute_match else 0
        has_meridiem = bool(re.search(r"\b(?:AM|PM)\b", parsed_time))

        if minute not in {0, 15, 30, 45}:
            continue
        if has_meridiem and not 1 <= hour <= 12:
            continue
        if not has_meridiem and not 0 <= hour <= 23:
            continue

        result["time"] = parsed_time
        break

    return result

def _merge_entities(session_id: str, session: Dict[str, Any], entities: Dict[str, Any]) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}

    # Preserve an existing intent unless the user is starting a fresh transaction.
    if not session.get("intent") and entities.get("intent"):
        updates["intent"] = entities["intent"].value

    for key in ("date", "time", "customer_name", "phone_number", "appointment_id"):
        value = entities.get(key)
        if value not in (None, "", "null", "None"):
            updates[key] = value

    if updates:
        return _save(session_id, **updates)
    return session


def _missing_field(session: Dict[str, Any]) -> Optional[str]:
    intent = _normalize_intent(session.get("intent"))
    if intent is None:
        return None
    for field in REQUIRED_FIELDS[intent]:
        if session.get(field) in (None, ""):
            return field
    return None


def _prompt_for_stage(stage: Stage, intent: Optional[Intent]) -> str:
    if stage == Stage.COLLECT_INTENT:
        return (
            "I can help you book, reschedule, cancel, or look up an appointment. "
            "What would you like to do?"
        )
    if stage == Stage.COLLECT_DATE:
        if intent == Intent.RESCHEDULE:
            return "Sure. What new date would you prefer?"
        return "Sure. What date would you prefer?"
    if stage == Stage.COLLECT_TIME:
        if intent == Intent.RESCHEDULE:
            return "What new time would you prefer?"
        return "What time would you prefer?"
    if stage == Stage.COLLECT_NAME:
        return "May I have your full name, please?"
    if stage == Stage.COLLECT_PHONE:
        return "May I have your phone number?"
    if stage == Stage.COLLECT_APPOINTMENT_ID:
        return "Please share your appointment ID."
    return "How may I help you?"


def _confirmation_message(session: Dict[str, Any]) -> str:
    intent = _normalize_intent(session.get("intent"))

    if intent == Intent.BOOK:
        return (
            "Let me confirm. "
            f"You would like an appointment on {session.get('date')} at {session.get('time')} "
            f"under the name {session.get('customer_name')}, with phone number "
            f"{session.get('phone_number')}. Should I book it?"
        )

    if intent == Intent.RESCHEDULE:
        return (
            "Let me confirm. "
            f"You want the appointment linked to {session.get('phone_number')} moved to "
            f"{session.get('date')} at {session.get('time')}. Should I reschedule it?"
        )

    if intent == Intent.CANCEL:
        return (
            "Let me confirm. Should I cancel the active appointment linked to "
            f"{session.get('phone_number')}?"
        )

    return "Should I proceed?"


def _result_value(result: Any, *names: str) -> Any:
    if result is None:
        return None
    if isinstance(result, dict):
        for name in names:
            if result.get(name) is not None:
                return result.get(name)
    for name in names:
        value = getattr(result, name, None)
        if value is not None:
            return value
    return None


def _call_flexibly(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Call existing project functions even if their parameter names differ slightly."""
    try:
        return func(*args, **kwargs)
    except TypeError:
        signature = inspect.signature(func)
        accepted = {
            key: value
            for key, value in kwargs.items()
            if key in signature.parameters
        }
        return func(*args, **accepted)


def _validate_requested_slot(
    session_id: str,
    session: Dict[str, Any],
    db: Session,
    *,
    exclude_appointment_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Normalize, validate, and check availability of the requested slot."""

    appointment_date = session.get("date")
    appointment_time = session.get("time")

    try:
        normalized_date, normalized_time, _ = normalize_appointment_slot(
            appointment_date,
            appointment_time,
        )
    except ValueError as exc:
        _save(
            session_id,
            time=None,
            stage=Stage.COLLECT_TIME,
        )
        return _response(
            session_id,
            str(exc),
            status="invalid_slot",
            end_call=False,
        )

    _save(
        session_id,
        date=normalized_date,
        time=normalized_time,
    )

    if is_slot_available(
        db,
        normalized_date,
        normalized_time,
        exclude_appointment_id=exclude_appointment_id,
    ):
        return None

    suggestions = find_next_available_slots(
        db,
        normalized_date,
        normalized_time,
        exclude_appointment_id=exclude_appointment_id,
        number_of_slots=3,
    )

    suggestion_text = ", ".join(
        suggestion["display"]
        for suggestion in suggestions
    )

    _save(
        session_id,
        time=None,
        stage=Stage.COLLECT_TIME,
    )

    if suggestion_text:
        message = (
            "That slot is already booked. "
            f"The next available options are {suggestion_text}. "
            "What time would you prefer?"
        )
    else:
        message = (
            "That slot is already booked. "
            "Please tell me another preferred time."
        )

    return _response(
        session_id,
        message,
        status="slot_unavailable",
        end_call=False,
        suggested_slots=suggestions,
    )


def _build_appointment_payload(session: Dict[str, Any]) -> AppointmentCreate:
    """Build AppointmentCreate using the field names defined by the actual schema."""

    model_fields = getattr(AppointmentCreate, "model_fields", {})
    field_names = set(model_fields)

    payload: Dict[str, Any] = {}

    if "customer_name" in field_names:
        payload["customer_name"] = session["customer_name"]
    elif "name" in field_names:
        payload["name"] = session["customer_name"]

    if "phone_number" in field_names:
        payload["phone_number"] = session["phone_number"]
    elif "phone" in field_names:
        payload["phone"] = session["phone_number"]

    if "appointment_date" in field_names:
        payload["appointment_date"] = session["date"]
    elif "date" in field_names:
        payload["date"] = session["date"]

    if "appointment_time" in field_names:
        payload["appointment_time"] = session["time"]
    elif "time" in field_names:
        payload["time"] = session["time"]

    if "status" in field_names:
        payload["status"] = "confirmed"

    return AppointmentCreate(**payload)

def _execute_booking(session_id: str, session: Dict[str, Any], db: Session) -> Dict[str, Any]:
    missing = _missing_field(session)
    if missing:
        stage = FIELD_TO_STAGE[missing]
        _save(session_id, stage=stage)
        return _response(
            session_id,
            (
                f"I cannot confirm this appointment because the required "
                f"{_required_field_label(stage)} is missing. The request is on hold "
                "due to insufficient information."
            ),
            status="on_hold",
            end_call=True,
            appointment_id=None,
        )

    slot_error = _validate_requested_slot(
        session_id,
        session,
        db,
    )
    if slot_error:
        return slot_error

    session = _safe_session(session_id)
    appointment_data = _build_appointment_payload(session)
    appointment = create_appointment(db, appointment_data)

    appointment_id = _result_value(appointment, "id", "appointment_id")
    calendar_event_link = None
    calendar_event_id = None

    try:
        calendar_result = _call_flexibly(
            create_calendar_event,
            appointment,
            appointment=appointment,
            date=session["date"],
            time=session["time"],
            customer_name=session["customer_name"],
            phone_number=session["phone_number"],
        )
        calendar_event_id = _result_value(calendar_result, "id", "event_id", "calendar_event_id")
        calendar_event_link = _result_value(
            calendar_result,
            "htmlLink",
            "html_link",
            "event_link",
            "calendar_event_link",
            "link",
        )

        if appointment_id and calendar_event_id:
            _call_flexibly(
                update_calendar_event_id,
                db,
                appointment_id,
                calendar_event_id,
                appointment_id=appointment_id,
                calendar_event_id=calendar_event_id,
                event_id=calendar_event_id,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Appointment booked but calendar sync failed: %s", exc)

    _save(session_id, stage=Stage.END, awaiting_change=False)
    return _response(
        session_id,
        (
            f"Your appointment has been booked successfully for {session['date']} "
            f"at {session['time']}."
        ),
        status="success",
        end_call=True,
        appointment_id=appointment_id,
        calendar_event_link=calendar_event_link,
    )


def _find_appointment_for_phone(db: Session, phone_number: str):
    return get_latest_appointment_by_phone(db, phone_number)


def _execute_lookup(session_id: str, session: Dict[str, Any], db: Session) -> Dict[str, Any]:
    phone_number = session["phone_number"]
    appointment = _find_appointment_for_phone(db, phone_number)

    if not appointment:
        _save(session_id, stage=Stage.END)
        return _response(
            session_id,
            "I couldn't find an active appointment linked to that phone number.",
            status="not_found",
            end_call=True,
        )

    date = _result_value(appointment, "date", "appointment_date")
    time = _result_value(appointment, "time", "appointment_time")
    name = _result_value(appointment, "customer_name", "name")
    status = _result_value(appointment, "status") or "confirmed"

    _save(session_id, stage=Stage.END)
    return _response(
        session_id,
        (
            f"I found the appointment for {name or 'the customer'} on {date} at {time}. "
            f"Its status is {status}."
        ),
        status="success",
        end_call=True,
        appointment_id=_result_value(appointment, "id", "appointment_id"),
    )


def _execute_cancellation(session_id: str, session: Dict[str, Any], db: Session) -> Dict[str, Any]:
    phone_number = session["phone_number"]
    appointment = _find_appointment_for_phone(db, phone_number)

    if not appointment:
        _save(session_id, stage=Stage.END)
        return _response(
            session_id,
            "I couldn't find an active appointment linked to that phone number.",
            status="not_found",
            end_call=True,
        )

    appointment_id = _result_value(appointment, "id", "appointment_id")
    calendar_event_id = _result_value(appointment, "calendar_event_id", "event_id")

    if calendar_event_id:
        try:
            _call_flexibly(
                delete_calendar_event,
                calendar_event_id,
                event_id=calendar_event_id,
                calendar_event_id=calendar_event_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Calendar deletion failed: %s", exc)

    cancel_appointment(db, appointment_id)

    _save(session_id, stage=Stage.END)
    return _response(
        session_id,
        "Your appointment has been cancelled successfully.",
        status="success",
        end_call=True,
        appointment_id=appointment_id,
    )


def _execute_reschedule(session_id: str, session: Dict[str, Any], db: Session) -> Dict[str, Any]:
    phone_number = session["phone_number"]
    appointment = _find_appointment_for_phone(db, phone_number)

    if not appointment:
        _save(session_id, stage=Stage.END)
        return _response(
            session_id,
            "I couldn't find an active appointment linked to that phone number.",
            status="not_found",
            end_call=True,
        )

    appointment_id = _result_value(appointment, "id", "appointment_id")

    slot_error = _validate_requested_slot(
        session_id,
        session,
        db,
        exclude_appointment_id=appointment_id,
    )
    if slot_error:
        return slot_error

    session = _safe_session(session_id)
    updated = reschedule_appointment(
        db,
        appointment_id,
        new_date=session["date"],
        new_time=session["time"],
    )

    calendar_event_id = _result_value(appointment, "calendar_event_id", "event_id")
    calendar_event_link = None

    if calendar_event_id:
        try:
            calendar_result = _call_flexibly(
                update_calendar_event,
                calendar_event_id,
                session["date"],
                session["time"],
                event_id=calendar_event_id,
                calendar_event_id=calendar_event_id,
                new_date=session["date"],
                new_time=session["time"],
                date=session["date"],
                time=session["time"],
                appointment=updated or appointment,
            )
            calendar_event_link = _result_value(
                calendar_result,
                "htmlLink",
                "html_link",
                "event_link",
                "calendar_event_link",
                "link",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Calendar update failed: %s", exc)

    _save(session_id, stage=Stage.END)
    return _response(
        session_id,
        (
            f"Your appointment has been rescheduled successfully to "
            f"{session['date']} at {session['time']}."
        ),
        status="success",
        end_call=True,
        appointment_id=appointment_id,
        calendar_event_link=calendar_event_link,
    )


def _execute_action(session_id: str, db: Session) -> Dict[str, Any]:
    session = _safe_session(session_id)
    intent = _normalize_intent(session.get("intent"))

    try:
        if intent == Intent.BOOK:
            return _execute_booking(session_id, session, db)
        if intent == Intent.LOOKUP:
            return _execute_lookup(session_id, session, db)
        if intent == Intent.CANCEL:
            return _execute_cancellation(session_id, session, db)
        if intent == Intent.RESCHEDULE:
            return _execute_reschedule(session_id, session, db)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to execute %s: %s", intent, exc)
        _save(session_id, stage=Stage.CONFIRM_FINAL)
        return _response(
            session_id,
            "I'm sorry, I couldn't complete that because of a technical issue. Please say yes to try again or no to stop.",
            status="error",
            end_call=False,
        )

    _save(session_id, stage=Stage.COLLECT_INTENT)
    return _response(
        session_id,
        "I couldn't understand what action to perform. Would you like to book, reschedule, cancel, or look up an appointment?",
    )


def _apply_requested_change(session_id: str, message: str) -> Dict[str, Any]:
    session = _safe_session(session_id)
    lowered = message.lower()
    entities = _extract_with_agent(message, session)

    # If the caller supplies the replacement value directly, use it now.
    direct_updates = {
        key: value
        for key, value in entities.items()
        if key in {"date", "time", "customer_name", "phone_number", "appointment_id"}
        and value not in (None, "")
    }
    if direct_updates:
        direct_updates["awaiting_change"] = False
        session = _save(session_id, **direct_updates)
        missing = _missing_field(session)
        if missing:
            stage = FIELD_TO_STAGE[missing]
            _save(session_id, stage=stage)
            return _response(session_id, _prompt_for_stage(stage, _normalize_intent(session.get("intent"))))
        _save(session_id, stage=Stage.CONFIRM_FINAL)
        return _response(session_id, _confirmation_message(_safe_session(session_id)))

    keyword_map = {
        "date": ("date", "day"),
        "time": ("time",),
        "customer_name": ("name",),
        "phone_number": ("phone", "number", "contact"),
        "appointment_id": ("appointment id", "booking id", "id"),
    }
    for field, keywords in keyword_map.items():
        if any(keyword in lowered for keyword in keywords):
            stage = FIELD_TO_STAGE[field]
            _save(session_id, **{field: None, "awaiting_change": False, "stage": stage})
            return _response(session_id, _prompt_for_stage(stage, _normalize_intent(session.get("intent"))))

    return _response(
        session_id,
        "Please tell me what you want to change: the date, time, name, phone number, or appointment ID.",
    )

def _detect_direct_intent(message: str) -> Optional[Intent]:
    """Detect appointment intent reliably from natural speech."""

    lowered = _clean_text(message).lower()
    words = set(re.findall(r"[a-z]+", lowered))

    # Check specific actions first.
    if (
        "cancel" in words
        or "cancellation" in words
        or "delete" in words
    ):
        return Intent.CANCEL

    if (
        "reschedule" in words
        or "postpone" in words
        or (
            ("change" in words or "move" in words)
            and "appointment" in words
        )
    ):
        return Intent.RESCHEDULE

    if (
        "lookup" in words
        or (
            {"check", "appointment"}.issubset(words)
        )
        or (
            {"find", "appointment"}.issubset(words)
        )
        or (
            {"appointment", "status"}.issubset(words)
        )
    ):
        return Intent.LOOKUP

    # Accept many variations:
    # "book appointment"
    # "I want to book an appointment"
    # "I want book appointment"
    # "schedule one for me"
    if (
        "book" in words
        or "booking" in words
        or "schedule" in words
    ):
        return Intent.BOOK

    return None

def _is_required_detail_refusal(message: str) -> bool:
    """Detect a refusal even when speech-to-text adds extra filler words."""

    lowered = _clean_text(message).lower()
    normalized = re.sub(r"[^a-z0-9']+", " ", lowered).strip()
    tokens = set(re.findall(r"[a-z']+", normalized))

    exact_refusals = {
        "no",
        "nope",
        "nah",
        "no thanks",
        "no thank you",
        "skip it",
        "skip this",
        "leave it",
        "prefer not to say",
        "prefer not to share",
    }

    refusal_phrases = (
        "don't want",
        "dont want",
        "do not want",
        "won't give",
        "wont give",
        "will not give",
        "won't share",
        "wont share",
        "will not share",
        "not comfortable",
        "not giving",
        "cannot share",
        "can't share",
        "cant share",
        "cannot give",
        "can't give",
        "cant give",
        "i refuse",
        "i said no",
    )

    # A short response beginning with no/nope/nah is a refusal. Longer replies
    # such as "no, tomorrow" are not treated as refusals because they contain
    # an actionable replacement value.
    starts_with_no = bool(re.match(r"^(no|nope|nah)\b", normalized))
    short_negative = starts_with_no and len(normalized.split()) <= 5

    return (
        normalized in exact_refusals
        or short_negative
        or bool(tokens & {"refuse"})
        or any(phrase in normalized for phrase in refusal_phrases)
    )


def _requests_same_value(message: str, field: str) -> bool:
    """Return True for replies like 'same time' or 'keep the same date'."""

    normalized = re.sub(
        r"[^a-z0-9']+",
        " ",
        _clean_text(message).lower(),
    ).strip()

    same_markers = (
        "same",
        "keep it",
        "keep the",
        "do not change",
        "don't change",
        "dont change",
        "unchanged",
        "as it is",
        "current",
        "existing",
    )

    if not any(marker in normalized for marker in same_markers):
        return False

    # At a date/time collection stage, a plain "same" is unambiguous.
    return field in {"date", "time"}


def _required_field_label(stage: Stage) -> str:
    labels = {
        Stage.COLLECT_DATE: "appointment date",
        Stage.COLLECT_TIME: "appointment time",
        Stage.COLLECT_NAME: "full name",
        Stage.COLLECT_PHONE: "phone number",
        Stage.COLLECT_APPOINTMENT_ID: "appointment ID",
    }

    return labels.get(stage, "required information")


def handle_call(message: str, session_id: str, db: Session) -> Dict[str, Any]:
    """Public entry point used by the voice/chat routes."""

    message = _clean_text(message)
    session = _safe_session(session_id)
    stage = _normalize_stage(session.get("stage"))

    if not message:
        return _response(
            session_id,
            "I didn't catch that. Could you please repeat it?",
        )

    # On the first turn, greet only when the caller said a pure greeting.
    # Otherwise process the actionable first message immediately.
    if stage == Stage.GREETING:
        if _is_pure_greeting(message):
            _save(session_id, stage=Stage.COLLECT_INTENT)
            return _response(
                session_id,
                "Hello, Vaani this side. How may I help you?",
            )

        _save(session_id, stage=Stage.COLLECT_INTENT)
        session = _safe_session(session_id)
        stage = Stage.COLLECT_INTENT

    # Handle final confirmation before NLU so a plain yes/no is not lost.
    if stage == Stage.CONFIRM_FINAL:
        if session.get("awaiting_change"):
            return _apply_requested_change(session_id, message)

        decision = _classify_yes_no(message)

        if decision is True:
            _save(session_id, stage=Stage.EXECUTE)
            return _execute_action(session_id, db)

        if decision is False:
            _save(session_id, awaiting_change=True)
            return _response(
                session_id,
                "No problem. What would you like to change?",
            )

        return _response(
            session_id,
            "Please say yes to proceed or no to make a change.",
        )

    # A clear appointment command must never be consumed as a name, phone
    # number, date, or time. If the caller restarts with a command while the
    # session is collecting another field, begin that transaction cleanly.
    global_direct_intent = _detect_direct_intent(message)
    if global_direct_intent is not None and stage not in {
        Stage.CONFIRM_FINAL,
        Stage.EXECUTE,
        Stage.END,
    }:
        clear_session(session_id)
        session = _save(
            session_id,
            stage=Stage.COLLECT_INTENT,
            intent=global_direct_intent,
        )
        stage = Stage.COLLECT_INTENT

    if stage == Stage.END:
        lowered = message.lower()

        if lowered in {
            "no",
            "no thanks",
            "nothing",
            "that's all",
            "bye",
            "goodbye",
        }:
            clear_session(session_id)
            return {
                "status": "success",
                "end_call": True,
                "message": "Thank you for calling. Have a great day!",
                "session": {},
            }

        # Start another request in the same call.
        clear_session(session_id)
        _save(session_id, stage=Stage.COLLECT_INTENT)
        session = _safe_session(session_id)
        stage = Stage.COLLECT_INTENT

    required_field_stages = {
        Stage.COLLECT_DATE,
        Stage.COLLECT_TIME,
        Stage.COLLECT_NAME,
        Stage.COLLECT_PHONE,
        Stage.COLLECT_APPOINTMENT_ID,
    }

    # Do not create or confirm an appointment when required information is refused.
    # Keep the request on hold and end the voice call cleanly.
    if (
        stage in required_field_stages
        and _is_required_detail_refusal(message)
    ):
        field_label = _required_field_label(stage)
        session = _save(session_id, stage=stage)

        return {
            "status": "on_hold",
            "end_call": True,
            "appointment_id": None,
            "message": (
                f"I understand. Without your {field_label}, I cannot complete or confirm "
                "the appointment request. I have kept this request on hold due to "
                "insufficient information."
            ),
            "session": session,
        }

    # During slot collection, prioritize deterministic extraction for the
    # specific field Vaani asked for.
    stage_field = {
        Stage.COLLECT_DATE: "date",
        Stage.COLLECT_TIME: "time",
        Stage.COLLECT_NAME: "customer_name",
        Stage.COLLECT_PHONE: "phone_number",
        Stage.COLLECT_APPOINTMENT_ID: "appointment_id",
    }.get(stage)


    if stage_field:
        intent = _normalize_intent(session.get("intent"))

        # During rescheduling, "same date" or "same time" means reuse the
        # corresponding value from the existing appointment linked by phone.
        if (
            intent == Intent.RESCHEDULE
            and stage_field in {"date", "time"}
            and _requests_same_value(message, stage_field)
        ):
            phone_number = session.get("phone_number")
            existing = (
                _find_appointment_for_phone(db, phone_number)
                if phone_number
                else None
            )

            if not existing:
                return _response(
                    session_id,
                    "I couldn't find an active appointment linked to that phone number.",
                    status="not_found",
                    end_call=True,
                )

            if stage_field == "date":
                stage_value = _result_value(existing, "appointment_date", "date")
            else:
                stage_value = _result_value(existing, "appointment_time", "time")
        else:
            fallback = _fallback_extract(message)
            stage_value = fallback.get(stage_field)

        # Normalize replies such as "It's Aayan Pandit" to "Aayan Pandit".
        if stage_field == "customer_name":
            # Appointment commands such as "book an appointment" are actions,
            # never customer names.
            if _detect_direct_intent(message) is not None:
                stage_value = None
            else:
                stage_value = _extract_name_response(message)

        if stage_value not in (None, ""):
            session = _save(
                session_id,
                **{stage_field: stage_value},
            )
        else:
            # Never let the LLM invent a name or phone number from unrelated speech.
            # Ask for the same field again unless the caller explicitly refused it.
            return _response(
                session_id,
                _prompt_for_stage(stage, _normalize_intent(session.get("intent"))),
            )
    else:
        # Explicit phrases such as "book an appointment" should take
        # priority over the agent's intent extraction.
        direct_intent = _detect_direct_intent(message)

        if direct_intent is not None:
            session = _save(
                session_id,
                intent=direct_intent,
            )

        entities = _extract_with_agent(message, session)
        session = _merge_entities(
            session_id,
            session,
            entities,
        )

    intent = _normalize_intent(session.get("intent"))

    if intent is None:
        _save(session_id, stage=Stage.COLLECT_INTENT)
        return _response(
            session_id,
            (
                "I can help you book, reschedule, cancel, or look up "
                "an appointment. What would you like to do?"
            ),
        )

    missing = _missing_field(session)

    if missing:
        next_stage = FIELD_TO_STAGE[missing]
        _save(session_id, stage=next_stage)
        return _response(
            session_id,
            _prompt_for_stage(next_stage, intent),
        )

    if intent == Intent.LOOKUP:
        _save(session_id, stage=Stage.EXECUTE)
        return _execute_action(session_id, db)

    if intent in {Intent.BOOK, Intent.RESCHEDULE}:
        exclude_appointment_id = None

        if intent == Intent.RESCHEDULE:
            existing = _find_appointment_for_phone(
                db,
                session.get("phone_number"),
            )
            if existing:
                exclude_appointment_id = _result_value(
                    existing,
                    "id",
                    "appointment_id",
                )

        slot_error = _validate_requested_slot(
            session_id,
            session,
            db,
            exclude_appointment_id=exclude_appointment_id,
        )
        if slot_error:
            return slot_error

        session = _safe_session(session_id)

    _save(
        session_id,
        stage=Stage.CONFIRM_FINAL,
        awaiting_change=False,
    )

    return _response(
        session_id,
        _confirmation_message(_safe_session(session_id)),
    )