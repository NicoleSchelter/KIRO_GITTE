#!/usr/bin/env python3
"""
Script to apply JSON serialization fixes to the codebase.
"""

import re

def fix_onboarding_logic():
    """Fix the onboarding logic to use upsert_preferences and make it non-blocking."""
    file_path = "src/logic/onboarding.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace save_preferences with upsert_preferences
    old_pattern = r'preferences_service\.save_preferences\(\s*user_id=user_id,\s*preferences=preferences_data,\s*category=f"onboarding_{data_type}"\s*\)'
    new_replacement = '''success = preferences_service.upsert_preferences(
                user_id=user_id,
                category=f"onboarding_{data_type}",
                prefs=preferences_data
            )
            
            if success:
                logger.info(f"Collected personalization data for user {user_id}: {data_type}")
            else:
                logger.warning(f"Failed to save preferences for user {user_id}, data_type: {data_type}")'''
    
    content = re.sub(old_pattern, new_replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Make the exception handling non-blocking
    old_exception = r'logger\.info\(f"Collected personalization data for user {user_id}: {data_type}"\)\s*except Exception as e:\s*logger\.error\(f"Error collecting personalization data for user {user_id}: {e}"\)\s*raise OnboardingError\(f"Failed to collect personalization data: {e}"\)'
    new_exception = '''except Exception as e:
            logger.exception(f"Error collecting personalization data for user {user_id}: {e}")
            # Don't raise - make this non-blocking for onboarding flow
            logger.warning(f"Continuing onboarding despite preferences save failure for user {user_id}")'''
    
    content = re.sub(old_exception, new_exception, content, flags=re.MULTILINE | re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")

if __name__ == "__main__":
    fix_onboarding_logic()
    print("JSON serialization fixes applied successfully!")