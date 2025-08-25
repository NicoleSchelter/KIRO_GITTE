#!/usr/bin/env python3
"""
Script to create an admin user for GITTE system.
Run this script to create an admin account that can access the admin UI.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from src.data.database_factory import initialize_database, get_session_sync
from src.data.models import User, UserRole
from src.data.repositories import UserRepository
from src.security.encryption import hash_password

def create_admin_user(username: str, password: str) -> None:
    """Create an admin user account."""
    try:
        # Initialize database
        initialize_database()
        
        # Get database session
        session = get_session_sync()
        
        # Create user repository
        user_repo = UserRepository(session)
        
        # Check if user already exists
        existing_user = user_repo.get_by_username(username)
        if existing_user:
            print(f"User '{username}' already exists.")
            if existing_user.role == UserRole.ADMIN.value:
                print("User is already an admin.")
            else:
                # Update user to admin role
                existing_user.role = UserRole.ADMIN.value
                session.commit()
                print(f"Updated user '{username}' to admin role.")
            return
        
        # Create new admin user
        password_hash_data = hash_password(password)
        # For simplicity, we'll store the hash directly
        # In a real application, you'd want to store the hash, salt, and algorithm
        password_hash = password_hash_data["hash"]
        
        admin_user = User(
            username=username,
            password_hash=password_hash,
            role=UserRole.ADMIN.value,
            pseudonym=f"admin_{username}"  # Simple pseudonym for admin
        )
        
        session.add(admin_user)
        session.commit()
        
        print(f"Admin user '{username}' created successfully!")
        print("You can now log in with this account to access the admin UI.")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        sys.exit(1)
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    print("GITTE Admin User Creation Script")
    print("=" * 40)
    
    # Get username and password from user
    username = input("Enter admin username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)
    
    password = input("Enter admin password: ").strip()
    if not password:
        print("Password cannot be empty.")
        sys.exit(1)
    
    confirm_password = input("Confirm password: ").strip()
    if password != confirm_password:
        print("Passwords do not match.")
        sys.exit(1)
    
    create_admin_user(username, password)