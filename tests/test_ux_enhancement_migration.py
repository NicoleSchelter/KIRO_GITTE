"""
Tests for UX enhancement database migration.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.data.models import Base


class TestUXEnhancementMigration:
    """Test UX enhancement database migration."""

    def test_migration_creates_tables(self):
        """Test that migration creates all required tables."""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        # Check that all UX enhancement tables exist
        with engine.connect() as conn:
            # Check image_processing_results table
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='image_processing_results'"
            ))
            assert result.fetchone() is not None
            
            # Check image_corrections table
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='image_corrections'"
            ))
            assert result.fetchone() is not None
            
            # Check prerequisite_check_results table
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='prerequisite_check_results'"
            ))
            assert result.fetchone() is not None
            
            # Check tooltip_interactions table
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tooltip_interactions'"
            ))
            assert result.fetchone() is not None
            
            # Check ux_audit_logs table
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ux_audit_logs'"
            ))
            assert result.fetchone() is not None

    def test_table_columns_exist(self):
        """Test that tables have the expected columns."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        with engine.connect() as conn:
            # Test image_processing_results columns
            result = conn.execute(text("PRAGMA table_info(image_processing_results)"))
            columns = [row[1] for row in result.fetchall()]
            expected_columns = [
                'id', 'user_id', 'original_image_path', 'processed_image_path',
                'processing_method', 'status', 'confidence_score', 'processing_time_ms',
                'quality_issues', 'person_count', 'quality_score', 'created_at', 'updated_at'
            ]
            for col in expected_columns:
                assert col in columns, f"Column {col} missing from image_processing_results"
            
            # Test prerequisite_check_results columns
            result = conn.execute(text("PRAGMA table_info(prerequisite_check_results)"))
            columns = [row[1] for row in result.fetchall()]
            expected_columns = [
                'id', 'user_id', 'operation_name', 'checker_name', 'check_type',
                'status', 'message', 'details', 'resolution_steps', 'check_time_ms',
                'confidence_score', 'cached', 'created_at'
            ]
            for col in expected_columns:
                assert col in columns, f"Column {col} missing from prerequisite_check_results"

    def test_foreign_key_relationships(self):
        """Test that foreign key relationships work correctly."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            from src.data.models import User, ImageProcessingResult, ImageCorrection
            
            # Create a test user
            user = User(
                username="testuser",
                password_hash="hash",
                pseudonym="test_pseudo",
                role="participant"
            )
            session.add(user)
            session.commit()
            
            # Create an image processing result
            result = ImageProcessingResult(
                user_id=user.id,
                original_image_path="/test/path.jpg",
                processing_method="test",
                status="pending"
            )
            session.add(result)
            session.commit()
            
            # Create an image correction
            correction = ImageCorrection(
                processing_result_id=result.id,
                user_id=user.id,
                correction_action="accept_processed"
            )
            session.add(correction)
            session.commit()
            
            # Test relationships
            assert result.user == user
            assert correction.user == user
            assert correction.processing_result == result
            assert len(result.corrections) == 1
            assert result.corrections[0] == correction
            
        finally:
            session.close()

    def test_json_columns_work(self):
        """Test that JSON columns can store and retrieve data."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            from src.data.models import User, ImageProcessingResult, PrerequisiteCheckResult
            
            # Create a test user
            user = User(
                username="testuser",
                password_hash="hash",
                pseudonym="test_pseudo",
                role="participant"
            )
            session.add(user)
            session.commit()
            
            # Test JSON column in ImageProcessingResult
            result = ImageProcessingResult(
                user_id=user.id,
                original_image_path="/test/path.jpg",
                processing_method="test",
                status="pending",
                quality_issues=["blur_detected", "noise_detected"]
            )
            session.add(result)
            session.commit()
            
            # Retrieve and verify JSON data
            retrieved_result = session.query(ImageProcessingResult).first()
            assert retrieved_result.quality_issues == ["blur_detected", "noise_detected"]
            
            # Test JSON column in PrerequisiteCheckResult
            prereq_result = PrerequisiteCheckResult(
                user_id=user.id,
                operation_name="test_op",
                checker_name="test_checker",
                check_type="required",
                status="passed",
                message="Test message",
                resolution_steps=["Step 1", "Step 2", "Step 3"]
            )
            session.add(prereq_result)
            session.commit()
            
            # Retrieve and verify JSON data
            retrieved_prereq = session.query(PrerequisiteCheckResult).first()
            assert retrieved_prereq.resolution_steps == ["Step 1", "Step 2", "Step 3"]
            
        finally:
            session.close()

    def test_enum_validation_works(self):
        """Test that enum validation works correctly."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            from src.data.models import (
                User, ImageProcessingResult, ImageProcessingResultStatus,
                PrerequisiteCheckResult, PrerequisiteCheckResultStatus
            )
            
            # Create a test user
            user = User(
                username="testuser",
                password_hash="hash",
                pseudonym="test_pseudo",
                role="participant"
            )
            session.add(user)
            session.commit()
            
            # Test valid enum value
            result = ImageProcessingResult(
                user_id=user.id,
                original_image_path="/test/path.jpg",
                processing_method="test",
                status=ImageProcessingResultStatus.SUCCESS.value
            )
            session.add(result)
            session.commit()
            
            # Verify the value was stored correctly
            retrieved_result = session.query(ImageProcessingResult).first()
            assert retrieved_result.status == ImageProcessingResultStatus.SUCCESS.value
            
            # Test that invalid enum values raise validation errors
            with pytest.raises(ValueError, match="Invalid status"):
                ImageProcessingResult(
                    user_id=user.id,
                    original_image_path="/test/path2.jpg",
                    processing_method="test",
                    status="invalid_status"
                )
            
        finally:
            session.close()