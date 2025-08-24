"""
Admin convenience functions for database management.
Provides easy-to-use functions for database initialization and reset operations.
"""

import logging
from typing import Any

from src.data.database import get_session
from src.logic.admin_logic import AdminLogic, InitializationResult, ResetResult
from src.services.admin_service import AdminService

logger = logging.getLogger(__name__)


def init_all_db() -> InitializationResult:
    """
    Initialize all database tables exactly once.
    
    This function creates all required tables for the study participation system:
    - pseudonyms
    - study_consent_records  
    - study_survey_responses
    - chat_messages
    - study_pald_data
    - generated_images
    - feedback_records
    - interaction_logs
    - pseudonym_mappings
    
    Returns:
        InitializationResult with operation details
    """
    try:
        # Initialize admin logic with database manager
        admin_logic = AdminLogic(db_manager)
        
        # Perform database initialization
        result = admin_logic.initialize_database_schema()
        
        if result.success:
            logger.info(f"Database initialization completed successfully. Created tables: {result.tables_created}")
        else:
            logger.error(f"Database initialization failed. Errors: {result.errors}")
            
        return result
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return InitializationResult(
            success=False,
            tables_created=[],
            errors=[str(e)],
            timestamp=result.timestamp if 'result' in locals() else None
        )


def reset_all_study_data() -> ResetResult:
    """
    Reset all study data by dropping and recreating all tables.
    
    WARNING: This function will permanently delete ALL data in the database!
    Use only for clean experiments or testing environments.
    
    Returns:
        ResetResult with operation details
    """
    try:
        # Initialize admin logic with database manager
        admin_logic = AdminLogic(db_manager)
        
        # Perform database reset
        result = admin_logic.reset_all_study_data()
        
        if result.success:
            logger.warning(f"Database reset completed. Dropped: {result.tables_dropped}, Recreated: {result.tables_recreated}")
        else:
            logger.error(f"Database reset failed. Errors: {result.errors}")
            
        return result
        
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        return ResetResult(
            success=False,
            tables_dropped=[],
            tables_recreated=[],
            errors=[str(e)],
            timestamp=result.timestamp if 'result' in locals() else None
        )


def validate_database_integrity() -> dict[str, Any]:
    """
    Validate database integrity and foreign key constraints.
    
    Returns:
        Dictionary with validation results
    """
    try:
        admin_logic = AdminLogic(db_manager)
        result = admin_logic.validate_database_integrity()
        
        return {
            "success": result.success,
            "constraint_violations": result.constraint_violations,
            "missing_tables": result.missing_tables,
            "errors": result.errors,
            "timestamp": result.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return {
            "success": False,
            "constraint_violations": [],
            "missing_tables": [],
            "errors": [str(e)],
            "timestamp": None
        }


def get_database_stats() -> dict[str, Any]:
    """
    Get comprehensive database statistics.
    
    Returns:
        Dictionary with database statistics
    """
    try:
        admin_logic = AdminLogic(db_manager)
        stats = admin_logic.get_database_statistics()
        
        # Add additional metadata
        stats["database_initialized"] = db_manager._initialized
        stats["timestamp"] = logger.info("Retrieved database statistics")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database statistics: {e}")
        return {"error": str(e)}


def export_all_study_data(output_path: str) -> dict[str, Any]:
    """
    Export all study data to a JSON file.
    
    Args:
        output_path: Path where to save the exported data
        
    Returns:
        Dictionary with export results
    """
    try:
        with get_session() as session:
            admin_service = AdminService(session)
            result = admin_service.export_study_data_to_file(output_path)
            
            if result["success"]:
                logger.info(f"Study data exported successfully to {output_path}")
            else:
                logger.error(f"Study data export failed: {result['errors']}")
                
            return result
            
    except Exception as e:
        logger.error(f"Failed to export study data: {e}")
        return {
            "success": False,
            "file_path": None,
            "records_exported": {},
            "errors": [str(e)],
            "timestamp": None
        }


def cleanup_orphaned_data() -> dict[str, int]:
    """
    Clean up orphaned records in the database.
    
    Returns:
        Dictionary with cleanup statistics
    """
    try:
        with get_session() as session:
            admin_service = AdminService(session)
            cleanup_counts = admin_service.cleanup_orphaned_records()
            
            total_cleaned = sum(v for k, v in cleanup_counts.items() if k != "error")
            if total_cleaned > 0:
                logger.info(f"Cleaned up {total_cleaned} orphaned records")
            else:
                logger.info("No orphaned records found")
                
            return cleanup_counts
            
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned data: {e}")
        return {"error": str(e)}


def delete_participant_data(pseudonym_id: str) -> bool:
    """
    Delete all data for a specific participant (for GDPR compliance).
    
    Args:
        pseudonym_id: The pseudonym ID to delete data for
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        from uuid import UUID
        
        # Convert string to UUID
        pseudonym_uuid = UUID(pseudonym_id)
        
        admin_logic = AdminLogic(db_manager)
        success = admin_logic.delete_participant_data(pseudonym_uuid)
        
        if success:
            logger.info(f"Successfully deleted all data for participant {pseudonym_id}")
        else:
            logger.error(f"Failed to delete data for participant {pseudonym_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Failed to delete participant data: {e}")
        return False


# Convenience aliases for backward compatibility
initialize_database = init_all_db
reset_database = reset_all_study_data