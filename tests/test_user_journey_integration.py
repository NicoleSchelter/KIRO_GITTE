"""
User journey integration tests for GITTE UX enhancements.
Tests complete user workflows and scenarios from start to finish.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.ui.tooltip_system import TooltipSystem
from src.ui.tooltip_content_manager import TooltipContentManager
from src.logic.prerequisite_validation import PrerequisiteValidationLogic
from src.ui.prerequisite_checklist_ui import PrerequisiteChecklistUI
from src.services.audit_service import AuditService


class TestUserJourneyTooltipInteractions:
    """Test user journey scenarios with tooltip interactions."""
    
    @pytest.fixture
    def user_journey_setup(self):
        """Setup for user journey testing."""
        return {
            "new_user_id": uuid4(),
            "experienced_user_id": uuid4(),
            "accessibility_user_id": uuid4()
        }
    
    def test_new_user_tooltip_discovery_journey(self, user_journey_setup):
        """Test new user discovering and using tooltips throughout their journey."""
        user_id = user_journey_setup["new_user_id"]
        
        # Step 1: User arrives at registration page
        tooltip_system = TooltipSystem()
        content_manager = TooltipContentManager()
        
        # Register registration form tooltips
        registration_tooltips = {
            "email_input": "Enter your email address. This will be used for login and notifications.",
            "password_input": "Create a strong password with at least 8 characters, including letters and numbers.",
            "confirm_password": "Re-enter your password to confirm it matches.",
            "terms_checkbox": "Please read and accept our terms of service to continue.",
            "register_button": "Click to create your account and start using GITTE."
        }
        
        for element_id, content in registration_tooltips.items():
            tooltip_system.register_tooltip(element_id, content, context="registration")
        
        tooltip_system.set_context("registration")
        
        # Step 2: User discovers tooltips by hovering over form fields
        tooltip_interactions = []
        
        for element_id in registration_tooltips.keys():
            # Simulate user hovering over element
            tooltip = tooltip_system.get_tooltip(element_id)
            tooltip_system.track_tooltip_interaction(user_id, element_id, "hover")
            
            tooltip_interactions.append({
                "element_id": element_id,
                "tooltip_content": tooltip,
                "interaction_type": "hover"
            })
            
            assert tooltip is not None
            assert len(tooltip) > 20  # Should have meaningful content
        
        # Step 3: User completes registration with tooltip guidance
        # Simulate user clicking on help icon for additional guidance
        help_tooltip = tooltip_system.get_tooltip("register_button")
        tooltip_system.track_tooltip_interaction(user_id, "register_button", "click_help")
        
        assert "create your account" in help_tooltip.lower()
        
        # Step 4: User moves to main application
        tooltip_system.set_context("main_application")
        
        # Register main app tooltips
        main_app_tooltips = {
            "chat_button": "Start a conversation with the AI assistant.",
            "image_generation_button": "Generate personalized images for your content.",
            "settings_menu": "Access your account settings and preferences.",
            "help_center": "Find answers to common questions and get support."
        }
        
        for element_id, content in main_app_tooltips.items():
            tooltip_system.register_tooltip(element_id, content, context="main_application")
        
        # Step 5: User explores main features with tooltip guidance
        for element_id in main_app_tooltips.keys():
            tooltip = tooltip_system.get_tooltip(element_id)
            tooltip_system.track_tooltip_interaction(user_id, element_id, "hover")
            
            assert tooltip is not None
            assert tooltip == main_app_tooltips[element_id]
        
        # Step 6: Analyze user's tooltip usage patterns
        interaction_stats = tooltip_system.get_interaction_statistics(user_id)
        
        assert interaction_stats["total_interactions"] >= 9  # 5 registration + 4 main app
        assert "registration" in interaction_stats["contexts_explored"]
        assert "main_application" in interaction_stats["contexts_explored"]
        assert interaction_stats["unique_tooltips_accessed"] >= 9
    
    def test_experienced_user_advanced_tooltip_journey(self, user_journey_setup):
        """Test experienced user journey with advanced tooltip features."""
        user_id = user_journey_setup["experienced_user_id"]
        
        tooltip_system = TooltipSystem()
        
        # Set user as experienced (simulated through user preferences)
        user_preferences = {
            "experience_level": "advanced",
            "show_basic_tooltips": False,
            "show_keyboard_shortcuts": True,
            "tooltip_delay": 500  # Faster tooltip display
        }
        
        # Register advanced tooltips
        advanced_tooltips = {
            "bulk_image_generation": "Generate multiple images at once. Keyboard shortcut: Ctrl+Shift+G",
            "advanced_settings": "Configure advanced generation parameters. Press F12 for developer options.",
            "batch_operations": "Perform operations on multiple items. Select items and press Ctrl+B.",
            "api_integration": "Access API settings for external integrations. Requires admin privileges."
        }
        
        for element_id, content in advanced_tooltips.items():
            tooltip_system.register_tooltip(
                element_id, 
                content, 
                context="advanced_features",
                experience_level="advanced"
            )
        
        tooltip_system.set_context("advanced_features")
        
        # Step 1: User accesses advanced features
        for element_id in advanced_tooltips.keys():
            tooltip = tooltip_system.get_tooltip(
                element_id,
                user_preferences=user_preferences
            )
            
            assert tooltip is not None
            # Advanced tooltips should include keyboard shortcuts
            assert "ctrl" in tooltip.lower() or "f12" in tooltip.lower() or "admin" in tooltip.lower()
        
        # Step 2: User uses keyboard shortcuts mentioned in tooltips
        tooltip_system.track_tooltip_interaction(user_id, "bulk_image_generation", "keyboard_shortcut_used")
        tooltip_system.track_tooltip_interaction(user_id, "advanced_settings", "keyboard_shortcut_used")
        
        # Step 3: Analyze advanced user patterns
        interaction_stats = tooltip_system.get_interaction_statistics(user_id)
        
        assert "keyboard_shortcut_used" in [i["interaction_type"] for i in interaction_stats.get("interactions", [])]
        assert interaction_stats.get("advanced_features_used", 0) > 0
    
    def test_accessibility_user_tooltip_journey(self, user_journey_setup):
        """Test accessibility user journey with enhanced tooltip features."""
        user_id = user_journey_setup["accessibility_user_id"]
        
        tooltip_system = TooltipSystem()
        
        # Set accessibility preferences
        accessibility_preferences = {
            "screen_reader": True,
            "high_contrast": True,
            "large_text": True,
            "keyboard_navigation": True,
            "detailed_descriptions": True
        }
        
        # Register accessibility-enhanced tooltips
        accessibility_tooltips = {
            "main_navigation": {
                "content": "Main navigation menu with 5 options",
                "aria_label": "Main navigation menu",
                "detailed_description": "Navigation menu containing Home, Chat, Images, Settings, and Help options. Use arrow keys to navigate, Enter to select.",
                "keyboard_instructions": "Press Tab to enter menu, arrow keys to navigate, Enter to select, Escape to exit"
            },
            "image_upload": {
                "content": "Upload image button",
                "aria_label": "Upload image file",
                "detailed_description": "Button to upload image files. Accepts PNG, JPG, and GIF formats up to 10MB.",
                "keyboard_instructions": "Press Enter or Space to open file dialog"
            }
        }
        
        for element_id, tooltip_data in accessibility_tooltips.items():
            tooltip_system.register_tooltip(
                element_id,
                tooltip_data["content"],
                context="accessibility",
                aria_label=tooltip_data["aria_label"],
                detailed_description=tooltip_data["detailed_description"],
                keyboard_instructions=tooltip_data["keyboard_instructions"]
            )
        
        tooltip_system.set_context("accessibility")
        
        # Step 1: User navigates with screen reader
        for element_id in accessibility_tooltips.keys():
            # Get accessibility-enhanced tooltip
            tooltip = tooltip_system.get_tooltip(
                element_id,
                include_accessibility=True,
                user_preferences=accessibility_preferences
            )
            
            assert tooltip is not None
            assert len(tooltip) > 50  # Should be detailed for accessibility
            
            # Get ARIA attributes
            aria_attributes = tooltip_system.get_aria_attributes(element_id)
            
            assert "aria-label" in aria_attributes
            assert "aria-describedby" in aria_attributes
            
            # Track accessibility interaction
            tooltip_system.track_tooltip_interaction(
                user_id, 
                element_id, 
                "screen_reader_access",
                accessibility_context=accessibility_preferences
            )
        
        # Step 2: User uses keyboard navigation
        keyboard_help = tooltip_system.get_keyboard_navigation_help("accessibility")
        
        assert keyboard_help is not None
        assert "tab" in keyboard_help.lower()
        assert "enter" in keyboard_help.lower()
        assert "arrow" in keyboard_help.lower()
        
        # Step 3: Analyze accessibility usage patterns
        interaction_stats = tooltip_system.get_interaction_statistics(user_id)
        
        assert "screen_reader_access" in [i["interaction_type"] for i in interaction_stats.get("interactions", [])]
        assert interaction_stats.get("accessibility_features_used", 0) > 0
    
    def test_tooltip_help_system_integration_journey(self, user_journey_setup):
        """Test integration between tooltip system and help system."""
        user_id = user_journey_setup["new_user_id"]
        
        tooltip_system = TooltipSystem()
        content_manager = TooltipContentManager()
        
        # Step 1: User encounters complex feature
        complex_feature_tooltip = {
            "element_id": "image_correction_dialog",
            "basic_content": "Adjust image settings",
            "detailed_content": "Use this dialog to manually correct image generation issues. You can crop, adjust colors, or regenerate the image.",
            "help_link": "/help/image-correction",
            "video_tutorial": "/tutorials/image-correction-basics"
        }
        
        tooltip_system.register_tooltip(
            complex_feature_tooltip["element_id"],
            complex_feature_tooltip["basic_content"],
            context="image_correction",
            detailed_content=complex_feature_tooltip["detailed_content"],
            help_resources={
                "help_link": complex_feature_tooltip["help_link"],
                "video_tutorial": complex_feature_tooltip["video_tutorial"]
            }
        )
        
        # Step 2: User views basic tooltip
        basic_tooltip = tooltip_system.get_tooltip("image_correction_dialog")
        assert basic_tooltip == complex_feature_tooltip["basic_content"]
        
        # Step 3: User requests more detailed help
        detailed_tooltip = tooltip_system.get_tooltip(
            "image_correction_dialog",
            detail_level="detailed"
        )
        
        assert "manually correct" in detailed_tooltip
        assert "crop" in detailed_tooltip
        assert "regenerate" in detailed_tooltip
        
        # Step 4: User accesses help resources
        help_resources = tooltip_system.get_help_resources("image_correction_dialog")
        
        assert "help_link" in help_resources
        assert "video_tutorial" in help_resources
        assert help_resources["help_link"] == "/help/image-correction"
        
        # Track help resource access
        tooltip_system.track_tooltip_interaction(
            user_id,
            "image_correction_dialog",
            "help_resource_accessed",
            resource_type="help_link"
        )
        
        # Step 5: System provides contextual help suggestions
        related_help = tooltip_system.get_related_help_topics("image_correction")
        
        assert related_help is not None
        assert len(related_help) > 0
        assert any("image" in topic.lower() for topic in related_help)
    
    def test_tooltip_learning_and_adaptation_journey(self, user_journey_setup):
        """Test tooltip system learning and adapting to user behavior."""
        user_id = user_journey_setup["experienced_user_id"]
        
        tooltip_system = TooltipSystem()
        
        # Step 1: User interacts with tooltips over multiple sessions
        sessions = [
            {
                "session_id": 1,
                "tooltips_accessed": ["login_button", "password_input", "help_link"],
                "time_spent": [2.5, 5.0, 1.0]  # seconds
            },
            {
                "session_id": 2,
                "tooltips_accessed": ["image_generation", "settings_menu", "advanced_options"],
                "time_spent": [1.0, 0.5, 3.0]
            },
            {
                "session_id": 3,
                "tooltips_accessed": ["advanced_options", "api_settings", "bulk_operations"],
                "time_spent": [0.5, 2.0, 1.5]
            }
        ]
        
        # Register tooltips
        all_tooltips = {
            "login_button": "Click to log in to your account",
            "password_input": "Enter your password",
            "help_link": "Get help and support",
            "image_generation": "Generate AI images",
            "settings_menu": "Access your settings",
            "advanced_options": "Configure advanced settings",
            "api_settings": "Manage API integrations",
            "bulk_operations": "Perform bulk operations"
        }
        
        for element_id, content in all_tooltips.items():
            tooltip_system.register_tooltip(element_id, content)
        
        # Simulate user sessions
        for session in sessions:
            for i, element_id in enumerate(session["tooltips_accessed"]):
                tooltip_system.track_tooltip_interaction(
                    user_id,
                    element_id,
                    "hover",
                    session_id=session["session_id"],
                    time_spent=session["time_spent"][i]
                )
        
        # Step 2: System analyzes user patterns
        user_patterns = tooltip_system.analyze_user_patterns(user_id)
        
        assert "frequently_accessed" in user_patterns
        assert "rarely_accessed" in user_patterns
        assert "progression_path" in user_patterns
        
        # User should show progression from basic to advanced features
        assert "advanced_options" in user_patterns["frequently_accessed"]
        assert user_patterns["experience_level"] == "intermediate" or user_patterns["experience_level"] == "advanced"
        
        # Step 3: System adapts tooltip behavior
        adapted_tooltip = tooltip_system.get_tooltip(
            "advanced_options",
            user_id=user_id,
            adaptive=True
        )
        
        # Should be shorter/more concise for experienced user
        original_tooltip = all_tooltips["advanced_options"]
        assert len(adapted_tooltip) <= len(original_tooltip) or "shortcut" in adapted_tooltip.lower()
        
        # Step 4: System provides personalized recommendations
        recommendations = tooltip_system.get_personalized_recommendations(user_id)
        
        assert recommendations is not None
        assert len(recommendations) > 0
        
        # Should recommend features user hasn't explored much
        unexplored_features = [tip for tip in recommendations if "api" in tip.lower() or "bulk" in tip.lower()]
        assert len(unexplored_features) > 0


class TestUserJourneyPrerequisiteIntegration:
    """Test user journey scenarios with prerequisite validation integration."""
    
    def test_user_journey_with_prerequisite_failures(self):
        """Test user journey when prerequisites fail and recovery process."""
        user_id = uuid4()
        
        # Step 1: User attempts to start chat
        logic = PrerequisiteValidationLogic()
        ui = PrerequisiteChecklistUI()
        
        # Mock failed prerequisites
        with patch('src.services.prerequisite_checker.OllamaConnectivityChecker') as mock_ollama:
            mock_ollama_instance = mock_ollama.return_value
            mock_ollama_instance.name = "ollama_connectivity"
            mock_ollama_instance.check.return_value = {
                "passed": False,
                "message": "Ollama service is not running",
                "details": {"error": "Connection refused"},
                "resolution_steps": [
                    "Start the Ollama service",
                    "Check if port 11434 is available",
                    "Verify Ollama installation"
                ],
                "estimated_fix_time": "2-5 minutes"
            }
            
            logic.register_checker(mock_ollama_instance)
            
            # Step 2: System detects prerequisite failure
            validation_result = logic.validate_prerequisites_for_operation(user_id, "chat_interaction")
            
            assert validation_result["overall_status"] == "failed"
            assert not validation_result["individual_results"]["ollama_connectivity"]["passed"]
            
            # Step 3: System presents user-friendly resolution UI
            with patch('streamlit.error') as mock_error, \
                 patch('streamlit.info') as mock_info, \
                 patch('streamlit.button') as mock_button, \
                 patch('streamlit.progress') as mock_progress:
                
                mock_button.return_value = True  # User clicks "Try to Fix"
                
                resolution_result = ui.render_prerequisite_resolution(
                    user_id,
                    "chat_interaction",
                    validation_result
                )
                
                # Should show error and resolution steps
                mock_error.assert_called()
                mock_info.assert_called()
                
                # Should provide fix button
                mock_button.assert_called()
            
            # Step 4: User follows resolution steps
            # Simulate user fixing the issue
            mock_ollama_instance.check.return_value = {
                "passed": True,
                "message": "Ollama service is now running",
                "details": {"version": "0.1.0", "response_time_ms": 200}
            }
            
            # Step 5: System re-validates prerequisites
            revalidation_result = logic.validate_prerequisites_for_operation(user_id, "chat_interaction")
            
            assert revalidation_result["overall_status"] == "passed"
            assert revalidation_result["individual_results"]["ollama_connectivity"]["passed"]
            
            # Step 6: User can now proceed with original action
            can_proceed = logic.can_proceed_with_operation(user_id, "chat_interaction")
            assert can_proceed is True
    
    def test_user_journey_with_partial_prerequisite_failures(self):
        """Test user journey with some prerequisites passing and others failing."""
        user_id = uuid4()
        
        logic = PrerequisiteValidationLogic()
        
        # Setup mixed prerequisite results
        with patch('src.services.prerequisite_checker.OllamaConnectivityChecker') as mock_ollama, \
             patch('src.services.prerequisite_checker.DatabaseConnectivityChecker') as mock_db, \
             patch('src.services.prerequisite_checker.ConsentStatusChecker') as mock_consent:
            
            # Ollama passes
            mock_ollama_instance = mock_ollama.return_value
            mock_ollama_instance.name = "ollama_connectivity"
            mock_ollama_instance.check.return_value = {"passed": True, "message": "Ollama OK"}
            
            # Database fails
            mock_db_instance = mock_db.return_value
            mock_db_instance.name = "database_connectivity"
            mock_db_instance.check.return_value = {
                "passed": False,
                "message": "Database connection failed",
                "severity": "critical",
                "blocks_operation": True
            }
            
            # Consent passes with warning
            mock_consent_instance = mock_consent.return_value
            mock_consent_instance.name = "consent_status"
            mock_consent_instance.check.return_value = {
                "passed": True,
                "message": "Consent valid but expires soon",
                "severity": "warning",
                "blocks_operation": False
            }
            
            logic.register_checker(mock_ollama_instance)
            logic.register_checker(mock_db_instance)
            logic.register_checker(mock_consent_instance)
            
            # User attempts image generation
            validation_result = logic.validate_prerequisites_for_operation(user_id, "image_generation")
            
            # Should fail due to database issue
            assert validation_result["overall_status"] == "failed"
            
            # Should show mixed results
            results = validation_result["individual_results"]
            assert results["ollama_connectivity"]["passed"] is True
            assert results["database_connectivity"]["passed"] is False
            assert results["consent_status"]["passed"] is True
            
            # Should identify blocking vs non-blocking issues
            blocking_issues = [name for name, result in results.items() 
                             if not result["passed"] and result.get("blocks_operation", True)]
            warning_issues = [name for name, result in results.items() 
                            if result["passed"] and result.get("severity") == "warning"]
            
            assert "database_connectivity" in blocking_issues
            assert "consent_status" in warning_issues


if __name__ == "__main__":
    pytest.main([__file__, "-v"])