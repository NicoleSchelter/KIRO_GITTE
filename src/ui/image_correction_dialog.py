"""
Image Correction Dialog UI Components for GITTE system.
Provides interactive dialog for image correction and approval with accessibility support.
"""

import logging
import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CorrectionDialogState:
    """State management for correction dialog."""
    
    original_image_path: str
    processed_image_path: Optional[str]
    user_decision: Optional[str] = None
    crop_coordinates: Optional[Tuple[int, int, int, int]] = None
    rejection_reason: Optional[str] = None
    suggested_modifications: Optional[str] = None
    dialog_completed: bool = False


class ImageCorrectionDialog:
    """Interactive dialog for image correction and approval with accessibility support."""
    
    def __init__(self):
        """Initialize the correction dialog."""
        self.state = None
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state for dialog."""
        if 'correction_dialog_state' not in st.session_state:
            st.session_state.correction_dialog_state = None
        if 'crop_preview_enabled' not in st.session_state:
            st.session_state.crop_preview_enabled = False
    
    def render_correction_interface(
        self, 
        original_image_path: str, 
        processed_image_path: Optional[str] = None,
        isolation_success: bool = False,
        confidence_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Render the correction dialog interface with accessibility support.
        
        Args:
            original_image_path: Path to original generated image
            processed_image_path: Path to processed/isolated image (if available)
            isolation_success: Whether automatic isolation was successful
            confidence_score: Confidence score of automatic processing
            
        Returns:
            Dict containing user decisions and corrections
        """
        # Initialize or update state
        if (st.session_state.correction_dialog_state is None or 
            st.session_state.correction_dialog_state.original_image_path != original_image_path):
            st.session_state.correction_dialog_state = CorrectionDialogState(
                original_image_path=original_image_path,
                processed_image_path=processed_image_path
            )
        
        self.state = st.session_state.correction_dialog_state
        
        # Main dialog container with accessibility
        with st.container():
            st.markdown("""
            <div role="dialog" aria-labelledby="correction-dialog-title" aria-describedby="correction-dialog-desc">
            """, unsafe_allow_html=True)
            
            # Dialog header
            st.markdown('<h2 id="correction-dialog-title">🎨 Review Your Generated Avatar</h2>', 
                       unsafe_allow_html=True)
            st.markdown(
                '<p id="correction-dialog-desc">Review the automatically processed image and choose how to proceed.</p>',
                unsafe_allow_html=True
            )
            
            # Processing status indicator
            self._render_processing_status(isolation_success, confidence_score)
            
            # Side-by-side image comparison
            self._render_image_comparison()
            
            # User decision interface
            result = self._render_decision_interface()
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            return result
    
    def _render_processing_status(self, isolation_success: bool, confidence_score: float):
        """Render processing status with accessibility."""
        if isolation_success:
            status_color = "green" if confidence_score > 0.7 else "orange"
            status_icon = "✅" if confidence_score > 0.7 else "⚠️"
            status_text = f"Automatic processing completed (confidence: {confidence_score:.1%})"
        else:
            status_color = "red"
            status_icon = "❌"
            status_text = "Automatic processing failed - showing original image"
        
        st.markdown(f"""
        <div style="padding: 10px; border-left: 4px solid {status_color}; background-color: rgba(128,128,128,0.1); margin-bottom: 20px;" 
             role="status" aria-live="polite">
            {status_icon} {status_text}
        </div>
        """, unsafe_allow_html=True)
    
    def _render_image_comparison(self):
        """Render side-by-side image comparison with accessibility."""
        col1, col2 = st.columns(2)
        
        try:
            # Load images
            original_img = Image.open(self.state.original_image_path)
            
            with col1:
                st.markdown("**Original Generated Image**")
                st.image(
                    original_img, 
                    caption="Original image from generation",
                    use_column_width=True
                )
                
                # Image metadata for accessibility
                st.caption(f"Dimensions: {original_img.size[0]}×{original_img.size[1]} pixels")
            
            with col2:
                st.markdown("**Processed Image**")
                
                if self.state.processed_image_path and Path(self.state.processed_image_path).exists():
                    processed_img = Image.open(self.state.processed_image_path)
                    st.image(
                        processed_img, 
                        caption="Automatically isolated avatar",
                        use_column_width=True
                    )
                    st.caption(f"Dimensions: {processed_img.size[0]}×{processed_img.size[1]} pixels")
                else:
                    st.warning("⚠️ Processed image not available")
                    st.image(
                        original_img, 
                        caption="Original image (fallback)",
                        use_column_width=True
                    )
                    st.caption("Using original image as fallback")
                    
        except Exception as e:
            logger.error(f"Error loading images for correction dialog: {e}")
            st.error("❌ Error loading images. Please try regenerating.")
    
    def _render_decision_interface(self) -> Dict[str, Any]:
        """Render user decision interface with keyboard navigation support."""
        st.markdown("### What would you like to do?")
        
        # Decision options with accessibility
        decision_options = [
            ("accept", "✅ Accept processed image", "Use the automatically processed image as your avatar"),
            ("adjust", "✂️ Adjust crop/selection", "Manually adjust the image cropping or selection area"),
            ("original", "📷 Use original image", "Use the original generated image without processing"),
            ("regenerate", "🔄 Mark as garbage and regenerate", "Reject this image and generate a new one")
        ]
        
        # Radio button selection with help text
        decision_labels = [label for _, label, _ in decision_options]
        decision_helps = [help_text for _, _, help_text in decision_options]
        
        selected_index = st.radio(
            "Choose an option:",
            range(len(decision_options)),
            format_func=lambda i: decision_labels[i],
            help="Use arrow keys to navigate options, space to select",
            key="correction_decision"
        )
        
        # Show help text for selected option
        if selected_index is not None:
            st.info(f"ℹ️ {decision_helps[selected_index]}")
        
        decision_key = decision_options[selected_index][0]
        self.state.user_decision = decision_key
        
        result = {"decision": decision_key}
        
        # Render specific interfaces based on decision
        if decision_key == "adjust":
            result.update(self._render_crop_adjustment())
        elif decision_key == "regenerate":
            result.update(self._render_regeneration_options())
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("⬅️ Back", help="Return to previous step"):
                result["action"] = "back"
        
        with col2:
            if st.button("🔄 Reset", help="Reset all selections"):
                self._reset_dialog_state()
                st.rerun()
        
        with col3:
            confirm_disabled = decision_key == "adjust" and not st.session_state.crop_preview_enabled
            confirm_help = "Preview crop first" if confirm_disabled else "Confirm your selection and proceed"
            
            if st.button(
                "✅ Confirm", 
                disabled=confirm_disabled,
                help=confirm_help,
                type="primary"
            ):
                result["action"] = "confirm"
                self.state.dialog_completed = True
        
        return result
    
    def _render_crop_adjustment(self) -> Dict[str, Any]:
        """Render interactive crop adjustment interface with accessibility."""
        st.markdown("#### 🎯 Adjust Selection Area")
        st.markdown("Use the controls below to adjust the crop area. Changes will be previewed in real-time.")
        
        try:
            image = Image.open(self.state.original_image_path)
            img_width, img_height = image.size
            
            # Crop parameter controls with accessibility
            st.markdown("**Crop Boundaries**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                left = st.slider(
                    "Left edge", 
                    min_value=0, 
                    max_value=img_width-1, 
                    value=0,
                    help="Left boundary of the crop area",
                    key="crop_left"
                )
                top = st.slider(
                    "Top edge", 
                    min_value=0, 
                    max_value=img_height-1, 
                    value=0,
                    help="Top boundary of the crop area",
                    key="crop_top"
                )
            
            with col2:
                right = st.slider(
                    "Right edge", 
                    min_value=left+1, 
                    max_value=img_width, 
                    value=img_width,
                    help="Right boundary of the crop area",
                    key="crop_right"
                )
                bottom = st.slider(
                    "Bottom edge", 
                    min_value=top+1, 
                    max_value=img_height, 
                    value=img_height,
                    help="Bottom boundary of the crop area",
                    key="crop_bottom"
                )
            
            # Crop dimensions display
            crop_width = right - left
            crop_height = bottom - top
            st.info(f"📏 Crop dimensions: {crop_width}×{crop_height} pixels")
            
            # Preview controls
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("👁️ Preview Crop", help="Generate preview of the cropped image"):
                    self._generate_crop_preview(image, (left, top, right, bottom))
                    st.session_state.crop_preview_enabled = True
                    st.rerun()
            
            with col2:
                if st.button("🔄 Reset Crop", help="Reset crop to full image"):
                    st.session_state.crop_left = 0
                    st.session_state.crop_top = 0
                    st.session_state.crop_right = img_width
                    st.session_state.crop_bottom = img_height
                    st.session_state.crop_preview_enabled = False
                    st.rerun()
            
            # Show preview if available
            if st.session_state.crop_preview_enabled:
                self._display_crop_preview()
            
            self.state.crop_coordinates = (left, top, right, bottom)
            
            return {
                "crop_coordinates": (left, top, right, bottom),
                "crop_dimensions": (crop_width, crop_height),
                "preview_generated": st.session_state.crop_preview_enabled
            }
            
        except Exception as e:
            logger.error(f"Error in crop adjustment interface: {e}")
            st.error("❌ Error loading image for cropping. Please try using the original image.")
            return {"error": str(e)}
    
    def _generate_crop_preview(self, image: Image.Image, coordinates: Tuple[int, int, int, int]):
        """Generate and store crop preview."""
        try:
            left, top, right, bottom = coordinates
            cropped = image.crop((left, top, right, bottom))
            
            # Store preview in session state
            st.session_state.crop_preview_image = cropped
            
        except Exception as e:
            logger.error(f"Error generating crop preview: {e}")
            st.error("❌ Error generating crop preview")
    
    def _display_crop_preview(self):
        """Display the crop preview with accessibility."""
        if 'crop_preview_image' in st.session_state:
            st.markdown("**🔍 Crop Preview**")
            st.image(
                st.session_state.crop_preview_image,
                caption="Preview of cropped area",
                use_column_width=True
            )
            
            # Preview metadata
            preview_img = st.session_state.crop_preview_image
            st.caption(f"Preview dimensions: {preview_img.size[0]}×{preview_img.size[1]} pixels")
    
    def _render_regeneration_options(self) -> Dict[str, Any]:
        """Render options for image regeneration with accessibility."""
        st.markdown("#### 🔄 Regeneration Options")
        st.markdown("Help us understand what went wrong so we can generate a better image.")
        
        # Reason selection with accessibility
        reason_options = [
            "Wrong person/character appearance",
            "Poor image quality (blurry, distorted)",
            "Inappropriate or unwanted content",
            "Multiple people in image",
            "Background or composition issues",
            "Other (please specify)"
        ]
        
        reason = st.selectbox(
            "Why is this image unsuitable?",
            options=reason_options,
            help="Select the primary reason for rejecting this image",
            key="rejection_reason"
        )
        
        # Custom reason input
        custom_reason = None
        if reason == "Other (please specify)":
            custom_reason = st.text_input(
                "Please specify the issue:",
                help="Describe what's wrong with the image",
                key="custom_rejection_reason"
            )
            if custom_reason:
                reason = custom_reason
        
        # Improvement suggestions
        modifications = st.text_area(
            "Suggested improvements for regeneration:",
            placeholder="Describe what should be different in the new image (e.g., 'make the person younger', 'use better lighting', 'simpler background')...",
            help="Provide specific guidance for generating a better image",
            key="suggested_modifications"
        )
        
        # Priority level
        priority = st.select_slider(
            "How important is getting this right?",
            options=["Low", "Medium", "High", "Critical"],
            value="Medium",
            help="Higher priority may use more resources for better results",
            key="regeneration_priority"
        )
        
        self.state.rejection_reason = reason
        self.state.suggested_modifications = modifications
        
        return {
            "rejection_reason": reason,
            "custom_reason": custom_reason,
            "suggested_modifications": modifications,
            "priority": priority
        }
    
    def _reset_dialog_state(self):
        """Reset dialog state for fresh start."""
        # Clear session state
        keys_to_clear = [
            'correction_decision',
            'crop_left', 'crop_top', 'crop_right', 'crop_bottom',
            'crop_preview_enabled', 'crop_preview_image',
            'rejection_reason', 'custom_rejection_reason',
            'suggested_modifications', 'regeneration_priority'
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Reset state object
        if self.state:
            self.state.user_decision = None
            self.state.crop_coordinates = None
            self.state.rejection_reason = None
            self.state.suggested_modifications = None
            self.state.dialog_completed = False
    
    def is_dialog_completed(self) -> bool:
        """Check if dialog has been completed."""
        return self.state and self.state.dialog_completed
    
    def get_final_result(self) -> Dict[str, Any]:
        """Get the final result of the correction dialog."""
        if not self.state or not self.state.dialog_completed:
            return {"completed": False}
        
        result = {
            "completed": True,
            "decision": self.state.user_decision,
            "original_image_path": self.state.original_image_path,
            "processed_image_path": self.state.processed_image_path
        }
        
        if self.state.crop_coordinates:
            result["crop_coordinates"] = self.state.crop_coordinates
        
        if self.state.rejection_reason:
            result["rejection_reason"] = self.state.rejection_reason
        
        if self.state.suggested_modifications:
            result["suggested_modifications"] = self.state.suggested_modifications
        
        return result