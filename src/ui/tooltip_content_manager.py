"""
Tooltip Content Manager for GITTE UI Elements.
Provides comprehensive tooltip content for all critical UI elements.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.ui.tooltip_system import (
    TooltipSystem,
    TooltipContent,
    TooltipConfig,
    TooltipTheme,
    TooltipPosition,
    disabled_element_processor,
    form_validation_processor,
    get_tooltip_system
)

logger = logging.getLogger(__name__)


@dataclass
class UIElementTooltips:
    """Container for UI element tooltip definitions."""
    
    # Authentication and Registration
    registration_tooltips: Dict[str, TooltipContent]
    
    # Consent and Privacy
    consent_tooltips: Dict[str, TooltipContent]
    
    # Embodiment Design
    embodiment_tooltips: Dict[str, TooltipContent]
    
    # Chat Interface
    chat_tooltips: Dict[str, TooltipContent]
    
    # Image Generation
    image_tooltips: Dict[str, TooltipContent]
    
    # Navigation and General
    navigation_tooltips: Dict[str, TooltipContent]
    
    # Admin and Settings
    admin_tooltips: Dict[str, TooltipContent]


class TooltipContentManager:
    """Manages comprehensive tooltip content for GITTE UI elements."""
    
    def __init__(self, tooltip_system: Optional[TooltipSystem] = None):
        """
        Initialize tooltip content manager.
        
        Args:
            tooltip_system: Optional tooltip system instance
        """
        self.tooltip_system = tooltip_system or get_tooltip_system()
        self.ui_tooltips = self._create_ui_tooltips()
        self._register_all_tooltips()
        self._register_context_processors()
    
    def _create_ui_tooltips(self) -> UIElementTooltips:
        """Create comprehensive tooltip definitions for all UI elements."""
        
        # Registration and Authentication Tooltips
        registration_tooltips = {
            "username_input": TooltipContent(
                title="Username",
                description="Choose a unique username for your GITTE account. This will be used to identify you in the system.",
                action_text="Must be 3-50 characters, letters, numbers, and underscores only",
                accessibility_label="Username input field - required for registration"
            ),
            
            "email_input": TooltipContent(
                title="Email Address",
                description="Your email address for account verification and important notifications. We'll never share your email with third parties.",
                action_text="Must be a valid email address format",
                accessibility_label="Email input field - required for account verification"
            ),
            
            "password_input": TooltipContent(
                title="Password",
                description="Create a secure password to protect your account. Your password is encrypted and stored securely.",
                action_text="Minimum 8 characters with letters, numbers, and special characters",
                accessibility_label="Password input field - must meet security requirements"
            ),
            
            "confirm_password_input": TooltipContent(
                title="Confirm Password",
                description="Re-enter your password to ensure it was typed correctly.",
                action_text="Must match the password entered above",
                accessibility_label="Password confirmation field"
            ),
            
            "register_submit_button": TooltipContent(
                title="Create Account",
                description="Complete your registration and create your GITTE learning assistant account.",
                action_text="Complete all required fields and accept terms to enable",
                theme=TooltipTheme.SUCCESS,
                accessibility_label="Registration submit button - creates new account"
            ),
            
            "login_button": TooltipContent(
                title="Sign In",
                description="Access your existing GITTE account with your username and password.",
                action_text="Enter valid credentials to sign in",
                accessibility_label="Login button - access existing account"
            ),
            
            "forgot_password_link": TooltipContent(
                title="Forgot Password",
                description="Reset your password if you can't remember it. We'll send reset instructions to your email.",
                help_link="/help/password-reset",
                accessibility_label="Password reset link"
            ),
            
            "role_select": TooltipContent(
                title="Account Type",
                description="Choose your account type. Participants have access to learning features, while Admins can manage the system.",
                action_text="Most users should select 'Participant'",
                accessibility_label="Account type selector"
            ),
            
            "terms_checkbox": TooltipContent(
                title="Terms and Conditions",
                description="By checking this box, you agree to our Terms of Service and Privacy Policy. This is required to create an account.",
                action_text="Review the terms before accepting",
                help_link="/terms-of-service",
                accessibility_label="Terms acceptance checkbox - required"
            )
        }
        
        # Consent and Privacy Tooltips
        consent_tooltips = {
            "data_processing_consent": TooltipContent(
                title="Data Processing Consent",
                description="Required to use GITTE's AI features. We process your data to provide personalized learning experiences and generate responses.",
                action_text="Check this box to enable AI features like chat and image generation",
                help_link="/privacy-policy",
                accessibility_label="Data processing consent checkbox - required for AI features"
            ),
            
            "llm_interaction_consent": TooltipContent(
                title="AI Chat Consent",
                description="Allows GITTE to process your messages and provide AI-powered responses. Your conversations help improve your learning experience.",
                action_text="Required to use the chat feature with your learning assistant",
                help_link="/privacy-policy#ai-interaction",
                accessibility_label="AI interaction consent - enables chat features"
            ),
            
            "image_generation_consent": TooltipContent(
                title="Image Generation Consent",
                description="Enables creation of visual representations for your learning assistant. Images are generated based on your preferences.",
                action_text="Required to create and customize your assistant's appearance",
                help_link="/privacy-policy#image-generation",
                accessibility_label="Image generation consent - enables avatar creation"
            ),
            
            "analytics_consent": TooltipContent(
                title="Analytics Consent (Optional)",
                description="Helps us understand how GITTE is used to improve the learning experience. All analytics data is anonymized.",
                action_text="Optional - you can use GITTE without enabling analytics",
                help_link="/privacy-policy#analytics",
                theme=TooltipTheme.LIGHT,
                accessibility_label="Optional analytics consent"
            ),
            
            "consent_settings_button": TooltipContent(
                title="Manage Consent",
                description="Review and modify your consent preferences. You can change these settings at any time.",
                action_text="Click to open consent management interface",
                help_link="/privacy-policy#consent-management",
                accessibility_label="Consent management button"
            )
        }
        
        # Embodiment Design Tooltips
        embodiment_tooltips = {
            "character_name_input": TooltipContent(
                title="Assistant Name",
                description="Give your learning assistant a name. This personalizes your interaction and makes the experience more engaging.",
                action_text="Choose any name you like - you can change it later",
                accessibility_label="Assistant name input field"
            ),
            
            "character_age_slider": TooltipContent(
                title="Apparent Age",
                description="Set the apparent age for your learning assistant's visual representation. This affects the generated appearance but not the AI capabilities.",
                action_text="Slide to select age range from 18 to 65",
                accessibility_label="Age selection slider for assistant appearance"
            ),
            
            "character_gender_select": TooltipContent(
                title="Gender Presentation",
                description="Choose how you'd like your assistant to be visually represented. This only affects appearance, not personality or capabilities.",
                action_text="Select from available options or choose 'Other' for non-binary representation",
                accessibility_label="Gender presentation selector"
            ),
            
            "character_style_select": TooltipContent(
                title="Visual Style",
                description="Choose the artistic style for your assistant's appearance. Different styles create different visual aesthetics.",
                action_text="Preview different styles to see which you prefer",
                accessibility_label="Visual style selector for assistant appearance"
            ),
            
            "personality_traits_input": TooltipContent(
                title="Personality Traits",
                description="Describe personality characteristics you'd like your assistant to embody. This influences both appearance and interaction style.",
                action_text="Use descriptive words like 'friendly', 'professional', 'creative', etc.",
                accessibility_label="Personality traits text input"
            ),
            
            "subject_expertise_select": TooltipContent(
                title="Subject Expertise",
                description="Choose areas where you'd like your assistant to be particularly knowledgeable. This helps tailor responses to your learning needs.",
                action_text="Select one or more subject areas",
                accessibility_label="Subject expertise multi-select"
            ),
            
            "generate_preview_button": TooltipContent(
                title="Generate Preview",
                description="Create a preview of your learning assistant based on your current settings. You can regenerate if you're not satisfied.",
                action_text="Complete the form fields above to enable preview generation",
                theme=TooltipTheme.SUCCESS,
                accessibility_label="Preview generation button"
            ),
            
            "age_range_select": TooltipContent(
                title="Age Range",
                description="Select the approximate age range for your learning assistant's appearance.",
                action_text="Choose an age range that fits your learning preferences",
                accessibility_label="Age range selector for assistant appearance"
            ),
            
            "ethnicity_select": TooltipContent(
                title="Ethnicity",
                description="Choose the ethnic appearance for your learning assistant. This helps create a more personalized experience.",
                action_text="Select an ethnicity that represents your preferences",
                accessibility_label="Ethnicity selector for assistant appearance"
            ),
            
            "clothing_style_select": TooltipContent(
                title="Clothing Style",
                description="Select the clothing style for your assistant. Options range from casual to formal professional attire.",
                action_text="Choose a style that matches your learning environment",
                accessibility_label="Clothing style selector for assistant appearance"
            ),
            
            "background_style_select": TooltipContent(
                title="Background Style",
                description="Choose the background environment for your assistant. Options include office, classroom, library, and more.",
                action_text="Select a background that fits your learning context",
                accessibility_label="Background style selector for assistant appearance"
            )
        }
        
        # Chat Interface Tooltips
        chat_tooltips = {
            "chat_input_field": TooltipContent(
                title="Message Input",
                description="Type your message or question here. Your learning assistant can help with explanations, answer questions, or discuss topics.",
                action_text="Press Enter to send, Shift+Enter for new line",
                accessibility_label="Chat message input field"
            ),
            
            "send_message_button": TooltipContent(
                title="Send Message",
                description="Send your message to your learning assistant. You'll receive a personalized response based on your question.",
                action_text="Type a message first to enable sending",
                accessibility_label="Send message button"
            ),
            
            "clear_chat_button": TooltipContent(
                title="Clear Conversation",
                description="Clear the current conversation history. This starts a fresh conversation but doesn't affect your learning progress.",
                action_text="Click to clear all messages in this session",
                theme=TooltipTheme.WARNING,
                accessibility_label="Clear conversation button - removes all messages"
            ),
            
            "chat_history_button": TooltipContent(
                title="Conversation History",
                description="View your previous conversations with your learning assistant. This helps track your learning journey.",
                action_text="Click to view conversation history",
                accessibility_label="Conversation history button"
            ),
            
            "export_chat_button": TooltipContent(
                title="Export Conversation",
                description="Download your conversation as a text file for your records or further study.",
                action_text="Click to download conversation as text file",
                accessibility_label="Export conversation button"
            ),
            
            "chat_settings_button": TooltipContent(
                title="Chat Settings",
                description="Adjust chat preferences like response length, formality level, and interaction style.",
                action_text="Click to open chat configuration",
                accessibility_label="Chat settings button"
            ),
            
            "voice_chat_button": TooltipContent(
                title="Voice Chat",
                description="Switch to voice-based interaction with your learning assistant. Speak naturally and receive audio responses.",
                action_text="Click to enable voice chat mode",
                accessibility_label="Voice chat toggle button"
            ),
            
            "chat_model_select": TooltipContent(
                title="AI Model",
                description="Choose the AI model for your chat interactions. Different models have different capabilities and response styles.",
                action_text="Select an AI model that fits your learning needs",
                accessibility_label="AI model selector for chat"
            ),
            
            "response_length_slider": TooltipContent(
                title="Response Length",
                description="Adjust how detailed your assistant's responses should be. Shorter for quick answers, longer for comprehensive explanations.",
                action_text="Drag slider to adjust response detail level",
                accessibility_label="Response length adjustment slider"
            ),
            
            "formality_level_select": TooltipContent(
                title="Formality Level",
                description="Choose how formal or casual your assistant's communication style should be.",
                action_text="Select from formal, neutral, or casual communication style",
                accessibility_label="Communication formality selector"
            )
        }
        
        # Image Generation Tooltips
        image_tooltips = {
            "image_prompt_input": TooltipContent(
                title="Image Description",
                description="Describe what you'd like to see in the generated image. Be specific about details, style, and composition.",
                action_text="Use descriptive language like 'a professional woman in business attire, smiling, office background'",
                accessibility_label="Image generation prompt input"
            ),
            
            "image_style_select": TooltipContent(
                title="Image Style",
                description="Choose the artistic style for the generated image. Different styles produce different visual aesthetics.",
                action_text="Select from realistic, artistic, cartoon, or other available styles",
                accessibility_label="Image style selector"
            ),
            
            "image_quality_select": TooltipContent(
                title="Image Quality",
                description="Higher quality takes longer to generate but produces better results. Choose based on your needs and patience.",
                action_text="Standard quality is usually sufficient for most purposes",
                accessibility_label="Image quality selector"
            ),
            
            "generate_image_button": TooltipContent(
                title="Generate Image",
                description="Create an image based on your description and settings. This may take 30-60 seconds depending on quality settings.",
                action_text="Provide a description first to enable generation",
                theme=TooltipTheme.SUCCESS,
                accessibility_label="Image generation button - creates new image"
            ),
            
            "regenerate_image_button": TooltipContent(
                title="Regenerate Image",
                description="Create a new image with the same settings. Each generation produces a unique result.",
                action_text="Click to generate a different version",
                accessibility_label="Regenerate image button"
            ),
            
            "save_image_button": TooltipContent(
                title="Save Image",
                description="Save the current image to your account. Saved images can be used as your assistant's appearance.",
                action_text="Click to save image to your account",
                theme=TooltipTheme.SUCCESS,
                accessibility_label="Save image button"
            ),
            
            "download_image_button": TooltipContent(
                title="Download Image",
                description="Download the image to your device. The image will be saved in high quality PNG format.",
                action_text="Click to download image to your device",
                accessibility_label="Download image button"
            ),
            
            "image_size_select": TooltipContent(
                title="Image Size",
                description="Choose the dimensions for your generated image. Larger sizes provide more detail but take longer to generate.",
                action_text="Select size based on your needs and patience",
                accessibility_label="Image size selector"
            ),
            
            "aspect_ratio_select": TooltipContent(
                title="Aspect Ratio",
                description="Choose the shape of your image. Common ratios include square, portrait, and landscape orientations.",
                action_text="Select aspect ratio that fits your intended use",
                accessibility_label="Image aspect ratio selector"
            ),
            
            "seed_input": TooltipContent(
                title="Seed Value",
                description="Set a specific seed value for reproducible image generation. Same seed + prompt produces similar results.",
                action_text="Leave empty for random generation, or set for consistent results",
                accessibility_label="Image generation seed input"
            ),
            
            "negative_prompt_input": TooltipContent(
                title="Negative Prompt",
                description="Specify what you don't want to see in the image. This helps avoid unwanted elements.",
                action_text="Use terms like 'blurry', 'low quality', 'text' to exclude elements",
                accessibility_label="Negative prompt input for image generation"
            )
        }
        
        # Navigation and General Tooltips
        navigation_tooltips = {
            "home_nav_button": TooltipContent(
                title="Home",
                description="Return to the main dashboard where you can access all GITTE features and see your learning progress.",
                action_text="Click to navigate to home dashboard",
                accessibility_label="Home navigation button"
            ),
            
            "profile_nav_button": TooltipContent(
                title="Profile",
                description="View and edit your account information, preferences, and learning assistant settings.",
                action_text="Click to open profile settings",
                accessibility_label="Profile navigation button"
            ),
            
            "settings_nav_button": TooltipContent(
                title="Settings",
                description="Configure GITTE preferences, privacy settings, and system options.",
                action_text="Click to open system settings",
                accessibility_label="Settings navigation button"
            ),
            
            "help_nav_button": TooltipContent(
                title="Help & Support",
                description="Access documentation, tutorials, FAQs, and contact support for assistance.",
                action_text="Click to open help documentation",
                help_link="/help",
                accessibility_label="Help and support navigation button"
            ),
            
            "logout_button": TooltipContent(
                title="Sign Out",
                description="Safely sign out of your GITTE account. Your progress and settings will be saved.",
                action_text="Click to sign out of your account",
                theme=TooltipTheme.WARNING,
                accessibility_label="Logout button - signs out of account"
            ),
            
            "theme_toggle_button": TooltipContent(
                title="Toggle Theme",
                description="Switch between light and dark themes for better visibility and comfort.",
                action_text="Click to switch between light and dark themes",
                accessibility_label="Theme toggle button"
            ),
            
            "language_select": TooltipContent(
                title="Language",
                description="Change the interface language. Your learning assistant will also respond in the selected language.",
                action_text="Select your preferred language from the dropdown",
                accessibility_label="Language selector"
            ),
            
            "export_button": TooltipContent(
                title="Export Data",
                description="Download your data in a portable format for backup or transfer purposes",
                action_text="Click to generate and download your data export",
                accessibility_label="Data export button"
            ),
            
            "search_input": TooltipContent(
                title="Search",
                description="Search through GITTE features, help content, and your learning materials.",
                action_text="Type keywords to find relevant information",
                accessibility_label="Search input field"
            ),
            
            "notifications_button": TooltipContent(
                title="Notifications",
                description="View system notifications, updates, and important messages about your account.",
                action_text="Click to view notification center",
                accessibility_label="Notifications button"
            ),
            
            "feedback_button": TooltipContent(
                title="Feedback",
                description="Share your thoughts, report issues, or suggest improvements for GITTE.",
                action_text="Click to submit feedback or report issues",
                help_link="/feedback",
                accessibility_label="Feedback button"
            )
        }
        
        # Admin and Settings Tooltips
        admin_tooltips = {
            "admin_dashboard_button": TooltipContent(
                title="Admin Dashboard",
                description="Access administrative functions and system monitoring tools. Available only to administrators.",
                action_text="Click to open admin dashboard (admin access required)",
                theme=TooltipTheme.WARNING,
                accessibility_label="Admin dashboard button - restricted access"
            ),
            
            "user_management_button": TooltipContent(
                title="User Management",
                description="Manage user accounts, permissions, and system access. Administrative function only.",
                action_text="Click to manage user accounts and permissions",
                theme=TooltipTheme.WARNING,
                accessibility_label="User management button - admin only"
            ),
            
            "system_settings_button": TooltipContent(
                title="System Settings",
                description="Configure system-wide settings, feature flags, and operational parameters.",
                action_text="Click to configure system settings (admin only)",
                theme=TooltipTheme.ERROR,
                accessibility_label="System settings button - admin only"
            ),
            
            "backup_button": TooltipContent(
                title="Backup Data",
                description="Create a backup of user data and system configuration. Important for data protection.",
                action_text="Click to create system backup",
                theme=TooltipTheme.WARNING,
                accessibility_label="Backup creation button"
            ),
            
            "logs_button": TooltipContent(
                title="System Logs",
                description="View system logs for troubleshooting and monitoring. Contains technical information.",
                action_text="Click to view system logs and diagnostics",
                theme=TooltipTheme.WARNING,
                accessibility_label="System logs button"
            ),
            
            "system_health_button": TooltipContent(
                title="System Health",
                description="Monitor system performance, resource usage, and overall health status.",
                action_text="Click to view system health dashboard",
                theme=TooltipTheme.WARNING,
                accessibility_label="System health monitoring button"
            ),
            
            "feature_flags_button": TooltipContent(
                title="Feature Flags",
                description="Enable or disable system features for testing and gradual rollout.",
                action_text="Click to manage feature flags (admin only)",
                theme=TooltipTheme.WARNING,
                accessibility_label="Feature flag management button"
            ),
            
            "audit_logs_button": TooltipContent(
                title="Audit Logs",
                description="View detailed audit trail of system activities and user actions for compliance.",
                action_text="Click to view audit logs",
                theme=TooltipTheme.ERROR,
                accessibility_label="Audit logs button - compliance tracking"
            ),
            
            "maintenance_mode_button": TooltipContent(
                title="Maintenance Mode",
                description="Enable maintenance mode to restrict user access during system updates.",
                action_text="Click to toggle maintenance mode (admin only)",
                theme=TooltipTheme.ERROR,
                accessibility_label="Maintenance mode toggle button"
            )
        }
        
        return UIElementTooltips(
            registration_tooltips=registration_tooltips,
            consent_tooltips=consent_tooltips,
            embodiment_tooltips=embodiment_tooltips,
            chat_tooltips=chat_tooltips,
            image_tooltips=image_tooltips,
            navigation_tooltips=navigation_tooltips,
            admin_tooltips=admin_tooltips
        )
    
    def _register_all_tooltips(self):
        """Register all tooltip content with the tooltip system."""
        tooltip_categories = [
            self.ui_tooltips.registration_tooltips,
            self.ui_tooltips.consent_tooltips,
            self.ui_tooltips.embodiment_tooltips,
            self.ui_tooltips.chat_tooltips,
            self.ui_tooltips.image_tooltips,
            self.ui_tooltips.navigation_tooltips,
            self.ui_tooltips.admin_tooltips
        ]
        
        total_registered = 0
        
        for category in tooltip_categories:
            for element_id, content in category.items():
                self.tooltip_system.register_tooltip(element_id, content)
                total_registered += 1
        
        logger.info(f"Registered {total_registered} comprehensive tooltips")
    
    def _register_context_processors(self):
        """Register context processors for dynamic tooltip behavior."""
        
        # Form validation processor for input fields
        form_input_elements = [
            "username_input", "email_input", "password_input", "confirm_password_input",
            "character_name_input", "personality_traits_input", "image_prompt_input",
            "search_input", "seed_input", "negative_prompt_input"
        ]
        
        for element_id in form_input_elements:
            self.tooltip_system.register_context_processor(element_id, form_validation_processor)
        
        # Disabled element processor for buttons
        button_elements = [
            "register_submit_button", "generate_preview_button", "send_message_button",
            "generate_image_button", "save_image_button", "regenerate_image_button",
            "download_image_button", "export_button", "backup_button"
        ]
        
        for element_id in button_elements:
            self.tooltip_system.register_context_processor(element_id, disabled_element_processor)
        
        # Custom processor for consent checkboxes
        consent_elements = [
            "data_processing_consent", "llm_interaction_consent", "image_generation_consent",
            "analytics_consent"
        ]
        
        for element_id in consent_elements:
            self.tooltip_system.register_context_processor(element_id, self._consent_processor)
        
        # Slider processor for range inputs
        slider_elements = [
            "response_length_slider"
        ]
        
        for element_id in slider_elements:
            self.tooltip_system.register_context_processor(element_id, self._slider_processor)
        
        logger.info("Registered context processors for dynamic tooltip behavior")
    
    def _consent_processor(self, base_tooltip: TooltipContent, context: Dict[str, Any]) -> TooltipContent:
        """
        Context processor for consent checkboxes.
        
        Args:
            base_tooltip: Base tooltip content
            context: Context containing consent state
            
        Returns:
            Modified tooltip content
        """
        is_granted = context.get("consent_granted", False)
        dependent_features = context.get("dependent_features", [])
        
        if is_granted:
            # Consent already granted
            modified = TooltipContent(
                title=f"✅ {base_tooltip.title}",
                description=f"{base_tooltip.description} (Currently granted)",
                action_text="Uncheck to revoke consent (will disable related features)",
                theme=TooltipTheme.SUCCESS,
                accessibility_label=f"{base_tooltip.accessibility_label} - currently granted"
            )
        else:
            # Consent not granted
            feature_list = ", ".join(dependent_features) if dependent_features else "AI features"
            modified = TooltipContent(
                title=f"⚠️ {base_tooltip.title}",
                description=base_tooltip.description,
                action_text=f"Check to enable: {feature_list}",
                theme=TooltipTheme.WARNING,
                accessibility_label=f"{base_tooltip.accessibility_label} - not granted, features disabled"
            )
        
        return modified
    
    def _slider_processor(self, base_tooltip: TooltipContent, context: Dict[str, Any]) -> TooltipContent:
        """
        Context processor for slider inputs.
        
        Args:
            base_tooltip: Base tooltip content
            context: Context containing slider state
            
        Returns:
            Modified tooltip content
        """
        current_value = context.get("current_value", None)
        min_value = context.get("min_value", 0)
        max_value = context.get("max_value", 100)
        
        if current_value is not None:
            # Add current value to description
            modified = TooltipContent(
                title=base_tooltip.title,
                description=f"{base_tooltip.description} Current value: {current_value}",
                action_text=f"Drag to adjust between {min_value} and {max_value}",
                theme=base_tooltip.theme,
                accessibility_label=f"{base_tooltip.accessibility_label} - current value: {current_value}"
            )
        else:
            # No current value
            modified = TooltipContent(
                title=base_tooltip.title,
                description=base_tooltip.description,
                action_text=f"Drag to set value between {min_value} and {max_value}",
                theme=base_tooltip.theme,
                accessibility_label=base_tooltip.accessibility_label
            )
        
        return modified
    
    def get_tooltip_for_element(self, element_id: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get tooltip help text for a UI element.
        
        Args:
            element_id: UI element identifier
            context: Optional context for dynamic content
            
        Returns:
            Help text string or None if not found
        """
        return self.tooltip_system.get_streamlit_help(element_id, context)
    
    def get_all_registered_elements(self) -> List[str]:
        """Get list of all registered UI elements with tooltips."""
        return self.tooltip_system.registry.list_registered()
    
    def get_tooltips_by_category(self, category: str) -> Dict[str, TooltipContent]:
        """
        Get tooltips for a specific UI category.
        
        Args:
            category: Category name (registration, consent, embodiment, etc.)
            
        Returns:
            Dictionary of tooltips for the category
        """
        category_map = {
            "registration": self.ui_tooltips.registration_tooltips,
            "consent": self.ui_tooltips.consent_tooltips,
            "embodiment": self.ui_tooltips.embodiment_tooltips,
            "chat": self.ui_tooltips.chat_tooltips,
            "image": self.ui_tooltips.image_tooltips,
            "navigation": self.ui_tooltips.navigation_tooltips,
            "admin": self.ui_tooltips.admin_tooltips
        }
        
        return category_map.get(category, {})
    
    def validate_tooltip_coverage(self, ui_elements: List[str]) -> Dict[str, Any]:
        """
        Validate tooltip coverage for a list of UI elements.
        
        Args:
            ui_elements: List of UI element identifiers to check
            
        Returns:
            Dictionary with coverage analysis
        """
        registered_elements = set(self.get_all_registered_elements())
        provided_elements = set(ui_elements)
        
        covered = provided_elements.intersection(registered_elements)
        missing = provided_elements - registered_elements
        extra = registered_elements - provided_elements
        
        coverage_percentage = (len(covered) / len(provided_elements)) * 100 if provided_elements else 0
        
        return {
            "total_elements": len(provided_elements),
            "covered_elements": len(covered),
            "missing_elements": len(missing),
            "coverage_percentage": coverage_percentage,
            "covered": list(covered),
            "missing": list(missing),
            "extra_registered": list(extra)
        }
    
    def generate_tooltip_documentation(self) -> str:
        """
        Generate documentation for all registered tooltips.
        
        Returns:
            Markdown documentation string
        """
        doc_lines = [
            "# GITTE UI Tooltip Documentation",
            "",
            "This document describes all available tooltips in the GITTE user interface.",
            ""
        ]
        
        categories = [
            ("Registration & Authentication", self.ui_tooltips.registration_tooltips),
            ("Consent & Privacy", self.ui_tooltips.consent_tooltips),
            ("Embodiment Design", self.ui_tooltips.embodiment_tooltips),
            ("Chat Interface", self.ui_tooltips.chat_tooltips),
            ("Image Generation", self.ui_tooltips.image_tooltips),
            ("Navigation & General", self.ui_tooltips.navigation_tooltips),
            ("Admin & Settings", self.ui_tooltips.admin_tooltips)
        ]
        
        for category_name, tooltips in categories:
            doc_lines.extend([
                f"## {category_name}",
                ""
            ])
            
            for element_id, content in tooltips.items():
                doc_lines.extend([
                    f"### `{element_id}`",
                    f"**Title:** {content.title}",
                    f"**Description:** {content.description}",
                ])
                
                if content.action_text:
                    doc_lines.append(f"**Action:** {content.action_text}")
                
                if content.help_link:
                    doc_lines.append(f"**Help Link:** {content.help_link}")
                
                doc_lines.extend(["", "---", ""])
        
        return "\n".join(doc_lines)


# Global tooltip content manager instance
_tooltip_content_manager = None


def get_tooltip_content_manager() -> TooltipContentManager:
    """
    Get global tooltip content manager instance.
    
    Returns:
        TooltipContentManager instance
    """
    global _tooltip_content_manager
    
    if _tooltip_content_manager is None:
        _tooltip_content_manager = TooltipContentManager()
    
    return _tooltip_content_manager