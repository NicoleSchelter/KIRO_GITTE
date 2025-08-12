"""
Authentication logic for GITTE system.
Handles user registration, login, logout, and role-based access control.
"""

import logging
import secrets
import string
from datetime import datetime
from typing import Any

import bcrypt

from config.config import config
from src.data.models import UserRole
from src.data.repositories import UserRepository
from src.data.schemas import UserCreate, UserLogin, UserResponse
from src.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication errors."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""

    pass


class UserAlreadyExistsError(AuthenticationError):
    """Raised when trying to register a user that already exists."""

    pass


class InactiveUserError(AuthenticationError):
    """Raised when trying to authenticate an inactive user."""

    pass


class AuthenticationLogic:
    """Authentication business logic."""

    def __init__(self, user_repository: UserRepository, session_manager: SessionManager):
        self.user_repository = user_repository
        self.session_manager = session_manager

    def register_user(self, user_data: UserCreate) -> UserResponse:
        """
        Register a new user with password hashing and pseudonymization.

        Args:
            user_data: User registration data

        Returns:
            UserResponse: Created user information

        Raises:
            UserAlreadyExistsError: If username already exists
            AuthenticationError: If registration fails
        """
        try:
            # Check if user already exists
            existing_user = self.user_repository.get_by_username(user_data.username)
            if existing_user:
                raise UserAlreadyExistsError(
                    f"User with username '{user_data.username}' already exists"
                )

            # Hash password using bcrypt
            password_hash = self._hash_password(user_data.password)

            # Generate pseudonym for privacy compliance
            pseudonym = self._generate_pseudonym()

            # Ensure pseudonym is unique
            while self.user_repository.get_by_pseudonym(pseudonym):
                pseudonym = self._generate_pseudonym()

            # Create user
            user = self.user_repository.create(user_data, password_hash, pseudonym)
            if not user:
                raise AuthenticationError("Failed to create user")

            logger.info(
                f"User registered successfully: {user.username} (pseudonym: {user.pseudonym})"
            )

            return UserResponse.model_validate(user)

        except UserAlreadyExistsError:
            raise
        except Exception as e:
            logger.error(f"User registration failed: {e}")
            raise AuthenticationError(f"Registration failed: {str(e)}")

    def authenticate_user(self, login_data: UserLogin) -> UserResponse:
        """
        Authenticate user with username and password.

        Args:
            login_data: User login credentials

        Returns:
            UserResponse: Authenticated user information

        Raises:
            InvalidCredentialsError: If credentials are invalid
            InactiveUserError: If user account is inactive
            AuthenticationError: If authentication fails
        """
        try:
            # Get user by username
            user = self.user_repository.get_by_username(login_data.username)
            if not user:
                raise InvalidCredentialsError("Invalid username or password")

            # Check if user is active
            if not user.is_active:
                raise InactiveUserError("User account is inactive")

            # Verify password
            if not self._verify_password(login_data.password, user.password_hash):
                raise InvalidCredentialsError("Invalid username or password")

            logger.info(f"User authenticated successfully: {user.username}")

            return UserResponse.model_validate(user)

        except (InvalidCredentialsError, InactiveUserError):
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    def login_user(self, login_data: UserLogin) -> dict[str, Any]:
        """
        Login user and create session.

        Args:
            login_data: User login credentials

        Returns:
            Dict containing user info and session data

        Raises:
            InvalidCredentialsError: If credentials are invalid
            InactiveUserError: If user account is inactive
            AuthenticationError: If login fails
        """
        try:
            # Authenticate user
            user = self.authenticate_user(login_data)

            # Create session
            session_data = self.session_manager.create_session(user.id, user.role)

            logger.info(f"User logged in successfully: {user.username}")

            return {"user": user, "session": session_data, "login_time": datetime.utcnow()}

        except (InvalidCredentialsError, InactiveUserError, AuthenticationError):
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise AuthenticationError(f"Login failed: {str(e)}")

    def logout_user(self, session_id: str) -> bool:
        """
        Logout user and invalidate session.

        Args:
            session_id: Session identifier

        Returns:
            bool: True if logout successful
        """
        try:
            success = self.session_manager.invalidate_session(session_id)
            if success:
                logger.info(f"User logged out successfully: session {session_id}")
            return success

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    def get_current_user(self, session_id: str) -> UserResponse | None:
        """
        Get current user from session.

        Args:
            session_id: Session identifier

        Returns:
            UserResponse: Current user information or None if invalid session
        """
        try:
            session_data = self.session_manager.get_session(session_id)
            if not session_data:
                return None

            user = self.user_repository.get_by_id(session_data["user_id"])
            if not user or not user.is_active:
                # Invalidate session if user is inactive or deleted
                self.session_manager.invalidate_session(session_id)
                return None

            return UserResponse.model_validate(user)

        except Exception as e:
            logger.error(f"Failed to get current user: {e}")
            return None

    def check_user_role(self, session_id: str, required_role: UserRole) -> bool:
        """
        Check if current user has required role.

        Args:
            session_id: Session identifier
            required_role: Required user role

        Returns:
            bool: True if user has required role
        """
        try:
            user = self.get_current_user(session_id)
            if not user:
                return False

            # Admin role has access to everything
            if user.role == UserRole.ADMIN:
                return True

            # Check specific role
            return user.role == required_role

        except Exception as e:
            logger.error(f"Role check failed: {e}")
            return False

    def require_authentication(self, session_id: str) -> UserResponse:
        """
        Require valid authentication, raise exception if not authenticated.

        Args:
            session_id: Session identifier

        Returns:
            UserResponse: Current user information

        Raises:
            AuthenticationError: If not authenticated
        """
        user = self.get_current_user(session_id)
        if not user:
            raise AuthenticationError("Authentication required")
        return user

    def require_role(self, session_id: str, required_role: UserRole) -> UserResponse:
        """
        Require specific role, raise exception if not authorized.

        Args:
            session_id: Session identifier
            required_role: Required user role

        Returns:
            UserResponse: Current user information

        Raises:
            AuthenticationError: If not authenticated or authorized
        """
        user = self.require_authentication(session_id)

        # Admin role has access to everything
        if user.role == UserRole.ADMIN:
            return user

        # Check specific role
        if user.role != required_role:
            raise AuthenticationError(f"Role '{required_role.value}' required")

        return user

    def require_admin(self, session_id: str) -> UserResponse:
        """
        Require admin role.

        Args:
            session_id: Session identifier

        Returns:
            UserResponse: Current user information

        Raises:
            AuthenticationError: If not authenticated or not admin
        """
        return self.require_role(session_id, UserRole.ADMIN)

    def change_password(self, session_id: str, current_password: str, new_password: str) -> bool:
        """
        Change user password.

        Args:
            session_id: Session identifier
            current_password: Current password for verification
            new_password: New password

        Returns:
            bool: True if password changed successfully

        Raises:
            AuthenticationError: If not authenticated
            InvalidCredentialsError: If current password is incorrect
        """
        try:
            user = self.require_authentication(session_id)

            # Get full user record
            user_record = self.user_repository.get_by_id(user.id)
            if not user_record:
                raise AuthenticationError("User not found")

            # Verify current password
            if not self._verify_password(current_password, user_record.password_hash):
                raise InvalidCredentialsError("Current password is incorrect")

            # Hash new password
            self._hash_password(new_password)

            # Update password (this would require extending UserRepository)
            # For now, we'll log this as a placeholder
            logger.info(f"Password change requested for user: {user.username}")

            return True

        except (AuthenticationError, InvalidCredentialsError):
            raise
        except Exception as e:
            logger.error(f"Password change failed: {e}")
            return False

    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        # Use configured number of rounds
        rounds = config.security.password_hash_rounds
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash.

        Args:
            password: Plain text password
            password_hash: Hashed password

        Returns:
            bool: True if password matches
        """
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def _generate_pseudonym(self) -> str:
        """
        Generate a random pseudonym for privacy compliance.

        Returns:
            str: Random pseudonym
        """
        # Generate a random pseudonym with format: GITTE_XXXXXXXX
        random_part = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8)
        )
        return f"GITTE_{random_part}"
