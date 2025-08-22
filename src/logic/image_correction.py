"""
Image Correction Logic for GITTE system.
Handles user correction decisions and processing workflows.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from uuid import UUID

from PIL import Image
import numpy as np

from src.services.image_isolation_service import ImageIsolationService
from src.services.image_service import ImageService
from src.services.audit_service import AuditService
from src.data.models import User

logger = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    """Result of user correction processing."""
    
    success: bool
    final_image_path: str
    processing_method: str
    processing_time: float
    user_feedback_recorded: bool
    error_message: Optional[str] = None
    regeneration_triggered: bool = False


@dataclass
class LearningData:
    """Data collected for improving future processing."""
    
    user_id: UUID
    original_image_path: str
    correction_type: str
    user_decision: str
    crop_coordinates: Optional[Tuple[int, int, int, int]]
    rejection_reason: Optional[str]
    suggested_modifications: Optional[str]
    processing_confidence: float
    timestamp: str


class ImageCorrectionLogic:
    """Logic layer for handling image correction workflows."""
    
    def __init__(
        self,
        image_service: ImageService,
        isolation_service: ImageIsolationService,
        audit_service: AuditService
    ):
        """
        Initialize image correction logic.
        
        Args:
            image_service: Service for image operations
            isolation_service: Service for image isolation
            audit_service: Service for audit logging
        """
        self.image_service = image_service
        self.isolation_service = isolation_service
        self.audit_service = audit_service
        self.learning_data_cache = []
    
    def process_user_correction(
        self,
        user_id: UUID,
        correction_data: Dict[str, Any]
    ) -> CorrectionResult:
        """
        Process user correction decision and return final image.
        
        Args:
            user_id: User identifier
            correction_data: User correction decisions from dialog
            
        Returns:
            CorrectionResult with processing outcome
        """
        start_time = time.time()
        
        try:
            decision = correction_data.get("decision")
            original_path = correction_data.get("original_image_path")
            processed_path = correction_data.get("processed_image_path")
            
            if not original_path or not Path(original_path).exists():
                result = CorrectionResult(
                    success=False,
                    final_image_path="",
                    processing_method="error",
                    processing_time=time.time() - start_time,
                    user_feedback_recorded=False,
                    error_message="Original image not found"
                )
                # Log even failed corrections
                self._log_correction_result(user_id, correction_data, result)
                return result
            
            # Record user feedback for learning
            self._record_user_feedback(user_id, correction_data)
            
            # Process based on user decision
            if decision == "accept":
                result = self._process_accept_decision(processed_path, original_path)
            elif decision == "adjust":
                result = self._process_adjust_decision(user_id, correction_data)
            elif decision == "original":
                result = self._process_original_decision(original_path)
            elif decision == "regenerate":
                result = self._process_regenerate_decision(user_id, correction_data)
            else:
                result = CorrectionResult(
                    success=False,
                    final_image_path=original_path,
                    processing_method="fallback",
                    processing_time=time.time() - start_time,
                    user_feedback_recorded=True,
                    error_message=f"Unknown decision: {decision}"
                )
            
            # Update processing time
            result.processing_time = time.time() - start_time
            
            # Log correction result
            self._log_correction_result(user_id, correction_data, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing user correction: {e}")
            return CorrectionResult(
                success=False,
                final_image_path=correction_data.get("original_image_path", ""),
                processing_method="error",
                processing_time=time.time() - start_time,
                user_feedback_recorded=False,
                error_message=str(e)
            )
    
    def _process_accept_decision(
        self,
        processed_path: Optional[str],
        original_path: str
    ) -> CorrectionResult:
        """Process user decision to accept processed image."""
        if processed_path and Path(processed_path).exists():
            return CorrectionResult(
                success=True,
                final_image_path=processed_path,
                processing_method="accept_processed",
                processing_time=0.0,
                user_feedback_recorded=True
            )
        else:
            # Fallback to original if processed not available
            return CorrectionResult(
                success=True,
                final_image_path=original_path,
                processing_method="accept_fallback",
                processing_time=0.0,
                user_feedback_recorded=True,
                error_message="Processed image not available, using original"
            )
    
    def _process_adjust_decision(
        self,
        user_id: UUID,
        correction_data: Dict[str, Any]
    ) -> CorrectionResult:
        """Process user decision to manually adjust crop."""
        try:
            original_path = correction_data["original_image_path"]
            crop_coords = correction_data.get("crop_coordinates")
            
            if not crop_coords:
                return CorrectionResult(
                    success=False,
                    final_image_path=original_path,
                    processing_method="adjust_failed",
                    processing_time=0.0,
                    user_feedback_recorded=True,
                    error_message="No crop coordinates provided"
                )
            
            # Apply manual crop
            cropped_path = self._apply_manual_crop(original_path, crop_coords, user_id)
            
            if cropped_path:
                return CorrectionResult(
                    success=True,
                    final_image_path=cropped_path,
                    processing_method="manual_crop",
                    processing_time=0.0,
                    user_feedback_recorded=True
                )
            else:
                return CorrectionResult(
                    success=False,
                    final_image_path=original_path,
                    processing_method="crop_failed",
                    processing_time=0.0,
                    user_feedback_recorded=True,
                    error_message="Failed to apply manual crop"
                )
                
        except Exception as e:
            logger.error(f"Error processing adjust decision: {e}")
            return CorrectionResult(
                success=False,
                final_image_path=correction_data.get("original_image_path", ""),
                processing_method="adjust_error",
                processing_time=0.0,
                user_feedback_recorded=True,
                error_message=str(e)
            )
    
    def _process_original_decision(self, original_path: str) -> CorrectionResult:
        """Process user decision to use original image."""
        return CorrectionResult(
            success=True,
            final_image_path=original_path,
            processing_method="use_original",
            processing_time=0.0,
            user_feedback_recorded=True
        )
    
    def _process_regenerate_decision(
        self,
        user_id: UUID,
        correction_data: Dict[str, Any]
    ) -> CorrectionResult:
        """Process user decision to regenerate image."""
        try:
            # Extract regeneration parameters
            rejection_reason = correction_data.get("rejection_reason", "")
            modifications = correction_data.get("suggested_modifications", "")
            priority = correction_data.get("priority", "Medium")
            
            # Trigger regeneration with modified parameters
            regeneration_params = self._build_regeneration_parameters(
                rejection_reason, modifications, priority
            )
            
            # Note: Actual regeneration would be handled by the image service
            # This logic prepares the parameters and triggers the process
            
            logger.info(f"Regeneration triggered for user {user_id}: {rejection_reason}")
            
            return CorrectionResult(
                success=True,
                final_image_path="",  # Will be set by regeneration process
                processing_method="regenerate",
                processing_time=0.0,
                user_feedback_recorded=True,
                regeneration_triggered=True
            )
            
        except Exception as e:
            logger.error(f"Error processing regenerate decision: {e}")
            return CorrectionResult(
                success=False,
                final_image_path=correction_data.get("original_image_path", ""),
                processing_method="regenerate_error",
                processing_time=0.0,
                user_feedback_recorded=True,
                error_message=str(e)
            )
    
    def _apply_manual_crop(
        self,
        image_path: str,
        crop_coordinates: Tuple[int, int, int, int],
        user_id: UUID
    ) -> Optional[str]:
        """
        Apply manual crop to image based on user selection.
        
        Args:
            image_path: Path to original image
            crop_coordinates: (left, top, right, bottom) coordinates
            user_id: User identifier for file naming
            
        Returns:
            Path to cropped image or None if failed
        """
        try:
            # Load original image
            image = Image.open(image_path)
            
            # Validate crop coordinates
            left, top, right, bottom = crop_coordinates
            img_width, img_height = image.size
            
            # Ensure coordinates are within image bounds
            left = max(0, min(left, img_width - 1))
            top = max(0, min(top, img_height - 1))
            right = max(left + 1, min(right, img_width))
            bottom = max(top + 1, min(bottom, img_height))
            
            # Apply crop
            cropped_image = image.crop((left, top, right, bottom))
            
            # Generate output path
            original_path = Path(image_path)
            output_path = original_path.parent / f"{original_path.stem}_cropped_{user_id}.png"
            
            # Save cropped image
            cropped_image.save(output_path, "PNG")
            
            logger.info(f"Manual crop applied: {crop_coordinates} -> {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error applying manual crop: {e}")
            return None
    
    def _build_regeneration_parameters(
        self,
        rejection_reason: str,
        modifications: str,
        priority: str
    ) -> Dict[str, Any]:
        """
        Build parameters for image regeneration based on user feedback.
        
        Args:
            rejection_reason: Why the image was rejected
            modifications: Suggested improvements
            priority: Priority level for regeneration
            
        Returns:
            Dict with regeneration parameters
        """
        params = {
            "rejection_reason": rejection_reason,
            "modifications": modifications,
            "priority": priority,
            "retry_count": 1,
            "enhanced_quality": priority in ["High", "Critical"]
        }
        
        # Add specific adjustments based on rejection reason
        if "quality" in rejection_reason.lower():
            params["quality_boost"] = True
            params["resolution_multiplier"] = 1.5
        
        if "multiple people" in rejection_reason.lower():
            params["single_person_emphasis"] = True
            params["composition_guidance"] = "single subject focus"
        
        if "background" in rejection_reason.lower():
            params["background_simplification"] = True
            params["isolation_priority"] = True
        
        if "character" in rejection_reason.lower() or "person" in rejection_reason.lower():
            params["character_consistency"] = True
            params["appearance_refinement"] = True
        
        return params
    
    def _record_user_feedback(self, user_id: UUID, correction_data: Dict[str, Any]):
        """
        Record user feedback for learning and improvement.
        
        Args:
            user_id: User identifier
            correction_data: User correction data
        """
        try:
            learning_data = LearningData(
                user_id=user_id,
                original_image_path=correction_data.get("original_image_path", ""),
                correction_type=correction_data.get("decision", "unknown"),
                user_decision=correction_data.get("decision", ""),
                crop_coordinates=correction_data.get("crop_coordinates"),
                rejection_reason=correction_data.get("rejection_reason"),
                suggested_modifications=correction_data.get("suggested_modifications"),
                processing_confidence=correction_data.get("confidence_score", 0.0),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # Cache learning data for batch processing
            self.learning_data_cache.append(learning_data)
            
            # Process learning data if cache is full
            if len(self.learning_data_cache) >= 10:
                self._process_learning_data_batch()
            
        except Exception as e:
            logger.error(f"Error recording user feedback: {e}")
    
    def _process_learning_data_batch(self):
        """Process batch of learning data for system improvement."""
        try:
            if not self.learning_data_cache:
                return
            
            # Analyze patterns in user corrections
            correction_patterns = self._analyze_correction_patterns()
            
            # Update system parameters based on patterns
            self._update_system_parameters(correction_patterns)
            
            # Clear cache
            self.learning_data_cache.clear()
            
            logger.info(f"Processed learning data batch with {len(correction_patterns)} patterns")
            
        except Exception as e:
            logger.error(f"Error processing learning data batch: {e}")
    
    def _analyze_correction_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in user corrections."""
        patterns = {
            "common_rejections": {},
            "frequent_crops": [],
            "quality_issues": {},
            "user_preferences": {}
        }
        
        for data in self.learning_data_cache:
            # Track rejection reasons
            if data.rejection_reason:
                reason = data.rejection_reason
                patterns["common_rejections"][reason] = patterns["common_rejections"].get(reason, 0) + 1
            
            # Track crop patterns
            if data.crop_coordinates:
                patterns["frequent_crops"].append(data.crop_coordinates)
            
            # Track quality issues
            if data.processing_confidence < 0.7:
                decision = data.user_decision
                patterns["quality_issues"][decision] = patterns["quality_issues"].get(decision, 0) + 1
        
        return patterns
    
    def _update_system_parameters(self, patterns: Dict[str, Any]):
        """Update system parameters based on learning patterns."""
        try:
            # This would update configuration or model parameters
            # For now, just log the insights
            
            common_rejections = patterns.get("common_rejections", {})
            if common_rejections:
                most_common = max(common_rejections.items(), key=lambda x: x[1])
                logger.info(f"Most common rejection reason: {most_common[0]} ({most_common[1]} times)")
            
            quality_issues = patterns.get("quality_issues", {})
            if quality_issues:
                logger.info(f"Quality issue patterns: {quality_issues}")
            
            # Future: Update isolation service parameters, quality thresholds, etc.
            
        except Exception as e:
            logger.error(f"Error updating system parameters: {e}")
    
    def _log_correction_result(
        self,
        user_id: UUID,
        correction_data: Dict[str, Any],
        result: CorrectionResult
    ):
        """Log correction result for audit trail."""
        try:
            audit_data = {
                "user_id": str(user_id),
                "action": "image_correction",
                "decision": correction_data.get("decision"),
                "success": result.success,
                "processing_method": result.processing_method,
                "processing_time": result.processing_time,
                "final_image_path": result.final_image_path,
                "regeneration_triggered": result.regeneration_triggered
            }
            
            if result.error_message:
                audit_data["error_message"] = result.error_message
            
            self.audit_service.log_user_action(
                user_id=user_id,
                action="image_correction_processed",
                details=audit_data
            )
            
        except Exception as e:
            logger.error(f"Error logging correction result: {e}")
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from accumulated learning data."""
        if not self.learning_data_cache:
            return {"message": "No learning data available"}
        
        patterns = self._analyze_correction_patterns()
        
        insights = {
            "total_corrections": len(self.learning_data_cache),
            "common_issues": patterns.get("common_rejections", {}),
            "quality_patterns": patterns.get("quality_issues", {}),
            "recommendations": self._generate_improvement_recommendations(patterns)
        }
        
        return insights
    
    def _generate_improvement_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate recommendations for system improvement."""
        recommendations = []
        
        common_rejections = patterns.get("common_rejections", {})
        
        if "quality" in str(common_rejections).lower():
            recommendations.append("Consider increasing default quality thresholds")
        
        if "multiple people" in str(common_rejections).lower():
            recommendations.append("Improve person detection sensitivity")
        
        if "background" in str(common_rejections).lower():
            recommendations.append("Enhance background removal algorithms")
        
        quality_issues = patterns.get("quality_issues", {})
        if "adjust" in quality_issues and quality_issues["adjust"] > 3:
            recommendations.append("Review automatic cropping algorithms")
        
        return recommendations