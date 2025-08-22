"""
Image Quality Detection Service for GITTE system.
Provides comprehensive faulty image detection and quality validation capabilities.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageStat

logger = logging.getLogger(__name__)


class FaultyImageReason(Enum):
    """Reasons why an image might be considered faulty."""
    
    NO_PERSON_DETECTED = "no_person_detected"
    MULTIPLE_PEOPLE_DETECTED = "multiple_people_detected"
    WRONG_SUBJECT_TYPE = "wrong_subject_type"
    POOR_QUALITY = "poor_quality"
    IMAGE_TOO_BLURRY = "image_too_blurry"
    IMAGE_TOO_NOISY = "image_too_noisy"
    POOR_BRIGHTNESS = "poor_brightness"
    LOW_CONTRAST = "low_contrast"
    CORRUPTED_IMAGE = "corrupted_image"
    INVALID_FORMAT = "invalid_format"


@dataclass
class QualityDetectionConfig:
    """Configuration for quality detection."""
    
    enabled: bool = True
    min_person_confidence: float = 0.8
    max_people_allowed: int = 1
    min_quality_score: float = 0.6
    blur_threshold: float = 0.3
    noise_threshold: float = 0.1
    min_brightness: float = 0.1
    max_brightness: float = 0.9
    min_contrast: float = 0.2
    min_image_size: Tuple[int, int] = (256, 256)
    max_image_size: Tuple[int, int] = (2048, 2048)
    supported_formats: List[str] = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']


@dataclass
class DetectionResult:
    """Result of faulty image detection."""
    
    is_faulty: bool
    reasons: List[FaultyImageReason]
    confidence_score: float
    quality_metrics: Dict[str, float]
    person_count: int
    processing_time: float
    recommendations: List[str]
    details: Optional[str] = None


@dataclass
class BatchProcessingResult:
    """Result of batch image processing analysis."""
    
    total_images: int
    faulty_images: int
    faulty_percentage: float
    should_regenerate: bool
    common_issues: List[FaultyImageReason]
    batch_quality_score: float
    processing_time: float


class ImageQualityDetector:
    """Detector for image quality and content validation."""
    
    def __init__(self, config: QualityDetectionConfig):
        """
        Initialize image quality detector.
        
        Args:
            config: Configuration for quality detection
        """
        self.config = config
        self.person_classifier = self._load_person_classifier()
        self.quality_analyzer = self._load_quality_analyzer()
        
    def detect_faulty_image(self, image_path: str) -> DetectionResult:
        """
        Comprehensive faulty image detection.
        
        Args:
            image_path: Path to image to analyze
            
        Returns:
            DetectionResult with detailed analysis
        """
        start_time = time.time()
        
        try:
            if not self.config.enabled:
                return DetectionResult(
                    is_faulty=False,
                    reasons=[],
                    confidence_score=1.0,
                    quality_metrics={},
                    person_count=1,
                    processing_time=0.0,
                    recommendations=["Quality detection is disabled"]
                )
            
            # Basic file validation
            file_validation = self._validate_image_file(image_path)
            if file_validation["is_faulty"]:
                return DetectionResult(
                    is_faulty=True,
                    reasons=file_validation["reasons"],
                    confidence_score=1.0,
                    quality_metrics={},
                    person_count=0,
                    processing_time=time.time() - start_time,
                    recommendations=file_validation["recommendations"],
                    details=file_validation["details"]
                )
            
            # Load and validate image
            image = cv2.imread(image_path)
            if image is None:
                return DetectionResult(
                    is_faulty=True,
                    reasons=[FaultyImageReason.CORRUPTED_IMAGE],
                    confidence_score=1.0,
                    quality_metrics={},
                    person_count=0,
                    processing_time=time.time() - start_time,
                    recommendations=["Regenerate image with different parameters"],
                    details="Could not load image file"
                )
            
            # Perform comprehensive analysis
            reasons = []
            quality_metrics = {}
            recommendations = []
            
            # Person detection analysis
            person_analysis = self.detect_people(image_path)
            quality_metrics.update(person_analysis["metrics"])
            
            if not person_analysis["person_detected"]:
                reasons.append(FaultyImageReason.NO_PERSON_DETECTED)
                recommendations.append("Adjust prompt to emphasize person/character generation")
            elif person_analysis["person_count"] > self.config.max_people_allowed:
                reasons.append(FaultyImageReason.MULTIPLE_PEOPLE_DETECTED)
                recommendations.append("Use more specific prompts to generate single person")
            
            # Subject type validation
            subject_analysis = self.validate_subject_type(image_path)
            quality_metrics.update(subject_analysis["metrics"])
            
            if not subject_analysis["is_person"]:
                reasons.append(FaultyImageReason.WRONG_SUBJECT_TYPE)
                recommendations.append("Modify prompt to focus on human subjects")
            
            # Image quality assessment
            quality_analysis = self.assess_image_quality(image_path)
            quality_metrics.update(quality_analysis["metrics"])
            
            # Check individual quality metrics
            if quality_analysis["blur_score"] < self.config.blur_threshold:
                reasons.append(FaultyImageReason.IMAGE_TOO_BLURRY)
                recommendations.append("Increase image resolution or adjust generation parameters")
            
            if quality_analysis["noise_score"] > self.config.noise_threshold:
                reasons.append(FaultyImageReason.IMAGE_TOO_NOISY)
                recommendations.append("Use denoising in post-processing or adjust model settings")
            
            brightness = quality_analysis["brightness_score"]
            if brightness < self.config.min_brightness or brightness > self.config.max_brightness:
                reasons.append(FaultyImageReason.POOR_BRIGHTNESS)
                recommendations.append("Adjust lighting conditions in prompt")
            
            if quality_analysis["contrast_score"] < self.config.min_contrast:
                reasons.append(FaultyImageReason.LOW_CONTRAST)
                recommendations.append("Enhance contrast in prompt or post-processing")
            
            # Calculate overall confidence score
            confidence_score = self._calculate_confidence_score(quality_metrics, reasons)
            
            # Determine if image is faulty
            is_faulty = (
                len(reasons) > 0 or 
                confidence_score < self.config.min_quality_score
            )
            
            processing_time = time.time() - start_time
            
            # Log detection results for audit trail
            self._log_detection_result(
                image_path, is_faulty, reasons, confidence_score, 
                quality_metrics, processing_time
            )
            
            return DetectionResult(
                is_faulty=is_faulty,
                reasons=reasons,
                confidence_score=confidence_score,
                quality_metrics=quality_metrics,
                person_count=person_analysis["person_count"],
                processing_time=processing_time,
                recommendations=recommendations,
                details=f"Overall quality score: {quality_analysis['overall_score']:.2f}"
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Faulty image detection failed for {image_path}: {e}")
            
            return DetectionResult(
                is_faulty=True,
                reasons=[FaultyImageReason.CORRUPTED_IMAGE],
                confidence_score=0.0,
                quality_metrics={},
                person_count=0,
                processing_time=processing_time,
                recommendations=["Regenerate image due to processing error"],
                details=f"Detection error: {str(e)}"
            )
    
    def detect_people(self, image_path: str) -> Dict:
        """
        Detect people in image and return count and bounding boxes.
        
        Args:
            image_path: Path to image to analyze
            
        Returns:
            Dict with detection results and metrics
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "person_detected": False,
                    "person_count": 0,
                    "confidence": 0.0,
                    "bounding_boxes": [],
                    "metrics": {"person_detection_confidence": 0.0}
                }
            
            # Use HOG descriptor for person detection
            if self.person_classifier is not None:
                (rects, weights) = self.person_classifier.detectMultiScale(
                    image,
                    winStride=(4, 4),
                    padding=(8, 8),
                    scale=1.05
                )
                
                # Filter by confidence threshold
                confident_detections = [
                    (rect, weight) for rect, weight in zip(rects, weights)
                    if weight >= self.config.min_person_confidence
                ]
                
                person_count = len(confident_detections)
                max_confidence = max(weights) if len(weights) > 0 else 0.0
                
                return {
                    "person_detected": person_count > 0,
                    "person_count": person_count,
                    "confidence": float(max_confidence),
                    "bounding_boxes": confident_detections,
                    "metrics": {
                        "person_detection_confidence": float(max_confidence),
                        "detected_person_count": person_count
                    }
                }
            else:
                # Fallback: use simple heuristics
                return self._fallback_person_detection(image)
                
        except Exception as e:
            logger.error(f"Person detection failed: {e}")
            return {
                "person_detected": False,
                "person_count": 0,
                "confidence": 0.0,
                "bounding_boxes": [],
                "metrics": {"person_detection_confidence": 0.0}
            }
    
    def assess_image_quality(self, image_path: str) -> Dict:
        """
        Assess overall image quality (blur, noise, corruption).
        
        Args:
            image_path: Path to image to analyze
            
        Returns:
            Dict with quality metrics and scores
        """
        try:
            # Load image in both OpenCV and PIL formats
            cv_image = cv2.imread(image_path)
            pil_image = Image.open(image_path)
            
            if cv_image is None or pil_image is None:
                return {
                    "blur_score": 0.0,
                    "noise_score": 1.0,
                    "brightness_score": 0.0,
                    "contrast_score": 0.0,
                    "overall_score": 0.0,
                    "metrics": {}
                }
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Blur detection using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_score = min(1.0, laplacian_var / 1000.0)
            
            # Noise estimation using local standard deviation
            noise_score = self._estimate_noise(gray)
            
            # Brightness assessment
            brightness_score = np.mean(gray) / 255.0
            
            # Contrast assessment using standard deviation
            contrast_score = np.std(gray) / 255.0
            
            # Sharpness assessment using gradient magnitude
            sharpness_score = self._assess_sharpness(gray)
            
            # Color distribution analysis (for PIL image)
            color_metrics = self._analyze_color_distribution(pil_image)
            
            # Calculate overall quality score
            overall_score = float(
                blur_score * 0.25 +
                (1.0 - noise_score) * 0.20 +
                min(brightness_score, 1.0 - brightness_score) * 2 * 0.15 +
                contrast_score * 0.20 +
                sharpness_score * 0.20
            )
            
            metrics = {
                "blur_score": float(blur_score),
                "noise_score": float(noise_score),
                "brightness_score": float(brightness_score),
                "contrast_score": float(contrast_score),
                "sharpness_score": float(sharpness_score),
                "overall_quality_score": float(overall_score),
                **color_metrics
            }
            
            return {
                "blur_score": float(blur_score),
                "noise_score": float(noise_score),
                "brightness_score": float(brightness_score),
                "contrast_score": float(contrast_score),
                "sharpness_score": float(sharpness_score),
                "overall_score": float(overall_score),
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Image quality assessment failed: {e}")
            return {
                "blur_score": 0.0,
                "noise_score": 1.0,
                "brightness_score": 0.0,
                "contrast_score": 0.0,
                "overall_score": 0.0,
                "metrics": {}
            }
    
    def validate_subject_type(self, image_path: str) -> Dict:
        """
        Validate that image contains appropriate subject (person).
        
        Args:
            image_path: Path to image to analyze
            
        Returns:
            Dict with subject validation results
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "is_person": False,
                    "confidence": 0.0,
                    "detected_objects": [],
                    "metrics": {"subject_validation_confidence": 0.0}
                }
            
            # Use person detection as primary subject validation
            person_detection = self.detect_people(image_path)
            
            # Additional heuristics for subject validation
            subject_confidence = person_detection["confidence"]
            
            # Analyze image composition for human-like features
            composition_score = self._analyze_human_composition(image)
            
            # Combine scores
            final_confidence = float(subject_confidence * 0.7 + composition_score * 0.3)
            
            is_person = bool(
                person_detection["person_detected"] and 
                final_confidence >= self.config.min_person_confidence
            )
            
            return {
                "is_person": is_person,
                "confidence": final_confidence,
                "detected_objects": ["person"] if is_person else ["unknown"],
                "metrics": {
                    "subject_validation_confidence": float(final_confidence),
                    "composition_score": float(composition_score)
                }
            }
            
        except Exception as e:
            logger.error(f"Subject type validation failed: {e}")
            return {
                "is_person": False,
                "confidence": 0.0,
                "detected_objects": [],
                "metrics": {"subject_validation_confidence": 0.0}
            }
    
    def analyze_batch_processing(self, image_paths: List[str]) -> BatchProcessingResult:
        """
        Analyze batch of images for automatic regeneration decision.
        
        Args:
            image_paths: List of image paths to analyze
            
        Returns:
            BatchProcessingResult with batch analysis
        """
        start_time = time.time()
        
        try:
            if not image_paths:
                return BatchProcessingResult(
                    total_images=0,
                    faulty_images=0,
                    faulty_percentage=0.0,
                    should_regenerate=False,
                    common_issues=[],
                    batch_quality_score=0.0,
                    processing_time=0.0
                )
            
            # Analyze each image
            results = []
            for image_path in image_paths:
                result = self.detect_faulty_image(image_path)
                results.append(result)
            
            # Calculate batch statistics
            total_images = len(results)
            faulty_images = sum(1 for r in results if r.is_faulty)
            faulty_percentage = (faulty_images / total_images) * 100
            
            # Calculate average quality score
            quality_scores = [r.confidence_score for r in results if r.confidence_score > 0]
            batch_quality_score = np.mean(quality_scores) if quality_scores else 0.0
            
            # Find common issues
            all_reasons = []
            for result in results:
                all_reasons.extend(result.reasons)
            
            # Count reason frequencies
            reason_counts = {}
            for reason in all_reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            # Get most common issues (appearing in >30% of faulty images)
            common_threshold = max(1, faulty_images * 0.3)
            common_issues = [
                reason for reason, count in reason_counts.items()
                if count >= common_threshold
            ]
            
            # Decide if regeneration is needed
            should_regenerate = (
                faulty_percentage > 70 or  # More than 70% faulty
                batch_quality_score < 0.4 or  # Very low quality
                FaultyImageReason.NO_PERSON_DETECTED in common_issues or
                FaultyImageReason.CORRUPTED_IMAGE in common_issues
            )
            
            processing_time = time.time() - start_time
            
            return BatchProcessingResult(
                total_images=total_images,
                faulty_images=faulty_images,
                faulty_percentage=faulty_percentage,
                should_regenerate=should_regenerate,
                common_issues=common_issues,
                batch_quality_score=batch_quality_score,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Batch processing analysis failed: {e}")
            
            return BatchProcessingResult(
                total_images=len(image_paths),
                faulty_images=len(image_paths),
                faulty_percentage=100.0,
                should_regenerate=True,
                common_issues=[FaultyImageReason.CORRUPTED_IMAGE],
                batch_quality_score=0.0,
                processing_time=processing_time
            )
    
    def _load_person_classifier(self):
        """Load person detection classifier."""
        try:
            # Initialize HOG descriptor for person detection
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            return hog
        except Exception as e:
            logger.warning(f"Failed to load person classifier: {e}")
            return None
    
    def _load_quality_analyzer(self):
        """Load quality analysis models."""
        # Placeholder for future ML-based quality analysis models
        return None
    
    def _validate_image_file(self, image_path: str) -> Dict:
        """Validate image file format and basic properties."""
        try:
            path = Path(image_path)
            
            # Check if file exists
            if not path.exists():
                return {
                    "is_faulty": True,
                    "reasons": [FaultyImageReason.CORRUPTED_IMAGE],
                    "recommendations": ["Ensure image file exists"],
                    "details": "Image file not found"
                }
            
            # Check file extension
            if path.suffix.lower() not in self.config.supported_formats:
                return {
                    "is_faulty": True,
                    "reasons": [FaultyImageReason.INVALID_FORMAT],
                    "recommendations": [f"Use supported formats: {self.config.supported_formats}"],
                    "details": f"Unsupported format: {path.suffix}"
                }
            
            # Check file size (basic validation)
            file_size = path.stat().st_size
            if file_size == 0:
                return {
                    "is_faulty": True,
                    "reasons": [FaultyImageReason.CORRUPTED_IMAGE],
                    "recommendations": ["Regenerate image"],
                    "details": "Empty image file"
                }
            
            # Try to get image dimensions
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    
                    # Check minimum size
                    if width < self.config.min_image_size[0] or height < self.config.min_image_size[1]:
                        return {
                            "is_faulty": True,
                            "reasons": [FaultyImageReason.POOR_QUALITY],
                            "recommendations": ["Increase image resolution"],
                            "details": f"Image too small: {width}x{height}"
                        }
                    
                    # Check maximum size
                    if width > self.config.max_image_size[0] or height > self.config.max_image_size[1]:
                        return {
                            "is_faulty": True,
                            "reasons": [FaultyImageReason.POOR_QUALITY],
                            "recommendations": ["Reduce image size for processing"],
                            "details": f"Image too large: {width}x{height}"
                        }
            
            except Exception:
                return {
                    "is_faulty": True,
                    "reasons": [FaultyImageReason.CORRUPTED_IMAGE],
                    "recommendations": ["Regenerate image"],
                    "details": "Cannot read image dimensions"
                }
            
            return {
                "is_faulty": False,
                "reasons": [],
                "recommendations": [],
                "details": "File validation passed"
            }
            
        except Exception as e:
            return {
                "is_faulty": True,
                "reasons": [FaultyImageReason.CORRUPTED_IMAGE],
                "recommendations": ["Check file integrity"],
                "details": f"Validation error: {str(e)}"
            }
    
    def _fallback_person_detection(self, image: np.ndarray) -> Dict:
        """Fallback person detection using simple heuristics."""
        height, width = image.shape[:2]
        
        # Simple heuristic based on image composition
        # Look for vertical structures that might be people
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Look for vertical lines (potential person silhouettes)
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, height // 4))
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        # Count significant vertical structures
        contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size and aspect ratio
        person_like_contours = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = h / w if w > 0 else 0
            area = cv2.contourArea(contour)
            
            # Heuristic: person-like if tall and reasonably sized
            if aspect_ratio > 1.5 and area > (width * height * 0.05):
                person_like_contours.append(contour)
        
        person_count = len(person_like_contours)
        confidence = min(0.6, person_count * 0.3) if person_count > 0 else 0.2
        
        return {
            "person_detected": person_count > 0,
            "person_count": person_count,
            "confidence": confidence,
            "bounding_boxes": [],
            "metrics": {
                "person_detection_confidence": confidence,
                "detected_person_count": person_count
            }
        }
    
    def _estimate_noise(self, gray_image: np.ndarray) -> float:
        """Estimate noise level in grayscale image."""
        # Use local standard deviation method
        kernel = np.ones((5, 5), np.float32) / 25
        mean_filtered = cv2.filter2D(gray_image.astype(np.float32), -1, kernel)
        noise_map = np.abs(gray_image.astype(np.float32) - mean_filtered)
        noise_score = np.mean(noise_map) / 255.0
        
        return min(1.0, noise_score)
    
    def _assess_sharpness(self, gray_image: np.ndarray) -> float:
        """Assess image sharpness using gradient magnitude."""
        # Sobel gradients
        grad_x = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
        
        # Gradient magnitude
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        sharpness_score = np.mean(gradient_magnitude) / 255.0
        
        return min(1.0, sharpness_score)
    
    def _analyze_color_distribution(self, pil_image: Image.Image) -> Dict[str, float]:
        """Analyze color distribution in PIL image."""
        try:
            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Get image statistics
            stat = ImageStat.Stat(pil_image)
            
            # Calculate color metrics
            mean_colors = stat.mean
            std_colors = stat.stddev
            
            # Color balance (how balanced are the RGB channels)
            color_balance = 1.0 - (np.std(mean_colors) / np.mean(mean_colors)) if np.mean(mean_colors) > 0 else 0.0
            
            # Color richness (standard deviation across channels)
            color_richness = np.mean(std_colors) / 255.0
            
            return {
                "color_balance": float(color_balance),
                "color_richness": float(color_richness),
                "mean_red": float(mean_colors[0]) / 255.0,
                "mean_green": float(mean_colors[1]) / 255.0,
                "mean_blue": float(mean_colors[2]) / 255.0
            }
            
        except Exception as e:
            logger.warning(f"Color distribution analysis failed: {e}")
            return {
                "color_balance": 0.5,
                "color_richness": 0.5,
                "mean_red": 0.5,
                "mean_green": 0.5,
                "mean_blue": 0.5
            }
    
    def _analyze_human_composition(self, image: np.ndarray) -> float:
        """Analyze image composition for human-like features."""
        try:
            height, width = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Look for face-like regions using Haar cascades (if available)
            try:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                face_score = min(1.0, len(faces) * 0.5) if len(faces) > 0 else 0.0
            except Exception:
                face_score = 0.0
            
            # Look for skin-tone regions (simple heuristic)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Define skin color range in HSV
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([20, 255, 255], dtype=np.uint8)
            
            skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
            skin_percentage = np.sum(skin_mask > 0) / (width * height)
            skin_score = min(1.0, skin_percentage * 5)  # Scale up skin percentage
            
            # Combine scores
            composition_score = (face_score * 0.6 + skin_score * 0.4)
            
            return composition_score
            
        except Exception as e:
            logger.warning(f"Human composition analysis failed: {e}")
            return 0.3  # Default moderate score
    
    def _calculate_confidence_score(self, quality_metrics: Dict[str, float], reasons: List[FaultyImageReason]) -> float:
        """Calculate overall confidence score based on metrics and detected issues."""
        # Start with base score from quality metrics
        base_score = quality_metrics.get("overall_quality_score", 0.5)
        
        # Apply penalties for detected issues
        penalty = 0.0
        for reason in reasons:
            if reason in [FaultyImageReason.NO_PERSON_DETECTED, FaultyImageReason.CORRUPTED_IMAGE]:
                penalty += 0.4  # Major issues
            elif reason in [FaultyImageReason.MULTIPLE_PEOPLE_DETECTED, FaultyImageReason.WRONG_SUBJECT_TYPE]:
                penalty += 0.3  # Significant issues
            else:
                penalty += 0.1  # Minor quality issues
        
        # Calculate final confidence score
        confidence_score = max(0.0, base_score - penalty)
        
        return confidence_score
    
    def _log_detection_result(
        self, 
        image_path: str, 
        is_faulty: bool, 
        reasons: List[FaultyImageReason], 
        confidence_score: float,
        quality_metrics: Dict[str, float],
        processing_time: float
    ):
        """Log detection results for audit trail."""
        log_data = {
            "image_path": image_path,
            "is_faulty": is_faulty,
            "reasons": [reason.value for reason in reasons],
            "confidence_score": confidence_score,
            "processing_time": processing_time,
            "quality_metrics": quality_metrics
        }
        
        if is_faulty:
            logger.warning(f"Faulty image detected: {image_path}", extra=log_data)
        else:
            logger.info(f"Image quality validation passed: {image_path}", extra=log_data)