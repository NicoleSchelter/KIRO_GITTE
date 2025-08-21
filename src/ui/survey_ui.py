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
from src.data.schemas import PALDDataCreate
from src.logic.pald import PALDManager
from src.ui.tooltip_integration import form_submit_button

logger = logging.getLogger(__name__)


class SurveyUI:
    """UI components for personalization survey."""

    def __init__(self):
        pass

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
                if form_submit_button("Skip Survey"):
                    return self._create_default_survey_data()

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
            }

            # Save survey data as PALD data
            try:
                self._save_survey_as_pald(user_id, survey_data)
                st.success("Survey completed successfully! Your preferences have been saved.")
                st.balloons()

                logger.info(f"Survey completed for user {user_id}")
                return survey_data

            except Exception as e:
                logger.error(f"Failed to save survey data for user {user_id}: {e}")
                st.error("Failed to save survey data. Please try again.")
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
                        self._save_survey_as_pald(user_id, updated_data)
                        st.success("Learning preferences updated!")
                        return updated_data
                    except Exception as e:
                        st.error("Failed to update preferences.")
                        logger.error(f"Failed to update survey data: {e}")

        return None

    def _save_survey_as_pald(self, user_id: UUID, survey_data: dict[str, Any]) -> None:
        """Save survey data as PALD data."""
        with get_session() as db_session:
            pald_manager = PALDManager(db_session)

            pald_create = PALDDataCreate(pald_content=survey_data, schema_version="1.0")

            pald_manager.create_pald_data(user_id, pald_create)

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
