"""
Basic migration tests for PALD Enhancement tables.
Tests table creation, indexes, and basic CRUD operations.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import text
from src.data.database import get_session
from src.data.models import (
    PALDSchemaFieldCandidate,
    PALDProcessingLog,
    BiasAnalysisJob,
    BiasAnalysisResult,
    BiasAnalysisJobStatus
)


class TestPALDEnhancementTables:
    """Test PALD Enhancement database tables."""

    def test_schema_field_candidates_table_exists(self):
        """Test that schema_field_candidates table exists and has correct structure."""
        with get_session() as session:
            # Test table exists
            result = session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = 'schema_field_candidates'"
            ))
            assert result.fetchone() is not None

            # Test indexes exist
            indexes = session.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'schema_field_candidates'"
            )).fetchall()
            index_names = [idx[0] for idx in indexes]
            
            assert 'idx_schema_field_name' in index_names
            assert 'idx_schema_field_threshold' in index_names
            assert 'idx_schema_field_added' in index_names

    def test_schema_field_candidate_crud(self):
        """Test basic CRUD operations on schema field candidates."""
        with get_session() as session:
            # Create
            candidate = PALDSchemaFieldCandidate(
                field_name="test_field",
                field_category="test",
                mention_count=1
            )
            session.add(candidate)
            session.flush()
            
            candidate_id = candidate.id
            assert candidate_id is not None

            # Read
            retrieved = session.query(PALDSchemaFieldCandidate).filter(
                PALDSchemaFieldCandidate.id == candidate_id
            ).first()
            assert retrieved is not None
            assert retrieved.field_name == "test_field"
            assert retrieved.mention_count == 1

            # Update
            retrieved.mention_count = 5
            retrieved.threshold_reached = True
            session.flush()

            updated = session.query(PALDSchemaFieldCandidate).filter(
                PALDSchemaFieldCandidate.id == candidate_id
            ).first()
            assert updated.mention_count == 5
            assert updated.threshold_reached is True

            # Delete
            session.delete(updated)
            session.flush()

            deleted = session.query(PALDSchemaFieldCandidate).filter(
                PALDSchemaFieldCandidate.id == candidate_id
            ).first()
            assert deleted is None

