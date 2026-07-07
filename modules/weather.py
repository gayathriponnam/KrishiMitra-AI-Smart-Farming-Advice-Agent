# =============================================================================
# modules/weather.py — Weather Service Integration
# Uses OpenWeatherMap API with intelligent fallback / mock data
# =============================================================================
import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# ── Agro-climatic zones for automatic season detection ────────────────────────
SEASON_MAP = {
    (6, 7, 8, 9): "Kharif (Rainy Season) — Sow rice, maize, cotton, soybean, groundnut",
    (10, 11): "Transition (Rabi Sowing) — Sow wheat, mustard, chickpea, peas",
    (12, 1, 2): "Rabi (Winter) — Wheat, mustard, chickpea, potato in growth",
    (3, 4, 5): "Zaid (Summer) — Vegetables, watermelon, cucumber, mung bean",
}


def get_current_season() -> str:
    month = datetime.now().month
    for months, season in SEASON_MAP.items():
        if month in months:
            return season
    return "Transition period"


def get_weather(location: str) -> dict:
    """
    Fetch current weather + 5-day forecast for the given location.
    Returns a structured dict with agricultural insights.
    Falls back to mock data if API key is missing or request fails.
    """
    if not OPENWEATHER_API_KEY:
        logger.warning("No OpenWeatherMap API key — using mock weather data.")
        return _mock_weather(location)

    try:
        # Current weather
        current_url = f"{OPENWEATHER_BASE_URL}/weather"
        params = {
            "q": f"{location},IN",  # default to India
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
        }
        current_resp = requests.get(current_url, params=params, timeout=10)

        if current_resp.status_code == 404:
            # Try without country code
            params["q"] = location
            current_resp = requests.get(current_url, params=params, timeout=10)

        current_resp.raise_for_status()
        current_data = current_resp.json()

        # 5-day forecast
        forecast_url = f"{OPENWEATHER_BASE_URL}/forecast"
        forecast_resp = requests.get(forecast_url, params=params, timeout=10)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()

        return _parse_weather(current_data, forecast_data, location)

    except requests.exceptions.RequestException as e:
        logger.warning(f"Weather API error for {location}: {e}")
        return _mock_weather(location)
    except Exception as e:
        logger.error(f"Unexpected weather error: {e}")
        return _mock_weather(location)


def _parse_weather(current: dict, forecast: dict, location: str) -> dict:
    """Parse OpenWeatherMap response into agricultural insights."""
    temp = current["main"]["temp"]
    humidity = current["main"]["humidity"]
    wind_speed = current["wind"]["speed"]  # m/s
    description = current["weather"][0]["description"].title()
    feels_like = current["main"]["feels_like"]
    pressure = current["main"]["pressure"]

    # Extract 3-day daily forecasts
    daily_forecasts = []
    seen_dates = set()
    for item in forecast.get("list", []):
        date = datetime.fromtimestamp(item["dt"]).strftime("%A, %b %d")
        if date not in seen_dates and len(daily_forecasts) < 5:
            seen_dates.add(date)
            daily_forecasts.append({
                "date": date,
                "temp_max": round(item["main"]["temp_max"], 1),
                "temp_min": round(item["main"]["temp_min"], 1),
                "description": item["weather"][0]["description"].title(),
                "humidity": item["main"]["humidity"],
                "rain": item.get("rain", {}).get("3h", 0),
            })

    # Generate agricultural advisory from weather
    advisory = _generate_weather_advisory(temp, humidity, wind_speed, description)
    alerts = _generate_weather_alerts(temp, humidity, forecast)

    return {
        "location": location,
        "temperature": round(temp, 1),
        "feels_like": round(feels_like, 1),
        "humidity": humidity,
        "wind_speed": round(wind_speed * 3.6, 1),  # convert to km/h
        "description": description,
        "pressure": pressure,
        "season": get_current_season(),
        "forecast": daily_forecasts,
        "advisory": advisory,
        "alerts": alerts,
        "source": "OpenWeatherMap",
    }


def _generate_weather_advisory(temp: float, humidity: int, wind_speed: float, desc: str) -> list[str]:
    """Generate crop-relevant weather advisories."""
    advisories = []

    if temp > 40:
        advisories.append("⚠️ Extreme heat alert! Irrigate crops in early morning or evening. Avoid noon spraying.")
    elif temp > 35:
        advisories.append("🌡️ High temperature. Increase irrigation frequency. Monitor for heat stress in crops.")
    elif temp < 5:
        advisories.append("❄️ Frost risk! Cover sensitive crops (vegetables, nurseries) with plastic sheets at night.")
    elif temp < 10:
        advisories.append("🌡️ Cool weather. Monitor Rabi crops for frost in night. Delay irrigation to morning hours.")

    if humidity > 85:
        advisories.append("💧 High humidity — fungal disease risk is HIGH. Inspect crops for blight, powdery mildew, and rust. Avoid evening irrigation.")
    elif humidity < 30:
        advisories.append("🌵 Low humidity — increase irrigation. Watch for spider mite infestations.")

    if wind_speed > 30:  # km/h
        advisories.append("💨 Strong winds — postpone foliar spraying. Secure tall crops (maize, sugarcane) against lodging.")

    if "rain" in desc.lower() or "drizzle" in desc.lower():
        advisories.append("🌧️ Rain forecasted — avoid spray applications. Good time for land preparation after showers.")

    if "thunderstorm" in desc.lower():
        advisories.append("⛈️ Thunderstorm alert! Move farming equipment to shelter. Do not work in open fields.")

    return advisories if advisories else ["✅ Weather conditions look favorable for field operations today."]


def _generate_weather_alerts(temp: float, humidity: int, forecast: dict) -> list[str]:
    """Check 5-day forecast for significant alerts."""
    alerts = []
    rain_days = 0
    for item in forecast.get("list", [])[:15]:  # Next 40 hours
        if item.get("rain", {}).get("3h", 0) > 20:
            rain_days += 1
        if "thunderstorm" in item["weather"][0]["description"].lower():
            alerts.append("⛈️ Thunderstorm expected in next 48 hours")
            break

    if rain_days >= 5:
        alerts.append("🌧️ Heavy rainfall period ahead — avoid sowing, ensure field drainage")

    return alerts


def _mock_weather(location: str) -> dict:
    """Mock weather data for development/demo without API key."""
    month = datetime.now().month
    # Seasonal temperature ranges for India
    if month in [12, 1, 2]:
        temp, humidity = 18.0, 65
    elif month in [3, 4, 5]:
        temp, humidity = 38.0, 35
    elif month in [6, 7, 8, 9]:
        temp, humidity = 29.0, 85
    else:
        temp, humidity = 25.0, 70

    return {
        "location": location or "India",
        "temperature": temp,
        "feels_like": temp - 2,
        "humidity": humidity,
        "wind_speed": 12.0,
        "description": "Partly Cloudy",
        "pressure": 1013,
        "season": get_current_season(),
        "forecast": [
            {"date": "Tomorrow", "temp_max": temp + 2, "temp_min": temp - 4, "description": "Partly Cloudy", "humidity": humidity, "rain": 0},
            {"date": "Day after", "temp_max": temp + 1, "temp_min": temp - 5, "description": "Sunny", "humidity": humidity - 5, "rain": 0},
            {"date": "In 3 days", "temp_max": temp - 1, "temp_min": temp - 6, "description": "Light Rain", "humidity": humidity + 10, "rain": 5},
        ],
        "advisory": _generate_weather_advisory(temp, humidity, 3.0, "Partly Cloudy"),
        "alerts": [],
        "source": "Demo Data (add OPENWEATHER_API_KEY for live weather)",
    }


def weather_to_text(weather: dict) -> str:
    """Convert weather dict to a text summary for LLM prompt injection."""
    lines = [
        f"Location: {weather.get('location', 'Unknown')}",
        f"Temperature: {weather.get('temperature')}°C (feels like {weather.get('feels_like')}°C)",
        f"Humidity: {weather.get('humidity')}%",
        f"Wind: {weather.get('wind_speed')} km/h",
        f"Conditions: {weather.get('description')}",
        f"Season: {weather.get('season')}",
    ]
    if weather.get("advisory"):
        lines.append("Agricultural Advisory: " + "; ".join(weather["advisory"]))
    return " | ".join(lines)
