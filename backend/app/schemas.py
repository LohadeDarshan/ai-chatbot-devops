from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., examples=["demo-session-1"])
    message: str = Field(..., min_length=1, max_length=2000, examples=["Hello, who are you?"])


class ChatResponse(BaseModel):
    session_id: str
    user_message: str
    bot_response: str
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryItem(BaseModel):
    user_message: str
    bot_response: str
    created_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    database: str
    model_backend: str
