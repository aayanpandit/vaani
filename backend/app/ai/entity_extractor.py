import re


def extract_entities(text: str) -> dict:
    text = text.lower()
    entities = {}

    if "tomorrow" in text:
        entities["date"] = "tomorrow"
    elif "today" in text:
        entities["date"] = "today"

    time_match = re.search(r"\b\d{1,2}\s?(am|pm)\b", text)

    if time_match:
        entities["time"] = time_match.group().upper()

    id_match = re.search(r"\b\d+\b", text)

    if id_match:
        entities["appointment_id"] = id_match.group()

    return entities