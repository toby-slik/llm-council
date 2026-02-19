import os
import sys
import traceback

# Get the path to the root directory
# Vercel's task executes from /var/task
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Now import the app
try:
    from backend.main import app
except Exception as e:
    # If the import fails, create a minimal app that reports the error
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    error_detail = traceback.format_exc()

    @app.get("/api/debug")
    async def debug():
        return {
            "error": str(e),
            "traceback": error_detail,
            "sys_path": sys.path,
            "root_dir": root_dir,
            "cwd": os.getcwd(),
            "files_in_root": os.listdir(root_dir) if os.path.exists(root_dir) else [],
        }

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    async def catch_all(path: str):
        return {
            "error": "Backend failed to start",
            "detail": str(e),
            "traceback": error_detail,
        }

# This is the variable Vercel looks for
handler = app
