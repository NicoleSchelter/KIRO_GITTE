"""
User Preferences Service
Service for managing user preference data separate from PALD.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UserPreferencesService:
    """Service for managing user preference data."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def save_preferences(
        self, 
        user_id: UUID, 
        preferences: dict[str, Any],
        category: str = "general"
    ) -> 'UserPreferences':
        """Save user preference data."""
        try:
            # Import here to avoid circular imports
            from src.data.models import UserPreferences
            
            # Check if preferences exist for this category
            existing = self.db_session.query(UserPreferences).filter(
                UserPreferences.user_id == user_id,
                UserPreferences.category == category
            ).first()
            
            if existing:
                # Update existing preferences
                existing.preferences = preferences
                existing.updated_at = datetime.utcnow()
                result = existing
            else:
                # Create new preferences
                result = UserPreferences(
                    user_id=user_id,
                    preferences=preferences,
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
    
    def get_user_preferences(self, user_id: UUID, category: str | None = None) -> list['UserPreferences']:
        """Retrieve user's preferences."""
        try:
            from src.data.models import UserPreferences
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
    ) -> 'UserPreferences':
        """Update user preferences."""
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