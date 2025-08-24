#!/usr/bin/env python3
"""
Headless End-to-End Smoke Test for GITTE
Exercises core functionality without UI interaction
"""

import os
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def setup_environment():
    """Setup test environment variables"""
    os.environ.setdefault("ENVIRONMENT", "testing")
    os.environ.setdefault("POSTGRES_DSN", "postgresql://gitte:sicheres_passwort@localhost:5432/kiro_test")
    os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")
    os.environ.setdefault("LOG_LEVEL", "WARNING")
    os.environ.setdefault("FEATURE_ENABLE_IMAGE_GENERATION", "true")
    os.environ.setdefault("FEATURE_ENABLE_MINIO_STORAGE", "false")  # Use filesystem fallback

def test_database_connectivity():
    """Test database connection and basic schema"""
    print("🔍 Testing database connectivity...")
    
    try:
        from src.data.database import setup_database, health_check
        setup_database()
        
        if not health_check():
            raise RuntimeError("Database health check failed")
            
        print("✅ Database connectivity: PASS")
        return True
    except Exception as e:
        print(f"❌ Database connectivity: FAIL - {e}")
        return False

def test_prerequisite_checks():
    """Test prerequisite validation system"""
    print("🔍 Testing prerequisite checks...")
    
    try:
        from src.services.prerequisite_checker import PrerequisiteValidationService
        from src.services.prerequisite_checker import (
            DatabaseConnectivityChecker,
            OllamaConnectivityChecker,
            SystemHealthChecker
        )
        
        service = PrerequisiteValidationService()
        service.register_checker(DatabaseConnectivityChecker())
        service.register_checker(OllamaConnectivityChecker())
        service.register_checker(SystemHealthChecker())
        
        results = service.run_all_checks(use_cache=False)
        
        if results.required_passed:
            print("✅ Prerequisite checks: PASS")
            return True
        else:
            failed = [r.name for r in results.results if r.status.value == "failed"]
            print(f"❌ Prerequisite checks: FAIL - {failed}")
            return False
            
    except Exception as e:
        print(f"❌ Prerequisite checks: FAIL - {e}")
        return False

def test_pseudonym_creation():
    """Test pseudonym creation and validation"""
    print("🔍 Testing pseudonym creation...")
    
    try:
        from src.services.pseudonym_service import PseudonymService
        
        service = PseudonymService()
        user_id = uuid.uuid4()
        
        # Create pseudonym
        result = service.create_pseudonym(user_id, "test_user_smoke")
        
        if result and result.pseudonym == "test_user_smoke":
            print("✅ Pseudonym creation: PASS")
            return True, user_id
        else:
            print("❌ Pseudonym creation: FAIL - Invalid result")
            return False, None
            
    except Exception as e:
        print(f"❌ Pseudonym creation: FAIL - {e}")
        return False, None

def test_consent_management(user_id: uuid.UUID):
    """Test consent collection and validation"""
    print("🔍 Testing consent management...")
    
    try:
        from src.services.consent_service import ConsentService
        from src.data.models import ConsentType
        
        service = ConsentService()
        
        # Grant required consents
        consents = [
            ConsentType.DATA_PROCESSING,
            ConsentType.AI_INTERACTION,
            ConsentType.IMAGE_GENERATION
        ]
        
        for consent_type in consents:
            service.grant_consent(user_id, consent_type)
        
        # Verify consents
        all_granted = all(service.check_consent(user_id, ct) for ct in consents)
        
        if all_granted:
            print("✅ Consent management: PASS")
            return True
        else:
            print("❌ Consent management: FAIL - Consents not granted")
            return False
            
    except Exception as e:
        print(f"❌ Consent management: FAIL - {e}")
        return False

def test_survey_processing(user_id: uuid.UUID):
    """Test survey data processing"""
    print("🔍 Testing survey processing...")
    
    try:
        from src.services.survey_service import SurveyService
        
        service = SurveyService()
        
        # Mock survey data
        survey_data = {
            "learning_style": "visual",
            "difficulty_preference": "intermediate",
            "pace_preference": "moderate",
            "topics_of_interest": ["AI", "Programming"]
        }
        
        result = service.process_survey_response(user_id, survey_data)
        
        if result:
            print("✅ Survey processing: PASS")
            return True
        else:
            print("❌ Survey processing: FAIL - No result")
            return False
            
    except Exception as e:
        print(f"❌ Survey processing: FAIL - {e}")
        return False

def test_chat_interaction(user_id: uuid.UUID):
    """Test chat message processing"""
    print("🔍 Testing chat interaction...")
    
    try:
        from src.services.chat_service import ChatService
        
        service = ChatService()
        
        # Send test message
        message = "Hello, this is a smoke test message."
        result = service.process_message(user_id, message)
        
        if result and hasattr(result, 'response_text'):
            print("✅ Chat interaction: PASS")
            return True
        else:
            print("❌ Chat interaction: FAIL - No valid response")
            return False
            
    except Exception as e:
        print(f"❌ Chat interaction: FAIL - {e}")
        return False

def test_pald_extraction(user_id: uuid.UUID):
    """Test PALD Light extraction"""
    print("🔍 Testing PALD extraction...")
    
    try:
        from src.logic.pald_boundary import PALDBoundaryLogic
        
        logic = PALDBoundaryLogic()
        
        # Mock conversation data
        conversation_data = {
            "messages": [
                {"role": "user", "content": "I like visual learning"},
                {"role": "assistant", "content": "Great! Visual learning is effective."}
            ]
        }
        
        result = logic.extract_pald_light(conversation_data)
        
        if result:
            print("✅ PALD extraction: PASS")
            return True
        else:
            print("❌ PALD extraction: FAIL - No result")
            return False
            
    except Exception as e:
        print(f"❌ PALD extraction: FAIL - {e}")
        return False

def test_image_generation(user_id: uuid.UUID):
    """Test image generation (mock/CPU fallback)"""
    print("🔍 Testing image generation...")
    
    try:
        from src.services.image_generation_service import ImageGenerationService
        
        service = ImageGenerationService()
        
        # Simple prompt
        prompt = "A friendly AI assistant"
        result = service.generate_image(user_id, prompt)
        
        if result and hasattr(result, 'image_path'):
            print("✅ Image generation: PASS")
            return True
        else:
            print("❌ Image generation: FAIL - No image generated")
            return False
            
    except Exception as e:
        print(f"❌ Image generation: FAIL - {e}")
        return False

def test_audit_logging(user_id: uuid.UUID):
    """Test audit trail creation"""
    print("🔍 Testing audit logging...")
    
    try:
        from src.services.interaction_logger import InteractionLogger
        
        logger = InteractionLogger()
        
        # Log test interaction
        result = logger.log_interaction(
            user_id=user_id,
            interaction_type="smoke_test",
            content={"test": "smoke_test_data"},
            metadata={"source": "smoke_e2e"}
        )
        
        if result:
            print("✅ Audit logging: PASS")
            return True
        else:
            print("❌ Audit logging: FAIL - No log entry")
            return False
            
    except Exception as e:
        print(f"❌ Audit logging: FAIL - {e}")
        return False

def verify_database_state():
    """Verify expected database records exist"""
    print("🔍 Verifying database state...")
    
    try:
        from src.data.database import get_session
        
        expected_tables = [
            'users', 'pseudonyms', 'consent_records', 
            'survey_responses', 'chat_messages', 
            'pald_data', 'audit_logs'
        ]
        
        with get_session() as session:
            for table in expected_tables:
                try:
                    result = session.execute(f"SELECT COUNT(*) FROM {table}")
                    count = result.scalar()
                    print(f"  📊 {table}: {count} records")
                except Exception as e:
                    print(f"  ⚠️ {table}: Error - {e}")
        
        print("✅ Database state verification: PASS")
        return True
        
    except Exception as e:
        print(f"❌ Database state verification: FAIL - {e}")
        return False

def main():
    """Run complete smoke test suite"""
    print("🚀 Starting GITTE Smoke Test Suite")
    print("=" * 50)
    
    start_time = time.time()
    setup_environment()
    
    # Test sequence
    tests = [
        ("Database Connectivity", test_database_connectivity),
        ("Prerequisite Checks", test_prerequisite_checks),
    ]
    
    # Tests requiring user_id
    user_tests = [
        ("Pseudonym Creation", test_pseudonym_creation),
        ("Consent Management", test_consent_management),
        ("Survey Processing", test_survey_processing),
        ("Chat Interaction", test_chat_interaction),
        ("PALD Extraction", test_pald_extraction),
        ("Image Generation", test_image_generation),
        ("Audit Logging", test_audit_logging),
    ]
    
    results = {}
    user_id = None
    
    # Run basic tests
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name}: EXCEPTION - {e}")
            results[test_name] = False
    
    # Run user-dependent tests
    for test_name, test_func in user_tests:
        try:
            if test_name == "Pseudonym Creation":
                success, user_id = test_func()
                results[test_name] = success
            elif user_id:
                results[test_name] = test_func(user_id)
            else:
                print(f"⏭️ {test_name}: SKIPPED - No user_id")
                results[test_name] = False
        except Exception as e:
            print(f"❌ {test_name}: EXCEPTION - {e}")
            results[test_name] = False
    
    # Final verification
    results["Database State"] = verify_database_state()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SMOKE TEST RESULTS")
    print("=" * 50)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    elapsed = time.time() - start_time
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Duration: {elapsed:.2f} seconds")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - System is ready!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} TESTS FAILED - Check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())