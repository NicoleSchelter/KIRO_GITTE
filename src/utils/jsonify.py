"""
JSON serialization utilities for GITTE system.
Provides utilities to convert complex objects to JSON-serializable formats.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID


def to_jsonable(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable formats.
    Handles UUID→str, datetime/date→isoformat, Enum→value, set→list.
    
    Args:
        obj: Object to serialize (can be dict, list, set, or primitive)
        
    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, set):
        return [to_jsonable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: to_jsonable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [to_jsonable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(to_jsonable(item) for item in obj)
    else:
        return obj