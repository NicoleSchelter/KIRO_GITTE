"""
Centralized text management system for internationalization (i18n) support.
Provides localized text strings and runtime language switching.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TextManager:
    """Manages localized text strings for the application."""

    default_language: str = "en"
    current_language: str = "en"
    texts: dict[str, dict[str, str]] = field(default_factory=dict)
    fallback_texts: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize text manager with default texts."""
        self._load_default_texts()
        self._load_text_files()

        # Override language from environment
        if env_lang := os.getenv("LANGUAGE"):
            self.current_language = env_lang

    def _load_default_texts(self) -> None:
        """Load default English text strings."""
        default_texts = {
            "en": {
                # Application
                "app_title": "GITTE - Great Individual Tutor Embodiment",
                "app_subtitle": "Personalized Learning Assistant Avatar Creation",
                # Authentication
                "login_title": "Login to GITTE",
                "register_title": "Register for GITTE",
                "username_label": "Username",
                "password_label": "Password",
                "login_button": "Login",
                "register_button": "Register",
                "logout_button": "Logout",
                # Consent
                "consent_title": "Privacy Consent",
                "consent_required": "You must provide consent to continue",
                "consent_description": "We need your consent to process your data for personalized learning experiences.",
                "consent_agree": "I agree to the privacy policy",
                "consent_disagree": "I do not agree",
                "consent_withdraw": "Withdraw Consent",
                # Survey
                "survey_title": "Personalization Survey",
                "survey_description": "Help us create your personalized learning assistant",
                "survey_learning_style": "What is your preferred learning style?",
                "survey_difficulty": "What difficulty level do you prefer?",
                "survey_interests": "What are your main interests?",
                "survey_submit": "Submit Survey",
                # Chat
                "chat_title": "Embodiment Chat",
                "chat_description": "Describe your ideal learning assistant",
                "chat_placeholder": "Tell me about your ideal learning assistant...",
                "chat_send": "Send",
                "chat_clear": "Clear Chat",
                # Image Generation
                "image_generation_title": "Avatar Generation",
                "image_generation_description": "Generate visual representations of your learning assistant",
                "image_prompt_label": "Describe the appearance:",
                "image_generate_button": "Generate Avatar",
                "image_regenerate_button": "Generate Another",
                "image_save_button": "Save Avatar",
                # Admin
                "admin_title": "GITTE Administration",
                "admin_dashboard": "Dashboard",
                "admin_users": "User Management",
                "admin_exports": "Data Exports",
                "admin_statistics": "System Statistics",
                "admin_pald_analysis": "PALD Analysis",
                # Navigation
                "nav_home": "Home",
                "nav_chat": "Chat",
                "nav_images": "Images",
                "nav_admin": "Admin",
                "nav_profile": "Profile",
                # Messages
                "success_registration": "Registration successful! Please log in.",
                "success_consent_recorded": "Consent recorded successfully.",
                "success_image_generated": "Avatar generated successfully!",
                "success_data_exported": "Data exported successfully.",
                "success_settings_saved": "Settings saved successfully.",
                # Errors
                "error_generic": "An error occurred. Please try again.",
                "error_auth_failed": "Authentication failed. Please check your credentials.",
                "error_consent_required": "Consent is required to access this feature.",
                "error_image_generation_failed": "Failed to generate image. Please try again.",
                "error_data_export_failed": "Failed to export data. Please try again.",
                "error_invalid_input": "Invalid input. Please check your data.",
                "error_network": "Network error. Please check your connection.",
                "error_server": "Server error. Please try again later.",
                # Status
                "status_loading": "Loading...",
                "status_generating": "Generating...",
                "status_processing": "Processing...",
                "status_saving": "Saving...",
                "status_complete": "Complete",
                # Accessibility
                "aria_menu": "Main menu",
                "aria_close": "Close",
                "aria_expand": "Expand",
                "aria_collapse": "Collapse",
                "aria_loading": "Loading content",
                # Data and Privacy
                "privacy_policy": "Privacy Policy",
                "terms_of_service": "Terms of Service",
                "data_deletion": "Delete My Data",
                "data_export": "Export My Data",
                "consent_version": "Consent Version 1.0",
                # Feature Descriptions
                "feature_chat_desc": "Interactive chat to define your learning assistant",
                "feature_image_desc": "Generate visual avatars for your assistant",
                "feature_personalization_desc": "Customize your learning experience",
                "feature_privacy_desc": "Your data is protected and encrypted",
            }
        }

        self.texts.update(default_texts)
        self.fallback_texts = default_texts["en"]

    def _load_text_files(self) -> None:
        """Load text files from the locales directory."""
        locales_dir = Path("config/locales")
        if not locales_dir.exists():
            return

        for locale_file in locales_dir.glob("*.json"):
            language_code = locale_file.stem
            try:
                with open(locale_file, encoding="utf-8") as f:
                    texts = json.load(f)
                    self.texts[language_code] = texts
            except Exception as e:
                print(f"Warning: Failed to load locale file {locale_file}: {e}")

    def get_text(self, key: str, language: str | None = None, **kwargs) -> str:
        """
        Get localized text string.

        Args:
            key: Text key to retrieve
            language: Language code (uses current_language if None)
            **kwargs: Format parameters for string interpolation

        Returns:
            Localized text string
        """
        lang = language or self.current_language

        # Try to get text in requested language
        text = self.texts.get(lang, {}).get(key)

        # Fallback to default language
        if text is None:
            text = self.texts.get(self.default_language, {}).get(key)

        # Final fallback to key itself
        if text is None:
            text = self.fallback_texts.get(key, key)

        # Apply string formatting if parameters provided
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                # If formatting fails, return unformatted text
                pass

        return text

    def set_language(self, language: str) -> bool:
        """
        Set the current language.

        Args:
            language: Language code to set

        Returns:
            True if language was set successfully, False otherwise
        """
        if language in self.texts:
            self.current_language = language
            return True
        return False

    def get_available_languages(self) -> list[str]:
        """Get list of available language codes."""
        return list(self.texts.keys())

    def add_texts(self, language: str, texts: dict[str, str]) -> None:
        """
        Add or update texts for a language.

        Args:
            language: Language code
            texts: Dictionary of key-value text pairs
        """
        if language not in self.texts:
            self.texts[language] = {}
        self.texts[language].update(texts)

    def export_texts(self, language: str) -> dict[str, str] | None:
        """
        Export texts for a specific language.

        Args:
            language: Language code

        Returns:
            Dictionary of texts or None if language not found
        """
        return self.texts.get(language)

    def save_texts_to_file(self, language: str, file_path: str) -> bool:
        """
        Save texts for a language to a JSON file.

        Args:
            language: Language code
            file_path: Path to save the file

        Returns:
            True if saved successfully, False otherwise
        """
        texts = self.export_texts(language)
        if texts is None:
            return False

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(texts, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False


def create_locale_files() -> None:
    """Create default locale files for supported languages."""
    locales_dir = Path("config/locales")
    locales_dir.mkdir(exist_ok=True)

    # German translations (example)
    german_texts = {
        "app_title": "GITTE - Großartiger Individueller Tutor Verkörperung",
        "login_title": "Bei GITTE anmelden",
        "register_title": "Für GITTE registrieren",
        "username_label": "Benutzername",
        "password_label": "Passwort",
        "login_button": "Anmelden",
        "register_button": "Registrieren",
        "consent_title": "Datenschutz-Einverständnis",
        "consent_required": "Sie müssen Ihre Einverständnis geben, um fortzufahren",
        "error_generic": "Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
        "success_registration": "Registrierung erfolgreich! Bitte melden Sie sich an.",
    }

    with open(locales_dir / "de.json", "w", encoding="utf-8") as f:
        json.dump(german_texts, f, indent=2, ensure_ascii=False)

    # Spanish translations (example)
    spanish_texts = {
        "app_title": "GITTE - Gran Encarnación de Tutor Individual",
        "login_title": "Iniciar sesión en GITTE",
        "register_title": "Registrarse en GITTE",
        "username_label": "Nombre de usuario",
        "password_label": "Contraseña",
        "login_button": "Iniciar sesión",
        "register_button": "Registrarse",
        "consent_title": "Consentimiento de Privacidad",
        "consent_required": "Debe dar su consentimiento para continuar",
        "error_generic": "Ocurrió un error. Por favor, inténtelo de nuevo.",
        "success_registration": "¡Registro exitoso! Por favor, inicie sesión.",
    }

    with open(locales_dir / "es.json", "w", encoding="utf-8") as f:
        json.dump(spanish_texts, f, indent=2, ensure_ascii=False)


# Global text manager instance
text_manager = TextManager()


# Convenience function for getting text
def get_text(key: str, language: str | None = None, **kwargs) -> str:
    """Convenience function to get localized text."""
    return text_manager.get_text(key, language, **kwargs)


# Convenience function for setting language
def set_language(language: str) -> bool:
    """Convenience function to set current language."""
    return text_manager.set_language(language)
