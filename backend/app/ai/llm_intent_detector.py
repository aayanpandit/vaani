from app.llm.groq_client import ask_groq


def detect_intent_with_llm(message: str) -> str:
    prompt = f"""
You are an intent classification system for an AI receptionist.

Classify the user's intent into exactly one of these labels:

book_appointment
- cancel_appointment
- reschedule_appointment
- unknown

User message:
"{message}"

Return only the label. Do not explain.
"""

    intent = ask_groq(prompt).strip().lower()

    if intent not in [
    "book_appointment",
    "cancel_appointment",
    "reschedule_appointment",
    "unknown",
]:
      return "unknown"
    
    
    return intent