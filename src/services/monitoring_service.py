"""
System monitoring service for GITTE.
Provides comprehensive monitoring, health checks, and alerting functionality.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import psutil
import requests

from config.config import config
from src.data.database import get_session
from src.services.audit_service import get_audit_service

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Health check result."""

    service: str
    status: HealthStatus
    response_time_ms: float | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SystemMetrics:
    """System performance metrics."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: dict[str, int]
    active_connections: int
    response_times: dict[str, float]
    error_rates: dict[str, float]


@dataclass
class Alert:
    """System alert."""

    id: str
    level: AlertLevel
    service: str
    message: str
    details: dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    resolved_at: datetime | None = None


class MonitoringService:
    """Comprehensive system monitoring service."""

    def __init__(self):
        self.audit_service = get_audit_service()
        self.metrics_history: list[SystemMetrics] = []
        self.active_alerts: dict[str, Alert] = {}
        self.health_checks: dict[str, HealthCheck] = {}
        self._monitoring_active = False
        self._monitoring_thread: threading.Thread | None = None

        # Thresholds for alerts
        self.thresholds = {
            "cpu_warning": 80.0,
            "cpu_critical": 95.0,
            "memory_warning": 85.0,
            "memory_critical": 95.0,
            "disk_warning": 90.0,
            "disk_critical": 98.0,
            "response_time_warning": 5000.0,  # ms
            "response_time_critical": 10000.0,  # ms
            "error_rate_warning": 5.0,  # %
            "error_rate_critical": 10.0,  # %
        }

    def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start continuous monitoring."""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, args=(interval_seconds,), daemon=True
        )
        self._monitoring_thread.start()
        logger.info("System monitoring started")

    def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("System monitoring stopped")

    def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                # Collect metrics
                metrics = self.collect_system_metrics()
                self.metrics_history.append(metrics)

                # Keep only last 24 hours of metrics
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.metrics_history = [
                    m for m in self.metrics_history if m.timestamp > cutoff_time
                ]

                # Perform health checks
                self.perform_health_checks()

                # Check for alerts
                self.check_alerts(metrics)

                time.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval_seconds)

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            }

            # Active connections (approximate)
            connections = len(psutil.net_connections())

            # Response times from recent audit logs
            response_times = self._get_recent_response_times()

            # Error rates from recent audit logs
            error_rates = self._get_recent_error_rates()

            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk_percent,
                network_io=network_io,
                active_connections=connections,
                response_times=response_times,
                error_rates=error_rates,
            )

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_io={},
                active_connections=0,
                response_times={},
                error_rates={},
            )

    def perform_health_checks(self) -> dict[str, HealthCheck]:
        """Perform health checks on all services."""
        health_checks = {}

        # Database health check
        health_checks["database"] = self._check_database_health()

        # LLM service health check
        health_checks["llm_service"] = self._check_llm_health()

        # Image generation health check
        health_checks["image_generation"] = self._check_image_generation_health()

        # Storage health check
        health_checks["storage"] = self._check_storage_health()

        # Update stored health checks
        self.health_checks.update(health_checks)

        return health_checks

    def _check_database_health(self) -> HealthCheck:
        """Check database health."""
        start_time = time.time()

        try:
            with get_session() as db_session:
                db_session.execute("SELECT 1")
                response_time = (time.time() - start_time) * 1000

                return HealthCheck(
                    service="database",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message="Database connection successful",
                )

        except Exception as e:
            return HealthCheck(
                service="database",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {e}",
            )

    def _check_llm_health(self) -> HealthCheck:
        """Check LLM service health."""
        start_time = time.time()

        try:
            # Simple health check to Ollama
            response = requests.get(f"{config.llm.ollama_url}/api/tags", timeout=10)
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                models = response.json().get("models", [])
                return HealthCheck(
                    service="llm_service",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message=f"LLM service healthy, {len(models)} models available",
                    details={"models_count": len(models)},
                )
            else:
                return HealthCheck(
                    service="llm_service",
                    status=HealthStatus.WARNING,
                    response_time_ms=response_time,
                    message=f"LLM service returned status {response.status_code}",
                )

        except requests.exceptions.Timeout:
            return HealthCheck(
                service="llm_service", status=HealthStatus.WARNING, message="LLM service timeout"
            )
        except Exception as e:
            return HealthCheck(
                service="llm_service",
                status=HealthStatus.CRITICAL,
                message=f"LLM service check failed: {e}",
            )

    def _check_image_generation_health(self) -> HealthCheck:
        """Check image generation service health."""
        try:
            # Check if required packages are available
            import torch

            # Check GPU availability if configured
            if config.image_generation.device == "cuda":
                if torch.cuda.is_available():
                    gpu_count = torch.cuda.device_count()
                    return HealthCheck(
                        service="image_generation",
                        status=HealthStatus.HEALTHY,
                        message=f"Image generation ready with {gpu_count} GPU(s)",
                        details={"gpu_count": gpu_count, "device": "cuda"},
                    )
                else:
                    return HealthCheck(
                        service="image_generation",
                        status=HealthStatus.WARNING,
                        message="CUDA configured but not available, falling back to CPU",
                        details={"device": "cpu"},
                    )
            else:
                return HealthCheck(
                    service="image_generation",
                    status=HealthStatus.HEALTHY,
                    message="Image generation ready (CPU mode)",
                    details={"device": "cpu"},
                )

        except ImportError as e:
            return HealthCheck(
                service="image_generation",
                status=HealthStatus.CRITICAL,
                message=f"Image generation dependencies missing: {e}",
            )
        except Exception as e:
            return HealthCheck(
                service="image_generation",
                status=HealthStatus.WARNING,
                message=f"Image generation check failed: {e}",
            )

    def _check_storage_health(self) -> HealthCheck:
        """Check storage service health."""
        try:
            # Check local storage
            local_path = Path(config.storage.local_storage_path)
            if not local_path.exists():
                local_path.mkdir(parents=True, exist_ok=True)

            # Test write access
            test_file = local_path / ".health_check"
            test_file.write_text("health_check")
            test_file.unlink()

            details = {"local_storage": "healthy"}

            # Check MinIO if enabled
            if config.storage.use_minio:
                try:
                    from minio import Minio

                    client = Minio(
                        config.storage.minio_endpoint,
                        access_key=config.storage.minio_access_key,
                        secret_key=config.storage.minio_secret_key,
                        secure=False,
                    )

                    # Test connection
                    buckets = list(client.list_buckets())
                    details["minio"] = "healthy"
                    details["minio_buckets"] = len(buckets)

                except Exception as e:
                    details["minio"] = f"error: {e}"
                    return HealthCheck(
                        service="storage",
                        status=HealthStatus.WARNING,
                        message="Local storage healthy, MinIO unavailable",
                        details=details,
                    )

            return HealthCheck(
                service="storage",
                status=HealthStatus.HEALTHY,
                message="Storage services healthy",
                details=details,
            )

        except Exception as e:
            return HealthCheck(
                service="storage",
                status=HealthStatus.CRITICAL,
                message=f"Storage check failed: {e}",
            )

    def _get_recent_response_times(self) -> dict[str, float]:
        """Get recent response times from audit logs."""
        try:
            with get_session() as db_session:
                query = """
                SELECT operation, AVG(latency_ms) as avg_latency
                FROM audit_logs 
                WHERE created_at > NOW() - INTERVAL '1 hour'
                AND latency_ms IS NOT NULL
                GROUP BY operation
                """

                result = db_session.execute(query)
                response_times = {}

                for row in result:
                    response_times[row.operation] = float(row.avg_latency)

                return response_times

        except Exception as e:
            logger.error(f"Error getting response times: {e}")
            return {}

    def _get_recent_error_rates(self) -> dict[str, float]:
        """Get recent error rates from audit logs."""
        try:
            with get_session() as db_session:
                query = """
                SELECT 
                    operation,
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as errors
                FROM audit_logs 
                WHERE created_at > NOW() - INTERVAL '1 hour'
                GROUP BY operation
                """

                result = db_session.execute(query)
                error_rates = {}

                for row in result:
                    if row.total > 0:
                        error_rate = (row.errors / row.total) * 100
                        error_rates[row.operation] = error_rate

                return error_rates

        except Exception as e:
            logger.error(f"Error getting error rates: {e}")
            return {}

    def check_alerts(self, metrics: SystemMetrics) -> list[Alert]:
        """Check for alert conditions and generate alerts."""
        new_alerts = []

        # CPU alerts
        if metrics.cpu_percent > self.thresholds["cpu_critical"]:
            alert = self._create_alert(
                "cpu_critical",
                AlertLevel.CRITICAL,
                "system",
                f"Critical CPU usage: {metrics.cpu_percent:.1f}%",
                {"cpu_percent": metrics.cpu_percent},
            )
            new_alerts.append(alert)
        elif metrics.cpu_percent > self.thresholds["cpu_warning"]:
            alert = self._create_alert(
                "cpu_warning",
                AlertLevel.WARNING,
                "system",
                f"High CPU usage: {metrics.cpu_percent:.1f}%",
                {"cpu_percent": metrics.cpu_percent},
            )
            new_alerts.append(alert)

        # Memory alerts
        if metrics.memory_percent > self.thresholds["memory_critical"]:
            alert = self._create_alert(
                "memory_critical",
                AlertLevel.CRITICAL,
                "system",
                f"Critical memory usage: {metrics.memory_percent:.1f}%",
                {"memory_percent": metrics.memory_percent},
            )
            new_alerts.append(alert)
        elif metrics.memory_percent > self.thresholds["memory_warning"]:
            alert = self._create_alert(
                "memory_warning",
                AlertLevel.WARNING,
                "system",
                f"High memory usage: {metrics.memory_percent:.1f}%",
                {"memory_percent": metrics.memory_percent},
            )
            new_alerts.append(alert)

        # Disk alerts
        if metrics.disk_percent > self.thresholds["disk_critical"]:
            alert = self._create_alert(
                "disk_critical",
                AlertLevel.CRITICAL,
                "system",
                f"Critical disk usage: {metrics.disk_percent:.1f}%",
                {"disk_percent": metrics.disk_percent},
            )
            new_alerts.append(alert)
        elif metrics.disk_percent > self.thresholds["disk_warning"]:
            alert = self._create_alert(
                "disk_warning",
                AlertLevel.WARNING,
                "system",
                f"High disk usage: {metrics.disk_percent:.1f}%",
                {"disk_percent": metrics.disk_percent},
            )
            new_alerts.append(alert)

        # Response time alerts
        for operation, response_time in metrics.response_times.items():
            if response_time > self.thresholds["response_time_critical"]:
                alert = self._create_alert(
                    f"response_time_critical_{operation}",
                    AlertLevel.CRITICAL,
                    operation,
                    f"Critical response time for {operation}: {response_time:.0f}ms",
                    {"operation": operation, "response_time_ms": response_time},
                )
                new_alerts.append(alert)
            elif response_time > self.thresholds["response_time_warning"]:
                alert = self._create_alert(
                    f"response_time_warning_{operation}",
                    AlertLevel.WARNING,
                    operation,
                    f"High response time for {operation}: {response_time:.0f}ms",
                    {"operation": operation, "response_time_ms": response_time},
                )
                new_alerts.append(alert)

        # Error rate alerts
        for operation, error_rate in metrics.error_rates.items():
            if error_rate > self.thresholds["error_rate_critical"]:
                alert = self._create_alert(
                    f"error_rate_critical_{operation}",
                    AlertLevel.CRITICAL,
                    operation,
                    f"Critical error rate for {operation}: {error_rate:.1f}%",
                    {"operation": operation, "error_rate_percent": error_rate},
                )
                new_alerts.append(alert)
            elif error_rate > self.thresholds["error_rate_warning"]:
                alert = self._create_alert(
                    f"error_rate_warning_{operation}",
                    AlertLevel.WARNING,
                    operation,
                    f"High error rate for {operation}: {error_rate:.1f}%",
                    {"operation": operation, "error_rate_percent": error_rate},
                )
                new_alerts.append(alert)

        # Add new alerts to active alerts
        for alert in new_alerts:
            self.active_alerts[alert.id] = alert

        return new_alerts

    def _create_alert(
        self, alert_id: str, level: AlertLevel, service: str, message: str, details: dict[str, Any]
    ) -> Alert:
        """Create a new alert."""
        return Alert(
            id=alert_id,
            level=level,
            service=service,
            message=message,
            details=details,
            timestamp=datetime.now(),
        )

    def get_system_status(self) -> dict[str, Any]:
        """Get overall system status."""
        health_checks = self.perform_health_checks()

        # Determine overall status
        statuses = [check.status for check in health_checks.values()]

        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        elif HealthStatus.HEALTHY in statuses:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN

        # Get latest metrics
        latest_metrics = self.metrics_history[-1] if self.metrics_history else None

        return {
            "overall_status": overall_status.value,
            "health_checks": {
                name: {
                    "status": check.status.value,
                    "response_time_ms": check.response_time_ms,
                    "message": check.message,
                    "details": check.details,
                    "timestamp": check.timestamp.isoformat(),
                }
                for name, check in health_checks.items()
            },
            "metrics": {
                "cpu_percent": latest_metrics.cpu_percent if latest_metrics else 0,
                "memory_percent": latest_metrics.memory_percent if latest_metrics else 0,
                "disk_percent": latest_metrics.disk_percent if latest_metrics else 0,
                "active_connections": latest_metrics.active_connections if latest_metrics else 0,
                "timestamp": latest_metrics.timestamp.isoformat() if latest_metrics else None,
            },
            "active_alerts": len([a for a in self.active_alerts.values() if not a.resolved]),
            "uptime_hours": self._get_uptime_hours(),
        }

    def get_metrics_history(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get metrics history for the specified number of hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        filtered_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]

        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "disk_percent": m.disk_percent,
                "active_connections": m.active_connections,
                "response_times": m.response_times,
                "error_rates": m.error_rates,
            }
            for m in filtered_metrics
        ]

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get all active (unresolved) alerts."""
        active_alerts = [alert for alert in self.active_alerts.values() if not alert.resolved]

        return [
            {
                "id": alert.id,
                "level": alert.level.value,
                "service": alert.service,
                "message": alert.message,
                "details": alert.details,
                "timestamp": alert.timestamp.isoformat(),
            }
            for alert in active_alerts
        ]

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            return True
        return False

    def _get_uptime_hours(self) -> float:
        """Get system uptime in hours."""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            return uptime_seconds / 3600
        except:
            return 0.0


# Global monitoring service instance
_monitoring_service: MonitoringService | None = None


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
