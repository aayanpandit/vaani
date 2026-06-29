class VaaniAgent:

    def process(self, message: str):

        text = message.lower()

        if any(word in text for word in [
            "appointment",
            "book",
            "schedule",
            "meeting",
        ]):
            return {
                "message": message,
                "intent": "book_appointment",
                "tool": "appointment_service",
            }

        return {
            "message": message,
            "intent": "unknown",
            "tool": None,
        }