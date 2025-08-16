"""
PALD Diff Calculation and Persistence System
Handles comparison between description and embodiment PALDs and persistence of PALD artifacts.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FieldStatus(Enum):
    """Status of a field comparison."""
    MATCH = "match"
    HALLUCINATION = "hallucination"
    MISSING = "missing"


@dataclass
class PALDDiffResult:
    """Result of PALD diff calculation."""
    matches: dict[str, Any]
    hallucinations: dict[str, Any]
    missing_fields: dict[str, Any]
    similarity_score: float
    field_classifications: dict[str, FieldStatus]
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PALDArtifact:
    """PALD artifact for persistence."""
    artifact_id: str
    session_id: str
    user_pseudonym: str
    description_text: str
    embodiment_caption: str | None
    pald_light: dict[str, Any]
    pald_diff: PALDDiffResult | None
    processing_metadata: dict[str, Any]
    created_at: datetime
    input_ids: dict[str, str] = field(default_factory=dict)


class PALDDiffCalculator:
    """Calculates differences between PALD datasets."""
    
    def __init__(self):
        pass
    
    def calculate_diff(
        self, 
        description_pald: dict[str, Any], 
        embodiment_pald: dict[str, Any]
    ) -> PALDDiffResult:
        """Calculate comprehensive diff between PALDs."""
        try:
            matches = {}
            hallucinations = {}
            missing_fields = {}
            field_classifications = {}
            
            # Get all field paths from both PALDs
            desc_paths = self._get_field_paths(description_pald)
            emb_paths = self._get_field_paths(embodiment_pald)
            all_paths = desc_paths | emb_paths
            
            # Compare each field
            for field_path in all_paths:
                desc_value = self._get_value_by_path(description_pald, field_path)
                emb_value = self._get_value_by_path(embodiment_pald, field_path)
                
                status = self.classify_field_status(field_path, desc_value, emb_value)
                field_classifications[field_path] = status
                
                if status == FieldStatus.MATCH:
                    matches[field_path] = {
                        "description": desc_value,
                        "embodiment": emb_value
                    }
                elif status == FieldStatus.HALLUCINATION:
                    hallucinations[field_path] = {
                        "description": desc_value,
                        "embodiment": emb_value,
                        "reason": "Present in embodiment but not in description"
                    }
                elif status == FieldStatus.MISSING:
                    missing_fields[field_path] = {
                        "description": desc_value,
                        "embodiment": emb_value,
                        "reason": "Present in description but missing in embodiment"
                    }
            
            # Calculate similarity score
            similarity_score = self._calculate_similarity_score(matches, hallucinations, missing_fields, all_paths)
            
            # Generate summary
            summary = self.generate_diff_summary(matches, hallucinations, missing_fields, similarity_score)
            
            return PALDDiffResult(
                matches=matches,
                hallucinations=hallucinations,
                missing_fields=missing_fields,
                similarity_score=similarity_score,
                field_classifications=field_classifications,
                summary=summary,
                metadata={
                    "calculation_timestamp": datetime.now().isoformat(),
                    "total_fields": len(all_paths),
                    "matched_fields": len(matches),
                    "hallucinated_fields": len(hallucinations),
                    "missing_fields": len(missing_fields)
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating PALD diff: {e}")
            return self._create_error_diff_result(str(e))
    
    def classify_field_status(self, field_path: str, desc_value: Any, emb_value: Any) -> FieldStatus:
        """Classify field as match/hallucination/missing."""
        desc_has_value = self._has_meaningful_value(desc_value)
        emb_has_value = self._has_meaningful_value(emb_value)
        
        if desc_has_value and emb_has_value:
            # Both have values - check if they match
            if self._values_match(desc_value, emb_value):
                return FieldStatus.MATCH
            else:
                # Values differ - could be hallucination or legitimate difference
                # For now, treat as hallucination if embodiment has more specific value
                if self._is_more_specific(emb_value, desc_value):
                    return FieldStatus.HALLUCINATION
                else:
                    return FieldStatus.MATCH  # Treat as acceptable variation
        elif desc_has_value and not emb_has_value:
            # Description has value but embodiment doesn't
            return FieldStatus.MISSING
        elif not desc_has_value and emb_has_value:
            # Embodiment has value but description doesn't
            return FieldStatus.HALLUCINATION
        else:
            # Neither has meaningful value - treat as match (both empty)
            return FieldStatus.MATCH
    
    def generate_diff_summary(
        self, 
        matches: dict[str, Any], 
        hallucinations: dict[str, Any], 
        missing_fields: dict[str, Any], 
        similarity_score: float
    ) -> str:
        """Generate human-readable diff summary."""
        total_fields = len(matches) + len(hallucinations) + len(missing_fields)
        
        if total_fields == 0:
            return "No PALD data to compare"
        
        summary_parts = [
            f"PALD Comparison Summary (Similarity: {similarity_score:.1%})"
        ]
        
        if matches:
            summary_parts.append(f"✓ {len(matches)} matching fields")
        
        if hallucinations:
            summary_parts.append(f"⚠ {len(hallucinations)} potential hallucinations")
            # List top hallucinations
            top_hallucinations = list(hallucinations.keys())[:3]
            for field in top_hallucinations:
                summary_parts.append(f"  - {field}: added in embodiment")
        
        if missing_fields:
            summary_parts.append(f"❌ {len(missing_fields)} missing fields")
            # List top missing fields
            top_missing = list(missing_fields.keys())[:3]
            for field in top_missing:
                summary_parts.append(f"  - {field}: missing from embodiment")
        
        # Add quality assessment
        if similarity_score >= 0.8:
            summary_parts.append("Assessment: High consistency")
        elif similarity_score >= 0.6:
            summary_parts.append("Assessment: Moderate consistency")
        elif similarity_score >= 0.4:
            summary_parts.append("Assessment: Low consistency")
        else:
            summary_parts.append("Assessment: Poor consistency")
        
        return "\n".join(summary_parts)
    
    def _get_field_paths(self, pald_data: dict[str, Any], prefix: str = "") -> set[str]:
        """Get all field paths from PALD data."""
        paths = set()
        
        if not isinstance(pald_data, dict):
            return paths
        
        for key, value in pald_data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            paths.add(current_path)
            
            if isinstance(value, dict):
                paths.update(self._get_field_paths(value, current_path))
        
        return paths
    
    def _get_value_by_path(self, pald_data: dict[str, Any], path: str) -> Any:
        """Get value at specified path."""
        if not isinstance(pald_data, dict):
            return None
        
        parts = path.split(".")
        current = pald_data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _has_meaningful_value(self, value: Any) -> bool:
        """Check if value is meaningful (not None, empty string, or empty dict)."""
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, dict) and len(value) == 0:
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        return True
    
    def _values_match(self, value1: Any, value2: Any) -> bool:
        """Check if two values match (with some tolerance for variations)."""
        if value1 == value2:
            return True
        
        # Handle string comparisons with normalization
        if isinstance(value1, str) and isinstance(value2, str):
            norm1 = value1.lower().strip()
            norm2 = value2.lower().strip()
            return norm1 == norm2
        
        # Handle numeric comparisons with tolerance
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            return abs(value1 - value2) <= 1  # Allow small differences
        
        return False
    
    def _is_more_specific(self, value1: Any, value2: Any) -> bool:
        """Check if value1 is more specific than value2."""
        if isinstance(value1, str) and isinstance(value2, str):
            return len(value1.strip()) > len(value2.strip())
        
        if isinstance(value1, dict) and isinstance(value2, dict):
            return len(value1) > len(value2)
        
        return False
    
    def _calculate_similarity_score(
        self, 
        matches: dict[str, Any], 
        hallucinations: dict[str, Any], 
        missing_fields: dict[str, Any], 
        all_paths: set[str]
    ) -> float:
        """Calculate similarity score between PALDs."""
        if len(all_paths) == 0:
            return 1.0  # Perfect match if no data
        
        # Weight different types of differences
        match_weight = 1.0
        hallucination_penalty = 0.5  # Hallucinations are less severe than missing
        missing_penalty = 0.8
        
        total_score = (
            len(matches) * match_weight - 
            len(hallucinations) * hallucination_penalty - 
            len(missing_fields) * missing_penalty
        )
        
        max_possible_score = len(all_paths) * match_weight
        
        if max_possible_score == 0:
            return 1.0
        
        similarity = max(0.0, total_score / max_possible_score)
        return round(similarity, 3)
    
    def _create_error_diff_result(self, error_message: str) -> PALDDiffResult:
        """Create error diff result when calculation fails."""
        return PALDDiffResult(
            matches={},
            hallucinations={},
            missing_fields={},
            similarity_score=0.0,
            field_classifications={},
            summary=f"Error calculating diff: {error_message}",
            metadata={
                "error": True,
                "error_message": error_message,
                "calculation_timestamp": datetime.now().isoformat()
            }
        )


class PALDPersistenceManager:
    """Manages persistence of PALD artifacts with pseudonymization."""
    
    def __init__(self):
        self.artifacts: dict[str, PALDArtifact] = {}  # In-memory storage for now
        
    def create_artifact(
        self,
        session_id: str,
        user_id: str,
        description_text: str,
        embodiment_caption: str | None,
        pald_light: dict[str, Any],
        pald_diff: PALDDiffResult | None = None,
        processing_metadata: dict[str, Any] | None = None
    ) -> str:
        """Create and store PALD artifact with pseudonymized identifiers."""
        try:
            artifact_id = str(uuid.uuid4())
            user_pseudonym = self._generate_pseudonym(user_id)
            
            # Generate input IDs for tracking without PII
            input_ids = {
                "description_hash": self._hash_text(description_text),
                "embodiment_hash": self._hash_text(embodiment_caption) if embodiment_caption else None,
                "session_hash": self._hash_text(session_id)
            }
            
            artifact = PALDArtifact(
                artifact_id=artifact_id,
                session_id=session_id,
                user_pseudonym=user_pseudonym,
                description_text=description_text,
                embodiment_caption=embodiment_caption,
                pald_light=pald_light,
                pald_diff=pald_diff,
                processing_metadata=processing_metadata or {},
                created_at=datetime.now(),
                input_ids=input_ids
            )
            
            self.artifacts[artifact_id] = artifact
            
            logger.info(f"Created PALD artifact {artifact_id} for session {session_id}")
            return artifact_id
            
        except Exception as e:
            logger.error(f"Error creating PALD artifact: {e}")
            raise
    
    def get_artifact(self, artifact_id: str) -> PALDArtifact | None:
        """Get PALD artifact by ID."""
        return self.artifacts.get(artifact_id)
    
    def get_artifacts_by_session(self, session_id: str) -> list[PALDArtifact]:
        """Get all artifacts for a session."""
        return [
            artifact for artifact in self.artifacts.values()
            if artifact.session_id == session_id
        ]
    
    def get_artifacts_by_pseudonym(self, user_pseudonym: str) -> list[PALDArtifact]:
        """Get all artifacts for a pseudonymized user."""
        return [
            artifact for artifact in self.artifacts.values()
            if artifact.user_pseudonym == user_pseudonym
        ]
    
    def update_artifact_diff(self, artifact_id: str, pald_diff: PALDDiffResult) -> bool:
        """Update artifact with diff calculation results."""
        if artifact_id not in self.artifacts:
            logger.error(f"Artifact {artifact_id} not found")
            return False
        
        try:
            self.artifacts[artifact_id].pald_diff = pald_diff
            logger.info(f"Updated artifact {artifact_id} with diff results")
            return True
        except Exception as e:
            logger.error(f"Error updating artifact {artifact_id}: {e}")
            return False
    
    def export_artifacts(
        self, 
        session_ids: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Export artifacts as serializable data (for research/analysis)."""
        artifacts_to_export = []
        
        for artifact in self.artifacts.values():
            # Apply filters
            if session_ids and artifact.session_id not in session_ids:
                continue
            
            if start_date and artifact.created_at < start_date:
                continue
                
            if end_date and artifact.created_at > end_date:
                continue
            
            # Serialize artifact (excluding PII)
            exported_artifact = {
                "artifact_id": artifact.artifact_id,
                "session_id": artifact.session_id,
                "user_pseudonym": artifact.user_pseudonym,
                "input_ids": artifact.input_ids,
                "pald_light": artifact.pald_light,
                "pald_diff": self._serialize_diff_result(artifact.pald_diff) if artifact.pald_diff else None,
                "processing_metadata": artifact.processing_metadata,
                "created_at": artifact.created_at.isoformat(),
                # Note: description_text and embodiment_caption are excluded for privacy
            }
            
            artifacts_to_export.append(exported_artifact)
        
        return artifacts_to_export
    
    def cleanup_old_artifacts(self, older_than_days: int = 90) -> int:
        """Clean up artifacts older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        
        artifacts_to_remove = [
            artifact_id for artifact_id, artifact in self.artifacts.items()
            if artifact.created_at < cutoff_date
        ]
        
        for artifact_id in artifacts_to_remove:
            del self.artifacts[artifact_id]
        
        logger.info(f"Cleaned up {len(artifacts_to_remove)} old PALD artifacts")
        return len(artifacts_to_remove)
    
    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about stored artifacts."""
        if not self.artifacts:
            return {
                "total_artifacts": 0,
                "unique_sessions": 0,
                "unique_users": 0,
                "date_range": None
            }
        
        artifacts = list(self.artifacts.values())
        
        return {
            "total_artifacts": len(artifacts),
            "unique_sessions": len(set(a.session_id for a in artifacts)),
            "unique_users": len(set(a.user_pseudonym for a in artifacts)),
            "date_range": {
                "earliest": min(a.created_at for a in artifacts).isoformat(),
                "latest": max(a.created_at for a in artifacts).isoformat()
            },
            "artifacts_with_diffs": len([a for a in artifacts if a.pald_diff is not None])
        }
    
    def _generate_pseudonym(self, user_id: str) -> str:
        """Generate pseudonymized identifier for user."""
        # Use a hash-based pseudonym that's consistent but not reversible
        hash_obj = hashlib.sha256(f"pald_user_{user_id}".encode())
        return f"user_{hash_obj.hexdigest()[:16]}"
    
    def _hash_text(self, text: str) -> str:
        """Generate hash of text for tracking without storing content."""
        if not text:
            return ""
        hash_obj = hashlib.sha256(text.encode())
        return hash_obj.hexdigest()[:16]
    
    def _serialize_diff_result(self, diff_result: PALDDiffResult) -> dict[str, Any]:
        """Serialize diff result for export."""
        return {
            "matches": diff_result.matches,
            "hallucinations": diff_result.hallucinations,
            "missing_fields": diff_result.missing_fields,
            "similarity_score": diff_result.similarity_score,
            "field_classifications": {k: v.value for k, v in diff_result.field_classifications.items()},
            "summary": diff_result.summary,
            "metadata": diff_result.metadata
        }


# Global instances
pald_diff_calculator = PALDDiffCalculator()
pald_persistence_manager = PALDPersistenceManager()