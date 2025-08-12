"""
Tests for PALD logic layer.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.data.models import Base, PALDAttributeCandidate, User, UserRole
from src.data.schemas import PALDDataCreate, PALDDataUpdate, PALDValidationResult
from src.logic.pald import PALDManager, PALDSchemaManager


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


class TestPALDManager:
    """Test PALD manager business logic."""

    def test_create_pald_data(self, db_session):
        """Test creating PALD data."""
        # Create test user
        user = User(
            username="testuser",
            password_hash="hashed",
            role=UserRole.PARTICIPANT.value,
            pseudonym="test_pseudo",
        )
        db_session.add(user)
        db_session.commit()

        manager = PALDManager(db_session)

        # Ensure schema exists
        version, schema = manager.schema_service.get_current_schema()

        pald_create = PALDDataCreate(
            pald_content={
                "appearance": {"gender": "female", "age_range": "adult"},
                "personality": {"teaching_style": "encouraging"},
                "expertise": {"subject_areas": ["math"], "experience_level": "expert"},
                "interaction_preferences": {"preferred_pace": "moderate"},
            },
            schema_version=version,
        )

        result = manager.create_pald_data(user.id, pald_create)

        assert result.user_id == user.id
        assert result.pald_content == pald_create.pald_content
        assert result.schema_version == version
        assert result.is_validated is True

    def test_update_pald_data(self, db_session):
        """Test updating PALD data."""
        # Create test user and PALD data
        user = User(
            username="testuser",
            password_hash="hashed",
            role=UserRole.PARTICIPANT.value,
            pseudonym="test_pseudo",
        )
        db_session.add(user)
        db_session.commit()

        manager = PALDManager(db_session)
        version, schema = manager.schema_service.get_current_schema()

        # Create initial PALD data
        pald_create = PALDDataCreate(
            pald_content={
                "appearance": {"gender": "male"},
                "personality": {"teaching_style": "formal"},
                "expertise": {"subject_areas": ["science"], "experience_level": "intermediate"},
                "interaction_preferences": {"preferred_pace": "slow"},
            },
            schema_version=version,
        )

        created_pald = manager.create_pald_data(user.id, pald_create)

        # Update the PALD data
        pald_update = PALDDataUpdate(
            pald_content={
                "appearance": {"gender": "female", "age_range": "young_adult"},
                "personality": {"teaching_style": "encouraging"},
                "expertise": {"subject_areas": ["math", "science"], "experience_level": "expert"},
                "interaction_preferences": {"preferred_pace": "moderate"},
            }
        )

        updated_pald = manager.update_pald_data(created_pald.id, user.id, pald_update)

        assert updated_pald.pald_content["appearance"]["gender"] == "female"
        assert updated_pald.pald_content["personality"]["teaching_style"] == "encouraging"
        assert "math" in updated_pald.pald_content["expertise"]["subject_areas"]

    def test_get_user_pald_data(self, db_session):
        """Test getting user PALD data."""
        # Create test user
        user = User(
            username="testuser",
            password_hash="hashed",
            role=UserRole.PARTICIPANT.value,
            pseudonym="test_pseudo",
        )
        db_session.add(user)
        db_session.commit()

        manager = PALDManager(db_session)
        version, schema = manager.schema_service.get_current_schema()

        # Create multiple PALD data entries
        for i in range(3):
            pald_create = PALDDataCreate(
                pald_content={
                    "appearance": {"gender": "female"},
                    "personality": {"teaching_style": f"style_{i}"},
                    "expertise": {"subject_areas": ["math"], "experience_level": "expert"},
                    "interaction_preferences": {"preferred_pace": "moderate"},
                },
                schema_version=version,
            )
            manager.create_pald_data(user.id, pald_create)

        pald_data_list = manager.get_user_pald_data(user.id)

        assert len(pald_data_list) == 3
        assert all(pald.user_id == user.id for pald in pald_data_list)

    def test_validate_pald_data(self, db_session):
        """Test PALD data validation."""
        manager = PALDManager(db_session)

        # Get current schema
        version, schema = manager.schema_service.get_current_schema()

        valid_data = {
            "appearance": {"gender": "male", "age_range": "adult"},
            "personality": {"teaching_style": "formal"},
            "expertise": {"subject_areas": ["math"], "experience_level": "expert"},
            "interaction_preferences": {"preferred_pace": "moderate"},
        }

        result = manager.validate_pald_data(valid_data)

        assert isinstance(result, PALDValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_compare_pald_data(self, db_session):
        """Test comparing PALD data."""
        # Create test user
        user = User(
            username="testuser",
            password_hash="hashed",
            role=UserRole.PARTICIPANT.value,
            pseudonym="test_pseudo",
        )
        db_session.add(user)
        db_session.commit()

        manager = PALDManager(db_session)
        version, schema = manager.schema_service.get_current_schema()

        # Create two PALD data entries
        pald_create_a = PALDDataCreate(
            pald_content={
                "appearance": {"gender": "male", "age_range": "adult"},
                "personality": {"teaching_style": "formal"},
                "expertise": {"subject_areas": ["math"], "experience_level": "expert"},
                "interaction_preferences": {"preferred_pace": "slow"},
            },
            schema_version=version,
        )

        pald_create_b = PALDDataCreate(
            pald_content={
                "appearance": {"gender": "female", "age_range": "adult"},
                "personality": {"teaching_style": "encouraging"},
                "expertise": {"subject_areas": ["math", "science"], "experience_level": "expert"},
                "interaction_preferences": {"preferred_pace": "moderate"},
            },
            schema_version=version,
        )

        pald_a = manager.create_pald_data(user.id, pald_create_a)
        pald_b = manager.create_pald_data(user.id, pald_create_b)

        diff = manager.compare_pald_data(pald_a.id, pald_b.id, user.id)

        assert len(diff.modified_fields) > 0
        assert len(diff.unchanged_fields) > 0
        assert 0 <= diff.similarity_score <= 1

    def test_calculate_pald_coverage(self, db_session):
        """Test calculating PALD coverage."""
        # Create test user
        user = User(
            username="testuser",
            password_hash="hashed",
            role=UserRole.PARTICIPANT.value,
            pseudonym="test_pseudo",
        )
        db_session.add(user)
        db_session.commit()

        manager = PALDManager(db_session)
        version, schema = manager.schema_service.get_current_schema()

        # Create partial PALD data
        pald_create = PALDDataCreate(
            pald_content={
                "appearance": {"gender": "male"},  # Partial appearance data
                "personality": {"teaching_style": "formal"},  # Partial personality data
                "expertise": {"subject_areas": ["math"], "experience_level": "expert"},
                "interaction_preferences": {"preferred_pace": "moderate"},
            },
            schema_version=version,
        )

        pald = manager.create_pald_data(user.id, pald_create)
        coverage = manager.calculate_pald_coverage(pald.id, user.id)

        assert coverage.total_fields > 0
        assert coverage.filled_fields > 0
        assert 0 <= coverage.coverage_percentage <= 100
        assert len(coverage.missing_fields) >= 0

    def test_process_chat_for_attribute_extraction(self, db_session):
        """Test processing chat for attribute extraction."""
        # Create test user
        user = User(
            username="testuser",
            password_hash="hashed",
            role=UserRole.PARTICIPANT.value,
            pseudonym="test_pseudo",
        )
        db_session.add(user)
        db_session.commit()

        manager = PALDManager(db_session)

        chat_text = "I want my tutor to be friendly and patient with brown hair."

        attributes = manager.process_chat_for_attribute_extraction(user.id, chat_text)

        # Result depends on whether evolution is enabled
        assert isinstance(attributes, list)

    def test_get_schema_evolution_status(self, db_session):
        """Test getting schema evolution status."""
        manager = PALDManager(db_session)

        # Create some test attribute candidates
        candidate = PALDAttributeCandidate(
            attribute_name="test_attribute",
            mention_count=5,
            threshold_reached=True,
            added_to_schema=False,
        )
        db_session.add(candidate)
        db_session.commit()

        status = manager.get_schema_evolution_status()

        assert "current_schema_version" in status
        assert "evolution_enabled" in status
        assert "candidates_ready_for_evolution" in status
        assert "total_attribute_candidates" in status
        assert "ready_candidates" in status

        assert status["total_attribute_candidates"] >= 1

    def test_permission_checks(self, db_session):
        """Test that permission checks work correctly."""
        # Create two test users
        user1 = User(
            username="user1",
            password_hash="hashed",
            role=UserRole.PARTICIPANT.value,
            pseudonym="pseudo1",
        )
        user2 = User(
            username="user2",
            password_hash="hashed",
            role=UserRole.PARTICIPANT.value,
            pseudonym="pseudo2",
        )
        db_session.add_all([user1, user2])
        db_session.commit()

        manager = PALDManager(db_session)
        version, schema = manager.schema_service.get_current_schema()

        # Create PALD data for user1
        pald_create = PALDDataCreate(
            pald_content={
                "appearance": {"gender": "male"},
                "personality": {"teaching_style": "formal"},
                "expertise": {"subject_areas": ["math"], "experience_level": "expert"},
                "interaction_preferences": {"preferred_pace": "moderate"},
            },
            schema_version=version,
        )

        pald = manager.create_pald_data(user1.id, pald_create)

        # Try to access with user2 - should fail
        with pytest.raises(ValueError, match="permission"):
            manager.get_pald_data_by_id(pald.id, user2.id)

        # Try to update with user2 - should fail
        with pytest.raises(ValueError, match="permission"):
            manager.update_pald_data(pald.id, user2.id, PALDDataUpdate(pald_content={}))


class TestPALDSchemaManager:
    """Test PALD schema manager business logic."""

    def test_get_current_schema(self, db_session):
        """Test getting current schema."""
        manager = PALDSchemaManager(db_session)

        schema = manager.get_current_schema()

        assert schema.version is not None
        assert schema.schema_content is not None
        assert schema.is_active is True

    def test_create_schema_version(self, db_session):
        """Test creating new schema version."""
        manager = PALDSchemaManager(db_session)

        test_schema = {"type": "object", "properties": {"test_field": {"type": "string"}}}

        schema = manager.create_schema_version(
            version="2.0.0", schema_content=test_schema, migration_notes="Test schema creation"
        )

        assert schema.version == "2.0.0"
        assert schema.schema_content == test_schema
        assert schema.migration_notes == "Test schema creation"

    def test_activate_schema_version(self, db_session):
        """Test activating a schema version."""
        manager = PALDSchemaManager(db_session)

        # Create a new schema version
        test_schema = {"type": "object", "properties": {"new_field": {"type": "string"}}}

        manager.create_schema_version(version="3.0.0", schema_content=test_schema)

        # Activate it
        activated_schema = manager.activate_schema_version("3.0.0")

        assert activated_schema.version == "3.0.0"
        assert activated_schema.is_active is True

        # Check that previous active schema is deactivated
        all_schemas = manager.get_all_schema_versions()
        active_schemas = [s for s in all_schemas if s.is_active]
        assert len(active_schemas) == 1
        assert active_schemas[0].version == "3.0.0"

    def test_get_all_schema_versions(self, db_session):
        """Test getting all schema versions."""
        manager = PALDSchemaManager(db_session)

        # Ensure we have at least one schema (the default)
        current_schema = manager.get_current_schema()

        all_schemas = manager.get_all_schema_versions()

        assert len(all_schemas) >= 1
        assert any(s.version == current_schema.version for s in all_schemas)


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        password_hash="hashed_password",
        role=UserRole.PARTICIPANT.value,
        pseudonym="test_pseudonym",
    )
    db_session.add(user)
    db_session.commit()
    return user
