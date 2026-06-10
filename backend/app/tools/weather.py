from __future__ import annotations

from collections import defaultdict
import requests
from app.core.config import settings


def get_weather_forecast(city: str) -> list[dict]:
    """Fetch a compact 5-day OpenWeather forecast. Uses demo values when no key is configured."""
    if not city:
        return []

    if not settings.openweather_api_key:
        return [
            {
                "date": "demo",
                "summary": "No OPENWEATHER_API_KEY configured",
                "temp_min_c": 24,
                "temp_max_c": 30,
                "rain_probability": "unknown",
            }
        ]

    params = {
        "q": city,
        "appid": settings.openweather_api_key,
        "units": "metric",
        "cnt": 40,
    }
    try:
        resp = requests.get("https://api.openweathermap.org/data/2.5/forecast", params=params, timeout=20)
        resp.raise_for_status()
        raw = resp.json().get("list", [])

        grouped: dict[str, list[dict]] = defaultdict(list)
        for item in raw:
            date = item.get("dt_txt", "")[:10]
            grouped[date].append(item)

        compact = []
        for date, items in list(grouped.items())[:5]:
            temps = [x.get("main", {}).get("temp") for x in items if x.get("main")]
            pops = [x.get("pop", 0) for x in items]
            descriptions = [x.get("weather", [{}])[0].get("description", "") for x in items]
            most_common = max(set(descriptions), key=descriptions.count) if descriptions else ""
            compact.append(
                {
                    "date": date,
                    "summary": most_common,
                    "temp_min_c": round(min(temps), 1) if temps else None,
                    "temp_max_c": round(max(temps), 1) if temps else None,
                    "rain_probability": f"{round(max(pops) * 100)}%" if pops else "unknown",
                }
            )
        return compact
    except Exception as exc:  # noqa: BLE001
        return [
            {
                "date": "error",
                "summary": f"Could not fetch OpenWeather data: {exc}",
                "temp_min_c": None,
                "temp_max_c": None,
                "rain_probability": "unknown",
            }
        ]
