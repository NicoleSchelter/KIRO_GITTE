"""
Centralized Database Factory - Single Source of Truth
Replaces scattered engine/session creation with unified management
"""

import logging
import threading
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config.config import config

logger = logging.getLogger(__name__)

class DatabaseFactory:
    """Singleton database factory ensuring single engine/session management"""
    
    _instance: Optional['DatabaseFactory'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'DatabaseFactory':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize database engine and session factory (idempotent)"""
        if self._initialized:
            logger.debug("Database factory already initialized")
            return
            
        with self._lock:
            if self._initialized:
                return
                
            try:
                # Create engine with unified configuration
                engine_kwargs = {
                    "pool_size": config.database.pool_size,
                    "max_overflow": config.database.max_overflow,
                    "echo": config.database.echo,
                    "pool_pre_ping": True,
                }
                
                # Handle SQLite vs PostgreSQL
                if config.database.dsn.startswith("sqlite"):
                    engine_kwargs.update({
                        "poolclass": StaticPool,
                        "connect_args": {"check_same_thread": False}
                    })
                    engine_kwargs.pop("pool_size", None)
                    engine_kwargs.pop("max_overflow", None)
                
                self._engine = create_engine(config.database.dsn, **engine_kwargs)
                self._setup_connection_events()
                
                # Create session factory
                self._session_factory = sessionmaker(
                    bind=self._engine,
                    autocommit=False,
                    autoflush=False,
                    expire_on_commit=False
                )
                
                self._initialized = True
                logger.info("Database factory initialized with DSN: %s", 
                           self._mask_dsn(config.database.dsn))
                
            except Exception as e:
                logger.error("Failed to initialize database factory: %s", e)
                raise
    
    def _setup_connection_events(self) -> None:
        """Setup SQLAlchemy connection event listeners"""
        
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if "sqlite" in config.database.dsn:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
        
        @event.listens_for(self._engine, "connect")
        def set_postgresql_settings(dbapi_connection, connection_record):
            if "postgresql" in config.database.dsn:
                cursor = dbapi_connection.cursor()
                cursor.execute("SET timezone TO 'UTC'")
                cursor.close()
    
    @staticmethod
    def _mask_dsn(dsn: str) -> str:
        """Mask password in DSN for logging"""
        import re
        return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1****\3', dsn)
    
    @property
    def engine(self) -> Engine:
        """Get database engine (lazy initialization)"""
        if not self._initialized:
            self.initialize()
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get session factory (lazy initialization)"""
        if not self._initialized:
            self.initialize()
        return self._session_factory
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic transaction management"""
        if not self._initialized:
            self.initialize()
            
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Database session error: %s", e)
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get database session for synchronous use (caller must close)"""
        if not self._initialized:
            self.initialize()
        return self._session_factory()
    
    def health_check(self) -> bool:
        """Check database connection health"""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database health check failed: %s", e)
            return False
    
    def create_all_tables(self) -> None:
        """Create all database tables"""
        from .models import Base
        
        if not self._initialized:
            self.initialize()
            
        try:
            Base.metadata.create_all(bind=self._engine)
            logger.info("All database tables created successfully")
        except Exception as e:
            logger.error("Failed to create database tables: %s", e)
            raise
    
    def close(self) -> None:
        """Close database connections and reset factory"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")
        
        self._engine = None
        self._session_factory = None
        self._initialized = False

# Global factory instance
_db_factory = DatabaseFactory()

# Public API functions (backward compatibility)
def get_session() -> Generator[Session, None, None]:
    """Get database session context manager"""
    return _db_factory.get_session()

def get_session_sync() -> Session:
    """Get database session for synchronous use"""
    return _db_factory.get_session_sync()

def initialize_database() -> None:
    """Initialize database connection"""
    _db_factory.initialize()

def create_all_tables() -> None:
    """Create all database tables"""
    _db_factory.create_all_tables()

def health_check() -> bool:
    """Check database health"""
    return _db_factory.health_check()

def close_database() -> None:
    """Close database connections"""
    _db_factory.close()

def setup_database() -> None:
    """Complete database setup for application startup"""
    logger.info("Setting up database...")
    
    try:
        initialize_database()
        create_all_tables()
        
        if not health_check():
            raise RuntimeError("Database health check failed")
            
        logger.info("Database setup completed successfully")
        
    except Exception as e:
        logger.error("Database setup failed: %s", e)
        raise

# Context manager for transactions
@contextmanager
def database_transaction() -> Generator[Session, None, None]:
    """Context manager for database transactions"""
    with get_session() as session:
        yield session