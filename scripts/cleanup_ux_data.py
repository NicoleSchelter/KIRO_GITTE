#!/usr/bin/env python3
"""
Data retention and cleanup script for UX enhancement data.
Cleans up old prerequisite check results, tooltip interactions, and UX audit logs.
"""

import argparse
import logging
from datetime import datetime, timedelta

from src.data.database import get_session_sync
from src.data.repositories import (
    PrerequisiteCheckResultRepository,
    TooltipInteractionRepository,
    UXAuditLogRepository,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_prerequisite_results(days_to_keep: int = 30, dry_run: bool = False) -> int:
    """
    Clean up old prerequisite check results.
    
    Args:
        days_to_keep: Number of days to keep results
        dry_run: If True, only count records without deleting
        
    Returns:
        Number of records that would be/were deleted
    """
    session = get_session_sync()
    repo = PrerequisiteCheckResultRepository(session)
    
    try:
        if dry_run:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            count = session.query(repo.model_class).filter(
                repo.model_class.created_at < cutoff_date
            ).count()
            logger.info(f"Would delete {count} prerequisite check results older than {days_to_keep} days")
            return count
        else:
            deleted_count = repo.cleanup_old_results(days_to_keep)
            session.commit()
            logger.info(f"Deleted {deleted_count} prerequisite check results older than {days_to_keep} days")
            return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up prerequisite results: {e}")
        session.rollback()
        return 0
    finally:
        session.close()


def cleanup_tooltip_interactions(days_to_keep: int = 180, dry_run: bool = False) -> int:
    """
    Clean up old tooltip interactions.
    
    Args:
        days_to_keep: Number of days to keep interactions
        dry_run: If True, only count records without deleting
        
    Returns:
        Number of records that would be/were deleted
    """
    session = get_session_sync()
    repo = TooltipInteractionRepository(session)
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        if dry_run:
            count = session.query(repo.model_class).filter(
                repo.model_class.created_at < cutoff_date
            ).count()
            logger.info(f"Would delete {count} tooltip interactions older than {days_to_keep} days")
            return count
        else:
            deleted_count = session.query(repo.model_class).filter(
                repo.model_class.created_at < cutoff_date
            ).delete()
            session.commit()
            logger.info(f"Deleted {deleted_count} tooltip interactions older than {days_to_keep} days")
            return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up tooltip interactions: {e}")
        session.rollback()
        return 0
    finally:
        session.close()


def cleanup_ux_audit_logs(days_to_keep: int = 90, dry_run: bool = False) -> int:
    """
    Clean up old UX audit logs.
    
    Args:
        days_to_keep: Number of days to keep logs
        dry_run: If True, only count records without deleting
        
    Returns:
        Number of records that would be/were deleted
    """
    session = get_session_sync()
    repo = UXAuditLogRepository(session)
    
    try:
        if dry_run:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            count = session.query(repo.model_class).filter(
                repo.model_class.created_at < cutoff_date
            ).count()
            logger.info(f"Would delete {count} UX audit logs older than {days_to_keep} days")
            return count
        else:
            deleted_count = repo.cleanup_old_logs(days_to_keep)
            session.commit()
            logger.info(f"Deleted {deleted_count} UX audit logs older than {days_to_keep} days")
            return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up UX audit logs: {e}")
        session.rollback()
        return 0
    finally:
        session.close()


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description="Clean up old UX enhancement data")
    parser.add_argument(
        "--prerequisite-days", 
        type=int, 
        default=30,
        help="Days to keep prerequisite check results (default: 30)"
    )
    parser.add_argument(
        "--tooltip-days", 
        type=int, 
        default=180,
        help="Days to keep tooltip interactions (default: 180)"
    )
    parser.add_argument(
        "--audit-days", 
        type=int, 
        default=90,
        help="Days to keep UX audit logs (default: 90)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--skip-prerequisite", 
        action="store_true",
        help="Skip prerequisite check results cleanup"
    )
    parser.add_argument(
        "--skip-tooltip", 
        action="store_true",
        help="Skip tooltip interactions cleanup"
    )
    parser.add_argument(
        "--skip-audit", 
        action="store_true",
        help="Skip UX audit logs cleanup"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting UX data cleanup...")
    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be deleted")
    
    total_deleted = 0
    
    # Clean up prerequisite check results
    if not args.skip_prerequisite:
        logger.info("Cleaning up prerequisite check results...")
        deleted = cleanup_prerequisite_results(args.prerequisite_days, args.dry_run)
        total_deleted += deleted
    
    # Clean up tooltip interactions
    if not args.skip_tooltip:
        logger.info("Cleaning up tooltip interactions...")
        deleted = cleanup_tooltip_interactions(args.tooltip_days, args.dry_run)
        total_deleted += deleted
    
    # Clean up UX audit logs
    if not args.skip_audit:
        logger.info("Cleaning up UX audit logs...")
        deleted = cleanup_ux_audit_logs(args.audit_days, args.dry_run)
        total_deleted += deleted
    
    if args.dry_run:
        logger.info(f"Cleanup complete. Would delete {total_deleted} total records.")
    else:
        logger.info(f"Cleanup complete. Deleted {total_deleted} total records.")


if __name__ == "__main__":
    main()