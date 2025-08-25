"""
Pseudonym logic for GITTE study participation system.
Handles pseudonym creation, validation, and hash generation for research data anonymization.
"""

import hashlib
import logging
import re
from typing import Any
from uuid import UUID

from src.data.models import Pseudonym
from src.data.repositories import PseudonymRepository
from src.data.schemas import PseudonymCreate, PseudonymResponse, PseudonymValidation
from src.utils.study_error_handler import (
    ErrorContext,
    StudyErrorCategory,
    StudyErrorHandler,
    StudyRetryConfig,
    with_study_error_handling
)

logger = logging.getLogger(__name__)


class PseudonymError(Exception):
    """Base exception for pseudonym errors."""

    pass


class InvalidPseudonymFormatError(PseudonymError):
    """Raised when pseudonym format is invalid."""

    pass


class PseudonymNotUniqueError(PseudonymError):
    """Raised when pseudonym is not unique."""

    pass


class PseudonymLogic:
    """Pseudonym business logic with comprehensive error handling."""

    def __init__(self, pseudonym_repository: PseudonymRepository):
        self.pseudonym_repository = pseudonym_repository
        self.error_handler = StudyErrorHandler()
        self.retry_config = StudyRetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )

    def validate_pseudonym_format(self, pseudonym_text: str) -> PseudonymValidation:
        """
        Validate pseudonym format according to requirements.
        
        Expected format: [FirstLetter][BirthMonth][LastLetter][BirthYear][ParentLetters][CustomPart]
        Example: M03s2001AJ13
        
        Args:
            pseudonym_text: The pseudonym text to validate
            
        Returns:
            PseudonymValidation: Validation result with details
        """
        try:
            # Basic length check (minimum 8 characters for basic format)
            if len(pseudonym_text) < 8:
                return PseudonymValidation(
                    is_valid=False,
                    is_unique=False,
                    error_message="Pseudonym must be at least 8 characters long"
                )

            # Check for basic pattern: Letter + 2digits + letter + 4digits + 2letters + custom
            # This is a flexible validation that allows for the described format
            pattern = r'^[A-Z]\d{2}[a-z]\d{4}[A-Z]{2}.+$'
            
            if not re.match(pattern, pseudonym_text):
                return PseudonymValidation(
                    is_valid=False,
                    is_unique=False,
                    error_message="Pseudonym format invalid. Expected: [FirstLetter][Month][LastLetter][Year][ParentLetters][Custom]"
                )

            # Check uniqueness
            is_unique = self.pseudonym_repository.is_pseudonym_unique(pseudonym_text)
            
            return PseudonymValidation(
                is_valid=True,
                is_unique=is_unique,
                error_message=None if is_unique else "Pseudonym already exists"
            )

        except Exception as e:
            logger.error(f"Error validating pseudonym format: {e}")
            return PseudonymValidation(
                is_valid=False,
                is_unique=False,
                error_message="Validation error occurred"
            )

    def generate_pseudonym_hash(self, pseudonym_text: str, user_id: UUID) -> str:
        """
        Generate a secure hash for the pseudonym.
        
        Args:
            pseudonym_text: The pseudonym text
            user_id: The user ID for additional entropy
            
        Returns:
            str: SHA-256 hash of the pseudonym with salt
        """
        try:
            # Use user_id as salt for additional security
            salt = str(user_id)
            combined = f"{pseudonym_text}:{salt}"
            
            # Generate SHA-256 hash
            hash_object = hashlib.sha256(combined.encode('utf-8'))
            return hash_object.hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating pseudonym hash: {e}")
            raise PseudonymError(f"Failed to generate pseudonym hash: {e}")

    def create_pseudonym_with_consents(
        self, 
        user_id: UUID, 
        pseudonym_text: str, 
        staged_consents: list[dict[str, Any]], 
        created_by: str = "system",
        max_retries: int = 3
    ) -> dict[str, Any]:
        """
        Create pseudonym and persist staged consents in a single transaction (Flow B).
        
        Args:
            user_id: The user ID
            pseudonym_text: The pseudonym text
            staged_consents: List of staged consent dictionaries
            created_by: Who created the pseudonym (for audit)
            max_retries: Maximum retry attempts
            
        Returns:
            Dict containing creation results
            
        Raises:
            InvalidPseudonymFormatError: If pseudonym format is invalid
            PseudonymNotUniqueError: If pseudonym is not unique
            PseudonymError: If creation fails
        """
        for attempt in range(max_retries):
            try:
                from src.data.database_factory import database_transaction
                
                # Use fresh session for each attempt
                with database_transaction() as session:
                    # Create repositories with the session
                    from src.data.repositories import PseudonymRepository, StudyConsentRepository
                    pseudonym_repo = PseudonymRepository(session)
                    consent_repo = StudyConsentRepository(session)
                    
                    # Note: No longer checking for existing user pseudonyms since we removed user-pseudonym connections

                    # Validate pseudonym format and uniqueness
                    validation = self.validate_pseudonym_format(pseudonym_text)
                    
                    if not validation.is_valid:
                        raise InvalidPseudonymFormatError(validation.error_message or "Invalid format")
                    
                    # Check if pseudonym text already exists
                    existing_by_text = pseudonym_repo.get_by_text(pseudonym_text)
                    if existing_by_text:
                        # Handle collision by incrementing the last number in the pseudonym
                        pseudonym_text = self._handle_pseudonym_collision(pseudonym_text, pseudonym_repo)
                        logger.info(f"Pseudonym collision detected, using: {pseudonym_text}")

                    # Generate hash with retry logic
                    pseudonym_hash = self._generate_hash_with_retry(pseudonym_text, user_id)

                    # Create pseudonym without mapping (no user connection)
                    pseudonym_data = PseudonymCreate(pseudonym_text=pseudonym_text)
                    
                    pseudonym = pseudonym_repo.create_pseudonym_standalone(
                        pseudonym_data, pseudonym_hash, created_by
                    )
                    
                    if not pseudonym:
                        raise PseudonymError("Failed to create pseudonym in database")

                    logger.info(f"pseudonym_logic: created standalone pseudonym {pseudonym.pseudonym_id}")

                    # Persist all staged consents with the new pseudonym_id
                    consent_records = []
                    for staged_consent in staged_consents:
                        record = consent_repo.create_consent(
                            pseudonym_id=pseudonym.pseudonym_id,
                            consent_type=staged_consent["consent_type"],
                            granted=staged_consent["granted"],
                            version=staged_consent["version"],
                            metadata=staged_consent.get("metadata", {})
                        )
                        consent_records.append(record)
                    
                    # Transaction commits automatically on successful exit
                    logger.info(f"pseudonym_logic: persisted {len(consent_records)} consents for pseudonym {pseudonym.pseudonym_id}")
                    
                    return {
                        "success": True,
                        "pseudonym_created": True,
                        "pseudonym": pseudonym,
                        "consent_records": consent_records,
                        "attempt": attempt + 1
                    }
                    
            except (InvalidPseudonymFormatError, PseudonymNotUniqueError):
                # Don't retry validation errors
                raise
            except Exception as e:
                logger.error(f"pseudonym_logic: rolling back and opening fresh session for retry (attempt {attempt + 1}): {e}")
                
                if attempt == max_retries - 1:
                    logger.error(f"Failed to create pseudonym with consents after {max_retries} attempts: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "pseudonym_created": False,
                        "pseudonym": None,
                        "consent_records": [],
                        "attempt": attempt + 1
                    }
                # Continue to next attempt with fresh session
                continue
        
        # Should not reach here
        return {
            "success": False,
            "error": "Unexpected retry loop exit",
            "pseudonym_created": False,
            "pseudonym": None,
            "consent_records": [],
            "attempt": max_retries
        }

    def create_pseudonym(self, user_id: UUID, pseudonym_text: str, created_by: str = "system") -> PseudonymResponse:
        """
        Create a new pseudonym for a user with comprehensive error handling.
        This is the legacy method, kept for backward compatibility.
        
        Args:
            user_id: The user ID
            pseudonym_text: The pseudonym text
            created_by: Who created the pseudonym (for audit)
            
        Returns:
            PseudonymResponse: The created pseudonym
            
        Raises:
            InvalidPseudonymFormatError: If pseudonym format is invalid
            PseudonymNotUniqueError: If pseudonym is not unique
            PseudonymError: If creation fails
        """
        context = ErrorContext(
            user_id=user_id,
            operation="create_pseudonym",
            component="pseudonym_logic",
            metadata={"pseudonym_length": len(pseudonym_text), "created_by": created_by}
        )
        
        with self.error_handler.error_boundary(StudyErrorCategory.PSEUDONYM_CREATION, context, self.retry_config):
            try:
                # No longer checking for existing user pseudonyms since we removed user-pseudonym connections
                
                # Validate pseudonym format
                validation = self.validate_pseudonym_format(pseudonym_text)
                
                if not validation.is_valid:
                    raise InvalidPseudonymFormatError(validation.error_message or "Invalid format")
                
                # Handle pseudonym collisions by incrementing the number
                existing_by_text = self.pseudonym_repository.get_by_text(pseudonym_text)
                if existing_by_text:
                    pseudonym_text = self._handle_pseudonym_collision(pseudonym_text, self.pseudonym_repository)
                    logger.info(f"Pseudonym collision handled, using: {pseudonym_text}")

                # Generate hash with retry logic
                pseudonym_hash = self._generate_hash_with_retry(pseudonym_text, user_id)

                # Create standalone pseudonym (no user mapping)
                pseudonym_data = PseudonymCreate(
                    pseudonym_text=pseudonym_text
                )
                
                pseudonym = self.pseudonym_repository.create_pseudonym_standalone(
                    pseudonym_data, pseudonym_hash, created_by
                )
                
                if not pseudonym:
                    raise PseudonymError("Failed to create pseudonym in database")

                logger.info(f"Successfully created pseudonym for user {user_id}")
                return PseudonymResponse(
                    pseudonym_id=pseudonym.pseudonym_id,
                    pseudonym_text=pseudonym.pseudonym_text,
                    pseudonym_hash=pseudonym.pseudonym_hash,
                    created_at=pseudonym.created_at,
                    is_active=pseudonym.is_active
                )

            except (InvalidPseudonymFormatError, PseudonymNotUniqueError):
                raise
            except Exception as e:
                logger.error(f"Error creating pseudonym: {e}")
                raise PseudonymError(f"Failed to create pseudonym: {e}")

    def _handle_pseudonym_collision(self, original_pseudonym: str, pseudonym_repo) -> str:
        """
        Handle pseudonym collision by incrementing the last number.
        
        Args:
            original_pseudonym: The original pseudonym text
            pseudonym_repo: Pseudonym repository for checking existence
            
        Returns:
            str: Modified pseudonym that doesn't exist
        """
        import re
        
        # Extract the last number from the pseudonym
        # Pattern: Find the last sequence of digits at the very end of the string
        match = re.search(r'(\d+)$', original_pseudonym)
        
        if match:
            # Found a number at the end or near end
            last_number = int(match.group(1))
            start_pos = match.start(1)
            end_pos = match.end(1)
            
            # Try incrementing the number until we find a unique pseudonym
            attempt = 0
            max_attempts = 100  # Prevent infinite loop
            
            while attempt < max_attempts:
                new_number = last_number + attempt + 1
                new_pseudonym = original_pseudonym[:start_pos] + str(new_number) + original_pseudonym[end_pos:]
                
                # Check if this new pseudonym exists
                if not pseudonym_repo.get_by_text(new_pseudonym):
                    return new_pseudonym
                
                attempt += 1
            
            # If we can't find a unique number, append a number
            return original_pseudonym + "1"
        else:
            # No number found, append "1" to the end
            attempt = 1
            while attempt <= 100:
                new_pseudonym = original_pseudonym + str(attempt)
                if not pseudonym_repo.get_by_text(new_pseudonym):
                    return new_pseudonym
                attempt += 1
            
            # Fallback - should never reach here
            return original_pseudonym + "999"
    
    def _generate_hash_with_retry(self, pseudonym_text: str, user_id: UUID, max_retries: int = 3) -> str:
        """Generate pseudonym hash with retry logic for robustness."""
        
        for attempt in range(max_retries):
            try:
                return self.generate_pseudonym_hash(pseudonym_text, user_id)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to generate hash after {max_retries} attempts: {e}")
                    raise PseudonymError(f"Hash generation failed after {max_retries} attempts")
                else:
                    logger.warning(f"Hash generation attempt {attempt + 1} failed, retrying: {e}")
                    continue

    def get_user_pseudonym(self, user_id: UUID) -> PseudonymResponse | None:
        """
        Get the active pseudonym for a user.
        
        Note: Since user-pseudonym connections have been removed for privacy,
        this method now returns None. Users must remember their pseudonyms.
        
        Args:
            user_id: The user ID
            
        Returns:
            PseudonymResponse | None: Always returns None (no user-pseudonym connection)
        """
        logger.info(f"get_user_pseudonym called for user {user_id} - returning None (no user-pseudonym connection)")
        return None

    def deactivate_pseudonym(self, user_id: UUID) -> bool:
        """
        Deactivate a user's pseudonym (for data deletion requests).
        
        Args:
            user_id: The user ID
            
        Returns:
            bool: True if deactivated successfully, False otherwise
        """
        try:
            return self.pseudonym_repository.deactivate_user_pseudonym(user_id)

        except Exception as e:
            logger.error(f"Error deactivating pseudonym for user {user_id}: {e}")
            return False

    def verify_pseudonym_ownership(self, user_id: UUID, pseudonym_text: str) -> bool:
        """
        Verify that a pseudonym belongs to a specific user.
        
        Args:
            user_id: The user ID
            pseudonym_text: The pseudonym text to verify
            
        Returns:
            bool: True if the pseudonym belongs to the user, False otherwise
        """
        try:
            user_pseudonym = self.pseudonym_repository.get_by_user_id(user_id)
            
            if not user_pseudonym:
                return False

            return user_pseudonym.pseudonym_text == pseudonym_text

        except Exception as e:
            logger.error(f"Error verifying pseudonym ownership: {e}")
            return False