"""
Unit tests for prerequisite workflow integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

import streamlit as st

from src.ui.prerequisite_integration import (
    PrerequisiteWorkflowIntegration,
    get_prerequisite_integration,
    prerequisite_check,
    with_prerequisites,
    PrerequisiteContext,
    prerequisite_context,
    integrate_registration_prerequisites,
    integrate_chat_prerequisites,
    integrate_image_generation_prerequisites,
    integrate_system_startup_prerequisites
)
from src.logic.prerequisite_validation import PrerequisiteValidationLogic
from src.ui.prerequisite_checklist_ui import PrerequisiteChecklistUI


class TestPrerequisiteWorkflowIntegration:
    """Test cases for PrerequisiteWorkflowIntegration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_validation_logic = Mock(spec=PrerequisiteValidationLogic)
        self.mock_consent_service = Mock()
        self.user_id = uuid4()
        
        # Clear Streamlit session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
    
    def test_initialization(self):
        """Test integration initialization."""
        integration = PrerequisiteWorkflowIntegration(
            validation_logic=self.mock_validation_logic,
            consent_service=self.mock_consent_service
        )
        
        assert integration.validation_logic == self.mock_validation_logic
        assert integration.consent_service == self.mock_consent_service
        assert isinstance(integration.checklist_ui, PrerequisiteChecklistUI)
        
        # Check session state initialization
        assert 'prerequisite_status' in st.session_state
        assert 'prerequisite_warnings_shown' in st.session_state
    
    def test_check_prerequisites_for_operation_ready(self):
        """Test prerequisite check when operation is ready."""
        readiness = {
            "ready": True,
            "can_proceed_with_warnings": True,
            "required_failures": [],
            "recommended_failures": []
        }
        
        self.mock_validation_logic.check_operation_readiness.return_value = readiness
        
        integration = PrerequisiteWorkflowIntegration(
            validation_logic=self.mock_validation_logic
        )
        
        result = integration.check_prerequisites_for_operation("test_operation", self.user_id)
        
        assert result["blocked"] is False
        assert result["readiness"] == readiness
        
        # Check caching
        cache_key = f"test_operation_{self.user_id}"
        assert st.session_state.prerequisite_status[cache_key] == readiness
    
    def test_check_prerequisites_for_operation_not_ready(self):
        """Test prerequisite check when operation is not ready."""
        readiness = {
            "ready": False,
            "can_proceed_with_warnings": False,
            "required_failures": ["Database", "Ollama"],
            "recommended_failures": []
        }
        
        self.mock_validation_logic.check_operation_readiness.return_value = readiness
        
        integration = PrerequisiteWorkflowIntegration(
            validation_logic=self.mock_validation_logic
        )
        
        with patch.object(integration, '_render_blocking_prerequisites_ui') as mock_render:
            result = integration.check_prerequisites_for_operation("test_operation", self.user_id)
        
        assert result["blocked"] is True
        assert result["readiness"] == readiness
        mock_render.assert_called_once()
    
    def test_check_prerequisites_for_operation_with_warnings(self):
        """Test prerequisite check with warnings."""
        readiness = {
            "ready": True,
            "can_proceed_with_warnings": False,
            "required_failures": [],
            "recommended_failures": ["System Health"]
        }
        
        self.mock_validation_logic.check_operation_readiness.return_value = readiness
        
        integration = PrerequisiteWorkflowIntegration(
            validation_logic=self.mock_validation_logic
        )
        
        with patch.object(integration, '_render_prerequisite_warnings') as mock_render:
            result = integration.check_prerequisites_for_operation("test_operation", self.user_id)
        
        assert result["blocked"] is False
        mock_render.assert_called_once()
    
    def test_check_prerequisites_for_operation_error(self):
        """Test prerequisite check with error."""
        self.mock_validation_logic.check_operation_readiness.side_effect = Exception("Test error")
        
        integration = PrerequisiteWorkflowIntegration(
            validation_logic=self.mock_validation_logic
        )
        
        with patch('streamlit.error') as mock_error:
            result = integration.check_prerequisites_for_operation("test_operation", self.user_id)
        
        assert result["blocked"] is True
        assert "error" in result
        mock_error.assert_called_once()
    
    @patch('streamlit.sidebar')
    @patch('streamlit.write')
    @patch('streamlit.markdown')
    def test_add_prerequisite_sidebar_status(self, mock_markdown, mock_write, mock_sidebar):
        """Test adding prerequisite status to sidebar."""
        # Mock sidebar context manager
        mock_sidebar.__enter__ = Mock()
        mock_sidebar.__exit__ = Mock(return_value=None)
        
        integration = PrerequisiteWorkflowIntegration()
        
        with patch.object(integration.checklist_ui, 'render_compact_status', return_value={"ready": True}):
            integration.add_prerequisite_sidebar_status("test_operation", self.user_id)
        
        mock_sidebar.__enter__.assert_called_once()
        mock_write.assert_called()
    
    @patch('streamlit.sidebar')
    @patch('streamlit.button')
    def test_add_prerequisite_sidebar_status_with_issues(self, mock_button, mock_sidebar):
        """Test sidebar status with issues."""
        # Mock sidebar context manager
        mock_sidebar.__enter__ = Mock()
        mock_sidebar.__exit__ = Mock(return_value=None)
        mock_button.return_value = False
        
        integration = PrerequisiteWorkflowIntegration()
        
        with patch.object(integration.checklist_ui, 'render_compact_status', return_value={"ready": False}):
            with patch('streamlit.write'):
                integration.add_prerequisite_sidebar_status("test_operation", self.user_id)
        
        mock_button.assert_called_once()
    
    def test_prerequisite_gate_allows_ready_operation(self):
        """Test prerequisite gate allows ready operations."""
        integration = PrerequisiteWorkflowIntegration()
        
        with patch.object(integration, 'check_prerequisites_for_operation', return_value={"blocked": False}):
            result = integration.prerequisite_gate("test_operation", self.user_id)
        
        assert result is True
    
    def test_prerequisite_gate_blocks_failed_operation(self):
        """Test prerequisite gate blocks failed operations."""
        integration = PrerequisiteWorkflowIntegration()
        
        with patch.object(integration, 'check_prerequisites_for_operation', return_value={"blocked": True}):
            result = integration.prerequisite_gate("test_operation", self.user_id, "block")
        
        assert result is False
    
    def test_prerequisite_gate_allows_with_fallback(self):
        """Test prerequisite gate allows with fallback behavior."""
        integration = PrerequisiteWorkflowIntegration()
        
        with patch.object(integration, 'check_prerequisites_for_operation', return_value={"blocked": True}):
            with patch('streamlit.warning') as mock_warning:
                result = integration.prerequisite_gate("test_operation", self.user_id, "allow")
        
        assert result is True
        mock_warning.assert_called_once()
    
    @patch('streamlit.error')
    @patch('streamlit.write')
    def test_render_blocking_prerequisites_ui(self, mock_write, mock_error):
        """Test rendering blocking prerequisites UI."""
        readiness = {
            "required_failures": ["Database", "Ollama"],
            "recommended_failures": []
        }
        
        integration = PrerequisiteWorkflowIntegration()
        
        # Mock columns with context manager support
        mock_cols = []
        for i in range(2):
            col = MagicMock()
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)
            mock_cols.append(col)
        
        with patch('streamlit.columns', return_value=mock_cols):
            with patch('streamlit.button', return_value=False):
                integration._render_blocking_prerequisites_ui("test_operation", readiness, self.user_id)
        
        mock_error.assert_called_once()
        mock_write.assert_called()
    
    @patch('streamlit.expander')
    @patch('streamlit.warning')
    def test_render_prerequisite_warnings(self, mock_warning, mock_expander):
        """Test rendering prerequisite warnings."""
        readiness = {
            "recommended_failures": ["System Health"]
        }
        
        # Mock expander context manager
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        integration = PrerequisiteWorkflowIntegration()
        
        with patch('streamlit.write'):
            integration._render_prerequisite_warnings("test_operation", readiness)
        
        mock_expander.assert_called_once()
        mock_warning.assert_called_once()
    
    @patch('streamlit.expander')
    def test_show_prerequisite_resolution_dialog(self, mock_expander):
        """Test showing prerequisite resolution dialog."""
        # Mock expander context manager
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        integration = PrerequisiteWorkflowIntegration()
        
        with patch.object(integration.checklist_ui, 'render_checklist') as mock_render:
            integration._show_prerequisite_resolution_dialog("test_operation", self.user_id)
        
        mock_expander.assert_called_once()
        mock_render.assert_called_once()


class TestGlobalFunctions:
    """Test cases for global functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
        
        # Clear global instance
        import src.ui.prerequisite_integration
        src.ui.prerequisite_integration._prerequisite_integration = None
    
    def test_get_prerequisite_integration(self):
        """Test getting global prerequisite integration instance."""
        integration1 = get_prerequisite_integration()
        integration2 = get_prerequisite_integration()
        
        assert isinstance(integration1, PrerequisiteWorkflowIntegration)
        assert integration1 is integration2  # Should be singleton
    
    def test_prerequisite_check_function(self):
        """Test prerequisite check function."""
        with patch('src.ui.prerequisite_integration.get_prerequisite_integration') as mock_get:
            mock_integration = Mock()
            mock_integration.prerequisite_gate.return_value = True
            mock_get.return_value = mock_integration
            
            result = prerequisite_check("test_operation", self.user_id, "block")
        
        assert result is True
        mock_integration.prerequisite_gate.assert_called_once_with("test_operation", self.user_id, "block")
    
    def test_with_prerequisites_decorator(self):
        """Test with_prerequisites decorator."""
        @with_prerequisites("test_operation", "block")
        def test_function(user_id):
            return f"Success for {user_id}"
        
        with patch('src.ui.prerequisite_integration.prerequisite_check', return_value=True):
            result = test_function(str(self.user_id))
        
        assert result == f"Success for {self.user_id}"
    
    def test_with_prerequisites_decorator_blocked(self):
        """Test with_prerequisites decorator when blocked."""
        @with_prerequisites("test_operation", "block")
        def test_function(user_id):
            return f"Success for {user_id}"
        
        with patch('src.ui.prerequisite_integration.prerequisite_check', return_value=False):
            result = test_function(str(self.user_id))
        
        assert result is None


class TestPrerequisiteContext:
    """Test cases for PrerequisiteContext."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
    
    def test_prerequisite_context_success(self):
        """Test prerequisite context when operation succeeds."""
        with patch('src.ui.prerequisite_integration.get_prerequisite_integration') as mock_get:
            mock_integration = Mock()
            mock_integration.prerequisite_gate.return_value = True
            mock_get.return_value = mock_integration
            
            with PrerequisiteContext("test_operation", self.user_id) as can_proceed:
                assert can_proceed is True
    
    def test_prerequisite_context_blocked(self):
        """Test prerequisite context when operation is blocked."""
        with patch('src.ui.prerequisite_integration.get_prerequisite_integration') as mock_get:
            mock_integration = Mock()
            mock_integration.prerequisite_gate.return_value = False
            mock_get.return_value = mock_integration
            
            with PrerequisiteContext("test_operation", self.user_id) as can_proceed:
                assert can_proceed is False
    
    def test_prerequisite_context_function(self):
        """Test prerequisite_context function."""
        context = prerequisite_context("test_operation", self.user_id, "warn")
        
        assert isinstance(context, PrerequisiteContext)
        assert context.operation_name == "test_operation"
        assert context.user_id == self.user_id
        assert context.fallback_behavior == "warn"


class TestWorkflowIntegrationFunctions:
    """Test cases for workflow-specific integration functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
    
    @patch('src.ui.prerequisite_integration.get_prerequisite_integration')
    def test_integrate_registration_prerequisites(self, mock_get):
        """Test registration prerequisite integration."""
        mock_integration = Mock()
        mock_integration.check_prerequisites_for_operation.return_value = {"status": "ready"}
        mock_get.return_value = mock_integration
        
        result = integrate_registration_prerequisites()
        
        assert result == {"status": "ready"}
        mock_integration.add_prerequisite_sidebar_status.assert_called_once_with("registration")
        mock_integration.check_prerequisites_for_operation.assert_called_once()
    
    @patch('src.ui.prerequisite_integration.get_prerequisite_integration')
    def test_integrate_chat_prerequisites(self, mock_get):
        """Test chat prerequisite integration."""
        mock_integration = Mock()
        mock_integration.prerequisite_gate.return_value = True
        mock_get.return_value = mock_integration
        
        result = integrate_chat_prerequisites(self.user_id)
        
        assert result is True
        mock_integration.add_prerequisite_sidebar_status.assert_called_once_with("chat", self.user_id)
        mock_integration.prerequisite_gate.assert_called_once_with("chat", self.user_id, "block")
    
    @patch('src.ui.prerequisite_integration.get_prerequisite_integration')
    def test_integrate_image_generation_prerequisites(self, mock_get):
        """Test image generation prerequisite integration."""
        mock_integration = Mock()
        mock_integration.prerequisite_gate.return_value = True
        mock_get.return_value = mock_integration
        
        result = integrate_image_generation_prerequisites(self.user_id)
        
        assert result is True
        mock_integration.add_prerequisite_sidebar_status.assert_called_once_with("image_generation", self.user_id)
        mock_integration.prerequisite_gate.assert_called_once_with("image_generation", self.user_id, "warn")
    
    @patch('src.ui.prerequisite_integration.get_prerequisite_integration')
    def test_integrate_system_startup_prerequisites(self, mock_get):
        """Test system startup prerequisite integration."""
        mock_integration = Mock()
        mock_integration.check_prerequisites_for_operation.return_value = {"status": "ready"}
        mock_get.return_value = mock_integration
        
        result = integrate_system_startup_prerequisites()
        
        assert result == {"status": "ready"}
        mock_integration.add_prerequisite_sidebar_status.assert_called_once_with("system_startup")
        mock_integration.check_prerequisites_for_operation.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])