"""
Study Participation Admin UI components.
Provides Streamlit components for study-specific administrative functions,
database management, and data export with proper pseudonymization.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import streamlit as st

from src.data.database import DatabaseManager, get_session
from src.logic.admin_logic import AdminLogic
from src.services.admin_service import AdminService

logger = logging.getLogger(__name__)


class StudyAdminUI:
    """Streamlit UI components for study administration."""

    def __init__(self):
        """Initialize study admin UI."""
        self.db_manager = DatabaseManager()
        self.admin_logic = AdminLogic(self.db_manager)

    def render_admin_dashboard(self) -> None:
        """
        Render the main admin dashboard with database management options.
        
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
        """
        st.title("🔧 Study Administration Dashboard")
        st.markdown("---")

        # Database status section
        self._render_database_status()
        
        # Database management section
        self._render_database_management()
        
        # Data export section
        self._render_data_export()
        
        # Data privacy section
        self._render_data_privacy()

    def _render_database_status(self) -> None:
        """Render database status and statistics."""
        st.subheader("📊 Database Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh Statistics", key="refresh_stats"):
                st.rerun()
        
        with col2:
            if st.button("🔍 Validate Integrity", key="validate_integrity"):
                with st.spinner("Validating database integrity..."):
                    result = self.admin_logic.validate_database_integrity()
                    
                    if result.success:
                        st.success("✅ Database integrity validation passed")
                    else:
                        st.error("❌ Database integrity issues found")
                        for violation in result.constraint_violations:
                            st.error(f"• {violation}")
                        for missing in result.missing_tables:
                            st.error(f"• Missing table: {missing}")

        # Display statistics
        try:
            stats = self.admin_logic.get_database_statistics()
            
            if "error" not in stats:
                st.markdown("### 📈 Record Counts")
                
                # Create metrics display
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Pseudonyms", stats.get("pseudonyms", 0))
                    st.metric("Consent Records", stats.get("consent_records", 0))
                
                with col2:
                    st.metric("Survey Responses", stats.get("survey_responses", 0))
                    st.metric("Chat Messages", stats.get("chat_messages", 0))
                
                with col3:
                    st.metric("PALD Data", stats.get("pald_data", 0))
                    st.metric("Generated Images", stats.get("generated_images", 0))
                
                with col4:
                    st.metric("Feedback Records", stats.get("feedback_records", 0))
                    st.metric("Interaction Logs", stats.get("interaction_logs", 0))
                
                # Summary metrics
                st.markdown("### 📋 Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Active Pseudonyms", stats.get("active_pseudonyms", 0))
                
                with col2:
                    st.metric("Total Study Records", stats.get("total_study_records", 0))
                
                with col3:
                    last_updated = datetime.now().strftime("%H:%M:%S")
                    st.metric("Last Updated", last_updated)
            else:
                st.error(f"Failed to load statistics: {stats['error']}")
                
        except Exception as e:
            st.error(f"Error loading database statistics: {e}")

    def _render_database_management(self) -> None:
        """Render database management controls with safety checks."""
        st.subheader("🗄️ Database Management")
        
        # Safety warning
        st.warning("⚠️ **Warning**: Database operations are irreversible. Use with caution!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Initialize Database")
            st.info("Creates all required tables if they don't exist. Safe to run multiple times.")
            
            if st.button("🚀 Initialize Database", key="init_db"):
                with st.spinner("Initializing database..."):
                    result = self.admin_logic.initialize_database_schema()
                    
                    if result.success:
                        st.success("✅ Database initialized successfully")
                        if result.tables_created:
                            st.info(f"Created tables: {', '.join(result.tables_created)}")
                        else:
                            st.info("All tables already exist")
                    else:
                        st.error("❌ Database initialization failed")
                        for error in result.errors:
                            st.error(f"• {error}")
        
        with col2:
            st.markdown("#### Reset Database")
            st.error("⚠️ **DANGER**: This will delete ALL study data permanently!")
            
            # Safety confirmation
            confirm_reset = st.checkbox("I understand this will delete all data", key="confirm_reset")
            
            if confirm_reset:
                safety_text = st.text_input(
                    "Type 'DELETE ALL DATA' to confirm:",
                    key="safety_confirmation"
                )
                
                if safety_text == "DELETE ALL DATA":
                    if st.button("💥 RESET DATABASE", key="reset_db", type="primary"):
                        with st.spinner("Resetting database..."):
                            result = self.admin_logic.reset_all_study_data()
                            
                            if result.success:
                                st.success("✅ Database reset completed")
                                st.info(f"Dropped tables: {', '.join(result.tables_dropped)}")
                                st.info(f"Recreated tables: {', '.join(result.tables_recreated)}")
                                # Clear the confirmation
                                st.rerun()
                            else:
                                st.error("❌ Database reset failed")
                                for error in result.errors:
                                    st.error(f"• {error}")

    def _render_data_export(self) -> None:
        """Render data export interface with pseudonymization options."""
        st.subheader("📤 Data Export")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Export Options")
            
            # Export scope selection
            export_scope = st.radio(
                "Export Scope:",
                ["All Data", "Specific Pseudonym"],
                key="export_scope"
            )
            
            pseudonym_id = None
            if export_scope == "Specific Pseudonym":
                pseudonym_text = st.text_input(
                    "Pseudonym ID (UUID):",
                    help="Enter the UUID of the pseudonym to export data for",
                    key="export_pseudonym_id"
                )
                
                if pseudonym_text:
                    try:
                        pseudonym_id = UUID(pseudonym_text)
                    except ValueError:
                        st.error("Invalid UUID format")
                        return
            
            # Export format
            export_format = st.selectbox(
                "Export Format:",
                ["JSON"],
                key="export_format"
            )
        
        with col2:
            st.markdown("#### Export Actions")
            
            # Preview export
            if st.button("👁️ Preview Export", key="preview_export"):
                with st.spinner("Generating export preview..."):
                    result = self.admin_logic.export_study_data(pseudonym_id)
                    
                    if result.success:
                        st.success("✅ Export preview generated")
                        
                        # Display export statistics
                        st.markdown("**Export Statistics:**")
                        for table, count in result.exported_records.items():
                            st.write(f"• {table}: {count} records")
                        
                        total_records = sum(result.exported_records.values())
                        st.info(f"**Total records to export: {total_records}**")
                    else:
                        st.error("❌ Export preview failed")
                        for error in result.errors:
                            st.error(f"• {error}")
            
            # Download export
            if st.button("💾 Download Export", key="download_export"):
                with st.spinner("Generating export file..."):
                    try:
                        with get_session() as session:
                            admin_service = AdminService(session)
                            
                            # Create temporary file
                            with tempfile.NamedTemporaryFile(
                                mode='w', 
                                suffix='.json', 
                                delete=False
                            ) as tmp_file:
                                export_result = admin_service.export_study_data_to_file(
                                    tmp_file.name,
                                    pseudonym_id,
                                    export_format.lower()
                                )
                                
                                if export_result["success"]:
                                    # Read the file for download
                                    with open(tmp_file.name, 'r', encoding='utf-8') as f:
                                        export_data = f.read()
                                    
                                    # Generate filename
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    scope = "all" if pseudonym_id is None else str(pseudonym_id)[:8]
                                    filename = f"study_export_{scope}_{timestamp}.json"
                                    
                                    st.download_button(
                                        label="📥 Download Export File",
                                        data=export_data,
                                        file_name=filename,
                                        mime="application/json",
                                        key="download_button"
                                    )
                                    
                                    st.success("✅ Export file ready for download")
                                    
                                    # Show export statistics
                                    total_records = sum(export_result["records_exported"].values())
                                    st.info(f"Exported {total_records} total records")
                                    
                                else:
                                    st.error("❌ Export generation failed")
                                    for error in export_result["errors"]:
                                        st.error(f"• {error}")
                                
                                # Clean up temporary file
                                Path(tmp_file.name).unlink(missing_ok=True)
                                
                    except Exception as e:
                        st.error(f"Export failed: {e}")

    def _render_data_privacy(self) -> None:
        """Render data privacy and participant rights interface."""
        st.subheader("🔒 Data Privacy & Participant Rights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Delete Participant Data")
            st.info("Delete all data associated with a specific pseudonym (GDPR compliance)")
            
            delete_pseudonym_text = st.text_input(
                "Pseudonym ID to Delete:",
                help="Enter the UUID of the pseudonym to delete all data for",
                key="delete_pseudonym_id"
            )
            
            if delete_pseudonym_text:
                try:
                    delete_pseudonym_id = UUID(delete_pseudonym_text)
                    
                    # Safety confirmation
                    confirm_delete = st.checkbox(
                        f"I confirm deletion of all data for pseudonym {delete_pseudonym_id}",
                        key="confirm_delete"
                    )
                    
                    if confirm_delete:
                        if st.button("🗑️ Delete Participant Data", key="delete_participant", type="primary"):
                            with st.spinner("Deleting participant data..."):
                                success = self.admin_logic.delete_participant_data(delete_pseudonym_id)
                                
                                if success:
                                    st.success("✅ Participant data deleted successfully")
                                else:
                                    st.error("❌ Failed to delete participant data")
                                    
                except ValueError:
                    st.error("Invalid UUID format")
        
        with col2:
            st.markdown("#### Data Cleanup")
            st.info("Clean up orphaned records and maintain data integrity")
            
            if st.button("🧹 Clean Orphaned Records", key="cleanup_orphaned"):
                with st.spinner("Cleaning up orphaned records..."):
                    try:
                        with get_session() as session:
                            admin_service = AdminService(session)
                            cleanup_result = admin_service.cleanup_orphaned_records()
                            
                            if "error" not in cleanup_result:
                                total_cleaned = sum(cleanup_result.values())
                                if total_cleaned > 0:
                                    st.success(f"✅ Cleaned up {total_cleaned} orphaned records")
                                    for table, count in cleanup_result.items():
                                        if count > 0:
                                            st.info(f"• {table}: {count} records cleaned")
                                else:
                                    st.info("No orphaned records found")
                            else:
                                st.error(f"Cleanup failed: {cleanup_result['error']}")
                                
                    except Exception as e:
                        st.error(f"Cleanup failed: {e}")
            
            if st.button("🔧 Database Maintenance", key="db_maintenance"):
                with st.spinner("Performing database maintenance..."):
                    try:
                        with get_session() as session:
                            admin_service = AdminService(session)
                            success = admin_service.vacuum_database()
                            
                            if success:
                                st.success("✅ Database maintenance completed")
                            else:
                                st.warning("Database maintenance not applicable or failed")
                                
                    except Exception as e:
                        st.error(f"Database maintenance failed: {e}")

    def render_admin_sidebar(self) -> None:
        """Render admin-specific sidebar controls."""
        with st.sidebar:
            st.markdown("### 🔧 Admin Tools")
            
            # Quick actions
            if st.button("🔄 Refresh All", key="sidebar_refresh"):
                st.rerun()
            
            # Database status indicator
            try:
                stats = self.admin_logic.get_database_statistics()
                if "error" not in stats:
                    total_records = stats.get("total_study_records", 0)
                    st.metric("Total Study Records", total_records)
                    
                    active_pseudonyms = stats.get("active_pseudonyms", 0)
                    if active_pseudonyms > 0:
                        st.success(f"✅ {active_pseudonyms} active participants")
                    else:
                        st.info("No active participants")
                else:
                    st.error("Database connection issue")
                    
            except Exception as e:
                st.error(f"Status check failed: {e}")
            
            # Safety reminders
            st.markdown("---")
            st.markdown("### ⚠️ Safety Reminders")
            st.warning("• Always backup before reset")
            st.warning("• Verify exports before deletion")
            st.warning("• Database operations are irreversible")


def render_study_admin_page() -> None:
    """
    Main function to render the study administration page.
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
    """
    # Check if user has admin privileges (this would be integrated with auth system)
    # For now, we'll assume admin access is granted
    
    admin_ui = StudyAdminUI()
    
    # Render sidebar
    admin_ui.render_admin_sidebar()
    
    # Render main dashboard
    admin_ui.render_admin_dashboard()


# Streamlit app entry point for testing
if __name__ == "__main__":
    render_study_admin_page()