from typing import Any, Annotated, Literal
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TravelState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]

    # Extracted trip preferences
    origin: str
    destination: str
    start_date: str
    end_date: str
    budget: str
    travelers: int
    interests: list[str]
    notes: str

    # Agent outputs
    research: list[dict[str, Any]]
    weather: list[dict[str, Any]]
    flights: list[dict[str, Any]]
    hotels: list[dict[str, Any]]
    itinerary: str
    reflection: str
    final_answer: str

    # Supervisor and HITL
    steps_done: list[str]
    next: Literal[
        "research_agent",
        "weather_agent",
        "flight_hotel_agent",
        "itinerary_agent",
        "reflection_agent",
        "approval_node",
        "finalizer",
    ]
    approval: dict[str, Any]
    error: str
