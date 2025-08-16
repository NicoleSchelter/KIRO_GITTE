"""
PALD Light Extraction System
Handles mandatory immediate PALD extraction for prompt compression and image generation.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from config.pald_enhancement import schema_loader, pald_enhancement_config

logger = logging.getLogger(__name__)


@dataclass
class PALDLightResult:
    """Result of PALD Light extraction."""
    pald_light: dict[str, Any]
    extraction_confidence: float
    filled_fields: list[str]
    missing_fields: list[str]
    validation_errors: list[str]
    compressed_prompt: str
    processing_metadata: dict[str, Any] = field(default_factory=dict)


class PALDLightExtractor:
    """Extracts mandatory PALD data for immediate use."""
    
    def __init__(self):
        self.schema_loader = schema_loader
        
    def extract_from_text(
        self, 
        description_text: str, 
        embodiment_caption: str | None = None,
        schema: dict[str, Any] | None = None
    ) -> PALDLightResult:
        """Extract PALD Light from text inputs."""
        try:
            # Load schema if not provided
            if schema is None:
                schema = self.schema_loader.load_schema()
            
            # Combine texts for extraction
            combined_text = description_text
            if embodiment_caption:
                combined_text += f" {embodiment_caption}"
            
            logger.debug(f"Extracting PALD from text: {combined_text[:100]}...")
            
            # Extract PALD data
            pald_data = self._extract_pald_attributes(combined_text, schema)
            
            # Validate extraction
            validation_result = self.validate_extraction(pald_data, schema)
            
            # Calculate confidence
            confidence = self._calculate_extraction_confidence(pald_data, combined_text)
            
            # Get field lists
            filled_fields = self._get_filled_fields(pald_data)
            missing_fields = self._get_missing_fields(pald_data, schema)
            
            # Compress for prompt
            compressed_prompt = self.compress_for_prompt(pald_data)
            
            # Create metadata
            metadata = {
                "extraction_timestamp": datetime.now().isoformat(),
                "input_text_length": len(combined_text),
                "has_embodiment_caption": embodiment_caption is not None,
                "schema_version": schema.get("$schema", "unknown")
            }
            
            return PALDLightResult(
                pald_light=pald_data,
                extraction_confidence=confidence,
                filled_fields=filled_fields,
                missing_fields=missing_fields,
                validation_errors=validation_result.get("errors", []),
                compressed_prompt=compressed_prompt,
                processing_metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"PALD extraction failed: {e}")
            return self._create_fallback_result(description_text, str(e))
    
    def _extract_pald_attributes(self, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Extract PALD attributes from text based on schema."""
        pald_data = {}
        text_lower = text.lower()
        
        # Get schema properties (handle both direct and JSON Schema formats)
        schema_properties = schema.get("properties", schema)
        
        # Extract global design level
        if "global_design_level" in schema_properties:
            pald_data["global_design_level"] = self._extract_global_design_level(text_lower, schema_properties["global_design_level"])
        
        # Extract middle design level
        if "middle_design_level" in schema_properties:
            pald_data["middle_design_level"] = self._extract_middle_design_level(text_lower, schema_properties["middle_design_level"])
        
        # Extract detailed level
        if "detailed_level" in schema_properties:
            pald_data["detailed_level"] = self._extract_detailed_level(text_lower, schema_properties["detailed_level"])
        
        # Remove empty sections
        pald_data = {k: v for k, v in pald_data.items() if v and any(val for val in v.values() if val is not None)}
        
        return pald_data
    
    def _extract_global_design_level(self, text: str, schema_section: dict[str, Any]) -> dict[str, Any]:
        """Extract global design level attributes."""
        global_data = {}
        properties = schema_section.get("properties", {})
        
        # Extract type
        if "type" in properties:
            type_enum = properties["type"].get("enum", [])
            
            # Check for specific type indicators
            if any(word in text for word in ["cartoon", "animated", "animation"]):
                global_data["type"] = "cartoon"
            elif any(word in text for word in ["object", "portrait", "still life", "3d model"]):
                global_data["type"] = "object"
            elif any(word in text for word in ["animal", "dog", "cat", "horse", "bird", "dragon"]):
                global_data["type"] = "animal"
            elif any(word in text for word in ["fantasy", "unicorn", "elf", "orc", "alien", "fairy"]):
                global_data["type"] = "fantasy_figure"
            else:
                # Only set human type if there are person-related terms
                if any(word in text for word in ["person", "human", "man", "woman", "teacher", "assistant", "he", "she", "character"]):
                    global_data["type"] = "human"
                # Don't set a default type if no indicators are found
        
        # Extract cartoon information if type is cartoon
        if global_data.get("type") == "cartoon" and "cartoon" in properties:
            cartoon_props = properties["cartoon"].get("properties", {})
            cartoon_data = {}
            
            # Animation detection
            if "animation" in cartoon_props:
                if any(word in text for word in ["animated", "moving", "animation"]):
                    cartoon_data["animation"] = "animated"
                elif any(word in text for word in ["static", "still", "picture"]):
                    cartoon_data["animation"] = "static"
            
            # Representation detection (specific character names)
            if "representation" in cartoon_props:
                character_patterns = [
                    r"mickey\s*mouse", r"spongebob", r"superman", r"batman", 
                    r"wonder\s*woman", r"pikachu", r"mario", r"sonic"
                ]
                for pattern in character_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        cartoon_data["representation"] = match.group(0)
                        break
            
            if cartoon_data:
                global_data["cartoon"] = cartoon_data
        
        # Extract object type
        if "object_type" in properties and global_data.get("type") == "object":
            object_patterns = [
                r"portrait", r"still\s*life", r"3d\s*model", r"sculpture", 
                r"painting", r"drawing", r"sketch"
            ]
            for pattern in object_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    global_data["object_type"] = match.group(0)
                    break
        
        # Extract animal type
        if "animal_type" in properties and global_data.get("type") == "animal":
            animal_patterns = [
                r"dog", r"cat", r"horse", r"bird", r"fish", r"dragon", 
                r"lion", r"tiger", r"elephant", r"bear"
            ]
            for pattern in animal_patterns:
                if pattern in text:
                    global_data["animal_type"] = pattern
                    break
        
        # Extract fantasy figure type
        if "fantasy_figure_type" in properties and global_data.get("type") == "fantasy_figure":
            fantasy_patterns = [
                r"unicorn", r"elf", r"orc", r"alien", r"fairy", r"wizard", 
                r"witch", r"vampire", r"werewolf", r"ghost"
            ]
            for pattern in fantasy_patterns:
                if pattern in text:
                    global_data["fantasy_figure_type"] = pattern
                    break
        
        # Extract other characteristics
        if "other_characteristics" in properties:
            characteristic_patterns = [
                r"realistic", r"stylized", r"abstract", r"minimalist", 
                r"detailed", r"simple", r"complex"
            ]
            characteristics = []
            for pattern in characteristic_patterns:
                if pattern in text:
                    characteristics.append(pattern)
            
            if characteristics:
                global_data["other_characteristics"] = ", ".join(characteristics)
        
        return global_data
    
    def _extract_middle_design_level(self, text: str, schema_section: dict[str, Any]) -> dict[str, Any]:
        """Extract middle design level attributes."""
        middle_data = {}
        properties = schema_section.get("properties", {})
        
        # Extract lifelikeness (1-7 scale)
        if "lifelikeness" in properties:
            lifelike_patterns = [
                (r"photorealistic|photo-realistic|very realistic", 7),
                (r"realistic|lifelike", 6),
                (r"somewhat realistic|fairly realistic", 5),
                (r"moderately realistic|average realism", 4),
                (r"stylized|somewhat stylized", 3),
                (r"cartoon-like|cartoonish", 2),
                (r"very stylized|abstract", 1)
            ]
            
            for pattern, score in lifelike_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    middle_data["lifelikeness"] = score
                    break
        
        # Extract realism (1-7 scale)
        if "realism" in properties:
            realism_patterns = [
                (r"extremely realistic|hyper-realistic", 7),
                (r"very realistic|highly realistic", 6),
                (r"realistic|real-looking", 5),
                (r"somewhat realistic|fairly real", 4),
                (r"moderately realistic|average", 3),
                (r"stylized|artistic", 2),
                (r"unrealistic|fantasy-like", 1)
            ]
            
            for pattern, score in realism_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    middle_data["realism"] = score
                    break
        
        # Extract animation level (1-7 scale)
        if "animation_level" in properties:
            animation_patterns = [
                (r"fully animated|complete animation", 7),
                (r"highly animated|very animated", 6),
                (r"animated|moving", 5),
                (r"some animation|partially animated", 4),
                (r"minimal animation|slight movement", 3),
                (r"barely animated|almost static", 2),
                (r"static|still|no animation", 1)
            ]
            
            for pattern, score in animation_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    middle_data["animation_level"] = score
                    break
        
        # Extract partial representation
        if "partial_representation" in properties:
            partial_patterns = [
                r"head\s*only|just\s*head|head\s*shot",
                r"half\s*body|upper\s*body|torso",
                r"full\s*body|whole\s*body|complete\s*figure",
                r"face\s*only|just\s*face|facial"
            ]
            
            for pattern in partial_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    middle_data["partial_representation"] = match.group(0).lower()
                    break
        
        # Extract likeability (1-7 scale)
        if "likeability" in properties:
            likeability_patterns = [
                (r"very\s*likeable|extremely\s*friendly|very\s*charming", 7),
                (r"likeable|friendly|charming|pleasant", 6),
                (r"somewhat\s*likeable|fairly\s*friendly", 5),
                (r"neutral|average|okay", 4),
                (r"somewhat\s*unfriendly|slightly\s*off-putting", 3),
                (r"unfriendly|unpleasant|cold", 2),
                (r"very\s*unfriendly|extremely\s*unpleasant", 1)
            ]
            
            for pattern, score in likeability_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    middle_data["likeability"] = score
                    break
        
        # Extract competence (1-7 scale)
        if "competence" in properties:
            competence_patterns = [
                (r"highly\s*competent|very\s*skilled|expert|master", 7),
                (r"competent|skilled|capable|proficient", 6),
                (r"somewhat\s*competent|fairly\s*skilled", 5),
                (r"average\s*competence|moderately\s*skilled", 4),
                (r"somewhat\s*incompetent|limited\s*skills", 3),
                (r"incompetent|unskilled|incapable", 2),
                (r"very\s*incompetent|completely\s*unskilled", 1)
            ]
            
            for pattern, score in competence_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    middle_data["competence"] = score
                    break
        
        # Extract role
        if "role" in properties:
            role_patterns = [
                r"teacher|instructor|educator|tutor",
                r"assistant|helper|aide|support",
                r"guide|mentor|coach|advisor",
                r"expert|specialist|professional|consultant",
                r"friend|companion|buddy|peer"
            ]
            
            for pattern in role_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    middle_data["role"] = match.group(0).lower()
                    break
        
        # Extract role model
        if "role_model" in properties:
            role_model_patterns = [
                r"like\s+([a-zA-Z\s]+?)(?:\s|$|,|\.|!|\?)",
                r"similar\s+to\s+([a-zA-Z\s]+?)(?:\s|$|,|\.|!|\?)",
                r"based\s+on\s+([a-zA-Z\s]+?)(?:\s|$|,|\.|!|\?)"
            ]
            
            for pattern in role_model_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    role_model = match.group(1).strip()
                    if len(role_model) > 2 and len(role_model) < 50:
                        middle_data["role_model"] = role_model
                        break
        
        return middle_data
    
    def _extract_detailed_level(self, text: str, schema_section: dict[str, Any]) -> dict[str, Any]:
        """Extract detailed level attributes."""
        detailed_data = {}
        properties = schema_section.get("properties", {})
        
        # Extract age
        if "age" in properties:
            # Try to extract specific age numbers first
            age_number_match = re.search(r"(\d+)\s*years?\s*old", text)
            if age_number_match:
                detailed_data["age"] = int(age_number_match.group(1))
            else:
                # Extract age categories
                # Extract age categories with more specific matching
                if re.search(r"\b(?:child|kid|little)\b", text, re.IGNORECASE):
                    detailed_data["age"] = "child"
                elif re.search(r"\b(?:young|youth)\b", text, re.IGNORECASE):
                    detailed_data["age"] = "young"
                elif re.search(r"\b(?:teenager|teen|adolescent)\b", text, re.IGNORECASE):
                    detailed_data["age"] = "teenager"
                elif re.search(r"\b(?:adult|grown-up|mature)\b", text, re.IGNORECASE):
                    detailed_data["age"] = "adult"
                elif re.search(r"\b(?:elderly|old|senior|aged)\b", text, re.IGNORECASE):
                    detailed_data["age"] = "elderly"
        
        # Extract gender
        if "gender" in properties:
            gender_patterns = [
                (r"female|woman|girl|she|her", "female"),
                (r"male|man|boy|he|him", "male"),
                (r"non-binary|nonbinary|they|them", "non-binary"),
                (r"other|different|unique", "other")
            ]
            
            for pattern, gender in gender_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detailed_data["gender"] = gender
                    break
        
        # Extract clothing
        if "clothing" in properties:
            clothing_patterns = [
                r"wearing\s+([^.!?]+?)(?:\.|!|\?|$)",
                r"dressed\s+in\s+([^.!?]+?)(?:\.|!|\?|$)",
                r"clothes?\s*:\s*([^.!?]+?)(?:\.|!|\?|$)",
                r"outfit\s*:\s*([^.!?]+?)(?:\.|!|\?|$)"
            ]
            
            for pattern in clothing_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    clothing = match.group(1).strip()
                    if len(clothing) > 2 and len(clothing) < 100:
                        detailed_data["clothing"] = clothing
                        break
            
            # Also look for specific clothing items
            if "clothing" not in detailed_data:
                clothing_items = [
                    r"shirt|blouse|top", r"pants|trousers|jeans", r"dress|skirt",
                    r"suit|jacket|coat", r"uniform|costume", r"casual|formal"
                ]
                
                found_items = []
                for item_pattern in clothing_items:
                    if re.search(item_pattern, text, re.IGNORECASE):
                        found_items.append(re.search(item_pattern, text, re.IGNORECASE).group(0))
                
                if found_items:
                    detailed_data["clothing"] = ", ".join(found_items)
        
        # Extract weight/build
        if "weight" in properties:
            weight_patterns = [
                r"slim|thin|skinny|slender",
                r"average|normal|medium",
                r"heavy|overweight|large|big",
                r"athletic|muscular|fit|strong",
                r"petite|small|tiny"
            ]
            
            for pattern in weight_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detailed_data["weight"] = pattern.split("|")[0]  # Use first term
                    break
        
        # Extract other features
        if "other_features" in properties:
            feature_patterns = [
                r"hair\s*:\s*([^.!?]+?)(?:\.|!|\?|$)",
                r"eyes\s*:\s*([^.!?]+?)(?:\.|!|\?|$)",
                r"skin\s*:\s*([^.!?]+?)(?:\.|!|\?|$)",
                r"voice\s*:\s*([^.!?]+?)(?:\.|!|\?|$)"
            ]
            
            features = []
            for pattern in feature_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    feature = match.group(1).strip()
                    if len(feature) > 2 and len(feature) < 50:
                        features.append(feature)
            
            if features:
                detailed_data["other_features"] = "; ".join(features)
        
        return detailed_data
    
    def validate_extraction(self, pald_data: dict[str, Any], schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate extracted PALD against schema."""
        if schema is None:
            schema = self.schema_loader.load_schema()
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Basic structure validation
            schema_properties = schema.get("properties", schema)
            
            for section_name, section_data in pald_data.items():
                if section_name not in schema_properties:
                    validation_result["warnings"].append(f"Unknown section: {section_name}")
                    continue
                
                section_schema = schema_properties[section_name]
                section_properties = section_schema.get("properties", {})
                
                if not isinstance(section_data, dict):
                    validation_result["errors"].append(f"Section {section_name} must be an object")
                    validation_result["is_valid"] = False
                    continue
                
                # Validate fields in section
                for field_name, field_value in section_data.items():
                    if field_name not in section_properties:
                        validation_result["warnings"].append(f"Unknown field: {section_name}.{field_name}")
                        continue
                    
                    field_schema = section_properties[field_name]
                    
                    # Type validation
                    expected_types = field_schema.get("type", [])
                    if isinstance(expected_types, str):
                        expected_types = [expected_types]
                    
                    if expected_types and "null" not in expected_types:
                        if field_value is not None:
                            field_type = type(field_value).__name__
                            python_to_json_type = {
                                "str": "string",
                                "int": "integer", 
                                "float": "number",
                                "bool": "boolean",
                                "dict": "object",
                                "list": "array"
                            }
                            
                            json_type = python_to_json_type.get(field_type, field_type)
                            if json_type not in expected_types:
                                validation_result["errors"].append(
                                    f"Field {section_name}.{field_name} has type {json_type}, expected {expected_types}"
                                )
                                validation_result["is_valid"] = False
                    
                    # Enum validation
                    if "enum" in field_schema and field_value is not None:
                        if field_value not in field_schema["enum"]:
                            validation_result["warnings"].append(
                                f"Field {section_name}.{field_name} value '{field_value}' not in enum {field_schema['enum']}"
                            )
                    
                    # Range validation for integers
                    if field_schema.get("type") == "integer" and isinstance(field_value, int):
                        if "minimum" in field_schema and field_value < field_schema["minimum"]:
                            validation_result["errors"].append(
                                f"Field {section_name}.{field_name} value {field_value} below minimum {field_schema['minimum']}"
                            )
                            validation_result["is_valid"] = False
                        
                        if "maximum" in field_schema and field_value > field_schema["maximum"]:
                            validation_result["errors"].append(
                                f"Field {section_name}.{field_name} value {field_value} above maximum {field_schema['maximum']}"
                            )
                            validation_result["is_valid"] = False
            
        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def compress_for_prompt(self, pald_data: dict[str, Any]) -> str:
        """Compress PALD data for Stable Diffusion prompt."""
        prompt_parts = []
        
        try:
            # Global design level
            if "global_design_level" in pald_data:
                global_data = pald_data["global_design_level"]
                
                if "type" in global_data:
                    prompt_parts.append(global_data["type"])
                
                if "cartoon" in global_data and global_data["cartoon"]:
                    cartoon_data = global_data["cartoon"]
                    if "representation" in cartoon_data:
                        prompt_parts.append(cartoon_data["representation"])
                    if "animation" in cartoon_data:
                        prompt_parts.append(cartoon_data["animation"])
                
                if "object_type" in global_data:
                    prompt_parts.append(global_data["object_type"])
                
                if "animal_type" in global_data:
                    prompt_parts.append(global_data["animal_type"])
                
                if "fantasy_figure_type" in global_data:
                    prompt_parts.append(global_data["fantasy_figure_type"])
            
            # Middle design level
            if "middle_design_level" in pald_data:
                middle_data = pald_data["middle_design_level"]
                
                # Convert numeric scales to descriptive terms
                if "lifelikeness" in middle_data:
                    lifelikeness_map = {
                        7: "photorealistic", 6: "realistic", 5: "semi-realistic",
                        4: "stylized", 3: "cartoon-like", 2: "abstract", 1: "minimal"
                    }
                    if middle_data["lifelikeness"] in lifelikeness_map:
                        prompt_parts.append(lifelikeness_map[middle_data["lifelikeness"]])
                
                if "role" in middle_data:
                    prompt_parts.append(middle_data["role"])
                
                if "partial_representation" in middle_data:
                    prompt_parts.append(middle_data["partial_representation"])
            
            # Detailed level
            if "detailed_level" in pald_data:
                detailed_data = pald_data["detailed_level"]
                
                if "age" in detailed_data:
                    prompt_parts.append(str(detailed_data["age"]))
                
                if "gender" in detailed_data:
                    prompt_parts.append(detailed_data["gender"])
                
                if "clothing" in detailed_data:
                    # Simplify clothing description
                    clothing = detailed_data["clothing"]
                    if len(clothing) > 50:
                        clothing = clothing[:47] + "..."
                    prompt_parts.append(f"wearing {clothing}")
                
                if "weight" in detailed_data:
                    prompt_parts.append(detailed_data["weight"])
            
            # Join parts and clean up
            compressed = ", ".join(prompt_parts)
            
            # Remove redundant words and clean up
            compressed = re.sub(r'\b(the|a|an)\b', '', compressed, flags=re.IGNORECASE)
            compressed = re.sub(r'\s+', ' ', compressed)
            compressed = compressed.strip(", ")
            
            # Limit length for SD prompts (typically 75-77 tokens max)
            if len(compressed) > 200:
                compressed = compressed[:197] + "..."
            
            return compressed
            
        except Exception as e:
            logger.error(f"Error compressing PALD for prompt: {e}")
            return "person"  # Fallback
    
    def _calculate_extraction_confidence(self, pald_data: dict[str, Any], text: str) -> float:
        """Calculate confidence score for extraction."""
        try:
            total_fields = 0
            filled_fields = 0
            
            # Count total possible fields and filled fields
            for section_name, section_data in pald_data.items():
                if isinstance(section_data, dict):
                    for field_name, field_value in section_data.items():
                        total_fields += 1
                        if field_value is not None and field_value != "":
                            filled_fields += 1
            
            # Base confidence on fill rate
            if total_fields == 0:
                return 0.0
            
            # If no text provided, confidence should be very low
            if len(text.strip()) == 0:
                return 0.0
            
            fill_rate = filled_fields / total_fields
            
            # Adjust based on text length (more text = potentially higher confidence)
            text_length_factor = min(len(text) / 500, 1.0)  # Cap at 500 chars
            
            # Penalize very low absolute number of filled fields
            if filled_fields <= 1:
                fill_rate = fill_rate * 0.3  # Very low confidence for minimal extraction
            elif filled_fields <= 3:
                fill_rate = fill_rate * 0.6  # Moderate penalty for few fields
            
            # Combine factors with more weight on actual extraction success
            confidence = (fill_rate * 0.8) + (text_length_factor * 0.2)
            
            return round(confidence, 2)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.0
    
    def _get_filled_fields(self, pald_data: dict[str, Any]) -> list[str]:
        """Get list of filled field paths."""
        filled_fields = []
        
        for section_name, section_data in pald_data.items():
            if isinstance(section_data, dict):
                for field_name, field_value in section_data.items():
                    if field_value is not None and field_value != "":
                        filled_fields.append(f"{section_name}.{field_name}")
        
        return sorted(filled_fields)
    
    def _get_missing_fields(self, pald_data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
        """Get list of missing field paths based on schema."""
        missing_fields = []
        schema_properties = schema.get("properties", schema)
        
        for section_name, section_schema in schema_properties.items():
            section_properties = section_schema.get("properties", {})
            section_data = pald_data.get(section_name, {})
            
            for field_name in section_properties.keys():
                field_value = section_data.get(field_name)
                if field_value is None or field_value == "":
                    missing_fields.append(f"{section_name}.{field_name}")
        
        return sorted(missing_fields)
    
    def _create_fallback_result(self, description_text: str, error_message: str) -> PALDLightResult:
        """Create a fallback result when extraction fails."""
        logger.warning(f"Creating fallback PALD result due to error: {error_message}")
        
        # Create minimal valid PALD structure
        minimal_pald = {
            "global_design_level": {
                "type": "human"  # Safe default
            },
            "middle_design_level": {
                "role": "assistant"  # Safe default
            },
            "detailed_level": {}
        }
        
        # Try to extract at least basic info from description
        text_lower = description_text.lower()
        
        # Basic gender detection
        if any(word in text_lower for word in ["she", "her", "woman", "girl", "female"]):
            minimal_pald["detailed_level"]["gender"] = "female"
        elif any(word in text_lower for word in ["he", "him", "man", "boy", "male"]):
            minimal_pald["detailed_level"]["gender"] = "male"
        
        # Basic age detection
        if any(word in text_lower for word in ["child", "kid", "young"]):
            minimal_pald["detailed_level"]["age"] = "child"
        elif any(word in text_lower for word in ["adult", "grown"]):
            minimal_pald["detailed_level"]["age"] = "adult"
        
        return PALDLightResult(
            pald_light=minimal_pald,
            extraction_confidence=0.1,  # Very low confidence
            filled_fields=self._get_filled_fields(minimal_pald),
            missing_fields=[],  # Don't calculate missing for fallback
            validation_errors=[f"Extraction failed: {error_message}"],
            compressed_prompt="person",  # Simple fallback
            processing_metadata={
                "is_fallback": True,
                "error_message": error_message,
                "extraction_timestamp": datetime.now().isoformat()
            }
        )