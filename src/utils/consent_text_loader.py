"""
Consent text loader utility for GITTE system.
Loads detailed consent information from markdown files.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from src.data.models import ConsentType

logger = logging.getLogger(__name__)

# Base directory for consent text files
CONSENT_TEXTS_DIR = Path(__file__).parent.parent.parent / "consent_texts"


def load_consent_text(consent_type: ConsentType) -> Optional[str]:
    """
    Load detailed consent text from markdown file.
    
    Args:
        consent_type: The type of consent to load text for
        
    Returns:
        Markdown content as string, or None if file not found
    """
    try:
        filename_map = {
            ConsentType.DATA_PROCESSING: "data_processing.md",
            ConsentType.AI_INTERACTION: "ai_interaction.md", 
            ConsentType.IMAGE_GENERATION: "image_generation.md",
            ConsentType.FEDERATED_LEARNING: "federated_learning.md",
            ConsentType.ANALYTICS: "analytics.md",
            ConsentType.INVESTIGATION_PARTICIPATION: "investigation_participation.md",
        }
        
        filename = filename_map.get(consent_type)
        if not filename:
            logger.warning(f"No consent text file mapped for consent type: {consent_type}")
            return None
            
        file_path = CONSENT_TEXTS_DIR / filename
        
        if not file_path.exists():
            logger.warning(f"Consent text file not found: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        logger.debug(f"Loaded consent text for {consent_type} from {file_path}")
        return content
        
    except Exception as e:
        logger.error(f"Error loading consent text for {consent_type}: {e}")
        return None


def get_all_consent_texts() -> Dict[ConsentType, str]:
    """
    Load all available consent texts.
    
    Returns:
        Dictionary mapping consent types to their markdown content
    """
    consent_texts = {}
    
    for consent_type in ConsentType:
        text = load_consent_text(consent_type)
        if text:
            consent_texts[consent_type] = text
            
    return consent_texts


def render_consent_text_expander(consent_type: ConsentType, label: str = None) -> None:
    """
    Render consent text in an expandable section.
    
    Args:
        consent_type: The type of consent to display
        label: Custom label for the expander (defaults to consent type display name)
    """
    try:
        import streamlit as st
        
        text = load_consent_text(consent_type)
        
        if not text:
            st.warning(f"Detailed information for {consent_type.value} is currently unavailable.")
            return
            
        if not label:
            label = f"📋 View detailed {consent_type.value.replace('_', ' ').title()} information"
            
        with st.expander(label, expanded=False):
            st.markdown(text)
            
    except Exception as e:
        logger.error(f"Error rendering consent text expander for {consent_type}: {e}")
        try:
            import streamlit as st
            st.error("Error loading detailed consent information.")
        except ImportError:
            pass


def render_consent_text_modal(consent_type: ConsentType) -> None:
    """
    Render consent text in a modal dialog (using Streamlit components).
    
    Args:
        consent_type: The type of consent to display
    """
    try:
        import streamlit as st
        
        text = load_consent_text(consent_type)
        
        if not text:
            st.warning(f"Detailed information for {consent_type.value} is currently unavailable.")
            return
            
        # Create a unique key for the modal state
        modal_key = f"consent_modal_{consent_type.value}"
        
        # Button to open modal
        if st.button(f"📖 Read full {consent_type.value.replace('_', ' ').title()} details", 
                    key=f"open_{modal_key}"):
            st.session_state[modal_key] = True
            
        # Display modal content if opened
        if st.session_state.get(modal_key, False):
            st.markdown(f"### {consent_type.value.replace('_', ' ').title()} - Detailed Information")
            st.markdown(text)
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("✖️ Close", key=f"close_{modal_key}"):
                    st.session_state[modal_key] = False
                    st.rerun()
                    
    except Exception as e:
        logger.error(f"Error rendering consent text modal for {consent_type}: {e}")
        try:
            import streamlit as st
            st.error("Error loading detailed consent information.")
        except ImportError:
            pass


def get_cached_consent_text(consent_type_value: str) -> Optional[str]:
    """
    Get cached consent text for improved performance.
    
    Args:
        consent_type_value: String value of the consent type
        
    Returns:
        Cached markdown content
    """
    try:
        import streamlit as st
        
        # Use streamlit cache if available
        @st.cache_data
        def _cached_load(consent_type_value: str) -> Optional[str]:
            consent_type = ConsentType(consent_type_value)
            return load_consent_text(consent_type)
            
        return _cached_load(consent_type_value)
    except ImportError:
        # Fallback without caching if streamlit not available
        try:
            consent_type = ConsentType(consent_type_value)
            return load_consent_text(consent_type)
        except ValueError:
            logger.error(f"Invalid consent type value: {consent_type_value}")
            return None
    except ValueError:
        logger.error(f"Invalid consent type value: {consent_type_value}")
        return None