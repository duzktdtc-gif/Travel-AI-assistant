from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from app.agents.graph import travel_graph
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, ResumeRequest

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _get_state_values(config: dict) -> dict:
    """
    LangGraph sometimes stores the useful state in the checkpointer
    when interrupt/human-in-the-loop is used.
    """
    try:
        snapshot = travel_graph.get_state(config)
        if snapshot and isinstance(snapshot.values, dict):
            return snapshot.values
    except Exception:
        pass
    return {}


def _ensure_result_dict(result, config: dict) -> dict:
    if isinstance(result, dict) and result:
        return result

    state_values = _get_state_values(config)
    if state_values:
        return state_values

    return {}


def _extract_interrupt(result: dict) -> dict | None:
    if not isinstance(result, dict):
        return None

    interrupts = result.get("__interrupt__")
    if interrupts:
        first = interrupts[0] if isinstance(interrupts, (list, tuple)) else interrupts
        value = getattr(first, "value", None)
        if value is None:
            value = first
        return value if isinstance(value, dict) else {"value": value}

    # Fallback: nếu có itinerary nhưng chưa approval/final answer,
    # coi như đang chờ người dùng xác nhận.
    itinerary = result.get("itinerary")
    approval = result.get("approval") or {}
    final_answer = result.get("final_answer")

    if itinerary and not approval and not final_answer:
        return {
            "type": "travel_plan_approval",
            "question": "Bạn có muốn xác nhận kế hoạch du lịch này không? Nếu chưa, hãy nhập góp ý để agent lập lại.",
            "itinerary": itinerary,
            "flights": result.get("flights", []),
            "hotels": result.get("hotels", []),
            "weather": result.get("weather", []),
        }

    return None


def _latest_ai_text(result: dict) -> str:
    if not isinstance(result, dict):
        return ""

    if result.get("final_answer"):
        return str(result["final_answer"])

    messages = result.get("messages") or []
    for message in reversed(messages):
        if isinstance(message, AIMessage) or getattr(message, "type", None) == "ai":
            return str(message.content)

    # Fallback để không bị answer rỗng
    if result.get("itinerary"):
        return str(result["itinerary"])

    return ""


@app.get("/health")
def health():
    return {"ok": True, "app": settings.app_name}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    thread_id = payload.thread_id or str(uuid4())
    config = _thread_config(thread_id)

    result = travel_graph.invoke(
        {"messages": [HumanMessage(content=payload.message)]},
        config=config,
    )

    result = _ensure_result_dict(result, config)

    interrupt_payload = _extract_interrupt(result)
    if interrupt_payload:
        return ChatResponse(
            status="requires_approval",
            thread_id=thread_id,
            interrupt=interrupt_payload,
            answer=interrupt_payload.get("itinerary", ""),
        )

    return ChatResponse(
        status="completed",
        thread_id=thread_id,
        answer=_latest_ai_text(result),
    )


@app.post("/api/chat/resume", response_model=ChatResponse)
def resume(payload: ResumeRequest):
    config = _thread_config(payload.thread_id)

    result = travel_graph.invoke(
        Command(resume={
            "approved": payload.approved,
            "feedback": payload.feedback or "",
        }),
        config=config,
    )

    result = _ensure_result_dict(result, config)

    interrupt_payload = _extract_interrupt(result)
    if interrupt_payload:
        return ChatResponse(
            status="requires_approval",
            thread_id=payload.thread_id,
            interrupt=interrupt_payload,
            answer=interrupt_payload.get("itinerary", ""),
        )

    return ChatResponse(
        status="completed",
        thread_id=payload.thread_id,
        answer=_latest_ai_text(result),
    )