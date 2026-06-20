"""
MongoDB connection manager using motor (async driver).
Collections: users, sessions, incidents, logs, reports
"""
import os

# Load .env before reading environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.environ.get("MONGODB_DB", "cyberguard_db")

client: AsyncIOMotorClient = None
db = None

# Collection references (set after connect)
users_collection = None
sessions_collection = None
incidents_collection = None
logs_collection = None
reports_collection = None


async def connect_to_mongodb():
    """Connect to MongoDB on startup. Prints status. Does NOT crash if unavailable."""
    global client, db
    global users_collection, sessions_collection, incidents_collection, logs_collection, reports_collection
    try:
        client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Force a connection attempt to verify MongoDB is reachable
        await client.admin.command("ping")
        db = client[MONGODB_DB]

        # Collection references
        users_collection = db["users"]
        sessions_collection = db["sessions"]
        incidents_collection = db["incidents"]
        logs_collection = db["logs"]
        reports_collection = db["reports"]

        # Create unique index on email
        await users_collection.create_index("email", unique=True)
        # Index on googleId for fast Google OAuth lookups
        await users_collection.create_index("googleId", sparse=True)
        # Index on session token for fast lookups
        await sessions_collection.create_index("token")
        # Index on incident_id
        await incidents_collection.create_index("incident_id")

        print(f"[OK] MongoDB connected to {MONGODB_DB}")
    except Exception as e:
        print(f"[WARNING] MongoDB connection failed: {e}")
        print("   FastAPI will continue WITHOUT MongoDB. Auth/history features will be unavailable.")
        client = None
        db = None


async def close_mongodb_connection():
    """Close MongoDB connection on shutdown."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")


def get_db():
    """Return the database instance (or None if not connected)."""
    return db
