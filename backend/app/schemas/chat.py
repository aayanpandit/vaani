from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    customer_name: str | None = None
    phone_number: str | None = None


class ChatResponse(BaseModel):
    message: str
    intent: str
    tool: str | None = None
    entities: dict = {}