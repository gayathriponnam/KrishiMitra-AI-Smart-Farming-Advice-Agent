# =============================================================================
# modules/market_prices.py — Mandi / Market Price Service
# Uses Agmarknet/data.gov.in API with mock fallback
# =============================================================================
import os
import requests
import logging
import json
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

AGMARKET_API_KEY = os.getenv("AGMARKET_API_KEY", "")

# Mock price database (₹/quintal) — realistic ranges for major Indian markets
MOCK_PRICES = {
    "Wheat": {"min": 2100, "max": 2800, "modal": 2350, "unit": "quintal"},
    "Rice (Common)": {"min": 1700, "max": 2400, "modal": 2050, "unit": "quintal"},
    "Rice (Fine)": {"min": 2800, "max": 4500, "modal": 3600, "unit": "quintal"},
    "Paddy": {"min": 1800, "max": 2300, "modal": 2015, "unit": "quintal"},
    "Cotton": {"min": 5800, "max": 7200, "modal": 6400, "unit": "quintal"},
    "Soybean": {"min": 3800, "max": 5500, "modal": 4600, "unit": "quintal"},
    "Maize": {"min": 1400, "max": 2200, "modal": 1850, "unit": "quintal"},
    "Onion": {"min": 400, "max": 3500, "modal": 1200, "unit": "quintal"},
    "Potato": {"min": 500, "max": 2000, "modal": 900, "unit": "quintal"},
    "Tomato": {"min": 300, "max": 4000, "modal": 1500, "unit": "quintal"},
    "Chilli (Dry)": {"min": 8000, "max": 22000, "modal": 14000, "unit": "quintal"},
    "Turmeric": {"min": 7000, "max": 14000, "modal": 10500, "unit": "quintal"},
    "Groundnut": {"min": 4800, "max": 6500, "modal": 5600, "unit": "quintal"},
    "Mustard": {"min": 4800, "max": 6000, "modal": 5350, "unit": "quintal"},
    "Sugarcane": {"min": 285, "max": 380, "modal": 315, "unit": "quintal"},
    "Chickpea (Gram)": {"min": 4500, "max": 6000, "modal": 5300, "unit": "quintal"},
    "Arhar (Tur Dal)": {"min": 7000, "max": 9500, "modal": 8200, "unit": "quintal"},
    "Urad Dal": {"min": 7200, "max": 10000, "modal": 8500, "unit": "quintal"},
    "Jowar (Sorghum)": {"min": 2100, "max": 3200, "modal": 2700, "unit": "quintal"},
    "Bajra (Pearl Millet)": {"min": 1800, "max": 2600, "modal": 2250, "unit": "quintal"},
    "Sunflower": {"min": 5200, "max": 7000, "modal": 6100, "unit": "quintal"},
    "Garlic": {"min": 2000, "max": 12000, "modal": 5500, "unit": "quintal"},
    "Ginger (Fresh)": {"min": 3000, "max": 10000, "modal": 6000, "unit": "quintal"},
    "Banana": {"min": 800, "max": 2500, "modal": 1400, "unit": "quintal"},
    "Mango": {"min": 1500, "max": 6000, "modal": 3000, "unit": "quintal"},
}

# Major mandi markets by region
MAJOR_MARKETS = {
    "north": ["Azadpur (Delhi)", "Karnal (Haryana)", "Ludhiana (Punjab)", "Agra (UP)", "Jaipur (Rajasthan)"],
    "south": ["Kurnool (AP)", "Guntur (AP)", "Warangal (Telangana)", "Bellary (Karnataka)", "Chennai (TN)"],
    "west": ["APMC Mumbai", "Pune (Maharashtra)", "Ahmedabad (Gujarat)", "Rajkot (Gujarat)"],
    "central": ["Indore (MP)", "Bhopal (MP)", "Nagpur (Maharashtra)", "Raipur (CG)"],
    "east": ["Howrah (WB)", "Patna (Bihar)", "Bhubaneswar (Odisha)"],
}

MSP_2024_25 = {
    "Wheat": 2275,
    "Paddy (Common)": 2300,
    "Paddy (Grade A)": 2320,
    "Maize": 2225,
    "Jowar (Hybrid)": 3371,
    "Jowar (Maldandi)": 3421,
    "Bajra": 2625,
    "Ragi": 4290,
    "Arhar (Tur)": 7550,
    "Moong (Green Gram)": 8682,
    "Urad (Black Gram)": 7400,
    "Groundnut": 6783,
    "Soybean (Yellow)": 4892,
    "Sunflower Seed": 7280,
    "Sesamum (Til)": 9267,
    "Sugarcane (FRP)": 340,
    "Cotton (Medium Staple)": 7121,
    "Cotton (Long Staple)": 7521,
    "Mustard (Rapeseed)": 5950,
    "Safflower": 5800,
}


def get_market_prices(crop: str = None, location: str = None) -> dict:
    """
    Get current market prices for crops.
    Returns price data with MSP comparison and market insights.
    """
    if AGMARKET_API_KEY:
        return _fetch_live_prices(crop, location)
    else:
        return _get_mock_prices(crop, location)


def _fetch_live_prices(crop: str, location: str) -> dict:
    """Fetch live prices from data.gov.in Agmarknet API."""
    try:
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            "api-key": AGMARKET_API_KEY,
            "format": "json",
            "limit": 20,
        }
        if crop:
            params["filters[commodity]"] = crop
        if location:
            params["filters[state]"] = location

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("records"):
            return _parse_agmarknet_response(data["records"], crop)
    except Exception as e:
        logger.warning(f"Live market price fetch failed: {e}")

    return _get_mock_prices(crop, location)


def _parse_agmarknet_response(records: list, crop: str) -> dict:
    """Parse Agmarknet API response."""
    prices = []
    for rec in records:
        prices.append({
            "crop": rec.get("commodity", "Unknown"),
            "variety": rec.get("variety", "-"),
            "market": rec.get("market", "Unknown"),
            "state": rec.get("state", "Unknown"),
            "min_price": float(rec.get("min_price", 0)),
            "max_price": float(rec.get("max_price", 0)),
            "modal_price": float(rec.get("modal_price", 0)),
            "date": rec.get("arrival_date", datetime.now().strftime("%d/%m/%Y")),
        })
    return {
        "prices": prices,
        "msp": MSP_2024_25.get(crop, "N/A"),
        "source": "Agmarknet (data.gov.in)",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _get_mock_prices(crop: str = None, location: str = None) -> dict:
    """Generate realistic mock market prices."""
    prices = []

    if crop and crop in MOCK_PRICES:
        crops_to_show = [crop]
    elif crop:
        # Fuzzy match
        crops_to_show = [c for c in MOCK_PRICES if crop.lower() in c.lower()]
        if not crops_to_show:
            crops_to_show = list(MOCK_PRICES.keys())[:8]
    else:
        crops_to_show = list(MOCK_PRICES.keys())[:10]

    # Determine region for markets
    region_markets = _get_markets_for_location(location)

    for crop_name in crops_to_show[:8]:
        base = MOCK_PRICES[crop_name]
        for market in region_markets[:3]:
            # Add slight random variation per market
            variation = random.uniform(0.95, 1.08)
            modal = round(base["modal"] * variation)
            prices.append({
                "crop": crop_name,
                "variety": "Common",
                "market": market,
                "state": location or "India",
                "min_price": round(base["min"] * variation),
                "max_price": round(base["max"] * variation),
                "modal_price": modal,
                "unit": f"₹/{base['unit']}",
                "date": datetime.now().strftime("%d/%m/%Y"),
                "vs_msp": _compare_to_msp(crop_name, modal),
            })

    return {
        "prices": prices,
        "msp_rates": {k: v for k, v in list(MSP_2024_25.items())[:10]},
        "source": "Demo Data (add AGMARKET_API_KEY for live prices)",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "Connect to Agmarknet API for real-time prices from 7,000+ mandis",
    }


def _get_markets_for_location(location: str) -> list:
    """Get relevant markets for a location."""
    if not location:
        return MAJOR_MARKETS["north"] + MAJOR_MARKETS["south"]

    location_lower = location.lower()
    for region, markets in MAJOR_MARKETS.items():
        if any(location_lower in m.lower() for m in markets):
            return markets

    # State-based matching
    state_region_map = {
        "punjab": "north", "haryana": "north", "up": "north", "uttarakhand": "north",
        "rajasthan": "north", "bihar": "north",
        "andhra": "south", "telangana": "south", "karnataka": "south", "tamil": "south", "kerala": "south",
        "gujarat": "west", "maharashtra": "west",
        "madhya pradesh": "central", "mp": "central", "chhattisgarh": "central",
        "west bengal": "east", "odisha": "east", "assam": "east",
    }
    for key, region in state_region_map.items():
        if key in location_lower:
            return MAJOR_MARKETS[region]

    return MAJOR_MARKETS["north"]


def _compare_to_msp(crop: str, modal_price: float) -> str:
    """Compare market price to MSP."""
    msp_map = {
        "Wheat": "Wheat", "Paddy": "Paddy (Common)", "Maize": "Maize",
        "Soybean": "Soybean (Yellow)", "Mustard": "Mustard (Rapeseed)",
        "Cotton": "Cotton (Medium Staple)", "Groundnut": "Groundnut",
        "Arhar (Tur Dal)": "Arhar (Tur)",
    }
    msp_key = msp_map.get(crop)
    if msp_key and msp_key in MSP_2024_25:
        msp = MSP_2024_25[msp_key]
        diff = modal_price - msp
        pct = (diff / msp) * 100
        if diff > 0:
            return f"↑ ₹{diff:.0f} above MSP (+{pct:.1f}%)"
        else:
            return f"↓ ₹{abs(diff):.0f} below MSP ({pct:.1f}%)"
    return "MSP N/A"
