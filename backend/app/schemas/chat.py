from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str
    intent: str
    tool: str | None = None
    entities: dict = {}