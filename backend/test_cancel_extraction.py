from app.ai.llm_entity_extractor import extract_entities_with_llm

result = extract_entities_with_llm(
    "Cancel appointment 8"
)

print(result)