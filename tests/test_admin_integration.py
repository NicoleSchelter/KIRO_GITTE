"""
Integration tests for admin database management functionality.
Tests end-to-end database operations, reset functionality, and data integrity validation.
"""

import pytest
from datetime import datetime
from tempfile import NamedTemporaryFile
from uuid import uuid4

from src.data.database import get_session
from src.data.models import (
    Pseudonym,
    StudyConsentRecord,
    StudySurveyResponse,
    ChatMessage,
    StudyPALDData,
    GeneratedImage,
    FeedbackRecord,
    InteractionLog,
)
from src.logic.admin_logic import AdminLogic
from src.services.admin_service import AdminService
from src.services.admin_functions import (
    init_all_db,
    reset_all_study_data,
    validate_database_integrity,
    export_all_study_data,
    cleanup_orphaned_data,
    delete_participant_data,
)


@pytest.mark.integration
class TestAdminIntegration:
    """Integration test cases for admin functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Initialize database for testing
        init_result = init_all_db()
        assert init_result.success, f"Database initialization failed: {init_result.errors}"

    def teardown_method(self):
        """Clean up after tests."""
        # Reset database to clean state
        reset_result = reset_all_study_data()
        assert reset_result.success, f"Database reset failed: {reset_result.errors}"

    def test_database_initialization_and_reset_cycle(self):
        """Test complete database initialization and reset cycle."""
        # Test initialization
        init_result = init_all_db()
        assert init_result.success
        assert isinstance(init_result.timestamp, datetime)

        # Verify tables exist by creating some test data
        with get_session() as session:
            # Create a test pseudonym
            pseudonym = Pseudonym(
                pseudonym_text="test_pseudonym",
                pseudonym_hash="hash123",
                is_active=True
            )
            session.add(pseudonym)
            session.flush()
            
            # Verify it was created
            created_pseudonym = session.query(Pseudonym).filter(
                Pseudonym.pseudonym_text == "test_pseudonym"
            ).first()
            assert created_pseudonym is not None
            assert created_pseudonym.is_active is True

        # Test reset
        reset_result = reset_all_study_data()
        assert reset_result.success
        assert len(reset_result.tables_dropped) > 0
        assert len(reset_result.tables_recreated) > 0
        assert len(reset_result.tables_dropped) == len(reset_result.tables_recreated)

        # Verify data was cleared
        with get_session() as session:
            pseudonym_count = session.query(Pseudonym).count()
            assert pseudonym_count == 0

    def test_database_integrity_validation_with_clean_database(self):
        """Test database integrity validation on clean database."""
        # Validate clean database
        validation_result = validate_database_integrity()
        
        assert validation_result["success"] is True
        assert len(validation_result["constraint_violations"]) == 0
        assert len(validation_result["missing_tables"]) == 0
        assert len(validation_result["errors"]) == 0

    def test_database_integrity_validation_with_data(self):
        """Test database integrity validation with valid data."""
        # Create valid test data
        with get_session() as session:
            # Create pseudonym
            pseudonym = Pseudonym(
                pseudonym_text="test_pseudonym",
                pseudonym_hash="hash123",
                is_active=True
            )
            session.add(pseudonym)
            session.flush()
            
            # Create consent record
            consent = StudyConsentRecord(
                pseudonym_id=pseudonym.pseudonym_id,
                consent_type="data_protection",
                granted=True,
                version="1.0"
            )
            session.add(consent)
            
            # Create survey response
            survey = StudySurveyResponse(
                pseudonym_id=pseudonym.pseudonym_id,
                survey_version="1.0",
                responses={"question1": "answer1"}
            )
            session.add(survey)

        # Validate database with data
        validation_result = validate_database_integrity()
        
        assert validation_result["success"] is True
        assert len(validation_result["constraint_violations"]) == 0

    def test_export_study_data_integration(self):
        """Test complete study data export functionality."""
        # Create comprehensive test data
        with get_session() as session:
            # Create pseudonym
            pseudonym = Pseudonym(
                pseudonym_text="export_test_pseudonym",
                pseudonym_hash="export_hash123",
                is_active=True
            )
            session.add(pseudonym)
            session.flush()
            
            # Create consent records
            consent1 = StudyConsentRecord(
                pseudonym_id=pseudonym.pseudonym_id,
                consent_type="data_protection",
                granted=True,
                version="1.0"
            )
            consent2 = StudyConsentRecord(
                pseudonym_id=pseudonym.pseudonym_id,
                consent_type="ai_interaction",
                granted=True,
                version="1.0"
            )
            session.add_all([consent1, consent2])
            
            # Create survey response
            survey = StudySurveyResponse(
                pseudonym_id=pseudonym.pseudonym_id,
                survey_version="1.0",
                responses={"question1": "answer1", "question2": "answer2"}
            )
            session.add(survey)
            
            # Create chat message
            chat = ChatMessage(
                pseudonym_id=pseudonym.pseudonym_id,
                session_id=uuid4(),
                message_type="user",
                content="Test message"
            )
            session.add(chat)
            
            # Create PALD data
            pald = StudyPALDData(
                pseudonym_id=pseudonym.pseudonym_id,
                session_id=uuid4(),
                pald_content={"attribute1": "value1"},
                pald_type="input"
            )
            session.add(pald)

        # Export data to temporary file
        with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            export_result = export_all_study_data(temp_path)
            
            # Verify export success
            assert export_result["success"] is True
            assert export_result["file_path"] == temp_path
            assert export_result["records_exported"]["pseudonyms"] == 1
            assert export_result["records_exported"]["consent_records"] == 2
            assert export_result["records_exported"]["survey_responses"] == 1
            assert export_result["records_exported"]["chat_messages"] == 1
            assert export_result["records_exported"]["pald_data"] == 1
            
            # Verify file was created and contains data
            import json
            with open(temp_path, 'r') as f:
                exported_data = json.load(f)
            
            assert "pseudonyms" in exported_data
            assert "consent_records" in exported_data
            assert "survey_responses" in exported_data
            assert len(exported_data["pseudonyms"]) == 1
            assert len(exported_data["consent_records"]) == 2
            assert exported_data["pseudonyms"][0]["pseudonym_text"] == "export_test_pseudonym"

        finally:
            # Clean up
            import os
            os.unlink(temp_path)

    def test_participant_data_deletion_integration(self):
        """Test complete participant data deletion functionality."""
        # Create test data for deletion
        pseudonym_id = None
        with get_session() as session:
            # Create pseudonym
            pseudonym = Pseudonym(
                pseudonym_text="delete_test_pseudonym",
                pseudonym_hash="delete_hash123",
                is_active=True
            )
            session.add(pseudonym)
            session.flush()
            pseudonym_id = pseudonym.pseudonym_id
            
            # Create related data
            consent = StudyConsentRecord(
                pseudonym_id=pseudonym_id,
                consent_type="data_protection",
                granted=True,
                version="1.0"
            )
            survey = StudySurveyResponse(
                pseudonym_id=pseudonym_id,
                survey_version="1.0",
                responses={"question1": "answer1"}
            )
            chat = ChatMessage(
                pseudonym_id=pseudonym_id,
                session_id=uuid4(),
                message_type="user",
                content="Test message"
            )
            pald = StudyPALDData(
                pseudonym_id=pseudonym_id,
                session_id=uuid4(),
                pald_content={"attribute1": "value1"},
                pald_type="input"
            )
            session.add_all([consent, survey, chat, pald])

        # Verify data exists before deletion
        with get_session() as session:
            assert session.query(Pseudonym).filter(Pseudonym.pseudonym_id == pseudonym_id).count() == 1
            assert session.query(StudyConsentRecord).filter(StudyConsentRecord.pseudonym_id == pseudonym_id).count() == 1
            assert session.query(StudySurveyResponse).filter(StudySurveyResponse.pseudonym_id == pseudonym_id).count() == 1
            assert session.query(ChatMessage).filter(ChatMessage.pseudonym_id == pseudonym_id).count() == 1
            assert session.query(StudyPALDData).filter(StudyPALDData.pseudonym_id == pseudonym_id).count() == 1

        # Delete participant data
        deletion_success = delete_participant_data(str(pseudonym_id))
        assert deletion_success is True

        # Verify all data was deleted
        with get_session() as session:
            assert session.query(Pseudonym).filter(Pseudonym.pseudonym_id == pseudonym_id).count() == 0
            assert session.query(StudyConsentRecord).filter(StudyConsentRecord.pseudonym_id == pseudonym_id).count() == 0
            assert session.query(StudySurveyResponse).filter(StudySurveyResponse.pseudonym_id == pseudonym_id).count() == 0
            assert session.query(ChatMessage).filter(ChatMessage.pseudonym_id == pseudonym_id).count() == 0
            assert session.query(StudyPALDData).filter(StudyPALDData.pseudonym_id == pseudonym_id).count() == 0

    def test_orphaned_data_cleanup_integration(self):
        """Test orphaned data cleanup functionality."""
        # Create orphaned data scenario
        orphaned_pseudonym_id = uuid4()
        
        with get_session() as session:
            # Create valid pseudonym
            valid_pseudonym = Pseudonym(
                pseudonym_text="valid_pseudonym",
                pseudonym_hash="valid_hash",
                is_active=True
            )
            session.add(valid_pseudonym)
            session.flush()
            
            # Create valid consent record
            valid_consent = StudyConsentRecord(
                pseudonym_id=valid_pseudonym.pseudonym_id,
                consent_type="data_protection",
                granted=True,
                version="1.0"
            )
            session.add(valid_consent)
            
            # Create orphaned consent record (references non-existent pseudonym)
            orphaned_consent = StudyConsentRecord(
                pseudonym_id=orphaned_pseudonym_id,
                consent_type="ai_interaction",
                granted=True,
                version="1.0"
            )
            session.add(orphaned_consent)

        # Verify orphaned data exists
        with get_session() as session:
            total_consents = session.query(StudyConsentRecord).count()
            assert total_consents == 2

        # Clean up orphaned data
        cleanup_result = cleanup_orphaned_data()
        
        # Verify cleanup results
        assert cleanup_result["consent_records"] == 1  # One orphaned record cleaned

        # Verify only valid data remains
        with get_session() as session:
            remaining_consents = session.query(StudyConsentRecord).count()
            assert remaining_consents == 1
            
            # Verify the remaining consent belongs to valid pseudonym
            remaining_consent = session.query(StudyConsentRecord).first()
            assert remaining_consent.consent_type == "data_protection"

    def test_admin_service_table_management_integration(self):
        """Test AdminService table management operations."""
        with get_session() as session:
            admin_service = AdminService(session)
            
            # Test table count functionality
            counts = admin_service.get_table_counts()
            assert "pseudonyms" in counts
            assert "consent_records" in counts
            assert isinstance(counts["pseudonyms"], int)
            
            # Test foreign key constraint verification
            violations = admin_service.verify_foreign_key_constraints()
            assert isinstance(violations, list)
            # Should be no violations in clean database
            assert len(violations) == 0

    def test_admin_logic_statistics_integration(self):
        """Test AdminLogic database statistics functionality."""
        admin_logic = AdminLogic()
        
        # Create some test data
        with get_session() as session:
            pseudonym1 = Pseudonym(
                pseudonym_text="stats_test_1",
                pseudonym_hash="hash1",
                is_active=True
            )
            pseudonym2 = Pseudonym(
                pseudonym_text="stats_test_2",
                pseudonym_hash="hash2",
                is_active=False
            )
            session.add_all([pseudonym1, pseudonym2])
            session.flush()
            
            consent = StudyConsentRecord(
                pseudonym_id=pseudonym1.pseudonym_id,
                consent_type="data_protection",
                granted=True,
                version="1.0"
            )
            session.add(consent)

        # Get statistics
        stats = admin_logic.get_database_statistics()
        
        # Verify statistics
        assert "pseudonyms" in stats
        assert "consent_records" in stats
        assert "active_pseudonyms" in stats
        assert "total_study_records" in stats
        
        assert stats["pseudonyms"] == 2
        assert stats["consent_records"] == 1
        assert stats["active_pseudonyms"] == 1
        assert stats["total_study_records"] >= 1