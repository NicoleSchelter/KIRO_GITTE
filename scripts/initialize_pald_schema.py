"""
Initialize PALD schema in the database.
Creates the default PALD schema version if it doesn't exist.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.data.database import get_session, initialize_database
from src.data.models import PALDSchemaVersion
from src.services.pald_service import PALDSchemaService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_pald_schema():
    """Initialize the default PALD schema in the database."""
    # Initialize database connection
    initialize_database()

    with get_session() as session:
        # Check if any schema version exists
        existing_schema = session.query(PALDSchemaVersion).first()

        if existing_schema:
            logger.info("PALD schema already exists, skipping initialization")
            return

        # Create schema service and initialize default schema
        schema_service = PALDSchemaService(session)

        # This will create the default schema if none exists
        version, schema_content = schema_service.get_current_schema()

        logger.info(f"Initialized PALD schema version {version}")


if __name__ == "__main__":
    initialize_pald_schema()
