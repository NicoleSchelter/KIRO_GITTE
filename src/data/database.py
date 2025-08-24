"""
Database connection and session management for GITTE system.
DEPRECATED: Use src.data.database_factory for new code.
Provides backward compatibility wrapper.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

# Import from centralized factory
from .database_factory import (
    _db_factory,
    get_session as factory_get_session,
    get_session_sync as factory_get_session_sync,
    initialize_database as factory_initialize_database,
    create_all_tables as factory_create_all_tables,
    health_check as factory_health_check,
    close_database as factory_close_database,
    setup_database as factory_setup_database,
    database_transaction as factory_database_transaction,
)

logger = logging.getLogger(__name__)

# Legacy compatibility layer - use database_factory directly for new code

# Public API functions (backward compatibility)
def get_session() -> Generator[Session, None, None]:
    """Get database session context manager."""
    return factory_get_session()

def get_session_sync() -> Session:
    """Get database session for synchronous use."""
    return factory_get_session_sync()

def initialize_database() -> None:
    """Initialize database connection."""
    return factory_initialize_database()

def create_all_tables() -> None:
    """Create all database tables."""
    return factory_create_all_tables()

def health_check() -> bool:
    """Check database health."""
    return factory_health_check()

def close_database() -> None:
    """Close database connections."""
    return factory_close_database()

def setup_database() -> None:
    """Set up database for application startup."""
    return factory_setup_database()

@contextmanager
def database_transaction() -> Generator[Session, None, None]:
    """Context manager for database transactions."""
    return factory_database_transaction()
