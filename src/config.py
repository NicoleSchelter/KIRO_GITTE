# src/config.py
"""
Shim to expose central configuration from config/config.py under the src.* namespace.
Do NOT duplicate values here; import and re-export instead.
"""

# Re-export everything so existing imports keep working
from config.config import *  # noqa: F401,F403
