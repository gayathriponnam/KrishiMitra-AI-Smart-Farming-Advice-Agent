# =============================================================================
# modules/profile_manager.py — Farm Profile Management
# Saves/loads farmer profiles to/from JSON files
# =============================================================================
import os
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROFILES_DIR = Path(os.getenv("PROFILES_DIR", "./profiles"))
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PROFILE = {
    "profile_id": "default",
    "farmer_name": "",
    "farm_name": "My Farm",
    "location": "",
    "state": "",
    "district": "",
    "village": "",
    "area_acres": 0,
    "soil_type": "Loamy",
    "irrigation_type": "Rainfed",
    "water_source": "",
    "current_crops": [],
    "planned_crops": [],
    "livestock": [],
    "preferred_language": "en",
    "farming_type": "Conventional",  # Organic, Conventional, Mixed
    "experience_years": 0,
    "phone": "",
    "created_at": "",
    "updated_at": "",
}

SOIL_TYPES = [
    "Alluvial", "Black Cotton (Vertisol)", "Red Laterite", "Sandy Loam",
    "Clay Loam", "Loamy", "Sandy", "Silty", "Saline-Alkaline", "Acidic Hill Soil"
]

IRRIGATION_TYPES = [
    "Rainfed", "Canal Irrigation", "Drip Irrigation", "Sprinkler",
    "Borewell/Tubewell", "Dug Well", "Tank/Pond", "River/Stream Lift",
]

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman & Nicobar Islands", "Chandigarh", "Dadra & Nagar Haveli",
    "Daman & Diu", "Delhi", "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

COMMON_CROPS = [
    "Rice", "Wheat", "Maize", "Sorghum (Jowar)", "Pearl Millet (Bajra)",
    "Finger Millet (Ragi)", "Cotton", "Sugarcane", "Soybean", "Groundnut",
    "Mustard", "Sunflower", "Chickpea (Gram)", "Arhar (Tur Dal)", "Moong Dal",
    "Urad Dal", "Lentil (Masoor)", "Peas", "Potato", "Onion", "Tomato",
    "Chilli", "Turmeric", "Ginger", "Garlic", "Mango", "Banana", "Papaya",
    "Guava", "Grapes", "Orange", "Pomegranate", "Apple", "Tea", "Coffee",
    "Rubber", "Coconut", "Areca Nut", "Jute", "Fodder Crops",
]


class ProfileManager:
    """Manage farmer profiles with CRUD operations."""

    def get_all_profiles(self) -> list:
        """Return list of all profiles."""
        profiles = []
        for f in sorted(PROFILES_DIR.glob("profile_*.json"),
                        key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    profile = json.load(fp)
                    profiles.append(profile)
            except Exception as e:
                logger.warning(f"Could not load profile {f}: {e}")
        return profiles

    def get_profile(self, profile_id: str) -> dict | None:
        """Load a specific profile by ID."""
        path = PROFILES_DIR / f"profile_{profile_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Could not load profile {profile_id}: {e}")
            return None

    def save_profile(self, profile_data: dict) -> dict:
        """Create or update a profile. Returns the saved profile."""
        profile = DEFAULT_PROFILE.copy()
        profile.update(profile_data)

        # Ensure required fields
        if not profile.get("profile_id") or profile["profile_id"] == "default":
            profile["profile_id"] = self._generate_id(profile)

        now = datetime.now().isoformat()
        if not profile.get("created_at"):
            profile["created_at"] = now
        profile["updated_at"] = now

        path = PROFILES_DIR / f"profile_{profile['profile_id']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

        logger.info(f"Profile saved: {profile['profile_id']}")
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile."""
        path = PROFILES_DIR / f"profile_{profile_id}.json"
        if path.exists():
            path.unlink()
            logger.info(f"Profile deleted: {profile_id}")
            return True
        return False

    def get_active_profile(self) -> dict | None:
        """Get the most recently updated profile as the 'active' profile."""
        profiles = self.get_all_profiles()
        return profiles[0] if profiles else None

    def _generate_id(self, profile: dict) -> str:
        """Generate a simple profile ID from farmer name and timestamp."""
        name = profile.get("farmer_name", "farmer").lower().replace(" ", "_")[:15]
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{name}_{ts}"

    def profile_to_context(self, profile: dict) -> dict:
        """Extract context-relevant fields for the LLM prompt."""
        if not profile:
            return {}
        return {
            "farm_name": profile.get("farm_name"),
            "location": f"{profile.get('village', '')}, {profile.get('district', '')}, {profile.get('state', '')}".strip(", "),
            "area_acres": profile.get("area_acres"),
            "soil_type": profile.get("soil_type"),
            "irrigation_type": profile.get("irrigation_type"),
            "current_crops": profile.get("current_crops", []),
            "farming_type": profile.get("farming_type"),
        }


# Singleton instance
profile_manager = ProfileManager()
