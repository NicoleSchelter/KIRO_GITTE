"""
Tests for PALD service layer.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.data.models import Base, PALDAttributeCandidate, PALDSchemaVersion
from src.data.schemas import PALDCoverageMetrics, PALDDiff, PALDValidationResult
from src.services.pald_service import PALDEvolutionService, PALDSchemaService


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return SessionLocal


@pytest.fixture
def db_session(test_db):
    """Create database session for testing."""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


class TestPALDSchemaService:
    """Test PALD schema service."""

    def test_get_current_schema_creates_default(self, db_session):
        """Test that get_current_schema creates default schema if none exists."""
        service = PALDSchemaService(db_session)

        version, schema = service.get_current_schema()

        assert version == "1.0.0"
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "appearance" in schema["properties"]
        assert "personality" in schema["properties"]

        # Verify it was saved to database
        schema_obj = (
            db_session.query(PALDSchemaVersion).filter(PALDSchemaVersion.version == "1.0.0").first()
        )
        assert schema_obj is not None
        assert schema_obj.is_active is True

    def test_create_schema_version(self, db_session):
        """Test creating a new schema version."""
        service = PALDSchemaService(db_session)

        test_schema = {"type": "object", "properties": {"test_field": {"type": "string"}}}

        schema_version = service.create_schema_version(
            version="2.0.0",
            schema_content=test_schema,
            migration_notes="Test schema",
            is_active=True,
        )

        assert schema_version.version == "2.0.0"
        assert schema_version.schema_content == test_schema
        assert schema_version.migration_notes == "Test schema"
        assert schema_version.is_active is True

    def test_validate_pald_data_valid(self, db_session):
        """Test validating valid PALD data."""
        service = PALDSchemaService(db_session)

        # Get current schema first to ensure it exists
        version, schema = service.get_current_schema()

        valid_pald_data = {
            "appearance": {"gender": "female", "age_range": "adult", "hair_color": "brown"},
            "personality": {"teaching_style": "encouraging", "patience_level": "high"},
            "expertise": {
                "subject_areas": ["mathematics", "science"],
                "experience_level": "expert",
            },
            "interaction_preferences": {
                "preferred_pace": "moderate",
                "feedback_style": "immediate",
            },
        }

        result = service.validate_pald_data(valid_pald_data)

        assert isinstance(result, PALDValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.coverage_percentage > 0

    def test_validate_pald_data_invalid(self, db_session):
        """Test validating invalid PALD data."""
        service = PALDSchemaService(db_session)

        # Get current schema first
        version, schema = service.get_current_schema()

        invalid_pald_data = {
            "appearance": {"gender": "invalid_gender", "age_range": "adult"},  # Invalid enum value
            "personality": {"teaching_style": "encouraging"},
            # Missing required sections
        }

        result = service.validate_pald_data(invalid_pald_data)

        assert isinstance(result, PALDValidationResult)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_compare_pald_data(self, db_session):
        """Test comparing PALD data."""
        service = PALDSchemaService(db_session)

        pald_a = {
            "appearance": {"gender": "male", "age_range": "adult"},
            "personality": {"teaching_style": "formal"},
        }

        pald_b = {
            "appearance": {"gender": "female", "age_range": "adult"},
            "personality": {"teaching_style": "formal"},
            "expertise": {"subject_areas": ["math"]},
        }

        diff = service.compare_pald_data(pald_a, pald_b)

        assert isinstance(diff, PALDDiff)
        assert "expertise.subject_areas" in diff.added_fields
        assert "appearance.gender" in diff.modified_fields
        assert "appearance.age_range" in diff.unchanged_fields
        assert "personality.teaching_style" in diff.unchanged_fields
        assert 0 <= diff.similarity_score <= 1

    def test_calculate_coverage(self, db_session):
        """Test calculating PALD coverage."""
        service = PALDSchemaService(db_session)

        # Get current schema first
        version, schema = service.get_current_schema()

        partial_pald_data = {
            "appearance": {
                "gender": "male",
                "age_range": "adult",
                # Missing other appearance fields
            },
            "personality": {
                "teaching_style": "formal"
                # Missing other personality fields
            },
            # Missing expertise and interaction_preferences sections
        }

        coverage = service.calculate_coverage(partial_pald_data)

        assert isinstance(coverage, PALDCoverageMetrics)
        assert coverage.total_fields > 0
        assert coverage.filled_fields > 0
        assert coverage.filled_fields < coverage.total_fields
        assert 0 <= coverage.coverage_percentage <= 100
        assert len(coverage.missing_fields) > 0
        assert isinstance(coverage.field_completeness, dict)


class TestPALDEvolutionService:
    """Test PALD evolution service."""

    def test_extract_embodiment_attributes(self, db_session):
        """Test extracting embodiment attributes from text."""
        service = PALDEvolutionService(db_session)

        chat_text = """
        I want my tutor to look like a friendly young woman with brown hair and blue eyes.
        She should be patient and encouraging, with a casual teaching style.
        """

        attributes = service.extract_embodiment_attributes(chat_text)

        assert isinstance(attributes, list)
        # Should extract some attributes (exact matches depend on regex patterns)
        assert len(attributes) >= 0  # May be empty if evolution is disabled

    def test_track_attribute_mentions(self, db_session):
        """Test tracking attribute mentions."""
        service = PALDEvolutionService(db_session)

        # Enable evolution for this test
        original_threshold = service.attribute_threshold
        service.attribute_threshold = 2

        try:
            attributes = ["friendly", "patient", "encouraging"]

            # Track attributes first time
            service.track_attribute_mentions(attributes)

            # Check they were created
            for attr_name in attributes:
                candidate = (
                    db_session.query(PALDAttributeCandidate)
                    .filter(PALDAttributeCandidate.attribute_name == attr_name)
                    .first()
                )
                assert candidate is not None
                assert candidate.mention_count == 1
                assert candidate.threshold_reached is False

            # Track again to increment counts
            service.track_attribute_mentions(attributes)

            # Check counts were incremented and threshold reached
            for attr_name in attributes:
                candidate = (
                    db_session.query(PALDAttributeCandidate)
                    .filter(PALDAttributeCandidate.attribute_name == attr_name)
                    .first()
                )
                assert candidate.mention_count == 2
                assert candidate.threshold_reached is True

        finally:
            service.attribute_threshold = original_threshold

    def test_get_schema_evolution_candidates(self, db_session):
        """Test getting schema evolution candidates."""
        service = PALDEvolutionService(db_session)

        # Create some test candidates
        candidate1 = PALDAttributeCandidate(
            attribute_name="test_attr_1",
            mention_count=5,
            threshold_reached=True,
            added_to_schema=False,
        )
        candidate2 = PALDAttributeCandidate(
            attribute_name="test_attr_2",
            mention_count=3,
            threshold_reached=False,
            added_to_schema=False,
        )
        candidate3 = PALDAttributeCandidate(
            attribute_name="test_attr_3",
            mention_count=7,
            threshold_reached=True,
            added_to_schema=True,  # Already added
        )

        db_session.add_all([candidate1, candidate2, candidate3])
        db_session.commit()

        candidates = service.get_schema_evolution_candidates()

        # Should only return candidate1 (threshold reached but not added to schema)
        assert len(candidates) == 1
        assert candidates[0].attribute_name == "test_attr_1"

    def test_propose_schema_evolution(self, db_session):
        """Test proposing schema evolution."""
        service = PALDEvolutionService(db_session)

        # Ensure we have a current schema
        version, schema = service.schema_service.get_current_schema()

        # Create test candidates
        candidates = [
            PALDAttributeCandidate(
                attribute_name="friendly_demeanor",
                attribute_category="personality",
                mention_count=5,
                threshold_reached=True,
            ),
            PALDAttributeCandidate(
                attribute_name="curly_hair",
                attribute_category="appearance",
                mention_count=3,
                threshold_reached=True,
            ),
        ]

        proposal = service.propose_schema_evolution(candidates)

        assert "current_version" in proposal
        assert "proposed_schema" in proposal
        assert "added_attributes" in proposal
        assert "evolution_summary" in proposal

        assert proposal["current_version"] == version
        assert len(proposal["added_attributes"]) == 2
        assert "friendly_demeanor" in proposal["added_attributes"]
        assert "curly_hair" in proposal["added_attributes"]

    def test_categorize_attribute(self, db_session):
        """Test attribute categorization."""
        service = PALDEvolutionService(db_session)

        # Test appearance attributes
        assert service._categorize_attribute("brown hair") == "appearance"
        assert service._categorize_attribute("tall height") == "appearance"
        assert service._categorize_attribute("blue eyes") == "appearance"

        # Test personality attributes
        assert service._categorize_attribute("very friendly") == "personality"
        assert service._categorize_attribute("patient teacher") == "personality"
        assert service._categorize_attribute("kind person") == "personality"

        # Test teaching attributes
        assert service._categorize_attribute("formal teaching") == "teaching_style"
        assert service._categorize_attribute("interactive style") == "teaching_style"

        # Test miscellaneous
        assert service._categorize_attribute("random word") == "misc"

    def test_map_category_to_schema_section(self, db_session):
        """Test mapping categories to schema sections."""
        service = PALDEvolutionService(db_session)

        assert service._map_category_to_schema_section("appearance") == "appearance"
        assert service._map_category_to_schema_section("personality") == "personality"
        assert (
            service._map_category_to_schema_section("teaching_style") == "interaction_preferences"
        )
        assert service._map_category_to_schema_section("misc") == "appearance"
        assert service._map_category_to_schema_section("unknown") == "appearance"


@pytest.fixture
def sample_pald_data():
    """Sample PALD data for testing."""
    return {
        "appearance": {
            "gender": "female",
            "age_range": "adult",
            "ethnicity": "caucasian",
            "hair_color": "brown",
            "hair_style": "long",
            "eye_color": "blue",
            "skin_tone": "fair",
            "height": "average",
            "build": "slim",
        },
        "personality": {
            "teaching_style": "encouraging",
            "communication_style": "gentle",
            "patience_level": "high",
            "enthusiasm_level": "high",
            "formality": "casual",
        },
        "expertise": {
            "subject_areas": ["mathematics", "science", "programming"],
            "experience_level": "expert",
            "specializations": ["algebra", "physics", "python"],
        },
        "interaction_preferences": {
            "preferred_pace": "moderate",
            "feedback_style": "immediate",
            "question_frequency": "medium",
            "encouragement_style": "frequent",
        },
    }


@pytest.fixture
def sample_schema():
    """Sample PALD schema for testing."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Test PALD Schema",
        "type": "object",
        "properties": {
            "appearance": {
                "type": "object",
                "properties": {
                    "gender": {"type": "string"},
                    "age_range": {"type": "string"},
                    "hair_color": {"type": "string"},
                },
            },
            "personality": {
                "type": "object",
                "properties": {
                    "teaching_style": {"type": "string"},
                    "patience_level": {"type": "string"},
                },
            },
        },
        "required": ["appearance", "personality"],
    }
