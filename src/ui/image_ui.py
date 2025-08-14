"""
Image generation UI components for GITTE system.
Provides Streamlit components for avatar creation and image generation.
"""

import logging
from typing import Any
from uuid import UUID

import streamlit as st
from PIL import Image

from config.config import get_text
from src.data.models import ConsentType
from src.logic.embodiment import EmbodimentRequest, get_embodiment_logic
from src.services.consent_service import get_consent_service
from src.services.image_provider import ImageProviderError
from src.services.image_service import get_image_service

logger = logging.getLogger(__name__)


class ImageGenerationUI:
    """UI components for image generation and avatar creation."""

    def __init__(self):
        self.embodiment_logic = get_embodiment_logic()
        self.consent_service = get_consent_service()
        self.image_service = get_image_service()

    def render_image_generation_interface(
        self, user_id: UUID, embodiment_data: dict[str, Any] | None = None
    ) -> str | None:
        """
        Render the main image generation interface with enhanced accessibility.

        Args:
            user_id: User identifier
            embodiment_data: Embodiment characteristics data

        Returns:
            Generated image path if successful, None otherwise
        """
        # Check consent for image generation
        if not self._check_image_consent(user_id):
            return None

        # Add semantic structure for screen readers
        st.markdown('<main role="main" id="main-content">', unsafe_allow_html=True)
        
        st.title(get_text("image_generation_title"))
        
        # Add description for screen readers
        st.markdown(
            """
            <div class="sr-only">
                Image generation interface. Create visual representations of your personalized learning assistant.
                You can generate images from your embodiment design, use custom prompts, or create variations.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(
            """
        Generate visual representations of your personalized learning assistant! 
        You can use your embodiment design or create custom prompts.
        """
        )
        
        # Add accessibility notice
        st.info(
            "🔍 **Accessibility Note:** All generated images will include alternative text descriptions. "
            "If you have visual impairments, the system will provide detailed descriptions of generated avatars."
        )

        # Generation options with enhanced accessibility
        st.markdown("### 🎨 Generation Options")
        
        generation_mode = st.radio(
            "Generation Mode",
            options=["From Embodiment Design", "Custom Prompt", "Variations"],
            help="Choose how you want to generate your avatar. Each option provides different ways to create your learning assistant's visual representation.",
            key="generation_mode_radio"
        )
        
        # Add descriptions for each mode
        mode_descriptions = {
            "From Embodiment Design": "Use your previously designed embodiment characteristics to automatically generate an avatar that matches your learning assistant's personality and style.",
            "Custom Prompt": "Write a detailed description of how you want your avatar to look. This gives you full creative control over the appearance.",
            "Variations": "Create multiple versions based on an existing image, exploring different styles, expressions, or characteristics."
        }
        
        st.markdown(
            f"""
            <div class="generation-mode-description" role="region" aria-label="Selected mode description">
                <p><strong>Selected:</strong> {generation_mode}</p>
                <p>{mode_descriptions[generation_mode]}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Render the selected generation mode
        result = None
        if generation_mode == "From Embodiment Design":
            result = self._render_embodiment_generation(user_id, embodiment_data)
        elif generation_mode == "Custom Prompt":
            result = self._render_custom_prompt_generation(user_id)
        else:  # Variations
            result = self._render_variation_generation(user_id)
        
        # Close main content area
        st.markdown('</main>', unsafe_allow_html=True)
        
        return result

    def render_image_gallery(self, user_id: UUID) -> None:
        """
        Render gallery of generated images for the user.

        Args:
            user_id: User identifier
        """
        st.subheader("🖼️ Your Avatar Gallery")

        # Get user's generated images
        generated_images = self._get_user_images(user_id)

        if not generated_images:
            st.info("No images generated yet. Create your first avatar above!")
            return

        # Display images in grid
        cols = st.columns(3)

        for i, image_info in enumerate(generated_images):
            col_idx = i % 3

            with cols[col_idx]:
                try:
                    # Display image
                    image = Image.open(image_info["path"])
                    st.image(image, caption=f"Generated {image_info['created_at']}")

                    # Image actions
                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("Download", key=f"download_{i}"):
                            self._download_image(image_info)

                    with col2:
                        if st.button("Delete", key=f"delete_{i}"):
                            self._delete_image(user_id, image_info["id"])
                            st.rerun()

                    # Show generation details
                    with st.expander("Details", expanded=False):
                        st.write(f"**Prompt:** {image_info.get('prompt', 'N/A')}")
                        st.write(f"**Model:** {image_info.get('model', 'N/A')}")
                        st.write(f"**Parameters:** {image_info.get('parameters', {})}")

                except Exception as e:
                    st.error(f"Error loading image: {e}")

    def render_image_customization(self, user_id: UUID, base_image_path: str) -> str | None:
        """
        Render image customization interface.

        Args:
            user_id: User identifier
            base_image_path: Path to base image for customization

        Returns:
            Path to customized image if successful
        """
        st.subheader("🎨 Customize Your Avatar")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Original Image**")
            try:
                original_image = Image.open(base_image_path)
                st.image(original_image, caption="Original")
            except Exception as e:
                st.error(f"Error loading original image: {e}")
                return None

        with col2:
            st.write("**Customization Options**")

            # Style modifications
            style_changes = st.multiselect(
                "Style modifications",
                options=[
                    "More professional",
                    "More casual",
                    "More colorful",
                    "More minimalist",
                    "Different age",
                    "Different expression",
                ],
            )

            # Custom modifications
            custom_modifications = st.text_area(
                "Custom modifications",
                placeholder="Describe specific changes you'd like...",
                help="Be specific about what you want to change",
            )

            # Generation parameters
            with st.expander("Advanced Parameters"):
                strength = st.slider(
                    "Modification strength",
                    min_value=0.1,
                    max_value=1.0,
                    value=0.7,
                    step=0.1,
                    help="How much to modify the original image",
                )

                guidance_scale = st.slider(
                    "Guidance scale",
                    min_value=1.0,
                    max_value=20.0,
                    value=7.5,
                    step=0.5,
                    help="How closely to follow the prompt",
                )

            if st.button("Generate Customized Avatar", type="primary"):
                if style_changes or custom_modifications:
                    with st.spinner("Generating customized avatar..."):
                        try:
                            # Create modification prompt
                            modification_prompt = self._create_modification_prompt(
                                style_changes, custom_modifications
                            )

                            # Generate customized image
                            result = self._generate_customized_image(
                                user_id,
                                base_image_path,
                                modification_prompt,
                                {"strength": strength, "guidance_scale": guidance_scale},
                            )

                            if result:
                                st.success("Customized avatar generated!")
                                return result
                            else:
                                st.error("Failed to generate customized avatar.")

                        except Exception as e:
                            logger.error(f"Error generating customized image: {e}")
                            st.error("Error generating customized avatar.")
                else:
                    st.warning("Please select modifications or provide custom description.")

        return None

    def render_batch_generation(self, user_id: UUID, embodiment_data: dict[str, Any]) -> list[str]:
        """
        Render batch generation interface for multiple variations.

        Args:
            user_id: User identifier
            embodiment_data: Embodiment characteristics

        Returns:
            List of generated image paths
        """
        st.subheader("🎭 Generate Multiple Variations")

        st.write("Generate multiple avatar variations at once to explore different styles.")

        # Variation options
        variation_count = st.slider(
            "Number of variations",
            min_value=2,
            max_value=8,
            value=4,
            help="How many variations to generate",
        )

        variation_types = st.multiselect(
            "Variation types",
            options=[
                "Different expressions",
                "Different styles",
                "Different ages",
                "Different clothing",
                "Different backgrounds",
                "Different poses",
            ],
            default=["Different expressions", "Different styles"],
        )

        if st.button("Generate Variations", type="primary"):
            if variation_types:
                with st.spinner(f"Generating {variation_count} variations..."):
                    try:
                        # Create variation prompts
                        variation_prompts = self._create_variation_prompts(
                            embodiment_data, variation_types, variation_count
                        )

                        # Generate variations
                        results = []
                        progress_bar = st.progress(0)

                        for i, prompt in enumerate(variation_prompts):
                            result = self._generate_single_variation(user_id, prompt)
                            if result:
                                results.append(result)

                            progress_bar.progress((i + 1) / len(variation_prompts))

                        if results:
                            st.success(f"Generated {len(results)} variations!")

                            # Display results in grid
                            cols = st.columns(min(4, len(results)))
                            for i, image_path in enumerate(results):
                                col_idx = i % len(cols)
                                with cols[col_idx]:
                                    try:
                                        image = Image.open(image_path)
                                        st.image(image, caption=f"Variation {i+1}")
                                    except Exception:
                                        st.error(f"Error loading variation {i+1}")

                            return results
                        else:
                            st.error("Failed to generate variations.")

                    except Exception as e:
                        logger.error(f"Error in batch generation: {e}")
                        st.error("Error generating variations.")
            else:
                st.warning("Please select at least one variation type.")

        return []

    def _check_image_consent(self, user_id: UUID) -> bool:
        """Check if user has consent for image generation."""
        try:
            if not self.consent_service.check_consent(user_id, ConsentType.IMAGE_GENERATION):
                st.error(get_text("error_consent_required"))
                st.warning("You need to provide consent for image generation to use this feature.")

                if st.button("Manage Consent Settings"):
                    st.session_state.show_consent_ui = True
                    st.rerun()

                return False

            return True

        except Exception as e:
            logger.error(f"Error checking image consent for user {user_id}: {e}")
            st.error("Error checking consent status.")
            return False

    def _render_embodiment_generation(
        self, user_id: UUID, embodiment_data: dict[str, Any] | None
    ) -> str | None:
        """Render embodiment-based generation interface."""
        if not embodiment_data:
            st.warning("No embodiment design found. Please complete the embodiment design first.")
            return None

        st.subheader("Generate from Embodiment Design")

        # Show embodiment summary
        with st.expander("Your Embodiment Design", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.write(
                    "**Appearance Style:**",
                    embodiment_data.get("appearance_style", "Not specified"),
                )
                st.write("**Personality:**", embodiment_data.get("personality", "Not specified"))

            with col2:
                st.write(
                    "**Communication Style:**",
                    embodiment_data.get("communication_style", "Not specified"),
                )
                st.write("**Age Range:**", embodiment_data.get("age_range", "Not specified"))

        # Generation parameters
        with st.expander("Generation Parameters"):
            image_style = st.selectbox(
                "Image style",
                options=["Realistic", "Artistic", "Cartoon", "Professional Photo", "Illustration"],
                index=0,
            )

            background = st.selectbox(
                "Background",
                options=["Professional", "Casual", "Educational", "Abstract", "None"],
                index=0,
            )

            quality = st.selectbox("Quality", options=["Standard", "High", "Ultra"], index=1)

        if st.button("Generate Avatar", type="primary"):
            with st.spinner("Generating your avatar..."):
                try:
                    # Create embodiment request
                    request = EmbodimentRequest(
                        user_id=user_id,
                        pald_data=embodiment_data,
                        parameters={
                            "style": image_style.lower(),
                            "background": background.lower(),
                            "quality": quality.lower(),
                        },
                    )

                    # Generate image
                    result = self.embodiment_logic.generate_embodiment_image(request)

                    if result and result.image_path:
                        st.success(get_text("success_image_generated"))

                        # Display generated image
                        try:
                            image = Image.open(result.image_path)
                            st.image(image, caption="Your Generated Avatar")
                        except Exception as e:
                            st.error(f"Error displaying image: {e}")

                        return result.image_path
                    else:
                        st.error("Failed to generate image.")

                except ImageProviderError as e:
                    st.error(f"Image generation failed: {e}")
                except Exception as e:
                    logger.error(f"Error generating embodiment image: {e}")
                    st.error("Error generating avatar.")

        return None

    def _render_custom_prompt_generation(self, user_id: UUID) -> str | None:
        """Render custom prompt generation interface."""
        st.subheader("Generate from Custom Prompt")

        # Prompt input
        custom_prompt = st.text_area(
            "Describe your avatar",
            placeholder="A friendly professional teacher with warm smile, wearing casual business attire...",
            help="Be as detailed as possible for better results",
            height=100,
        )

        # Style presets
        col1, col2 = st.columns(2)

        with col1:
            style_preset = st.selectbox(
                "Style preset",
                options=[
                    "None",
                    "Professional Portrait",
                    "Friendly Teacher",
                    "Creative Artist",
                    "Tech Expert",
                ],
                index=0,
            )

        with col2:
            if style_preset != "None":
                preset_prompts = {
                    "Professional Portrait": "professional headshot, business attire, confident expression",
                    "Friendly Teacher": "warm smile, approachable, educational setting, casual professional",
                    "Creative Artist": "creative, artistic, colorful, expressive, inspiring",
                    "Tech Expert": "modern, tech-savvy, innovative, clean background",
                }
                st.info(f"Preset adds: {preset_prompts.get(style_preset, '')}")

        # Advanced parameters
        with st.expander("Advanced Parameters"):
            col1, col2 = st.columns(2)

            with col1:
                guidance_scale = st.slider("Guidance scale", 1.0, 20.0, 7.5, 0.5)
                num_steps = st.slider("Inference steps", 10, 50, 20, 5)

            with col2:
                seed = st.number_input(
                    "Seed (optional)", min_value=0, value=0, help="Use 0 for random"
                )
                aspect_ratio = st.selectbox("Aspect ratio", ["1:1", "4:3", "3:4", "16:9"], index=0)

        if st.button("Generate Custom Avatar", type="primary"):
            if not custom_prompt.strip():
                st.warning("Please enter a description for your avatar.")
                return None

            with st.spinner("Generating custom avatar..."):
                try:
                    # Combine prompt with preset
                    final_prompt = custom_prompt
                    if style_preset != "None":
                        preset_addition = {
                            "Professional Portrait": "professional headshot, business attire, confident expression",
                            "Friendly Teacher": "warm smile, approachable, educational setting, casual professional",
                            "Creative Artist": "creative, artistic, colorful, expressive, inspiring",
                            "Tech Expert": "modern, tech-savvy, innovative, clean background",
                        }.get(style_preset, "")
                        final_prompt = f"{custom_prompt}, {preset_addition}"

                    # Generate image
                    result = self.image_service.generate_embodiment_image(
                        prompt=final_prompt,
                        user_id=user_id,
                        parameters={
                            "guidance_scale": guidance_scale,
                            "num_inference_steps": num_steps,
                            "seed": seed if seed > 0 else None,
                            "aspect_ratio": aspect_ratio,
                        },
                    )

                    if result and result.image_path:
                        st.success("Custom avatar generated!")

                        # Display generated image
                        try:
                            image = Image.open(result.image_path)
                            st.image(image, caption="Your Custom Avatar")
                        except Exception as e:
                            st.error(f"Error displaying image: {e}")

                        return result.image_path
                    else:
                        st.error("Failed to generate custom avatar.")

                except Exception as e:
                    logger.error(f"Error generating custom image: {e}")
                    st.error("Error generating custom avatar.")

        return None

    def _render_variation_generation(self, user_id: UUID) -> str | None:
        """Render variation generation interface."""
        st.subheader("Generate Variations")

        # Base image selection
        user_images = self._get_user_images(user_id)

        if not user_images:
            st.warning("No existing images found. Generate a base image first.")
            return None

        # Select base image
        base_image_options = [
            f"Image {i+1} - {img['created_at']}" for i, img in enumerate(user_images)
        ]
        selected_base_idx = st.selectbox(
            "Select base image",
            range(len(base_image_options)),
            format_func=lambda x: base_image_options[x],
        )

        base_image_info = user_images[selected_base_idx]

        # Show selected base image
        try:
            base_image = Image.open(base_image_info["path"])
            st.image(base_image, caption="Base Image", width=300)
        except Exception as e:
            st.error(f"Error loading base image: {e}")
            return None

        # Variation options
        variation_prompt = st.text_area(
            "Variation description",
            placeholder="Different expression, different clothing, different background...",
            help="Describe how you want to modify the base image",
        )

        if st.button("Generate Variation", type="primary"):
            if not variation_prompt.strip():
                st.warning("Please describe the variation you want.")
                return None

            with st.spinner("Generating variation..."):
                try:
                    # Generate variation (this would use img2img functionality)
                    result = self._generate_image_variation(
                        user_id, base_image_info["path"], variation_prompt
                    )

                    if result:
                        st.success("Variation generated!")

                        # Display result
                        try:
                            variation_image = Image.open(result)
                            col1, col2 = st.columns(2)

                            with col1:
                                st.image(base_image, caption="Original")

                            with col2:
                                st.image(variation_image, caption="Variation")
                        except Exception as e:
                            st.error(f"Error displaying variation: {e}")

                        return result
                    else:
                        st.error("Failed to generate variation.")

                except Exception as e:
                    logger.error(f"Error generating variation: {e}")
                    st.error("Error generating variation.")

        return None

    def _get_user_images(self, user_id: UUID) -> list[dict[str, Any]]:
        """Get list of user's generated images."""
        # This would typically query the database for user's images
        # For now, return mock data
        return [
            {
                "id": "img1",
                "path": "./generated_images/mock_embodiment_1754900071_1.png",
                "prompt": "Professional teacher avatar",
                "created_at": "2024-01-15 10:30",
                "model": "stable-diffusion-v1-5",
                "parameters": {"guidance_scale": 7.5},
            }
        ]

    def _download_image(self, image_info: dict[str, Any]) -> None:
        """Handle image download."""
        try:
            with open(image_info["path"], "rb") as file:
                st.download_button(
                    label="Download Image",
                    data=file.read(),
                    file_name=f"gitte_avatar_{image_info['id']}.png",
                    mime="image/png",
                )
        except Exception as e:
            st.error(f"Error downloading image: {e}")

    def _delete_image(self, user_id: UUID, image_id: str) -> None:
        """Handle image deletion."""
        # This would delete from database and filesystem
        st.success(f"Image {image_id} deleted.")

    def _create_modification_prompt(
        self, style_changes: list[str], custom_modifications: str
    ) -> str:
        """Create prompt for image modifications."""
        prompt_parts = []

        if style_changes:
            prompt_parts.extend(style_changes)

        if custom_modifications:
            prompt_parts.append(custom_modifications)

        return ", ".join(prompt_parts)

    def _generate_customized_image(
        self,
        user_id: UUID,
        base_image_path: str,
        modification_prompt: str,
        parameters: dict[str, Any],
    ) -> str | None:
        """Generate customized image based on base image."""
        # This would use img2img functionality
        # For now, return mock result
        return "./generated_images/mock_embodiment_1754900072_1.png"

    def _create_variation_prompts(
        self, embodiment_data: dict[str, Any], variation_types: list[str], count: int
    ) -> list[str]:
        """Create prompts for batch variations."""
        base_prompt = self.image_service.create_embodiment_prompt(embodiment_data)

        variation_modifiers = {
            "Different expressions": ["smiling", "serious", "thoughtful", "friendly"],
            "Different styles": ["professional", "casual", "artistic", "modern"],
            "Different ages": ["young", "middle-aged", "mature", "youthful"],
            "Different clothing": [
                "business suit",
                "casual wear",
                "academic attire",
                "creative outfit",
            ],
            "Different backgrounds": ["office", "classroom", "library", "modern space"],
            "Different poses": ["front view", "slight angle", "profile", "three-quarter view"],
        }

        prompts = []
        for i in range(count):
            prompt = base_prompt
            for variation_type in variation_types:
                if variation_type in variation_modifiers:
                    modifiers = variation_modifiers[variation_type]
                    modifier = modifiers[i % len(modifiers)]
                    prompt += f", {modifier}"
            prompts.append(prompt)

        return prompts

    def _generate_single_variation(self, user_id: UUID, prompt: str) -> str | None:
        """Generate a single variation."""
        try:
            result = self.image_service.generate_embodiment_image(
                prompt=prompt, user_id=user_id, parameters={}
            )
            return result.image_path if result else None
        except Exception as e:
            logger.error(f"Error generating single variation: {e}")
            return None

    def _generate_image_variation(
        self, user_id: UUID, base_image_path: str, variation_prompt: str
    ) -> str | None:
        """Generate image variation from base image."""
        # This would use img2img functionality
        # For now, return mock result
        return "./generated_images/mock_embodiment_1754900073_1.png"


# Global image UI instance
image_ui = ImageGenerationUI()


# Convenience functions
def render_image_generation_interface(
    user_id: UUID, embodiment_data: dict[str, Any] | None = None
) -> str | None:
    """Render image generation interface."""
    return image_ui.render_image_generation_interface(user_id, embodiment_data)


def render_image_gallery(user_id: UUID) -> None:
    """Render image gallery."""
    image_ui.render_image_gallery(user_id)


def render_image_customization(user_id: UUID, base_image_path: str) -> str | None:
    """Render image customization interface."""
    return image_ui.render_image_customization(user_id, base_image_path)


def render_batch_generation(user_id: UUID, embodiment_data: dict[str, Any]) -> list[str]:
    """Render batch generation interface."""
    return image_ui.render_batch_generation(user_id, embodiment_data)
