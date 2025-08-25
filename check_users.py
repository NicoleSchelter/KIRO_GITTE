#!/usr/bin/env python3
"""
Script to check database and users.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from src.data.database_factory import get_session_sync
from src.data.models import User

def check_users():
    """Check database and users."""
    try:
        # Get database session
        session = get_session_sync()
        
        # Get all users
        users = session.query(User).all()
        print(f"Found {len(users)} users")
        
        for user in users:
            print(f"  - {user.username} ({user.role})")
        
        session.close()
        
    except Exception as e:
        print(f"Error checking users: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_users()