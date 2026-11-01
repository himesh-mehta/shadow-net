"""
Database layer for SHADOW-NET.
Manages asynchronous MongoDB connection via motor with automatic fallback
to mongomock-motor for standalone development and testing when MongoDB is offline.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

logger = logging.getLogger("shadow_net.db")

class DatabaseManager:
    client: AsyncIOMotorClient = None
    db = None
    is_mock: bool = False

db_manager = DatabaseManager()


async def connect_to_mongo():
    """Connect to MongoDB or fallback to in-memory mock client."""
    settings = get_settings()
    logger.info("Connecting to configured MongoDB...")

    try:
        # Attempt connecting to real MongoDB with a fast 2-second server selection timeout
        real_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=2000,
        )
        # Verify connection
        await real_client.admin.command("ping")
        db_manager.client = real_client
        db_manager.db = real_client[settings.MONGODB_DB_NAME]
        db_manager.is_mock = False
        logger.info("Successfully connected to live MongoDB instance.")
    except Exception as exc:
        logger.warning(
            f"Live MongoDB unreachable ({exc}). Falling back to in-memory AsyncMongoMockClient for dev/testing."
        )
        try:
            from mongomock_motor import AsyncMongoMockClient
            mock_client = AsyncMongoMockClient()
            db_manager.client = mock_client
            db_manager.db = mock_client[settings.MONGODB_DB_NAME]
            db_manager.is_mock = True
            logger.info("In-memory MongoDB mock client initialized.")
        except ImportError:
            logger.error("mongomock-motor not found. Database operations will fail.")
            raise exc

    # Ensure indexes on key collections
    await init_indexes()
    if db_manager.is_mock:
        await seed_demo_users()


async def close_mongo_connection():
    """Close MongoDB connection gracefully."""
    if db_manager.client is not None:
        db_manager.client.close()
        logger.info("MongoDB connection closed.")


async def init_indexes():
    """Create essential indexes for performance and uniqueness."""
    if db_manager.db is None:
        return

    try:
        # Users indexes
        await db_manager.db.users.create_index("username", unique=True)
        await db_manager.db.users.create_index("email", unique=True)

        # Sessions indexes
        await db_manager.db.sessions.create_index("session_id", unique=True)
        await db_manager.db.sessions.create_index("user_id")
        await db_manager.db.sessions.create_index("status")

        # Incidents indexes
        await db_manager.db.incidents.create_index("incident_id", unique=True)
        await db_manager.db.incidents.create_index("session_id")
        await db_manager.db.incidents.create_index("timestamp")

        # Settings index
        await db_manager.db.settings.create_index("scope", unique=True)
    except Exception as e:
        logger.warning(f"Index creation notice: {e}")


def get_db():
    """Dependency getter for the database instance."""
    return db_manager.db


async def seed_demo_users():
    """Predictable public demo accounts, only in temporary mock storage."""
    import uuid
    from datetime import datetime
    from app.routers.auth import get_password_hash
    accounts = [("alex.vance", "admin123456", "Administrator"),
                ("sarah.chen", "analyst123456", "Security Analyst"),
                ("james.wilson", "user123456", "User")]
    for username, password, role in accounts:
        if await db_manager.db.users.find_one({"username": username}):
            continue
        await db_manager.db.users.insert_one({
            "id": str(uuid.uuid4()), "username": username, "email": username + "@example.com",
            "hashed_password": get_password_hash(password), "role": role,
            "is_active": True, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
        })
