#!/usr/bin/env python3
"""
Script to fix the import typo in onboarding.py
"""

def fix_import_typo():
    """Fix the get_session_sync_sync typo."""
    file_path = "src/logic/onboarding.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the typo
    content = content.replace('get_session_sync_sync', 'get_session_sync')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed import typo in {file_path}")

if __name__ == "__main__":
    fix_import_typo()
    print("Import typo fixed successfully!")