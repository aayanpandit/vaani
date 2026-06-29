from app.llm.groq_client import ask_groq

response = ask_groq(
    "What is Artificial Intelligence in one sentence?"
)

print(response)