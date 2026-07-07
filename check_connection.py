"""
check_connection.py — Diagnose IBM watsonx.ai connection
Run: python check_connection.py
"""
from dotenv import load_dotenv
import os, requests

load_dotenv(".env")

api_key    = os.getenv("IBM_API_KEY", "")
url        = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
project_id = os.getenv("IBM_PROJECT_ID", "")

if not api_key:
    print("ERROR: IBM_API_KEY not found in .env file")
    exit(1)

print("=" * 60)
print("IBM watsonx.ai Connection Diagnostics")
print("=" * 60)
print(f"API Key    : {api_key[:12]}...{api_key[-4:]}")
print(f"URL        : {url}")
print(f"Project ID : {project_id}")
print()

# Step 1: Authenticate with IBM IAM
print("Step 1: Authenticating with IBM Cloud IAM...")
try:
    iam_resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    if iam_resp.status_code != 200:
        print(f"  FAILED: HTTP {iam_resp.status_code}")
        print(f"  {iam_resp.text[:300]}")
        exit(1)
    token = iam_resp.json()["access_token"]
    print("  SUCCESS - API key is valid")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

# Step 2: Verify project exists and check its services
print()
print(f"Step 2: Checking project {project_id}...")
try:
    proj_resp = requests.get(
        f"https://api.dataplatform.cloud.ibm.com/v2/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if proj_resp.status_code == 200:
        pdata = proj_resp.json()
        name = pdata.get("entity", {}).get("name", "Unknown")
        print(f"  SUCCESS - Project found: '{name}'")

        # Check for WML service
        services = pdata.get("entity", {}).get("storage", {})
        compute = pdata.get("entity", {}).get("compute", [])
        print(f"  Associated services: {len(compute)} found")
        if compute:
            for svc in compute:
                print(f"    - {svc.get('name','?')} [{svc.get('type','?')}]")
        else:
            print("  WARNING: No Watson Machine Learning service associated!")
            print("  --> You need to add WML service to this project.")
    else:
        print(f"  HTTP {proj_resp.status_code}: {proj_resp.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Step 3: Test model call
print()
print("Step 3: Testing IBM Granite model call (chat API)...")
try:
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    model_id = os.getenv("WATSONX_MODEL_ID", "ibm/granite-4-h-small")
    model = ModelInference(
        model_id=model_id,
        credentials=Credentials(url=url, api_key=api_key),
        project_id=project_id,
        params={"max_tokens": 80, "temperature": 0.3},
    )
    messages = [
        {"role": "system", "content": "You are KrishiMitra, an AI farming advisor for Indian farmers."},
        {"role": "user",   "content": "What is the best crop to grow in black cotton soil during Kharif? One sentence."},
    ]
    response = model.chat(messages=messages)
    result = response["choices"][0]["message"]["content"]
    print(f"  Model     : {model_id}")
    print(f"  Response  : {result.strip()}")
    print()
    print("  *** SUCCESS - IBM watsonx.ai is FULLY CONNECTED! ***")
    print()
    print("  Now run:  python app.py")
    print("  Open:     http://localhost:5000")
    print("  Status badge will show: IBM Granite  (not Demo Mode)")
except Exception as e:
    err = str(e)
    print(f"  FAILED: {err[:200]}")
    if "no_associated_service_instance" in err:
        print("  --> Associate Watson Machine Learning / watsonx.ai Runtime to your project.")
    elif "not supported" in err or "model_not_supported" in err:
        print("  --> Model not available. Check WATSONX_MODEL_ID in .env")

print()
print("=" * 60)
