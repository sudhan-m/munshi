"""
Database connection and operations for conversation service.
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# MongoDB connection
client: Optional[AsyncIOMotorClient] = None
database = None

async def connect_to_mongo():
    """Create database connection."""
    global client, database
    
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "munshi_conversations")
    
    client = AsyncIOMotorClient(mongodb_url)
    database = client[database_name]
    
    print(f"Connected to MongoDB: {database_name}")

async def close_mongo_connection():
    """Close database connection."""
    global client
    if client:
        client.close()
        print("Disconnected from MongoDB")

def get_conversations_collection():
    """Get conversations collection."""
    return database.conversations

def get_users_collection():
    """Get users collection."""
    return database.users

def get_sessions_collection():
    """Get sessions collection."""
    return database.sessions