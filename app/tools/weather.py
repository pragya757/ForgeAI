import requests
from typing import List, Any, Dict
from app.tools.registry import BaseTool, ToolParameter

class WeatherTool(BaseTool):
    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Get current weather conditions and forecasts for a given latitude and longitude using the Open-Meteo public API."

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="latitude",
                type="number",
                description="Latitude coordinate (e.g., 51.5074 for London, 1.3521 for Singapore).",
                required=True
            ),
            ToolParameter(
                name="longitude",
                type="number",
                description="Longitude coordinate (e.g., -0.1278 for London, 103.8198 for Singapore).",
                required=True
            ),
            ToolParameter(
                name="city",
                type="string",
                description="Optional city name for location tracking.",
                required=False
            )
        ]

    def execute(self, latitude: float, longitude: float, city: str = "", **kwargs: Any) -> Dict[str, Any]:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m"],
            "timezone": "auto"
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                return {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": data.get("timezone"),
                    "temperature_celsius": current.get("temperature_2m"),
                    "relative_humidity_percent": current.get("relative_humidity_2m"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                    "source": "Open-Meteo Public API"
                }
            return {"error": f"Open-Meteo returned status {resp.status_code}", "latitude": latitude, "longitude": longitude}
        except Exception as e:
            # Fallback for offline execution
            return {
                "latitude": latitude,
                "longitude": longitude,
                "temperature_celsius": 22.5,
                "relative_humidity_percent": 65,
                "wind_speed_kmh": 12.0,
                "notice": "Offline fallback data returned",
                "source": "Open-Meteo (simulated)"
            }
