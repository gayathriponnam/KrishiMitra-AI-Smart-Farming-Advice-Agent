# 🌾 KrishiMitra — AI Smart Farming Advice Agent

> **Your AI-Powered Smart Farming Companion**  
> Built with **Python Flask** + **IBM watsonx.ai** + **IBM Granite Models** + **RAG (FAISS)**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com/)
[![IBM watsonx.ai](https://img.shields.io/badge/IBM-watsonx.ai-0043CE)](https://www.ibm.com/watsonx)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Local Setup & Running](#local-setup)
5. [IBM Cloud Credentials](#ibm-cloud-credentials)
6. [Customizing the Agent](#customizing-the-agent)
7. [RAG Knowledge Base](#rag-knowledge-base)
8. [API Reference](#api-reference)
9. [IBM Cloud Deployment](#ibm-cloud-deployment)
10. [Troubleshooting](#troubleshooting)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **IBM Granite AI Chat** | Chat with `ibm/granite-3-8b-instruct` via watsonx.ai |
| 📚 **RAG Knowledge Base** | FAISS-indexed agricultural documents for accurate advice |
| 🌾 **Crop Recommendations** | Personalized crops based on soil, season, location |
| 🌤️ **Weather Insights** | Live weather + agricultural advisories (OpenWeatherMap) |
| 🌍 **Soil Health Analysis** | Interpret Soil Health Card values + fertilizer recs |
| 🐛 **Pest & Disease Advisory** | AI diagnosis + organic & chemical treatment options |
| 💧 **Irrigation Planner** | Crop-stage based water management schedules |
| 💰 **Mandi Market Prices** | Current rates + MSP comparison (Agmarknet) |
| 🌐 **Multilingual** | English, Hindi, Telugu, Tamil, Kannada, Marathi, Gujarati, Punjabi, Bengali |
| 🎤 **Voice I/O** | Web Speech API for voice input + text-to-speech output |
| 📄 **PDF Reports** | Downloadable comprehensive farming advisory reports |
| 👨‍🌾 **Farm Profiles** | Manage multiple family farm profiles |
| 🌙 **Dark Mode** | Full dark/light mode with smooth transitions |
| 📱 **Mobile Responsive** | Fully responsive Bootstrap 5 UI with bottom nav |

---

## 📁 Project Structure

```
AI smart farming advice agent/
│
├── app.py                          # ← Flask backend (main entry point)
├── agent_instructions.py           # ← CUSTOMIZE AGENT HERE (tone, languages, rules)
├── wsgi.py                         # ← Production WSGI entry point
├── Procfile                        # ← Heroku/Cloud Foundry deployment
├── requirements.txt                # ← Python dependencies
├── .env.example                    # ← Environment variables template
│
├── rag/
│   ├── __init__.py
│   ├── rag_engine.py               # ← FAISS RAG engine
│   ├── knowledge_base/             # ← Add .txt agricultural documents here
│   │   ├── crops_india.txt
│   │   ├── soil_health.txt
│   │   ├── pest_disease.txt
│   │   └── irrigation_water.txt
│   └── vector_store/               # ← FAISS index (auto-generated)
│       ├── index.faiss
│       ├── chunks.npy
│       └── sources.npy
│
├── modules/
│   ├── __init__.py
│   ├── weather.py                  # ← OpenWeatherMap integration
│   ├── market_prices.py            # ← Agmarknet/mock mandi prices
│   ├── profile_manager.py          # ← Farm profile CRUD
│   └── report_generator.py         # ← PDF/JSON report generation
│
├── templates/
│   └── index.html                  # ← Main SPA frontend (Bootstrap 5)
│
├── static/
│   ├── css/
│   │   └── style.css               # ← Custom agriculture-themed CSS
│   └── js/
│       └── app.js                  # ← Full frontend JavaScript
│
├── reports/                        # ← Generated reports stored here
└── profiles/                       # ← Farmer profiles stored here
```

---

## 🔧 Prerequisites

- **Python** 3.9 or higher
- **pip** (Python package manager)
- **IBM Cloud account** with watsonx.ai access
- **IBM watsonx.ai** project with API key
- **OpenWeatherMap API key** (free tier — optional but recommended)
- **Git** (for version control)

---

## 🚀 Local Setup

### Step 1 — Clone / Download the Project

```bash
# If using Git:
git clone https://github.com/yourusername/krishimitra.git
cd krishimitra

# OR simply navigate to the project folder
cd "AI smart farming advice agent"
```

### Step 2 — Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note**: `faiss-cpu` and `sentence-transformers` are large packages.
> If you encounter issues, install them separately:
> ```bash
> pip install faiss-cpu==1.8.0
> pip install sentence-transformers==3.0.1
> ```

### Step 4 — Configure Environment Variables

```bash
# Copy the example .env file
copy .env.example .env        # Windows
cp .env.example .env           # macOS/Linux

# Edit .env with your credentials (see next section)
notepad .env                   # Windows
nano .env                      # macOS/Linux
```

### Step 5 — Run the Application

```bash
python app.py
```

**Output:**
```
==============================================================
🌾 KrishiMitra v2.0.0
Your AI-Powered Smart Farming Companion
==============================================================
🌐 Running at: http://0.0.0.0:5000
🤖 IBM watsonx.ai: ✅ Connected  (or ⚠️ Demo Mode if no key)
📚 RAG Engine: ✅ Ready
==============================================================
```

Open your browser at: **http://localhost:5000**

---

## 🔑 IBM Cloud Credentials

### Getting Your IBM API Key

1. Log in to **IBM Cloud**: https://cloud.ibm.com
2. Click your profile (top right) → **"Manage"** → **"Access (IAM)"**
3. In the left menu → **"API keys"**
4. Click **"Create an IBM Cloud API key"**
5. Name it: `KrishiMitra-Agent`
6. Copy the API key immediately (it's shown only once!)

### Getting Your watsonx.ai Project ID

1. Open **IBM watsonx.ai**: https://dataplatform.cloud.ibm.com
2. Create a new project or open an existing one
3. Click **"Manage"** tab in the project
4. Under **"General"**, copy the **"Project ID"**

### Getting the watsonx.ai URL

Find your region URL:
| Region | URL |
|--------|-----|
| US South (Dallas) | `https://us-south.ml.cloud.ibm.com` |
| Europe (Frankfurt) | `https://eu-de.ml.cloud.ibm.com` |
| Asia Pacific (Tokyo) | `https://jp-tok.ml.cloud.ibm.com` |

### Edit Your `.env` File

```env
IBM_API_KEY=your_actual_ibm_api_key_here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
IBM_PROJECT_ID=your_actual_project_id_here
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
OPENWEATHER_API_KEY=your_openweathermap_key_here   # Optional
FLASK_SECRET_KEY=your-long-random-secret-key-here
```

### OpenWeatherMap API Key (Optional)

1. Sign up at https://openweathermap.org/api
2. Free tier provides 1,000 calls/day — sufficient for development
3. Copy API key and set `OPENWEATHER_API_KEY` in `.env`

---

## 🎛️ Customizing the Agent

**All customization is in `agent_instructions.py`** — no other files need changing.

```python
# ── Agent Identity ──────────────────────────────────────────────────────
AGENT_NAME = "KrishiMitra"           # Change the agent's name
AGENT_TAGLINE = "Your AI-Powered Smart Farming Companion"

# ── Tone & Personality ──────────────────────────────────────────────────
AGENT_TONE = "friendly"              # Options: formal, friendly, concise, empathetic

TONE_GUIDELINES = """
- Speak like a knowledgeable friend...
"""  # ← Modify personality here

# ── Supported Languages ─────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "te": "Telugu (తెలుగు)",
    # Add more languages...
}

# ── Safety Rules ─────────────────────────────────────────────────────────
SAFETY_RULES = """
1. PESTICIDE SAFETY: ...    # ← Modify safety constraints
"""

# ── Regional Context ─────────────────────────────────────────────────────
REGIONAL_CONTEXT = {
    "south_india": {...},   # ← Add/modify regional farming practices
}
```

After modifying, **restart the Flask server** for changes to take effect.

---

## 📚 RAG Knowledge Base

### Adding Your Own Agricultural Documents

1. **Create a `.txt` file** in `rag/knowledge_base/`
2. Write your agricultural content in plain text
3. **Rebuild the FAISS index** via API:
   ```bash
   curl -X POST http://localhost:5000/api/rag/rebuild
   ```
   Or from the browser console:
   ```javascript
   fetch('/api/rag/rebuild', {method:'POST'}).then(r=>r.json()).then(console.log)
   ```

### File Format Guidelines

```
TOPIC TITLE
Source: Author/Organization
Last Updated: YYYY

=== SECTION HEADER ===
Content goes here...

=== ANOTHER SECTION ===
More content...
```

### Supported File Types

| Format | Status |
|--------|--------|
| `.txt` | ✅ Fully supported |
| `.pdf` | ⚙️ Requires `pypdf` (installed) |

---

## 🌐 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application |
| `/api/chat` | POST | Send message to AI |
| `/api/weather?location=` | GET | Get weather + advisory |
| `/api/market-prices?crop=&location=` | GET | Get mandi prices |
| `/api/crop-recommendation` | POST | Get crop recommendations |
| `/api/profiles` | GET/POST | List/create profiles |
| `/api/profiles/{id}` | GET/DELETE | Get/delete a profile |
| `/api/reports/generate` | POST | Generate farming report |
| `/api/reports/download/{filename}` | GET | Download report |
| `/api/reports/list` | GET | List all reports |
| `/api/rag/rebuild` | POST | Rebuild FAISS index |
| `/api/config` | GET | Agent configuration |
| `/api/health` | GET | Health check |

### Chat API Example

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My cotton crop has yellowing leaves. What should I do?",
    "language": "en",
    "location": "Warangal, Telangana"
  }'
```

---

## ☁️ IBM Cloud Deployment

### Option A — IBM Code Engine (Recommended)

1. **Install IBM Cloud CLI**:
   ```bash
   curl -fsSL https://clis.cloud.ibm.com/install/linux | sh
   ibmcloud plugin install code-engine
   ```

2. **Login and set up Code Engine**:
   ```bash
   ibmcloud login --apikey YOUR_IBM_API_KEY -r us-south
   ibmcloud ce project create --name krishimitra-project
   ibmcloud ce project select --name krishimitra-project
   ```

3. **Create a container image** (requires Docker):
   ```bash
   docker build -t krishimitra:latest .
   ibmcloud cr login
   docker tag krishimitra:latest us.icr.io/YOUR_NAMESPACE/krishimitra:latest
   docker push us.icr.io/YOUR_NAMESPACE/krishimitra:latest
   ```

4. **Deploy to Code Engine**:
   ```bash
   ibmcloud ce app create --name krishimitra \
     --image us.icr.io/YOUR_NAMESPACE/krishimitra:latest \
     --env IBM_API_KEY=your_key \
     --env IBM_PROJECT_ID=your_project_id \
     --env IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com \
     --env FLASK_SECRET_KEY=your_secret \
     --min-scale 1 --max-scale 3 \
     --cpu 1 --memory 4G
   ```

5. **Get your app URL**:
   ```bash
   ibmcloud ce app get --name krishimitra --output url
   ```

### Option B — IBM Cloud Foundry

```bash
# Install CF plugin
ibmcloud cf push krishimitra \
  --buildpack python_buildpack \
  -m 1G -k 2G \
  --no-start

# Set environment variables
ibmcloud cf set-env krishimitra IBM_API_KEY "your_key"
ibmcloud cf set-env krishimitra IBM_PROJECT_ID "your_id"
ibmcloud cf set-env krishimitra IBM_WATSONX_URL "https://us-south.ml.cloud.ibm.com"
ibmcloud cf set-env krishimitra FLASK_SECRET_KEY "your_secret"

# Start the app
ibmcloud cf start krishimitra
```

### Dockerfile (for Container Deployment)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p reports profiles rag/vector_store

EXPOSE 5000

CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120"]
```

---

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `IBM credentials not set` | Add `IBM_API_KEY` and `IBM_PROJECT_ID` to `.env` |
| `faiss-cpu` install fails | Try: `pip install faiss-cpu --no-cache-dir` |
| `sentence-transformers` slow first run | It downloads a 90MB model — wait for it |
| Weather shows "Demo Data" | Add `OPENWEATHER_API_KEY` to `.env` |
| Market prices are estimated | Add `AGMARKET_API_KEY` for live Agmarknet data |
| RAG not finding relevant info | Add more `.txt` files to `rag/knowledge_base/` and rebuild |
| Chat not responding | Check `IBM_API_KEY` and `IBM_PROJECT_ID` are correct |
| PDF not generated | Run `pip install reportlab fpdf2` separately |

### Running Without IBM Credentials

The application runs in **Demo Mode** without IBM credentials. In Demo Mode:
- The AI uses a built-in knowledge base with pre-written farming advice
- RAG retrieval still works for keyword-matched responses
- All other features (weather, market prices, profiles, reports) work normally
- To switch to IBM Granite AI: add your credentials to `.env` and restart

### Checking Application Health

```bash
curl http://localhost:5000/api/health
```

Response:
```json
{
  "status": "healthy",
  "agent": "KrishiMitra",
  "version": "2.0.0",
  "watsonx_connected": true,
  "rag_ready": true
}
```

---

## 📞 Support & Resources

| Resource | Link |
|----------|------|
| IBM watsonx.ai Docs | https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-overview.html |
| IBM Granite Models | https://www.ibm.com/granite |
| IBM Cloud Console | https://cloud.ibm.com |
| ICAR (Indian Agriculture) | https://www.icar.org.in |
| KVK Locator | https://kvk.icar.gov.in |
| Agmarknet Prices | https://agmarknet.gov.in |
| OpenWeatherMap | https://openweathermap.org/api |
| PM-Kisan Scheme | https://pmkisan.gov.in |

---

## 📜 License

MIT License — Free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- **IBM watsonx.ai** and **IBM Granite** models for AI capabilities
- **ICAR, SAU, KVK** for agricultural knowledge
- **Indian farmer community** for whom this tool is built

---

*Built with ❤️ for Indian farmers — Jai Kisan! 🌾*
