from app.ai.agent import VaaniAgent
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import (
    create_appointment,
    get_appointment,
    cancel_appointment,
    reschedule_appointment,
    update_calendar_event_id,
)
from app.integrations.google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    update_calendar_event,
)
from app.memory.session_memory import get_session, update_session, clear_session


agent = VaaniAgent()


def is_yes(message: str):
    msg = message.lower()

    yes_words = [
        "yes",
        "yeah",
        "yup",
        "correct",
        "confirm",
        "yes confirm",
        "proceed",
        "book it",
        "go ahead",
        "sure",
        "okay",
        "ok"
    ]

    return any(word in msg for word in yes_words)


def is_no(message: str) -> bool:
    message = message.lower().strip()
    return message in [
        "no", "nope", "wrong", "incorrect",
        "not correct", "cancel", "don't", "do not",
    ]


def correct_intent_from_message(message: str, intent: str):
    message_lower = message.lower()

    if "cancel" in message_lower:
        return "cancel_appointment"

    if any(x in message_lower for x in ["reschedule", "change appointment", "shift appointment"]):
        return "reschedule_appointment"

    if any(x in message_lower for x in ["status", "details", "check appointment"]):
        return "get_appointment"

    if any(x in message_lower for x in ["book", "schedule", "new appointment", "want appointment", "need appointment", "appointment"]):
        return "book_appointment"

    return intent


def ask_next_missing_field(session_id: str):
    session = get_session(session_id)
    intent = session.get("intent")

    if intent == "book_appointment":
        if not session.get("date"):
            update_session(session_id, {"stage": "collect_date"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Sure, I can help you book an appointment. Which date would you prefer?",
                "session": get_session(session_id),
            }

        if not session.get("time"):
            update_session(session_id, {"stage": "collect_time"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "At what time would you like the appointment?",
                "session": get_session(session_id),
            }

        if not session.get("customer_name"):
            update_session(session_id, {"stage": "collect_name"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "May I have your full name?",
                "session": get_session(session_id),
            }

        if not session.get("phone_number"):
            update_session(session_id, {"stage": "collect_phone"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Could I have your phone number?",
                "session": get_session(session_id),
            }

        update_session(session_id, {"stage": "confirm_identity"})
        session = get_session(session_id)

        return {
            "status": "in_progress",
            "end_call": False,
            "message": f"Just to confirm, your name is {session['customer_name']} and your phone number is {session['phone_number']}. Is that correct?",
            "session": session,
        }

    if intent == "reschedule_appointment":
        if not session.get("appointment_id"):
            update_session(session_id, {"stage": "collect_appointment_id"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Sure, I can help you reschedule. Could you share your appointment ID with me?",
                "session": get_session(session_id),
            }

        if not session.get("date"):
            update_session(session_id, {"stage": "collect_date"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "What new date would you like for the appointment?",
                "session": get_session(session_id),
            }

        if not session.get("time"):
            update_session(session_id, {"stage": "collect_time"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "What new time would you like for the appointment?",
                "session": get_session(session_id),
            }

        update_session(session_id, {"stage": "confirm_final"})
        session = get_session(session_id)

        return {
            "status": "in_progress",
            "end_call": False,
            "message": f"Just to confirm, you want to reschedule appointment ID {session['appointment_id']} to {session['date']} at {session['time']}. Should I proceed?",
            "session": session,
        }

    if intent == "cancel_appointment":
        if not session.get("appointment_id"):
            update_session(session_id, {"stage": "collect_appointment_id"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Sure, I can help you cancel an appointment. Please tell me your appointment ID.",
                "session": get_session(session_id),
            }

        update_session(session_id, {"stage": "confirm_final"})
        session = get_session(session_id)

        return {
            "status": "in_progress",
            "end_call": False,
            "message": f"Just to confirm, you want to cancel appointment ID {session['appointment_id']}. Should I proceed?",
            "session": session,
        }

    if intent == "get_appointment":
        if not session.get("appointment_id"):
            update_session(session_id, {"stage": "collect_appointment_id"})
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Sure. Please tell me your appointment ID.",
                "session": get_session(session_id),
            }

        update_session(session_id, {"stage": "execute"})
        return None

    return {
        "status": "in_progress",
        "end_call": False,
        "message": "Sure. Would you like to book, reschedule, cancel, or check an appointment?",
        "session": session,
    }


def handle_call(message: str, session_id: str, db):
    session = get_session(session_id)

    if not session:
        session = {}

    stage = session.get("stage", "greeting")

    if stage == "greeting":
        update_session(session_id, {"stage": "collect_intent"})

        return {
            "status": "in_progress",
            "end_call": False,
            "message": "Hello, Vaani this side! How may I help you?",
            "session": get_session(session_id),
        }

    agent_response = agent.process(message)

    print("\n========== DEBUG ==========")
    print("MESSAGE:", message)
    print("AGENT RESPONSE:", agent_response)
    print("===========================\n")

    intent = agent_response.get("intent")
    entities = agent_response.get("entities", {})

    corrected_intent = correct_intent_from_message(message, intent)

# If user is only giving missing details like "at 4 pm",
# do not overwrite the previous intent stored in session.
    if session.get("intent") and corrected_intent in ["unknown", "get_appointment"]:
      corrected_intent = session.get("intent")
    update_data = {
        "intent": corrected_intent if corrected_intent != "unknown" else session.get("intent"),
        "date": entities.get("date") or session.get("date"),
        "time": entities.get("time") or session.get("time"),
        "appointment_id": entities.get("appointment_id") or session.get("appointment_id"),
        "customer_name": entities.get("customer_name") or session.get("customer_name"),
        "phone_number": entities.get("phone_number") or session.get("phone_number"),
        "stage": stage,
    }

    session = update_session(session_id, update_data)

    if stage == "collect_intent":
        if not session.get("intent"):
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Sure. Would you like to book, reschedule, cancel, or check an appointment?",
                "session": session,
            }

        next_response = ask_next_missing_field(session_id)
        return execute_action(session_id, db) if next_response is None else next_response

    if stage == "collect_appointment_id":
        if not session.get("appointment_id"):
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Please provide your appointment ID.",
                "session": session,
            }

        next_response = ask_next_missing_field(session_id)
        return execute_action(session_id, db) if next_response is None else next_response

    if stage == "collect_date":
        if not session.get("date"):
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Please tell me the date for the appointment.",
                "session": session,
            }

        next_response = ask_next_missing_field(session_id)
        return execute_action(session_id, db) if next_response is None else next_response

    if stage == "collect_time":
        if not session.get("time"):
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Please tell me the time for the appointment.",
                "session": session,
            }

        next_response = ask_next_missing_field(session_id)
        return execute_action(session_id, db) if next_response is None else next_response

    if stage == "collect_name":
        if not session.get("customer_name"):
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Please tell me your full name.",
                "session": session,
            }

        next_response = ask_next_missing_field(session_id)
        return execute_action(session_id, db) if next_response is None else next_response

    if stage == "collect_phone":
        if not session.get("phone_number"):
            return {
                "status": "in_progress",
                "end_call": False,
                "message": "Could I have your phone number?",
                "session": session,
            }

        next_response = ask_next_missing_field(session_id)
        return execute_action(session_id, db) if next_response is None else next_response

    update_session(session_id, {"stage": "confirm_final"})
    session = get_session(session_id)

    return {
    "status": "in_progress",
    "end_call": False,
    "message": (
        f"Let me confirm. "
        f"You would like an appointment on "
        f"{session['date']} at {session['time']} "
        f"under the name {session['customer_name']} "
        f"with phone number {session['phone_number']}. "
        f"Should I book it?"
    ),
    "session": session,
}


def execute_action(session_id: str, db):
    session = get_session(session_id)
    intent = session.get("intent")

    if intent == "book_appointment":
        appointment = AppointmentCreate(
            customer_name=session["customer_name"],
            phone_number=session["phone_number"],
            appointment_time=f"{session['date']} {session['time']}",
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

        clear_session(session_id)

        return {
            "status": "success",
            "end_call": True,
            "message": f"Your appointment has been booked successfully for {appointment.appointment_time}. Thank you for calling Vaani. Have a great day!",
            "appointment_id": created_appointment.id,
            "calendar_event_link": calendar_event.get("htmlLink"),
        }

    if intent == "cancel_appointment":
        appointment_id = int(session["appointment_id"])
        appointment = get_appointment(db, appointment_id)

        if not appointment:
            clear_session(session_id)
            return {
                "status": "error",
                "end_call": True,
                "message": f"I could not find any appointment with ID {appointment_id}. Thank you for calling Vaani.",
            }

        if appointment.calendar_event_id:
            delete_calendar_event(appointment.calendar_event_id)

        cancel_appointment(db, appointment_id)
        clear_session(session_id)

        return {
            "status": "success",
            "end_call": True,
            "message": f"Appointment ID {appointment_id} has been cancelled successfully. Thank you for calling Vaani. Have a great day!",
        }

    if intent == "reschedule_appointment":
        appointment_id = int(session["appointment_id"])
        appointment = get_appointment(db, appointment_id)

        if not appointment:
            clear_session(session_id)
            return {
                "status": "error",
                "end_call": True,
                "message": f"I could not find any appointment with ID {appointment_id}. Thank you for calling Vaani.",
            }

        new_datetime = f"{session['date']} {session['time']}"

        if appointment.calendar_event_id:
            update_calendar_event(
                appointment.calendar_event_id,
                new_datetime,
            )

        reschedule_appointment(db, appointment_id, new_datetime)
        clear_session(session_id)

        return {
            "status": "success",
            "end_call": True,
            "message": f"Appointment ID {appointment_id} has been rescheduled to {new_datetime}. Thank you for calling Vaani. Have a great day!",
        }

    if intent == "get_appointment":
        appointment_id = int(session["appointment_id"])
        appointment = get_appointment(db, appointment_id)

        clear_session(session_id)

        if not appointment:
            return {
                "status": "error",
                "end_call": True,
                "message": f"I could not find any appointment with ID {appointment_id}. Thank you for calling Vaani.",
            }

        return {
            "status": "success",
            "end_call": True,
            "message": f"Appointment ID {appointment.id} is booked for {appointment.appointment_time} under the name {appointment.customer_name}. Thank you for calling Vaani.",
            "appointment": {
                "id": appointment.id,
                "customer_name": appointment.customer_name,
                "phone_number": appointment.phone_number,
                "appointment_time": appointment.appointment_time,
                "status": appointment.status,
            },
        }

    clear_session(session_id)

    return {
        "status": "error",
        "end_call": True,
        "message": "Sorry, I could not complete the request. Thank you for calling Vaani.",
    }