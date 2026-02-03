import os
import sys

# Add the project root to the Python path so Vercel can find the 'backend' package
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.main import app

# This allows Vercel to find the FastAPI instance
# Vercel expects the app to be available as 'app' in the entry file
