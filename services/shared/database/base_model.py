"""
Base database models and mixins for microservices.

Provides common database model patterns and utilities that can be
reused across all services.
"""

from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr
import logging

logger = logging.getLogger(__name__)

# Base class for all database models
BaseModel = declarative_base()


class TimestampMixin:
    """
    Mixin to add created_at and updated_at timestamps to models.
    """
    
    @declared_attr
    def created_at(cls):
        return Column(
            DateTime,
            default=func.now(),
            nullable=False,
            comment="Record creation timestamp"
        )
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=True,
            comment="Record last update timestamp"
        )


class IDMixin:
    """
    Mixin to add auto-incrementing ID primary key.
    """
    
    @declared_attr
    def id(cls):
        return Column(
            Integer,
            primary_key=True,
            autoincrement=True,
            comment="Auto-incrementing primary key"
        )


class BaseServiceModel(BaseModel, IDMixin, TimestampMixin):
    """
    Base model class for all service models.
    
    Includes:
    - Auto-incrementing ID primary key
    - Created/updated timestamps
    - Common utility methods
    """
    
    __abstract__ = True
    
    def to_dict(self, exclude_fields: list = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Args:
            exclude_fields: List of field names to exclude
            
        Returns:
            Dictionary representation of model
        """
        exclude_fields = exclude_fields or []
        
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)
                # Convert datetime objects to ISO format
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude_fields: list = None):
        """
        Update model instance from dictionary.
        
        Args:
            data: Dictionary of field values
            exclude_fields: List of field names to exclude from update
        """
        exclude_fields = exclude_fields or ['id', 'created_at']
        
        for key, value in data.items():
            if key not in exclude_fields and hasattr(self, key):
                setattr(self, key, value)
        
        # Update the updated_at timestamp
        if hasattr(self, 'updated_at'):
            self.updated_at = datetime.utcnow()
    
    @classmethod
    def get_table_name(cls) -> str:
        """Get the table name for this model."""
        return cls.__tablename__
    
    @classmethod
    def get_columns(cls) -> list:
        """Get list of column names for this model."""
        return [column.name for column in cls.__table__.columns]
    
    def __repr__(self) -> str:
        """String representation of model instance."""
        class_name = self.__class__.__name__
        if hasattr(self, 'id'):
            return f"<{class_name}(id={self.id})>"
        return f"<{class_name}()>"


class AuditMixin:
    """
    Mixin to add audit fields for tracking changes.
    """
    
    @declared_attr
    def created_by(cls):
        return Column(
            Integer,
            nullable=True,
            comment="ID of user who created this record"
        )
    
    @declared_attr
    def updated_by(cls):
        return Column(
            Integer,
            nullable=True,
            comment="ID of user who last updated this record"
        )
    
    def set_audit_info(self, user_id: int, is_create: bool = False):
        """
        Set audit information for create/update operations.
        
        Args:
            user_id: ID of the user performing the operation
            is_create: Whether this is a create operation
        """
        if is_create and hasattr(self, 'created_by'):
            self.created_by = user_id
        
        if hasattr(self, 'updated_by'):
            self.updated_by = user_id


class SoftDeleteMixin:
    """
    Mixin to add soft delete functionality.
    """
    
    @declared_attr
    def deleted_at(cls):
        return Column(
            DateTime,
            nullable=True,
            comment="Soft delete timestamp"
        )
    
    @declared_attr
    def is_deleted(cls):
        return Column(
            "is_deleted",
            nullable=False,
            default=False,
            comment="Soft delete flag"
        )
    
    def soft_delete(self, user_id: int = None):
        """
        Perform soft delete on this record.
        
        Args:
            user_id: ID of user performing the deletion
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        
        if user_id and hasattr(self, 'updated_by'):
            self.updated_by = user_id
    
    def restore(self, user_id: int = None):
        """
        Restore a soft-deleted record.
        
        Args:
            user_id: ID of user performing the restoration
        """
        self.is_deleted = False
        self.deleted_at = None
        
        if user_id and hasattr(self, 'updated_by'):
            self.updated_by = user_id


class BaseServiceModelWithAudit(BaseServiceModel, AuditMixin):
    """
    Base model with audit fields for services that need user tracking.
    """
    __abstract__ = True


class BaseServiceModelWithSoftDelete(BaseServiceModel, SoftDeleteMixin):
    """
    Base model with soft delete for services that need to retain data.
    """
    __abstract__ = True


class BaseServiceModelFull(BaseServiceModel, AuditMixin, SoftDeleteMixin):
    """
    Full-featured base model with timestamps, audit, and soft delete.
    """
    __abstract__ = True