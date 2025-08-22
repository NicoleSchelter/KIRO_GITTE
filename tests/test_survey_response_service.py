"""
Tests for survey response service functionality.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.data.models import Base, User, SurveyResponse, UserRole
from src.services.survey_response_service import SurveyResponseService


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


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        password_hash="hashed_password",
        role=UserRole.PARTICIPANT.value,
        pseudonym="test_pseudonym"
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestSurveyResponseService:
    """Test survey response service functionality."""

    def test_save_new_survey_response(self, db_session, sample_user):
        """Test saving a new survey response."""
        service = SurveyResponseService(db_session)
        
        survey_data = {
            "learning_preferences": {
                "learning_style": "Visual",
                "difficulty_preference": "Intermediate"
            },
            "survey_version": "1.0",
            "survey_skipped": False
        }
        
        # Save without auto-commit to test transaction handling
        result = service.save_survey_response(
            user_id=sample_user.id,
            survey_data=survey_data,
            survey_version="1.0",
            auto_commit=False
        )
        
        assert result is not None
        assert result.user_id == sample_user.id
        assert result.survey_data == survey_data
        assert result.survey_version == "1.0"
        
        # Verify it's in the session but not committed yet
        db_session.flush()
        found = db_session.query(SurveyResponse).filter(
            SurveyResponse.user_id == sample_user.id
        ).first()
        assert found is not None
        assert found.id == result.id

    def test_update_existing_survey_response(self, db_session, sample_user):
        """Test updating an existing survey response."""
        service = SurveyResponseService(db_session)
        
        # Create initial response
        initial_data = {
            "learning_preferences": {"learning_style": "Visual"},
            "survey_version": "1.0"
        }
        
        initial_response = service.save_survey_response(
            user_id=sample_user.id,
            survey_data=initial_data,
            auto_commit=False
        )
        db_session.commit()
        
        # Update the response
        updated_data = {
            "learning_preferences": {"learning_style": "Auditory"},
            "interaction_style": {"communication_style": "Formal"},
            "survey_version": "1.0"
        }
        
        updated_response = service.save_survey_response(
            user_id=sample_user.id,
            survey_data=updated_data,
            auto_commit=False
        )
        
        # Should be the same record, just updated
        assert updated_response.id == initial_response.id
        assert updated_response.survey_data == updated_data
        # Note: updated_at might be the same in fast tests, so we check >= instead
        assert updated_response.updated_at >= initial_response.updated_at

    def test_get_user_survey_data(self, db_session, sample_user):
        """Test retrieving user survey data."""
        service = SurveyResponseService(db_session)
        
        # Initially no data
        result = service.get_user_survey_data(sample_user.id)
        assert result is None
        
        # Save some data
        survey_data = {"test": "data"}
        service.save_survey_response(
            user_id=sample_user.id,
            survey_data=survey_data,
            auto_commit=False
        )
        db_session.commit()
        
        # Now should find it
        result = service.get_user_survey_data(sample_user.id)
        assert result is not None
        assert result.user_id == sample_user.id
        assert result.survey_data == survey_data

    def test_update_survey_response_method(self, db_session, sample_user):
        """Test the update_survey_response method."""
        service = SurveyResponseService(db_session)
        
        # Create initial response
        initial_data = {
            "learning_preferences": {"learning_style": "Visual"},
            "goals": {"learning_goals": "Basic skills"}
        }
        
        service.save_survey_response(
            user_id=sample_user.id,
            survey_data=initial_data,
            auto_commit=False
        )
        db_session.commit()
        
        # Update with partial data
        updates = {
            "learning_preferences": {"learning_style": "Kinesthetic"},
            "new_field": "new_value"
        }
        
        result = service.update_survey_response(
            user_id=sample_user.id,
            updates=updates,
            auto_commit=False
        )
        
        # Should merge the data
        expected_data = {
            "learning_preferences": {"learning_style": "Kinesthetic"},
            "goals": {"learning_goals": "Basic skills"},
            "new_field": "new_value"
        }
        
        assert result.survey_data == expected_data

    def test_update_nonexistent_survey_response(self, db_session, sample_user):
        """Test updating a survey response that doesn't exist."""
        service = SurveyResponseService(db_session)
        
        with pytest.raises(ValueError, match="No survey response found"):
            service.update_survey_response(
                user_id=sample_user.id,
                updates={"test": "data"}
            )

    def test_auto_commit_behavior(self, db_session, sample_user):
        """Test auto_commit parameter behavior."""
        service = SurveyResponseService(db_session)
        
        survey_data = {"test": "data"}
        
        # Test with auto_commit=False
        result = service.save_survey_response(
            user_id=sample_user.id,
            survey_data=survey_data,
            auto_commit=False
        )
        
        # Should be in session but not committed
        assert result is not None
        
        # Rollback to test that it wasn't committed
        db_session.rollback()
        
        # Should not find it after rollback
        found = db_session.query(SurveyResponse).filter(
            SurveyResponse.user_id == sample_user.id
        ).first()
        assert found is None
        
        # Now test with auto_commit=True
        result = service.save_survey_response(
            user_id=sample_user.id,
            survey_data=survey_data,
            auto_commit=True
        )
        
        # Should be committed and findable
        found = db_session.query(SurveyResponse).filter(
            SurveyResponse.user_id == sample_user.id
        ).first()
        assert found is not None
        assert found.id == result.id