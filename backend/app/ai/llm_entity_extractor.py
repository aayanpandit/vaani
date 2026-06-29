import json
import re

from app.llm.groq_client import ask_groq


def extract_entities_with_llm(message: str) -> dict:
    prompt = f"""
You are an entity extraction system for an AI receptionist.

Extract appointment booking details from the user message.

Return ONLY valid JSON.
No explanation.
No markdown.

Required JSON format:
{{
  "date": "",
  "time": ""
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
        return {}

    try:
        return json.loads(json_match.group())
    except Exception as e:
        print("JSON parse error:", e)
        print("LLM raw response:", response)
        return {}