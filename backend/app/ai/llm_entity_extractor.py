import json
import re

from app.llm.groq_client import ask_groq


def extract_entities_with_llm(message: str) -> dict:
    prompt = f"""
You are an entity extraction system for an AI receptionist.

Extract appointment-related information from the user's message.

Return ONLY valid JSON.
No explanation.
No markdown.
No extra text.

If a value is not present, return an empty string.

Required JSON format:

{{
    "date": "",
    "time": "",
    "appointment_id": "",
    "customer_name": "",
    "phone_number": ""
}}

Examples:

User:
"Book an appointment tomorrow at 5 PM. My name is Aayan Pandit and my phone number is 7415048185"

Output:
{{
    "date": "tomorrow",
    "time": "5 PM",
    "appointment_id": "",
    "customer_name": "Aayan Pandit",
    "phone_number": "7415048185"
}}

User:
"Cancel appointment 12"

Output:
{{
    "date": "",
    "time": "",
    "appointment_id": "12",
    "customer_name": "",
    "phone_number": ""
}}

User message:
"{message}"
"""

    response = ask_groq(prompt)

    response = response.replace("```json", "")
    response = response.replace("```", "")
    response = response.strip()

    json_match = re.search(r"\{.*\}", response, re.DOTALL)

    if not json_match:
        print("LLM raw response:", response)
        return {
            "date": "",
            "time": "",
            "appointment_id": "",
            "customer_name": "",
            "phone_number": "",
        }

    try:
        parsed = json.loads(json_match.group())

        return {
            "date": parsed.get("date", ""),
            "time": parsed.get("time", ""),
            "appointment_id": parsed.get("appointment_id", ""),
            "customer_name": parsed.get("customer_name", ""),
            "phone_number": parsed.get("phone_number", ""),
        }

    except Exception as e:
        print("JSON parse error:", e)
        print("LLM raw response:", response)

        return {
            "date": "",
            "time": "",
            "appointment_id": "",
            "customer_name": "",
            "phone_number": "",
        }