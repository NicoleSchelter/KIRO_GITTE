"""
Unit tests for PALD diff calculation and persistence system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.logic.pald_diff_calculation import (
    PALDDiffCalculator,
    PALDPersistenceManager,
    PALDDiffResult,
    PALDArtifact,
    FieldStatus
)


class TestPALDDiffCalculator:
    """Test PALD diff calculator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = PALDDiffCalculator()
        
        # Sample PALD data for testing
        self.description_pald = {
            "global_design_level": {
                "type": "human"
            },
            "middle_design_level": {
                "role": "teacher",
                "competence": 7
            },
            "detailed_level": {
                "age": 30,
                "gender": "female",
                "clothing": "professional suit"
            }
        }
        
        self.embodiment_pald = {
            "global_design_level": {
                "type": "human"
            },
            "middle_design_level": {
                "role": "teacher",
                "competence": 6,  # Different value
                "lifelikeness": 5  # New field (hallucination)
            },
            "detailed_level": {
                "age": 30,
                "gender": "female"
                # Missing clothing field
            }
        }
    
    def test_calculate_diff_basic(self):
        """Test basic diff calculation."""
        result = self.calculator.calculate_diff(self.description_pald, self.embodiment_pald)
        
        assert isinstance(result, PALDDiffResult)
        assert isinstance(result.matches, dict)
        assert isinstance(result.hallucinations, dict)
        assert isinstance(result.missing_fields, dict)
        assert 0.0 <= result.similarity_score <= 1.0
        assert isinstance(result.summary, str)
    
    def test_calculate_diff_matches(self):
        """Test identification of matching fields."""
        result = self.calculator.calculate_diff(self.description_pald, self.embodiment_pald)
        
        # Should identify matching fields
        assert "global_design_level.type" in result.matches
        assert "middle_design_level.role" in result.matches
        assert "detailed_level.age" in result.matches
        assert "detailed_level.gender" in result.matches
        
        # Check match values
        type_match = result.matches["global_design_level.type"]
        assert type_match["description"] == "human"
        assert type_match["embodiment"] == "human"
    
    def test_calculate_diff_hallucinations(self):
        """Test identification of hallucinated fields."""
        result = self.calculator.calculate_diff(self.description_pald, self.embodiment_pald)
        
        # Should identify hallucinated field
        assert "middle_design_level.lifelikeness" in result.hallucinations
        
        hallucination = result.hallucinations["middle_design_level.lifelikeness"]
        assert hallucination["description"] is None
        assert hallucination["embodiment"] == 5
        assert "not in description" in hallucination["reason"]
    
    def test_calculate_diff_missing_fields(self):
        """Test identification of missing fields."""
        result = self.calculator.calculate_diff(self.description_pald, self.embodiment_pald)
        
        # Should identify missing field
        assert "detailed_level.clothing" in result.missing_fields
        
        missing = result.missing_fields["detailed_level.clothing"]
        assert missing["description"] == "professional suit"
        assert missing["embodiment"] is None
        assert "missing in embodiment" in missing["reason"]
    
    def test_calculate_diff_identical_palds(self):
        """Test diff calculation with identical PALDs."""
        result = self.calculator.calculate_diff(self.description_pald, self.description_pald)
        
        assert len(result.hallucinations) == 0
        assert len(result.missing_fields) == 0
        assert len(result.matches) > 0
        assert result.similarity_score == 1.0
        assert "High consistency" in result.summary
    
    def test_calculate_diff_empty_palds(self):
        """Test diff calculation with empty PALDs."""
        result = self.calculator.calculate_diff({}, {})
        
        assert len(result.matches) == 0
        assert len(result.hallucinations) == 0
        assert len(result.missing_fields) == 0
        assert result.similarity_score == 1.0
        assert "No PALD data to compare" in result.summary
    
    def test_classify_field_status_match(self):
        """Test field status classification for matches."""
        status = self.calculator.classify_field_status("test_field", "value", "value")
        assert status == FieldStatus.MATCH
        
        # Test case-insensitive string matching
        status = self.calculator.classify_field_status("test_field", "Value", "value")
        assert status == FieldStatus.MATCH
        
        # Test numeric matching with tolerance
        status = self.calculator.classify_field_status("test_field", 5, 5)
        assert status == FieldStatus.MATCH
        
        status = self.calculator.classify_field_status("test_field", 5, 6)
        assert status == FieldStatus.MATCH  # Within tolerance
    
    def test_classify_field_status_hallucination(self):
        """Test field status classification for hallucinations."""
        # Embodiment has value, description doesn't
        status = self.calculator.classify_field_status("test_field", None, "value")
        assert status == FieldStatus.HALLUCINATION
        
        status = self.calculator.classify_field_status("test_field", "", "value")
        assert status == FieldStatus.HALLUCINATION
    
    def test_classify_field_status_missing(self):
        """Test field status classification for missing fields."""
        # Description has value, embodiment doesn't
        status = self.calculator.classify_field_status("test_field", "value", None)
        assert status == FieldStatus.MISSING
        
        status = self.calculator.classify_field_status("test_field", "value", "")
        assert status == FieldStatus.MISSING
    
    def test_classify_field_status_both_empty(self):
        """Test field status classification when both are empty."""
        status = self.calculator.classify_field_status("test_field", None, None)
        assert status == FieldStatus.MATCH
        
        status = self.calculator.classify_field_status("test_field", "", "")
        assert status == FieldStatus.MATCH
    
    def test_get_field_paths(self):
        """Test field path extraction."""
        paths = self.calculator._get_field_paths(self.description_pald)
        
        expected_paths = {
            "global_design_level",
            "global_design_level.type",
            "middle_design_level",
            "middle_design_level.role",
            "middle_design_level.competence",
            "detailed_level",
            "detailed_level.age",
            "detailed_level.gender",
            "detailed_level.clothing"
        }
        
        assert paths == expected_paths
    
    def test_get_value_by_path(self):
        """Test value retrieval by path."""
        value = self.calculator._get_value_by_path(self.description_pald, "global_design_level.type")
        assert value == "human"
        
        value = self.calculator._get_value_by_path(self.description_pald, "detailed_level.age")
        assert value == 30
        
        value = self.calculator._get_value_by_path(self.description_pald, "nonexistent.path")
        assert value is None
    
    def test_has_meaningful_value(self):
        """Test meaningful value detection."""
        assert self.calculator._has_meaningful_value("test") is True
        assert self.calculator._has_meaningful_value(42) is True
        assert self.calculator._has_meaningful_value({"key": "value"}) is True
        assert self.calculator._has_meaningful_value(["item"]) is True
        
        assert self.calculator._has_meaningful_value(None) is False
        assert self.calculator._has_meaningful_value("") is False
        assert self.calculator._has_meaningful_value("   ") is False
        assert self.calculator._has_meaningful_value({}) is False
        assert self.calculator._has_meaningful_value([]) is False
    
    def test_values_match(self):
        """Test value matching logic."""
        # Exact matches
        assert self.calculator._values_match("test", "test") is True
        assert self.calculator._values_match(42, 42) is True
        
        # Case-insensitive string matching
        assert self.calculator._values_match("Test", "test") is True
        assert self.calculator._values_match("  Test  ", "test") is True
        
        # Numeric tolerance
        assert self.calculator._values_match(5, 5) is True
        assert self.calculator._values_match(5, 6) is True  # Within tolerance
        assert self.calculator._values_match(5, 7) is False  # Outside tolerance
        
        # Non-matches
        assert self.calculator._values_match("test", "other") is False
        assert self.calculator._values_match(5, "test") is False
    
    def test_is_more_specific(self):
        """Test specificity comparison."""
        # String length comparison
        assert self.calculator._is_more_specific("longer string", "short") is True
        assert self.calculator._is_more_specific("short", "longer string") is False
        
        # Dict size comparison
        assert self.calculator._is_more_specific({"a": 1, "b": 2}, {"a": 1}) is True
        assert self.calculator._is_more_specific({"a": 1}, {"a": 1, "b": 2}) is False
    
    def test_calculate_similarity_score(self):
        """Test similarity score calculation."""
        all_paths = {"field1", "field2", "field3", "field4"}
        
        # Perfect match
        matches = {"field1": {}, "field2": {}, "field3": {}, "field4": {}}
        score = self.calculator._calculate_similarity_score(matches, {}, {}, all_paths)
        assert score == 1.0
        
        # Some hallucinations and missing fields
        matches = {"field1": {}, "field2": {}}
        hallucinations = {"field3": {}}
        missing = {"field4": {}}
        score = self.calculator._calculate_similarity_score(matches, hallucinations, missing, all_paths)
        assert 0.0 <= score <= 1.0
        assert score < 1.0  # Should be less than perfect
    
    def test_generate_diff_summary(self):
        """Test diff summary generation."""
        matches = {"field1": {}, "field2": {}}
        hallucinations = {"field3": {}}
        missing = {"field4": {}}
        
        summary = self.calculator.generate_diff_summary(matches, hallucinations, missing, 0.75)
        
        assert "Similarity: 75.0%" in summary
        assert "2 matching fields" in summary
        assert "1 potential hallucinations" in summary
        assert "1 missing fields" in summary
        assert "Moderate consistency" in summary
    
    def test_calculate_diff_error_handling(self):
        """Test error handling in diff calculation."""
        # Test with invalid input
        with patch.object(self.calculator, '_get_field_paths', side_effect=Exception("Test error")):
            result = self.calculator.calculate_diff({}, {})
            
            assert result.similarity_score == 0.0
            assert "Error calculating diff" in result.summary
            assert result.metadata["error"] is True


class TestPALDPersistenceManager:
    """Test PALD persistence manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = PALDPersistenceManager()
        
        self.sample_pald_light = {
            "global_design_level": {"type": "human"},
            "detailed_level": {"age": 30, "gender": "female"}
        }
        
        self.sample_diff_result = PALDDiffResult(
            matches={"field1": {"description": "value", "embodiment": "value"}},
            hallucinations={},
            missing_fields={},
            similarity_score=1.0,
            field_classifications={"field1": FieldStatus.MATCH},
            summary="Perfect match"
        )
    
    def test_create_artifact(self):
        """Test artifact creation."""
        artifact_id = self.manager.create_artifact(
            session_id="test_session",
            user_id="test_user",
            description_text="A friendly teacher",
            embodiment_caption="The teacher smiles",
            pald_light=self.sample_pald_light
        )
        
        assert artifact_id is not None
        assert artifact_id in self.manager.artifacts
        
        artifact = self.manager.artifacts[artifact_id]
        assert artifact.session_id == "test_session"
        assert artifact.description_text == "A friendly teacher"
        assert artifact.embodiment_caption == "The teacher smiles"
        assert artifact.pald_light == self.sample_pald_light
        assert artifact.user_pseudonym.startswith("user_")
        assert len(artifact.user_pseudonym) == 21  # "user_" + 16 char hash
    
    def test_create_artifact_with_diff(self):
        """Test artifact creation with diff result."""
        artifact_id = self.manager.create_artifact(
            session_id="test_session",
            user_id="test_user",
            description_text="A teacher",
            embodiment_caption=None,
            pald_light=self.sample_pald_light,
            pald_diff=self.sample_diff_result
        )
        
        artifact = self.manager.artifacts[artifact_id]
        assert artifact.pald_diff == self.sample_diff_result
    
    def test_get_artifact(self):
        """Test artifact retrieval."""
        artifact_id = self.manager.create_artifact(
            session_id="test_session",
            user_id="test_user",
            description_text="A teacher",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        retrieved = self.manager.get_artifact(artifact_id)
        assert retrieved is not None
        assert retrieved.artifact_id == artifact_id
        
        # Test non-existent artifact
        assert self.manager.get_artifact("nonexistent") is None
    
    def test_get_artifacts_by_session(self):
        """Test retrieving artifacts by session."""
        # Create artifacts for different sessions
        artifact1 = self.manager.create_artifact(
            session_id="session1",
            user_id="user1",
            description_text="Teacher 1",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        artifact2 = self.manager.create_artifact(
            session_id="session1",
            user_id="user2",
            description_text="Teacher 2",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        artifact3 = self.manager.create_artifact(
            session_id="session2",
            user_id="user1",
            description_text="Teacher 3",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        session1_artifacts = self.manager.get_artifacts_by_session("session1")
        assert len(session1_artifacts) == 2
        assert all(a.session_id == "session1" for a in session1_artifacts)
        
        session2_artifacts = self.manager.get_artifacts_by_session("session2")
        assert len(session2_artifacts) == 1
        assert session2_artifacts[0].session_id == "session2"
    
    def test_get_artifacts_by_pseudonym(self):
        """Test retrieving artifacts by user pseudonym."""
        # Create artifacts for same user
        artifact1 = self.manager.create_artifact(
            session_id="session1",
            user_id="test_user",
            description_text="Teacher 1",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        artifact2 = self.manager.create_artifact(
            session_id="session2",
            user_id="test_user",
            description_text="Teacher 2",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        # Different user
        artifact3 = self.manager.create_artifact(
            session_id="session1",
            user_id="other_user",
            description_text="Teacher 3",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        # Get pseudonym from first artifact
        pseudonym = self.manager.artifacts[artifact1].user_pseudonym
        
        user_artifacts = self.manager.get_artifacts_by_pseudonym(pseudonym)
        assert len(user_artifacts) == 2
        assert all(a.user_pseudonym == pseudonym for a in user_artifacts)
    
    def test_update_artifact_diff(self):
        """Test updating artifact with diff results."""
        artifact_id = self.manager.create_artifact(
            session_id="test_session",
            user_id="test_user",
            description_text="A teacher",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        # Initially no diff
        artifact = self.manager.artifacts[artifact_id]
        assert artifact.pald_diff is None
        
        # Update with diff
        success = self.manager.update_artifact_diff(artifact_id, self.sample_diff_result)
        assert success is True
        
        # Check diff was updated
        artifact = self.manager.artifacts[artifact_id]
        assert artifact.pald_diff == self.sample_diff_result
        
        # Test updating non-existent artifact
        success = self.manager.update_artifact_diff("nonexistent", self.sample_diff_result)
        assert success is False
    
    def test_export_artifacts(self):
        """Test artifact export functionality."""
        # Create test artifacts
        artifact1 = self.manager.create_artifact(
            session_id="session1",
            user_id="user1",
            description_text="Teacher 1",
            embodiment_caption="Caption 1",
            pald_light=self.sample_pald_light,
            pald_diff=self.sample_diff_result
        )
        
        artifact2 = self.manager.create_artifact(
            session_id="session2",
            user_id="user2",
            description_text="Teacher 2",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        # Export all artifacts
        exported = self.manager.export_artifacts()
        assert len(exported) == 2
        
        # Check exported structure
        export1 = exported[0]
        assert "artifact_id" in export1
        assert "session_id" in export1
        assert "user_pseudonym" in export1
        assert "pald_light" in export1
        assert "input_ids" in export1
        
        # Check PII is excluded
        assert "description_text" not in export1
        assert "embodiment_caption" not in export1
        
        # Export with session filter
        filtered = self.manager.export_artifacts(session_ids=["session1"])
        assert len(filtered) == 1
        assert filtered[0]["session_id"] == "session1"
    
    def test_cleanup_old_artifacts(self):
        """Test cleanup of old artifacts."""
        # Create artifacts with different ages
        artifact1 = self.manager.create_artifact(
            session_id="session1",
            user_id="user1",
            description_text="Recent",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        artifact2 = self.manager.create_artifact(
            session_id="session2",
            user_id="user2",
            description_text="Old",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        # Manually set old creation time
        old_time = datetime.now() - timedelta(days=100)
        self.manager.artifacts[artifact2].created_at = old_time
        
        # Cleanup artifacts older than 90 days
        cleaned_count = self.manager.cleanup_old_artifacts(older_than_days=90)
        
        assert cleaned_count == 1
        assert artifact1 in self.manager.artifacts  # Recent artifact remains
        assert artifact2 not in self.manager.artifacts  # Old artifact removed
    
    def test_get_statistics(self):
        """Test statistics generation."""
        # Empty manager
        stats = self.manager.get_statistics()
        assert stats["total_artifacts"] == 0
        assert stats["unique_sessions"] == 0
        assert stats["unique_users"] == 0
        
        # Create some artifacts
        self.manager.create_artifact(
            session_id="session1",
            user_id="user1",
            description_text="Teacher 1",
            embodiment_caption=None,
            pald_light=self.sample_pald_light,
            pald_diff=self.sample_diff_result
        )
        
        self.manager.create_artifact(
            session_id="session1",
            user_id="user2",
            description_text="Teacher 2",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        self.manager.create_artifact(
            session_id="session2",
            user_id="user1",
            description_text="Teacher 3",
            embodiment_caption=None,
            pald_light=self.sample_pald_light
        )
        
        stats = self.manager.get_statistics()
        assert stats["total_artifacts"] == 3
        assert stats["unique_sessions"] == 2
        assert stats["unique_users"] == 2
        assert stats["artifacts_with_diffs"] == 1
        assert "date_range" in stats
    
    def test_generate_pseudonym_consistency(self):
        """Test that pseudonym generation is consistent for same user."""
        pseudonym1 = self.manager._generate_pseudonym("test_user")
        pseudonym2 = self.manager._generate_pseudonym("test_user")
        
        assert pseudonym1 == pseudonym2
        assert pseudonym1.startswith("user_")
        
        # Different users should have different pseudonyms
        pseudonym3 = self.manager._generate_pseudonym("other_user")
        assert pseudonym1 != pseudonym3
    
    def test_hash_text(self):
        """Test text hashing functionality."""
        hash1 = self.manager._hash_text("test text")
        hash2 = self.manager._hash_text("test text")
        
        assert hash1 == hash2
        assert len(hash1) == 16
        
        # Different text should have different hash
        hash3 = self.manager._hash_text("different text")
        assert hash1 != hash3
        
        # Empty text
        hash_empty = self.manager._hash_text("")
        assert hash_empty == ""
    
    def test_serialize_diff_result(self):
        """Test diff result serialization."""
        serialized = self.manager._serialize_diff_result(self.sample_diff_result)
        
        assert "matches" in serialized
        assert "hallucinations" in serialized
        assert "missing_fields" in serialized
        assert "similarity_score" in serialized
        assert "field_classifications" in serialized
        assert "summary" in serialized
        assert "metadata" in serialized
        
        # Check field classifications are serialized as strings
        assert serialized["field_classifications"]["field1"] == "match"


if __name__ == "__main__":
    pytest.main([__file__])