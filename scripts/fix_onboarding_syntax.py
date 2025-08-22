#!/usr/bin/env python3
"""
Script to fix the syntax error in onboarding.py
"""

def fix_onboarding_syntax():
    """Fix the indentation syntax error in the collect_personalization_data method."""
    file_path = "src/logic/onboarding.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the indentation issue - the except block was incorrectly indented
    # Look for the specific pattern and fix it
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        # Find the line with the incorrect except indentation
        if line.strip() == "except Exception as e:" and i > 0:
            # Check if the previous line suggests this should be at the method level
            prev_line = lines[i-1].strip()
            if prev_line.endswith('data_type: {data_type}")'):
                # This is the problematic except block - fix its indentation
                lines[i] = "        except Exception as e:"
                # Also fix the following lines
                if i+1 < len(lines) and lines[i+1].strip().startswith("logger.exception"):
                    lines[i+1] = "            logger.exception(f\"Error collecting personalization data for user {user_id}: {e}\")"
                if i+2 < len(lines) and lines[i+2].strip().startswith("# Don't raise"):
                    lines[i+2] = "            # Don't raise - make this non-blocking for onboarding flow"
                if i+3 < len(lines) and lines[i+3].strip().startswith("logger.warning"):
                    lines[i+3] = "            logger.warning(f\"Continuing onboarding despite preferences save failure for user {user_id}\")"
                break
    
    content = '\n'.join(lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed syntax error in {file_path}")

if __name__ == "__main__":
    fix_onboarding_syntax()
    print("Onboarding syntax error fixed successfully!")