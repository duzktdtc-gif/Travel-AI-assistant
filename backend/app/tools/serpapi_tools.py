from __future__ import annotations

import requests
from app.core.config import settings


def _demo_flights(origin: str, destination: str, start_date: str, end_date: str) -> list[dict]:
    return [
        {
            "airline": "Demo Airlines",
            "route": f"{origin or 'Origin'} → {destination or 'Destination'}",
            "departure": start_date or "TBD",
            "return": end_date or "TBD",
            "price": "Set SERPAPI_API_KEY for live Google Flights data",
            "duration": "TBD",
        }
    ]


def _demo_hotels(destination: str) -> list[dict]:
    return [
        {
            "name": "Demo Central Hotel",
            "location": destination or "Destination",
            "price": "Set SERPAPI_API_KEY for live Google Hotels data",
            "rating": "TBD",
            "link": "",
        }
    ]


def search_flights(origin: str, destination: str, start_date: str, end_date: str) -> list[dict]:
    """Search flights via SerpApi Google Flights engine. Works best with airport codes."""
    if not settings.serpapi_api_key:
        return _demo_flights(origin, destination, start_date, end_date)

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": start_date,
        "return_date": end_date,
        "currency": "USD",
        "hl": "en",
        "api_key": settings.serpapi_api_key,
    }
    try:
        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        flights = data.get("best_flights") or data.get("other_flights") or []
        compact = []
        for f in flights[:5]:
            segments = f.get("flights", [])
            first = segments[0] if segments else {}
            compact.append(
                {
                    "airline": first.get("airline", "Unknown"),
                    "route": f"{origin} → {destination}",
                    "departure": first.get("departure_airport", {}).get("time", start_date),
                    "return": end_date,
                    "price": f.get("price", "Unknown"),
                    "duration": f.get("total_duration", "Unknown"),
                }
            )
        return compact or _demo_flights(origin, destination, start_date, end_date)
    except Exception as exc:  # noqa: BLE001
        return [{"airline": "Search error", "route": f"{origin} → {destination}", "price": str(exc)}]


def search_hotels(destination: str, check_in: str, check_out: str, adults: int = 1) -> list[dict]:
    """Search hotels via SerpApi Google Hotels engine."""
    if not settings.serpapi_api_key:
        return _demo_hotels(destination)

    params = {
        "engine": "google_hotels",
        "q": destination,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": adults,
        "currency": "USD",
        "hl": "en",
        "api_key": settings.serpapi_api_key,
    }
    try:
        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        hotels = data.get("properties") or []
        compact = []
        for h in hotels[:5]:
            rate = h.get("rate_per_night", {}) or {}
            compact.append(
                {
                    "name": h.get("name", "Unknown hotel"),
                    "location": destination,
                    "price": rate.get("lowest") or h.get("total_rate", {}).get("lowest", "Unknown"),
                    "rating": h.get("overall_rating", "Unknown"),
                    "link": h.get("link", ""),
                }
            )
        return compact or _demo_hotels(destination)
    except Exception as exc:  # noqa: BLE001
        return [{"name": "Hotel search error", "location": destination, "price": str(exc), "rating": ""}]
