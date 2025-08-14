"""
Error Monitoring Service for GITTE UX enhancements.
Provides real-time error monitoring, alerting, and health checks.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# ProcessingResourceError will be defined inline if needed
from src.utils.circuit_breaker import get_all_circuit_breaker_stats, get_unhealthy_services
from src.utils.error_handler import get_error_stats, get_recent_errors
from src.utils.ux_error_handler import get_ux_error_stats

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
    metadata: Dict[str, Any] = None


@dataclass
class HealthMetrics:
    """System health metrics."""
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
    error_rate_threshold: float = 0.1  # 10% error rate threshold
    critical_error_threshold: int = 5  # 5 critical errors in window
    monitoring_window_minutes: int = 15
    alert_cooldown_minutes: int = 5
    max_alerts_stored: int = 100
    enable_resource_monitoring: bool = True
    enable_circuit_breaker_monitoring: bool = True


class ErrorMonitoringService:
    """Service for monitoring system errors and health."""
    
    def __init__(self, config: MonitoringConfig = None):
        """
        Initialize error monitoring service.
        
        Args:
            config: Monitoring configuration
        """
        self.config = config or MonitoringConfig()
        self.alerts: deque = deque(maxlen=self.config.max_alerts_stored)
        self.alert_history: Dict[str, datetime] = {}  # For cooldown tracking
        self.metrics_history: deque = deque(maxlen=100)  # Store last 100 metrics
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Error tracking
        self.error_counts = defaultdict(int)
        self.error_timestamps = defaultdict(list)
        
        logger.info("Error monitoring service initialized")
    
    def register_alert_callback(self, callback: Callable[[Alert], None]):
        """
        Register callback function for alert notifications.
        
        Args:
            callback: Function to call when alert is raised
        """
        self.alert_callbacks.append(callback)
        logger.info(f"Registered alert callback: {callback.__name__}")
    
    def check_system_health(self) -> HealthMetrics:
        """
        Perform comprehensive system health check.
        
        Returns:
            HealthMetrics with current system health status
        """
        timestamp = datetime.now()
        
        # Get error statistics
        error_stats = get_error_stats()
        ux_error_stats = get_ux_error_stats()
        
        # Calculate error rate
        total_errors = error_stats.get("total_errors", 0)
        recent_errors = len(get_recent_errors(10))
        error_rate = self._calculate_error_rate(recent_errors)
        
        # Check circuit breaker health
        circuit_breaker_health = self._assess_circuit_breaker_health()
        
        # Check resource health
        resource_health = self._assess_resource_health()
        
        # Check processing health
        processing_health = self._assess_processing_health(ux_error_stats)
        
        # Calculate overall health (weighted average)
        overall_health = (
            circuit_breaker_health * 0.3 +
            resource_health * 0.3 +
            processing_health * 0.4
        )
        
        # Count active alerts
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        critical_alerts = [
            alert for alert in active_alerts 
            if alert.severity == AlertSeverity.CRITICAL
        ]
        
        metrics = HealthMetrics(
            overall_health=overall_health,
            error_rate=error_rate,
            circuit_breaker_health=circuit_breaker_health,
            resource_health=resource_health,
            processing_health=processing_health,
            timestamp=timestamp,
            alerts_count=len(active_alerts),
            critical_alerts_count=len(critical_alerts)
        )
        
        # Store metrics history
        self.metrics_history.append(metrics)
        
        # Check for alert conditions
        self._check_alert_conditions(metrics)
        
        return metrics
    
    def record_error(self, error_type: str, component: str = "unknown"):
        """
        Record an error occurrence for monitoring.
        
        Args:
            error_type: Type of error that occurred
            component: Component where error occurred
        """
        now = datetime.now()
        self.error_counts[error_type] += 1
        self.error_timestamps[error_type].append(now)
        
        # Clean old timestamps (outside monitoring window)
        cutoff_time = now - timedelta(minutes=self.config.monitoring_window_minutes)
        self.error_timestamps[error_type] = [
            ts for ts in self.error_timestamps[error_type] 
            if ts > cutoff_time
        ]
        
        # Check if this error type is causing issues
        recent_count = len(self.error_timestamps[error_type])
        if recent_count >= self.config.critical_error_threshold:
            self._raise_alert(
                AlertSeverity.ERROR,
                f"High error rate for {error_type}",
                f"Detected {recent_count} {error_type} errors in the last {self.config.monitoring_window_minutes} minutes",
                component
            )
    
    def _calculate_error_rate(self, recent_errors: int) -> float:
        """
        Calculate current error rate.
        
        Args:
            recent_errors: Number of recent errors
            
        Returns:
            Error rate as percentage (0.0 to 1.0)
        """
        # Simple calculation based on recent errors
        # In a real system, this would be errors/total_requests
        if recent_errors == 0:
            return 0.0
        elif recent_errors <= 2:
            return 0.05  # 5%
        elif recent_errors <= 5:
            return 0.15  # 15%
        else:
            return min(0.5, recent_errors * 0.05)  # Cap at 50%
    
    def _assess_circuit_breaker_health(self) -> float:
        """
        Assess circuit breaker health.
        
        Returns:
            Health score (0.0 to 1.0)
        """
        if not self.config.enable_circuit_breaker_monitoring:
            return 1.0
        
        try:
            cb_stats = get_all_circuit_breaker_stats()
            unhealthy_services = get_unhealthy_services()
            
            if not cb_stats:
                return 1.0  # No circuit breakers configured
            
            total_breakers = len(cb_stats)
            healthy_breakers = total_breakers - len(unhealthy_services)
            
            health_score = healthy_breakers / total_breakers if total_breakers > 0 else 1.0
            
            # Alert on unhealthy services
            if unhealthy_services:
                self._raise_alert(
                    AlertSeverity.WARNING,
                    "Circuit breakers open",
                    f"Services with open circuit breakers: {', '.join(unhealthy_services)}",
                    "circuit_breaker"
                )
            
            return health_score
            
        except Exception as e:
            logger.warning(f"Failed to assess circuit breaker health: {e}")
            return 0.8  # Assume mostly healthy if we can't check
    
    def _assess_resource_health(self) -> float:
        """
        Assess system resource health.
        
        Returns:
            Health score (0.0 to 1.0)
        """
        if not self.config.enable_resource_monitoring:
            return 1.0
        
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_health = max(0.0, 1.0 - (memory.percent / 100.0))
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_health = max(0.0, 1.0 - (disk_usage_percent / 100.0))
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_health = max(0.0, 1.0 - (cpu_percent / 100.0))
            
            # Weighted average
            resource_health = (memory_health * 0.4 + disk_health * 0.3 + cpu_health * 0.3)
            
            # Alert on critical resource usage
            if memory.percent > 90:
                self._raise_alert(
                    AlertSeverity.CRITICAL,
                    "High memory usage",
                    f"Memory usage at {memory.percent:.1f}%",
                    "system_resources"
                )
            
            if disk_usage_percent > 90:
                self._raise_alert(
                    AlertSeverity.CRITICAL,
                    "Low disk space",
                    f"Disk usage at {disk_usage_percent:.1f}%",
                    "system_resources"
                )
            
            if cpu_percent > 95:
                self._raise_alert(
                    AlertSeverity.WARNING,
                    "High CPU usage",
                    f"CPU usage at {cpu_percent:.1f}%",
                    "system_resources"
                )
            
            return resource_health
            
        except ImportError:
            logger.warning("psutil not available for resource monitoring")
            return 1.0
        except Exception as e:
            logger.warning(f"Failed to assess resource health: {e}")
            return 0.8
    
    def _assess_processing_health(self, ux_error_stats: Dict[str, Any]) -> float:
        """
        Assess UX processing health.
        
        Args:
            ux_error_stats: UX error statistics
            
        Returns:
            Health score (0.0 to 1.0)
        """
        try:
            total_failures = ux_error_stats.get("total_failures", 0)
            
            if total_failures == 0:
                return 1.0
            
            # Calculate health based on failure types and counts
            image_failures = ux_error_stats.get("image_processing_failures", 0)
            prerequisite_failures = ux_error_stats.get("prerequisite_failures", 0)
            retry_exhaustions = ux_error_stats.get("retry_exhaustions", 0)
            
            # Weight different failure types
            weighted_failures = (
                image_failures * 0.4 +
                prerequisite_failures * 0.3 +
                retry_exhaustions * 0.3
            )
            
            # Convert to health score (inverse relationship)
            if weighted_failures <= 5:
                health_score = 1.0 - (weighted_failures * 0.1)
            else:
                health_score = max(0.0, 0.5 - ((weighted_failures - 5) * 0.05))
            
            # Alert on high processing failures
            if total_failures > 10:
                self._raise_alert(
                    AlertSeverity.WARNING,
                    "High processing failure rate",
                    f"Total UX processing failures: {total_failures}",
                    "ux_processing"
                )
            
            return max(0.0, health_score)
            
        except Exception as e:
            logger.warning(f"Failed to assess processing health: {e}")
            return 0.8
    
    def _check_alert_conditions(self, metrics: HealthMetrics):
        """
        Check for conditions that should trigger alerts.
        
        Args:
            metrics: Current health metrics
        """
        # Overall health alert
        if metrics.overall_health < 0.5:
            self._raise_alert(
                AlertSeverity.CRITICAL,
                "System health critical",
                f"Overall system health at {metrics.overall_health:.1%}",
                "system_health"
            )
        elif metrics.overall_health < 0.7:
            self._raise_alert(
                AlertSeverity.WARNING,
                "System health degraded",
                f"Overall system health at {metrics.overall_health:.1%}",
                "system_health"
            )
        
        # Error rate alert
        if metrics.error_rate > self.config.error_rate_threshold:
            self._raise_alert(
                AlertSeverity.ERROR,
                "High error rate",
                f"Error rate at {metrics.error_rate:.1%} (threshold: {self.config.error_rate_threshold:.1%})",
                "error_rate"
            )
    
    def _raise_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        component: str,
        metadata: Dict[str, Any] = None
    ):
        """
        Raise a system alert.
        
        Args:
            severity: Alert severity level
            title: Alert title
            message: Alert message
            component: Component that triggered the alert
            metadata: Additional alert metadata
        """
        alert_key = f"{component}:{title}"
        now = datetime.now()
        
        # Check cooldown period
        if alert_key in self.alert_history:
            last_alert_time = self.alert_history[alert_key]
            if now - last_alert_time < timedelta(minutes=self.config.alert_cooldown_minutes):
                return  # Skip alert due to cooldown
        
        # Create alert
        alert = Alert(
            id=f"{int(time.time())}_{component}_{severity.value}",
            severity=severity,
            title=title,
            message=message,
            timestamp=now,
            component=component,
            metadata=metadata or {}
        )
        
        # Store alert
        self.alerts.append(alert)
        self.alert_history[alert_key] = now
        
        # Log alert
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }[severity]
        
        logger.log(log_level, f"ALERT [{severity.value.upper()}] {title}: {message}")
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as resolved.
        
        Args:
            alert_id: ID of alert to resolve
            
        Returns:
            True if alert was found and resolved
        """
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolution_time = datetime.now()
                logger.info(f"Alert resolved: {alert.title}")
                return True
        
        return False
    
    def get_active_alerts(self, severity: AlertSeverity = None) -> List[Alert]:
        """
        Get list of active (unresolved) alerts.
        
        Args:
            severity: Optional severity filter
            
        Returns:
            List of active alerts
        """
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        if severity:
            active_alerts = [alert for alert in active_alerts if alert.severity == severity]
        
        return sorted(active_alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """
        Get alert history for specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of alerts from the specified period
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self.alerts 
            if alert.timestamp > cutoff_time
        ]
    
    def get_health_trend(self, hours: int = 6) -> List[HealthMetrics]:
        """
        Get health metrics trend for specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of health metrics from the specified period
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            metrics for metrics in self.metrics_history 
            if metrics.timestamp > cutoff_time
        ]
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring summary.
        
        Returns:
            Dict with monitoring statistics and status
        """
        current_health = self.check_system_health()
        active_alerts = self.get_active_alerts()
        recent_alerts = self.get_alert_history(24)
        
        return {
            "current_health": {
                "overall_health": current_health.overall_health,
                "error_rate": current_health.error_rate,
                "circuit_breaker_health": current_health.circuit_breaker_health,
                "resource_health": current_health.resource_health,
                "processing_health": current_health.processing_health,
                "timestamp": current_health.timestamp.isoformat(),
            },
            "alerts": {
                "active_count": len(active_alerts),
                "critical_count": current_health.critical_alerts_count,
                "recent_24h_count": len(recent_alerts),
                "active_alerts": [
                    {
                        "id": alert.id,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "message": alert.message,
                        "component": alert.component,
                        "timestamp": alert.timestamp.isoformat(),
                    }
                    for alert in active_alerts[:10]  # Limit to 10 most recent
                ],
            },
            "error_tracking": {
                "total_error_types": len(self.error_counts),
                "most_common_errors": sorted(
                    self.error_counts.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5],
            },
            "monitoring_config": {
                "error_rate_threshold": self.config.error_rate_threshold,
                "monitoring_window_minutes": self.config.monitoring_window_minutes,
                "alert_cooldown_minutes": self.config.alert_cooldown_minutes,
            },
        }


# Global error monitoring service instance
error_monitoring_service = ErrorMonitoringService()


def get_system_health() -> HealthMetrics:
    """Get current system health metrics."""
    return error_monitoring_service.check_system_health()


def record_error_for_monitoring(error_type: str, component: str = "unknown"):
    """Record an error for monitoring purposes."""
    error_monitoring_service.record_error(error_type, component)


def get_active_alerts(severity: AlertSeverity = None) -> List[Alert]:
    """Get list of active system alerts."""
    return error_monitoring_service.get_active_alerts(severity)


def resolve_alert(alert_id: str) -> bool:
    """Resolve a system alert by ID."""
    return error_monitoring_service.resolve_alert(alert_id)


def get_monitoring_summary() -> Dict[str, Any]:
    """Get comprehensive monitoring summary."""
    return error_monitoring_service.get_monitoring_summary()


def register_alert_callback(callback: Callable[[Alert], None]):
    """Register callback for alert notifications."""
    error_monitoring_service.register_alert_callback(callback)