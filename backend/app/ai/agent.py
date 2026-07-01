from app.ai.llm_intent_detector import detect_intent_with_llm
from app.ai.entity_extractor import extract_entities
from app.ai.tool_selector import select_tool
from app.ai.llm_entity_extractor import extract_entities_with_llm


class VaaniAgent:

    def process(self, message: str):
        intent = detect_intent_with_llm(message)

        try:
            llm_entities = extract_entities_with_llm(message)
        except Exception:
            llm_entities = {}

        regex_entities = extract_entities(message)

        entities = {
            **regex_entities,
            **llm_entities,
        }

        # Ensure all expected fields always exist
        entities.setdefault("date", None)
        entities.setdefault("time", None)
        entities.setdefault("appointment_id", None)
        entities.setdefault("customer_name", None)
        entities.setdefault("phone_number", None)

        tool = select_tool(intent)

        return {
            "message": message,
            "intent": intent,
            "tool": tool,
            "entities": entities,
        }