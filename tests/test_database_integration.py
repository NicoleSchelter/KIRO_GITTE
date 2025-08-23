"""
Database integration tests for Study Participation system.
Tests database schema, foreign key relationships, cascade operations, and data integrity.

This test suite validates:
- Database schema integrity and constraints
- Foreign key relationships between all tables
- Cascade deletion behavior for participant data
- Transaction handling and rollback scenarios
- Data consistency across related tables
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID

from src.data.models import (
    StudyConsentType, 
    ChatMessageType, 
    StudyPALDType,
    Pseudon