from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str | None = None


class ResumeRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    approved: bool
    feedback: str | None = ""


class ChatResponse(BaseModel):
    status: str
    thread_id: str
    answer: str | None = None
    interrupt: dict | None = None
