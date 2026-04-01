import json
import os
from pathlib import Path

# Anchor data dir relative to this file so it works regardless of cwd
_HERE = Path(__file__).parent.parent  # project root
DATA_DIR = _HERE / "data"
DATA_DIR.mkdir(exist_ok=True)
PAID_USERS_FILE = DATA_DIR / "paid_users.json"


def _load_paid_users() -> set:
    if not PAID_USERS_FILE.exists():
        return set()
    try:
        with open(PAID_USERS_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("paid_users", []))
    except Exception:
        return set()

def _save_paid_users(users: set):
    with open(PAID_USERS_FILE, "w") as f:
        json.dump({"paid_users": list(users)}, f, indent=2)

def is_user_paid(user_id: str) -> bool:
    """Check if the given clerk user_id has paid."""
    if not user_id:
        return False
    users = _load_paid_users()
    return user_id in users

def mark_user_paid(user_id: str):
    """Mark the given clerk user_id as paid."""
    users = _load_paid_users()
    users.add(user_id)
    _save_paid_users(users)
