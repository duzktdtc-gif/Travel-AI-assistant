from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage


def get_last_human_text(messages: list[Any]) -> str:
    for message in reversed(messages or []):
        if isinstance(message, HumanMessage) or getattr(message, "type", None) == "human":
            return str(message.content)
    return ""


def safe_json_loads(text: str) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def simple_preference_fallback(text: str) -> dict:
    """Small heuristic fallback so the app still demonstrates the graph without an LLM key."""
    lower = text.lower()
    destination = ""
    origin = ""

    # Very simple English/Vietnamese patterns.
    patterns = [
        r"to\s+([A-Z][A-Za-z\s]+?)(?:\s+from|\s+on|\s+in|\s+for|,|$)",
        r"đến\s+([A-ZÀ-Ỹ][\wÀ-ỹ\s]+?)(?:\s+từ|\s+ngày|\s+trong|,|$)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            destination = m.group(1).strip()
            break

    m = re.search(r"from\s+([A-Z][A-Za-z\s]+?)(?:\s+to|\s+on|\s+in|,|$)", text)
    if m:
        origin = m.group(1).strip()
    m = re.search(r"từ\s+([A-ZÀ-Ỹ][\wÀ-ỹ\s]+?)(?:\s+đến|\s+ngày|,|$)", text)
    if m and not origin:
        origin = m.group(1).strip()

    dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
    budget_match = re.search(r"(\$\s?\d+[\d,]*|\d+[\d,.]*\s?(usd|dollar|triệu|tr|vnd))", lower)
    travelers_match = re.search(r"(\d+)\s*(people|traveler|travelers|người|khách)", lower)

    interests = []
    for word in ["food", "museum", "shopping", "beach", "anime", "nature", "history", "ẩm thực", "biển", "mua sắm", "bảo tàng"]:
        if word in lower:
            interests.append(word)

    return {
        "origin": origin,
        "destination": destination,
        "start_date": dates[0] if dates else "",
        "end_date": dates[1] if len(dates) > 1 else "",
        "budget": budget_match.group(0) if budget_match else "",
        "travelers": int(travelers_match.group(1)) if travelers_match else 1,
        "interests": interests,
        "notes": text,
    }


def compact_dict(data: dict) -> dict:
    """Remove empty values while preserving useful zero/false values."""
    cleaned = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        cleaned[key] = value
    return cleaned
