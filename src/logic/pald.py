"""
PALD Logic Layer
Business logic for PALD schema management, validation, and evolution.
Enhanced with PALD Light extraction, bias analysis, and diff calculation.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.config import config
from config.pald_enhancement import pald_enhancement_config
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
from src.logic.pald_light_extraction import PALDLightExtractor, PALDLightResult
from src.logic.bias_analysis import BiasAnalysisEngine, BiasJobManager, BiasAnalysisJob, BiasType, JobStatus, bias_job_manager
from src.logic.pald_diff_calculation import PALDDiffCalculator, PALDPersistenceManager, PALDDiffResult

logger = logging.getLogger(__name__)


# Enhanced PALD data classes
from dataclasses import dataclass, field


@dataclass
class PALDProcessingRequest:
    """Request for PALD processing."""
    user_id: UUID
    session_id: str
    description_text: str
    embodiment_caption: str | None = None
    defer_bias_scan: bool = True
    processing_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class PALDProcessingResponse:
    """Response from PALD processing."""
    pald_light: dict[str, Any]
    pald_diff_summary: str | None = None
    defer_notice: str | None = None
    validation_errors: list[str] = field(default_factory=list)
    processing_metadata: dict[str, Any] = field(default_factory=dict)


class PALDManager:
    """Business logic manager for PALD operations with enhanced capabilities."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.repository = PALDDataRepository(db_session)
        self.schema_service = PALDSchemaService(db_session)
        self.evolution_service = PALDEvolutionService(db_session)
        
        # Enhanced PALD components
        self.pald_extractor = PALDLightExtractor()
        self.bias_analyzer = BiasAnalysisEngine()
        self.bias_job_manager = bias_job_manager  # Use global instance
        self.diff_calculator = PALDDiffCalculator()
        self.persistence_manager = PALDPersistenceManager()

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

    def process_enhanced_pald(self, request: PALDProcessingRequest) -> PALDProcessingResponse:
        """Process PALD with enhanced capabilities including mandatory extraction and optional bias analysis."""
        try:
            logger.info(f"Processing enhanced PALD for session {request.session_id}")
            
            # Step 1: Mandatory PALD Light extraction (always performed)
            pald_light_result = self._extract_pald_light(request)
            
            # Step 2: Calculate diff if embodiment caption is provided
            pald_diff_result = None
            if request.embodiment_caption:
                pald_diff_result = self._calculate_pald_diff(request, pald_light_result)
            
            # Step 3: Handle bias analysis (deferred or immediate based on configuration)
            defer_notice = None
            if pald_enhancement_config.enable_bias_analysis:
                defer_notice = self._handle_bias_analysis(request, pald_light_result, pald_diff_result)
            
            # Step 4: Persist PALD artifacts
            artifact_id = self._persist_pald_artifacts(request, pald_light_result, pald_diff_result)
            
            # Step 5: Create response
            response = PALDProcessingResponse(
                pald_light=pald_light_result.pald_light,
                pald_diff_summary=pald_diff_result.summary if pald_diff_result else None,
                defer_notice=defer_notice,
                validation_errors=pald_light_result.validation_errors,
                processing_metadata={
                    "artifact_id": artifact_id,
                    "extraction_confidence": pald_light_result.extraction_confidence,
                    "compressed_prompt": pald_light_result.compressed_prompt,
                    "processing_timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Enhanced PALD processing completed for session {request.session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Enhanced PALD processing failed for session {request.session_id}: {e}")
            return self._create_error_response(str(e))
    
    def _extract_pald_light(self, request: PALDProcessingRequest) -> PALDLightResult:
        """Extract mandatory PALD Light data."""
        try:
            return self.pald_extractor.extract_from_text(
                description_text=request.description_text,
                embodiment_caption=request.embodiment_caption
            )
        except Exception as e:
            logger.error(f"PALD Light extraction failed: {e}")
            # Return minimal fallback result
            return PALDLightResult(
                pald_light={"global_design_level": {"type": "human"}},
                extraction_confidence=0.0,
                filled_fields=[],
                missing_fields=[],
                validation_errors=[f"Extraction failed: {str(e)}"],
                compressed_prompt="person"
            )
    
    def _calculate_pald_diff(self, request: PALDProcessingRequest, pald_light_result: PALDLightResult) -> PALDDiffResult | None:
        """Calculate diff between description and embodiment PALDs."""
        try:
            # Extract PALD from embodiment caption separately
            embodiment_result = self.pald_extractor.extract_from_text(
                description_text="",
                embodiment_caption=request.embodiment_caption or ""
            )
            
            # Calculate diff
            return self.diff_calculator.calculate_diff(
                description_pald=pald_light_result.pald_light,
                embodiment_pald=embodiment_result.pald_light
            )
        except Exception as e:
            logger.error(f"PALD diff calculation failed: {e}")
            return None
    
    def _handle_bias_analysis(
        self, 
        request: PALDProcessingRequest, 
        pald_light_result: PALDLightResult, 
        pald_diff_result: PALDDiffResult | None
    ) -> str | None:
        """Handle bias analysis based on configuration."""
        try:
            if not pald_enhancement_config.enable_bias_analysis:
                return None
            
            # Determine analysis types to perform
            analysis_types = self._get_enabled_analysis_types()
            
            if request.defer_bias_scan or pald_enhancement_config.pald_analysis_deferred:
                # Create deferred bias job
                job_id = self.bias_job_manager.create_bias_job(
                    session_id=request.session_id,
                    description_pald=pald_light_result.pald_light,
                    embodiment_pald=pald_diff_result.hallucinations if pald_diff_result else {},
                    analysis_types=analysis_types,
                    priority=1
                )
                return f"Bias analysis queued for post-session processing (Job ID: {job_id})"
            else:
                # Perform immediate bias analysis
                self._perform_immediate_bias_analysis(request, pald_light_result, analysis_types)
                return None
                
        except Exception as e:
            logger.error(f"Bias analysis handling failed: {e}")
            return f"Bias analysis failed: {str(e)}"
    
    def _get_enabled_analysis_types(self) -> list[BiasType]:
        """Get list of enabled bias analysis types."""
        enabled_types = []
        
        if pald_enhancement_config.enable_age_shift_analysis:
            enabled_types.append(BiasType.AGE_SHIFT)
        if pald_enhancement_config.enable_gender_conformity_analysis:
            enabled_types.append(BiasType.GENDER_CONFORMITY)
        if pald_enhancement_config.enable_ethnicity_analysis:
            enabled_types.append(BiasType.ETHNICITY_CONSISTENCY)
        if pald_enhancement_config.enable_occupational_stereotype_analysis:
            enabled_types.append(BiasType.OCCUPATIONAL_STEREOTYPES)
        if pald_enhancement_config.enable_ambivalent_stereotype_analysis:
            enabled_types.append(BiasType.AMBIVALENT_STEREOTYPES)
        if pald_enhancement_config.enable_multiple_stereotyping_analysis:
            enabled_types.append(BiasType.MULTIPLE_STEREOTYPING)
            
        return enabled_types
    
    def _perform_immediate_bias_analysis(
        self, 
        request: PALDProcessingRequest, 
        pald_light_result: PALDLightResult, 
        analysis_types: list[BiasType]
    ):
        """Perform immediate bias analysis."""
        try:
            # This would perform immediate analysis - for now just log
            logger.info(f"Performing immediate bias analysis for session {request.session_id}")
            # Implementation would call bias_analyzer methods directly
        except Exception as e:
            logger.error(f"Immediate bias analysis failed: {e}")
    
    def _persist_pald_artifacts(
        self, 
        request: PALDProcessingRequest, 
        pald_light_result: PALDLightResult, 
        pald_diff_result: PALDDiffResult | None
    ) -> str:
        """Persist PALD artifacts with pseudonymization."""
        try:
            return self.persistence_manager.create_artifact(
                session_id=request.session_id,
                user_id=str(request.user_id),
                description_text=request.description_text,
                embodiment_caption=request.embodiment_caption,
                pald_light=pald_light_result.pald_light,
                pald_diff=pald_diff_result,
                processing_metadata=pald_light_result.processing_metadata
            )
        except Exception as e:
            logger.error(f"PALD artifact persistence failed: {e}")
            return "persistence_failed"
    
    def _create_error_response(self, error_message: str) -> PALDProcessingResponse:
        """Create error response for failed processing."""
        return PALDProcessingResponse(
            pald_light={"global_design_level": {"type": "human"}},
            pald_diff_summary=None,
            defer_notice=None,
            validation_errors=[error_message],
            processing_metadata={
                "error": True,
                "error_message": error_message,
                "processing_timestamp": datetime.now().isoformat()
            }
        )

    def get_bias_job_status(self, job_id: str) -> dict[str, Any]:
        """Get status of a bias analysis job."""
        try:
            status = self.bias_job_manager.get_job_status(job_id)
            return {
                "job_id": job_id,
                "status": status.value if status else "not_found",
                "message": f"Job status: {status.value}" if status else "Job not found"
            }
        except Exception as e:
            logger.error(f"Error getting bias job status: {e}")
            return {
                "job_id": job_id,
                "status": "error",
                "message": f"Error retrieving status: {str(e)}"
            }

    def process_bias_job_queue(self, batch_size: int | None = None) -> dict[str, Any]:
        """Process queued bias analysis jobs."""
        try:
            batch_size = batch_size or pald_enhancement_config.bias_job_batch_size
            results = self.bias_job_manager.process_bias_queue(batch_size)
            
            return {
                "processed_jobs": len(results),
                "successful_jobs": len([r for r in results if r.status == JobStatus.COMPLETED]),
                "failed_jobs": len([r for r in results if r.status == JobStatus.FAILED]),
                "processing_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error processing bias job queue: {e}")
            return {
                "processed_jobs": 0,
                "successful_jobs": 0,
                "failed_jobs": 0,
                "error": str(e),
                "processing_timestamp": datetime.now().isoformat()
            }


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
