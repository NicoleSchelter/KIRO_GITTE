"""
Survey UI components for GITTE system.
Provides Streamlit components for collecting minimal personalization data.
"""

import logging
from typing import Any
from uuid import UUID

import streamlit as st

from config.config import get_text
from src.data.database import get_session  
from src.services.survey_service import SurveyService
from src.ui.tooltip_integration import form_submit_button
from src.logic.pald_boundary import PALDBoundaryEnforcer

logger = logging.getLogger(__name__)


class SurveyUI:
    """UI components for personalization survey."""

    def __init__(self):
        # Initialize boundary enforcer for validation
        from src.services.pald_schema_registry_service import PALDSchemaRegistryService
        from config.config import config
        # Note: These will be properly injected in production via dependency injection

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


def render_survey_summary(survey_data: dict[str, Any]) -> None:
    """Render survey summary."""
    survey_ui.render_survey_summary(survey_data)


def render_survey_update_form(user_id: UUID, current_data: dict[str, Any]) -> dict[str, Any] | None:
    """Render survey update form."""
    return survey_ui.render_survey_update_form(user_id, current_data)