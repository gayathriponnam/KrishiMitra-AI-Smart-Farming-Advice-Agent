# =============================================================================
# wsgi.py — Production WSGI entry point for Gunicorn / IBM Code Engine
# =============================================================================
from app import app

if __name__ == "__main__":
    app.run()
