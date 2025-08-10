"""
Database configuration and connection management for the authentication service.

This module handles the database connection, session management, and table
creation for the auth service's dedicated PostgreSQL database. Each microservice
maintains its own isolated database for security and scalability.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

from config import get_auth_settings

settings = get_auth_settings()

engine = create_engine(settings.auth_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI endpoints.
    
    Creates and manages database sessions with proper cleanup.
    Used as a dependency injection for endpoints that need database access.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        @app.get("/users/")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables for the authentication service.
    
    This function creates the user table and any other auth-related tables
    in the dedicated auth database. Should be called on service startup.
    
    Note:
        Only creates tables that don't already exist. Safe to call multiple times.
    """
    from models import Base
    Base.metadata.create_all(bind=engine)