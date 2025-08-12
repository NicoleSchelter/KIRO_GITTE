"""
Session management service for GITTE system.
Handles user session creation, validation, and cleanup.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from config.config import config

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session management service.

    In a production system, this would typically use Redis or another
    persistent session store. For development, we use in-memory storage.
    """

    def __init__(self):
        # In-memory session storage (use Redis in production)
        self._sessions: dict[str, dict[str, Any]] = {}
        self._session_timeout = timedelta(hours=config.security.session_timeout_hours)

    def create_session(self, user_id: UUID, user_role: str) -> dict[str, Any]:
        """
        Create a new user session.

        Args:
            user_id: User identifier
            user_role: User role

        Returns:
            Dict containing session data
        """
        try:
            # Generate secure session ID
            session_id = self._generate_session_id()

            # Create session data
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "user_role": user_role,
                "created_at": datetime.utcnow(),
                "last_accessed": datetime.utcnow(),
                "expires_at": datetime.utcnow() + self._session_timeout,
            }

            # Store session
            self._sessions[session_id] = session_data

            # Clean up expired sessions
            self._cleanup_expired_sessions()

            logger.info(f"Session created for user {user_id}: {session_id}")

            return session_data

        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Get session data by session ID.

        Args:
            session_id: Session identifier

        Returns:
            Dict containing session data or None if invalid/expired
        """
        try:
            session_data = self._sessions.get(session_id)
            if not session_data:
                return None

            # Check if session is expired
            if datetime.utcnow() > session_data["expires_at"]:
                self.invalidate_session(session_id)
                return None

            # Update last accessed time
            session_data["last_accessed"] = datetime.utcnow()

            return session_data

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session.

        Args:
            session_id: Session identifier

        Returns:
            bool: True if session was invalidated
        """
        try:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Session invalidated: {session_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to invalidate session {session_id}: {e}")
            return False

    def refresh_session(self, session_id: str) -> bool:
        """
        Refresh session expiration time.

        Args:
            session_id: Session identifier

        Returns:
            bool: True if session was refreshed
        """
        try:
            session_data = self._sessions.get(session_id)
            if not session_data:
                return False

            # Update expiration time
            session_data["expires_at"] = datetime.utcnow() + self._session_timeout
            session_data["last_accessed"] = datetime.utcnow()

            logger.debug(f"Session refreshed: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh session {session_id}: {e}")
            return False

    def invalidate_user_sessions(self, user_id: UUID) -> int:
        """
        Invalidate all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            int: Number of sessions invalidated
        """
        try:
            sessions_to_remove = []

            for session_id, session_data in self._sessions.items():
                if session_data["user_id"] == user_id:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                del self._sessions[session_id]

            logger.info(f"Invalidated {len(sessions_to_remove)} sessions for user {user_id}")
            return len(sessions_to_remove)

        except Exception as e:
            logger.error(f"Failed to invalidate sessions for user {user_id}: {e}")
            return 0

    def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions.

        Returns:
            int: Number of active sessions
        """
        try:
            self._cleanup_expired_sessions()
            return len(self._sessions)

        except Exception as e:
            logger.error(f"Failed to get active sessions count: {e}")
            return 0

    def get_user_sessions(self, user_id: UUID) -> list:
        """
        Get all active sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of session data for the user
        """
        try:
            user_sessions = []

            for session_data in self._sessions.values():
                if session_data["user_id"] == user_id:
                    # Check if session is still valid
                    if datetime.utcnow() <= session_data["expires_at"]:
                        user_sessions.append(session_data)

            return user_sessions

        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []

    def _generate_session_id(self) -> str:
        """
        Generate a secure session ID.

        Returns:
            str: Secure session identifier
        """
        # Generate a cryptographically secure random session ID
        return secrets.token_urlsafe(32)

    def _cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            current_time = datetime.utcnow()
            expired_sessions = []

            for session_id, session_data in self._sessions.items():
                if current_time > session_data["expires_at"]:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self._sessions[session_id]

            if expired_sessions:
                logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")

            return len(expired_sessions)

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0

    def cleanup_all_sessions(self) -> int:
        """
        Clean up all sessions (for testing or maintenance).

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            session_count = len(self._sessions)
            self._sessions.clear()
            logger.info(f"Cleaned up all {session_count} sessions")
            return session_count

        except Exception as e:
            logger.error(f"Failed to cleanup all sessions: {e}")
            return 0


# Global session manager instance
session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    return session_manager
