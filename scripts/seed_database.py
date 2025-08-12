#!/usr/bin/env python3
"""
Database seeding script for GITTE.
Creates initial data for development and testing.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import config


def seed_database():
    """Seed the database with initial data."""
    print("🌱 Seeding database...")
    print(f"Environment: {config.environment}")
    print(f"Database: {config.database.dsn}")

    # TODO: Implement actual seeding logic in later tasks
    # This will include:
    # - Creating initial admin user
    # - Setting up PALD schema versions
    # - Creating sample consent templates

    print("✅ Database seeding completed (placeholder)")


if __name__ == "__main__":
    seed_database()
