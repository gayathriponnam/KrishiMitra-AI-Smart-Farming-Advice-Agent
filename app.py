# =============================================================================
# app.py — AI Smart Farming Advice Agent
# Flask backend with IBM watsonx.ai (Granite) + RAG + Full Feature Set
# =============================================================================
# See agent_instructions.py to customize the agent's behavior, tone, languages,
# safety rules, and agricultural specialization.
# =============================================================================

import os
import sys
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from functools import lru_cache

from flask import (Flask, request, jsonify, render_template, session,
                   send_file, abort)
from flask_cors import CORS
from dotenv import load_dotenv

# ── Load environment variables from .env ─────────────────────────────────────
load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Project modules ────────────────────────────────────────────────────────────
from agent_instructions import (
    build_system_prompt,
    QUICK_RESPONSE_TEMPLATES,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    AGENT_NAME,
    AGENT_TAGLINE,
    AGENT_ICON,
    AGENT_VERSION,
    AGRICULTURAL_DOMAINS,
    REGIONAL_CONTEXT,
)
from rag.rag_engine import FarmingRAGEngine
from modules.weather import get_weather, weather_to_text, get_current_season
from modules.market_prices import get_market_prices, MSP_2024_25
from modules.profile_manager import (
    profile_manager, SOIL_TYPES, IRRIGATION_TYPES,
    INDIAN_STATES, COMMON_CROPS,
)
from modules.report_generator import generate_farming_report, list_reports

# ── Flask app init ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "krishimitra-dev-secret-change-in-prod")
CORS(app)

# ── IBM watsonx.ai setup ───────────────────────────────────────────────────────
IBM_API_KEY = os.getenv("IBM_API_KEY", "")
IBM_WATSONX_URL = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "")
WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")

watsonx_client = None
watsonx_available = False


def _init_watsonx():
    """Initialize IBM watsonx.ai client using the modern chat API."""
    global watsonx_client, watsonx_available
    if not IBM_API_KEY or not IBM_PROJECT_ID:
        logger.warning("IBM credentials not set — running in demo mode with mock responses.")
        return

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(url=IBM_WATSONX_URL, api_key=IBM_API_KEY)
        watsonx_client = ModelInference(
            model_id=WATSONX_MODEL_ID,
            credentials=credentials,
            project_id=IBM_PROJECT_ID,
            params={
                "max_tokens": 1024,
                "temperature": 0.4,
                "top_p": 0.9,
            },
        )
        watsonx_available = True
        logger.info(f"IBM watsonx.ai initialized — Model: {WATSONX_MODEL_ID}")
    except ImportError:
        logger.warning("ibm-watsonx-ai SDK not installed. Run: pip install ibm-watsonx-ai")
    except Exception as e:
        logger.error(f"watsonx.ai init failed: {e}")


# ── RAG Engine init ────────────────────────────────────────────────────────────
KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "./rag/knowledge_base")
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./rag/vector_store/faiss_index")
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))

rag_engine = None


def _init_rag():
    global rag_engine
    try:
        rag_engine = FarmingRAGEngine(KNOWLEDGE_BASE_PATH, VECTOR_STORE_PATH)
        logger.info(f"RAG engine initialized — {rag_engine.chunk_count} knowledge chunks.")
    except Exception as e:
        logger.error(f"RAG engine init failed: {e}")


# ── App startup ────────────────────────────────────────────────────────────────
with app.app_context():
    _init_watsonx()
    _init_rag()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_session_id() -> str:
    """Get or create session ID for chat history tracking."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


# In-memory chat history store (keyed by session ID)
chat_histories: dict[str, list] = {}


def get_chat_history(session_id: str) -> list:
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    return chat_histories[session_id]


def detect_language(text: str) -> str:
    """
    Simple language detection based on Unicode ranges.
    Falls back to 'en'. For production, use langdetect library.
    """
    # Devanagari (Hindi, Marathi, etc.)
    if any("\u0900" <= c <= "\u097F" for c in text):
        return "hi"
    # Telugu
    if any("\u0C00" <= c <= "\u0C7F" for c in text):
        return "te"
    # Tamil
    if any("\u0B80" <= c <= "\u0BFF" for c in text):
        return "ta"
    # Kannada
    if any("\u0C80" <= c <= "\u0CFF" for c in text):
        return "kn"
    # Gujarati
    if any("\u0A80" <= c <= "\u0AFF" for c in text):
        return "gu"
    # Punjabi (Gurmukhi)
    if any("\u0A00" <= c <= "\u0A7F" for c in text):
        return "pa"
    # Bengali
    if any("\u0980" <= c <= "\u09FF" for c in text):
        return "bn"
    return "en"


def generate_ai_response(user_message: str, session_id: str,
                          farm_profile: dict = None, location: str = "India",
                          language: str = None) -> str:
    """
    Generate AI response using IBM Granite via watsonx.ai.
    Falls back to a structured mock response if watsonx is unavailable.
    """
    # Auto-detect language if not specified
    if not language:
        language = detect_language(user_message)

    # Retrieve relevant knowledge from RAG
    rag_context = ""
    if rag_engine and rag_engine.is_ready:
        rag_context = rag_engine.retrieve(user_message)

    # Get current weather for location context
    weather_text = "Not available"
    try:
        weather_data = get_weather(location)
        weather_text = weather_to_text(weather_data)
    except Exception:
        pass

    # Build system prompt from agent instructions
    system_prompt = build_system_prompt(
        language=language,
        location=location,
        season=get_current_season(),
        farm_profile=farm_profile,
        weather=weather_text,
        rag_context=rag_context,
    )

    # Build conversation history for context
    history = get_chat_history(session_id)
    chat_context = ""
    if history:
        recent = history[-6:]  # last 3 exchanges
        chat_context = "\n".join(
            f"{'Farmer' if m['role'] == 'user' else 'KrishiMitra'}: {m['content']}"
            for m in recent
        )

    # ── Try IBM watsonx.ai (modern chat API) ─────────────────────────────
    if watsonx_available and watsonx_client:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            # Inject last 3 conversation turns
            history = get_chat_history(session_id)
            for msg in history[-6:]:
                role = "user" if msg["role"] == "user" else "assistant"
                messages.append({"role": role, "content": msg["content"]})
            # Add current user message
            messages.append({"role": "user", "content": user_message})

            response = watsonx_client.chat(messages=messages)
            result = response["choices"][0]["message"]["content"]
            return result.strip()
        except Exception as e:
            logger.error(f"watsonx.ai generation failed: {e}")
            return _mock_response(user_message, language, rag_context)
    else:
        return _mock_response(user_message, language, rag_context)


def _mock_response(user_message: str, language: str, rag_context: str) -> str:
    """
    Structured mock response for demo/development when watsonx is not available.
    Provides useful farming advice based on keywords + RAG context.
    """
    msg_lower = user_message.lower()

    # Build response from RAG context if available
    rag_snippet = ""
    if rag_context and rag_context != "No additional context available.":
        lines = [l for l in rag_context.split("\n") if l.strip() and not l.startswith("[Source")]
        if lines:
            rag_snippet = "\n\n📚 **From Agricultural Knowledge Base:**\n" + "\n".join(lines[:8])

    # ── Keyword-based smart responses ────────────────────────────────────
    responses = {
        ("disease", "pest", "insect", "blight", "rust", "wilt", "aphid", "bollworm"):
            f"""I understand you're dealing with a crop health concern. Here's my assessment:

**Diagnosis & Management Steps:**

1. **Identify the problem**: Describe the symptoms — which part of the plant is affected (leaves, stem, roots, fruits)? What does it look like (yellowing, spots, holes, wilting)?

2. **First action — Do NOT panic**: Many issues are manageable with timely intervention.

3. **IPM Approach** (follow in order):
   - ✅ Remove and destroy severely affected plant parts
   - ✅ Ensure proper plant spacing for air circulation
   - ✅ Check if natural enemies (ladybirds, parasitic wasps) are present
   - ✅ Apply neem-based spray (NSKE 5%) as first line of treatment
   - ✅ Use chemical pesticides ONLY if IPM measures fail

4. **Wear PPE** when applying any chemical: gloves, mask, goggles.

{rag_snippet}

⚕️ For precise diagnosis, contact your nearest **Krishi Vigyan Kendra (KVK)** or upload a photo of the affected crop.""",

        ("fertilizer", "nutrient", "urea", "npk", "dap", "potash", "manure", "compost"):
            f"""Great question about soil nutrition! Here's a science-backed fertilizer guide:

**Integrated Nutrient Management (INM) Approach:**

1. **Test your soil first** — Get a Soil Health Card from your nearest soil testing lab. This tells you exactly what's deficient.

2. **Balanced N:P:K application**:
   - Nitrogen (N): For vegetative growth — use Urea (46% N) or CAN
   - Phosphorus (P): For roots & flowering — use DAP (18-46-0) or SSP
   - Potassium (K): For grain fill & disease resistance — use MOP or SOP

3. **Organic matter first**: Apply 10-15 tonnes FYM or 2-3 tonnes vermicompost per hectare before sowing.

4. **Micronutrients**: Zinc deficiency is MOST common in India — apply ZnSO₄ @ 25 kg/ha if deficient.

5. **Biofertilizers**: Apply Rhizobium (legumes) or Azotobacter (cereals) as seed treatment — saves 25% N fertilizer cost.

{rag_snippet}

💡 Tip: Split nitrogen into 3-4 applications rather than one large dose to reduce losses.""",

        ("weather", "rain", "monsoon", "drought", "flood", "temperature"):
            f"""Weather-based farming advice for your region:

**Current Season:** {get_current_season()}

**Key Weather-Based Actions:**

🌧️ **Monsoon (June-September)**:
- Complete sowing in first 2 weeks after monsoon onset
- Ensure field bunding to conserve rainwater
- Keep drainage channels clear to prevent waterlogging
- Kharif crops: Rice, Maize, Cotton, Soybean, Groundnut

❄️ **Winter (October-February)**:  
- Protect nurseries from frost with plastic covers at night
- Irrigate wheat at critical stages: CRI, tillering, flowering
- Rabi crops: Wheat, Mustard, Chickpea, Peas, Potato

☀️ **Summer (March-May)**:
- Deep summer plowing to kill soil-borne pests
- Grow short-duration vegetables with drip irrigation
- Zaid crops: Cucumber, Watermelon, Fodder maize

{rag_snippet}

⚡ For real-time weather alerts, share your location and I'll provide personalized advice.""",

        ("crop", "sow", "plant", "variety", "seed", "harvest"):
            f"""Excellent question about crop management! Here's my recommendation:

**Crop Selection & Sowing Guide:**

🌱 **For Kharif Season (June-September)**:
High-value options: Cotton, Soybean, Maize, Groundnut, Vegetables
Subsistence: Rice, Bajra, Jowar, Tur Dal

🌾 **For Rabi Season (October-February)**:
High-value: Wheat (irrigated), Mustard, Potato, Onion
Low-water: Chickpea, Lentil, Peas (rainfed)

📋 **Seed Selection Checklist**:
- ✅ Buy certified seeds from government/registered dealers
- ✅ Check for variety recommendation for your state (SAU-approved)
- ✅ Do seed germination test: 10 seeds on wet cloth, 7/10 should germinate
- ✅ Treat seeds with Thiram/Carbendazim before sowing

{rag_snippet}

🗓️ Share your location, soil type, and available irrigation to get a personalized crop calendar!""",

        ("price", "market", "mandi", "sell", "rate", "msp"):
            f"""Market Price Information:

**Current MSP Rates (2024-25) — Government Minimum Support Price:**

| Crop | MSP (₹/quintal) |
|------|----------------|
| Wheat | ₹2,275 |
| Paddy (Common) | ₹2,300 |
| Maize | ₹2,225 |
| Soybean | ₹4,892 |
| Cotton (Medium) | ₹7,121 |
| Mustard | ₹5,950 |
| Groundnut | ₹6,783 |
| Arhar Dal | ₹7,550 |

**Tips for Getting Best Prices:**
1. 🏪 Sell through **e-NAM** (National Agricultural Market) for transparent pricing
2. 🤝 Join **Farmer Producer Organizations (FPOs)** for collective bargaining
3. 📊 Check **Agmarknet** (agmarknet.nic.in) for daily mandi prices
4. ⏰ Avoid distress selling immediately after harvest — use warehouse receipts (WDRA)
5. 🏦 **PM-Kisan** provides ₹6,000/year directly to eligible farmers

{rag_snippet}""",

        ("irrigation", "water", "drip", "sprinkler", "borewell"):
            f"""Smart Irrigation Planning:

**Water Management Recommendations:**

💧 **Irrigation Methods by Efficiency:**
- Flood irrigation: 40-50% efficiency (most water wastage)
- Sprinkler: 70-80% efficiency — ideal for wheat, vegetables
- **Drip irrigation: 90-95% efficiency** — BEST for water-scarce areas

🏛️ **Government Subsidy Alert:**
- PMKSY (Pradhan Mantri Krishi Sinchayee Yojana) provides **55-85% subsidy** on drip/sprinkler installation
- Contact your District Agriculture Office or visit pmksy.gov.in

⏱️ **Critical Irrigation Stages** (never miss these):
- **Rice**: Transplanting, tillering, panicle initiation, heading
- **Wheat**: CRI (21-25 DAS), tillering, flowering, grain fill
- **Cotton**: Flowering, boll development (most water-critical period)

🌊 **Water-Saving Techniques:**
- Alternate Wetting & Drying (AWD) for rice — saves 25-30% water
- Laser land leveling — saves 25% water through uniform distribution
- Farm pond construction (MGNREGS funding available)

{rag_snippet}""",
    }

    # Match keywords
    for keywords, response in responses.items():
        if any(kw in msg_lower for kw in keywords):
            return response

    # Generic farming response
    return f"""Namaste! I'm KrishiMitra, your AI farming advisor. 🌾

I'm here to help you with:
- 🌱 **Crop Selection** — best crops for your soil, season & location
- 🐛 **Pest & Disease Management** — identification and treatment  
- 💧 **Irrigation Planning** — water-efficient techniques
- 🌿 **Soil Health** — fertilizer recommendations based on soil test
- 🌤️ **Weather Advisories** — season-appropriate farming decisions
- 💰 **Market Prices** — current mandi rates and MSP information
- 📋 **Farming Schedules** — day-wise crop calendar generation

**To get personalized advice, please share:**
1. Your location (state/district)
2. Soil type (black, red, alluvial, etc.)
3. Available irrigation source
4. The specific farming challenge you're facing

{rag_snippet if rag_snippet else ""}

What farming topic would you like guidance on today? 🙏"""


# =============================================================================
# FLASK ROUTES
# =============================================================================

@app.route("/")
def index():
    """Main application page."""
    return render_template("index.html",
                           agent_name=AGENT_NAME,
                           agent_tagline=AGENT_TAGLINE,
                           agent_icon=AGENT_ICON,
                           agent_version=AGENT_VERSION,
                           supported_languages=SUPPORTED_LANGUAGES)


@app.route("/api/chat", methods=["POST"])
def chat():
    """Main chat endpoint — processes user messages and returns AI responses."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        session_id = get_session_id()
        language = data.get("language", "")
        location = data.get("location", "India")
        profile_id = data.get("profile_id")

        # Load farm profile if provided
        farm_profile = None
        if profile_id:
            profile = profile_manager.get_profile(profile_id)
            if profile:
                farm_profile = profile_manager.profile_to_context(profile)

        # Add user message to history
        history = get_chat_history(session_id)
        history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
        })

        # Generate AI response
        response_text = generate_ai_response(
            user_message=user_message,
            session_id=session_id,
            farm_profile=farm_profile,
            location=location,
            language=language if language else None,
        )

        # Add assistant response to history
        history.append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat(),
        })

        return jsonify({
            "response": response_text,
            "session_id": session_id,
            "language": language or detect_language(user_message),
            "timestamp": datetime.now().isoformat(),
            "model": WATSONX_MODEL_ID if watsonx_available else "demo_mode",
        })

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": "Something went wrong. Please try again.", "detail": str(e)}), 500


@app.route("/api/weather", methods=["GET"])
def weather():
    """Fetch weather data and agricultural advisories."""
    location = request.args.get("location", "Delhi")
    try:
        data = get_weather(location)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/market-prices", methods=["GET"])
def market_prices():
    """Get current mandi market prices."""
    crop = request.args.get("crop", "")
    location = request.args.get("location", "")
    try:
        data = get_market_prices(crop or None, location or None)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Market prices error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/crop-recommendation", methods=["POST"])
def crop_recommendation():
    """Generate crop recommendations based on farm parameters."""
    try:
        data = request.get_json()
        soil_type = data.get("soil_type", "Loamy")
        location = data.get("location", "India")
        season = data.get("season", get_current_season())
        area = data.get("area_acres", 1)
        irrigation = data.get("irrigation", "Rainfed")
        experience = data.get("farming_type", "Conventional")

        # Ask the AI for crop recommendations
        prompt = (
            f"Give me 5 best crop recommendations for: "
            f"Soil type: {soil_type}, Location: {location}, Season: {season}, "
            f"Area: {area} acres, Irrigation: {irrigation}, "
            f"Farming type: {experience}. "
            f"For each crop, provide: expected yield, investment per acre, "
            f"ROI estimate, suitable varieties, and key success tips."
        )

        session_id = get_session_id()
        response = generate_ai_response(
            user_message=prompt,
            session_id=session_id,
            location=location,
        )

        return jsonify({
            "recommendations": response,
            "parameters": data,
            "season": get_current_season(),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Crop recommendation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    """Get all farm profiles."""
    profiles = profile_manager.get_all_profiles()
    return jsonify({"profiles": profiles, "count": len(profiles)})


@app.route("/api/profiles/<profile_id>", methods=["GET"])
def get_profile(profile_id: str):
    """Get a specific farm profile."""
    profile = profile_manager.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile)


@app.route("/api/profiles", methods=["POST"])
def create_profile():
    """Create or update a farm profile."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        profile = profile_manager.save_profile(data)
        return jsonify({"profile": profile, "message": "Profile saved successfully"}), 201
    except Exception as e:
        logger.error(f"Profile save error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/profiles/<profile_id>", methods=["DELETE"])
def delete_profile(profile_id: str):
    """Delete a farm profile."""
    if profile_manager.delete_profile(profile_id):
        return jsonify({"message": "Profile deleted"})
    return jsonify({"error": "Profile not found"}), 404


@app.route("/api/reports/generate", methods=["POST"])
def generate_report():
    """Generate a downloadable farming report."""
    try:
        data = request.get_json() or {}
        session_id = get_session_id()
        history = get_chat_history(session_id)

        profile_id = data.get("profile_id")
        profile = profile_manager.get_profile(profile_id) if profile_id else {}
        profile = profile or data.get("profile", {})

        location = profile.get("location") or data.get("location", "India")
        weather_data = get_weather(location)
        market_data = get_market_prices(location=location)

        recommendations = {
            "crops": [
                {"crop": c, "rationale": f"Recommended for {profile.get('soil_type', 'your')} soil"}
                for c in profile.get("current_crops", ["Wheat", "Rice"])[:5]
            ]
        }

        result = generate_farming_report(
            profile=profile,
            chat_history=history,
            weather=weather_data,
            market_data=market_data,
            recommendations=recommendations,
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/reports/download/<filename>")
def download_report(filename: str):
    """Download a generated report file."""
    # Security: prevent path traversal
    safe_filename = Path(filename).name
    if ".." in safe_filename or "/" in safe_filename:
        abort(400)

    # Try PDF first, then JSON
    pdf_path = REPORTS_DIR / f"{safe_filename}.pdf"
    json_path = REPORTS_DIR / f"{safe_filename}.json"

    if pdf_path.exists():
        return send_file(str(pdf_path), as_attachment=True,
                         download_name=f"{safe_filename}.pdf",
                         mimetype="application/pdf")
    elif json_path.exists():
        return send_file(str(json_path), as_attachment=True,
                         download_name=f"{safe_filename}.json",
                         mimetype="application/json")
    else:
        abort(404)


@app.route("/api/reports/list", methods=["GET"])
def list_all_reports():
    """List all generated reports."""
    return jsonify({"reports": list_reports()})


@app.route("/api/chat/history", methods=["GET"])
def chat_history():
    """Get chat history for current session."""
    session_id = get_session_id()
    history = get_chat_history(session_id)
    return jsonify({"history": history, "session_id": session_id})


@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    """Clear chat history for current session."""
    session_id = get_session_id()
    if session_id in chat_histories:
        chat_histories[session_id] = []
    return jsonify({"message": "Chat history cleared"})


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return agent configuration for frontend."""
    return jsonify({
        "agent_name": AGENT_NAME,
        "agent_tagline": AGENT_TAGLINE,
        "agent_icon": AGENT_ICON,
        "agent_version": AGENT_VERSION,
        "supported_languages": SUPPORTED_LANGUAGES,
        "default_language": DEFAULT_LANGUAGE,
        "agricultural_domains": AGRICULTURAL_DOMAINS,
        "soil_types": SOIL_TYPES,
        "irrigation_types": IRRIGATION_TYPES,
        "indian_states": INDIAN_STATES,
        "common_crops": COMMON_CROPS,
        "msp_rates": dict(list(MSP_2024_25.items())[:15]),
        "watsonx_available": watsonx_available,
        "model_id": WATSONX_MODEL_ID,
        "rag_available": rag_engine.is_ready if rag_engine else False,
        "current_season": get_current_season(),
    })


@app.route("/api/rag/rebuild", methods=["POST"])
def rebuild_rag():
    """Rebuild the FAISS vector index from knowledge base files."""
    if not rag_engine:
        return jsonify({"error": "RAG engine not initialized"}), 500
    success = rag_engine.rebuild_index()
    return jsonify({
        "success": success,
        "message": "Index rebuilt successfully" if success else "Rebuild failed",
        "chunks": rag_engine.chunk_count,
    })


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint for deployment monitoring."""
    return jsonify({
        "status": "healthy",
        "agent": AGENT_NAME,
        "version": AGENT_VERSION,
        "watsonx_connected": watsonx_available,
        "rag_ready": rag_engine.is_ready if rag_engine else False,
        "timestamp": datetime.now().isoformat(),
    })


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    logger.info(f"")
    logger.info(f"  {'='*60}")
    logger.info(f"  {AGENT_ICON} {AGENT_NAME} v{AGENT_VERSION}")
    logger.info(f"  {AGENT_TAGLINE}")
    logger.info(f"  {'='*60}")
    logger.info(f"  🌐 Running at: http://{host}:{port}")
    logger.info(f"  🤖 IBM watsonx.ai: {'✅ Connected' if watsonx_available else '⚠️ Demo Mode'}")
    logger.info(f"  📚 RAG Engine: {'✅ Ready' if (rag_engine and rag_engine.is_ready) else '⚠️ Not Ready'}")
    logger.info(f"  {'='*60}")
    logger.info(f"")

    app.run(host=host, port=port, debug=debug)
