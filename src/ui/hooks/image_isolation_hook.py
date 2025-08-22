"""
Streamlit Hook for Image Isolation Service.
Provides a simple interface for running image isolation in Streamlit UI.
"""

import logging
from typing import Dict, Any, Optional
import streamlit as st

from src.services.image_isolation_service import ImageIsolationService, ImageIsolationConfig
from src.exceptions import (
    RequiredPrerequisiteError,
    ServiceUnavailableError,
    PrerequisiteCheckFailedError,
    GITTEError
)
from config.config import config

logger = logging.getLogger(__name__)


def run_isolation(image_path: str, model: str | None = None) -> Dict[str, Any]:
    """
    Run image isolation with user-friendly error handling.
    
    Args:
        image_path: Path to input image
        model: Model to use (defaults to config default)
        
    Returns:
        dict with status, user_message, and result data if successful
    """
    try:
        # Create isolation service
        isolation_config = ImageIsolationConfig(
            enabled=config.image_isolation.enabled,
            endpoint=config.image_isolation.endpoint,
            timeout_seconds=config.image_isolation.timeout_seconds,
            retries=config.image_isolation.retries,
            model_default=config.image_isolation.model_default
        )
        
        service = ImageIsolationService(isolation_config)
        
        # Run isolation
        result = service.isolate(image_path, model)
        
        return {
            "status": "success",
            "user_message": "Image isolation completed successfully",
            "data": result
        }
        
    except RequiredPrerequisiteError as e:
        logger.warning(f"Prerequisite error in image isolation: {e}")
        return {
            "status": "error",
            "user_message": "Image isolation service is not properly configured",
            "error_type": "configuration",
            "resolution_steps": e.resolution_steps
        }
        
    except ServiceUnavailableError as e:
        logger.error(f"Service unavailable in image isolation: {e}")
        return {
            "status": "error",
            "user_message": "Image isolation service is currently unavailable",
            "error_type": "service_unavailable",
            "details": "Please try again later or check service status"
        }
        
    except PrerequisiteCheckFailedError as e:
        logger.error(f"Prerequisite check failed in image isolation: {e}")
        return {
            "status": "error",
            "user_message": "Image isolation failed due to service issues",
            "error_type": "service_error",
            "details": "Please check service configuration and try again"
        }
        
    except GITTEError as e:
        logger.error(f"GITTE error in image isolation: {e}")
        return {
            "status": "error",
            "user_message": "An unexpected error occurred during image isolation",
            "error_type": "system_error",
            "details": "Please contact support if the problem persists"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in image isolation: {e}")
        return {
            "status": "error",
            "user_message": "An unexpected error occurred",
            "error_type": "unknown_error",
            "details": "Please try again or contact support"
        }


def run_isolation_with_spinner(image_path: str, model: str | None = None) -> Dict[str, Any]:
    """
    Run image isolation with Streamlit spinner for better UX.
    
    Args:
        image_path: Path to input image
        model: Model to use (defaults to config default)
        
    Returns:
        dict with status, user_message, and result data if successful
    """
    with st.spinner("Running image isolation..."):
        return run_isolation(image_path, model)
