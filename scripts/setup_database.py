#!/usr/bin/env python3
"""
Database setup script for GITTE system.
Creates database tables and inserts initial data.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import config
from src.data import get_session, setup_database
from src.data.models import PALDSchemaVersion, SystemMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Set up the database with initial data."""
    try:
        logger.info("Setting up GITTE database...")

        # Initialize database and create tables
        setup_database()

        # Add initial data
        with get_session() as session:
            # Check if initial schema version exists
            existing_schema = (
                session.query(PALDSchemaVersion)
                .filter(PALDSchemaVersion.version == "1.0.0")
                .first()
            )

            if not existing_schema:
                # Create initial PALD schema version
                initial_schema = PALDSchemaVersion(
                    version="1.0.0",
                    schema_content={
                        "type": "object",
                        "properties": {
                            "learning_style": {
                                "type": "string",
                                "enum": ["visual", "auditory", "kinesthetic", "reading"],
                            },
                            "difficulty_preference": {
                                "type": "string",
                                "enum": ["beginner", "intermediate", "advanced"],
                            },
                            "interaction_style": {
                                "type": "string",
                                "enum": ["formal", "casual", "encouraging", "direct"],
                            },
                            "embodiment_preferences": {
                                "type": "object",
                                "properties": {
                                    "appearance": {"type": "string"},
                                    "personality": {"type": "string"},
                                    "voice_tone": {"type": "string"},
                                },
                            },
                            "subject_interests": {"type": "array", "items": {"type": "string"}},
                            "accessibility_needs": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": [
                            "learning_style",
                            "difficulty_preference",
                            "interaction_style",
                        ],
                    },
                    is_active=True,
                    migration_notes="Initial PALD schema with basic learning preferences and embodiment attributes",
                )
                session.add(initial_schema)
                logger.info("Created initial PALD schema version 1.0.0")

            # Check if system metadata exists
            existing_metadata = session.query(SystemMetadata).first()
            if not existing_metadata:
                # Add system metadata
                metadata_entries = [
                    SystemMetadata(key="database_version", value="1.0.0"),
                    SystemMetadata(key="schema_initialized", value="true"),
                    SystemMetadata(key="pald_threshold_mentions", value="10"),
                    SystemMetadata(key="audit_retention_days", value="365"),
                ]

                for entry in metadata_entries:
                    session.add(entry)

                logger.info("Added initial system metadata")

            session.commit()

        logger.info("Database setup completed successfully!")
        logger.info(f"Database DSN: {config.database.dsn}")

    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
