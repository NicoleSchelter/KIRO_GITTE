"""
Tests for authentication logic and session management.
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.data.models import Base, UserRole
from src.data.repositories import UserRepository
from src.data.schemas import UserCreate, UserLogin
from src.logic.authentication import (
    AuthenticationError,
    AuthenticationLogic,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from src.services.session_manager import SessionManager


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
def user_repository(db_session):
    """Create user repository for testing."""
    return UserRepository(db_session)


@pytest.fixture
def session_manager():
    """Create session manager for testing."""
    manager = SessionManager()
    # Clean up any existing sessions
    manager.cleanup_all_sessions()
    return manager


@pytest.fixture
def auth_logic(user_repository, session_manager):
    """Create authentication logic for testing."""
    return AuthenticationLogic(user_repository, session_manager)


@pytest.fixture
def sample_user_data():
    """Sample user registration data."""
    return UserCreate(username="testuser", password="SecurePass123", role=UserRole.PARTICIPANT)


@pytest.fixture
def sample_admin_data():
    """Sample admin registration data."""
    return UserCreate(username="admin", password="AdminPass123", role=UserRole.ADMIN)


class TestAuthenticationLogic:
    """Test authentication logic functionality."""

    def test_register_user_success(self, auth_logic, sample_user_data):
        """Test successful user registration."""
        user_response = auth_logic.register_user(sample_user_data)

        assert user_response.username == "testuser"
        assert user_response.role == UserRole.PARTICIPANT
        assert user_response.pseudonym.startswith("GITTE_")
        assert len(user_response.pseudonym) == 14  # GITTE_ + 8 chars
        assert user_response.is_active is True

    def test_register_user_duplicate_username(self, auth_logic, sample_user_data):
        """Test registration with duplicate username."""
        # Register first user
        auth_logic.register_user(sample_user_data)

        # Try to register same username again
        with pytest.raises(UserAlreadyExistsError):
            auth_logic.register_user(sample_user_data)

    def test_register_user_unique_pseudonyms(self, auth_logic):
        """Test that multiple users get unique pseudonyms."""
        user1_data = UserCreate(username="user1", password="password123", role=UserRole.PARTICIPANT)
        user2_data = UserCreate(username="user2", password="password123", role=UserRole.PARTICIPANT)

        user1 = auth_logic.register_user(user1_data)
        user2 = auth_logic.register_user(user2_data)

        assert user1.pseudonym != user2.pseudonym
        assert user1.pseudonym.startswith("GITTE_")
        assert user2.pseudonym.startswith("GITTE_")

    def test_authenticate_user_success(self, auth_logic, sample_user_data):
        """Test successful user authentication."""
        # Register user first
        registered_user = auth_logic.register_user(sample_user_data)

        # Authenticate user
        login_data = UserLogin(username="testuser", password="SecurePass123")
        authenticated_user = auth_logic.authenticate_user(login_data)

        assert authenticated_user.id == registered_user.id
        assert authenticated_user.username == "testuser"
        assert authenticated_user.role == UserRole.PARTICIPANT

    def test_authenticate_user_invalid_username(self, auth_logic):
        """Test authentication with invalid username."""
        login_data = UserLogin(username="nonexistent", password="password")

        with pytest.raises(InvalidCredentialsError):
            auth_logic.authenticate_user(login_data)

    def test_authenticate_user_invalid_password(self, auth_logic, sample_user_data):
        """Test authentication with invalid password."""
        # Register user first
        auth_logic.register_user(sample_user_data)

        # Try to authenticate with wrong password
        login_data = UserLogin(username="testuser", password="WrongPassword")

        with pytest.raises(InvalidCredentialsError):
            auth_logic.authenticate_user(login_data)

    def test_authenticate_inactive_user(self, auth_logic, sample_user_data, user_repository):
        """Test authentication with inactive user."""
        # Register user first
        registered_user = auth_logic.register_user(sample_user_data)

        # Deactivate user
        user_record = user_repository.get_by_id(registered_user.id)
        user_record.is_active = False
        user_repository.session.commit()

        # Try to authenticate inactive user
        login_data = UserLogin(username="testuser", password="SecurePass123")

        with pytest.raises(InactiveUserError):
            auth_logic.authenticate_user(login_data)

    def test_login_user_success(self, auth_logic, sample_user_data):
        """Test successful user login."""
        # Register user first
        auth_logic.register_user(sample_user_data)

        # Login user
        login_data = UserLogin(username="testuser", password="SecurePass123")
        login_result = auth_logic.login_user(login_data)

        assert "user" in login_result
        assert "session" in login_result
        assert "login_time" in login_result
        assert login_result["user"].username == "testuser"
        assert "session_id" in login_result["session"]

    def test_logout_user_success(self, auth_logic, sample_user_data):
        """Test successful user logout."""
        # Register and login user
        auth_logic.register_user(sample_user_data)
        login_data = UserLogin(username="testuser", password="SecurePass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Logout user
        logout_success = auth_logic.logout_user(session_id)
        assert logout_success is True

        # Verify session is invalidated
        current_user = auth_logic.get_current_user(session_id)
        assert current_user is None

    def test_get_current_user_valid_session(self, auth_logic, sample_user_data):
        """Test getting current user with valid session."""
        # Register and login user
        auth_logic.register_user(sample_user_data)
        login_data = UserLogin(username="testuser", password="SecurePass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Get current user
        current_user = auth_logic.get_current_user(session_id)
        assert current_user is not None
        assert current_user.username == "testuser"

    def test_get_current_user_invalid_session(self, auth_logic):
        """Test getting current user with invalid session."""
        current_user = auth_logic.get_current_user("invalid_session_id")
        assert current_user is None

    def test_check_user_role_participant(self, auth_logic, sample_user_data):
        """Test role checking for participant user."""
        # Register and login participant
        auth_logic.register_user(sample_user_data)
        login_data = UserLogin(username="testuser", password="SecurePass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Check participant role
        has_participant_role = auth_logic.check_user_role(session_id, UserRole.PARTICIPANT)
        assert has_participant_role is True

        # Check admin role (should be False)
        has_admin_role = auth_logic.check_user_role(session_id, UserRole.ADMIN)
        assert has_admin_role is False

    def test_check_user_role_admin(self, auth_logic, sample_admin_data):
        """Test role checking for admin user."""
        # Register and login admin
        auth_logic.register_user(sample_admin_data)
        login_data = UserLogin(username="admin", password="AdminPass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Admin should have access to both roles
        has_admin_role = auth_logic.check_user_role(session_id, UserRole.ADMIN)
        assert has_admin_role is True

        has_participant_role = auth_logic.check_user_role(session_id, UserRole.PARTICIPANT)
        assert has_participant_role is True  # Admin has access to everything

    def test_require_authentication_success(self, auth_logic, sample_user_data):
        """Test require authentication with valid session."""
        # Register and login user
        auth_logic.register_user(sample_user_data)
        login_data = UserLogin(username="testuser", password="SecurePass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Require authentication
        user = auth_logic.require_authentication(session_id)
        assert user.username == "testuser"

    def test_require_authentication_failure(self, auth_logic):
        """Test require authentication with invalid session."""
        with pytest.raises(AuthenticationError):
            auth_logic.require_authentication("invalid_session_id")

    def test_require_role_success(self, auth_logic, sample_user_data):
        """Test require role with correct role."""
        # Register and login user
        auth_logic.register_user(sample_user_data)
        login_data = UserLogin(username="testuser", password="SecurePass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Require participant role
        user = auth_logic.require_role(session_id, UserRole.PARTICIPANT)
        assert user.username == "testuser"

    def test_require_role_failure(self, auth_logic, sample_user_data):
        """Test require role with incorrect role."""
        # Register and login participant
        auth_logic.register_user(sample_user_data)
        login_data = UserLogin(username="testuser", password="SecurePass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Require admin role (should fail)
        with pytest.raises(AuthenticationError):
            auth_logic.require_role(session_id, UserRole.ADMIN)

    def test_require_admin_success(self, auth_logic, sample_admin_data):
        """Test require admin with admin user."""
        # Register and login admin
        auth_logic.register_user(sample_admin_data)
        login_data = UserLogin(username="admin", password="AdminPass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Require admin role
        user = auth_logic.require_admin(session_id)
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN

    def test_require_admin_failure(self, auth_logic, sample_user_data):
        """Test require admin with participant user."""
        # Register and login participant
        auth_logic.register_user(sample_user_data)
        login_data = UserLogin(username="testuser", password="SecurePass123")
        login_result = auth_logic.login_user(login_data)

        session_id = login_result["session"]["session_id"]

        # Require admin role (should fail)
        with pytest.raises(AuthenticationError):
            auth_logic.require_admin(session_id)

    def test_password_hashing_and_verification(self, auth_logic):
        """Test password hashing and verification."""
        password = "TestPassword123"

        # Hash password
        hashed = auth_logic._hash_password(password)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long

        # Verify correct password
        assert auth_logic._verify_password(password, hashed) is True

        # Verify incorrect password
        assert auth_logic._verify_password("WrongPassword", hashed) is False

    def test_pseudonym_generation(self, auth_logic):
        """Test pseudonym generation."""
        pseudonym1 = auth_logic._generate_pseudonym()
        pseudonym2 = auth_logic._generate_pseudonym()

        # Check format
        assert pseudonym1.startswith("GITTE_")
        assert pseudonym2.startswith("GITTE_")
        assert len(pseudonym1) == 14
        assert len(pseudonym2) == 14

        # Check uniqueness
        assert pseudonym1 != pseudonym2


class TestSessionManager:
    """Test session manager functionality."""

    def test_create_session(self, session_manager):
        """Test session creation."""
        user_id = uuid4()
        user_role = UserRole.PARTICIPANT.value

        session_data = session_manager.create_session(user_id, user_role)

        assert "session_id" in session_data
        assert session_data["user_id"] == user_id
        assert session_data["user_role"] == user_role
        assert "created_at" in session_data
        assert "expires_at" in session_data

    def test_get_session_valid(self, session_manager):
        """Test getting valid session."""
        user_id = uuid4()
        user_role = UserRole.PARTICIPANT.value

        # Create session
        session_data = session_manager.create_session(user_id, user_role)
        session_id = session_data["session_id"]

        # Get session
        retrieved_session = session_manager.get_session(session_id)
        assert retrieved_session is not None
        assert retrieved_session["user_id"] == user_id

    def test_get_session_invalid(self, session_manager):
        """Test getting invalid session."""
        retrieved_session = session_manager.get_session("invalid_session_id")
        assert retrieved_session is None

    def test_invalidate_session(self, session_manager):
        """Test session invalidation."""
        user_id = uuid4()
        user_role = UserRole.PARTICIPANT.value

        # Create session
        session_data = session_manager.create_session(user_id, user_role)
        session_id = session_data["session_id"]

        # Invalidate session
        success = session_manager.invalidate_session(session_id)
        assert success is True

        # Verify session is gone
        retrieved_session = session_manager.get_session(session_id)
        assert retrieved_session is None

    def test_refresh_session(self, session_manager):
        """Test session refresh."""
        user_id = uuid4()
        user_role = UserRole.PARTICIPANT.value

        # Create session
        session_data = session_manager.create_session(user_id, user_role)
        session_id = session_data["session_id"]
        original_expires_at = session_data["expires_at"]

        # Wait a moment and refresh
        import time

        time.sleep(0.1)

        success = session_manager.refresh_session(session_id)
        assert success is True

        # Get updated session
        updated_session = session_manager.get_session(session_id)
        assert updated_session["expires_at"] > original_expires_at

    def test_invalidate_user_sessions(self, session_manager):
        """Test invalidating all sessions for a user."""
        user_id = uuid4()
        user_role = UserRole.PARTICIPANT.value

        # Create multiple sessions for the same user
        session1 = session_manager.create_session(user_id, user_role)
        session2 = session_manager.create_session(user_id, user_role)

        # Create session for different user
        other_user_id = uuid4()
        session3 = session_manager.create_session(other_user_id, user_role)

        # Invalidate sessions for first user
        invalidated_count = session_manager.invalidate_user_sessions(user_id)
        assert invalidated_count == 2

        # Verify first user's sessions are gone
        assert session_manager.get_session(session1["session_id"]) is None
        assert session_manager.get_session(session2["session_id"]) is None

        # Verify other user's session still exists
        assert session_manager.get_session(session3["session_id"]) is not None

    def test_get_active_sessions_count(self, session_manager):
        """Test getting active sessions count."""
        initial_count = session_manager.get_active_sessions_count()

        # Create some sessions
        user_id = uuid4()
        session_manager.create_session(user_id, UserRole.PARTICIPANT.value)
        session_manager.create_session(user_id, UserRole.PARTICIPANT.value)

        new_count = session_manager.get_active_sessions_count()
        assert new_count == initial_count + 2

    def test_get_user_sessions(self, session_manager):
        """Test getting sessions for a specific user."""
        user_id = uuid4()
        other_user_id = uuid4()

        # Create sessions for first user
        session_manager.create_session(user_id, UserRole.PARTICIPANT.value)
        session_manager.create_session(user_id, UserRole.PARTICIPANT.value)

        # Create session for other user
        session_manager.create_session(other_user_id, UserRole.PARTICIPANT.value)

        # Get sessions for first user
        user_sessions = session_manager.get_user_sessions(user_id)
        assert len(user_sessions) == 2

        for session in user_sessions:
            assert session["user_id"] == user_id

    def test_cleanup_all_sessions(self, session_manager):
        """Test cleaning up all sessions."""
        # Create some sessions
        user_id = uuid4()
        session_manager.create_session(user_id, UserRole.PARTICIPANT.value)
        session_manager.create_session(user_id, UserRole.PARTICIPANT.value)

        # Cleanup all sessions
        cleaned_count = session_manager.cleanup_all_sessions()
        assert cleaned_count == 2

        # Verify no sessions remain
        assert session_manager.get_active_sessions_count() == 0


if __name__ == "__main__":
    pytest.main([__file__])
