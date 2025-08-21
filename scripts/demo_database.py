#!/usr/bin/env python3
"""
Database demonstration script for GITTE system.
Uses SQLite for demonstration purposes.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.models import Base, ConsentType, UserRole
from src.data.repositories import (
    ConsentRepository,
    PALDDataRepository,
    PALDSchemaRepository,
    UserRepository,
)
from src.data.schemas import (
    ConsentRecordCreate,
    PALDDataCreate,
    PALDSchemaVersionCreate,
    UserCreate,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Use the central data layer even for demos (DRY & realistic paths)
import os

def create_demo_database():
    """Prepare central DB manager to use in-memory SQLite for this demo."""
    # Force DSN locally for the demo process only
    os.environ["POSTGRES_DSN"] = "sqlite:///:memory:"  # central layer will detect SQLite and set StaticPool
    try:
        from data.database import setup_database, get_session  # 'src' was appended to sys.path above
    except Exception:
        from src.data.database import setup_database, get_session

    setup_database()  # creates tables via Base.metadata.create_all(...)
    return get_session  # return the context-manager factory


def demo_user_operations(session):
    """Demonstrate user operations."""
    logger.info("=== User Operations Demo ===")

    user_repo = UserRepository(session)

    # Create a user
    user_data = UserCreate(username="demo_user", password="password123", role=UserRole.PARTICIPANT)
    user = user_repo.create(user_data, "hashed_password_123", "pseudo_demo_123")

    logger.info(f"Created user: {user.username} (ID: {user.id})")

    # Get user by username
    retrieved_user = user_repo.get_by_username("demo_user")
    logger.info(f"Retrieved user by username: {retrieved_user.username}")

    # Get user by pseudonym
    retrieved_user = user_repo.get_by_pseudonym("pseudo_demo_123")
    logger.info(f"Retrieved user by pseudonym: {retrieved_user.pseudonym}")

    return user

def demo_consent_operations(session, user):
    """Demonstrate consent operations."""
    logger.info("\n=== Consent Operations Demo ===")

    consent_repo = ConsentRepository(session)

    # Create consent record
    consent_data = ConsentRecordCreate(
        consent_type=ConsentType.DATA_PROCESSING,
        consent_given=True,
        consent_version="1.0",
        consent_metadata={"source": "demo", "ip_address": "127.0.0.1"},
    )

    consent = consent_repo.create(user.id, consent_data)
    logger.info(f"Created consent record: {consent.consent_type} = {consent.consent_given}")

    # Check consent
    has_consent = consent_repo.check_consent(user.id, ConsentType.DATA_PROCESSING)
    logger.info(f"User has consent for data processing: {has_consent}")

    # Withdraw consent
    withdrawal_success = consent_repo.withdraw_consent(
        user.id, ConsentType.DATA_PROCESSING, "User requested withdrawal"
    )
    logger.info(f"Consent withdrawal successful: {withdrawal_success}")

    # Check consent after withdrawal
    has_consent_after = consent_repo.check_consent(user.id, ConsentType.DATA_PROCESSING)
    logger.info(f"User has consent after withdrawal: {has_consent_after}")

def demo_pald_operations(session, user):
    """Demonstrate PALD operations."""
    logger.info("\n=== PALD Operations Demo ===")

    schema_repo = PALDSchemaRepository(session)
    pald_repo = PALDDataRepository(session)

    # Create PALD schema version
    schema_data = PALDSchemaVersionCreate(
        version="1.0.0",
        schema_content={
            "type": "object",
            "properties": {
                "learning_style": {"type": "string", "enum": ["visual", "auditory", "kinesthetic"]},
                "difficulty_preference": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                },
                "interaction_style": {
                    "type": "string",
                    "enum": ["formal", "casual", "encouraging"],
                },
            },
            "required": ["learning_style", "difficulty_preference"],
        },
        migration_notes="Demo PALD schema",
    )

    schema = schema_repo.create(schema_data)
    logger.info(f"Created PALD schema version: {schema.version}")

    # Set as active schema
    schema_repo.set_active_schema("1.0.0")
    logger.info("Set schema as active")

    # Create PALD data for user
    pald_data = PALDDataCreate(
        pald_content={
            "learning_style": "visual",
            "difficulty_preference": "intermediate",
            "interaction_style": "encouraging",
            "subject_interests": ["mathematics", "computer_science"],
            "accessibility_needs": [],
        },
        schema_version="1.0.0",
    )

    pald = pald_repo.create(user.id, pald_data)
    logger.info(f"Created PALD data for user: {len(pald.pald_content)} attributes")

    # Retrieve PALD data
    retrieved_pald = pald_repo.get_by_user(user.id)
    logger.info(
        f"Retrieved PALD data: learning_style = {retrieved_pald.pald_content['learning_style']}"
    )

def main():
    """Run database demonstration."""
    logger.info("GITTE Database Demonstration")
    logger.info("Using SQLite in-memory database")

    try:
        # Create demo database
        get_session = create_demo_database()

        with get_session() as session:
            # Demo user operations
            user = demo_user_operations(session)

            # Demo consent operations
            demo_consent_operations(session, user)

            # Demo PALD operations
            demo_pald_operations(session, user)

            session.commit()

        logger.info("\n✓ Database demonstration completed successfully!")

    except Exception as e:
        logger.error(f"Database demonstration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
