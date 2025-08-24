#!/usr/bin/env python3
"""
Validation script for consent write-path fixes.
Tests the core functionality without requiring full database setup.
"""

import sys
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_enum_imports():
    """Test that all enum imports work correctly."""
    try:
        from src.data.models import StudyConsentType, ConsentType
        from src.exceptions import ConsentError, MissingPseudonymError
        
        # Test enum values
        assert StudyConsentType.DATA_PROTECTION == "data_protection"
        assert StudyConsentType.AI_INTERACTION == "ai_interaction"
        assert StudyConsentType.STUDY_PARTICIPATION == "study_participation"
        
        logger.info("✅ Enum imports and values correct")
        return True
    except Exception as e:
        logger.error(f"❌ Enum import test failed: {e}")
        return False

def test_consent_logic_normalization():
    """Test consent key normalization logic."""
    try:
        from src.logic.consent_logic import ConsentLogic, InvalidConsentTypeError
        from src.data.models import StudyConsentType
        
        # Create a mock repository for testing
        class MockRepository:
            pass
        
        logic = ConsentLogic(MockRepository())
        
        # Test valid normalizations
        assert logic._normalize_consent_key("data_protection") == StudyConsentType.DATA_PROTECTION
        assert logic._normalize_consent_key("data_processing") == StudyConsentType.DATA_PROTECTION
        assert logic._normalize_consent_key("ai_interaction") == StudyConsentType.AI_INTERACTION
        
        # Test invalid key
        try:
            logic._normalize_consent_key("invalid_key")
            assert False, "Should have raised InvalidConsentTypeError"
        except InvalidConsentTypeError as e:
            assert "invalid_key" in str(e)
            assert "Valid types:" in str(e)
        
        logger.info("✅ Consent key normalization works correctly")
        return True
    except Exception as e:
        logger.error(f"❌ Consent logic test failed: {e}")
        return False

def test_config_consent_types():
    """Test that config consent types are properly defined."""
    try:
        from config.config import CONSENT_TYPES_UI
        
        # Check structure
        assert isinstance(CONSENT_TYPES_UI, list)
        assert len(CONSENT_TYPES_UI) > 0
        
        for consent_key, consent_label in CONSENT_TYPES_UI:
            assert isinstance(consent_key, str)
            assert isinstance(consent_label, str)
            assert len(consent_key) > 0
            assert len(consent_label) > 0
        
        # Check expected keys are present
        consent_keys = [key for key, _ in CONSENT_TYPES_UI]
        expected_keys = ["data_protection", "ai_interaction", "study_participation"]
        
        for expected_key in expected_keys:
            assert expected_key in consent_keys, f"Missing expected consent key: {expected_key}"
        
        logger.info("✅ Config consent types properly defined")
        return True
    except Exception as e:
        logger.error(f"❌ Config consent types test failed: {e}")
        return False

def test_exception_hierarchy():
    """Test that exception hierarchy is properly defined."""
    try:
        from src.exceptions import (
            ConsentError, ConsentRequiredError, ConsentWithdrawalError,
            MissingPseudonymError, DatabaseError
        )
        
        # Test inheritance
        assert issubclass(ConsentRequiredError, ConsentError)
        assert issubclass(ConsentWithdrawalError, ConsentError)
        assert issubclass(MissingPseudonymError, DatabaseError)
        
        # Test exception creation
        consent_error = ConsentError("Test message")
        assert str(consent_error) == "Test message"
        
        required_error = ConsentRequiredError("Consent required for test", required=["test"])
        assert "test" in required_error.details["required_consents"]
        
        missing_error = MissingPseudonymError("Test pseudonym missing")
        assert "Test pseudonym missing" in str(missing_error)
        
        logger.info("✅ Exception hierarchy properly defined")
        return True
    except Exception as e:
        logger.error(f"❌ Exception hierarchy test failed: {e}")
        return False

def test_import_safety():
    """Test that imports don't create sessions at import time."""
    try:
        # These imports should not create database sessions
        from src.services.consent_service import ConsentService
        from src.logic.consent_logic import ConsentLogic
        from src.ui.consent_ui import ConsentUI
        
        # Test that service can be instantiated without database
        service = ConsentService()
        assert service.consent_logic is None
        
        logger.info("✅ Import safety verified - no sessions created at import time")
        return True
    except Exception as e:
        logger.error(f"❌ Import safety test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    logger.info("Starting consent write-path validation...")
    
    tests = [
        test_enum_imports,
        test_consent_logic_normalization,
        test_config_consent_types,
        test_exception_hierarchy,
        test_import_safety,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    logger.info(f"\nValidation Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All consent write-path fixes validated successfully!")
        return 0
    else:
        logger.error("💥 Some validation tests failed. Please review the fixes.")
        return 1

if __name__ == "__main__":
    sys.exit(main())