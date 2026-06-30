def detect_intent(text: str) -> str:
    text = text.lower()

    if any(word in text for word in [
        "cancel",
        "delete",
        "remove",
    ]):
        return "cancel_appointment"

    if any(word in text for word in [
        "appointment",
        "book",
        "schedule",
        "meeting",
        "consultation",
        "call",
    ]):
        return "book_appointment"
    
    if any(word in text for word in [
       "reschedule",
       "change",
       "move",
       "postpone",
       "shift",
]):
       return "reschedule_appointment"

    return "unknown"