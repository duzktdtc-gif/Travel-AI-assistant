from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.llm import get_llm
from app.agents.prompts import (
    FINALIZER_PROMPT,
    ITINERARY_PROMPT,
    PREFERENCE_EXTRACTION_PROMPT,
    REFLECTION_PROMPT,
    SUPERVISOR_PROMPT,
)
from app.agents.state import TravelState
from app.agents.utils import compact_dict, get_last_human_text, safe_json_loads, simple_preference_fallback
from app.tools.serpapi_tools import search_flights, search_hotels
from app.tools.tavily_search import search_web
from app.tools.weather import get_weather_forecast


def _steps(state: TravelState) -> list[str]:
    return list(state.get("steps_done") or [])


def _mark_done(state: TravelState, step: str) -> list[str]:
    steps = _steps(state)
    if step not in steps:
        steps.append(step)
    return steps


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def extract_preferences_node(state: TravelState) -> dict:
    """Extract structured travel preferences from conversation."""
    messages = state.get("messages", [])
    last_text = get_last_human_text(messages)
    llm = get_llm(temperature=0)

    if llm:
        response = llm.invoke(
            [
                SystemMessage(content=PREFERENCE_EXTRACTION_PROMPT),
                HumanMessage(content=f"Conversation messages: {messages}\nLatest request: {last_text}"),
            ]
        )
        extracted = safe_json_loads(_as_text(response.content))
    else:
        extracted = simple_preference_fallback(last_text)

    extracted = compact_dict(extracted)

    # Merge old state with new extraction. New non-empty values win.
    update = {
        "origin": state.get("origin", ""),
        "destination": state.get("destination", ""),
        "start_date": state.get("start_date", ""),
        "end_date": state.get("end_date", ""),
        "budget": state.get("budget", ""),
        "travelers": state.get("travelers", 1),
        "interests": state.get("interests", []),
        "notes": state.get("notes", ""),
    }
    previous_trip_fields = {
        key: update.get(key)
        for key in ["origin", "destination", "start_date", "end_date", "budget", "travelers", "interests", "notes"]
    }
    update.update(extracted)

    # If a follow-up message changes the trip requirements, force the supervisor to re-run agents.
    current_trip_fields = {
        key: update.get(key)
        for key in ["origin", "destination", "start_date", "end_date", "budget", "travelers", "interests", "notes"]
    }
    if state.get("steps_done") and previous_trip_fields != current_trip_fields:
        update.update(
            {
                "steps_done": [],
                "approval": {},
                "research": [],
                "weather": [],
                "flights": [],
                "hotels": [],
                "itinerary": "",
                "reflection": "",
                "final_answer": "",
            }
        )
    return update


def supervisor_node(state: TravelState) -> dict:
    """Custom LangGraph supervisor with an LLM-readable plan and deterministic safety guards."""
    steps = _steps(state)
    approval = state.get("approval") or {}

    # If the user rejected the plan, clear approval and force itinerary + reflection again.
    if approval and approval.get("approved") is False:
        replanning_steps = [s for s in steps if s not in {"itinerary_agent", "reflection_agent", "approval_node"}]
        feedback = approval.get("feedback", "")
        notes = (state.get("notes") or "").strip()
        if feedback and feedback not in notes:
            notes = (notes + f"\nHuman feedback for replanning: {feedback}").strip()
        return {
            "next": "itinerary_agent",
            "steps_done": replanning_steps,
            "approval": {},
            "notes": notes,
        }

    if not state.get("destination"):
        return {"next": "finalizer"}

    # Guard rails to ensure every specialist runs at least once.
    required_order = [
        ("research_agent", "research_agent"),
        ("weather_agent", "weather_agent"),
        ("flight_hotel_agent", "flight_hotel_agent"),
        ("itinerary_agent", "itinerary_agent"),
        ("reflection_agent", "reflection_agent"),
    ]
    for step_name, node_name in required_order:
        if step_name not in steps:
            return {"next": node_name}

    if not approval:
        return {"next": "approval_node"}

    if approval.get("approved") is True:
        return {"next": "finalizer"}

    # Optional LLM dynamic routing after the deterministic checks.
    llm = get_llm(temperature=0)
    if llm:
        routing_prompt = f"""
{SUPERVISOR_PROMPT}

Current compact state:
- destination: {state.get('destination')}
- dates: {state.get('start_date')} to {state.get('end_date')}
- done: {steps}
- approval: {approval}

Return only the next step name.
"""
        try:
            response = llm.invoke([HumanMessage(content=routing_prompt)])
            decision = _as_text(response.content).strip().split()[0]
            allowed = {
                "research_agent",
                "weather_agent",
                "flight_hotel_agent",
                "itinerary_agent",
                "reflection_agent",
                "approval_node",
                "finalizer",
            }
            if decision in allowed:
                return {"next": decision}
        except Exception:  # noqa: BLE001
            pass

    return {"next": "finalizer"}


def research_agent_node(state: TravelState) -> dict:
    destination = state.get("destination", "")
    interests = ", ".join(state.get("interests") or [])
    query = (
        f"Latest travel guide for {destination}. Attractions, neighborhoods, transport, safety, "
        f"local food, hidden gems, and tips for interests: {interests}."
    )
    raw_results = search_web(query=query, max_results=5)

    llm = get_llm(temperature=0.2)
    if llm:
        prompt = f"""
Summarize these real-time travel search results for a trip to {destination}.
Return concise bullet points with source titles when useful.

Results:
{raw_results}
"""
        try:
            summary = _as_text(llm.invoke([HumanMessage(content=prompt)]).content)
            raw_results.insert(0, {"title": "AI research summary", "url": "", "content": summary})
        except Exception as exc:  # noqa: BLE001
            raw_results.insert(0, {"title": "AI summary error", "url": "", "content": str(exc)})

    return {"research": raw_results, "steps_done": _mark_done(state, "research_agent")}


def weather_agent_node(state: TravelState) -> dict:
    destination = state.get("destination", "")
    forecast = get_weather_forecast(destination)
    return {"weather": forecast, "steps_done": _mark_done(state, "weather_agent")}


def flight_hotel_agent_node(state: TravelState) -> dict:
    origin = state.get("origin", "")
    destination = state.get("destination", "")
    start_date = state.get("start_date", "")
    end_date = state.get("end_date", "")
    travelers = int(state.get("travelers") or 1)

    flights = search_flights(origin, destination, start_date, end_date)
    hotels = search_hotels(destination, start_date, end_date, travelers)
    return {
        "flights": flights,
        "hotels": hotels,
        "steps_done": _mark_done(state, "flight_hotel_agent"),
    }


def itinerary_agent_node(state: TravelState) -> dict:
    destination = state.get("destination", "")
    if not destination:
        return {
            "itinerary": "",
            "steps_done": _mark_done(state, "itinerary_agent"),
        }

    llm = get_llm(temperature=0.35)
    prompt = prompt = f"""
Bạn là Travel AI Assistant. Hãy lập lịch trình du lịch theo đúng yêu cầu của người dùng.

YÊU CẦU GỐC:
{get_last_human_text(state.get("messages", []))}

THÔNG TIN ĐÃ TRÍCH XUẤT:
- Điểm đi: {state.get("origin") or "Không rõ"}
- Điểm đến: {state.get("destination") or "Không rõ"}
- Ngày bắt đầu: {state.get("start_date") or "Không rõ"}
- Ngày kết thúc: {state.get("end_date") or "Không rõ"}
- Ngân sách: {state.get("budget") or "Không rõ"}
- Số người: {state.get("travelers") or "Không rõ"}
- Sở thích: {state.get("interests") or "Không rõ"}

DỮ LIỆU THAM KHẢO:
Research:
{state.get("research")}

Weather:
{state.get("weather")}

Flights:
{state.get("flights")}

Hotels:
{state.get("hotels")}

QUY TẮC BẮT BUỘC:
1. Chỉ trả lời đúng bài toán lập lịch trình du lịch.
2. Không viết theo kiểu portfolio, case study, thuyết trình hội đồng, demo sinh viên nếu người dùng không yêu cầu.
3. Không tự thêm bối cảnh nghề nghiệp, học thuật, tuyển dụng.
4. Nếu người dùng hỏi ngắn, trả lời ngắn gọn, thực tế.
5. Nếu có ngân sách cụ thể, tổng chi phí ước tính không được vượt ngân sách.
6. Nếu ngân sách là VND/đồng, dùng đơn vị VNĐ.
7. Không dùng dữ liệu năm cũ như 2024 nếu người dùng không hỏi.
8. Không nhắc vé máy bay/khách sạn nếu lịch trình chỉ là 1 ngày trong cùng thành phố.
9. Câu trả lời nên có:
   - Tổng quan ngắn
   - Lịch trình theo giờ
   - Bảng ngân sách
   - Lưu ý di chuyển
   - Phương án dự phòng nếu mưa
10. Trả lời bằng tiếng Việt tự nhiên.

Hãy tạo lịch trình cuối cùng.
"""
    if llm:
        try:
            itinerary = _as_text(llm.invoke([HumanMessage(content=prompt)]).content)
        except Exception as exc:  # noqa: BLE001
            itinerary = f"Không thể gọi Gemini để tạo lịch trình: {exc}"
    else:
        itinerary = f"""
## Demo itinerary for {destination}

Gemini is not configured, so this is a fallback itinerary.

### Day 1
- Arrive from {state.get('origin') or 'your origin'}.
- Check in near the city center.
- Light walk, local dinner, and early rest.

### Day 2
- Visit the most iconic attractions.
- Add activities matching your interests: {', '.join(state.get('interests') or ['general sightseeing'])}.

### Day 3
- Explore local neighborhoods, food markets, and museums.
- Adjust the plan using live research/weather once API keys are configured.

### Flight and hotel notes
- Flights: {state.get('flights') or []}
- Hotels: {state.get('hotels') or []}
""".strip()

    return {"itinerary": itinerary, "steps_done": _mark_done(state, "itinerary_agent")}


def reflection_agent_node(state: TravelState) -> dict:
    """
    Reflection Agent chỉ đánh giá nội bộ.
    Không nối self-reflection vào itinerary để tránh lộ ra câu trả lời cuối.
    """
    itinerary = state.get("itinerary", "")

    reflection = """
### Self-reflection before approval

- Đã kiểm tra lịch trình theo ngân sách, thời gian, địa điểm và khả năng di chuyển.
- Nếu có ngân sách cụ thể, tổng chi phí phải nhỏ hơn hoặc bằng ngân sách.
- Nếu thiếu dữ liệu API thời tiết/chuyến bay/khách sạn, cần ghi rõ dữ liệu chỉ là ước tính.
- Nếu lịch trình quá dày, cần thêm thời gian nghỉ hoặc phương án dự phòng.
""".strip()

    return {
        "reflection": reflection,
        "itinerary": itinerary,
        "steps_done": _mark_done(state, "reflection_agent"),
    }

def approval_node(state: TravelState) -> dict:
    """Human-in-the-loop checkpoint. The graph pauses here until FastAPI resumes it."""
    payload = {
        "type": "travel_plan_approval",
        "question": "Bạn có muốn xác nhận kế hoạch du lịch này không? Nếu chưa, hãy nhập góp ý để agent lập lại.",
        "itinerary": state.get("itinerary", ""),
        "flights": state.get("flights", []),
        "hotels": state.get("hotels", []),
        "weather": state.get("weather", []),
    }
    human_response = interrupt(payload)

    if isinstance(human_response, dict):
        approved = bool(human_response.get("approved", False))
        feedback = human_response.get("feedback", "") or ""
    else:
        approved = str(human_response).lower() in {"yes", "y", "true", "approved", "ok", "đồng ý"}
        feedback = "" if approved else str(human_response)

    return {
        "approval": {"approved": approved, "feedback": feedback},
        "steps_done": _mark_done(state, "approval_node"),
    }


def finalizer_node(state: TravelState) -> dict:
    """
    Finalizer không gọi LLM lại.
    Nếu user approve, trả về itinerary cuối cùng.
    """
    itinerary = state.get("itinerary") or ""

    if not itinerary:
        answer = "Chưa có lịch trình để hiển thị."
    else:
        answer = itinerary

    return {
        "messages": [AIMessage(content=answer)],
        "final_answer": answer,
    }

def route_from_supervisor(state: TravelState) -> str:
    return state.get("next", "finalizer")


def build_graph():
    builder = StateGraph(TravelState)

    builder.add_node("extract_preferences", extract_preferences_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("research_agent", research_agent_node)
    builder.add_node("weather_agent", weather_agent_node)
    builder.add_node("flight_hotel_agent", flight_hotel_agent_node)
    builder.add_node("itinerary_agent", itinerary_agent_node)
    builder.add_node("reflection_agent", reflection_agent_node)
    builder.add_node("approval_node", approval_node)
    builder.add_node("finalizer", finalizer_node)

    builder.add_edge(START, "extract_preferences")
    builder.add_edge("extract_preferences", "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "research_agent": "research_agent",
            "weather_agent": "weather_agent",
            "flight_hotel_agent": "flight_hotel_agent",
            "itinerary_agent": "itinerary_agent",
            "reflection_agent": "reflection_agent",
            "approval_node": "approval_node",
            "finalizer": "finalizer",
        },
    )
    builder.add_edge("research_agent", "supervisor")
    builder.add_edge("weather_agent", "supervisor")
    builder.add_edge("flight_hotel_agent", "supervisor")
    builder.add_edge("itinerary_agent", "supervisor")
    builder.add_edge("reflection_agent", "supervisor")
    builder.add_edge("approval_node", "supervisor")
    builder.add_edge("finalizer", END)

    return builder.compile(checkpointer=MemorySaver())


travel_graph = build_graph()
