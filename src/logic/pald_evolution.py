"""
PALD Schema Evolution Logic
Manages PALD schema evolution and candidate field detection without exposing raw user data.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.data.models import PALDSchemaFieldCandidate
from src.services.pald_schema_registry_service import PALDSchemaRegistryService

logger = logging.getLogger(__name__)


@dataclass
class FieldCandidate:
    """Represents a candidate field for schema evolution."""
    field_name: str
    field_path: str
    detection_context: str
    occurrence_count: int
    example_values: list[Any]
    proposed_type: str
    confidence_score: float


@dataclass
class SchemaChange:
    """Represents a proposed schema change."""
    change_type: str  # add_field, modify_field, remove_field
    field_path: str
    old_definition: dict[str, Any] | None
    new_definition: dict[str, Any]
    justification: str
    impact_assessment: str


class PALDEvolutionManager:
    """Manages PALD schema evolution and candidate field detection."""
    
    def __init__(self, db_session: Session, schema_registry: PALDSchemaRegistryService):
        self.db_session = db_session
        self.schema_registry = schema_registry
    
    def extract_candidate_fields(
        self, 
        data: dict[str, Any], 
        current_schema: dict[str, Any]
    ) -> list[FieldCandidate]:
        """Extract fields that don't exist in current schema."""
        candidates = []
        
        if not isinstance(data, dict) or not current_schema:
            return candidates
        
        schema_properties = current_schema.get("properties", {})
        
        def extract_from_nested(obj: dict[str, Any], path_prefix: str = "") -> None:
            """Recursively extract candidate fields from nested objects."""
            for key, value in obj.items():
                current_path = f"{path_prefix}.{key}" if path_prefix else key
                
                # Check if this field exists in schema
                if key not in schema_properties and path_prefix == "":
                    # This is a new top-level field
                    candidate = FieldCandidate(
                        field_name=key,
                        field_path=current_path,
                        detection_context="user_input",
                        occurrence_count=1,
                        example_values=[self._anonymize_value(value)],
                        proposed_type=self._infer_type(value),
                        confidence_score=0.8
                    )
                    candidates.append(candidate)
                
                # Recursively check nested objects
                if isinstance(value, dict):
                    extract_from_nested(value, current_path)
        
        extract_from_nested(data)
        return candidates
    
    def harvest_schema_candidates(self, candidates: list[FieldCandidate]) -> None:
        """Store field candidates for governance review."""
        for candidate in candidates:
            # Check if candidate already exists
            existing = self.db_session.query(PALDSchemaFieldCandidate).filter(
                PALDSchemaFieldCandidate.field_name == candidate.field_name
            ).first()
            
            if existing:
                # Update occurrence count
                existing.mention_count += candidate.occurrence_count
                existing.updated_at = datetime.utcnow()
                
            else:
                # Create new candidate
                new_candidate = PALDSchemaFieldCandidate(
                    field_name=candidate.field_name,
                    field_category="detected",
                    mention_count=candidate.occurrence_count,
                    first_detected=datetime.utcnow(),
                    last_mentioned=datetime.utcnow()
                )
                self.db_session.add(new_candidate)
        
        self.db_session.commit()
        logger.info(f"Harvested {len(candidates)} schema field candidates")
    
    def propose_schema_changes(self, candidates: list[FieldCandidate]) -> list[SchemaChange]:
        """Propose schema changes based on candidate analysis."""
        changes = []
        
        for candidate in candidates:
            if candidate.occurrence_count >= 5 and candidate.confidence_score >= 0.7:
                change = SchemaChange(
                    change_type="add_field",
                    field_path=candidate.field_path,
                    old_definition=None,
                    new_definition={
                        "type": [candidate.proposed_type, "null"],
                        "description": f"Auto-detected field: {candidate.field_name}"
                    },
                    justification=f"Field detected {candidate.occurrence_count} times with {candidate.confidence_score:.2f} confidence",
                    impact_assessment="Low risk - new optional field"
                )
                changes.append(change)
        
        return changes
    
    def approve_candidate(self, candidate_id: UUID) -> None:
        """Approve a field candidate for schema integration."""
        candidate = self.db_session.query(PALDSchemaFieldCandidate).filter(
            PALDSchemaFieldCandidate.id == candidate_id
        ).first()
        
        if candidate:
            candidate.added_to_schema = True
            candidate.updated_at = datetime.utcnow()
            self.db_session.commit()
            logger.info(f"Approved schema candidate: {candidate.field_name}")
    
    def reject_candidate(self, candidate_id: UUID, reason: str) -> None:
        """Reject a field candidate with reason."""
        candidate = self.db_session.query(PALDSchemaFieldCandidate).filter(
            PALDSchemaFieldCandidate.id == candidate_id
        ).first()
        
        if candidate:
            # For now, just mark as not added (could add rejection fields to model later)
            candidate.added_to_schema = False
            candidate.updated_at = datetime.utcnow()
            self.db_session.commit()
            logger.info(f"Rejected schema candidate: {candidate.field_name} - {reason}")
    
    def _anonymize_value(self, value: Any) -> Any:
        """Anonymize sensitive values in examples."""
        if isinstance(value, str):
            if len(value) > 50:
                return f"<string:{len(value)}chars>"
            return f"<string_example>"
        elif isinstance(value, (int, float)):
            return f"<{type(value).__name__}_example>"
        elif isinstance(value, bool):
            return "<boolean_example>"
        elif isinstance(value, list):
            return f"<list:{len(value)}items>"
        elif isinstance(value, dict):
            return f"<dict:{len(value)}keys>"
        else:
            return f"<{type(value).__name__}>"
    
    def _infer_type(self, value: Any) -> str:
        """Infer JSON schema type from value."""
        if isinstance(value, str):
            return "string"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"