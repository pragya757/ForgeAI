import requests
from typing import List, Any, Dict
from app.tools.registry import BaseTool, ToolParameter

class WeatherTool(BaseTool):
    """
    Get current weather conditions using the Open-Meteo public API.
    Guarantees:
    - Strict 3-second network timeout
    - Traps timeouts and network exceptions
    - Graceful offline fallback
    """

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
            "latitude": float(latitude),
            "longitude": float(longitude),
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m"],
            "timezone": "auto"
        }
        try:
            resp = requests.get(url, params=params, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                return {
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": city or "Unknown",
                    "timezone": data.get("timezone"),
                    "temperature_celsius": current.get("temperature_2m"),
                    "relative_humidity_percent": current.get("relative_humidity_2m"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                    "source": "Open-Meteo Public API",
                    "status": "success"
                }
            return {
                "error": f"Weather API returned status {resp.status_code}",
                "status": "api_error",
                "latitude": latitude,
                "longitude": longitude
            }
        except requests.exceptions.Timeout:
            return {
                "error": "Weather API request timed out after 3.0 seconds.",
                "status": "timeout",
                "latitude": latitude,
                "longitude": longitude,
                "notice": "Offline fallback data returned",
                "temperature_celsius": 20.0,
                "relative_humidity_percent": 60,
                "source": "Open-Meteo (fallback)"
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Network error contacting weather API: {str(e)}",
                "status": "network_error",
                "latitude": latitude,
                "longitude": longitude,
                "notice": "Offline fallback data returned",
                "temperature_celsius": 20.0,
                "relative_humidity_percent": 60,
                "source": "Open-Meteo (fallback)"
            }
        except Exception as e:
            return {
                "error": f"Unexpected error in weather lookup: {str(e)}",
                "status": "error",
                "latitude": latitude,
                "longitude": longitude
            }
