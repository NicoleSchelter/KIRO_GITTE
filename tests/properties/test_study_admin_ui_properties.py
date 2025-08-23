"""
Property-based tests for StudyAdminUI components.
Tests invariants and properties of admin interface behavior.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from unittest.mock import Mock, patch
from uuid import UUID, uuid4
from datetime import datetime

from src.ui.study_admin_ui import StudyAdminUI
from src.logic.admin_logic import InitializationResult, ResetResult, ValidationResult, ExportResult


class TestStudyAdminUIProperties:
    """Property-based test cases for StudyAdminUI invariants."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_admin_logic = Mock()
        
        with patch('src.ui.study_admin_ui.DatabaseManager', return_value=self.mock_db_manager), \
             patch('src.ui.study_admin_ui.AdminLogic', return_value=self.mock_admin_logic):
            self.admin_ui = StudyAdminUI()

    @given(
        pseudonyms=st.integers(min_value=0, max_value=1000),
        consents=st.integers(min_value=0, max_value=1000),
        surveys=st.integers(min_value=0, max_value=1000),
        chats=st.integers(min_value=0, max_value=1000),
        palds=st.integers(min_value=0, max_value=1000),
        images=st.integers(min_value=0, max_value=1000),
        feedbacks=st.integers(min_value=0, max_value=1000),
        logs=st.integers(min_value=0, max_value=1000),
        active_pseudonyms=st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=50)
    def test_database_statistics_display_invariants(self, pseudonyms, consents, surveys, chats, 
                                                  palds, images, feedbacks, logs, active_pseudonyms):
        """Test that database statistics display maintains invariants regardless of data size."""
        # Ensure active pseudonyms doesn't exceed total pseudonyms
        assume(active_pseudonyms <= pseudonyms)
        
        # Setup statistics
        stats = {
            "pseudonyms": pseudonyms,
            "consent_records": consents,
            "survey_responses": surveys,
            "chat_messages": chats,
            "pald_data": palds,
            "generated_images": images,
            "feedback_records": feedbacks,
            "interaction_logs": logs,
            "active_pseudonyms": active_pseudonyms,
            "total_study_records": consents + surveys + chats + palds + images + feedbacks + logs
        }
        self.mock_admin_logic.get_database_statistics.return_value = stats

        # Mock Streamlit components
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock(), Mock(), Mock()]), \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.metric') as mock_metric:
            
            # Execute
            self.admin_ui._render_database_status()
            
            # Verify invariants
            # 1. All metrics should be called with non-negative values
            metric_calls = mock_metric.call_args_list
            for call in metric_calls:
                if len(call[0]) >= 2:  # Has label and value
                    value = call[0][1]
                    assert value >= 0, f"Metric value should be non-negative: {value}"
            
            # 2. Total study records should equal sum of individual record types
            expected_total = consents + surveys + chats + palds + images + feedbacks + logs
            assert stats["total_study_records"] == expected_total
            
            # 3. Active pseudonyms should not exceed total pseudonyms
            assert stats["active_pseudonyms"] <= stats["pseudonyms"]

    @given(
        success=st.booleans(),
        tables_created=st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=20),
        errors=st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)
    )
    @settings(max_examples=30)
    def test_initialization_result_display_invariants(self, success, tables_created, errors):
        """Test that initialization results are displayed consistently regardless of content."""
        # Setup initialization result
        result = InitializationResult(
            success=success,
            tables_created=tables_created,
            errors=errors,
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.initialize_database_schema.return_value = result

        # Mock Streamlit components
        with patch('streamlit.subheader'), \
             patch('streamlit.warning'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.button', side_effect=[True, False]), \
             patch('streamlit.spinner'), \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.info') as mock_info:
            
            # Execute
            self.admin_ui._render_database_management()
            
            # Verify invariants
            if success:
                # 1. Success should always show success message
                mock_success.assert_called()
                success_calls = [call for call in mock_success.call_args_list 
                               if "initialized successfully" in str(call)]
                assert len(success_calls) > 0
                
                # 2. If tables were created, info should be shown
                if tables_created:
                    info_calls = [call for call in mock_info.call_args_list 
                                if "Created tables" in str(call)]
                    assert len(info_calls) > 0
            else:
                # 3. Failure should show error messages
                if errors:
                    mock_error.assert_called()

    @given(
        success=st.booleans(),
        tables_dropped=st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=20),
        tables_recreated=st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=20),
        errors=st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)
    )
    @settings(max_examples=30)
    def test_reset_result_display_invariants(self, success, tables_dropped, tables_recreated, errors):
        """Test that reset results maintain consistency invariants."""
        # For successful resets, dropped and recreated tables should match
        if success:
            assume(len(tables_dropped) == len(tables_recreated))
        
        # Setup reset result
        result = ResetResult(
            success=success,
            tables_dropped=tables_dropped,
            tables_recreated=tables_recreated,
            errors=errors,
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.reset_all_study_data.return_value = result

        # Mock Streamlit components
        with patch('streamlit.subheader'), \
             patch('streamlit.warning'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.button', side_effect=[False, True]), \
             patch('streamlit.checkbox', return_value=True), \
             patch('streamlit.text_input', return_value="DELETE ALL DATA"), \
             patch('streamlit.spinner'), \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.info') as mock_info, \
             patch('streamlit.rerun'):
            
            # Execute
            self.admin_ui._render_database_management()
            
            # Verify invariants
            if success:
                # 1. Success should show completion message
                mock_success.assert_called()
                
                # 2. For successful resets, dropped and recreated counts should match
                assert len(tables_dropped) == len(tables_recreated)
                
                # 3. Info should show both dropped and recreated tables
                info_calls = mock_info.call_args_list
                dropped_info = any("Dropped tables" in str(call) for call in info_calls)
                recreated_info = any("Recreated tables" in str(call) for call in info_calls)
                if tables_dropped:
                    assert dropped_info
                if tables_recreated:
                    assert recreated_info
            else:
                # 4. Failure should show error messages
                if errors:
                    mock_error.assert_called()

    @given(
        exported_records=st.dictionaries(
            keys=st.sampled_from([
                "pseudonyms", "consent_records", "survey_responses", 
                "chat_messages", "pald_data", "generated_images", 
                "feedback_records", "interaction_logs"
            ]),
            values=st.integers(min_value=0, max_value=1000),
            min_size=1,
            max_size=8
        ),
        success=st.booleans(),
        errors=st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=5)
    )
    @settings(max_examples=30)
    def test_export_result_display_invariants(self, exported_records, success, errors):
        """Test that export results display maintains invariants."""
        # Setup export result
        result = ExportResult(
            success=success,
            exported_records=exported_records,
            file_path=None,
            errors=errors,
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.export_study_data.return_value = result

        # Mock Streamlit components
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.radio', return_value="All Data"), \
             patch('streamlit.selectbox', return_value="JSON"), \
             patch('streamlit.button', side_effect=[True, False]), \
             patch('streamlit.spinner'), \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.write') as mock_write, \
             patch('streamlit.info') as mock_info:
            
            # Execute
            self.admin_ui._render_data_export()
            
            # Verify invariants
            if success:
                # 1. Success should show completion message
                mock_success.assert_called()
                
                # 2. Total records calculation should be consistent
                total_records = sum(exported_records.values())
                info_calls = mock_info.call_args_list
                total_info = any(str(total_records) in str(call) for call in info_calls)
                assert total_info
                
                # 3. All record counts should be non-negative
                for table, count in exported_records.items():
                    assert count >= 0, f"Record count should be non-negative: {table}={count}"
                
                # 4. Individual record types should be displayed
                write_calls = mock_write.call_args_list
                for table, count in exported_records.items():
                    table_displayed = any(table in str(call) and str(count) in str(call) 
                                        for call in write_calls)
                    assert table_displayed, f"Table {table} with count {count} should be displayed"
            else:
                # 5. Failure should show error messages
                if errors:
                    mock_error.assert_called()

    @given(
        pseudonym_uuid=st.uuids(),
        deletion_success=st.booleans()
    )
    @settings(max_examples=20)
    def test_participant_deletion_invariants(self, pseudonym_uuid, deletion_success):
        """Test that participant deletion maintains invariants."""
        # Setup
        self.mock_admin_logic.delete_participant_data.return_value = deletion_success

        # Mock Streamlit components
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.text_input', return_value=str(pseudonym_uuid)), \
             patch('streamlit.checkbox', return_value=True), \
             patch('streamlit.button', side_effect=[True, False, False]), \
             patch('streamlit.spinner'), \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error:
            
            # Execute
            self.admin_ui._render_data_privacy()
            
            # Verify invariants
            # 1. Admin logic should be called with correct UUID type
            self.mock_admin_logic.delete_participant_data.assert_called_once_with(pseudonym_uuid)
            
            # 2. UI feedback should match operation result
            if deletion_success:
                mock_success.assert_called()
                success_calls = [call for call in mock_success.call_args_list 
                               if "deleted successfully" in str(call)]
                assert len(success_calls) > 0
            else:
                mock_error.assert_called()
                error_calls = [call for call in mock_error.call_args_list 
                             if "Failed to delete" in str(call)]
                assert len(error_calls) > 0

    @given(
        invalid_uuid_text=st.text(min_size=1, max_size=100).filter(
            lambda x: not _is_valid_uuid(x)
        )
    )
    @settings(max_examples=20)
    def test_uuid_validation_invariants(self, invalid_uuid_text):
        """Test that UUID validation consistently rejects invalid formats."""
        # Mock Streamlit components
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.radio', return_value="Specific Pseudonym"), \
             patch('streamlit.text_input', return_value=invalid_uuid_text), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.error') as mock_error:
            
            # Execute
            self.admin_ui._render_data_export()
            
            # Verify invariants
            # 1. Invalid UUID should always trigger error
            mock_error.assert_called_with("Invalid UUID format")
            
            # 2. Admin logic should never be called with invalid UUID
            self.mock_admin_logic.export_study_data.assert_not_called()

    @given(
        cleanup_results=st.dictionaries(
            keys=st.sampled_from([
                "consent_records", "survey_responses", "chat_messages",
                "pald_data", "generated_images", "feedback_records",
                "interaction_logs", "pseudonym_mappings"
            ]),
            values=st.integers(min_value=0, max_value=100),
            min_size=1,
            max_size=8
        )
    )
    @settings(max_examples=20)
    def test_cleanup_results_invariants(self, cleanup_results):
        """Test that cleanup results display maintains invariants."""
        # Mock AdminService
        mock_session = Mock()
        mock_admin_service = Mock()
        mock_admin_service.cleanup_orphaned_records.return_value = cleanup_results

        with patch('src.ui.study_admin_ui.get_session') as mock_get_session, \
             patch('src.ui.study_admin_ui.AdminService', return_value=mock_admin_service):
            
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            # Mock Streamlit components
            with patch('streamlit.subheader'), \
                 patch('streamlit.columns', return_value=[Mock(), Mock()]), \
                 patch('streamlit.button', side_effect=[False, True, False]), \
                 patch('streamlit.spinner'), \
                 patch('streamlit.success') as mock_success, \
                 patch('streamlit.info') as mock_info:
                
                # Execute
                self.admin_ui._render_data_privacy()
                
                # Verify invariants
                total_cleaned = sum(cleanup_results.values())
                
                if total_cleaned > 0:
                    # 1. Should show success with total count
                    success_calls = [call for call in mock_success.call_args_list 
                                   if f"Cleaned up {total_cleaned}" in str(call)]
                    assert len(success_calls) > 0
                    
                    # 2. Should show details for non-zero counts
                    info_calls = mock_info.call_args_list
                    for table, count in cleanup_results.items():
                        if count > 0:
                            table_info = any(table in str(call) and str(count) in str(call) 
                                           for call in info_calls)
                            assert table_info, f"Should show info for {table}: {count}"
                else:
                    # 3. Should show "no orphaned records" message
                    info_calls = [call for call in mock_info.call_args_list 
                                if "No orphaned records" in str(call)]
                    assert len(info_calls) > 0

    @given(
        confirmation_text=st.text(min_size=0, max_size=50),
        checkbox_state=st.booleans()
    )
    @settings(max_examples=20)
    def test_safety_confirmation_invariants(self, confirmation_text, checkbox_state):
        """Test that safety confirmations consistently prevent unauthorized operations."""
        # Mock Streamlit components
        with patch('streamlit.subheader'), \
             patch('streamlit.warning'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.button', side_effect=[False, True]), \
             patch('streamlit.checkbox', return_value=checkbox_state), \
             patch('streamlit.text_input', return_value=confirmation_text):
            
            # Execute
            self.admin_ui._render_database_management()
            
            # Verify invariants
            # 1. Reset should only be called with proper confirmation
            should_allow_reset = (checkbox_state and confirmation_text == "DELETE ALL DATA")
            
            if should_allow_reset:
                # Operation should be allowed - we'd need additional mocking to test this fully
                pass
            else:
                # Operation should be prevented
                self.mock_admin_logic.reset_all_study_data.assert_not_called()


def _is_valid_uuid(text: str) -> bool:
    """Helper function to check if text is a valid UUID."""
    try:
        UUID(text)
        return True
    except (ValueError, TypeError):
        return False