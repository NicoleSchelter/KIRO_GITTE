"""
PALD Logic Layer
Business logic for PALD schema management, validation, and evolution.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.config import config
from src.data.models import PALDAttributeCandidate, PALDData, PALDSchemaVersion
from src.data.repositories import PALDDataRepository
from src.data.schemas import (
    PALDCoverageMetrics,
    PALDDataCreate,
    PALDDataResponse,
    PALDDataUpdate,
    PALDDiff,
    PALDSchemaVersionResponse,
    PALDValidationResult,
)
from src.services.pald_service import PALDEvolutionService, PALDSchemaService

logger = logging.getLogger(__name__)


class PALDManager:
    """Business logic manager for PALD operations."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.repository = PALDDataRepository(db_session)
        self.schema_service = PALDSchemaService(db_session)
        self.evolution_service = PALDEvolutionService(db_session)

    def create_pald_data(self, user_id: UUID, pald_create: PALDDataCreate) -> PALDDataResponse:
        """Create new PALD data for a user."""
        # Validate the PALD data against current schema
        validation_result = self.schema_service.validate_pald_data(
            pald_create.pald_content, pald_create.schema_version
        )

        # Create PALD data record
        pald_data = PALDData(
            user_id=user_id,
            pald_content=pald_create.pald_content,
            schema_version=pald_create.schema_version,
            is_validated=validation_result.is_valid,
            validation_errors=(
                {"errors": validation_result.errors} if validation_result.errors else None
            ),
        )

        created_pald = self.repository.create(pald_data)

        logger.info(f"Created PALD data for user {user_id}, valid: {validation_result.is_valid}")

        return PALDDataResponse.model_validate(created_pald)

    def update_pald_data(
        self, pald_id: UUID, user_id: UUID, pald_update: PALDDataUpdate
    ) -> PALDDataResponse:
        """Update existing PALD data."""
        existing_pald = self.repository.get_by_id(pald_id)

        if not existing_pald:
            raise ValueError(f"PALD data with ID {pald_id} not found")

        if existing_pald.user_id != user_id:
            raise ValueError("User does not have permission to update this PALD data")

        # Update fields if provided
        if pald_update.pald_content is not None:
            existing_pald.pald_content = pald_update.pald_content

        if pald_update.schema_version is not None:
            existing_pald.schema_version = pald_update.schema_version

        # Re-validate after update
        validation_result = self.schema_service.validate_pald_data(
            existing_pald.pald_content, existing_pald.schema_version
        )

        existing_pald.is_validated = validation_result.is_valid
        existing_pald.validation_errors = (
            {"errors": validation_result.errors} if validation_result.errors else None
        )
        existing_pald.updated_at = datetime.utcnow()

        updated_pald = self.repository.update(existing_pald)

        logger.info(f"Updated PALD data {pald_id} for user {user_id}")

        return PALDDataResponse.model_validate(updated_pald)

    def get_user_pald_data(self, user_id: UUID) -> list[PALDDataResponse]:
        """Get all PALD data for a user."""
        pald_data_list = self.repository.get_by_user_id(user_id)
        return [PALDDataResponse.model_validate(pald) for pald in pald_data_list]

    def get_pald_data_by_id(self, pald_id: UUID, user_id: UUID) -> PALDDataResponse:
        """Get specific PALD data by ID."""
        pald_data = self.repository.get_by_id(pald_id)

        if not pald_data:
            raise ValueError(f"PALD data with ID {pald_id} not found")

        if pald_data.user_id != user_id:
            raise ValueError("User does not have permission to access this PALD data")

        return PALDDataResponse.model_validate(pald_data)

    def validate_pald_data(
        self, pald_content: dict[str, Any], schema_version: str | None = None
    ) -> PALDValidationResult:
        """Validate PALD data against schema."""
        return self.schema_service.validate_pald_data(pald_content, schema_version)

    def compare_pald_data(self, pald_id_a: UUID, pald_id_b: UUID, user_id: UUID) -> PALDDiff:
        """Compare two PALD data objects."""
        pald_a = self.repository.get_by_id(pald_id_a)
        pald_b = self.repository.get_by_id(pald_id_b)

        if not pald_a or not pald_b:
            raise ValueError("One or both PALD data objects not found")

        # Check permissions
        if pald_a.user_id != user_id or pald_b.user_id != user_id:
            raise ValueError("User does not have permission to compare these PALD data objects")

        return self.schema_service.compare_pald_data(pald_a.pald_content, pald_b.pald_content)

    def calculate_pald_coverage(self, pald_id: UUID, user_id: UUID) -> PALDCoverageMetrics:
        """Calculate coverage metrics for PALD data."""
        pald_data = self.repository.get_by_id(pald_id)

        if not pald_data:
            raise ValueError(f"PALD data with ID {pald_id} not found")

        if pald_data.user_id != user_id:
            raise ValueError("User does not have permission to access this PALD data")

        return self.schema_service.calculate_coverage(pald_data.pald_content)

    def process_chat_for_attribute_extraction(self, user_id: UUID, chat_text: str) -> list[str]:
        """Process chat text to extract and track embodiment attributes."""
        if not config.get_feature_flag("enable_pald_evolution"):
            return []

        # Extract attributes from chat text
        extracted_attributes = self.evolution_service.extract_embodiment_attributes(chat_text)

        if extracted_attributes:
            # Track the attributes for schema evolution
            self.evolution_service.track_attribute_mentions(extracted_attributes)

            logger.info(
                f"Extracted {len(extracted_attributes)} attributes from chat for user {user_id}"
            )

        return extracted_attributes

    def get_schema_evolution_status(self) -> dict[str, Any]:
        """Get current status of schema evolution."""
        candidates = self.evolution_service.get_schema_evolution_candidates()
        current_version, _ = self.schema_service.get_current_schema()

        # Get total attribute candidates
        total_candidates = self.db_session.query(PALDAttributeCandidate).count()

        return {
            "current_schema_version": current_version,
            "evolution_enabled": config.get_feature_flag("enable_pald_evolution"),
            "candidates_ready_for_evolution": len(candidates),
            "total_attribute_candidates": total_candidates,
            "ready_candidates": [
                {
                    "attribute_name": c.attribute_name,
                    "mention_count": c.mention_count,
                    "category": c.attribute_category,
                }
                for c in candidates
            ],
        }

    def trigger_schema_evolution(self) -> PALDSchemaVersionResponse | None:
        """Trigger schema evolution if candidates are available."""
        if not config.get_feature_flag("enable_pald_evolution"):
            raise ValueError("Schema evolution is disabled")

        candidates = self.evolution_service.get_schema_evolution_candidates()

        if not candidates:
            logger.info("No candidates available for schema evolution")
            return None

        # Apply schema evolution
        new_schema_version = self.evolution_service.apply_schema_evolution(candidates)

        logger.info(f"Schema evolution completed: created version {new_schema_version.version}")

        return PALDSchemaVersionResponse.model_validate(new_schema_version)

    def migrate_pald_data_to_new_schema(self, target_schema_version: str) -> dict[str, Any]:
        """Migrate existing PALD data to a new schema version."""
        # Get target schema
        target_schema_obj = (
            self.db_session.query(PALDSchemaVersion)
            .filter(PALDSchemaVersion.version == target_schema_version)
            .first()
        )

        if not target_schema_obj:
            raise ValueError(f"Schema version {target_schema_version} not found")

        # Get all PALD data that needs migration
        pald_data_to_migrate = (
            self.db_session.query(PALDData)
            .filter(PALDData.schema_version != target_schema_version)
            .all()
        )

        migration_results = {
            "total_records": len(pald_data_to_migrate),
            "successful_migrations": 0,
            "failed_migrations": 0,
            "errors": [],
        }

        for pald_data in pald_data_to_migrate:
            try:
                # Validate against new schema
                validation_result = self.schema_service.validate_pald_data(
                    pald_data.pald_content, target_schema_version
                )

                # Update schema version and validation status
                pald_data.schema_version = target_schema_version
                pald_data.is_validated = validation_result.is_valid
                pald_data.validation_errors = (
                    {"errors": validation_result.errors} if validation_result.errors else None
                )
                pald_data.updated_at = datetime.utcnow()

                migration_results["successful_migrations"] += 1

            except Exception as e:
                migration_results["failed_migrations"] += 1
                migration_results["errors"].append(
                    f"Failed to migrate PALD {pald_data.id}: {str(e)}"
                )
                logger.error(f"Failed to migrate PALD data {pald_data.id}: {str(e)}")

        self.db_session.commit()

        logger.info(
            f"PALD data migration completed: {migration_results['successful_migrations']} successful, {migration_results['failed_migrations']} failed"
        )

        return migration_results


class PALDSchemaManager:
    """Business logic manager for PALD schema operations."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.schema_service = PALDSchemaService(db_session)

    def get_current_schema(self) -> PALDSchemaVersionResponse:
        """Get the current active PALD schema."""
        version, schema_content = self.schema_service.get_current_schema()

        schema_obj = (
            self.db_session.query(PALDSchemaVersion)
            .filter(PALDSchemaVersion.version == version)
            .first()
        )

        return PALDSchemaVersionResponse.model_validate(schema_obj)

    def get_all_schema_versions(self) -> list[PALDSchemaVersionResponse]:
        """Get all PALD schema versions."""
        schema_versions = (
            self.db_session.query(PALDSchemaVersion)
            .order_by(PALDSchemaVersion.created_at.desc())
            .all()
        )

        return [PALDSchemaVersionResponse.model_validate(sv) for sv in schema_versions]

    def create_schema_version(
        self,
        version: str,
        schema_content: dict[str, Any],
        migration_notes: str | None = None,
        is_active: bool = False,
    ) -> PALDSchemaVersionResponse:
        """Create a new PALD schema version."""
        schema_version = self.schema_service.create_schema_version(
            version=version,
            schema_content=schema_content,
            migration_notes=migration_notes,
            is_active=is_active,
        )

        return PALDSchemaVersionResponse.model_validate(schema_version)

    def activate_schema_version(self, version: str) -> PALDSchemaVersionResponse:
        """Activate a specific schema version."""
        # Deactivate current active schema
        current_active = (
            self.db_session.query(PALDSchemaVersion)
            .filter(PALDSchemaVersion.is_active is True)
            .first()
        )

        if current_active:
            current_active.is_active = False

        # Activate target schema
        target_schema = (
            self.db_session.query(PALDSchemaVersion)
            .filter(PALDSchemaVersion.version == version)
            .first()
        )

        if not target_schema:
            raise ValueError(f"Schema version {version} not found")

        target_schema.is_active = True
        self.db_session.commit()

        # Clear cache in schema service
        self.schema_service._current_schema_cache = None
        self.schema_service._current_version_cache = None

        logger.info(f"Activated PALD schema version {version}")

        return PALDSchemaVersionResponse.model_validate(target_schema)
