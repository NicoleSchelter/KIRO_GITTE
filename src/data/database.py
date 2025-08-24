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

# Backward compatibility - delegate to factory
class DatabaseManager:
    """DEPRECATED: Use database_factory instead."""
    
    def __init__(self):
        logger.warning("DatabaseManager is deprecated, use database_factory")
        
    def initialize(self) -> None:
        return factory_initialize_database()
    
    @property
    def engine(self):
        return _db_factory.engine
    
    @property
    def session_factory(self):
        return _db_factory.session_factory
    
    def create_all_tables(self) -> None:
        return factory_create_all_tables()
    
    def drop_all_tables(self) -> None:
        # Not implemented in factory for safety
        raise NotImplementedError("Use database_factory for table operations")
    
    def get_session(self) -> Generator[Session, None, None]:
        return factory_get_session()
    
    def get_session_sync(self) -> Session:
        return factory_get_session_sync()
    
    def health_check(self) -> bool:
        return factory_health_check()
    
    def close(self) -> None:
        return factory_close_database()

# Global database manager instance (deprecated)
db_manager = DatabaseManager()

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
