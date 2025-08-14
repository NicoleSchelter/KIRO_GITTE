#!/usr/bin/env python3
"""
Rollback procedures for GITTE UX enhancements deployment.
Provides safe rollback mechanisms in case of deployment issues.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2
import redis

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages rollback procedures for GITTE UX enhancements."""
    
    def __init__(self, backup_dir: str = "./backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.rollback_log = []
    
    def log_action(self, action: str, success: bool, message: str = "", details: Dict = None):
        """Log rollback action."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.rollback_log.append(entry)
        
        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILED"
        logger.log(level, f"[{status}] {action}: {message}")
    
    def create_backup(self) -> bool:
        """Create a complete backup before rollback."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"pre_rollback_{timestamp}"
            backup_path.mkdir(exist_ok=True)
            
            # Backup configuration files
            config_files = [
                "docker-compose.yml",
                "docker-compose.prod.yml",
                ".env",
                "config/",
                "docs/"
            ]
            
            for config_file in config_files:
                if os.path.exists(config_file):
                    if os.path.isdir(config_file):
                        shutil.copytree(config_file, backup_path / config_file, dirs_exist_ok=True)
                    else:
                        shutil.copy2(config_file, backup_path / config_file)
            
            # Backup database
            self._backup_database(backup_path)
            
            # Backup Redis data
            self._backup_redis(backup_path)
            
            # Backup application logs
            self._backup_logs(backup_path)
            
            self.log_action(
                "create_backup",
                True,
                f"Backup created successfully at {backup_path}"
            )
            return True
            
        except Exception as e:
            self.log_action(
                "create_backup",
                False,
                f"Failed to create backup: {str(e)}"
            )
            return False
    
    def _backup_database(self, backup_path: Path):
        """Backup PostgreSQL database."""
        try:
            postgres_dsn = os.getenv("POSTGRES_DSN", "postgresql://gitte:password@localhost:5432/data_collector")
            
            # Extract connection parameters
            import urllib.parse
            parsed = urllib.parse.urlparse(postgres_dsn)
            
            db_backup_file = backup_path / "database_backup.sql"
            
            # Use pg_dump to create backup
            cmd = [
                "pg_dump",
                "-h", parsed.hostname or "localhost",
                "-p", str(parsed.port or 5432),
                "-U", parsed.username or "gitte",
                "-d", parsed.path.lstrip('/') or "data_collector",
                "-f", str(db_backup_file),
                "--verbose"
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password or "password"
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Database backup completed successfully")
            else:
                logger.warning(f"Database backup failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Database backup error: {str(e)}")
    
    def _backup_redis(self, backup_path: Path):
        """Backup Redis data."""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            
            # Get all keys and their values
            redis_backup = {}
            for key in r.scan_iter():
                key_str = key.decode() if isinstance(key, bytes) else key
                value = r.get(key)
                if value:
                    redis_backup[key_str] = value.decode() if isinstance(value, bytes) else value
            
            # Save to file
            redis_backup_file = backup_path / "redis_backup.json"
            with open(redis_backup_file, 'w') as f:
                json.dump(redis_backup, f, indent=2)
            
            logger.info("Redis backup completed successfully")
            
        except Exception as e:
            logger.error(f"Redis backup error: {str(e)}")
    
    def _backup_logs(self, backup_path: Path):
        """Backup application logs."""
        try:
            log_dirs = ["logs/", "/var/log/gitte/"]
            
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    shutil.copytree(log_dir, backup_path / "logs", dirs_exist_ok=True)
                    break
            
            logger.info("Logs backup completed successfully")
            
        except Exception as e:
            logger.error(f"Logs backup error: {str(e)}")
    
    def rollback_docker_services(self) -> bool:
        """Rollback Docker services to previous version."""
        try:
            # Stop current services
            logger.info("Stopping current Docker services...")
            result = subprocess.run(
                ["docker-compose", "down"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.log_action(
                    "stop_services",
                    False,
                    f"Failed to stop services: {result.stderr}"
                )
                return False
            
            # Remove UX enhancement containers and images
            ux_containers = [
                "gitte-app",
                "redis"
            ]
            
            for container in ux_containers:
                subprocess.run(
                    ["docker", "rm", "-f", container],
                    capture_output=True
                )
            
            # Remove UX enhancement images
            subprocess.run(
                ["docker", "rmi", "-f", "gitte_gitte-app:latest"],
                capture_output=True
            )
            
            self.log_action(
                "rollback_docker_services",
                True,
                "Docker services rolled back successfully"
            )
            return True
            
        except Exception as e:
            self.log_action(
                "rollback_docker_services",
                False,
                f"Failed to rollback Docker services: {str(e)}"
            )
            return False
    
    def rollback_configuration(self) -> bool:
        """Rollback configuration files to previous version."""
        try:
            # Find the most recent backup
            backups = sorted([d for d in self.backup_dir.iterdir() if d.is_dir()], reverse=True)
            
            if not backups:
                self.log_action(
                    "rollback_configuration",
                    False,
                    "No configuration backups found"
                )
                return False
            
            latest_backup = backups[0]
            logger.info(f"Rolling back configuration from {latest_backup}")
            
            # Restore configuration files
            config_files = [
                "docker-compose.yml",
                "docker-compose.prod.yml",
                ".env"
            ]
            
            for config_file in config_files:
                backup_file = latest_backup / config_file
                if backup_file.exists():
                    shutil.copy2(backup_file, config_file)
                    logger.info(f"Restored {config_file}")
            
            # Restore config directory
            config_backup = latest_backup / "config"
            if config_backup.exists():
                if os.path.exists("config"):
                    shutil.rmtree("config")
                shutil.copytree(config_backup, "config")
                logger.info("Restored config directory")
            
            self.log_action(
                "rollback_configuration",
                True,
                "Configuration rolled back successfully"
            )
            return True
            
        except Exception as e:
            self.log_action(
                "rollback_configuration",
                False,
                f"Failed to rollback configuration: {str(e)}"
            )
            return False
    
    def rollback_database_schema(self) -> bool:
        """Rollback database schema changes."""
        try:
            postgres_dsn = os.getenv("POSTGRES_DSN", "postgresql://gitte:password@localhost:5432/data_collector")
            
            # Connect to database
            conn = psycopg2.connect(postgres_dsn)
            cursor = conn.cursor()
            
            # Get list of UX enhancement migrations to rollback
            ux_migrations = [
                "add_ux_enhancements_schema",
                "add_image_correction_tables",
                "add_tooltip_interaction_tables",
                "add_prerequisite_validation_tables",
                "add_performance_monitoring_tables"
            ]
            
            # Rollback migrations in reverse order
            for migration in reversed(ux_migrations):
                try:
                    # Check if migration exists
                    cursor.execute(
                        "SELECT version_num FROM alembic_version WHERE version_num LIKE %s",
                        (f"%{migration}%",)
                    )
                    
                    if cursor.fetchone():
                        # Run Alembic downgrade
                        result = subprocess.run(
                            ["alembic", "downgrade", "-1"],
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode == 0:
                            logger.info(f"Rolled back migration: {migration}")
                        else:
                            logger.warning(f"Failed to rollback migration {migration}: {result.stderr}")
                
                except Exception as e:
                    logger.warning(f"Error rolling back migration {migration}: {str(e)}")
            
            cursor.close()
            conn.close()
            
            self.log_action(
                "rollback_database_schema",
                True,
                "Database schema rolled back successfully"
            )
            return True
            
        except Exception as e:
            self.log_action(
                "rollback_database_schema",
                False,
                f"Failed to rollback database schema: {str(e)}"
            )
            return False
    
    def cleanup_ux_data(self) -> bool:
        """Clean up UX enhancement data from database."""
        try:
            postgres_dsn = os.getenv("POSTGRES_DSN", "postgresql://gitte:password@localhost:5432/data_collector")
            
            conn = psycopg2.connect(postgres_dsn)
            cursor = conn.cursor()
            
            # Tables to clean up (in dependency order)
            cleanup_tables = [
                "tooltip_interactions",
                "prerequisite_validation_results",
                "image_correction_results",
                "performance_metrics",
                "ux_user_preferences"
            ]
            
            for table in cleanup_tables:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    deleted_count = cursor.rowcount
                    logger.info(f"Cleaned up {deleted_count} records from {table}")
                except psycopg2.Error as e:
                    if "does not exist" not in str(e):
                        logger.warning(f"Error cleaning up table {table}: {str(e)}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_action(
                "cleanup_ux_data",
                True,
                "UX enhancement data cleaned up successfully"
            )
            return True
            
        except Exception as e:
            self.log_action(
                "cleanup_ux_data",
                False,
                f"Failed to cleanup UX data: {str(e)}"
            )
            return False
    
    def clear_redis_cache(self) -> bool:
        """Clear Redis cache data."""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            
            # Clear UX enhancement related keys
            ux_patterns = [
                "tooltip:*",
                "prerequisite:*",
                "image_correction:*",
                "performance:*",
                "accessibility:*"
            ]
            
            total_deleted = 0
            for pattern in ux_patterns:
                keys = r.keys(pattern)
                if keys:
                    deleted = r.delete(*keys)
                    total_deleted += deleted
                    logger.info(f"Deleted {deleted} keys matching pattern {pattern}")
            
            self.log_action(
                "clear_redis_cache",
                True,
                f"Cleared {total_deleted} cache entries"
            )
            return True
            
        except Exception as e:
            self.log_action(
                "clear_redis_cache",
                False,
                f"Failed to clear Redis cache: {str(e)}"
            )
            return False
    
    def restart_services(self) -> bool:
        """Restart services after rollback."""
        try:
            logger.info("Starting services after rollback...")
            
            # Start services
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.log_action(
                    "restart_services",
                    False,
                    f"Failed to start services: {result.stderr}"
                )
                return False
            
            # Wait for services to be ready
            time.sleep(30)
            
            # Check service health
            health_check = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True,
                text=True
            )
            
            if "Up" in health_check.stdout:
                self.log_action(
                    "restart_services",
                    True,
                    "Services restarted successfully"
                )
                return True
            else:
                self.log_action(
                    "restart_services",
                    False,
                    "Services failed to start properly"
                )
                return False
            
        except Exception as e:
            self.log_action(
                "restart_services",
                False,
                f"Failed to restart services: {str(e)}"
            )
            return False
    
    def validate_rollback(self) -> bool:
        """Validate that rollback was successful."""
        try:
            # Run basic connectivity tests
            import requests
            
            # Test basic application health
            try:
                response = requests.get("http://localhost:8501/health", timeout=10)
                if response.status_code == 200:
                    logger.info("Application health check passed")
                else:
                    logger.warning(f"Application health check failed: {response.status_code}")
                    return False
            except requests.RequestException as e:
                logger.error(f"Application health check failed: {str(e)}")
                return False
            
            # Test that UX enhancement endpoints are no longer available
            ux_endpoints = [
                "/ux/image-correction",
                "/ux/tooltips",
                "/ux/prerequisites",
                "/ux/accessibility"
            ]
            
            for endpoint in ux_endpoints:
                try:
                    response = requests.get(f"http://localhost:8501{endpoint}", timeout=5)
                    if response.status_code == 404:
                        logger.info(f"UX endpoint {endpoint} properly removed")
                    else:
                        logger.warning(f"UX endpoint {endpoint} still accessible")
                except requests.RequestException:
                    logger.info(f"UX endpoint {endpoint} properly removed")
            
            self.log_action(
                "validate_rollback",
                True,
                "Rollback validation completed successfully"
            )
            return True
            
        except Exception as e:
            self.log_action(
                "validate_rollback",
                False,
                f"Rollback validation failed: {str(e)}"
            )
            return False
    
    def full_rollback(self) -> bool:
        """Perform complete rollback of UX enhancements."""
        logger.info("Starting full rollback of GITTE UX enhancements...")
        
        # Create backup before rollback
        if not self.create_backup():
            logger.error("Failed to create backup before rollback. Aborting.")
            return False
        
        rollback_steps = [
            ("Stop Docker services", self.rollback_docker_services),
            ("Rollback configuration", self.rollback_configuration),
            ("Rollback database schema", self.rollback_database_schema),
            ("Cleanup UX data", self.cleanup_ux_data),
            ("Clear Redis cache", self.clear_redis_cache),
            ("Restart services", self.restart_services),
            ("Validate rollback", self.validate_rollback)
        ]
        
        failed_steps = []
        
        for step_name, step_func in rollback_steps:
            logger.info(f"Executing rollback step: {step_name}")
            
            try:
                if not step_func():
                    failed_steps.append(step_name)
                    logger.error(f"Rollback step failed: {step_name}")
                else:
                    logger.info(f"Rollback step completed: {step_name}")
            except Exception as e:
                failed_steps.append(step_name)
                logger.error(f"Rollback step failed with exception: {step_name} - {str(e)}")
        
        # Generate rollback report
        self._generate_rollback_report(failed_steps)
        
        if not failed_steps:
            logger.info("Full rollback completed successfully!")
            return True
        else:
            logger.error(f"Rollback completed with {len(failed_steps)} failed steps: {failed_steps}")
            return False
    
    def _generate_rollback_report(self, failed_steps: List[str]):
        """Generate rollback report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.backup_dir / f"rollback_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "rollback_success": len(failed_steps) == 0,
            "failed_steps": failed_steps,
            "detailed_log": self.rollback_log
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Rollback report generated: {report_file}")


def main():
    """Main function for rollback procedures."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GITTE UX Enhancements Rollback Procedures")
    parser.add_argument(
        "--action",
        choices=["full", "config", "database", "services", "cache", "validate"],
        default="full",
        help="Rollback action to perform"
    )
    parser.add_argument(
        "--backup-dir",
        default="./backups",
        help="Directory for backups"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rollback without confirmation"
    )
    
    args = parser.parse_args()
    
    if not args.force:
        print("WARNING: This will rollback GITTE UX enhancements and may cause data loss.")
        confirmation = input("Are you sure you want to proceed? (yes/no): ")
        if confirmation.lower() != "yes":
            print("Rollback cancelled.")
            sys.exit(0)
    
    rollback_manager = RollbackManager(args.backup_dir)
    
    success = False
    
    if args.action == "full":
        success = rollback_manager.full_rollback()
    elif args.action == "config":
        success = rollback_manager.rollback_configuration()
    elif args.action == "database":
        success = rollback_manager.rollback_database_schema()
    elif args.action == "services":
        success = rollback_manager.rollback_docker_services()
    elif args.action == "cache":
        success = rollback_manager.clear_redis_cache()
    elif args.action == "validate":
        success = rollback_manager.validate_rollback()
    
    if success:
        print(f"Rollback action '{args.action}' completed successfully!")
        sys.exit(0)
    else:
        print(f"Rollback action '{args.action}' failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()