import os
import sys

# Add the project root to the Python path
# Vercel's current working directory is the project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import the FastAPI app
try:
    from backend.main import app
except ImportError as e:
    # This part should only run if there's a serious path issue
    from fastapi import FastAPI
    app = FastAPI()
    @app.get("/api/error")
    def error():
        return {"error": str(e), "sys_path": sys.path}

# Vercel's Python builder looks for 'app' or 'handler'
# If it's a FastAPI/ASGI app, it finds the 'app' variable.
