"""
Tests for data models and database functionality.
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.data.models import (
    Base,
    ConsentRecord,
    ConsentType,
    PALDData,
    PALDSchemaVersion,
    User,
    UserRole,
)
from src.data.repositories import ConsentRepository, PALDDataRepository, UserRepository
from src.data.schemas import ConsentRecordCreate, PALDDataCreate, UserCreate


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


def test_user_model_creation(db_session):
    """Test User model creation and validation."""
    user = User(
        username="testuser",
        password_hash="hashed_password",
        role=UserRole.PARTICIPANT.value,
        pseudonym="pseudo_123",
    )

    db_session.add(user)
    db_session.commit()

    # Verify user was created
    retrieved_user = db_session.query(User).filter(User.username == "testuser").first()
    assert retrieved_user is not None
    assert retrieved_user.username == "testuser"
    assert retrieved_user.role == UserRole.PARTICIPANT.value
    assert retrieved_user.pseudonym == "pseudo_123"
    assert retrieved_user.is_active is True


def test_user_repository(db_session):
    """Test UserRepository functionality."""
    repo = UserRepository(db_session)

    # Test user creation
    user_data = UserCreate(username="testuser", password="password123", role=UserRole.PARTICIPANT)
    user = repo.create(user_data, "hashed_password", "pseudo_123")

    assert user is not None
    assert user.username == "testuser"
    assert user.role == UserRole.PARTICIPANT.value

    # Test get by username
    retrieved_user = repo.get_by_username("testuser")
    assert retrieved_user is not None
    assert retrieved_user.id == user.id

    # Test get by pseudonym
    retrieved_user = repo.get_by_pseudonym("pseudo_123")
    assert retrieved_user is not None
    assert retrieved_user.id == user.id


def test_consent_model_and_repository(db_session):
    """Test ConsentRecord model and repository."""
    # Create a user first
    user = User(
        username="testuser",
        password_hash="hashed_password",
        role=UserRole.PARTICIPANT.value,
        pseudonym="pseudo_123",
    )
    db_session.add(user)
    db_session.commit()

    # Test consent repository
    consent_repo = ConsentRepository(db_session)

    consent_data = ConsentRecordCreate(
        consent_type=ConsentType.DATA_PROCESSING,
        consent_given=True,
        consent_version="1.0",
        consent_metadata={"source": "test"},
    )

    consent = consent_repo.create(user.id, consent_data)
    assert consent is not None
    assert consent.consent_type == ConsentType.DATA_PROCESSING.value
    assert consent.consent_given is True

    # Test consent checking
    has_consent = consent_repo.check_consent(user.id, ConsentType.DATA_PROCESSING)
    assert has_consent is True

    # Test consent withdrawal
    withdrawal_success = consent_repo.withdraw_consent(
        user.id, ConsentType.DATA_PROCESSING, "test withdrawal"
    )
    assert withdrawal_success is True

    # Check consent after withdrawal
    has_consent_after = consent_repo.check_consent(user.id, ConsentType.DATA_PROCESSING)
    assert has_consent_after is False


def test_pald_schema_version(db_session):
    """Test PALDSchemaVersion model."""
    schema = PALDSchemaVersion(
        version="1.0.0",
        schema_content={"type": "object", "properties": {"test": {"type": "string"}}},
        is_active=True,
        migration_notes="Initial schema",
    )

    db_session.add(schema)
    db_session.commit()

    retrieved_schema = (
        db_session.query(PALDSchemaVersion).filter(PALDSchemaVersion.version == "1.0.0").first()
    )
    assert retrieved_schema is not None
    assert retrieved_schema.is_active is True
    assert "test" in retrieved_schema.schema_content["properties"]


def test_pald_data_model_and_repository(db_session):
    """Test PALDData model and repository."""
    # Create user and schema first
    user = User(
        username="testuser",
        password_hash="hashed_password",
        role=UserRole.PARTICIPANT.value,
        pseudonym="pseudo_123",
    )
    db_session.add(user)

    schema = PALDSchemaVersion(
        version="1.0.0",
        schema_content={"type": "object", "properties": {"learning_style": {"type": "string"}}},
        is_active=True,
    )
    db_session.add(schema)
    db_session.commit()

    # Test PALD data repository
    pald_repo = PALDDataRepository(db_session)

    pald_data = PALDData(
        user_id=user.id,
        pald_content={"learning_style": "visual", "difficulty": "intermediate"},
        schema_version="1.0.0",
    )

    pald = pald_repo.create(pald_data)
    assert pald is not None
    assert pald.pald_content["learning_style"] == "visual"
    assert pald.schema_version == "1.0.0"

    # Test get by user
    retrieved_pald = pald_repo.get_by_user(user.id)
    assert retrieved_pald is not None
    assert retrieved_pald.id == pald.id


def test_database_relationships(db_session):
    """Test database relationships between models."""
    # Create user
    user = User(
        username="testuser",
        password_hash="hashed_password",
        role=UserRole.PARTICIPANT.value,
        pseudonym="pseudo_123",
    )
    db_session.add(user)

    # Create schema
    schema = PALDSchemaVersion(version="1.0.0", schema_content={"type": "object"}, is_active=True)
    db_session.add(schema)
    db_session.commit()

    # Create consent record
    consent = ConsentRecord(
        user_id=user.id,
        consent_type=ConsentType.DATA_PROCESSING.value,
        consent_given=True,
        consent_version="1.0",
    )
    db_session.add(consent)

    # Create PALD data
    pald = PALDData(user_id=user.id, pald_content={"test": "data"}, schema_version="1.0.0")
    db_session.add(pald)
    db_session.commit()

    # Test relationships
    assert len(user.consent_records) == 1
    assert len(user.pald_data) == 1
    assert user.consent_records[0].consent_type == ConsentType.DATA_PROCESSING.value
    assert user.pald_data[0].pald_content["test"] == "data"

    # Test schema relationship
    assert pald.schema_version_obj.version == "1.0.0"


def test_model_validation():
    """Test model validation."""
    # Test invalid user role
    with pytest.raises(ValueError):
        user = User(
            username="testuser",
            password_hash="hashed_password",
            role="invalid_role",
            pseudonym="pseudo_123",
        )
        user.validate_role("role", "invalid_role")

    # Test invalid consent type
    with pytest.raises(ValueError):
        consent = ConsentRecord(
            user_id=uuid4(), consent_type="invalid_type", consent_given=True, consent_version="1.0"
        )
        consent.validate_consent_type("consent_type", "invalid_type")


if __name__ == "__main__":
    pytest.main([__file__])
