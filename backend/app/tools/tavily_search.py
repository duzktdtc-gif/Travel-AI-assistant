from __future__ import annotations

import requests
from app.core.config import settings


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search real-time travel information with Tavily. Falls back to demo data without an API key."""
    if not settings.tavily_api_key:
        return [
            {
                "title": "Demo travel research source",
                "url": "https://example.com/demo-travel-source",
                "content": (
                    "TAVILY_API_KEY is not configured. This is demo research data. "
                    "Add the key in backend/.env to fetch live travel advisories, attractions, and local tips."
                ),
            }
        ]

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": True,
        "include_raw_content": False,
    }
    try:
        resp = requests.post("https://api.tavily.com/search", json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if data.get("answer"):
            results.insert(
                0,
                {
                    "title": "Tavily summary",
                    "url": "https://tavily.com",
                    "content": data["answer"],
                },
            )
        return results[:max_results]
    except Exception as exc:  # noqa: BLE001 - return usable message to the agent
        return [
            {
                "title": "Search error",
                "url": "",
                "content": f"Could not fetch Tavily results: {exc}",
            }
        ]
