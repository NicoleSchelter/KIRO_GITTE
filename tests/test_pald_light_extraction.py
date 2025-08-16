"""
Unit tests for PALD Light extraction system.
"""

import pytest
from unittest.mock import Mock, patch

from src.logic.pald_light_extraction import PALDLightExtractor, PALDLightResult


class TestPALDLightExtractor:
    """Test PALD Light extractor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PALDLightExtractor()
        
        # Mock schema for testing
        self.mock_schema = {
            "properties": {
                "global_design_level": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["human", "cartoon", "object", "animal", "fantasy_figure"]
                        },
                        "cartoon": {
                            "type": "object",
                            "properties": {
                                "animation": {
                                    "type": "string",
                                    "enum": ["animated", "static"]
                                },
                                "representation": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                },
                "middle_design_level": {
                    "type": "object",
                    "properties": {
                        "lifelikeness": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 7
                        },
                        "realism": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 7
                        },
                        "role": {
                            "type": "string"
                        },
                        "competence": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 7
                        }
                    }
                },
                "detailed_level": {
                    "type": "object",
                    "properties": {
                        "age": {
                            "type": ["string", "integer"]
                        },
                        "gender": {
                            "type": "string"
                        },
                        "clothing": {
                            "type": "string"
                        },
                        "weight": {
                            "type": "string"
                        }
                    }
                }
            }
        }
    
    def test_extract_from_description_only(self):
        """Test extraction with description text only."""
        description = "A friendly female teacher wearing a blue dress, she looks realistic and competent"
        
        with patch.object(self.extractor.schema_loader, 'load_schema', return_value=self.mock_schema):
            result = self.extractor.extract_from_text(description)
        
        assert isinstance(result, PALDLightResult)
        assert result.pald_light is not None
        assert result.extraction_confidence > 0
        assert len(result.filled_fields) > 0
        
        # Check specific extractions
        pald = result.pald_light
        assert pald.get("global_design_level", {}).get("type") == "human"
        assert pald.get("middle_design_level", {}).get("role") == "teacher"
        assert pald.get("detailed_level", {}).get("gender") == "female"
        assert "blue dress" in pald.get("detailed_level", {}).get("clothing", "")
    
    def test_extract_with_embodiment_caption(self):
        """Test extraction with both description and embodiment caption."""
        description = "Create a helpful assistant"
        embodiment_caption = "The assistant is a young man in casual clothing, very friendly"
        
        with patch.object(self.extractor.schema_loader, 'load_schema', return_value=self.mock_schema):
            result = self.extractor.extract_from_text(description, embodiment_caption)
        
        assert isinstance(result, PALDLightResult)
        pald = result.pald_light
        
        # Should extract from both texts
        assert pald.get("middle_design_level", {}).get("role") == "assistant"
        assert pald.get("detailed_level", {}).get("gender") == "male"
        assert pald.get("detailed_level", {}).get("age") == "young"
    
    def test_extract_cartoon_character(self):
        """Test extraction of cartoon character attributes."""
        description = "An animated Mickey Mouse character that moves around"
        
        with patch.object(self.extractor.schema_loader, 'load_schema', return_value=self.mock_schema):
            result = self.extractor.extract_from_text(description)
        
        pald = result.pald_light
        assert pald.get("global_design_level", {}).get("type") == "cartoon"
        
        cartoon_data = pald.get("global_design_level", {}).get("cartoon", {})
        assert cartoon_data.get("animation") == "animated"
        assert "mickey mouse" in cartoon_data.get("representation", "").lower()
    
    def test_extract_numeric_scales(self):
        """Test extraction of numeric scale values."""
        description = "A photorealistic and highly competent expert who is very skilled"
        
        with patch.object(self.extractor.schema_loader, 'load_schema', return_value=self.mock_schema):
            result = self.extractor.extract_from_text(description)
        
        pald = result.pald_light
        middle_level = pald.get("middle_design_level", {})
        
        # Should extract high values for realism/lifelikeness and competence
        assert middle_level.get("lifelikeness") == 7  # photorealistic
        assert middle_level.get("competence") >= 6  # highly competent/expert
    
    def test_extract_age_number(self):
        """Test extraction of specific age numbers."""
        description = "A 25 years old person"
        
        with patch.object(self.extractor.schema_loader, 'load_schema', return_value=self.mock_schema):
            result = self.extractor.extract_from_text(description)
        
        pald = result.pald_light
        assert pald.get("detailed_level", {}).get("age") == 25
    
    def test_extract_clothing_details(self):
        """Test extraction of clothing information."""
        description = "She is wearing a red shirt and blue jeans, dressed casually"
        
        with patch.object(self.extractor.schema_loader, 'load_schema', return_value=self.mock_schema):
            result = self.extractor.extract_from_text(description)
        
        pald = result.pald_light
        clothing = pald.get("detailed_level", {}).get("clothing", "")
        
        assert "red shirt" in clothing or "shirt" in clothing
        assert "jeans" in clothing or "blue jeans" in clothing
    
    def test_schema_validation_success(self):
        """Test successful schema validation."""
        valid_pald = {
            "global_design_level": {
                "type": "human"
            },
            "middle_design_level": {
                "lifelikeness": 5,
                "role": "teacher"
            },
            "detailed_level": {
                "age": "adult",
                "gender": "female"
            }
        }
        
        result = self.extractor.validate_extraction(valid_pald, self.mock_schema)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
    
    def test_schema_validation_type_errors(self):
        """Test schema validation with type errors."""
        invalid_pald = {
            "global_design_level": {
                "type": "human"
            },
            "middle_design_level": {
                "lifelikeness": "not_a_number",  # Should be integer
                "role": "teacher"
            }
        }
        
        result = self.extractor.validate_extraction(invalid_pald, self.mock_schema)
        
        assert result["is_valid"] is False
        assert any("type" in error for error in result["errors"])
    
    def test_schema_validation_range_errors(self):
        """Test schema validation with range errors."""
        invalid_pald = {
            "middle_design_level": {
                "lifelikeness": 10,  # Above maximum of 7
                "competence": 0      # Below minimum of 1
            }
        }
        
        result = self.extractor.validate_extraction(invalid_pald, self.mock_schema)
        
        assert result["is_valid"] is False
        assert any("above maximum" in error for error in result["errors"])
        assert any("below minimum" in error for error in result["errors"])
    
    def test_prompt_compression_basic(self):
        """Test basic prompt compression functionality."""
        pald_data = {
            "global_design_level": {
                "type": "human"
            },
            "middle_design_level": {
                "lifelikeness": 7,
                "role": "teacher"
            },
            "detailed_level": {
                "age": "adult",
                "gender": "female",
                "clothing": "blue dress"
            }
        }
        
        compressed = self.extractor.compress_for_prompt(pald_data)
        
        assert "human" in compressed
        assert "photorealistic" in compressed  # lifelikeness 7 -> photorealistic
        assert "teacher" in compressed
        assert "adult" in compressed
        assert "female" in compressed
        assert "wearing blue dress" in compressed
    
    def test_prompt_compression_length_limit(self):
        """Test that prompt compression respects length limits."""
        pald_data = {
            "detailed_level": {
                "clothing": "a very long and detailed description of clothing that goes on and on with many specific details about colors, patterns, materials, and styles that would make the prompt too long for stable diffusion to handle properly"
            }
        }
        
        compressed = self.extractor.compress_for_prompt(pald_data)
        
        # Should be truncated
        assert len(compressed) <= 200
        assert "..." in compressed
    
    def test_confidence_calculation(self):
        """Test extraction confidence calculation."""
        # High confidence case - many fields filled
        high_confidence_pald = {
            "global_design_level": {"type": "human"},
            "middle_design_level": {"role": "teacher", "lifelikeness": 5},
            "detailed_level": {"age": "adult", "gender": "female", "clothing": "dress"}
        }
        
        long_text = "A detailed description with lots of information about the character" * 10
        confidence = self.extractor._calculate_extraction_confidence(high_confidence_pald, long_text)
        
        assert confidence > 0.5
        
        # Low confidence case - few fields filled
        low_confidence_pald = {
            "global_design_level": {"type": "human"}
        }
        
        short_text = "Brief"
        confidence = self.extractor._calculate_extraction_confidence(low_confidence_pald, short_text)
        
        assert confidence < 0.5
    
    def test_filled_fields_detection(self):
        """Test detection of filled fields."""
        pald_data = {
            "global_design_level": {
                "type": "human",
                "other": None  # Should not be counted
            },
            "middle_design_level": {
                "role": "teacher",
                "empty_field": ""  # Should not be counted
            }
        }
        
        filled_fields = self.extractor._get_filled_fields(pald_data)
        
        assert "global_design_level.type" in filled_fields
        assert "middle_design_level.role" in filled_fields
        assert "global_design_level.other" not in filled_fields
        assert "middle_design_level.empty_field" not in filled_fields
    
    def test_missing_fields_detection(self):
        """Test detection of missing fields based on schema."""
        pald_data = {
            "global_design_level": {
                "type": "human"
                # Missing other fields
            }
        }
        
        missing_fields = self.extractor._get_missing_fields(pald_data, self.mock_schema)
        
        # Should include fields defined in schema but not in data
        assert any("middle_design_level" in field for field in missing_fields)
        assert any("detailed_level" in field for field in missing_fields)
    
    def test_fallback_result_creation(self):
        """Test creation of fallback result on extraction failure."""
        description = "A person"
        error_message = "Test error"
        
        result = self.extractor._create_fallback_result(description, error_message)
        
        assert isinstance(result, PALDLightResult)
        assert result.extraction_confidence == 0.1  # Very low
        assert result.processing_metadata["is_fallback"] is True
        assert error_message in result.validation_errors[0]
        assert result.compressed_prompt == "person"
        
        # Should have minimal valid structure
        assert result.pald_light["global_design_level"]["type"] == "human"
        assert result.pald_light["middle_design_level"]["role"] == "assistant"
    
    def test_fallback_basic_extraction(self):
        """Test that fallback can extract basic info from description."""
        description = "She is a young girl"
        error_message = "Test error"
        
        result = self.extractor._create_fallback_result(description, error_message)
        
        # Should extract basic gender and age even in fallback
        detailed_level = result.pald_light["detailed_level"]
        assert detailed_level.get("gender") == "female"
        assert detailed_level.get("age") == "child"
    
    def test_extraction_error_handling(self):
        """Test graceful handling of extraction errors."""
        description = "A person"
        
        # Mock schema loader to raise an exception
        with patch.object(self.extractor.schema_loader, 'load_schema', side_effect=Exception("Schema load failed")):
            result = self.extractor.extract_from_text(description)
        
        # Should return fallback result
        assert isinstance(result, PALDLightResult)
        assert result.processing_metadata.get("is_fallback") is True
        assert "Schema load failed" in result.validation_errors[0]
    
    def test_empty_text_handling(self):
        """Test handling of empty or minimal text input."""
        with patch.object(self.extractor.schema_loader, 'load_schema', return_value=self.mock_schema):
            result = self.extractor.extract_from_text("")
        
        assert isinstance(result, PALDLightResult)
        assert result.extraction_confidence == 0.0
        assert len(result.filled_fields) == 0
    
    def test_complex_text_extraction(self):
        """Test extraction from complex, realistic text."""
        description = """
        Create a friendly and competent female teacher who appears to be in her 30s. 
        She should look realistic and professional, wearing a navy blue blazer and white blouse. 
        She has a warm, encouraging personality and is very skilled at explaining complex topics.
        The character should be photorealistic and appear as a helpful mentor figure.
        """
        
        with patch.object(self.extractor.schema_loader, 'load_schema', return_value=self.mock_schema):
            result = self.extractor.extract_from_text(description)
        
        pald = result.pald_light
        
        # Should extract multiple attributes correctly
        assert pald.get("global_design_level", {}).get("type") == "human"
        assert pald.get("middle_design_level", {}).get("role") == "teacher"
        assert pald.get("middle_design_level", {}).get("lifelikeness") == 7  # photorealistic
        assert pald.get("detailed_level", {}).get("gender") == "female"
        
        # Should have reasonable confidence
        assert result.extraction_confidence > 0.3
        
        # Compressed prompt should be reasonable
        assert len(result.compressed_prompt) > 10
        assert "teacher" in result.compressed_prompt


if __name__ == "__main__":
    pytest.main([__file__])