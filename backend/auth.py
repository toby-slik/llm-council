import os
import json
import httpx
from dotenv import load_dotenv
from typing import Optional
from fastapi import Request, HTTPException
from jose import jwt

load_dotenv()

JWKS_CACHE = None

def get_clerk_jwks_url() -> str:
    """Derive the public JWKS URL from the Clerk publishable key."""
    import base64
    pub_key = os.getenv("VITE_CLERK_PUBLISHABLE_KEY", "")
    # Strip pk_test_ or pk_live_ prefix, then base64-decode to get the clerk domain
    raw = pub_key.replace("pk_test_", "").replace("pk_live_", "")
    try:
        # Pad to multiple of 4 for valid base64
        padding = "=" * (-len(raw) % 4)
        decoded = base64.b64decode(raw + padding).decode("utf-8").rstrip("$")
        return f"https://{decoded}/.well-known/jwks.json"
    except Exception:
        # Fallback for development
        return "https://api.clerk.com/v1/jwks"

async def get_clerk_jwks():
    global JWKS_CACHE
    if JWKS_CACHE:
        return JWKS_CACHE
    
    url = get_clerk_jwks_url()
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            JWKS_CACHE = response.json()
            return JWKS_CACHE
        else:
            print(f"Failed to fetch JWKS from {url}: {response.text}")
            return None

async def verify_clerk_token(token: str) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
        
    jwks = await get_clerk_jwks()
    if not jwks:
        raise HTTPException(status_code=500, detail="Could not fetch JWKS")
        
    try:
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        # Find the matching key in JWKS
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Invalid token signature")
            
        # Verify the token
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            # You could add audience verification here if needed
            options={"verify_aud": False}
        )
        return payload
    except Exception as e:
        print(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

async def get_current_user(request: Request) -> Optional[dict]:
    """Dependency to get the current authenticated user from Clerk."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    token = auth_header.split(" ")[1]
    payload = await verify_clerk_token(token)
    return payload
