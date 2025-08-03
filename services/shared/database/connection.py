"""
Database connection management for microservices.

Provides common database connection patterns, session management,
and utilities for SQLAlchemy across services.
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Generator, AsyncGenerator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from .base_model import BaseModel

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database connection manager for microservices.
    
    Provides connection pooling, session management, and health checks.
    """
    
    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600
    ):
        """
        Initialize database manager.
        
        Args:
            database_url: SQLAlchemy database URL
            echo: Enable SQL query logging
            pool_size: Base connection pool size
            max_overflow: Maximum overflow connections
            pool_timeout: Pool timeout in seconds
            pool_recycle: Connection recycle time in seconds
        """
        self.database_url = database_url
        self.echo = echo
        
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                database_url,
                echo=echo,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,  # Validate connections before use
                connect_args={
                    "options": "-c timezone=utc"  # Set timezone for PostgreSQL
                }
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Add connection event listeners
            self._setup_event_listeners()
            
            logger.info(f"Database manager initialized for {self._mask_url(database_url)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise
    
    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in database URL for logging."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.password:
                masked_url = url.replace(parsed.password, "***")
                return masked_url
            return url
        except Exception:
            return "***"
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring."""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set database-specific connection options."""
            if "sqlite" in self.database_url:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout."""
            logger.debug("Database connection checked out")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin."""
            logger.debug("Database connection checked in")
    
    def create_tables(self):
        """Create all tables defined in BaseModel."""
        try:
            BaseModel.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables (use with caution!)."""
        try:
            BaseModel.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Perform database health check.
        
        Returns:
            True if database is healthy, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Yields:
            SQLAlchemy session object
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_dependency(self) -> Generator[Session, None, None]:
        """
        FastAPI dependency function for database sessions.
        
        Yields:
            SQLAlchemy session object
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def execute_transaction(self, operations: list, session: Optional[Session] = None):
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of functions that take a session parameter
            session: Optional existing session to use
        """
        if session:
            # Use existing session
            for operation in operations:
                operation(session)
        else:
            # Create new session with transaction
            with self.get_session() as session:
                for operation in operations:
                    operation(session)
    
    def get_connection_info(self) -> dict:
        """
        Get database connection information.
        
        Returns:
            Dictionary with connection details
        """
        try:
            pool = self.engine.pool
            return {
                "url": self._mask_url(self.database_url),
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "is_healthy": self.health_check()
            }
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Close all database connections."""
        try:
            self.engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


class DatabaseRepository:
    """
    Base repository class for database operations.
    
    Provides common CRUD operations that can be extended by service-specific
    repositories.
    """
    
    def __init__(self, db_manager: DatabaseManager, model_class):
        self.db_manager = db_manager
        self.model_class = model_class
    
    def create(self, data: dict, user_id: int = None) -> object:
        """
        Create a new record.
        
        Args:
            data: Dictionary of field values
            user_id: ID of user creating the record
            
        Returns:
            Created model instance
        """
        with self.db_manager.get_session() as session:
            instance = self.model_class(**data)
            
            # Set audit information if available
            if user_id and hasattr(instance, 'set_audit_info'):
                instance.set_audit_info(user_id, is_create=True)
            
            session.add(instance)
            session.flush()  # Get the ID
            session.refresh(instance)
            
            return instance
    
    def get_by_id(self, record_id: int) -> Optional[object]:
        """
        Get record by ID.
        
        Args:
            record_id: Record ID
            
        Returns:
            Model instance or None if not found
        """
        with self.db_manager.get_session() as session:
            return session.query(self.model_class).filter(
                self.model_class.id == record_id
            ).first()
    
    def update(self, record_id: int, data: dict, user_id: int = None) -> Optional[object]:
        """
        Update a record by ID.
        
        Args:
            record_id: Record ID
            data: Dictionary of field values to update
            user_id: ID of user updating the record
            
        Returns:
            Updated model instance or None if not found
        """
        with self.db_manager.get_session() as session:
            instance = session.query(self.model_class).filter(
                self.model_class.id == record_id
            ).first()
            
            if not instance:
                return None
            
            instance.update_from_dict(data)
            
            # Set audit information if available
            if user_id and hasattr(instance, 'set_audit_info'):
                instance.set_audit_info(user_id, is_create=False)
            
            session.flush()
            session.refresh(instance)
            
            return instance
    
    def delete(self, record_id: int, user_id: int = None, soft_delete: bool = True) -> bool:
        """
        Delete a record by ID.
        
        Args:
            record_id: Record ID
            user_id: ID of user deleting the record
            soft_delete: Use soft delete if available
            
        Returns:
            True if deleted, False if not found
        """
        with self.db_manager.get_session() as session:
            instance = session.query(self.model_class).filter(
                self.model_class.id == record_id
            ).first()
            
            if not instance:
                return False
            
            if soft_delete and hasattr(instance, 'soft_delete'):
                instance.soft_delete(user_id)
            else:
                session.delete(instance)
            
            return True
    
    def list(self, limit: int = 100, offset: int = 0, filters: dict = None) -> list:
        """
        List records with pagination and filtering.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            filters: Dictionary of filter conditions
            
        Returns:
            List of model instances
        """
        with self.db_manager.get_session() as session:
            query = session.query(self.model_class)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model_class, field):
                        query = query.filter(getattr(self.model_class, field) == value)
            
            # Apply soft delete filter if available
            if hasattr(self.model_class, 'is_deleted'):
                query = query.filter(self.model_class.is_deleted == False)
            
            return query.offset(offset).limit(limit).all()
    
    def count(self, filters: dict = None) -> int:
        """
        Count records with optional filtering.
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            Number of matching records
        """
        with self.db_manager.get_session() as session:
            query = session.query(self.model_class)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model_class, field):
                        query = query.filter(getattr(self.model_class, field) == value)
            
            # Apply soft delete filter if available
            if hasattr(self.model_class, 'is_deleted'):
                query = query.filter(self.model_class.is_deleted == False)
            
            return query.count()