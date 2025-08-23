"""
Chat Logic for Study Participation
Handles chat message processing, PALD extraction, consistency checking, and feedback loops.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from config.config import config
from src.data.models import (
    ChatMessage,
    ChatMessageType,
    FeedbackRecord,
    GeneratedImage,
    InteractionLog,
    StudyPALDData,
    StudyPALDType,
)
from src.exceptions import ValidationError
from src.logic.pald_boundary import PALDBoundaryEnforcer
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class PALDExtractionResult:
    """Result of PALD extraction from text."""
    success: bool
    pald_data: dict[str, Any]
    extraction_confidence: float
    processing_time_ms: int
    error_message: str | None = None


@dataclass
class ConsistencyCheckResult:
    """Result of PALD consistency checking."""
    is_consistent: bool
    consistency_score: float
    differences: list[str]
    recommendation: str  # continue, regenerate, accept


@dataclass
class ChatProcessingResult:
    """Result of chat message processing."""
    message_id: UUID
    pald_extracted: bool
    pald_data: dict[str, Any] | None
    consistency_check_performed: bool
    consistency_result: ConsistencyCheckResult | None
    requires_regeneration: bool
    processing_metadata: dict[str, Any]


@dataclass
class FeedbackProcessingResult:
    """Result of feedback processing."""
    feedback_id: UUID
    round_number: int
    max_rounds_reached: bool
    feedback_pald: dict[str, Any] | None
    should_continue: bool
    processing_metadata: dict[str, Any]


class ChatLogic:
    """Logic layer for chat processing and PALD pipeline management."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.boundary_enforcer = PALDBoundaryEnforcer()
        self._pald_extraction_cache: dict[str, PALDExtractionResult] = {}

    def process_chat_input(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        message_content: str,
        message_type: ChatMessageType = ChatMessageType.USER,
    ) -> ChatProcessingResult:
        """
        Process a chat input message through the complete PALD pipeline.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            message_content: The message content to process
            message_type: Type of message (user, assistant, system)
            
        Returns:
            ChatProcessingResult: Complete processing result
        """
        start_time = datetime.now()
        message_id = uuid4()
        
        logger.info(f"Processing chat input for pseudonym {pseudonym_id}, session {session_id}")
        
        try:
            # Extract PALD from input message
            pald_result = self.extract_pald_from_text(message_content)
            
            processing_metadata = {
                "message_length": len(message_content),
                "pald_extraction_time_ms": pald_result.processing_time_ms,
                "pald_confidence": pald_result.extraction_confidence,
                "processing_start": start_time.isoformat(),
            }
            
            # Include error information if PALD extraction failed
            if not pald_result.success and pald_result.error_message:
                processing_metadata["pald_extraction_error"] = pald_result.error_message
            
            # Determine if consistency check is needed
            consistency_result = None
            consistency_check_performed = False
            requires_regeneration = False
            
            if (pald_result.success and 
                config.feature_flags.enable_consistency_check and 
                message_type == ChatMessageType.USER):
                
                # For user messages, we might need to check consistency with previous PALDs
                # This would typically happen after image generation and description
                consistency_check_performed = True
                # Note: Actual consistency check would happen in the image generation flow
                
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            processing_metadata["total_processing_time_ms"] = processing_time
            
            return ChatProcessingResult(
                message_id=message_id,
                pald_extracted=pald_result.success,
                pald_data=pald_result.pald_data if pald_result.success else None,
                consistency_check_performed=consistency_check_performed,
                consistency_result=consistency_result,
                requires_regeneration=requires_regeneration,
                processing_metadata=processing_metadata,
            )
            
        except Exception as e:
            logger.error(f"Error processing chat input: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ChatProcessingResult(
                message_id=message_id,
                pald_extracted=False,
                pald_data=None,
                consistency_check_performed=False,
                consistency_result=None,
                requires_regeneration=False,
                processing_metadata={
                    "error": str(e),
                    "message_length": len(message_content),
                    "processing_start": start_time.isoformat(),
                    "total_processing_time_ms": processing_time,
                },
            )

    def extract_pald_from_text(self, text: str) -> PALDExtractionResult:
        """
        Extract PALD data from text using LLM.
        
        Args:
            text: Input text to extract PALD from
            
        Returns:
            PALDExtractionResult: Extraction result with PALD data
        """
        start_time = datetime.now()
        
        # Check cache first
        cache_key = f"pald_extract_{hash(text)}"
        if cache_key in self._pald_extraction_cache:
            cached_result = self._pald_extraction_cache[cache_key]
            logger.debug(f"Using cached PALD extraction for text hash {hash(text)}")
            return cached_result
        
        try:
            # Create PALD extraction prompt
            extraction_prompt = self._create_pald_extraction_prompt(text)
            
            # Call LLM for PALD extraction
            llm_response = self.llm_service.generate_response(
                prompt=extraction_prompt,
                model=config.llm.models.get("default", "llama3"),
                parameters={
                    "temperature": 0.3,  # Lower temperature for more consistent extraction
                    "max_tokens": 1000,
                    "format": "json",
                }
            )
            
            # Parse PALD data from response
            pald_data = self._parse_pald_response(llm_response.text)
            
            # Validate and filter PALD data through boundary enforcer
            boundary_result = self.boundary_enforcer.validate_pald_boundary(pald_data)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if boundary_result.is_valid:
                result = PALDExtractionResult(
                    success=True,
                    pald_data=boundary_result.filtered_data,
                    extraction_confidence=0.8,  # Could be enhanced with confidence scoring
                    processing_time_ms=int(processing_time),
                )
            else:
                result = PALDExtractionResult(
                    success=False,
                    pald_data={},
                    extraction_confidence=0.0,
                    processing_time_ms=int(processing_time),
                    error_message=f"PALD boundary validation failed: {boundary_result.validation_errors}",
                )
            
            # Cache the result
            self._pald_extraction_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"PALD extraction failed: {e}")
            
            return PALDExtractionResult(
                success=False,
                pald_data={},
                extraction_confidence=0.0,
                processing_time_ms=int(processing_time),
                error_message=str(e),
            )

    def check_pald_consistency(
        self, 
        input_pald: dict[str, Any], 
        description_pald: dict[str, Any]
    ) -> ConsistencyCheckResult:
        """
        Check consistency between input PALD and image description PALD.
        
        Args:
            input_pald: PALD extracted from user input
            description_pald: PALD extracted from generated image description
            
        Returns:
            ConsistencyCheckResult: Consistency analysis result
        """
        logger.info("Performing PALD consistency check")
        
        try:
            # Calculate consistency score based on key attribute matching
            consistency_score = self._calculate_consistency_score(input_pald, description_pald)
            
            # Identify differences
            differences = self._identify_pald_differences(input_pald, description_pald)
            
            # Determine if consistent based on threshold
            threshold = config.pald_boundary.pald_consistency_threshold
            is_consistent = consistency_score >= threshold
            
            # Generate recommendation
            if is_consistent:
                recommendation = "continue"
            elif consistency_score >= threshold * 0.7:  # Close but not quite
                recommendation = "accept"  # Accept with minor differences
            else:
                recommendation = "regenerate"
            
            return ConsistencyCheckResult(
                is_consistent=is_consistent,
                consistency_score=consistency_score,
                differences=differences,
                recommendation=recommendation,
            )
            
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            
            # Return safe default - accept to avoid infinite loops
            return ConsistencyCheckResult(
                is_consistent=True,
                consistency_score=0.5,
                differences=[f"Consistency check error: {e}"],
                recommendation="accept",
            )

    def manage_feedback_loop(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        feedback_text: str,
        current_round: int,
        image_id: UUID | None = None,
        user_wants_to_stop: bool = False,
    ) -> FeedbackProcessingResult:
        """
        Manage feedback loop processing with round counting.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            feedback_text: User feedback text
            current_round: Current feedback round number
            image_id: Associated image ID if applicable
            user_wants_to_stop: Whether user wants to stop the feedback loop early
            
        Returns:
            FeedbackProcessingResult: Feedback processing result
        """
        feedback_id = uuid4()
        max_rounds = config.pald_boundary.max_feedback_rounds
        
        logger.info(f"Processing feedback round {current_round}/{max_rounds} for pseudonym {pseudonym_id}")
        
        try:
            # Extract PALD from feedback text
            feedback_pald_result = self.extract_pald_from_text(feedback_text)
            
            # Check if max rounds reached
            max_rounds_reached = current_round >= max_rounds
            
            # If PALD extraction failed, treat it as reaching max rounds to stop the loop
            if not feedback_pald_result.success:
                max_rounds_reached = True
            
            # If user wants to stop, treat it as reaching max rounds
            if user_wants_to_stop:
                max_rounds_reached = True
            
            # Determine if should continue based on rounds and feedback content
            # Stop if max rounds reached OR if PALD extraction failed OR if user wants to stop
            should_continue = not max_rounds_reached and feedback_pald_result.success and not user_wants_to_stop
            
            processing_metadata = {
                "feedback_length": len(feedback_text),
                "pald_extraction_success": feedback_pald_result.success,
                "pald_confidence": feedback_pald_result.extraction_confidence,
                "max_rounds": max_rounds,
                "rounds_remaining": max(0, max_rounds - current_round),
                "user_stopped_early": user_wants_to_stop,
            }
            
            # Include PALD extraction error if it failed
            if not feedback_pald_result.success and feedback_pald_result.error_message:
                processing_metadata["pald_extraction_error"] = feedback_pald_result.error_message
                processing_metadata["error"] = feedback_pald_result.error_message
            
            return FeedbackProcessingResult(
                feedback_id=feedback_id,
                round_number=current_round,
                max_rounds_reached=max_rounds_reached,
                feedback_pald=feedback_pald_result.pald_data if feedback_pald_result.success else None,
                should_continue=should_continue,
                processing_metadata=processing_metadata,
            )
            
        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")
            
            return FeedbackProcessingResult(
                feedback_id=feedback_id,
                round_number=current_round,
                max_rounds_reached=True,  # Stop on error
                feedback_pald=None,
                should_continue=False,
                processing_metadata={"error": str(e)},
            )

    def stop_feedback_loop(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        current_round: int,
    ) -> FeedbackProcessingResult:
        """
        Stop the feedback loop early at user request.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            current_round: Current feedback round number
            
        Returns:
            FeedbackProcessingResult: Result indicating loop was stopped
        """
        feedback_id = uuid4()
        max_rounds = config.pald_boundary.max_feedback_rounds
        
        logger.info(f"User stopped feedback loop early at round {current_round} for pseudonym {pseudonym_id}")
        
        return FeedbackProcessingResult(
            feedback_id=feedback_id,
            round_number=current_round,
            max_rounds_reached=True,  # Treat as max rounds reached
            feedback_pald=None,
            should_continue=False,
            processing_metadata={
                "user_stopped_early": True,
                "max_rounds": max_rounds,
                "rounds_remaining": max(0, max_rounds - current_round),
                "stop_reason": "user_request",
            },
        )

    def _create_pald_extraction_prompt(self, text: str) -> str:
        """Create a prompt for PALD extraction from text."""
        return f"""
Extract PALD (Pedagogical Agent Level of Design) information from the following text.
Focus only on embodiment-related attributes such as appearance, physical characteristics, 
visual design elements, and other attributes that describe how a pedagogical agent should look.

Text to analyze:
{text}

Please extract and return a JSON object with the following structure:
{{
    "global_design_level": {{
        "overall_appearance": "description",
        "style": "description",
        "theme": "description"
    }},
    "middle_design_level": {{
        "physical_attributes": "description",
        "clothing": "description",
        "accessories": "description"
    }},
    "detailed_level": {{
        "facial_features": "description",
        "hair": "description",
        "colors": "description",
        "specific_details": "description"
    }},
    "design_elements_not_in_PALD": []
}}

Only include attributes that are explicitly mentioned or can be reasonably inferred from the text.
If no embodiment information is found, return an empty object {{}}.
"""

    def _parse_pald_response(self, response_text: str) -> dict[str, Any]:
        """Parse PALD data from LLM response."""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Handle cases where response might have extra text around JSON
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Find JSON object in response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                logger.warning("No JSON object found in PALD response")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse PALD JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error parsing PALD response: {e}")
            return {}

    def _calculate_consistency_score(
        self, 
        input_pald: dict[str, Any], 
        description_pald: dict[str, Any]
    ) -> float:
        """Calculate consistency score between two PALD objects."""
        # Handle empty PALDs
        if not input_pald and not description_pald:
            return 1.0  # Both empty, perfectly consistent
        if not input_pald or not description_pald:
            return 0.0  # One empty, one not - inconsistent
        
        # Get all unique keys from both PALDs
        all_keys = set(input_pald.keys()) | set(description_pald.keys())
        
        if not all_keys:
            return 1.0  # Both empty, perfectly consistent
        
        matching_score = 0.0
        total_weight = 0.0
        
        # Weight different levels differently
        level_weights = {
            "global_design_level": 0.4,
            "middle_design_level": 0.35,
            "detailed_level": 0.25,
        }
        
        for key in all_keys:
            weight = level_weights.get(key, 0.1)  # Default weight for other keys
            total_weight += weight
            
            if key in input_pald and key in description_pald:
                # Both have the key, check similarity
                similarity = self._calculate_attribute_similarity(
                    input_pald[key], description_pald[key]
                )
                matching_score += similarity * weight
            elif key in input_pald or key in description_pald:
                # Only one has the key, partial penalty
                matching_score += 0.3 * weight
        
        return matching_score / total_weight if total_weight > 0 else 0.0

    def _calculate_attribute_similarity(self, attr1: Any, attr2: Any) -> float:
        """Calculate similarity between two PALD attributes."""
        if attr1 == attr2:
            return 1.0
        
        if isinstance(attr1, dict) and isinstance(attr2, dict):
            # For nested objects, recursively calculate similarity
            all_subkeys = set(attr1.keys()) | set(attr2.keys())
            if not all_subkeys:
                return 1.0
            
            similarity_sum = 0.0
            for subkey in all_subkeys:
                if subkey in attr1 and subkey in attr2:
                    similarity_sum += self._calculate_attribute_similarity(attr1[subkey], attr2[subkey])
                else:
                    similarity_sum += 0.3  # Partial match for missing keys
            
            return similarity_sum / len(all_subkeys)
        
        elif isinstance(attr1, str) and isinstance(attr2, str):
            # For strings, use simple word overlap (Jaccard similarity)
            words1 = set(attr1.lower().split())
            words2 = set(attr2.lower().split())
            
            if not words1 and not words2:
                return 1.0
            if not words1 or not words2:
                return 0.0
            
            intersection = words1 & words2
            union = words1 | words2
            
            # Calculate Jaccard similarity
            jaccard = len(intersection) / len(union) if union else 0.0
            
            # Add bonus for partial word matches (simple substring matching)
            if jaccard == 0.0:
                # Check for partial matches
                partial_matches = 0
                total_comparisons = len(words1) * len(words2)
                
                for w1 in words1:
                    for w2 in words2:
                        if len(w1) >= 3 and len(w2) >= 3:  # Only for words of reasonable length
                            if w1 in w2 or w2 in w1:
                                partial_matches += 1
                
                if total_comparisons > 0:
                    jaccard = (partial_matches / total_comparisons) * 0.3  # Partial match bonus
            
            return jaccard
        
        else:
            # Different types or other cases
            return 0.0

    def _identify_pald_differences(
        self, 
        input_pald: dict[str, Any], 
        description_pald: dict[str, Any]
    ) -> list[str]:
        """Identify specific differences between PALD objects."""
        differences = []
        
        all_keys = set(input_pald.keys()) | set(description_pald.keys())
        
        for key in all_keys:
            if key not in input_pald:
                differences.append(f"Key '{key}' present in description but not in input")
            elif key not in description_pald:
                differences.append(f"Key '{key}' present in input but not in description")
            elif input_pald[key] != description_pald[key]:
                differences.append(f"Key '{key}' has different values")
        
        return differences