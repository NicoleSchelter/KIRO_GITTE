"""
User Preferences Service
Service for managing user preference data separate from PALD.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.utils.jsonify import to_jsonable
from src.data.models import UserPreferences

logger = logging.getLogger(__name__)


class UserPreferencesService:
    """Service for managing user preference data."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def upsert_preferences(
        self, 
        user_id: UUID, 
        category: str,
        prefs: dict[str, Any]
    ) -> bool:
        """
        Upsert user preferences with centralized JSON serialization.
        
        Args:
            user_id: User identifier
            category: Preference category
            prefs: Preferences data (will be JSON-serialized)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from src.data.models import User
            
            # Clean and serialize preferences - remove any updated_at from JSON payload
            clean_prefs = {k: v for k, v in prefs.items() if k != 'updated_at'}
            serialized_prefs = to_jsonable(clean_prefs)
            
            # Begin transaction
            with self.db_session.begin():
                # Verify user exists
                user = self.db_session.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.error(f"User {user_id} not found in database")
                    return False
                
                # Check if preferences exist for this category (upsert logic)
                existing = self.db_session.query(UserPreferences).filter(
                    UserPreferences.user_id == user_id,
                    UserPreferences.category == category
                ).first()
                
                if existing:
                    # Update existing preferences
                    existing.preferences = serialized_prefs
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new preferences
                    new_prefs = UserPreferences(
                        user_id=user_id,
                        preferences=serialized_prefs,
                        category=category
                    )
                    self.db_session.add(new_prefs)
                
                # Flush to ensure changes are written
                self.db_session.flush()
                
                logger.info(f"Upserted preferences for user {user_id}, category: {category}")
                return True
                
        except Exception as e:
            logger.exception(f"Failed to upsert preferences for user {user_id}, category {category}: {e}")
            return False

    def save_preferences(
        self, 
        user_id: UUID, 
        preferences: dict[str, Any],
        category: str = "general"
    ) -> UserPreferences:
        """Save user preference data. DEPRECATED: Use upsert_preferences instead."""
        try:
            # Apply JSON serialization centrally
            clean_prefs = {k: v for k, v in preferences.items() if k != 'updated_at'}
            serialized_prefs = to_jsonable(clean_prefs)
            
            # Check if preferences exist for this category
            existing = self.db_session.query(UserPreferences).filter(
                UserPreferences.user_id == user_id,
                UserPreferences.category == category
            ).first()
            
            if existing:
                # Update existing preferences
                existing.preferences = serialized_prefs
                existing.updated_at = datetime.utcnow()
                result = existing
            else:
                # Create new preferences
                result = UserPreferences(
                    user_id=user_id,
                    preferences=serialized_prefs,
                    category=category
                )
                self.db_session.add(result)
            
            self.db_session.commit()
            logger.info(f"Saved preferences for user {user_id}, category: {category}")
            return result
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving preferences for user {user_id}: {e}")
            raise
    
    def get_user_preferences(self, user_id: UUID, category: str | None = None) -> list[UserPreferences]:
        """Retrieve user's preferences."""
        try:
            query = self.db_session.query(UserPreferences).filter(
                UserPreferences.user_id == user_id
            )
            
            if category:
                query = query.filter(UserPreferences.category == category)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error retrieving preferences for user {user_id}: {e}")
            return []
    
    def update_preferences(
        self, 
        user_id: UUID, 
        updates: dict[str, Any],
        category: str = "general"
    ) -> UserPreferences:
        """Update user preferences. DEPRECATED: Use upsert_preferences instead."""
        existing_prefs = self.get_user_preferences(user_id, category)
        
        if existing_prefs:
            # Merge with existing preferences
            current_data = existing_prefs[0].preferences
            updated_data = {**current_data, **updates}
        else:
            updated_data = updates
        
        return self.save_preferences(
            user_id=user_id,
            preferences=updated_data,
            category=category
        )