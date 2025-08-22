"""
Prerequisite Checklist UI Components for GITTE system.
Provides real-time prerequisite status display with resolution guidance.
"""

import logging
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from src.logic.prerequisite_validation import (
    PrerequisiteValidationLogic,
    PrerequisiteRecommendation,
    create_prerequisite_validation_logic
)
from src.services.prerequisite_checker import (
    PrerequisiteCheckSuite,
    PrerequisiteStatus,
    PrerequisiteType
)
from src.services.consent_service import ConsentService

logger = logging.getLogger(__name__)


class PrerequisiteChecklistUI:
    """Streamlit UI component for prerequisite checking and status display."""
    
    def __init__(
        self,
        validation_logic: Optional[PrerequisiteValidationLogic] = None,
        consent_service: Optional[ConsentService] = None
    ):
        """
        Initialize prerequisite checklist UI.
        
        Args:
            validation_logic: Optional prerequisite validation logic instance
            consent_service: Optional consent service for user-specific checks
        """
        self.validation_logic = validation_logic
        self.consent_service = consent_service
        
        # Initialize session state for UI
        if 'prerequisite_results' not in st.session_state:
            st.session_state.prerequisite_results = None
        if 'last_check_time' not in st.session_state:
            st.session_state.last_check_time = None
        if 'expanded_items' not in st.session_state:
            st.session_state.expanded_items = set()
    
    def render_checklist(
        self,
        operation_name: str = "system_startup",
        user_id: Optional[UUID] = None,
        show_header: bool = True,
        auto_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Render the prerequisite checklist interface.
        
        Args:
            operation_name: Name of operation to check prerequisites for
            user_id: Optional user ID for user-specific checks
            show_header: Whether to show the checklist header
            auto_refresh: Whether to enable auto-refresh functionality
            
        Returns:
            Dict with checklist status and user actions
        """
        if show_header:
            st.subheader("🔍 System Prerequisites")
            st.write("Checking system requirements and dependencies...")
        
        # Get validation logic
        logic = self._get_validation_logic(user_id)
        
        # Control buttons
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            if st.button("🔄 Check Prerequisites", key=f"check_{operation_name}"):
                st.session_state.prerequisite_results = None  # Force refresh
        
        with col2:
            export_requested = st.button("📊 Export Report", key=f"export_{operation_name}")
        
        with col3:
            if auto_refresh:
                auto_refresh_enabled = st.checkbox(
                    "Auto-refresh (30s)",
                    key=f"auto_refresh_{operation_name}"
                )
            else:
                auto_refresh_enabled = False
        
        # Perform prerequisite check
        if (st.session_state.prerequisite_results is None or 
            auto_refresh_enabled or 
            st.button("Refresh", key=f"refresh_{operation_name}", type="secondary")):
            
            with st.spinner("Checking prerequisites..."):
                try:
                    check_suite = logic.validate_for_operation(
                        operation_name,
                        user_id=user_id,
                        use_cache=not auto_refresh_enabled,
                        parallel_execution=True
                    )
                    st.session_state.prerequisite_results = check_suite
                    st.session_state.last_check_time = datetime.now()
                    
                except Exception as e:
                    st.error(f"Failed to check prerequisites: {str(e)}")
                    logger.error(f"Prerequisite check failed: {e}")
                    return {"status": "error", "message": str(e)}
        
        # Display results
        if st.session_state.prerequisite_results:
            result_data = self._render_results(
                st.session_state.prerequisite_results,
                logic,
                operation_name
            )
            
            # Handle export request
            if export_requested:
                self._handle_export_request(st.session_state.prerequisite_results)
            
            return result_data
        
        return {"status": "pending", "message": "No prerequisite check performed yet"}
    
    def render_compact_status(
        self,
        operation_name: str = "system_startup",
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Render a compact status indicator for prerequisites.
        
        Args:
            operation_name: Name of operation to check prerequisites for
            user_id: Optional user ID for user-specific checks
            
        Returns:
            Dict with status information
        """
        logic = self._get_validation_logic(user_id)
        
        try:
            readiness = logic.check_operation_readiness(operation_name, user_id)
            
            if readiness["ready"]:
                if readiness["can_proceed_with_warnings"]:
                    st.success("✅ System Ready")
                    if readiness["recommended_failures"]:
                        st.warning(f"⚠️ {len(readiness['recommended_failures'])} warnings")
                else:
                    st.success("✅ All Prerequisites Met")
            else:
                st.error(f"❌ {len(readiness['required_failures'])} Critical Issues")
                
                # Show critical issues
                if readiness["required_failures"]:
                    with st.expander("Critical Issues", expanded=True):
                        for issue in readiness["required_failures"]:
                            st.error(f"• {issue}")
            
            return readiness
            
        except Exception as e:
            st.error(f"Failed to check readiness: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _render_results(
        self,
        check_suite: PrerequisiteCheckSuite,
        logic: PrerequisiteValidationLogic,
        operation_name: str
    ) -> Dict[str, Any]:
        """Render the detailed prerequisite check results."""
        # Overall status
        self._render_overall_status(check_suite)
        
        # Detailed results
        st.write("### Detailed Results")
        
        # Group results by type
        required_results = [r for r in check_suite.results if r.prerequisite_type == PrerequisiteType.REQUIRED]
        recommended_results = [r for r in check_suite.results if r.prerequisite_type == PrerequisiteType.RECOMMENDED]
        optional_results = [r for r in check_suite.results if r.prerequisite_type == PrerequisiteType.OPTIONAL]
        
        # Render each group
        if required_results:
            st.write("#### 🔴 Required Prerequisites")
            for result in required_results:
                self._render_prerequisite_item(result, is_required=True)
        
        if recommended_results:
            st.write("#### 🟡 Recommended Prerequisites")
            for result in recommended_results:
                self._render_prerequisite_item(result, is_required=False)
        
        if optional_results:
            st.write("#### 🔵 Optional Prerequisites")
            for result in optional_results:
                self._render_prerequisite_item(result, is_required=False)
        
        # Show recommendations for failures
        if not check_suite.required_passed or not check_suite.recommended_passed:
            self._render_recommendations(check_suite, logic)
        
        # Show metadata
        self._render_metadata(check_suite)
        
        return {
            "status": check_suite.overall_status.value,
            "required_passed": check_suite.required_passed,
            "recommended_passed": check_suite.recommended_passed,
            "total_checks": len(check_suite.results),
            "check_time": check_suite.total_check_time
        }
    
    def _render_overall_status(self, check_suite: PrerequisiteCheckSuite):
        """Render the overall status summary."""
        if check_suite.overall_status == PrerequisiteStatus.PASSED:
            st.success("✅ All Prerequisites Satisfied")
        elif check_suite.overall_status == PrerequisiteStatus.WARNING:
            st.warning("⚠️ Prerequisites Met with Warnings")
        elif check_suite.overall_status == PrerequisiteStatus.FAILED:
            st.error("❌ Critical Prerequisites Failed")
        else:
            st.info("❓ Prerequisites Status Unknown")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Checks", len(check_suite.results))
        
        with col2:
            passed_count = sum(1 for r in check_suite.results if r.status == PrerequisiteStatus.PASSED)
            st.metric("Passed", passed_count)
        
        with col3:
            failed_count = sum(1 for r in check_suite.results if r.status == PrerequisiteStatus.FAILED)
            st.metric("Failed", failed_count)
        
        with col4:
            st.metric("Check Time", f"{check_suite.total_check_time:.2f}s")
    
    def _render_prerequisite_item(self, result, is_required: bool = True):
        """Render an individual prerequisite check result."""
        # Status icon and color
        if result.status == PrerequisiteStatus.PASSED:
            icon = "✅"
            status_color = "green"
        elif result.status == PrerequisiteStatus.FAILED:
            icon = "❌"
            status_color = "red"
        elif result.status == PrerequisiteStatus.WARNING:
            icon = "⚠️"
            status_color = "orange"
        else:
            icon = "❓"
            status_color = "gray"
        
        # Main item display
        col1, col2, col3 = st.columns([1, 6, 2])
        
        with col1:
            st.write(icon)
        
        with col2:
            st.write(f"**{result.name}**")
            st.write(result.message)
        
        with col3:
            expand_key = f"expand_{result.name}"
            if st.button("Details", key=expand_key):
                if result.name in st.session_state.expanded_items:
                    st.session_state.expanded_items.remove(result.name)
                else:
                    st.session_state.expanded_items.add(result.name)
        
        # Expanded details
        if result.name in st.session_state.expanded_items:
            with st.expander(f"Details for {result.name}", expanded=True):
                if result.details:
                    st.write("**Details:**")
                    st.write(result.details)
                
                if result.resolution_steps:
                    st.write("**Resolution Steps:**")
                    for i, step in enumerate(result.resolution_steps, 1):
                        st.write(f"{i}. {step}")
                
                st.write(f"**Check Time:** {result.check_time:.3f}s")
                st.write(f"**Type:** {result.prerequisite_type.value.title()}")
        
        st.divider()
    
    def _render_recommendations(
        self,
        check_suite: PrerequisiteCheckSuite,
        logic: PrerequisiteValidationLogic
    ):
        """Render recommendations for resolving prerequisite issues."""
        st.write("### 💡 Recommendations")
        
        try:
            recommendations = logic.analyze_prerequisite_failures(check_suite)
            
            if not recommendations:
                st.info("No specific recommendations available.")
                return
            
            for i, rec in enumerate(recommendations, 1):
                priority_color = {
                    "critical": "red",
                    "high": "orange", 
                    "medium": "blue",
                    "low": "gray"
                }.get(rec.priority, "gray")
                
                with st.container():
                    st.write(f"**{i}. {rec.checker_name}** ({rec.priority.upper()} priority)")
                    st.write(rec.issue_description)
                    
                    if rec.resolution_steps:
                        st.write("**Steps to resolve:**")
                        for step in rec.resolution_steps:
                            st.write(f"• {step}")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Estimated time:** {rec.estimated_time}")
                    
                    with col2:
                        if rec.automation_available:
                            if st.button(f"Auto-fix", key=f"autofix_{i}"):
                                st.info("Auto-fix functionality would be implemented here")
                    
                    st.divider()
                    
        except Exception as e:
            st.error(f"Failed to generate recommendations: {str(e)}")
            logger.error(f"Recommendation generation failed: {e}")
    
    def _render_metadata(self, check_suite: PrerequisiteCheckSuite):
        """Render metadata about the prerequisite check."""
        with st.expander("Check Metadata"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Timestamp:** {check_suite.timestamp}")
                st.write(f"**Total Time:** {check_suite.total_check_time:.3f}s")
            
            with col2:
                st.write(f"**Cached Results:** {'Yes' if check_suite.cached else 'No'}")
                st.write(f"**Required Passed:** {'Yes' if check_suite.required_passed else 'No'}")
    
    def _handle_export_request(self, check_suite: PrerequisiteCheckSuite):
        """Handle export report request."""
        try:
            # Generate report data
            report_data = {
                "timestamp": check_suite.timestamp,
                "overall_status": check_suite.overall_status.value,
                "required_passed": check_suite.required_passed,
                "recommended_passed": check_suite.recommended_passed,
                "total_check_time": check_suite.total_check_time,
                "results": []
            }
            
            for result in check_suite.results:
                report_data["results"].append({
                    "name": result.name,
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details,
                    "type": result.prerequisite_type.value,
                    "check_time": result.check_time,
                    "resolution_steps": result.resolution_steps or []
                })
            
            # Convert to JSON for download
            import json
            report_json = json.dumps(report_data, indent=2)
            
            st.download_button(
                label="📥 Download JSON Report",
                data=report_json,
                file_name=f"prerequisite_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            # Also offer CSV format
            import pandas as pd
            
            df_data = []
            for result in check_suite.results:
                df_data.append({
                    "Name": result.name,
                    "Status": result.status.value,
                    "Message": result.message,
                    "Type": result.prerequisite_type.value,
                    "Check Time (s)": result.check_time
                })
            
            df = pd.DataFrame(df_data)
            csv_data = df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download CSV Report",
                data=csv_data,
                file_name=f"prerequisite_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success("Report export options generated!")
            
        except Exception as e:
            st.error(f"Failed to generate export: {str(e)}")
            logger.error(f"Export generation failed: {e}")
    
    def _get_validation_logic(self, user_id: Optional[UUID]) -> PrerequisiteValidationLogic:
        """Get or create validation logic instance."""
        if self.validation_logic:
            return self.validation_logic
        
        return create_prerequisite_validation_logic(
            user_id=user_id,
            consent_service=self.consent_service
        )


def render_prerequisite_sidebar(
    operation_name: str = "system_startup",
    user_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Render a compact prerequisite status in the sidebar.
    
    Args:
        operation_name: Name of operation to check prerequisites for
        user_id: Optional user ID for user-specific checks
        
    Returns:
        Dict with status information
    """
    with st.sidebar:
        st.write("### System Status")
        
        checklist_ui = PrerequisiteChecklistUI()
        return checklist_ui.render_compact_status(operation_name, user_id)


def render_prerequisite_page(
    operation_name: str = "system_startup",
    user_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Render a full prerequisite checklist page.
    
    Args:
        operation_name: Name of operation to check prerequisites for
        user_id: Optional user ID for user-specific checks
        
    Returns:
        Dict with checklist results
    """
    st.title("System Prerequisites")
    st.write("Comprehensive system prerequisite checking and validation.")
    
    checklist_ui = PrerequisiteChecklistUI()
    
    return checklist_ui.render_checklist(
        operation_name=operation_name,
        user_id=user_id,
        show_header=False,
        auto_refresh=True
    )


# Accessibility helpers
def render_accessible_prerequisite_checklist(
    operation_name: str = "system_startup",
    user_id: Optional[UUID] = None,
    screen_reader_mode: bool = False
) -> Dict[str, Any]:
    """
    Render prerequisite checklist with enhanced accessibility features.
    
    Args:
        operation_name: Name of operation to check prerequisites for
        user_id: Optional user ID for user-specific checks
        screen_reader_mode: Whether to optimize for screen readers
        
    Returns:
        Dict with checklist results
    """
    if screen_reader_mode:
        # Provide text-only version for screen readers
        st.write("# System Prerequisites Check")
        st.write("This page shows the status of system prerequisites.")
    
    checklist_ui = PrerequisiteChecklistUI()
    
    # Add ARIA labels and roles via custom CSS
    st.markdown("""
    <style>
    .prerequisite-item {
        role: listitem;
        aria-label: "Prerequisite check result";
    }
    .prerequisite-status {
        role: status;
        aria-live: polite;
    }
    .prerequisite-actions {
        role: group;
        aria-label: "Prerequisite actions";
    }
    </style>
    """, unsafe_allow_html=True)
    
    return checklist_ui.render_checklist(
        operation_name=operation_name,
        user_id=user_id,
        show_header=True,
        auto_refresh=False
    )