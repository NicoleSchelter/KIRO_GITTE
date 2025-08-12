"""
LLM Logic Layer for GITTE system.
Handles business logic for LLM interactions, embodiment chat, and conversation management.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from config.config import config
from src.services.llm_provider import LLMProviderError, LLMResponse, LLMStreamResponse
from src.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


class LLMLogic:
    """
    Logic layer for LLM operations.
    Handles business rules, conversation context, and embodiment-specific interactions.
    """

    def __init__(self, llm_service: LLMService | None = None):
        """
        Initialize LLM logic.

        Args:
            llm_service: LLM service instance (defaults to global service)
        """
        self.llm_service = llm_service or get_llm_service()
        self._conversation_contexts: dict[str, list[dict[str, str]]] = {}

    def generate_embodiment_response(
        self,
        user_message: str,
        user_id: UUID,
        embodiment_context: dict[str, Any] | None = None,
        conversation_id: str | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """
        Generate a response for embodiment chat interaction.

        Args:
            user_message: User's message
            user_id: User identifier
            embodiment_context: PALD data or embodiment preferences
            conversation_id: Conversation identifier for context
            model: Model to use (defaults to configured default)

        Returns:
            LLMResponse: Generated embodiment response
        """
        try:
            # Build conversation context
            conversation_key = conversation_id or str(user_id)
            context_messages = self._get_conversation_context(conversation_key)

            # Create embodiment-aware prompt
            prompt = self._build_embodiment_prompt(
                user_message=user_message,
                embodiment_context=embodiment_context,
                conversation_history=context_messages,
            )

            # Generate response
            response = self.llm_service.generate_response(
                prompt=prompt,
                model=model,
                parameters=self._get_embodiment_parameters(),
                user_id=user_id,
            )

            # Update conversation context
            self._update_conversation_context(
                conversation_key=conversation_key,
                user_message=user_message,
                assistant_response=response.text,
            )

            logger.info(
                f"Generated embodiment response for user {user_id}: {len(response.text)} chars"
            )
            return response

        except LLMProviderError as e:
            logger.error(f"Failed to generate embodiment response: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in embodiment response generation: {e}")
            raise LLMProviderError(f"Unexpected error: {e}")

    def generate_streaming_embodiment_response(
        self,
        user_message: str,
        user_id: UUID,
        embodiment_context: dict[str, Any] | None = None,
        conversation_id: str | None = None,
        model: str | None = None,
    ) -> LLMStreamResponse:
        """
        Generate a streaming response for embodiment chat interaction.

        Args:
            user_message: User's message
            user_id: User identifier
            embodiment_context: PALD data or embodiment preferences
            conversation_id: Conversation identifier for context
            model: Model to use (defaults to configured default)

        Returns:
            LLMStreamResponse: Streaming embodiment response
        """
        try:
            # Build conversation context
            conversation_key = conversation_id or str(user_id)
            context_messages = self._get_conversation_context(conversation_key)

            # Create embodiment-aware prompt
            prompt = self._build_embodiment_prompt(
                user_message=user_message,
                embodiment_context=embodiment_context,
                conversation_history=context_messages,
            )

            # Generate streaming response
            response = self.llm_service.generate_streaming_response(
                prompt=prompt,
                model=model,
                parameters=self._get_embodiment_parameters(),
                user_id=user_id,
            )

            # Note: For streaming, we'll update context after the stream completes
            # This requires the caller to handle context updates

            logger.info(f"Started streaming embodiment response for user {user_id}")
            return response

        except LLMProviderError as e:
            logger.error(f"Failed to generate streaming embodiment response: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in streaming embodiment response generation: {e}")
            raise LLMProviderError(f"Unexpected error: {e}")

    def generate_image_prompt(
        self,
        user_description: str,
        embodiment_context: dict[str, Any] | None = None,
        user_id: UUID | None = None,
    ) -> str:
        """
        Generate an image generation prompt based on user description and embodiment context.

        Args:
            user_description: User's description of desired image
            embodiment_context: PALD data for embodiment attributes
            user_id: User identifier

        Returns:
            str: Optimized image generation prompt
        """
        try:
            # Create prompt for generating image prompts
            system_prompt = self._build_image_prompt_generation_prompt(
                user_description=user_description, embodiment_context=embodiment_context
            )

            # Generate optimized prompt
            response = self.llm_service.generate_response(
                prompt=system_prompt,
                model=config.llm.models.get("creative", "default"),
                parameters={"temperature": 0.7, "max_tokens": 200},
                user_id=user_id,
            )

            # Extract and clean the generated prompt
            image_prompt = response.text.strip()

            # Remove any unwanted prefixes or suffixes
            if image_prompt.startswith('"') and image_prompt.endswith('"'):
                image_prompt = image_prompt[1:-1]

            logger.info(f"Generated image prompt: {len(image_prompt)} chars")
            return image_prompt

        except Exception as e:
            logger.error(f"Failed to generate image prompt: {e}")
            # Fallback to user description
            return user_description

    def update_conversation_context_after_streaming(
        self, conversation_id: str, user_message: str, assistant_response: str
    ) -> None:
        """
        Update conversation context after streaming response completes.

        Args:
            conversation_id: Conversation identifier
            user_message: User's message
            assistant_response: Complete assistant response
        """
        self._update_conversation_context(
            conversation_key=conversation_id,
            user_message=user_message,
            assistant_response=assistant_response,
        )

    def clear_conversation_context(self, conversation_id: str) -> None:
        """
        Clear conversation context for a specific conversation.

        Args:
            conversation_id: Conversation identifier
        """
        if conversation_id in self._conversation_contexts:
            del self._conversation_contexts[conversation_id]
            logger.debug(f"Cleared conversation context for {conversation_id}")

    def get_conversation_summary(self, conversation_id: str) -> dict[str, Any]:
        """
        Get summary of conversation context.

        Args:
            conversation_id: Conversation identifier

        Returns:
            Dict containing conversation summary
        """
        context = self._conversation_contexts.get(conversation_id, [])

        return {
            "conversation_id": conversation_id,
            "message_count": len(context),
            "last_updated": datetime.utcnow().isoformat() if context else None,
            "context_length": sum(len(msg["content"]) for msg in context),
        }

    def _build_embodiment_prompt(
        self,
        user_message: str,
        embodiment_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Build a prompt for embodiment chat interaction."""

        # Base system prompt for embodiment
        system_prompt = """You are a personalized learning assistant embodiment. Your role is to help users explore and define their ideal learning companion through natural conversation.

Key guidelines:
- Be warm, encouraging, and supportive
- Ask thoughtful questions about learning preferences
- Help users articulate their vision of an ideal tutor
- Adapt your personality based on the user's preferences
- Keep responses conversational and engaging
- Focus on understanding the user's learning style and preferences"""

        # Add embodiment context if available
        if embodiment_context:
            appearance = embodiment_context.get("appearance", {})
            personality = embodiment_context.get("personality", {})
            expertise = embodiment_context.get("expertise", {})
            interaction_prefs = embodiment_context.get("interaction_preferences", {})

            context_parts = []

            if appearance:
                context_parts.append(
                    f"Appearance preferences: {self._format_context_section(appearance)}"
                )

            if personality:
                context_parts.append(
                    f"Personality traits: {self._format_context_section(personality)}"
                )

            if expertise:
                context_parts.append(f"Expertise areas: {self._format_context_section(expertise)}")

            if interaction_prefs:
                context_parts.append(
                    f"Interaction preferences: {self._format_context_section(interaction_prefs)}"
                )

            if context_parts:
                system_prompt += (
                    f"\n\nUser's embodiment preferences:\n{chr(10).join(context_parts)}"
                )

        # Build conversation history
        conversation_text = ""
        if conversation_history:
            for msg in conversation_history[-10:]:  # Keep last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                conversation_text += f"\n{role.title()}: {content}"

        # Combine all parts
        full_prompt = system_prompt
        if conversation_text:
            full_prompt += f"\n\nConversation history:{conversation_text}"

        full_prompt += f"\n\nUser: {user_message}\nAssistant:"

        return full_prompt

    def _build_image_prompt_generation_prompt(
        self, user_description: str, embodiment_context: dict[str, Any] | None = None
    ) -> str:
        """Build a prompt for generating image generation prompts."""

        system_prompt = """You are an expert at creating detailed, high-quality prompts for AI image generation. Your task is to transform user descriptions into optimized prompts for creating educational tutor embodiment images.

Guidelines:
- Create detailed, specific descriptions
- Include artistic style and quality modifiers
- Focus on professional, educational appearance
- Ensure the description is appropriate for a learning context
- Keep the prompt concise but descriptive
- Include lighting and composition suggestions"""

        # Add embodiment context
        context_text = ""
        if embodiment_context:
            appearance = embodiment_context.get("appearance", {})
            if appearance:
                context_text = f"\nEmbodiment context: {self._format_context_section(appearance)}"

        prompt = f"""{system_prompt}

User description: "{user_description}"{context_text}

Generate an optimized image generation prompt (return only the prompt, no explanations):"""

        return prompt

    def _format_context_section(self, section: dict[str, Any]) -> str:
        """Format a context section for inclusion in prompts."""
        items = []
        for key, value in section.items():
            if value and value != "":
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                items.append(f"{key.replace('_', ' ')}: {value}")
        return "; ".join(items)

    def _get_embodiment_parameters(self) -> dict[str, Any]:
        """Get default parameters for embodiment responses."""
        return {
            "temperature": 0.8,  # Slightly creative but consistent
            "max_tokens": 500,  # Reasonable response length
            "top_p": 0.9,  # Focused but diverse
            "frequency_penalty": 0.1,  # Slight penalty for repetition
            "presence_penalty": 0.1,  # Encourage topic diversity
        }

    def _get_conversation_context(self, conversation_key: str) -> list[dict[str, str]]:
        """Get conversation context for a conversation."""
        return self._conversation_contexts.get(conversation_key, [])

    def _update_conversation_context(
        self, conversation_key: str, user_message: str, assistant_response: str
    ) -> None:
        """Update conversation context with new messages."""
        if conversation_key not in self._conversation_contexts:
            self._conversation_contexts[conversation_key] = []

        context = self._conversation_contexts[conversation_key]

        # Add user message
        context.append(
            {"role": "user", "content": user_message, "timestamp": datetime.utcnow().isoformat()}
        )

        # Add assistant response
        context.append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep only last 20 messages (10 exchanges) to manage memory
        if len(context) > 20:
            context = context[-20:]
            self._conversation_contexts[conversation_key] = context

        logger.debug(
            f"Updated conversation context for {conversation_key}: {len(context)} messages"
        )


# Global LLM logic instance
_llm_logic: LLMLogic | None = None


def get_llm_logic() -> LLMLogic:
    """Get the global LLM logic instance."""
    global _llm_logic
    if _llm_logic is None:
        _llm_logic = LLMLogic()
    return _llm_logic


def set_llm_logic(logic: LLMLogic) -> None:
    """Set the global LLM logic instance (useful for testing)."""
    global _llm_logic
    _llm_logic = logic


# Convenience functions for common operations
def generate_embodiment_response(
    user_message: str,
    user_id: UUID,
    embodiment_context: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    model: str | None = None,
) -> LLMResponse:
    """Generate embodiment response using the global LLM logic."""
    return get_llm_logic().generate_embodiment_response(
        user_message, user_id, embodiment_context, conversation_id, model
    )


def generate_streaming_embodiment_response(
    user_message: str,
    user_id: UUID,
    embodiment_context: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    model: str | None = None,
) -> LLMStreamResponse:
    """Generate streaming embodiment response using the global LLM logic."""
    return get_llm_logic().generate_streaming_embodiment_response(
        user_message, user_id, embodiment_context, conversation_id, model
    )


def generate_image_prompt(
    user_description: str,
    embodiment_context: dict[str, Any] | None = None,
    user_id: UUID | None = None,
) -> str:
    """Generate image prompt using the global LLM logic."""
    return get_llm_logic().generate_image_prompt(user_description, embodiment_context, user_id)
