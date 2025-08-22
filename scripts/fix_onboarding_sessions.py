#!/usr/bin/env python3
"""
Script to fix the session management issues in onboarding.py
"""

def fix_session_management():
    """Fix the session management in onboarding logic."""
    file_path = "src/logic/onboarding.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the session management issues
    # Replace the problematic session creation with proper sync session
    old_pattern1 = '''        # Create a new session for this operation
        session_context = get_session()
        db_session = session_context.__enter__()
        return OnboardingProgressService(db_session)'''
    
    new_replacement1 = '''        # Create a new session for this operation
        from src.data.database import get_session_sync
        db_session = get_session_sync()
        return OnboardingProgressService(db_session)'''
    
    content = content.replace(old_pattern1, new_replacement1)
    
    old_pattern2 = '''        # Create a new session for this operation
        session_context = get_session()
        db_session = session_context.__enter__()
        return UserPreferencesService(db_session)'''
    
    new_replacement2 = '''        # Create a new session for this operation
        from src.data.database import get_session_sync
        db_session = get_session_sync()
        return UserPreferencesService(db_session)'''
    
    content = content.replace(old_pattern2, new_replacement2)
    
    # Also fix the imports at the top
    content = content.replace(
        'from src.data.database import get_session',
        'from src.data.database import get_session_sync'
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed session management in {file_path}")

if __name__ == "__main__":
    fix_session_management()
    print("Session management fixes applied successfully!")