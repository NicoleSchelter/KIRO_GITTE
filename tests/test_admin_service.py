"""
Unit tests for AdminService class.
Tests table management, data export, and database maintenance operations.
"""

import json
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch, PropertyMock
from uuid import uuid4

from src.services.admin_service import AdminService


class TestAdminService:
    """Test cases for AdminService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.admin_service = AdminService(self.mock_session)

    def test_create_all_tables_success(self):
        """Test successful table creation."""
        # Setup
        with patch('src.data.models.Base') as mock_base, \
             patch('src.data.database.db_manager') as mock_db_manager:
            
            mock_db_manager._initialized = False
            mock_db_manager.engine = Mock()
            mock_base.metadata.create_all = Mock()

            # Execute
            result = self.admin_service.create_all_tables()

            # Verify
            assert result is True
            mock_db_manager.initialize.assert_called_once()
            mock_base.metadata.create_all.assert_called_once_with(bind=mock_db_manager.engine)

    def test_create_all_tables_failure(self):
        """Test table creation failure."""
        # Setup
        with patch('src.data.models.Base') as mock_base, \
             patch('src.data.database.db_manager') as mock_db_manager:
            
            mock_db_manager._initialized = True
            mock_base.metadata.create_all.side_effect = Exception("Creation failed")

            # Execute
            result = self.admin_service.create_all_tables()

            # Verify
            assert result is False

    def test_drop_all_tables_success(self):
        """Test successful table dropping."""
        # Setup
        with patch('src.data.models.Base') as mock_base, \
             patch('src.data.database.db_manager') as mock_db_manager:
            
            mock_db_manager._initialized = True
            mock_db_manager.engine = Mock()
            mock_base.metadata.drop_all = Mock()

            # Execute
            result = self.admin_service.drop_all_tables()

            # Verify
            assert result is True
            mock_base.metadata.drop_all.assert_called_once_with(bind=mock_db_manager.engine)

    def test_drop_all_tables_failure(self):
        """Test table dropping failure."""
        # Setup
        with patch('src.data.models.Base') as mock_base, \
             patch('src.data.database.db_manager') as mock_db_manager:
            
            mock_db_manager._initialized = True
            mock_base.metadata.drop_all.side_effect = Exception("Drop failed")

            # Execute
            result = self.admin_service.drop_all_tables()

            # Verify
            assert result is False

    def test_verify_foreign_key_constraints_no_violations(self):
        """Test foreign key constraint verification with no violations."""
        # Setup
        self.mock_session.execute.return_value.fetchall.return_value = []

        # Execute
        violations = self.admin_service.verify_foreign_key_constraints()

        # Verify
        assert len(violations) == 0

    def test_verify_foreign_key_constraints_with_violations(self):
        """Test foreign key constraint verification with violations."""
        # Setup
        def mock_fetchall():
            # Return different results for different queries
            mock_fetchall.call_count = getattr(mock_fetchall, 'call_count', 0) + 1
            if mock_fetchall.call_count == 1:
                # Orphaned consent records
                return [(uuid4(), uuid4()), (uuid4(), uuid4())]
            else:
                return []
        
        self.mock_session.execute.return_value.fetchall = mock_fetchall

        # Execute
        violations = self.admin_service.verify_foreign_key_constraints()

        # Verify
        assert len(violations) > 0
        assert any("orphaned consent records" in v for v in violations)

    def test_verify_foreign_key_constraints_failure(self):
        """Test foreign key constraint verification failure."""
        # Setup
        self.mock_session.execute.side_effect = Exception("Query failed")

        # Execute
        violations = self.admin_service.verify_foreign_key_constraints()

        # Verify
        assert len(violations) == 1
        assert "Constraint verification failed" in violations[0]

    def test_export_study_data_to_file_success(self):
        """Test successful data export to file."""
        # Setup
        pseudonym_id = uuid4()
        
        # Mock database objects
        from datetime import datetime
        mock_pseudonym = Mock()
        mock_pseudonym.pseudonym_id = pseudonym_id
        mock_pseudonym.pseudonym_text = "test_pseudonym"
        mock_pseudonym.pseudonym_hash = "hash123"
        mock_pseudonym.created_at = datetime(2024, 1, 1)
        mock_pseudonym.is_active = True
        
        # Mock query chains
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_pseudonym]
        mock_query.all.return_value = []
        self.mock_session.query.return_value = mock_query

        # Execute with temporary file and mock JSON dump
        with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            with patch('json.dump') as mock_json_dump:
                result = self.admin_service.export_study_data_to_file(temp_path, pseudonym_id)

                # Verify
                assert result["success"] is True
                assert result["file_path"] == temp_path
                assert result["records_exported"]["pseudonyms"] == 1
                assert len(result["errors"]) == 0
                
                # Verify JSON dump was called
                mock_json_dump.assert_called_once()

        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_export_study_data_to_file_all_data(self):
        """Test exporting all data (no specific pseudonym)."""
        # Setup
        from datetime import datetime
        mock_pseudonyms = []
        for i in range(3):
            mock_p = Mock()
            mock_p.pseudonym_id = uuid4()
            mock_p.pseudonym_text = f"test_pseudonym_{i}"
            mock_p.pseudonym_hash = f"hash{i}"
            mock_p.created_at = datetime(2024, 1, 1)
            mock_p.is_active = True
            mock_pseudonyms.append(mock_p)
        
        mock_query = Mock()
        mock_query.all.return_value = mock_pseudonyms
        self.mock_session.query.return_value = mock_query

        # Execute with temporary file and mock JSON dump
        with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            with patch('json.dump') as mock_json_dump:
                result = self.admin_service.export_study_data_to_file(temp_path)

                # Verify
                assert result["success"] is True
                assert result["records_exported"]["pseudonyms"] == 3
                
                # Verify JSON dump was called
                mock_json_dump.assert_called_once()

        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_export_study_data_to_file_unsupported_format(self):
        """Test export with unsupported format."""
        # Setup - mock empty query results to avoid iteration issues
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_query.all.return_value = []
        self.mock_session.query.return_value = mock_query
        
        # Execute
        result = self.admin_service.export_study_data_to_file("test.csv", format="csv")

        # Verify
        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert "Unsupported format" in result["errors"][0]

    def test_export_study_data_to_file_failure(self):
        """Test data export failure."""
        # Setup
        self.mock_session.query.side_effect = Exception("Database error")

        # Execute
        result = self.admin_service.export_study_data_to_file("test.json")

        # Verify
        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert "Data export failed" in result["errors"][0]

    def test_get_table_counts_success(self):
        """Test successful table count retrieval."""
        # Setup
        self.mock_session.query.return_value.count.return_value = 10

        # Execute
        counts = self.admin_service.get_table_counts()

        # Verify
        assert "pseudonyms" in counts
        assert "consent_records" in counts
        assert "survey_responses" in counts
        assert counts["pseudonyms"] == 10

    def test_get_table_counts_failure(self):
        """Test table count retrieval failure."""
        # Setup
        self.mock_session.query.side_effect = Exception("Database error")

        # Execute
        counts = self.admin_service.get_table_counts()

        # Verify
        assert "error" in counts
        assert "Database error" in counts["error"]

    def test_cleanup_orphaned_records_success(self):
        """Test successful orphaned record cleanup."""
        # Setup
        def mock_execute(query):
            # Return different rowcounts for different DELETE queries
            mock_result = Mock()
            if "consent_records" in query:
                mock_result.rowcount = 5
            elif "survey_responses" in query:
                mock_result.rowcount = 2
            else:
                mock_result.rowcount = 0
            return mock_result
        
        self.mock_session.execute.side_effect = mock_execute

        # Execute
        cleanup_counts = self.admin_service.cleanup_orphaned_records()

        # Verify
        assert cleanup_counts["consent_records"] == 5
        assert cleanup_counts["survey_responses"] == 2
        assert cleanup_counts["chat_messages"] == 0

    def test_cleanup_orphaned_records_failure(self):
        """Test orphaned record cleanup failure."""
        # Setup
        self.mock_session.execute.side_effect = Exception("Database error")

        # Execute
        cleanup_counts = self.admin_service.cleanup_orphaned_records()

        # Verify
        assert "error" in cleanup_counts
        assert "Database error" in cleanup_counts["error"]

    def test_vacuum_database_postgresql(self):
        """Test database vacuum for PostgreSQL."""
        # Setup
        self.mock_session.bind.url = "postgresql://user:pass@localhost/db"

        # Execute
        result = self.admin_service.vacuum_database()

        # Verify
        assert result is True

    def test_vacuum_database_non_postgresql(self):
        """Test database vacuum for non-PostgreSQL database."""
        # Setup
        self.mock_session.bind.url = "sqlite:///test.db"

        # Execute
        result = self.admin_service.vacuum_database()

        # Verify
        assert result is True

    def test_vacuum_database_failure(self):
        """Test database vacuum failure."""
        # Setup - make the bind property raise an exception
        type(self.mock_session).bind = PropertyMock(side_effect=Exception("URL access failed"))

        # Execute
        result = self.admin_service.vacuum_database()

        # Verify
        assert result is False