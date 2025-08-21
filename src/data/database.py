"""
Database connection and session management for GITTE system.
Provides SQLAlchemy engine, session factory, and connection utilities.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config.config import config

from .models import Base

logger = logging.getLogger(__name__)

# after logger = logging.getLogger(__name__)
import re
def _mask_dsn(dsn: str) -> str:
    # mask password in URLs like postgresql://user:pass@host/db
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1****\3', dsn)


class DatabaseManager:
    """Database connection and session manager."""

    def __init__(self):
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize database connection and session factory."""
        if self._initialized:
            logger.warning("Database already initialized")
            return

        try:
            # Create engine with configuration
            engine_kwargs = {
                "pool_size": config.database.pool_size,
                "max_overflow": config.database.max_overflow,
                "echo": config.database.echo,
                "pool_pre_ping": True,  # Verify connections before use
            }

            # For SQLite (testing), use different pool settings
            if config.database.dsn.startswith("sqlite"):
                engine_kwargs.update(
                    {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
                )
                # Remove PostgreSQL-specific settings
                engine_kwargs.pop("pool_size", None)
                engine_kwargs.pop("max_overflow", None)

            self._engine = create_engine(config.database.dsn, **engine_kwargs)
            logger.info("Database DSN in use: %s", _mask_dsn(config.database.dsn))

            # Add connection event listeners
            self._setup_connection_events()

            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine, autocommit=False, autoflush=False, expire_on_commit=False
            )

            self._initialized = True
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _setup_connection_events(self) -> None:
        """Set up SQLAlchemy connection event listeners."""

        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance and consistency."""
            if "sqlite" in config.database.dsn:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()

        @event.listens_for(self._engine, "connect")
        def set_postgresql_settings(dbapi_connection, connection_record):
            """Set PostgreSQL connection settings."""
            if "postgresql" in config.database.dsn:
                cursor = dbapi_connection.cursor()
                cursor.execute("SET timezone TO 'UTC'")
                cursor.close()

    @property
    def engine(self) -> Engine:
        """Get database engine."""
        if not self._initialized:
            self.initialize()
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get session factory."""
        if not self._initialized:
            self.initialize()
        return self._session_factory

    def create_all_tables(self) -> None:
        """Create all database tables."""
        if not self._initialized:
            self.initialize()

        try:
            Base.metadata.create_all(bind=self._engine)
            logger.info("All database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def drop_all_tables(self) -> None:
        """Drop all database tables. Use with caution!"""
        if not self._initialized:
            self.initialize()

        try:
            Base.metadata.drop_all(bind=self._engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup."""
        if not self._initialized:
            self.initialize()

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_session_sync(self) -> Session:
        """Get database session for synchronous use. Remember to close it!"""
        if not self._initialized:
            self.initialize()
        return self._session_factory()

    def health_check(self) -> bool:
        """Check database connection health."""
        try:
            from sqlalchemy import text

            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def close(self) -> None:
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for common operations
def get_session() -> Generator[Session, None, None]:
    """Get database session context manager."""
    return db_manager.get_session()


def get_session_sync() -> Session:
    """Get database session for synchronous use."""
    return db_manager.get_session_sync()


def initialize_database() -> None:
    """Initialize database connection."""
    db_manager.initialize()


def create_all_tables() -> None:
    """Create all database tables."""
    db_manager.create_all_tables()


def health_check() -> bool:
    """Check database health."""
    return db_manager.health_check()


def close_database() -> None:
    """Close database connections."""
    db_manager.close()


# Database initialization function for application startup
def setup_database() -> None:
    """Set up database for application startup."""
    logger.info("Setting up database...")

    try:
        # Initialize database connection
        initialize_database()

        # Create tables if they don't exist
        create_all_tables()

        # Perform health check
        if not health_check():
            raise RuntimeError("Database health check failed")

        logger.info("Database setup completed successfully")

    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise


# Context manager for database transactions
@contextmanager
def database_transaction() -> Generator[Session, None, None]:
    """Context manager for database transactions with automatic rollback on error."""
    with get_session() as session:
        try:
            yield session
            # Commit is handled by get_session context manager
        except Exception:
            # Rollback is handled by get_session context manager
            raise
