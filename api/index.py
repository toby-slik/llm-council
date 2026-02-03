import os
import sys

# Get the absolute path to the root directory
# This ensures that 'backend' can be imported regardless of where the function starts
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from backend.main import app

# This exports 'app' so Vercel's Python builder can find the FastAPI instance
