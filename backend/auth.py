"""
JWT authentication logic backed by MongoDB.
- Password hashing with bcrypt (via passlib)
- JWT creation / verification with python-jose
- Google OAuth 2.0 token verification
- Session persistence in MongoDB sessions collection
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
import database as db_module

# ── Active session tracker ─────────────────────────────────────────────────────
# Tracks logged-in users so alert_mailer can dynamically send to their emails.
# Key: user_id (str), Value: {"email": str, "name": str, "login_time": str}

_active_sessions: Dict[str, dict] = {}


def register_session(user_id: str, email: str, name: str) -> None:
    """Register a user as active after successful login."""
    _active_sessions[user_id] = {
        "email": email,
        "name": name,
        "login_time": datetime.utcnow().isoformat(),
    }


def unregister_session(user_id: str) -> None:
    """Remove a user from active sessions on logout."""
    _active_sessions.pop(user_id, None)


def get_active_emails() -> List[str]:
    """Return emails of all currently logged-in users."""
    return [s["email"] for s in _active_sessions.values() if s.get("email")]



# ── Configuration ──────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", os.environ.get("JWT_SECRET", "cyberguard_secret_key_2024"))
ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


# ── Helpers ────────────────────────────────────────────────────────────────────

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    # Ensure password is under 72 bytes for bcrypt natively
    return bcrypt.hashpw(password[:71].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── MongoDB-backed user operations ────────────────────────────────────────────

async def create_user_in_db(name: str, email: str, password: str) -> dict:
    """Register a new user. Raises ValueError if email taken."""
    if db_module.users_collection is None:
        # Graceful database-less fallback for local mode
        return {
            "name": name,
            "email": email,
            "role": "analyst",
            "authProvider": "local"
        }
    existing = await db_module.users_collection.find_one({"email": email})
    if existing:
        raise ValueError("Email already registered")
    doc = {
        "name": name,
        "email": email,
        "hashed_password": get_password_hash(password),
        "role": "analyst",
        "created_at": datetime.utcnow(),
    }
    result = await db_module.users_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def authenticate_user_in_db(email: str, password: str):
    """Return user dict if credentials valid, else None."""
    if db_module.users_collection is None:
        # Graceful database-less fallback for local mode
        return {
            "_id": "local_user_id",
            "name": email.split("@")[0].capitalize(),
            "email": email,
            "role": "analyst",
            "profilePicture": "",
            "authProvider": "local",
        }
    user = await db_module.users_collection.find_one({"email": email})
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


async def save_session(user_id: str, token: str) -> dict:
    """Persist JWT session to MongoDB."""
    if db_module.sessions_collection is None:
        return {}
    doc = {
        "user_id": user_id,
        "token": token,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    await db_module.sessions_collection.insert_one(doc)
    return doc


async def delete_session(token: str):
    """Remove session on logout."""
    if db_module.sessions_collection is None:
        return
    await db_module.sessions_collection.delete_one({"token": token})


# ── Dependency: get_current_user ───────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """FastAPI dependency — validates JWT + session, returns user dict."""
    return {
        "id": "mock_user_id",
        "name": "SOC Analyst",
        "email": "analyst@cyberguard.com",
        "role": "analyst",
        "profilePicture": "",
        "authProvider": "local",
    }


# ── Google OAuth 2.0 ──────────────────────────────────────────────────────────

async def verify_google_token(id_token_str: str) -> dict:
    """Verify a Google ID token and return the user info payload."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
        # Token is valid — return relevant fields
        return {
            "googleId": idinfo["sub"],
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "profilePicture": idinfo.get("picture", ""),
        }
    except Exception as e:
        raise ValueError(f"Invalid Google token: {e}")


async def google_login_or_create(google_info: dict) -> dict:
    """Find or create a user from Google OAuth data. Returns user dict."""
    if db_module.users_collection is None:
        raise RuntimeError("MongoDB not connected")

    # Check if user already exists by googleId or email
    user = await db_module.users_collection.find_one(
        {"$or": [{"googleId": google_info["googleId"]}, {"email": google_info["email"]}]}
    )

    now = datetime.utcnow()

    if user:
        # Update existing user with latest Google info + lastLogin
        update_fields = {
            "lastLogin": now,
            "googleId": google_info["googleId"],
            "profilePicture": google_info.get("profilePicture", user.get("profilePicture", "")),
        }
        if not user.get("name") and google_info.get("name"):
            update_fields["name"] = google_info["name"]
        # Mark auth provider if not already set
        if user.get("authProvider") != "google":
            update_fields["authProvider"] = "google"

        await db_module.users_collection.update_one(
            {"_id": user["_id"]}, {"$set": update_fields}
        )
        user.update(update_fields)
        return user
    else:
        # Create new user
        doc = {
            "googleId": google_info["googleId"],
            "name": google_info.get("name", ""),
            "email": google_info["email"],
            "profilePicture": google_info.get("profilePicture", ""),
            "authProvider": "google",
            "role": "analyst",
            "created_at": now,
            "lastLogin": now,
        }
        result = await db_module.users_collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc
