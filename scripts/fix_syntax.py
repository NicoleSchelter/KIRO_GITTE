#!/usr/bin/env python3
"""
Script to fix the syntax error in onboarding.py
"""

def fix_syntax_error():
    """Fix the indentation syntax error in the collect_personalization_data method."""
    file_path = "src/logic/onboarding.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the indentation issue - the except block was incorrectly indented
    old_pattern = '''            if success:
                logger.info(f"Collected personalization data for user {user_id}: {data_type}")
            else:
                logger.warning(f"Failed to save preferences for user {user_id}, data_type: {data_type}")

            except Exception as e:
            logger.exception(f"Error collecting personalization data for user {user_id}: {e}")
            # Don't raise - make this non-blocking for onboarding flow
            logger.warning(f"Continuing onboarding despite preferences save failure for user {user_id}")'''
    
    new_replacement = '''            if success:
                logger.info(f"Collected personalization data for user {user_id}: {data_type}")
            else:
                logger.warning(f"Failed to save preferences for user {user_id}, data_type: {data_type}")

        except Exception as e:
            logger.exception(f"Error collecting personalization data for user {user_id}: {e}")
            # Don't raise - make this non-blocking for onboarding flow
            logger.warning(f"Continuing onboarding despite preferences save failure for user {user_id}")'''
    
    content = content.replace(old_pattern, new_replacement)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed syntax error in {file_path}")

if __name__ == "__main__":
    fix_syntax_error()
    print("Syntax error fixed successfully!")