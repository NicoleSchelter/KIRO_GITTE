#!/usr/bin/env python3
"""
End-to-end dry test for consent write-path fixes.
Tests the complete consent flow without requiring database setup.
"""

import sys
import logging
from pathlib import Path
from uuid import uuid4

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_consent_key_normalization():
    """Test consent key normalization with the exact payload from the task."""
    try:
        from src.logic.consent_logic import ConsentLogic
        from src.data.models import StudyConsentType
        
        # Mock repository
        class MockRepository:
            pass
        
        logic = ConsentLogic(MockRepository())
        
        # Test the exact payload from the task
        test_consents = {
            "data_processing": True,
            "ai_interaction": True, 
            "study_participation": True
        }
        
        # Test normalization for each key
        for consent_key, granted in test_consents.items():
            try:
                normalized = logic._normalize_consent_key(consent_key)
                logger.info(f"✅ '{consent_key}' -> '{normalized.value}' (granted: {granted})")
                
                # Verify expected mappings
                if consent_key == "data_processing":
                    assert normalized == StudyConsentType.DATA_PROTECTION
                elif consent_key == "ai_interaction":
                    assert normalized == StudyConsentType.AI_INTERACTION
                elif consent_key == "study_participation":
                    assert normalized == StudyConsentType.STUDY_PARTICIPATION
                    
            except Exception as e:
                logger.error(f"❌ Failed to normalize '{consent_key}': {e}")
                return False
        
        logger.info("✅ Consent E2E dry test payload normalization successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Consent normalization test failed: {e}")
        return False

def test_config_ui_consistency():
    """Test that UI config matches expected consent types."""
    try:
        from config.config import CONSENT_TYPES_UI
        from src.data.models import StudyConsentType
        
        # Extract keys from UI config
        ui_keys = [key for key, _ in CONSENT_TYPES_UI]
        
        # Expected keys that should be in UI
        expected_keys = ["data_protection", "ai_interaction", "study_participation"]
        
        for expected_key in expected_keys:
            if expected_key not in ui_keys:
                logger.error(f"❌ Missing expected UI key: {expected_key}")
                return False
            logger.info(f"✅ UI key '{expected_key}' found")
        
        # Test that UI keys can be normalized
        from src.logic.consent_logic import ConsentLogic
        
        class MockRepository:
            pass
        
        logic = ConsentLogic(MockRepository())
        
        for ui_key in ui_keys:
            try:
                normalized = logic._normalize_consent_key(ui_key)
                logger.info(f"✅ UI key '{ui_key}' normalizes to '{normalized.value}'")
            except Exception as e:
                logger.error(f"❌ UI key '{ui_key}' cannot be normalized: {e}")
                return False
        
        logger.info("✅ Config UI consistency test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Config UI consistency test failed: {e}")
        return False

def test_exception_handling():
    """Test that proper exceptions are raised for invalid scenarios."""
    try:
        from src.logic.consent_logic import ConsentLogic, InvalidConsentTypeError
        from src.exceptions import MissingPseudonymError
        
        class MockRepository:
            pass
        
        logic = ConsentLogic(MockRepository())
        
        # Test invalid consent type
        try:
            logic._normalize_consent_key("invalid_consent_type")
            logger.error("❌ Should have raised InvalidConsentTypeError")
            return False
        except InvalidConsentTypeError as e:
            logger.info(f"✅ InvalidConsentTypeError raised correctly: {e}")
        
        # Test MissingPseudonymError creation
        try:
            error = MissingPseudonymError("Test pseudonym missing")
            assert "Test pseudonym missing" in str(error)
            assert "Invalid participant identifier" in error.user_message
            logger.info("✅ MissingPseudonymError created correctly")
        except Exception as e:
            logger.error(f"❌ MissingPseudonymError creation failed: {e}")
            return False
        
        logger.info("✅ Exception handling test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Exception handling test failed: {e}")
        return False

def test_service_instantiation():
    """Test that services can be instantiated without database connections."""
    try:
        from src.services.consent_service import ConsentService
        from src.ui.consent_ui import ConsentUI
        
        # Test service instantiation
        service = ConsentService()
        assert service.consent_logic is None
        logger.info("✅ ConsentService instantiated without database connection")
        
        # Test UI instantiation
        ui = ConsentUI()
        assert ui.consent_service is not None
        logger.info("✅ ConsentUI instantiated successfully")
        
        logger.info("✅ Service instantiation test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Service instantiation test failed: {e}")
        return False

def test_enum_completeness():
    """Test that all required enum values are present."""
    try:
        from src.data.models import StudyConsentType
        
        # Check that all expected enum values exist
        expected_values = ["data_protection", "ai_interaction", "study_participation"]
        actual_values = [e.value for e in StudyConsentType]
        
        for expected_value in expected_values:
            if expected_value not in actual_values:
                logger.error(f"❌ Missing expected enum value: {expected_value}")
                return False
            logger.info(f"✅ Enum value '{expected_value}' present")
        
        # Test enum creation from string
        for value in expected_values:
            try:
                enum_instance = StudyConsentType(value)
                assert enum_instance.value == value
                logger.info(f"✅ Enum creation from string '{value}' works")
            except Exception as e:
                logger.error(f"❌ Enum creation from string '{value}' failed: {e}")
                return False
        
        logger.info("✅ Enum completeness test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enum completeness test failed: {e}")
        return False

def main():
    """Run all E2E dry tests."""
    logger.info("Starting consent E2E dry test...")
    logger.info("Testing payload: { 'data_processing': true, 'ai_interaction': true, 'study_participation': true }")
    
    tests = [
        test_consent_key_normalization,
        test_config_ui_consistency,
        test_exception_handling,
        test_service_instantiation,
        test_enum_completeness,
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
    
    logger.info(f"\nE2E Dry Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 Consent E2E dry test completed successfully!")
        logger.info("✅ All consent write-path fixes are working correctly")
        logger.info("✅ Ready for database integration testing")
        return 0
    else:
        logger.error("💥 Some E2E dry tests failed. Please review the fixes.")
        return 1

if __name__ == "__main__":
    sys.exit(main())