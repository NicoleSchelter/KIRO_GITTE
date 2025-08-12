#!/usr/bin/env python3
"""
Database validation script for GITTE system.
Validates that all tables and initial data are properly set up.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data import get_session, health_check
from src.data.models import (
    AuditLog,
    ConsentRecord,
    FederatedLearningUpdate,
    PALDAttributeCandidate,
    PALDData,
    PALDSchemaVersion,
    SystemMetadata,
    User,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_tables():
    """Validate that all required tables exist and are accessible."""
    tables_to_check = [
        ("users", User),
        ("consent_records", ConsentRecord),
        ("pald_data", PALDData),
        ("pald_schema_versions", PALDSchemaVersion),
        ("pald_attribute_candidates", PALDAttributeCandidate),
        ("audit_logs", AuditLog),
        ("fl_updates", FederatedLearningUpdate),
        ("system_metadata", SystemMetadata),
    ]

    with get_session() as session:
        for table_name, model_class in tables_to_check:
            try:
                count = session.query(model_class).count()
                logger.info(f"✓ Table '{table_name}': {count} records")
            except Exception as e:
                logger.error(f"✗ Table '{table_name}': Error - {e}")
                return False

    return True


def validate_initial_data():
    """Validate that initial data is properly set up."""
    with get_session() as session:
        # Check PALD schema version
        schema_count = session.query(PALDSchemaVersion).count()
        active_schema = (
            session.query(PALDSchemaVersion).filter(PALDSchemaVersion.is_active is True).first()
        )

        if schema_count == 0:
            logger.error("✗ No PALD schema versions found")
            return False

        if not active_schema:
            logger.error("✗ No active PALD schema version found")
            return False

        logger.info(
            f"✓ PALD schemas: {schema_count} total, active version: {active_schema.version}"
        )

        # Check system metadata
        metadata_count = session.query(SystemMetadata).count()
        if metadata_count == 0:
            logger.error("✗ No system metadata found")
            return False

        logger.info(f"✓ System metadata: {metadata_count} entries")

        # List some key metadata
        key_metadata = (
            session.query(SystemMetadata)
            .filter(SystemMetadata.key.in_(["database_version", "schema_initialized"]))
            .all()
        )

        for meta in key_metadata:
            logger.info(f"  - {meta.key}: {meta.value}")

    return True


def main():
    """Run database validation."""
    logger.info("Validating GITTE database setup...")

    try:
        # Check database health
        if not health_check():
            logger.error("✗ Database health check failed")
            sys.exit(1)

        logger.info("✓ Database connection successful")

        # Validate tables
        if not validate_tables():
            logger.error("✗ Table validation failed")
            sys.exit(1)

        # Validate initial data
        if not validate_initial_data():
            logger.error("✗ Initial data validation failed")
            sys.exit(1)

        logger.info("✓ Database validation completed successfully!")

    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
