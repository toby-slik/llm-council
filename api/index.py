import os
import sys

# Get the path to the root directory
# Vercel's task executes from /var/task
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Now import the app
from backend.main import app

# This is the variable Vercel looks for
handler = app
