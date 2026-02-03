import os
import sys

# Add the project root to the Python path
# Vercel's current working directory is the project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from backend.main import app
except ImportError as e:
    # If imports fail, create a fallback app to report the error
    from fastapi import FastAPI
    app = FastAPI()
    @app.get("/api/health")
    async def health():
        return {"status": "error", "message": str(e), "path": sys.path}
