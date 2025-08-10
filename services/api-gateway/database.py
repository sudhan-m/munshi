"""
Database models and connection management for the API Gateway service.

This module defines the database schema for the gateway's dedicated database,
including service registry, rate limiting, and request logging tables. The
gateway maintains its own isolated database separate from other microservices.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

from config import get_gateway_settings

settings = get_gateway_settings()

engine = create_engine(settings.gateway_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ServiceRegistry(Base):
    """
    SQLAlchemy model for the service registry table.
    
    Stores information about registered microservices including their URLs,
    health status, and metadata. Used for service discovery and load balancing.
    
    Attributes:
        id: Primary key identifier
        service_name: Unique name of the registered service
        service_url: Base URL where the service can be accessed
        health_check_url: Optional health check endpoint URL
        is_active: Whether the service is currently active
        last_health_check: Timestamp of last successful health check
        created_at: Service registration timestamp
        updated_at: Last modification timestamp
    """
    __tablename__ = "service_registry"
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, unique=True, index=True, nullable=False)
    service_url = Column(String, nullable=False)
    health_check_url = Column(String)
    is_active = Column(Boolean, default=True)
    last_health_check = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RateLimitEntry(Base):
    """
    SQLAlchemy model for rate limiting entries.
    
    Tracks request counts per client and endpoint for rate limiting enforcement.
    Entries are cleaned up periodically based on the time window configuration.
    
    Attributes:
        id: Primary key identifier
        client_id: Identifier for the client (IP address or user ID)
        endpoint: API endpoint being accessed
        requests_count: Number of requests in the current window
        window_start: Start time of the current rate limiting window
        created_at: Entry creation timestamp
    """
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, index=True, nullable=False)  # IP or user ID
    endpoint = Column(String, index=True, nullable=False)
    requests_count = Column(Integer, default=1)
    window_start = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RequestLog(Base):
    """
    SQLAlchemy model for HTTP request logging.
    
    Stores detailed information about HTTP requests processed by the gateway
    for monitoring, debugging, and analytics purposes.
    
    Attributes:
        id: Primary key identifier
        request_id: Unique identifier for the request
        method: HTTP method (GET, POST, etc.)
        path: Request path/endpoint
        user_id: Authenticated user ID (if available)
        client_ip: Client IP address
        user_agent: Client user agent string
        status_code: HTTP response status code
        response_time: Request processing time in seconds
        created_at: Request timestamp
    """
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True)
    method = Column(String, nullable=False)
    path = Column(String, nullable=False)
    user_id = Column(String)
    client_ip = Column(String)
    user_agent = Column(String)
    status_code = Column(Integer)
    response_time = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def get_gateway_db() -> Generator[Session, None, None]:
    """
    Database dependency for API Gateway endpoints.
    
    Creates and manages database sessions for the gateway's dedicated database.
    Used as a dependency injection for endpoints that need database access.
    
    Yields:
        Session: SQLAlchemy database session for the gateway database
        
    Example:
        @app.get("/services/")
        def get_services(db: Session = Depends(get_gateway_db)):
            return db.query(ServiceRegistry).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_gateway_tables():
    """
    Create all database tables for the API Gateway service.
    
    This function creates the service registry, rate limiting, and request
    logging tables in the gateway's dedicated database. Should be called
    on service startup.
    
    Note:
        Only creates tables that don't already exist. Safe to call multiple times.
    """
    Base.metadata.create_all(bind=engine)