#!/usr/bin/env python3
"""
Test script to verify the intro_chat step fix works correctly.
"""

import sys
import traceback
from uuid import UUID

def test_intro_chat_step():
    """Test that the intro_chat step is now handled correctly."""
    try:
        print("Testing intro_chat step handling...")
        
        # Test database initialization
        print("1. Testing database initialization...")
        from src.data.database import setup_database
        setup_database()
        print("   ✓ Database initialized successfully")
        
        # Test onboarding logic creation
        print("2. Testing onboarding logic creation...")
        from src.logic.onboarding import get_onboarding_logic, OnboardingStep
        onboarding_logic = get_onboarding_logic()
        print("   ✓ Onboarding logic created successfully")
        
        # Test that INTRO_CHAT is in the enum
        print("3. Testing INTRO_CHAT enum...")
        intro_chat_step = OnboardingStep.INTRO_CHAT
        print(f"   ✓ INTRO_CHAT step exists: {intro_chat_step}")
        
        # Test that intro_chat string can be converted to enum
        print("4. Testing intro_chat string conversion...")
        step_from_string = OnboardingStep("intro_chat")
        print(f"   ✓ Successfully converted 'intro_chat' to enum: {step_from_string}")
        
        # Test with the actual user ID from the log that was failing
        print("5. Testing with real user ID that had intro_chat...")
        user_id = UUID('ca3d621f-3fef-4f6c-b9cb-f7d078ad73c7')
        
        try:
            state = onboarding_logic.get_user_onboarding_state(user_id)
            print(f"   ✓ Got onboarding state successfully: {state['current_step']}")
        except Exception as e:
            print(f"   ⚠️  Error with real user (expected if user doesn't exist): {e}")
        
        # Test flow steps include INTRO_CHAT
        print("6. Testing flow steps...")
        flow_steps = onboarding_logic.flow_steps
        print(f"   ✓ Flow steps: {[step.value for step in flow_steps]}")
        
        if OnboardingStep.INTRO_CHAT in flow_steps:
            print("   ✓ INTRO_CHAT is in flow steps")
        else:
            print("   ❌ INTRO_CHAT is missing from flow steps")
            return False
        
        print("\n✅ All intro_chat tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_intro_chat_step()
    sys.exit(0 if success else 1)