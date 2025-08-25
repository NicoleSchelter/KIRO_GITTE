#!/usr/bin/env python3
"""
Test script to verify the intro chat step UI implementation.
"""

import sys
import traceback
from uuid import uuid4

def test_intro_chat_ui():
    """Test the intro chat UI implementation."""
    try:
        print("Testing intro chat UI implementation...")
        
        # Test 1: Import the onboarding UI
        print("1. Testing onboarding UI import...")
        from src.ui.onboarding_ui import OnboardingUI
        print("   ✅ OnboardingUI imported successfully")
        
        # Test 2: Create onboarding UI instance
        print("2. Testing onboarding UI instantiation...")
        ui = OnboardingUI()
        print("   ✅ OnboardingUI instance created successfully")
        
        # Test 3: Check if intro chat method exists
        print("3. Testing intro chat method existence...")
        assert hasattr(ui, '_render_intro_chat_step'), "Missing _render_intro_chat_step method"
        assert hasattr(ui, '_get_intro_welcome_message'), "Missing _get_intro_welcome_message method"
        assert hasattr(ui, '_generate_intro_chat_response'), "Missing _generate_intro_chat_response method"
        print("   ✅ All intro chat methods exist")
        
        # Test 4: Test welcome message generation
        print("4. Testing welcome message generation...")
        test_user_id = uuid4()
        welcome_msg = ui._get_intro_welcome_message(test_user_id)
        assert isinstance(welcome_msg, str), "Welcome message should be a string"
        assert len(welcome_msg) > 50, "Welcome message should be substantial"
        assert "learning assistant" in welcome_msg.lower(), "Welcome message should mention learning assistant"
        print("   ✅ Welcome message generation works")
        
        # Test 5: Test response generation
        print("5. Testing response generation...")
        test_inputs = [
            "Hello!",
            "How can you help me learn?",
            "What can you do?",
            "Tell me about yourself",
            "I want to learn math",
            "This is a random message"
        ]
        
        for i, test_input in enumerate(test_inputs):
            response = ui._generate_intro_chat_response(test_user_id, test_input, i + 1)
            assert isinstance(response, str), f"Response should be string for input: {test_input}"
            assert len(response) > 20, f"Response should be substantial for input: {test_input}"
            print(f"   ✅ Response generated for: '{test_input[:30]}...'")
        
        # Test 6: Test OnboardingStep enum includes INTRO_CHAT
        print("6. Testing OnboardingStep enum...")
        from src.logic.onboarding import OnboardingStep
        assert hasattr(OnboardingStep, 'INTRO_CHAT'), "OnboardingStep should have INTRO_CHAT"
        assert OnboardingStep.INTRO_CHAT.value == "intro_chat", "INTRO_CHAT value should be 'intro_chat'"
        print("   ✅ OnboardingStep.INTRO_CHAT exists and has correct value")
        
        print("\n🎉 All intro chat UI tests passed!")
        print("\n✅ Summary:")
        print("  - OnboardingUI can be imported and instantiated")
        print("  - All required intro chat methods exist")
        print("  - Welcome message generation works")
        print("  - Response generation works for various inputs")
        print("  - OnboardingStep.INTRO_CHAT enum exists")
        print("\n📋 What users will see:")
        print("  - Engaging welcome screen after completing survey")
        print("  - Interactive chat interface with AI assistant")
        print("  - Progress tracking (3 messages needed to continue)")
        print("  - Helpful conversation suggestions")
        print("  - Clear next step button when ready")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_intro_chat_ui()
    sys.exit(0 if success else 1)