"""
Streamlit Session State Management
Provides safe initialization and access patterns for session state
"""

import logging
from typing import Any, Dict, Optional, TypeVar, Union
from uuid import UUID

import streamlit as st

logger = logging.getLogger(__name__)

T = TypeVar('T')

class SessionStateManager:
    """Manages Streamlit session state with safe initialization patterns"""
    
    # Default values for session state keys
    DEFAULTS = {
        'authenticated': False,
        'current_user_id': None,
        'user_role': None,
        'username': None,
        'onboarding_complete': False,
        'onboarding_step': 'consent',
        'current_time': None,
        'survey_data': {},
        'embodiment_characteristics': {},
        'generated_avatar': None,
        'show_consent_ui': False,
        'chat_messages': [],
        'pald_data': {},
        'error_state': None,
        'last_error': None,
        'prerequisite_check_results': None,
        'tooltip_interactions': {},
        'accessibility_mode': False,
        'high_contrast_mode': False,
    }
    
    @classmethod
    def initialize_session_state(cls) -> None:
        """Initialize all session state keys with safe defaults"""
        for key, default_value in cls.DEFAULTS.items():
            if key not in st.session_state:
                # Use copy for mutable defaults to prevent shared references
                if isinstance(default_value, (dict, list)):
                    st.session_state[key] = default_value.copy()
                else:
                    st.session_state[key] = default_value
    
    @classmethod
    def get(cls, key: str, default: T = None) -> Union[T, Any]:
        """Safely get session state value with fallback"""
        cls.initialize_session_state()
        return st.session_state.get(key, default)
    
    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Safely set session state value"""
        cls.initialize_session_state()
        st.session_state[key] = value
    
    @classmethod
    def update(cls, updates: Dict[str, Any]) -> None:
        """Update multiple session state values"""
        cls.initialize_session_state()
        for key, value in updates.items():
            st.session_state[key] = value
    
    @classmethod
    def clear_key(cls, key: str) -> None:
        """Clear a specific session state key"""
        if key in st.session_state:
            del st.session_state[key]
    
    @classmethod
    def reset_session(cls) -> None:
        """Reset session state to defaults (use with caution)"""
        for key in list(st.session_state.keys()):
            if key in cls.DEFAULTS:
                del st.session_state[key]
        cls.initialize_session_state()
    
    @classmethod
    def get_user_id(cls) -> Optional[UUID]:
        """Get current user ID as UUID"""
        user_id = cls.get('current_user_id')
        if user_id:
            try:
                return UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
            except (ValueError, TypeError):
                logger.warning(f"Invalid user_id in session state: {user_id}")
                return None
        return None
    
    @classmethod
    def set_user_id(cls, user_id: Union[str, UUID]) -> None:
        """Set current user ID"""
        if user_id:
            cls.set('current_user_id', str(user_id))
        else:
            cls.clear_key('current_user_id')
    
    @classmethod
    def is_authenticated(cls) -> bool:
        """Check if user is authenticated"""
        return bool(cls.get('authenticated', False)) and cls.get_user_id() is not None
    
    @classmethod
    def authenticate_user(cls, user_id: Union[str, UUID], username: str, role: str) -> None:
        """Authenticate user and set session state"""
        cls.update({
            'authenticated': True,
            'current_user_id': str(user_id),
            'username': username,
            'user_role': role,
        })
    
    @classmethod
    def logout_user(cls) -> None:
        """Logout user and clear authentication state"""
        cls.update({
            'authenticated': False,
            'current_user_id': None,
            'username': None,
            'user_role': None,
        })
    
    @classmethod
    def set_onboarding_step(cls, step: str) -> None:
        """Set current onboarding step"""
        cls.set('onboarding_step', step)
    
    @classmethod
    def complete_onboarding(cls) -> None:
        """Mark onboarding as complete"""
        cls.set('onboarding_complete', True)
    
    @classmethod
    def add_chat_message(cls, message: Dict[str, Any]) -> None:
        """Add message to chat history"""
        messages = cls.get('chat_messages', [])
        messages.append(message)
        cls.set('chat_messages', messages)
    
    @classmethod
    def clear_chat_messages(cls) -> None:
        """Clear chat message history"""
        cls.set('chat_messages', [])
    
    @classmethod
    def set_error_state(cls, error: str, details: Optional[str] = None) -> None:
        """Set error state for UI display"""
        cls.update({
            'error_state': error,
            'last_error': details or error,
        })
    
    @classmethod
    def clear_error_state(cls) -> None:
        """Clear error state"""
        cls.update({
            'error_state': None,
            'last_error': None,
        })
    
    @classmethod
    def get_debug_info(cls) -> Dict[str, Any]:
        """Get debug information about session state"""
        return {
            'authenticated': cls.get('authenticated'),
            'user_id': cls.get('current_user_id'),
            'username': cls.get('username'),
            'role': cls.get('user_role'),
            'onboarding_complete': cls.get('onboarding_complete'),
            'onboarding_step': cls.get('onboarding_step'),
            'error_state': cls.get('error_state'),
            'total_keys': len(st.session_state),
        }

# Convenience functions for backward compatibility
def initialize_session_state() -> None:
    """Initialize session state (backward compatibility)"""
    SessionStateManager.initialize_session_state()

def get_session_value(key: str, default: Any = None) -> Any:
    """Get session state value (backward compatibility)"""
    return SessionStateManager.get(key, default)

def set_session_value(key: str, value: Any) -> None:
    """Set session state value (backward compatibility)"""
    SessionStateManager.set(key, value)