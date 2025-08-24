"""
Property-based tests for session state management
Tests invariants and properties that should always hold
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from unittest.mock import patch, MagicMock
from uuid import UUID, uuid4

from src.ui.session_state_manager import SessionStateManager


class TestSessionStateProperties:
    """Property-based tests for session state invariants"""
    
    @given(st.text(min_size=1, max_size=50))
    def test_get_set_roundtrip_property(self, key):
        """Property: get(set(key, value)) == value for any valid key/value"""
        assume(key.isidentifier())  # Valid Python identifier
        
        with patch('streamlit.session_state', {}):
            test_values = [
                "string_value",
                42,
                True,
                None,
                {"dict": "value"},
                ["list", "value"]
            ]
            
            for value in test_values:
                SessionStateManager.set(key, value)
                retrieved = SessionStateManager.get(key)
                assert retrieved == value
    
    @given(st.text(min_size=1, max_size=50))
    def test_initialization_idempotent_property(self, key):
        """Property: initialize_session_state() is idempotent"""
        assume(key in SessionStateManager.DEFAULTS)
        
        with patch('streamlit.session_state', {}) as mock_state:
            # First initialization
            SessionStateManager.initialize_session_state()
            first_value = mock_state.get(key)
            
            # Second initialization should not change values
            SessionStateManager.initialize_session_state()
            second_value = mock_state.get(key)
            
            assert first_value == second_value
    
    @given(st.uuids())
    def test_user_id_conversion_property(self, user_uuid):
        """Property: UUID conversion is consistent and reversible"""
        with patch('streamlit.session_state', {}):
            # Test UUID input
            SessionStateManager.set_user_id(user_uuid)
            retrieved_uuid = SessionStateManager.get_user_id()
            assert retrieved_uuid == user_uuid
            assert isinstance(retrieved_uuid, UUID)
            
            # Test string input
            user_str = str(user_uuid)
            SessionStateManager.set_user_id(user_str)
            retrieved_from_str = SessionStateManager.get_user_id()
            assert retrieved_from_str == user_uuid
            assert isinstance(retrieved_from_str, UUID)
    
    @given(st.text(min_size=1, max_size=100), st.text(min_size=1, max_size=50))
    def test_authentication_state_consistency_property(self, username, role):
        """Property: Authentication state is consistent across operations"""
        assume(username.strip() and role.strip())
        
        with patch('streamlit.session_state', {}):
            user_id = uuid4()
            
            # Authenticate user
            SessionStateManager.authenticate_user(user_id, username, role)
            
            # Check all authentication state is consistent
            assert SessionStateManager.is_authenticated() is True
            assert SessionStateManager.get_user_id() == user_id
            assert SessionStateManager.get('username') == username
            assert SessionStateManager.get('user_role') == role
            assert SessionStateManager.get('authenticated') is True
            
            # Logout should clear all authentication state
            SessionStateManager.logout_user()
            
            assert SessionStateManager.is_authenticated() is False
            assert SessionStateManager.get_user_id() is None
            assert SessionStateManager.get('authenticated') is False
    
    @given(st.lists(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.text(), st.integers(), st.booleans()),
        min_size=1, max_size=5
    ), min_size=0, max_size=10))
    def test_chat_message_ordering_property(self, messages):
        """Property: Chat messages maintain insertion order"""
        with patch('streamlit.session_state', {}):
            SessionStateManager.initialize_session_state()
            
            # Add messages in order
            for message in messages:
                SessionStateManager.add_chat_message(message)
            
            # Retrieve messages
            retrieved_messages = SessionStateManager.get('chat_messages', [])
            
            # Should maintain order
            assert len(retrieved_messages) == len(messages)
            for i, original_msg in enumerate(messages):
                assert retrieved_messages[i] == original_msg
    
    @given(st.text(min_size=1, max_size=100))
    def test_error_state_isolation_property(self, error_message):
        """Property: Error state operations don't affect other state"""
        with patch('streamlit.session_state', {}):
            SessionStateManager.initialize_session_state()
            
            # Set some initial state
            initial_user_id = uuid4()
            SessionStateManager.set_user_id(initial_user_id)
            SessionStateManager.set('onboarding_complete', True)
            
            # Set error state
            SessionStateManager.set_error_state(error_message)
            
            # Other state should be unchanged
            assert SessionStateManager.get_user_id() == initial_user_id
            assert SessionStateManager.get('onboarding_complete') is True
            assert SessionStateManager.get('error_state') == error_message
            
            # Clear error state
            SessionStateManager.clear_error_state()
            
            # Other state should still be unchanged
            assert SessionStateManager.get_user_id() == initial_user_id
            assert SessionStateManager.get('onboarding_complete') is True
            assert SessionStateManager.get('error_state') is None
    
    @given(st.dictionaries(
        keys=st.sampled_from(list(SessionStateManager.DEFAULTS.keys())),
        values=st.one_of(st.text(), st.integers(), st.booleans(), st.none()),
        min_size=1, max_size=5
    ))
    def test_bulk_update_atomicity_property(self, updates):
        """Property: Bulk updates are atomic (all or nothing)"""
        with patch('streamlit.session_state', {}) as mock_state:
            SessionStateManager.initialize_session_state()
            
            # Store initial state
            initial_state = dict(mock_state)
            
            # Perform bulk update
            SessionStateManager.update(updates)
            
            # All updates should be applied
            for key, value in updates.items():
                assert SessionStateManager.get(key) == value
            
            # Non-updated keys should retain initial values
            for key, initial_value in initial_state.items():
                if key not in updates:
                    assert SessionStateManager.get(key) == initial_value
    
    @given(st.text(min_size=1, max_size=50))
    def test_default_value_consistency_property(self, key):
        """Property: Default values are consistent with DEFAULTS definition"""
        assume(key in SessionStateManager.DEFAULTS)
        
        with patch('streamlit.session_state', {}):
            # Get value before initialization
            value_before = SessionStateManager.get(key)
            
            # Initialize
            SessionStateManager.initialize_session_state()
            
            # Get value after initialization
            value_after = SessionStateManager.get(key)
            
            # Should match DEFAULTS
            expected_default = SessionStateManager.DEFAULTS[key]
            
            # Before initialization, should get None or provided default
            # After initialization, should get the defined default
            assert value_after == expected_default
    
    @settings(max_examples=50)
    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10))
    def test_onboarding_step_progression_property(self, steps):
        """Property: Onboarding step changes are tracked correctly"""
        with patch('streamlit.session_state', {}):
            SessionStateManager.initialize_session_state()
            
            # Initial step should be default
            initial_step = SessionStateManager.get('onboarding_step')
            assert initial_step == SessionStateManager.DEFAULTS['onboarding_step']
            
            # Set each step and verify
            for step in steps:
                SessionStateManager.set_onboarding_step(step)
                current_step = SessionStateManager.get('onboarding_step')
                assert current_step == step
            
            # Complete onboarding
            SessionStateManager.complete_onboarding()
            assert SessionStateManager.get('onboarding_complete') is True
    
    def test_mutable_default_isolation_property(self):
        """Property: Mutable defaults don't share references between sessions"""
        with patch('streamlit.session_state', {}) as mock_state1:
            SessionStateManager.initialize_session_state()
            
            # Modify a mutable default
            messages1 = SessionStateManager.get('chat_messages')
            messages1.append({"test": "message1"})
            
        with patch('streamlit.session_state', {}) as mock_state2:
            SessionStateManager.initialize_session_state()
            
            # Should get fresh copy, not modified version
            messages2 = SessionStateManager.get('chat_messages')
            assert len(messages2) == 0  # Should be empty list
            assert messages1 is not messages2  # Should be different objects
    
    @given(st.text(min_size=1, max_size=100))
    def test_debug_info_completeness_property(self, username):
        """Property: Debug info contains all expected fields"""
        with patch('streamlit.session_state', {}):
            SessionStateManager.initialize_session_state()
            
            # Set some state
            user_id = uuid4()
            SessionStateManager.authenticate_user(user_id, username, "participant")
            
            # Get debug info
            debug_info = SessionStateManager.get_debug_info()
            
            # Should contain all expected fields
            expected_fields = [
                'authenticated', 'user_id', 'username', 'role',
                'onboarding_complete', 'onboarding_step', 
                'error_state', 'total_keys'
            ]
            
            for field in expected_fields:
                assert field in debug_info
            
            # Values should match current state
            assert debug_info['authenticated'] is True
            assert debug_info['user_id'] == str(user_id)
            assert debug_info['username'] == username
            assert debug_info['role'] == "participant"