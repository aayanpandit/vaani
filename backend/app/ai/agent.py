import re


class VaaniAgent:

    def process(self, message: str):

        text = message.lower()

        intent = "unknown"
        tool = None
        entities = {}

        if any(word in text for word in [
            "appointment",
            "book",
            "schedule",
            "meeting",
        ]):
            intent = "book_appointment"
            tool = "appointment_service"

        if "tomorrow" in text:
            entities["date"] = "tomorrow"
        elif "today" in text:
            entities["date"] = "today"

        time_match = re.search(r"\b\d{1,2}\s?(am|pm)\b", text)

        if time_match:
            entities["time"] = time_match.group().upper()

        return {
            "message": message,
            "intent": intent,
            "tool": tool,
            "entities": entities,
        }