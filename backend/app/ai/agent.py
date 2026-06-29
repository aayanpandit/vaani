class VaaniAgent:
    def process(self, message: str):
        return {
            "message": message,
            "intent": "unknown",
            "tool": None,
        }