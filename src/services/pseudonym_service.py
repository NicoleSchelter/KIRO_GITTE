"""
Pseudonym service for GITTE study participation system.
Provides service layer abstraction for pseudonym management operations.
"""

import logging
from uuid import UUID

from src.data.database import get_session
from src.data.repositories import PseudonymRepository
from src.data.schemas import PseudonymResponse, PseudonymValidation
from src.logic.pseudonym_logic import PseudonymLogic, PseudonymError, InvalidPseudonymFormatError, PseudonymNotUniqueError

logger = logging.getLogger(__name__)


class PseudonymService:
    """
    Service layer for pseudonym management.
    Handles database sessions and provides high-level pseudonym operations.
    """

    def __init__(self):
        self.pseudonym_logic = None  # Will be initialized per request

    def _get_pseudonym_logic(self) -> PseudonymLogic:
        """Get pseudonym logic with database session."""
        if not hasattr(self, "_session") or not self._session:
            raise RuntimeError("Service not properly initialized with session")

        if not self.pseudonym_logic:
            pseudonym_repository = PseudonymRepository(self._session)
            self.pseudonym_logic = PseudonymLogic(pseudonym_repository)

        return self.pseudonym_logic

    def create_pseudonym(self, user_id: UUID, pseudonym_text: str, created_by: str = "system") -> PseudonymResponse:
        """
        Create a new pseudonym for a user.
        
        Args:
            user_id: The user ID
            pseudonym_text: The pseudonym text
            
        Returns:
            PseudonymResponse: The created pseudonym
            
        Raises:
            InvalidPseudonymFormatError: If pseudonym format is invalid
            PseudonymNotUniqueError: If pseudonym is not unique
            PseudonymError: If creation fails
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_pseudonym_logic()
                result = logic.create_pseudonym(user_id, pseudonym_text, created_by)
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise
            finally:
                self._session = None
                self.pseudonym_logic = None

    def validate_pseudonym(self, pseudonym_text: str) -> PseudonymValidation:
        """
        Validate pseudonym format and uniqueness.
        
        Args:
            pseudonym_text: The pseudonym text to validate
            
        Returns:
            PseudonymValidation: Validation result
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_pseudonym_logic()
                return logic.validate_pseudonym_format(pseudonym_text)
            finally:
                self._session = None
                self.pseudonym_logic = None

    def get_user_pseudonym(self, user_id: UUID) -> PseudonymResponse | None:
        """
        Get the active pseudonym for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            PseudonymResponse | None: The user's active pseudonym or None
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_pseudonym_logic()
                return logic.get_user_pseudonym(user_id)
            finally:
                self._session = None
                self.pseudonym_logic = None

    def deactivate_user_pseudonym(self, user_id: UUID) -> bool:
        """
        Deactivate a user's pseudonym (for data deletion requests).
        
        Args:
            user_id: The user ID
            
        Returns:
            bool: True if deactivated successfully, False otherwise
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_pseudonym_logic()
                result = logic.deactivate_pseudonym(user_id)
                if result:
                    session.commit()
                return result
            except Exception:
                session.rollback()
                raise
            finally:
                self._session = None
                self.pseudonym_logic = None

    def verify_pseudonym_ownership(self, user_id: UUID, pseudonym_text: str) -> bool:
        """
        Verify that a pseudonym belongs to a specific user.
        
        Args:
            user_id: The user ID
            pseudonym_text: The pseudonym text to verify
            
        Returns:
            bool: True if the pseudonym belongs to the user, False otherwise
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_pseudonym_logic()
                return logic.verify_pseudonym_ownership(user_id, pseudonym_text)
            finally:
                self._session = None
                self.pseudonym_logic = None

    def has_user_pseudonym(self, user_id: UUID) -> bool:
        """
        Check if a user has an active pseudonym.
        
        Args:
            user_id: The user ID
            
        Returns:
            bool: True if user has an active pseudonym, False otherwise
        """
        pseudonym = self.get_user_pseudonym(user_id)
        return pseudonym is not None