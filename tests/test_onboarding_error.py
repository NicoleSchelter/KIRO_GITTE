#!/usr/bin/env python3
"""
Test script to identify the specific onboarding error.
"""

import sys
import traceback
from uuid import uuid4

def test_onboarding_logic():
    """Test the onboarding logic initialization."""
    try:
        print("Testing onboarding logic initialization...")
        
        # Test database initialization
        print("1. Testing database initialization...")
        from src.data.database import setup_database
        setup_database()
        print("   ✓ Database initialized successfully")
        
        # Test onboarding logic creation
        print("2. Testing onboarding logic creation...")
        from src.logic.onboarding import get_onboarding_logic
        onboarding_logic = get_onboarding_logic()
        print("   ✓ Onboarding logic created successfully")
        
        # Test getting user state
        print("3. Testing get_user_onboarding_state...")
        test_user_id = uuid4()
        state = onboarding_logic.get_user_onboarding_state(test_user_id)
        print(f"   ✓ Got onboarding state: {state}")
        
        print("\n✅ All tests passed! The onboarding logic is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_onboarding_logic()
    sys.exit(0 if success else 1)