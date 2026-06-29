from app.ai.llm_entity_extractor import extract_entities_with_llm

result = extract_entities_with_llm(
    "Can you schedule a call tomorrow at 5 PM?"
)

print(result)