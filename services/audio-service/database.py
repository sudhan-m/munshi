"""
MongoDB database connection and management for the audio service.

This module handles the MongoDB connection, collection management, and database
operations for storing audio metadata.
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    database = None
    audio_collection = None


mongodb = MongoDB()


async def connect_to_mongo():
    """Create database connection on startup."""
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_username = os.getenv("MONGODB_USERNAME", "root")
    mongodb_password = os.getenv("MONGODB_PASSWORD", "")
    
    if mongodb_username and mongodb_password:
        # Use authenticated connection
        mongodb.client = AsyncIOMotorClient(
            f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_url.split('://', 1)[1]}"
        )
    else:
        # Use unauthenticated connection for development
        mongodb.client = AsyncIOMotorClient(mongodb_url)
    
    mongodb.database = mongodb.client[os.getenv("MONGO_DB_NAME", "munshi_audio")]
    mongodb.audio_collection = mongodb.database["audio_recordings"]
    
    try:
        # Create indexes for better query performance
        await mongodb.audio_collection.create_index("user_id")
        await mongodb.audio_collection.create_index("created_at")
        print("Connected to MongoDB and created indexes")
    except Exception as e:
        print(f"Connected to MongoDB, but couldn't create indexes: {e}")
        # Continue anyway - indexes can be created manually if needed


async def close_mongo_connection():
    """Close database connection on shutdown."""
    if mongodb.client:
        mongodb.client.close()
        print("Disconnected from MongoDB")


def get_audio_collection():
    """Get the audio recordings collection."""
    return mongodb.audio_collection