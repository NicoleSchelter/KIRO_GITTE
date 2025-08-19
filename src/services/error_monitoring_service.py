"""Error Monitoring Service for GITTE UX enhancements.
Provides error monitoring, alerting, resource & processing health checks,
and a unified API compatible with existing call sites.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

# External / project utilities
from src.utils.circuit_breaker import get_all_circuit_breaker_stats, get_unhealthy_services
from src.utils.error_handler import get_error_stats, get_recent_errors
from src.utils.ux_error_handler import get_ux_error_stats

# Optional metrics (no-op fallback if not present)
try:
    from src.monitoring.metrics import MetricsCollector  # created elsewhere in your patch set
except Exception:  # pragma: no cover
    class MetricsCollector:  # type: ignore
        def increment_counter(self, *_args, **_kw): ...
        def gauge(self, *_args, **_kw): ...
        def observe_histogram(self, *_args, **_kw): ...

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """System alert information."""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    component: str
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Discrete health check result."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: float
    details: Optional[Dict[str, Any]] = None


@dataclass
class HealthMetrics:
    """Aggregated health metrics snapshot."""
    overall_health: float  # 0.0 to 1.0
    error_rate: float
    circuit_breaker_health: float
    resource_health: float
    processing_health: float
    timestamp: datetime
    alerts_count: int
    critical_alerts_count: int


@dataclass
class MonitoringConfig:
    """Configuration for error monitoring."""
    # Error rate / windowing
    error_rate_threshold: float = 0.1  # 10%
    critical_error_threshold: int = 5
    monitoring_window_minutes: int = 15
    alert_cooldown_minutes: int = 5
    max_alerts_stored: int = 100

    # Subsystems to include
    enable_resource_monitoring: bool = True
    enable_circuit_breaker_monitoring: bool = True

    # Resource thresholds (fractional)
    memory_threshold: float = 0.85   # 85% used => degraded/unhealthy
    disk_threshold: float = 0.90     # 90% used => unhealthy
    cpu_threshold: float = 0.95      # 95% used => unhealthy


class ErrorMonitoringService:
    """Service for monitoring system errors and overall health."""

    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.alerts: Deque[Alert] = deque(maxlen=self.config.max_alerts_stored)
        self.alert_history: Dict[str, datetime] = {}   # cooldown
        self.metrics_history: Deque[HealthMetrics] = deque(maxlen=100)
        self.alert_callbacks: List[Callable[[Alert], None]] = []

        # Error tracking
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_timestamps: Dict[str, List[datetime]] = defaultdict(list)

        # Health check results (latest run)
        self.health_checks: List[HealthCheck] = []

        # Metrics
        self.metrics = MetricsCollector()

        logger.info("Error monitoring service initialized")

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        self.alert_callbacks.append(callback)
        logger.info("Registered alert callback: %s", getattr(callback, "__name__", repr(callback)))

    def record_error(self, error_type: str, component: str = "unknown") -> None:
        """Record an error occurrence for monitoring."""
        now = datetime.now()
        self.error_counts[error_type] += 1
        self.error_timestamps[error_type].append(now)

        # clean old window
        cutoff = now - timedelta(minutes=self.config.monitoring_window_minutes)
        self.error_timestamps[error_type] = [ts for ts in self.error_timestamps[error_type] if ts > cutoff]

        recent_count = len(self.error_timestamps[error_type])
        if recent_count >= self.config.critical_error_threshold:
            self._raise_alert(
                AlertSeverity.ERROR,
                f"High error rate for {error_type}",
                f"Detected {recent_count} {error_type} errors in the last "
                f"{self.config.monitoring_window_minutes} minutes",
                component,
                metadata={"recent_count": recent_count},
            )

    def check_system_health(self) -> HealthMetrics:
        """Perform comprehensive system health check."""
        ts = datetime.now()

        # Error statistics
        _ = get_error_stats()  # retained for backward compat / side effects
        recent_errors = len(get_recent_errors(10))
        ux_error_stats = get_ux_error_stats()

        error_rate = self._calculate_error_rate(recent_errors)

        # Circuit breaker health
        circuit_breaker_health = self._assess_circuit_breaker_health()

        # Resource checks (memory/disk/cpu) -> resource_health + discrete checks stored
        resource_health = self._assess_resource_health()

        # Processing (UX pipeline) health from stats
        processing_health = self._assess_processing_health(ux_error_stats)

        # Overall (weighted)
        overall_health = (
            circuit_breaker_health * 0.30
            + resource_health * 0.30
            + processing_health * 0.40
        )

        active_alerts = [a for a in self.alerts if not a.resolved]
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]

        metrics = HealthMetrics(
            overall_health=overall_health,
            error_rate=error_rate,
            circuit_breaker_health=circuit_breaker_health,
            resource_health=resource_health,
            processing_health=processing_health,
            timestamp=ts,
            alerts_count=len(active_alerts),
            critical_alerts_count=len(critical_alerts),
        )
        self.metrics_history.append(metrics)

        # Emit alerts if thresholds crossed
        self._check_alert_conditions(metrics)

        # basic metrics
        try:
            self.metrics.increment_counter("health_checks_total", {"status": "ok"})
            self.metrics.gauge("overall_health", overall_health, {})
            self.metrics.gauge("processing_health", processing_health, {})
            self.metrics.gauge("resource_health", resource_health, {})
            self.metrics.gauge("circuit_breaker_health", circuit_breaker_health, {})
            self.metrics.gauge("error_rate", error_rate, {})
        except Exception:
            pass

        return metrics

    def resolve_alert(self, alert_id: str) -> bool:
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolution_time = datetime.now()
                logger.info("Alert resolved: %s", alert.title)
                return True
        return False

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        active = [a for a in self.alerts if not a.resolved]
        if severity:
            active = [a for a in active if a.severity == severity]
        return sorted(active, key=lambda a: a.timestamp, reverse=True)

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alerts if a.timestamp > cutoff]

    def get_health_trend(self, hours: int = 6) -> List[HealthMetrics]:
        cutoff = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics_history if m.timestamp > cutoff]

    def get_monitoring_summary(self) -> Dict[str, Any]:
        current = self.check_system_health()
        active = self.get_active_alerts()
        recent = self.get_alert_history(24)

        return {
            "current_health": {
                "overall_health": current.overall_health,
                "error_rate": current.error_rate,
                "circuit_breaker_health": current.circuit_breaker_health,
                "resource_health": current.resource_health,
                "processing_health": current.processing_health,
                "timestamp": current.timestamp.isoformat(),
            },
            "alerts": {
                "active_count": len(active),
                "critical_count": current.critical_alerts_count,
                "recent_24h_count": len(recent),
                "active_alerts": [
                    {
                        "id": a.id,
                        "severity": a.severity.value,
                        "title": a.title,
                        "message": a.message,
                        "component": a.component,
                        "timestamp": a.timestamp.isoformat(),
                    }
                    for a in active[:10]
                ],
            },
            "error_tracking": {
                "total_error_types": len(self.error_counts),
                "most_common_errors": sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            },
            "health_checks": [hc.__dict__ for hc in self.health_checks],  # last discrete checks
            "monitoring_config": {
                "error_rate_threshold": self.config.error_rate_threshold,
                "monitoring_window_minutes": self.config.monitoring_window_minutes,
                "alert_cooldown_minutes": self.config.alert_cooldown_minutes,
            },
        }

    # -------------------------------------------------------------------------
    # Internals: alerts, circuit breaker, resources, processing
    # -------------------------------------------------------------------------

    def _calculate_error_rate(self, recent_errors: int) -> float:
        if recent_errors <= 0:
            return 0.0
        if recent_errors <= 2:
            return 0.05
        if recent_errors <= 5:
            return 0.15
        return min(0.5, recent_errors * 0.05)

    def _assess_circuit_breaker_health(self) -> float:
        if not self.config.enable_circuit_breaker_monitoring:
            return 1.0
        try:
            cb_stats = get_all_circuit_breaker_stats()
            unhealthy = get_unhealthy_services()
            if not cb_stats:
                return 1.0

            total = len(cb_stats)
            healthy = total - len(unhealthy)
            score = healthy / total if total > 0 else 1.0

            if unhealthy:
                self._raise_alert(
                    AlertSeverity.WARNING,
                    "Circuit breakers open",
                    f"Services with open circuit breakers: {', '.join(unhealthy)}",
                    "circuit_breaker",
                    {"unhealthy": unhealthy},
                )
            return score
        except Exception as e:  # be robust
            logger.warning("Failed to assess circuit breaker health: %s", e)
            return 0.8

    def _status_to_score(self, status: str) -> float:
        if status == "healthy":
            return 1.0
        if status == "degraded":
            return 0.7
        return 0.3  # "unhealthy" or unknown

    def _assess_resource_health(self) -> float:
        """Run discrete HealthChecks for memory/disk/cpu and aggregate to a score."""
        self.health_checks = []  # reset for this run
        if not self.config.enable_resource_monitoring:
            return 1.0

        try:
            import psutil  # optional dependency
        except Exception:
            logger.warning("psutil not available; skipping resource checks")
            return 1.0

        checks: List[HealthCheck] = []

        # Memory
        try:
            mem = psutil.virtual_memory()
            usage = mem.percent / 100.0
            if usage > self.config.memory_threshold:
                status = "unhealthy" if usage > 0.95 else "degraded"
                msg = f"High memory usage: {usage:.1%}"
                if usage > 0.95:
                    self._raise_alert(AlertSeverity.CRITICAL, "High memory usage", msg, "system_resources",
                                      {"usage_percent": mem.percent})
            else:
                status = "healthy"
                msg = f"Memory usage normal: {usage:.1%}"
            checks.append(HealthCheck("memory", status, msg, time.time(), {"usage_percent": usage}))
            try:
                self.metrics.gauge("resource_memory_usage", usage, {})
            except Exception:
                pass
        except Exception as e:
            logger.warning("Memory check failed: %s", e)

        # Disk
        try:
            disk = psutil.disk_usage("/")
            usage = disk.percent / 100.0
            if usage > self.config.disk_threshold:
                status = "unhealthy"
                msg = f"Low disk space: {usage:.1%} used"
                self._raise_alert(AlertSeverity.CRITICAL, "Low disk space", msg, "system_resources",
                                  {"usage_percent": disk.percent})
            elif usage > 0.80:
                status = "degraded"
                msg = f"Disk space getting low: {usage:.1%} used"
            else:
                status = "healthy"
                msg = f"Disk space normal: {usage:.1%} used"
            checks.append(HealthCheck("disk", status, msg, time.time(), {"usage_percent": usage}))
            try:
                self.metrics.gauge("resource_disk_usage", usage, {})
            except Exception:
                pass
        except Exception as e:
            logger.warning("Disk check failed: %s", e)

        # CPU
        try:
            import psutil  # re-use to avoid linter nags
            cpu = psutil.cpu_percent(interval=0.1) / 100.0
            if cpu > self.config.cpu_threshold:
                status = "unhealthy"
                msg = f"High CPU usage: {cpu:.1%}"
                self._raise_alert(AlertSeverity.WARNING, "High CPU usage", msg, "system_resources",
                                  {"usage_percent": cpu * 100.0})
            elif cpu > 0.80:
                status = "degraded"
                msg = f"Elevated CPU usage: {cpu:.1%}"
            else:
                status = "healthy"
                msg = f"CPU usage normal: {cpu:.1%}"
            checks.append(HealthCheck("cpu", status, msg, time.time(), {"usage_percent": cpu}))
            try:
                self.metrics.gauge("resource_cpu_usage", cpu, {})
            except Exception:
                pass
        except Exception as e:
            logger.warning("CPU check failed: %s", e)

        self.health_checks = checks
        if not checks:
            return 1.0  # best effort

        # Aggregate
        score = sum(self._status_to_score(c.status) for c in checks) / len(checks)
        return max(0.0, min(1.0, score))

    def _assess_processing_health(self, ux_error_stats: Dict[str, Any]) -> float:
        """Assess UX processing health based on error counters."""
        try:
            total_failures = ux_error_stats.get("total_failures", 0)
            if total_failures <= 0:
                return 1.0

            img = ux_error_stats.get("image_processing_failures", 0)
            prereq = ux_error_stats.get("prerequisite_failures", 0)
            retry_ex = ux_error_stats.get("retry_exhaustions", 0)

            weighted = img * 0.4 + prereq * 0.3 + retry_ex * 0.3
            if weighted <= 5:
                score = 1.0 - (weighted * 0.1)
            else:
                score = max(0.0, 0.5 - ((weighted - 5) * 0.05))

            if total_failures > 10:
                self._raise_alert(
                    AlertSeverity.WARNING,
                    "High processing failure rate",
                    f"Total UX processing failures: {total_failures}",
                    "ux_processing",
                    {"total_failures": total_failures},
                )

            try:
                self.metrics.gauge("processing_health_weighted", weighted, {})
            except Exception:
                pass

            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.warning("Failed to assess processing health: %s", e)
            return 0.8

    def _check_alert_conditions(self, metrics: HealthMetrics) -> None:
        if metrics.overall_health < 0.5:
            self._raise_alert(
                AlertSeverity.CRITICAL,
                "System health critical",
                f"Overall system health at {metrics.overall_health:.1%}",
                "system_health",
                {"overall_health": metrics.overall_health},
            )
        elif metrics.overall_health < 0.7:
            self._raise_alert(
                AlertSeverity.WARNING,
                "System health degraded",
                f"Overall system health at {metrics.overall_health:.1%}",
                "system_health",
                {"overall_health": metrics.overall_health},
            )

        if metrics.error_rate > self.config.error_rate_threshold:
            self._raise_alert(
                AlertSeverity.ERROR,
                "High error rate",
                f"Error rate at {metrics.error_rate:.1%} "
                f"(threshold: {self.config.error_rate_threshold:.1%})",
                "error_rate",
                {"error_rate": metrics.error_rate},
            )

    def _raise_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        component: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create & broadcast an alert, honoring cooldown."""
        key = f"{component}:{title}"
        now = datetime.now()

        last = self.alert_history.get(key)
        if last and (now - last) < timedelta(minutes=self.config.alert_cooldown_minutes):
            return  # cooldown active

        alert = Alert(
            id=f"{int(time.time())}_{component}_{severity.value}",
            severity=severity,
            title=title,
            message=message,
            timestamp=now,
            component=component,
            metadata=metadata or {},
        )

        self.alerts.append(alert)
        self.alert_history[key] = now

        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }[severity]
        logger.log(log_level, "ALERT [%s] %s: %s", severity.value.upper(), title, message)

        for cb in list(self.alert_callbacks):
            try:
                cb(alert)
            except Exception as e:
                logger.error("Alert callback failed: %s", e)


# -----------------------------------------------------------------------------
# Module-level helpers (backward-compatible API)
# -----------------------------------------------------------------------------

error_monitoring_service = ErrorMonitoringService()


def get_system_health() -> HealthMetrics:
    return error_monitoring_service.check_system_health()


def record_error_for_monitoring(error_type: str, component: str = "unknown") -> None:
    error_monitoring_service.record_error(error_type, component)


def get_active_alerts(severity: Optional[AlertSeverity] = None) -> List[Alert]:
    return error_monitoring_service.get_active_alerts(severity)


def resolve_alert(alert_id: str) -> bool:
    return error_monitoring_service.resolve_alert(alert_id)


def get_monitoring_summary() -> Dict[str, Any]:
    return error_monitoring_service.get_monitoring_summary()


def register_alert_callback(callback: Callable[[Alert], None]) -> None:
    error_monitoring_service.register_alert_callback(callback)

__all__ = [
    "AlertSeverity", "Alert", "HealthCheck", "HealthMetrics", "MonitoringConfig",
    "ErrorMonitoringService",
    "get_system_health", "record_error_for_monitoring", "get_active_alerts",
    "resolve_alert", "get_monitoring_summary", "register_alert_callback",
]