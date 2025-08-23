"""
Enhanced Survey UI components for GITTE system.
Provides Streamlit components for dynamic survey rendering and study participation.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from pathlib import Path

import streamlit as st

from config.config import get_text, config
from src.data.database import get_session  
from src.services.survey_service import SurveyService
from src.logic.survey_logic import SurveyLogic, SurveyDefinition, SurveyQuestion
from src.ui.tooltip_integration import form_submit_button

logger = logging.getLogger(__name__)


class SurveyUI:
    """Enhanced UI components for dynamic survey rendering and study participation."""

    def __init__(self):
        """Initialize survey UI with dynamic survey capabilities."""
        self.survey_service = None
        self.survey_logic = None
    
    def _get_survey_logic(self) -> SurveyLogic:
        """Get survey logic instance with proper dependency injection."""
        # Create fresh instances for each request to ensure proper session handling
        db_session = get_session()
        survey_service = SurveyService(db_session)
        return SurveyLogic(survey_service)
    
    def render_dynamic_survey(
        self, 
        pseudonym_id: UUID, 
        survey_file_path: Optional[str] = None
    ) -> Dict[str, Any] | None:
        """
        Render dynamic survey loaded from CSV/Excel file for study participation.
        
        Args:
            pseudonym_id: Participant pseudonym ID
            survey_file_path: Path to survey definition file (defaults to config)
            
        Returns:
            Survey responses if completed, None otherwise
        """
        try:
            # Use default survey file if not specified
            if survey_file_path is None:
                survey_file_path = getattr(config, 'SURVEY_FILE_PATH', 'config/sample_survey.csv')
            
            # Load survey definition
            survey_logic = self._get_survey_logic()
            
            # Check if survey file exists
            if not Path(survey_file_path).exists():
                st.error(f"Survey file not found: {survey_file_path}")
                if getattr(config, 'SURVEY_FALLBACK_ENABLED', True):
                    st.info("Using fallback personalization survey...")
                    return self.render_personalization_survey(pseudonym_id)
                return None
            
            try:
                survey_definition = survey_logic.load_survey_definition(survey_file_path)
            except Exception as e:
                logger.error(f"Failed to load survey definition: {e}")
                st.error(f"Failed to load survey: {str(e)}")
                if getattr(config, 'SURVEY_FALLBACK_ENABLED', True):
                    st.info("Using fallback personalization survey...")
                    return self.render_personalization_survey(pseudonym_id)
                return None
            
            # Render survey UI
            return self._render_survey_form(pseudonym_id, survey_definition)
            
        except Exception as e:
            logger.exception(f"Error rendering dynamic survey: {e}")
            st.error("An error occurred while loading the survey. Please try again.")
            return None
    
    def _render_survey_form(
        self, 
        pseudonym_id: UUID, 
        survey_definition: SurveyDefinition
    ) -> Dict[str, Any] | None:
        """
        Render survey form based on survey definition.
        
        Args:
            pseudonym_id: Participant pseudonym ID
            survey_definition: Survey definition to render
            
        Returns:
            Survey responses if submitted, None otherwise
        """
        # Display survey header
        st.title(survey_definition.title)
        if survey_definition.description:
            st.write(survey_definition.description)
        
        # Initialize session state for form data
        form_key = f"dynamic_survey_{survey_definition.survey_id}"
        if f"{form_key}_responses" not in st.session_state:
            st.session_state[f"{form_key}_responses"] = {}
        
        with st.form(form_key):
            responses = {}
            validation_errors = []
            
            # Render each question
            for question in survey_definition.questions:
                try:
                    response_value = self._render_question(question)
                    if response_value is not None:
                        responses[question.question_id] = response_value
                except Exception as e:
                    logger.error(f"Error rendering question {question.question_id}: {e}")
                    st.error(f"Error rendering question: {question.question_text}")
            
            # Submit buttons
            col1, col2 = st.columns(2)
            
            with col1:
                submit_button = form_submit_button("Submit Survey", type="primary")
            
            with col2:
                skip_button = form_submit_button("Skip Survey")
        
        # Handle form submission
        if submit_button:
            return self._handle_survey_submission(pseudonym_id, responses, survey_definition)
        elif skip_button:
            return self._handle_survey_skip(pseudonym_id)
        
        return None
    
    def _render_question(self, question: SurveyQuestion) -> Any:
        """
        Render individual survey question based on type.
        
        Args:
            question: Question definition
            
        Returns:
            User response value
        """
        # Add required indicator
        label = question.question_text
        if question.required:
            label += " *"
        
        # Render based on question type
        if question.type == "text":
            return st.text_area(
                label,
                key=f"q_{question.question_id}",
                help="This field is required" if question.required else None
            )
        
        elif question.type == "number":
            return st.number_input(
                label,
                key=f"q_{question.question_id}",
                help="This field is required" if question.required else None
            )
        
        elif question.type == "choice":
            if not question.options:
                st.error(f"No options provided for choice question: {question.question_text}")
                return None
            
            # Add empty option for non-required questions
            options = question.options.copy()
            if not question.required:
                options = [""] + options
            
            return st.selectbox(
                label,
                options=options,
                key=f"q_{question.question_id}",
                help="This field is required" if question.required else None
            )
        
        elif question.type == "multi-choice":
            if not question.options:
                st.error(f"No options provided for multi-choice question: {question.question_text}")
                return None
            
            return st.multiselect(
                label,
                options=question.options,
                key=f"q_{question.question_id}",
                help="This field is required" if question.required else "Select all that apply"
            )
        
        else:
            st.error(f"Unsupported question type: {question.type}")
            return None
    
    def _handle_survey_submission(
        self, 
        pseudonym_id: UUID, 
        responses: Dict[str, Any], 
        survey_definition: SurveyDefinition
    ) -> Dict[str, Any] | None:
        """
        Handle survey submission with validation and storage.
        
        Args:
            pseudonym_id: Participant pseudonym ID
            responses: User responses
            survey_definition: Survey definition for validation
            
        Returns:
            Survey responses if successful, None otherwise
        """
        try:
            # Get survey logic instance
            survey_logic = self._get_survey_logic()
            
            # Validate responses
            validation_result = survey_logic.validate_survey_responses(responses, survey_definition)
            
            if not validation_result.is_valid:
                # Display validation errors
                st.error("Please correct the following errors:")
                for error in validation_result.errors:
                    st.error(f"• {error}")
                return None
            
            # Display warnings if any
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    st.warning(f"• {warning}")
            
            # Process submission
            submission_result = survey_logic.process_survey_submission(
                pseudonym_id, responses, survey_definition
            )
            
            if submission_result.success:
                st.success("Survey submitted successfully!")
                st.balloons()
                
                # Create response data for return
                survey_data = {
                    "survey_id": survey_definition.survey_id,
                    "survey_version": survey_definition.version,
                    "responses": responses,
                    "completed_at": st.session_state.get("current_time", ""),
                    "survey_skipped": False
                }
                
                logger.info(f"Dynamic survey completed for pseudonym {pseudonym_id}")
                return survey_data
            else:
                # Display submission errors
                st.error("Failed to submit survey:")
                for error in submission_result.errors:
                    st.error(f"• {error}")
                return None
                
        except Exception as e:
            logger.exception(f"Error handling survey submission: {e}")
            st.error("An error occurred while submitting the survey. Please try again.")
            return None
    
    def _handle_survey_skip(self, pseudonym_id: UUID) -> Dict[str, Any]:
        """
        Handle survey skip with default responses.
        
        Args:
            pseudonym_id: Participant pseudonym ID
            
        Returns:
            Default survey data
        """
        try:
            # Create default survey data
            default_data = {
                "survey_id": "default_survey",
                "survey_version": "1.0",
                "responses": {
                    "survey_skipped": True,
                    "default_preferences": "applied"
                },
                "completed_at": st.session_state.get("current_time", ""),
                "survey_skipped": True
            }
            
            st.info("Survey skipped. Default preferences have been applied.")
            logger.info(f"Dynamic survey skipped for pseudonym {pseudonym_id}")
            return default_data
            
        except Exception as e:
            logger.exception(f"Error handling survey skip: {e}")
            st.error("An error occurred while skipping the survey. Please try again.")
            return None
    
    def render_survey_validation_preview(self, survey_file_path: str) -> bool:
        """
        Render survey validation preview for admin/testing purposes.
        
        Args:
            survey_file_path: Path to survey file to validate
            
        Returns:
            True if survey is valid, False otherwise
        """
        try:
            st.subheader("Survey Validation Preview")
            
            if not Path(survey_file_path).exists():
                st.error(f"Survey file not found: {survey_file_path}")
                return False
            
            # Load and validate survey
            survey_logic = self._get_survey_logic()
            survey_definition = survey_logic.load_survey_definition(survey_file_path)
            
            # Display survey info
            st.success(f"✅ Survey loaded successfully!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Survey ID:** {survey_definition.survey_id}")
                st.write(f"**Title:** {survey_definition.title}")
            with col2:
                st.write(f"**Version:** {survey_definition.version}")
                st.write(f"**Questions:** {len(survey_definition.questions)}")
            
            # Display questions
            st.write("**Questions:**")
            for i, question in enumerate(survey_definition.questions, 1):
                with st.expander(f"Question {i}: {question.question_text}"):
                    st.write(f"**Type:** {question.type}")
                    st.write(f"**Required:** {'Yes' if question.required else 'No'}")
                    if question.options:
                        st.write(f"**Options:** {', '.join(question.options)}")
            
            return True
            
        except Exception as e:
            st.error(f"Survey validation failed: {str(e)}")
            logger.error(f"Survey validation error: {e}")
            return False

    def render_personalization_survey(self, user_id: UUID) -> dict[str, Any] | None:
        """
        Render personalization survey for collecting minimal data.

        Args:
            user_id: User identifier

        Returns:
            Dict containing survey responses if completed, None otherwise
        """
        st.title(get_text("survey_title"))

        st.write(
            """
        Help us personalize your learning experience! This brief survey will help us create 
        an embodiment that matches your preferences and learning style.
        """
        )

        with st.form("personalization_survey"):
            # Learning Preferences Section
            st.subheader("🎓 Learning Preferences")

            learning_style = st.selectbox(
                "What's your preferred learning style?",
                options=[
                    "Visual (diagrams, images, charts)",
                    "Auditory (explanations, discussions)",
                    "Kinesthetic (hands-on, interactive)",
                    "Reading/Writing (text-based)",
                    "Mixed (combination of styles)",
                ],
                help="This helps us tailor the interaction style",
            )

            difficulty_preference = st.select_slider(
                "Preferred difficulty level",
                options=["Beginner", "Intermediate", "Advanced", "Expert"],
                value="Intermediate",
                help="We'll adjust explanations to match your level",
            )

            feedback_style = st.selectbox(
                "How do you prefer to receive feedback?",
                options=[
                    "Encouraging and supportive",
                    "Direct and constructive",
                    "Detailed with examples",
                    "Brief and to the point",
                ],
            )

            # Interaction Preferences Section
            st.subheader("💬 Interaction Preferences")

            communication_style = st.selectbox(
                "Preferred communication style",
                options=[
                    "Formal and professional",
                    "Friendly and casual",
                    "Enthusiastic and energetic",
                    "Calm and patient",
                ],
            )

            pace_preference = st.select_slider(
                "Preferred learning pace",
                options=["Very Slow", "Slow", "Moderate", "Fast", "Very Fast"],
                value="Moderate",
            )

            # Embodiment Appearance Section
            st.subheader("👤 Embodiment Appearance")

            appearance_style = st.selectbox(
                "Preferred embodiment style",
                options=[
                    "Professional and formal",
                    "Friendly and approachable",
                    "Creative and artistic",
                    "Modern and tech-savvy",
                    "Classic and traditional",
                ],
            )

            age_preference = st.selectbox(
                "Preferred apparent age range",
                options=[
                    "Young adult (20-30)",
                    "Adult (30-45)",
                    "Mature adult (45-60)",
                    "No preference",
                ],
            )

            # Subject Areas Section
            st.subheader("📚 Subject Areas")

            subject_areas = st.multiselect(
                "What subjects are you most interested in?",
                options=[
                    "Mathematics",
                    "Science",
                    "Technology",
                    "Engineering",
                    "Language Arts",
                    "History",
                    "Art",
                    "Music",
                    "Business",
                    "Psychology",
                    "Philosophy",
                    "Other",
                ],
                help="Select all that apply",
            )

            # Goals and Motivation Section
            st.subheader("🎯 Goals and Motivation")

            learning_goals = st.text_area(
                "What are your main learning goals?",
                placeholder="e.g., Improve problem-solving skills, learn new concepts, prepare for exams...",
                help="Optional: Tell us what you hope to achieve",
            )

            motivation_factors = st.multiselect(
                "What motivates you to learn?",
                options=[
                    "Personal growth",
                    "Career advancement",
                    "Academic requirements",
                    "Curiosity and interest",
                    "Problem-solving challenges",
                    "Creative expression",
                ],
            )

            # Privacy and Personalization Section
            st.subheader("🔒 Privacy and Personalization")

            personalization_level = st.select_slider(
                "How much personalization do you want?",
                options=["Minimal", "Moderate", "High", "Maximum"],
                value="Moderate",
                help="Higher levels provide more tailored experiences but use more data",
            )

            data_sharing_comfort = st.select_slider(
                "Comfort level with anonymized data sharing for improvements",
                options=[
                    "Not comfortable",
                    "Somewhat comfortable",
                    "Comfortable",
                    "Very comfortable",
                ],
                value="Somewhat comfortable",
                help="This helps improve the system for everyone while protecting your privacy",
            )

            # Submit button
            col1, col2 = st.columns(2)

            with col1:
                survey_submitted = form_submit_button("Complete Survey", type="primary")

            with col2:
                survey_skipped = form_submit_button("Skip Survey")

        # Handle survey submission
        if survey_submitted:
            # Validate required fields
            if not subject_areas:
                st.warning("Please select at least one subject area of interest.")
                return None

            # Create survey response data
            survey_data = {
                "learning_preferences": {
                    "learning_style": learning_style,
                    "difficulty_preference": difficulty_preference,
                    "feedback_style": feedback_style,
                    "pace_preference": pace_preference,
                },
                "interaction_style": {
                    "communication_style": communication_style,
                    "personalization_level": personalization_level,
                },
                "appearance": {"style": appearance_style, "age_preference": age_preference},
                "subject_areas": subject_areas,
                "goals": {
                    "learning_goals": learning_goals,
                    "motivation_factors": motivation_factors,
                },
                "privacy": {
                    "personalization_level": personalization_level,
                    "data_sharing_comfort": data_sharing_comfort,
                },
                "survey_completed_at": st.session_state.get("current_time", ""),
                "survey_version": "1.0",
                "survey_skipped": False,
            }

            # Save survey data to dedicated survey table (NOT PALD)
            try:
                # Step 1: Save survey response (hard requirement)
                self._save_complete_survey(user_id, survey_data)
                
                # Show success message after Step 1 succeeds
                st.success("Survey completed successfully! Your preferences have been saved.")
                st.balloons()
                
                # Step 2: Save preferences (non-blocking)
                try:
                    prefs_success = self._save_survey_preferences(user_id, survey_data)
                    if not prefs_success:
                        st.warning("⚠️ Survey saved, but there was an issue saving your preferences.")
                except Exception as e:
                    logger.exception(f"Failed to save preferences for user {user_id}: {e}")
                    st.warning("⚠️ Survey saved, but there was an issue saving your preferences.")
                
                # Step 3: Advance onboarding step (non-blocking)
                try:
                    advance_success = self._advance_onboarding_step(user_id, "survey")
                    if not advance_success:
                        st.warning("⚠️ Survey saved, but there was an issue updating your progress. You can continue normally.")
                except Exception as e:
                    logger.exception(f"Failed to advance onboarding for user {user_id}: {e}")
                    st.warning("⚠️ Survey saved, but there was an issue updating your progress. You can continue normally.")

                logger.info(f"Survey completed for user {user_id}")
                return survey_data

            except Exception as e:
                logger.exception(f"Failed to save survey response for user {user_id}: {e}")
                st.error("Failed to save survey data. Please try again.")
                return None

        # Handle survey skipping
        elif survey_skipped:
            try:
                default_data = self._create_default_survey_data()
                staged_data = self._stage_survey_for_skip(user_id, default_data)
                # Store in session state for later use
                st.session_state["staged_survey_data"] = staged_data
                st.info("Survey skipped. Default preferences have been applied.")
                logger.info(f"Survey skipped for user {user_id}")
                return staged_data
            except Exception as e:
                logger.error(f"Failed to save default survey data for user {user_id}: {e}")
                st.error("Failed to save default preferences. Please try again.")
                return None

        return None

    def render_survey_summary(self, survey_data: dict[str, Any]) -> None:
        """
        Render a summary of survey responses.

        Args:
            survey_data: Survey response data
        """
        st.subheader("📋 Your Preferences Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.write(
                "**Learning Style:**",
                survey_data.get("learning_preferences", {}).get("learning_style", "Not specified"),
            )
            st.write(
                "**Difficulty Level:**",
                survey_data.get("learning_preferences", {}).get(
                    "difficulty_preference", "Not specified"
                ),
            )
            st.write(
                "**Communication Style:**",
                survey_data.get("interaction_style", {}).get(
                    "communication_style", "Not specified"
                ),
            )

        with col2:
            st.write(
                "**Embodiment Style:**",
                survey_data.get("appearance", {}).get("style", "Not specified"),
            )
            st.write(
                "**Learning Pace:**",
                survey_data.get("learning_preferences", {}).get("pace_preference", "Not specified"),
            )
            st.write(
                "**Personalization Level:**",
                survey_data.get("privacy", {}).get("personalization_level", "Not specified"),
            )

        # Subject areas
        subject_areas = survey_data.get("subject_areas", [])
        if subject_areas:
            st.write("**Subject Areas:**", ", ".join(subject_areas))

        # Learning goals
        learning_goals = survey_data.get("goals", {}).get("learning_goals", "")
        if learning_goals:
            st.write("**Learning Goals:**")
            st.write(learning_goals)

    def render_survey_update_form(
        self, user_id: UUID, current_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Render form to update survey preferences.

        Args:
            user_id: User identifier
            current_data: Current survey data

        Returns:
            Updated survey data if form submitted, None otherwise
        """
        st.subheader("Update Your Preferences")

        with st.expander("Update Learning Preferences", expanded=False):
            with st.form("update_learning_prefs"):
                current_learning = current_data.get("learning_preferences", {})

                learning_style = st.selectbox(
                    "Learning style",
                    options=[
                        "Visual (diagrams, images, charts)",
                        "Auditory (explanations, discussions)",
                        "Kinesthetic (hands-on, interactive)",
                        "Reading/Writing (text-based)",
                        "Mixed (combination of styles)",
                    ],
                    index=self._get_option_index(
                        [
                            "Visual (diagrams, images, charts)",
                            "Auditory (explanations, discussions)",
                            "Kinesthetic (hands-on, interactive)",
                            "Reading/Writing (text-based)",
                            "Mixed (combination of styles)",
                        ],
                        current_learning.get("learning_style", ""),
                    ),
                )

                difficulty_preference = st.select_slider(
                    "Difficulty level",
                    options=["Beginner", "Intermediate", "Advanced", "Expert"],
                    value=current_learning.get("difficulty_preference", "Intermediate"),
                )

                if form_submit_button("Update Learning Preferences"):
                    updated_data = current_data.copy()
                    updated_data["learning_preferences"] = {
                        **current_learning,
                        "learning_style": learning_style,
                        "difficulty_preference": difficulty_preference,
                    }

                    try:
                        self._save_complete_survey(user_id, updated_data)
                        st.success("Learning preferences updated!")
                        return updated_data
                    except Exception as e:
                        st.error("Failed to update preferences.")
                        logger.error(f"Failed to update survey data: {e}")

        return None

    def _save_complete_survey(self, user_id: UUID, survey_data: dict[str, Any]) -> None:
        """Save completed survey data using unified service."""
        try:
            # Ensure user_id is a proper UUID
            if isinstance(user_id, str):
                from uuid import UUID as UUIDClass
                user_id = UUIDClass(user_id)
            
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                result = survey_service.save_complete_survey(
                    user_id=user_id,
                    survey_data=survey_data,
                    survey_version=survey_data.get("survey_version", "1.0")
                )
                
                logger.info(f"Successfully saved complete survey with ID: {result.id}")
                
        except Exception as e:
            logger.exception(f"Error saving complete survey for user {user_id}: {e}")
            raise e

    def _stage_survey_for_skip(self, user_id: UUID, survey_data: dict[str, Any]) -> dict[str, Any]:
        """Stage survey data for skip flow without DB persistence."""
        try:
            # Ensure user_id is a proper UUID
            if isinstance(user_id, str):
                from uuid import UUID as UUIDClass
                user_id = UUIDClass(user_id)
            
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                staged_data = survey_service.stage_survey_data_for_skip(
                    user_id=user_id,
                    survey_data=survey_data
                )
                
                logger.info(f"Successfully staged survey data for user {user_id}")
                return staged_data
                
        except Exception as e:
            logger.exception(f"Error staging survey data for user {user_id}: {e}")
            raise e

    def _save_survey_preferences(self, user_id: UUID, survey_data: dict[str, Any]) -> bool:
        """Save survey preferences using survey service. Returns False on failure, does not throw."""
        try:
            # Ensure user_id is a proper UUID
            if isinstance(user_id, str):
                from uuid import UUID as UUIDClass
                user_id = UUIDClass(user_id)
            
            # Extract preferences from survey data
            preferences = {
                "learning_style": survey_data.get("learning_preferences", {}).get("learning_style"),
                "difficulty_preference": survey_data.get("learning_preferences", {}).get("difficulty_preference"),
                "communication_style": survey_data.get("interaction_style", {}).get("communication_style"),
                "personalization_level": survey_data.get("privacy", {}).get("personalization_level"),
                "appearance_style": survey_data.get("appearance", {}).get("style"),
                "age_preference": survey_data.get("appearance", {}).get("age_preference"),
                "subject_areas": survey_data.get("subject_areas", []),
                "learning_goals": survey_data.get("goals", {}).get("learning_goals"),
                "motivation_factors": survey_data.get("goals", {}).get("motivation_factors", []),
            }
            
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                success = survey_service.upsert_user_preferences(
                    user_id=user_id,
                    preferences=preferences,
                    category="onboarding_step_survey"
                )
                
                if success:
                    logger.info(f"Successfully saved survey preferences for user {user_id}")
                return success
                
        except Exception as e:
            logger.exception(f"Error saving survey preferences for user {user_id}: {e}")
            return False

    def _advance_onboarding_step(self, user_id: UUID, completed_step: str) -> bool:
        """Advance onboarding step. Returns False on failure, does not throw."""
        try:
            # Ensure user_id is a proper UUID
            if isinstance(user_id, str):
                from uuid import UUID as UUIDClass
                user_id = UUIDClass(user_id)
            
            from src.services.onboarding_service import advance_onboarding_step
            success = advance_onboarding_step(user_id, completed_step)
            
            if success:
                logger.info(f"Successfully advanced onboarding step for user {user_id}: {completed_step}")
            return success
                
        except Exception as e:
            logger.exception(f"Error advancing onboarding step for user {user_id}, step {completed_step}: {e}")
            return False

    def _create_default_survey_data(self) -> dict[str, Any]:
        """Create default survey data for users who skip the survey."""
        return {
            "learning_preferences": {
                "learning_style": "Mixed (combination of styles)",
                "difficulty_preference": "Intermediate",
                "feedback_style": "Encouraging and supportive",
                "pace_preference": "Moderate",
            },
            "interaction_style": {
                "communication_style": "Friendly and casual",
                "personalization_level": "Moderate",
            },
            "appearance": {"style": "Friendly and approachable", "age_preference": "Adult (30-45)"},
            "subject_areas": ["General"],
            "goals": {
                "learning_goals": "General learning and improvement",
                "motivation_factors": ["Personal growth", "Curiosity and interest"],
            },
            "privacy": {
                "personalization_level": "Moderate",
                "data_sharing_comfort": "Somewhat comfortable",
            },
            "survey_completed_at": st.session_state.get("current_time", ""),
            "survey_version": "1.0",
            "survey_skipped": True,
        }

    def _get_option_index(self, options: list[str], value: str) -> int:
        """Get index of option in list, return 0 if not found."""
        try:
            return options.index(value)
        except ValueError:
            return 0


# Global survey UI instance
survey_ui = SurveyUI()


# Convenience functions
def render_personalization_survey(user_id: UUID) -> dict[str, Any] | None:
    """Render personalization survey."""
    return survey_ui.render_personalization_survey(user_id)


def render_dynamic_survey(pseudonym_id: UUID, survey_file_path: Optional[str] = None) -> Dict[str, Any] | None:
    """Render dynamic survey for study participation."""
    return survey_ui.render_dynamic_survey(pseudonym_id, survey_file_path)


def render_survey_validation_preview(survey_file_path: str) -> bool:
    """Render survey validation preview."""
    return survey_ui.render_survey_validation_preview(survey_file_path)


def render_survey_summary(survey_data: dict[str, Any]) -> None:
    """Render survey summary."""
    survey_ui.render_survey_summary(survey_data)


def render_survey_update_form(user_id: UUID, current_data: dict[str, Any]) -> dict[str, Any] | None:
    """Render survey update form."""
    return survey_ui.render_survey_update_form(user_id, current_data)