from app.ai.llm_intent_detector import detect_intent_with_llm
from app.ai.entity_extractor import extract_entities
from app.ai.tool_selector import select_tool


class VaaniAgent:

    def process(self, message: str):

        intent = detect_intent_with_llm(message)
        entities = extract_entities(message)
        tool = select_tool(intent)

        return {
            "message": message,
            "intent": intent,
            "tool": tool,
            "entities": entities,
        }