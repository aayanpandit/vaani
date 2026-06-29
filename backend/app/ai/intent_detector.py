def detect_intent(text: str) -> str:
    text = text.lower()

    if any(word in text for word in [
        "appointment",
        "book",
        "schedule",
        "meeting",
    ]):
        return "book_appointment"

    return "unknown"