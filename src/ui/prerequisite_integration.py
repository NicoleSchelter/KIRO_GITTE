"""
Prerequisite Integration for GITTE workflows.
Integrates prerequisite checking with existing UI workflows.
"""

import logging
import streamlit as st
from typing import Dict, Optional, Any, Callable
from uuid import UUID

from src.logic.prerequisite_validation import (
    PrerequisiteValidationLogic,
    create_prerequisite_validation_logic
)
from src.services.prerequisite_checker import PrerequisiteStatus
from src.services.consent_service import ConsentService
from src.ui.prerequisite_checklist_ui import PrerequisiteChecklistUI

logger = logging.getLogger(__name__)


class PrerequisiteWorkflowIntegration:
    """Integration layer for adding prerequisite checks to existing workflows."""
    
    def __init__(
        self,
        validation_logic: Optional[PrerequisiteValidationLogic] = None,
        consent_service: Optional[ConsentService] = None
    ):
        """
        Initialize prerequisite workflow integration.
        
        Args:
            validation_logic: Optional prerequisite validation logic instance
            consent_service: Optional consent service for user-specific checks
        """
        self.validation_logic = validation_logic
        self.consent_service = consent_service
        self.checklist_ui = PrerequisiteChecklistUI(validation_logic, consent_service)
        
        # Initialize session state for prerequisite tracking
        if 'prerequisite_status' not in st.session_state:
            st.session_state.prerequisite_status = {}
        if 'prerequisite_warnings_shown' not in st.session_state:
            st.session_state.prerequisite_warnings_shown = set()
    
    def check_prerequisites_for_operation(
        self,
        operation_name: str,
        user_id: Optional[UUID] = None,
        show_blocking_ui: bool = True,
        show_warnings: bool = True
    ) -> Dict[str, Any]:
        """
        Check prerequisites for a specific operation.
        
        Args:
            operation_name: Name of the operation to check prerequisites for
            user_id: Optional user ID for user-specific checks
            show_blocking_ui: Whether to show blocking UI for failed prerequisites
            show_warnings: Whether to show warnings for non-critical issues
            
        Returns:
            Dict with prerequisite status and readiness information
        """
        try:
            logic = self._get_validation_logic(user_id)
            readiness = logic.check_operation_readiness(operation_name, user_id)
            
            # Cache the result
            cache_key = f"{operation_name}_{user_id or 'anonymous'}"
            st.session_state.prerequisite_status[cache_key] = readiness
            
            # Handle blocking prerequisites
            if not readiness["ready"] and show_blocking_ui:
                self._render_blocking_prerequisites_ui(operation_name, readiness, user_id)
                return {"blocked": True, "readiness": readiness}
            
            # Handle warnings
            if (readiness["ready"] and not readiness["can_proceed_with_warnings"] and 
                show_warnings and cache_key not in st.session_state.prerequisite_warnings_shown):
                self._render_prerequisite_warnings(operation_name, readiness)
                st.session_state.prerequisite_warnings_shown.add(cache_key)
            
            return {"blocked": False, "readiness": readiness}
            
        except Exception as e:
            logger.error(f"Prerequisite check failed for {operation_name}: {e}")
            if show_blocking_ui:
                st.error(f"Unable to check system prerequisites: {str(e)}")
            return {"blocked": True, "error": str(e)}
    
    def add_prerequisite_sidebar_status(
        self,
        operation_name: str = "system_startup",
        user_id: Optional[UUID] = None
    ):
        """
        Add prerequisite status to the sidebar.
        
        Args:
            operation_name: Operation to check prerequisites for
            user_id: Optional user ID for user-specific checks
        """
        with st.sidebar:
            st.markdown("---")
            st.write("### System Status")
            
            try:
                status = self.checklist_ui.render_compact_status(operation_name, user_id)
                
                # Add quick actions if there are issues
                if not status.get("ready", True):
                    if st.button("🔧 Fix Issues", key="sidebar_fix_issues"):
                        self._show_prerequisite_resolution_dialog(operation_name, user_id)
                        
            except Exception as e:
                st.error("Status check failed")
                logger.error(f"Sidebar status check failed: {e}")
    
    def prerequisite_gate(
        self,
        operation_name: str,
        user_id: Optional[UUID] = None,
        fallback_behavior: str = "block"
    ) -> bool:
        """
        Gate function that checks prerequisites before allowing operation.
        
        Args:
            operation_name: Name of the operation to gate
            user_id: Optional user ID for user-specific checks
            fallback_behavior: Behavior when prerequisites fail ("block", "warn", "allow")
            
        Returns:
            bool: True if operation should proceed, False if blocked
        """
        result = self.check_prerequisites_for_operation(
            operation_name,
            user_id,
            show_blocking_ui=(fallback_behavior == "block"),
            show_warnings=(fallback_behavior in ["warn", "block"])
        )
        
        if result.get("blocked", False):
            if fallback_behavior == "allow":
                st.warning(f"⚠️ Proceeding with {operation_name} despite prerequisite issues")
                return True
            return False
        
        return True
    
    def _render_blocking_prerequisites_ui(
        self,
        operation_name: str,
        readiness: Dict[str, Any],
        user_id: Optional[UUID]
    ):
        """Render UI for blocking prerequisite failures."""
        st.error("🚫 Cannot proceed - Critical prerequisites not met")
        
        st.write(f"**Operation:** {operation_name.replace('_', ' ').title()}")
        
        if readiness["required_failures"]:
            st.write("**Critical Issues:**")
            for issue in readiness["required_failures"]:
                st.write(f"❌ {issue}")
        
        # Show resolution options
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔧 Show Resolution Steps", key=f"resolve_{operation_name}"):
                self._show_prerequisite_resolution_dialog(operation_name, user_id)
        
        with col2:
            if st.button("🔄 Recheck Prerequisites", key=f"recheck_{operation_name}"):
                # Clear cache to force recheck
                cache_key = f"{operation_name}_{user_id or 'anonymous'}"
                if cache_key in st.session_state.prerequisite_status:
                    del st.session_state.prerequisite_status[cache_key]
                st.rerun()
    
    def _render_prerequisite_warnings(
        self,
        operation_name: str,
        readiness: Dict[str, Any]
    ):
        """Render warnings for non-critical prerequisite issues."""
        if readiness["recommended_failures"]:
            with st.expander("⚠️ System Warnings", expanded=False):
                st.warning("Some recommended prerequisites are not met. The system will work but may have reduced functionality.")
                
                for issue in readiness["recommended_failures"]:
                    st.write(f"⚠️ {issue}")
                
                st.write("You can continue using the system, but consider resolving these issues for optimal performance.")
    
    def _show_prerequisite_resolution_dialog(
        self,
        operation_name: str,
        user_id: Optional[UUID]
    ):
        """Show detailed prerequisite resolution dialog."""
        with st.expander("🔧 Prerequisite Resolution", expanded=True):
            self.checklist_ui.render_checklist(
                operation_name=operation_name,
                user_id=user_id,
                show_header=False,
                auto_refresh=False
            )
    
    def _get_validation_logic(self, user_id: Optional[UUID]) -> PrerequisiteValidationLogic:
        """Get or create validation logic instance."""
        if self.validation_logic:
            return self.validation_logic
        
        return create_prerequisite_validation_logic(
            user_id=user_id,
            consent_service=self.consent_service
        )


# Global instance for easy access
_prerequisite_integration = None


def get_prerequisite_integration() -> PrerequisiteWorkflowIntegration:
    """Get global prerequisite integration instance."""
    global _prerequisite_integration
    if _prerequisite_integration is None:
        _prerequisite_integration = PrerequisiteWorkflowIntegration()
    return _prerequisite_integration


def prerequisite_check(
    operation_name: str,
    user_id: Optional[UUID] = None,
    fallback_behavior: str = "block"
) -> bool:
    """
    Decorator-style function for prerequisite checking.
    
    Args:
        operation_name: Name of the operation to check
        user_id: Optional user ID for user-specific checks
        fallback_behavior: Behavior when prerequisites fail
        
    Returns:
        bool: True if operation should proceed
    """
    integration = get_prerequisite_integration()
    return integration.prerequisite_gate(operation_name, user_id, fallback_behavior)


def with_prerequisites(
    operation_name: str,
    fallback_behavior: str = "block"
):
    """
    Decorator for functions that require prerequisite checking.
    
    Args:
        operation_name: Name of the operation to check
        fallback_behavior: Behavior when prerequisites fail
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Try to extract user_id from args/kwargs
            user_id = None
            if args and isinstance(args[0], (str, UUID)):
                try:
                    user_id = UUID(str(args[0]))
                except (ValueError, TypeError):
                    pass
            
            if not prerequisite_check(operation_name, user_id, fallback_behavior):
                return None
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Workflow-specific integration functions

def integrate_registration_prerequisites():
    """Integrate prerequisite checks with registration workflow."""
    integration = get_prerequisite_integration()
    
    # Add sidebar status
    integration.add_prerequisite_sidebar_status("registration")
    
    # Check prerequisites for registration
    return integration.check_prerequisites_for_operation(
        "registration",
        show_blocking_ui=True,
        show_warnings=True
    )


def integrate_chat_prerequisites(user_id: UUID):
    """Integrate prerequisite checks with chat workflow."""
    integration = get_prerequisite_integration()
    
    # Add sidebar status
    integration.add_prerequisite_sidebar_status("chat", user_id)
    
    # Gate chat functionality
    return integration.prerequisite_gate("chat", user_id, "block")


def integrate_image_generation_prerequisites(user_id: UUID):
    """Integrate prerequisite checks with image generation workflow."""
    integration = get_prerequisite_integration()
    
    # Add sidebar status
    integration.add_prerequisite_sidebar_status("image_generation", user_id)
    
    # Gate image generation functionality
    return integration.prerequisite_gate("image_generation", user_id, "warn")


def integrate_system_startup_prerequisites():
    """Integrate prerequisite checks with system startup."""
    integration = get_prerequisite_integration()
    
    # Check system startup prerequisites
    result = integration.check_prerequisites_for_operation(
        "system_startup",
        show_blocking_ui=False,
        show_warnings=True
    )
    
    # Add to sidebar
    integration.add_prerequisite_sidebar_status("system_startup")
    
    return result


# Context managers for prerequisite-aware operations

class PrerequisiteContext:
    """Context manager for prerequisite-aware operations."""
    
    def __init__(
        self,
        operation_name: str,
        user_id: Optional[UUID] = None,
        fallback_behavior: str = "block"
    ):
        self.operation_name = operation_name
        self.user_id = user_id
        self.fallback_behavior = fallback_behavior
        self.integration = get_prerequisite_integration()
        self.can_proceed = False
    
    def __enter__(self):
        self.can_proceed = self.integration.prerequisite_gate(
            self.operation_name,
            self.user_id,
            self.fallback_behavior
        )
        return self.can_proceed
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Log completion or failure
        if exc_type is None and self.can_proceed:
            logger.info(f"Operation {self.operation_name} completed successfully")
        elif exc_type is not None:
            logger.error(f"Operation {self.operation_name} failed: {exc_val}")


def prerequisite_context(
    operation_name: str,
    user_id: Optional[UUID] = None,
    fallback_behavior: str = "block"
) -> PrerequisiteContext:
    """
    Create a prerequisite context manager.
    
    Args:
        operation_name: Name of the operation
        user_id: Optional user ID
        fallback_behavior: Behavior when prerequisites fail
        
    Returns:
        PrerequisiteContext instance
    """
    return PrerequisiteContext(operation_name, user_id, fallback_behavior)