"""
PALD Service Layer
Handles PALD schema management, validation, and evolution operations.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

import jsonschema
from jsonschema import Draft7Validator, ValidationError, validate
from sqlalchemy.orm import Session

from config.config import config
from src.data.models import PALDAttributeCandidate, PALDSchemaVersion
from src.data.schemas import PALDCoverageMetrics, PALDDiff, PALDValidationResult

logger = logging.getLogger(__name__)


class PALDSchemaService:
    """Service for managing PALD schemas and validation."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self._current_schema_cache: dict[str, Any] | None = None
        self._current_version_cache: str | None = None

    def get_current_schema(self) -> tuple[str, dict[str, Any]]:
        """Get the current active PALD schema."""
        if self._current_schema_cache is None or self._current_version_cache is None:
            schema_version = (
                self.db_session.query(PALDSchemaVersion)
                .filter(PALDSchemaVersion.is_active is True)
                .first()
            )

            if not schema_version:
                # Create default schema if none exists
                default_schema = self._get_default_schema()
                schema_version = self.create_schema_version("1.0.0", default_schema, is_active=True)

            self._current_version_cache = schema_version.version
            self._current_schema_cache = schema_version.schema_content

        return self._current_version_cache, self._current_schema_cache

    def create_schema_version(
        self,
        version: str,
        schema_content: dict[str, Any],
        migration_notes: str | None = None,
        is_active: bool = False,
    ) -> PALDSchemaVersion:
        """Create a new PALD schema version."""
        # Validate the schema itself
        try:
            Draft7Validator.check_schema(schema_content)
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON schema: {e}")

        # If setting as active, deactivate current active schema
        if is_active:
            current_active = (
                self.db_session.query(PALDSchemaVersion)
                .filter(PALDSchemaVersion.is_active is True)
                .first()
            )
            if current_active:
                current_active.is_active = False

        schema_version = PALDSchemaVersion(
            version=version,
            schema_content=schema_content,
            migration_notes=migration_notes,
            is_active=is_active,
        )

        self.db_session.add(schema_version)
        self.db_session.commit()

        # Clear cache if we created a new active schema
        if is_active:
            self._current_schema_cache = None
            self._current_version_cache = None

        logger.info(f"Created PALD schema version {version}, active: {is_active}")
        return schema_version

    def validate_pald_data(
        self, pald_data: dict[str, Any], schema_version: str | None = None
    ) -> PALDValidationResult:
        """Validate PALD data against schema."""
        if schema_version:
            schema_obj = (
                self.db_session.query(PALDSchemaVersion)
                .filter(PALDSchemaVersion.version == schema_version)
                .first()
            )
            if not schema_obj:
                return PALDValidationResult(
                    is_valid=False,
                    errors=[f"Schema version {schema_version} not found"],
                    coverage_percentage=0.0,
                )
            schema = schema_obj.schema_content
        else:
            _, schema = self.get_current_schema()

        errors = []
        warnings = []

        try:
            validate(instance=pald_data, schema=schema)
            is_valid = True
        except ValidationError as e:
            is_valid = False
            errors.append(
                f"Validation error at {'.'.join(str(p) for p in e.absolute_path)}: {e.message}"
            )
        except Exception as e:
            is_valid = False
            errors.append(f"Unexpected validation error: {str(e)}")

        # Calculate coverage
        coverage_metrics = self.calculate_coverage(pald_data, schema)

        return PALDValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            coverage_percentage=coverage_metrics.coverage_percentage,
        )

    def compare_pald_data(self, pald_a: dict[str, Any], pald_b: dict[str, Any]) -> PALDDiff:
        """Compare two PALD data objects and return differences."""

        def get_all_keys(data: dict[str, Any], prefix: str = "") -> set:
            """Recursively get all keys from nested dictionary."""
            keys = set()
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.add(full_key)
                if isinstance(value, dict):
                    keys.update(get_all_keys(value, full_key))
            return keys

        def get_value_at_path(data: dict[str, Any], path: str) -> Any:
            """Get value at nested path."""
            keys = path.split(".")
            current = data
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current

        keys_a = get_all_keys(pald_a)
        keys_b = get_all_keys(pald_b)

        added_fields = list(keys_b - keys_a)
        removed_fields = list(keys_a - keys_b)
        common_fields = keys_a & keys_b

        modified_fields = []
        unchanged_fields = []

        for field in common_fields:
            value_a = get_value_at_path(pald_a, field)
            value_b = get_value_at_path(pald_b, field)

            if value_a != value_b:
                modified_fields.append(field)
            else:
                unchanged_fields.append(field)

        # Calculate similarity score
        total_fields = len(keys_a | keys_b)
        if total_fields == 0:
            similarity_score = 1.0
        else:
            unchanged_count = len(unchanged_fields)
            similarity_score = unchanged_count / total_fields

        return PALDDiff(
            added_fields=sorted(added_fields),
            removed_fields=sorted(removed_fields),
            modified_fields=sorted(modified_fields),
            unchanged_fields=sorted(unchanged_fields),
            similarity_score=similarity_score,
        )

    def calculate_coverage(
        self, pald_data: dict[str, Any], schema: dict[str, Any] | None = None
    ) -> PALDCoverageMetrics:
        """Calculate coverage metrics for PALD data."""
        if schema is None:
            _, schema = self.get_current_schema()

        def get_required_fields(schema_obj: dict[str, Any], prefix: str = "") -> set:
            """Get all required fields from schema."""
            fields = set()

            if schema_obj.get("type") == "object":
                properties = schema_obj.get("properties", {})
                schema_obj.get("required", [])

                for prop_name, prop_schema in properties.items():
                    full_name = f"{prefix}.{prop_name}" if prefix else prop_name
                    fields.add(full_name)

                    if prop_schema.get("type") == "object":
                        fields.update(get_required_fields(prop_schema, full_name))

            return fields

        def get_filled_fields(data: dict[str, Any], prefix: str = "") -> set:
            """Get all filled fields from data."""
            fields = set()
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if value is not None and value != "":
                    fields.add(full_key)
                    if isinstance(value, dict):
                        fields.update(get_filled_fields(value, full_key))
            return fields

        def check_field_completeness(
            data: dict[str, Any], schema_obj: dict[str, Any], prefix: str = ""
        ) -> dict[str, bool]:
            """Check completeness of each field."""
            completeness = {}

            if schema_obj.get("type") == "object":
                properties = schema_obj.get("properties", {})

                for prop_name, prop_schema in properties.items():
                    full_name = f"{prefix}.{prop_name}" if prefix else prop_name
                    value = data.get(prop_name)

                    if value is not None and value != "":
                        completeness[full_name] = True
                        if isinstance(value, dict) and prop_schema.get("type") == "object":
                            completeness.update(
                                check_field_completeness(value, prop_schema, full_name)
                            )
                    else:
                        completeness[full_name] = False

            return completeness

        total_fields_set = get_required_fields(schema)
        filled_fields_set = get_filled_fields(pald_data)
        field_completeness = check_field_completeness(pald_data, schema)

        total_fields = len(total_fields_set)
        filled_fields = len(filled_fields_set & total_fields_set)

        coverage_percentage = (filled_fields / total_fields * 100) if total_fields > 0 else 100.0
        missing_fields = list(total_fields_set - filled_fields_set)

        return PALDCoverageMetrics(
            total_fields=total_fields,
            filled_fields=filled_fields,
            coverage_percentage=coverage_percentage,
            missing_fields=sorted(missing_fields),
            field_completeness=field_completeness,
        )

    def _get_default_schema(self) -> dict[str, Any]:
        """Get the default PALD schema."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "PALD Schema",
            "description": "Pedagogical Agent Level of Design schema for embodiment attributes",
            "type": "object",
            "properties": {
                "appearance": {
                    "type": "object",
                    "properties": {
                        "gender": {
                            "type": "string",
                            "enum": ["male", "female", "non-binary", "other"],
                        },
                        "age_range": {
                            "type": "string",
                            "enum": ["child", "teenager", "young_adult", "adult", "elderly"],
                        },
                        "ethnicity": {"type": "string"},
                        "hair_color": {"type": "string"},
                        "hair_style": {"type": "string"},
                        "eye_color": {"type": "string"},
                        "skin_tone": {"type": "string"},
                        "height": {"type": "string", "enum": ["short", "average", "tall"]},
                        "build": {
                            "type": "string",
                            "enum": ["slim", "average", "athletic", "heavy"],
                        },
                    },
                },
                "personality": {
                    "type": "object",
                    "properties": {
                        "teaching_style": {
                            "type": "string",
                            "enum": ["formal", "casual", "encouraging", "challenging"],
                        },
                        "communication_style": {
                            "type": "string",
                            "enum": ["direct", "gentle", "humorous", "serious"],
                        },
                        "patience_level": {"type": "string", "enum": ["low", "medium", "high"]},
                        "enthusiasm_level": {"type": "string", "enum": ["low", "medium", "high"]},
                        "formality": {
                            "type": "string",
                            "enum": ["very_formal", "formal", "casual", "very_casual"],
                        },
                    },
                },
                "expertise": {
                    "type": "object",
                    "properties": {
                        "subject_areas": {"type": "array", "items": {"type": "string"}},
                        "experience_level": {
                            "type": "string",
                            "enum": ["novice", "intermediate", "expert", "master"],
                        },
                        "specializations": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "interaction_preferences": {
                    "type": "object",
                    "properties": {
                        "preferred_pace": {"type": "string", "enum": ["slow", "moderate", "fast"]},
                        "feedback_style": {
                            "type": "string",
                            "enum": ["immediate", "delayed", "summary"],
                        },
                        "question_frequency": {"type": "string", "enum": ["low", "medium", "high"]},
                        "encouragement_style": {
                            "type": "string",
                            "enum": ["minimal", "moderate", "frequent"],
                        },
                    },
                },
            },
            "required": ["appearance", "personality", "expertise", "interaction_preferences"],
        }


class PALDEvolutionService:
    """Service for dynamic PALD schema evolution."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.schema_service = PALDSchemaService(db_session)
        self.attribute_threshold = (
            config.get_feature_flag("enable_pald_evolution") and 5 or 999999
        )  # Default threshold

    def extract_embodiment_attributes(self, chat_text: str) -> list[str]:
        """Extract potential embodiment attributes from chat text."""
        if not config.get_feature_flag("enable_pald_evolution"):
            return []

        # Define patterns for embodiment-related attributes
        embodiment_patterns = [
            # Appearance attributes
            r"\b(?:looks?|appears?|seems?)\s+(?:like\s+)?(?:a\s+)?(\w+(?:\s+\w+)?)\b",
            r"\b(?:has|have|with)\s+(\w+(?:\s+\w+)?)\s+(?:hair|eyes|skin|voice)\b",
            r"\b(?:tall|short|slim|heavy|athletic|muscular|petite)\b",
            r"\b(?:young|old|elderly|middle-aged|teenage)\b",
            # Personality attributes
            r"\b(?:is|are|being)\s+(?:very\s+)?(\w+(?:\s+\w+)?)\b",
            r"\b(?:sounds?|feels?|acts?)\s+(?:like\s+)?(?:a\s+)?(\w+(?:\s+\w+)?)\b",
            r"\b(?:friendly|serious|funny|strict|patient|kind|helpful|encouraging)\b",
            # Teaching style attributes
            r"\b(?:teaches?|explains?|shows?)\s+(?:in\s+a\s+)?(\w+(?:\s+\w+)?)\s+(?:way|manner|style)\b",
            r"\b(?:formal|casual|structured|flexible|interactive|passive)\s+(?:teaching|approach|style)\b",
        ]

        extracted_attributes = set()

        # Convert to lowercase for pattern matching
        text_lower = chat_text.lower()

        for pattern in embodiment_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""

                # Clean and validate the attribute
                attribute = match.strip()
                if len(attribute) > 2 and len(attribute) < 50:  # Reasonable length
                    # Filter out common non-attribute words
                    stop_words = {
                        "the",
                        "a",
                        "an",
                        "and",
                        "or",
                        "but",
                        "in",
                        "on",
                        "at",
                        "to",
                        "for",
                        "of",
                        "with",
                        "by",
                        "from",
                        "up",
                        "about",
                        "into",
                        "through",
                        "during",
                        "before",
                        "after",
                        "above",
                        "below",
                        "between",
                        "among",
                        "this",
                        "that",
                        "these",
                        "those",
                    }

                    if attribute not in stop_words:
                        extracted_attributes.add(attribute)

        return list(extracted_attributes)

    def track_attribute_mentions(self, attributes: list[str]) -> None:
        """Track mentions of attributes for schema evolution."""
        if not config.get_feature_flag("enable_pald_evolution") or not attributes:
            return

        for attribute_name in attributes:
            # Check if attribute already exists
            existing = (
                self.db_session.query(PALDAttributeCandidate)
                .filter(PALDAttributeCandidate.attribute_name == attribute_name)
                .first()
            )

            if existing:
                # Update existing attribute
                existing.mention_count += 1
                existing.last_mentioned = datetime.utcnow()

                # Check if threshold is reached
                if (
                    existing.mention_count >= self.attribute_threshold
                    and not existing.threshold_reached
                ):
                    existing.threshold_reached = True
                    logger.info(
                        f"Attribute '{attribute_name}' reached threshold with {existing.mention_count} mentions"
                    )
            else:
                # Create new attribute candidate
                candidate = PALDAttributeCandidate(
                    attribute_name=attribute_name,
                    attribute_category=self._categorize_attribute(attribute_name),
                    mention_count=1,
                )
                self.db_session.add(candidate)

        self.db_session.commit()

    def get_schema_evolution_candidates(self) -> list[PALDAttributeCandidate]:
        """Get attributes that have reached the threshold for schema evolution."""
        return (
            self.db_session.query(PALDAttributeCandidate)
            .filter(
                PALDAttributeCandidate.threshold_reached,
                ~PALDAttributeCandidate.added_to_schema,
            )
            .order_by(PALDAttributeCandidate.mention_count.desc())
            .all()
        )

    def propose_schema_evolution(self, candidates: list[PALDAttributeCandidate]) -> dict[str, Any]:
        """Propose schema evolution based on attribute candidates."""
        if not candidates:
            return {}

        current_version, current_schema = self.schema_service.get_current_schema()

        # Create a copy of the current schema for modification
        new_schema = json.loads(json.dumps(current_schema))

        # Group candidates by category
        categorized_candidates = {}
        for candidate in candidates:
            category = candidate.attribute_category or "misc"
            if category not in categorized_candidates:
                categorized_candidates[category] = []
            categorized_candidates[category].append(candidate)

        # Add new attributes to appropriate schema sections
        for category, attrs in categorized_candidates.items():
            schema_section = self._map_category_to_schema_section(category)

            if schema_section in new_schema.get("properties", {}):
                properties = new_schema["properties"][schema_section].get("properties", {})

                for attr in attrs:
                    attr_name = attr.attribute_name.replace(" ", "_").lower()
                    if attr_name not in properties:
                        properties[attr_name] = {
                            "type": "string",
                            "description": f"Auto-generated attribute from user interactions (mentioned {attr.mention_count} times)",
                        }

        return {
            "current_version": current_version,
            "proposed_schema": new_schema,
            "added_attributes": [attr.attribute_name for attr in candidates],
            "evolution_summary": f"Added {len(candidates)} new attributes based on user interactions",
        }

    def apply_schema_evolution(self, candidates: list[PALDAttributeCandidate]) -> PALDSchemaVersion:
        """Apply schema evolution by creating a new schema version."""
        proposal = self.propose_schema_evolution(candidates)

        if not proposal:
            raise ValueError("No schema evolution candidates provided")

        # Generate new version number
        current_version = proposal["current_version"]
        version_parts = current_version.split(".")
        major, minor, _patch = int(version_parts[0]), int(version_parts[1]), int(version_parts[2])
        new_version = f"{major}.{minor + 1}.0"  # Increment minor version for schema evolution

        # Create new schema version
        migration_notes = f"Schema evolution: {proposal['evolution_summary']}"
        new_schema_version = self.schema_service.create_schema_version(
            version=new_version,
            schema_content=proposal["proposed_schema"],
            migration_notes=migration_notes,
            is_active=True,
        )

        # Mark candidates as added to schema
        for candidate in candidates:
            candidate.added_to_schema = True
            candidate.schema_version_added = new_version

        self.db_session.commit()

        logger.info(
            f"Applied schema evolution: created version {new_version} with {len(candidates)} new attributes"
        )
        return new_schema_version

    def _categorize_attribute(self, attribute_name: str) -> str:
        """Categorize an attribute based on its name."""
        attribute_lower = attribute_name.lower()

        # Check for specific compound terms first (more specific matches)
        teaching_compounds = [
            "teaching style",
            "interactive style",
            "communication style",
            "formal teaching",
            "casual teaching",
            "structured approach",
            "flexible approach",
        ]

        appearance_compounds = ["hair style", "hair color", "eye color", "skin tone"]

        # Check compound terms first
        for compound in teaching_compounds:
            if compound in attribute_lower:
                return "teaching_style"

        for compound in appearance_compounds:
            if compound in attribute_lower:
                return "appearance"

        # Appearance-related keywords
        appearance_keywords = [
            "hair",
            "eye",
            "skin",
            "tall",
            "short",
            "slim",
            "heavy",
            "athletic",
            "muscular",
            "young",
            "old",
            "elderly",
            "color",
            "build",
            "height",
            "age",
        ]

        # Personality-related keywords
        personality_keywords = [
            "friendly",
            "serious",
            "funny",
            "strict",
            "patient",
            "kind",
            "helpful",
            "encouraging",
            "calm",
            "energetic",
            "quiet",
            "loud",
            "confident",
            "shy",
        ]

        # Teaching-related keywords
        teaching_keywords = [
            "formal",
            "casual",
            "structured",
            "flexible",
            "interactive",
            "passive",
            "teaching",
            "explains",
            "shows",
            "demonstrates",
            "guides",
        ]

        for keyword in appearance_keywords:
            if keyword in attribute_lower:
                return "appearance"

        for keyword in personality_keywords:
            if keyword in attribute_lower:
                return "personality"

        for keyword in teaching_keywords:
            if keyword in attribute_lower:
                return "teaching_style"

        return "misc"

    def _map_category_to_schema_section(self, category: str) -> str:
        """Map attribute category to schema section."""
        mapping = {
            "appearance": "appearance",
            "personality": "personality",
            "teaching_style": "interaction_preferences",
            "misc": "appearance",  # Default to appearance for uncategorized
        }
        return mapping.get(category, "appearance")
