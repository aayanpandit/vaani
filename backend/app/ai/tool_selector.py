def select_tool(intent: str) -> str | None:
    if intent == "book_appointment":
        return "appointment_service"

    return None