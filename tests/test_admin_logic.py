"""
Unit tests for AdminLogic class.
Tests database initialization, reset operations, and data integrity validation.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

from src.logic.admin_logic import AdminLogic, InitializationResult, ResetResult, ValidationResult, ExportResult


class TestAdminLogic:
    """Test cases for AdminLogic class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_db_manager._initialized = False
        self.mock_db_manager.engine = Mock()
        
        self.admin_logic = AdminLogic(self.mock_db_manager)

    def test_initialize_database_schema_success(self):
        """Test successful database schema initialization."""
        # Setup
        self.mock_db_manager._initialized = False
        
        with patch('src.logic.admin_logic.Base') as mock_base, \
             patch('src.logic.admin_logic.get_session') as mock_get_session:
            
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock table existence check - simulate no existing tables
            mock_session.execute.side_effect = Exception("Table doesn't exist")
            
            mock_base.metadata.tables.keys.return_value = ['pseudonyms', 'study_consent_records']
            mock_base.metadata.create_all = Mock()

            # Execute
            result = self.admin_logic.initialize_database_schema()

            # Verify
            assert isinstance(result, InitializationResult)
            assert result.success is True
            assert len(result.tables_created) == 2
            assert 'pseudonyms' in result.tables_created
            assert 'study_consent_records' in result.tables_created
            assert len(result.errors) == 0
            assert isinstance(result.timestamp, datetime)
            
            # Verify database manager was initialized
            self.mock_db_manager.initialize.assert_called_once()
            mock_base.metadata.create_all.assert_called_once_with(bind=self.mock_db_manager.engine)

    def test_initialize_database_schema_tables_exist(self):
        """Test database initialization when tables already exist."""
        # Setup
        self.mock_db_manager._initialized = True
        
        with patch('src.logic.admin_logic.Base') as mock_base, \
             patch('src.logic.admin_logic.get_session') as mock_get_session:
            
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock table existence check - simulate all tables exist
            mock_session.execute.return_value = Mock()
            
            mock_base.metadata.tables.keys.return_value = ['pseudonyms', 'study_consent_records']
            mock_base.metadata.create_all = Mock()

            # Execute
            result = self.admin_logic.initialize_database_schema()

            # Verify
            assert result.success is True
            assert len(result.tables_created) == 0  # No new tables created
            assert len(result.errors) == 0
            
            # Database manager should not be initialized again
            self.mock_db_manager.initialize.assert_not_called()

    def test_initialize_database_schema_failure(self):
        """Test database initialization failure."""
        # Setup
        self.mock_db_manager.initialize.side_effect = Exception("Database connection failed")
        
        # Execute
        result = self.admin_logic.initialize_database_schema()

        # Verify
        assert result.success is False
        assert len(result.tables_created) == 0
        assert len(result.errors) == 1
        assert "Database initialization failed" in result.errors[0]

    def test_reset_all_study_data_success(self):
        """Test successful database reset."""
        # Setup
        with patch('src.logic.admin_logic.Base') as mock_base:
            mock_base.metadata.tables.keys.return_value = ['pseudonyms', 'study_consent_records', 'chat_messages']
            mock_base.metadata.drop_all = Mock()
            mock_base.metadata.create_all = Mock()

            # Execute
            result = self.admin_logic.reset_all_study_data()

            # Verify
            assert isinstance(result, ResetResult)
            assert result.success is True
            assert len(result.tables_dropped) == 3
            assert len(result.tables_recreated) == 3
            assert 'pseudonyms' in result.tables_dropped
            assert 'pseudonyms' in result.tables_recreated
            assert len(result.errors) == 0
            
            mock_base.metadata.drop_all.assert_called_once_with(bind=self.mock_db_manager.engine)
            mock_base.metadata.create_all.assert_called_once_with(bind=self.mock_db_manager.engine)

    def test_reset_all_study_data_failure(self):
        """Test database reset failure."""
        # Setup
        with patch('src.logic.admin_logic.Base') as mock_base:
            mock_base.metadata.tables.keys.return_value = ['pseudonyms']
            mock_base.metadata.drop_all.side_effect = Exception("Drop failed")

            # Execute
            result = self.admin_logic.reset_all_study_data()

            # Verify
            assert result.success is False
            assert len(result.tables_dropped) == 0
            assert len(result.tables_recreated) == 0
            assert len(result.errors) == 1
            assert "Database reset failed" in result.errors[0]

    def test_validate_database_integrity_success(self):
        """Test successful database integrity validation."""
        # Setup
        with patch('src.logic.admin_logic.Base') as mock_base, \
             patch('src.logic.admin_logic.get_session') as mock_get_session:
            
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            mock_base.metadata.tables.keys.return_value = ['pseudonyms', 'study_consent_records']
            
            # Mock table existence checks - all tables exist
            mock_session.execute.return_value = Mock()
            
            # Mock constraint checks - no violations
            with patch.object(self.admin_logic, '_check_study_constraints', return_value=[]):
                # Execute
                result = self.admin_logic.validate_database_integrity()

                # Verify
                assert isinstance(result, ValidationResult)
                assert result.success is True
                assert len(result.constraint_violations) == 0
                assert len(result.missing_tables) == 0
                assert len(result.errors) == 0

    def test_validate_database_integrity_missing_tables(self):
        """Test database validation with missing tables."""
        # Setup
        with patch('src.logic.admin_logic.Base') as mock_base, \
             patch('src.logic.admin_logic.get_session') as mock_get_session:
            
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            mock_base.metadata.tables.keys.return_value = ['pseudonyms', 'study_consent_records']
            
            # Mock table existence checks - one table missing
            def mock_execute(query):
                if 'pseudonyms' in query:
                    return Mock()
                else:
                    raise Exception("Table doesn't exist")
            
            mock_session.execute.side_effect = mock_execute

            # Execute
            result = self.admin_logic.validate_database_integrity()

            # Verify
            assert result.success is False
            assert len(result.missing_tables) == 1
            assert 'study_consent_records' in result.missing_tables

    def test_check_study_constraints_no_violations(self):
        """Test study constraints check with no violations."""
        # Setup
        mock_session = Mock()
        mock_session.execute.return_value.scalar.return_value = 0

        # Execute
        violations = self.admin_logic._check_study_constraints(mock_session)

        # Verify
        assert len(violations) == 0

    def test_check_study_constraints_with_violations(self):
        """Test study constraints check with violations found."""
        # Setup
        mock_session = Mock()
        
        # Mock different violation counts for different queries
        def mock_scalar():
            # Return different counts for different constraint checks
            mock_scalar.call_count = getattr(mock_scalar, 'call_count', 0) + 1
            if mock_scalar.call_count == 1:
                return 5  # orphaned consents
            elif mock_scalar.call_count == 2:
                return 0  # no orphaned surveys
            elif mock_scalar.call_count == 3:
                return 2  # orphaned chats
            else:
                return 0
        
        mock_session.execute.return_value.scalar = mock_scalar

        # Execute
        violations = self.admin_logic._check_study_constraints(mock_session)

        # Verify
        assert len(violations) >= 2
        assert any("orphaned consent records" in v for v in violations)
        assert any("orphaned chat messages" in v for v in violations)

    def test_export_study_data_success(self):
        """Test successful study data export."""
        # Setup
        pseudonym_id = uuid4()
        
        with patch('src.logic.admin_logic.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock query results
            mock_pseudonym = Mock()
            mock_pseudonym.pseudonym_id = pseudonym_id
            mock_pseudonym.pseudonym_text = "test_pseudonym"
            
            mock_session.query.return_value.filter.return_value.all.return_value = [mock_pseudonym]
            mock_session.query.return_value.all.return_value = []

            # Execute
            result = self.admin_logic.export_study_data(pseudonym_id)

            # Verify
            assert isinstance(result, ExportResult)
            assert result.success is True
            assert "pseudonyms" in result.exported_records
            assert result.exported_records["pseudonyms"] == 1
            assert len(result.errors) == 0

    def test_export_study_data_all_participants(self):
        """Test exporting data for all participants."""
        # Setup
        with patch('src.logic.admin_logic.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock multiple pseudonyms
            mock_pseudonyms = [Mock(), Mock(), Mock()]
            for i, p in enumerate(mock_pseudonyms):
                p.pseudonym_id = uuid4()
                p.pseudonym_text = f"test_pseudonym_{i}"
            
            mock_session.query.return_value.all.return_value = mock_pseudonyms

            # Execute (no pseudonym_id specified = export all)
            result = self.admin_logic.export_study_data()

            # Verify
            assert result.success is True
            assert result.exported_records["pseudonyms"] == 3

    def test_export_study_data_failure(self):
        """Test study data export failure."""
        # Setup
        with patch('src.logic.admin_logic.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            # Execute
            result = self.admin_logic.export_study_data()

            # Verify
            assert result.success is False
            assert len(result.errors) == 1
            assert "Data export failed" in result.errors[0]

    def test_delete_participant_data_success(self):
        """Test successful participant data deletion."""
        # Setup
        pseudonym_id = uuid4()
        
        with patch('src.logic.admin_logic.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock successful deletions
            mock_session.query.return_value.filter.return_value.delete.return_value = 1

            # Execute
            result = self.admin_logic.delete_participant_data(pseudonym_id)

            # Verify
            assert result is True

    def test_delete_participant_data_failure(self):
        """Test participant data deletion failure."""
        # Setup
        pseudonym_id = uuid4()
        
        with patch('src.logic.admin_logic.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")

            # Execute
            result = self.admin_logic.delete_participant_data(pseudonym_id)

            # Verify
            assert result is False

    def test_get_database_statistics_success(self):
        """Test successful database statistics retrieval."""
        # Setup
        with patch('src.logic.admin_logic.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock count queries
            mock_session.query.return_value.count.return_value = 10
            mock_session.query.return_value.filter.return_value.count.return_value = 8

            # Execute
            stats = self.admin_logic.get_database_statistics()

            # Verify
            assert "pseudonyms" in stats
            assert "consent_records" in stats
            assert "active_pseudonyms" in stats
            assert "total_study_records" in stats
            assert stats["pseudonyms"] == 10
            assert stats["active_pseudonyms"] == 8

    def test_get_database_statistics_failure(self):
        """Test database statistics retrieval failure."""
        # Setup
        with patch('src.logic.admin_logic.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")

            # Execute
            stats = self.admin_logic.get_database_statistics()

            # Verify
            assert "error" in stats
            assert "Database error" in stats["error"]