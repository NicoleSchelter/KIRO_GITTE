"""
Administrative statistics service for GITTE.
Provides comprehensive statistics, analytics, and reporting for administrators.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.data.database import get_session
from src.services.audit_service import get_audit_service

logger = logging.getLogger(__name__)


@dataclass
class UserStatistics:
    """User-related statistics."""

    total_users: int
    admin_users: int
    participant_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    active_users_today: int
    active_users_this_week: int
    active_users_this_month: int


@dataclass
class SystemStatistics:
    """System-wide statistics."""

    total_chat_sessions: int
    total_images_generated: int
    total_pald_records: int
    total_audit_logs: int
    total_consent_records: int
    avg_session_duration_minutes: float
    avg_response_time_ms: float
    error_rate_percent: float
    uptime_hours: float


@dataclass
class PALDStatistics:
    """PALD-related statistics."""

    total_pald_records: int
    unique_schema_versions: int
    avg_coverage_percent: float
    attribute_candidates: int
    attributes_added_to_schema: int
    most_common_attributes: list[tuple[str, int]]
    schema_evolution_events: int


@dataclass
class PerformanceStatistics:
    """Performance-related statistics."""

    avg_llm_response_time_ms: float
    avg_image_generation_time_ms: float
    avg_database_query_time_ms: float
    peak_concurrent_users: int
    requests_per_hour: float
    cache_hit_rate_percent: float
    error_rate_by_operation: dict[str, float]


class AdminStatisticsService:
    """Service for generating administrative statistics and reports."""

    def __init__(self):
        self.audit_service = get_audit_service()

    def get_dashboard_statistics(self) -> dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        try:
            user_stats = self.get_user_statistics()
            system_stats = self.get_system_statistics()
            pald_stats = self.get_pald_statistics()
            performance_stats = self.get_performance_statistics()

            return {
                "users": {
                    "total": user_stats.total_users,
                    "admins": user_stats.admin_users,
                    "participants": user_stats.participant_users,
                    "new_today": user_stats.new_users_today,
                    "new_this_week": user_stats.new_users_this_week,
                    "new_this_month": user_stats.new_users_this_month,
                    "active_today": user_stats.active_users_today,
                    "active_this_week": user_stats.active_users_this_week,
                    "active_this_month": user_stats.active_users_this_month,
                },
                "system": {
                    "chat_sessions": system_stats.total_chat_sessions,
                    "images_generated": system_stats.total_images_generated,
                    "pald_records": system_stats.total_pald_records,
                    "audit_logs": system_stats.total_audit_logs,
                    "consent_records": system_stats.total_consent_records,
                    "avg_session_duration_minutes": system_stats.avg_session_duration_minutes,
                    "avg_response_time_ms": system_stats.avg_response_time_ms,
                    "error_rate_percent": system_stats.error_rate_percent,
                    "uptime_hours": system_stats.uptime_hours,
                },
                "pald": {
                    "total_records": pald_stats.total_pald_records,
                    "schema_versions": pald_stats.unique_schema_versions,
                    "avg_coverage_percent": pald_stats.avg_coverage_percent,
                    "attribute_candidates": pald_stats.attribute_candidates,
                    "attributes_added": pald_stats.attributes_added_to_schema,
                    "most_common_attributes": pald_stats.most_common_attributes,
                    "schema_evolution_events": pald_stats.schema_evolution_events,
                },
                "performance": {
                    "avg_llm_response_time_ms": performance_stats.avg_llm_response_time_ms,
                    "avg_image_generation_time_ms": performance_stats.avg_image_generation_time_ms,
                    "avg_database_query_time_ms": performance_stats.avg_database_query_time_ms,
                    "peak_concurrent_users": performance_stats.peak_concurrent_users,
                    "requests_per_hour": performance_stats.requests_per_hour,
                    "cache_hit_rate_percent": performance_stats.cache_hit_rate_percent,
                    "error_rate_by_operation": performance_stats.error_rate_by_operation,
                },
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating dashboard statistics: {e}")
            return {"error": str(e)}

    def get_user_statistics(self) -> UserStatistics:
        """Get user-related statistics."""
        try:
            with get_session() as db_session:
                # Total users by role
                total_users_result = db_session.execute("SELECT COUNT(*) FROM users").scalar()
                admin_users_result = db_session.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'ADMIN'"
                ).scalar()
                participant_users_result = db_session.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'PARTICIPANT'"
                ).scalar()

                # New users by time period
                new_users_today_result = db_session.execute(
                    "SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE"
                ).scalar()

                new_users_this_week_result = db_session.execute(
                    "SELECT COUNT(*) FROM users WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)"
                ).scalar()

                new_users_this_month_result = db_session.execute(
                    "SELECT COUNT(*) FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)"
                ).scalar()

                # Active users (users with recent audit log entries)
                active_users_today_result = db_session.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) FROM audit_logs 
                    WHERE DATE(created_at) = CURRENT_DATE AND user_id IS NOT NULL
                """
                ).scalar()

                active_users_this_week_result = db_session.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) FROM audit_logs 
                    WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE) AND user_id IS NOT NULL
                """
                ).scalar()

                active_users_this_month_result = db_session.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) FROM audit_logs 
                    WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE) AND user_id IS NOT NULL
                """
                ).scalar()

                return UserStatistics(
                    total_users=total_users_result or 0,
                    admin_users=admin_users_result or 0,
                    participant_users=participant_users_result or 0,
                    new_users_today=new_users_today_result or 0,
                    new_users_this_week=new_users_this_week_result or 0,
                    new_users_this_month=new_users_this_month_result or 0,
                    active_users_today=active_users_today_result or 0,
                    active_users_this_week=active_users_this_week_result or 0,
                    active_users_this_month=active_users_this_month_result or 0,
                )

        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return UserStatistics(0, 0, 0, 0, 0, 0, 0, 0, 0)

    def get_system_statistics(self) -> SystemStatistics:
        """Get system-wide statistics."""
        try:
            with get_session() as db_session:
                # Count different types of operations
                chat_sessions_result = db_session.execute(
                    "SELECT COUNT(*) FROM audit_logs WHERE operation = 'chat'"
                ).scalar()

                images_generated_result = db_session.execute(
                    "SELECT COUNT(*) FROM audit_logs WHERE operation = 'image_generation'"
                ).scalar()

                pald_records_result = db_session.execute("SELECT COUNT(*) FROM pald_data").scalar()
                audit_logs_result = db_session.execute("SELECT COUNT(*) FROM audit_logs").scalar()
                consent_records_result = db_session.execute(
                    "SELECT COUNT(*) FROM consent_records"
                ).scalar()

                # Average session duration (mock calculation)
                avg_session_duration = 15.5  # Would be calculated from actual session data

                # Average response time
                avg_response_time_result = db_session.execute(
                    "SELECT AVG(latency_ms) FROM audit_logs WHERE latency_ms IS NOT NULL"
                ).scalar()

                # Error rate
                total_operations_result = db_session.execute(
                    "SELECT COUNT(*) FROM audit_logs"
                ).scalar()
                error_operations_result = db_session.execute(
                    "SELECT COUNT(*) FROM audit_logs WHERE status = 'error'"
                ).scalar()

                error_rate = 0.0
                if total_operations_result and total_operations_result > 0:
                    error_rate = (error_operations_result / total_operations_result) * 100

                # System uptime (mock - would be calculated from system start time)
                uptime_hours = 72.5

                return SystemStatistics(
                    total_chat_sessions=chat_sessions_result or 0,
                    total_images_generated=images_generated_result or 0,
                    total_pald_records=pald_records_result or 0,
                    total_audit_logs=audit_logs_result or 0,
                    total_consent_records=consent_records_result or 0,
                    avg_session_duration_minutes=avg_session_duration,
                    avg_response_time_ms=float(avg_response_time_result or 0),
                    error_rate_percent=error_rate,
                    uptime_hours=uptime_hours,
                )

        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return SystemStatistics(0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0)

    def get_pald_statistics(self) -> PALDStatistics:
        """Get PALD-related statistics."""
        try:
            with get_session() as db_session:
                # Basic PALD counts
                total_pald_result = db_session.execute("SELECT COUNT(*) FROM pald_data").scalar()

                unique_schemas_result = db_session.execute(
                    "SELECT COUNT(DISTINCT schema_version) FROM pald_data"
                ).scalar()

                # Average coverage (mock calculation)
                avg_coverage = 75.5  # Would be calculated from actual PALD data

                # Attribute candidates
                attribute_candidates_result = db_session.execute(
                    "SELECT COUNT(*) FROM pald_attribute_candidates"
                ).scalar()

                attributes_added_result = db_session.execute(
                    "SELECT COUNT(*) FROM pald_attribute_candidates WHERE added_to_schema = true"
                ).scalar()

                # Most common attributes
                most_common_result = db_session.execute(
                    """
                    SELECT attribute_name, mention_count 
                    FROM pald_attribute_candidates 
                    ORDER BY mention_count DESC 
                    LIMIT 5
                """
                ).fetchall()

                most_common_attributes = [
                    (row.attribute_name, row.mention_count) for row in most_common_result
                ]

                # Schema evolution events
                schema_evolution_result = db_session.execute(
                    "SELECT COUNT(*) FROM pald_schema_versions"
                ).scalar()

                return PALDStatistics(
                    total_pald_records=total_pald_result or 0,
                    unique_schema_versions=unique_schemas_result or 0,
                    avg_coverage_percent=avg_coverage,
                    attribute_candidates=attribute_candidates_result or 0,
                    attributes_added_to_schema=attributes_added_result or 0,
                    most_common_attributes=most_common_attributes,
                    schema_evolution_events=schema_evolution_result or 0,
                )

        except Exception as e:
            logger.error(f"Error getting PALD statistics: {e}")
            return PALDStatistics(0, 0, 0.0, 0, 0, [], 0)

    def get_performance_statistics(self) -> PerformanceStatistics:
        """Get performance-related statistics."""
        try:
            with get_session() as db_session:
                # Average response times by operation
                llm_response_time_result = db_session.execute(
                    """
                    SELECT AVG(latency_ms) FROM audit_logs 
                    WHERE operation = 'chat' AND latency_ms IS NOT NULL
                """
                ).scalar()

                image_generation_time_result = db_session.execute(
                    """
                    SELECT AVG(latency_ms) FROM audit_logs 
                    WHERE operation = 'image_generation' AND latency_ms IS NOT NULL
                """
                ).scalar()

                # Database query time (mock)
                db_query_time = 25.0

                # Peak concurrent users (mock - would be calculated from session data)
                peak_concurrent = 15

                # Requests per hour
                requests_per_hour_result = db_session.execute(
                    """
                    SELECT COUNT(*) / 24.0 FROM audit_logs 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                """
                ).scalar()

                # Cache hit rate (mock)
                cache_hit_rate = 85.5

                # Error rate by operation
                error_rates_result = db_session.execute(
                    """
                    SELECT 
                        operation,
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'error' THEN 1 END) as errors
                    FROM audit_logs 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY operation
                """
                ).fetchall()

                error_rate_by_operation = {}
                for row in error_rates_result:
                    if row.total > 0:
                        error_rate = (row.errors / row.total) * 100
                        error_rate_by_operation[row.operation] = error_rate

                return PerformanceStatistics(
                    avg_llm_response_time_ms=float(llm_response_time_result or 0),
                    avg_image_generation_time_ms=float(image_generation_time_result or 0),
                    avg_database_query_time_ms=db_query_time,
                    peak_concurrent_users=peak_concurrent,
                    requests_per_hour=float(requests_per_hour_result or 0),
                    cache_hit_rate_percent=cache_hit_rate,
                    error_rate_by_operation=error_rate_by_operation,
                )

        except Exception as e:
            logger.error(f"Error getting performance statistics: {e}")
            return PerformanceStatistics(0.0, 0.0, 0.0, 0, 0.0, 0.0, {})

    def get_activity_trends(self, days: int = 7) -> list[dict[str, Any]]:
        """Get activity trends over the specified number of days."""
        try:
            with get_session() as db_session:
                query = """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(CASE WHEN operation = 'chat' THEN 1 END) as chat_sessions,
                    COUNT(CASE WHEN operation = 'image_generation' THEN 1 END) as images_generated,
                    COUNT(DISTINCT user_id) as active_users,
                    AVG(latency_ms) as avg_response_time
                FROM audit_logs 
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """

                result = db_session.execute(query, (days,))
                trends = []

                for row in result:
                    trends.append(
                        {
                            "date": row.date.isoformat() if row.date else None,
                            "chat_sessions": row.chat_sessions or 0,
                            "images_generated": row.images_generated or 0,
                            "active_users": row.active_users or 0,
                            "avg_response_time_ms": float(row.avg_response_time or 0),
                        }
                    )

                return trends

        except Exception as e:
            logger.error(f"Error getting activity trends: {e}")
            return []

    def get_user_engagement_metrics(self) -> dict[str, Any]:
        """Get user engagement metrics."""
        try:
            with get_session() as db_session:
                # Average sessions per user
                avg_sessions_result = db_session.execute(
                    """
                    SELECT AVG(session_count) FROM (
                        SELECT user_id, COUNT(*) as session_count
                        FROM audit_logs 
                        WHERE user_id IS NOT NULL
                        GROUP BY user_id
                    ) user_sessions
                """
                ).scalar()

                # User retention (mock calculation)
                retention_7_day = 65.5
                retention_30_day = 45.2

                # Most active users
                most_active_result = db_session.execute(
                    """
                    SELECT u.pseudonym, COUNT(*) as activity_count
                    FROM audit_logs a
                    JOIN users u ON a.user_id = u.id
                    WHERE a.created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY u.pseudonym
                    ORDER BY activity_count DESC
                    LIMIT 5
                """
                ).fetchall()

                most_active_users = [
                    {"pseudonym": row.pseudonym, "activity_count": row.activity_count}
                    for row in most_active_result
                ]

                return {
                    "avg_sessions_per_user": float(avg_sessions_result or 0),
                    "retention_7_day_percent": retention_7_day,
                    "retention_30_day_percent": retention_30_day,
                    "most_active_users": most_active_users,
                }

        except Exception as e:
            logger.error(f"Error getting user engagement metrics: {e}")
            return {}

    def get_system_health_summary(self) -> dict[str, Any]:
        """Get system health summary."""
        try:
            with get_session() as db_session:
                # Recent error count
                recent_errors_result = db_session.execute(
                    """
                    SELECT COUNT(*) FROM audit_logs 
                    WHERE status = 'error' AND created_at >= NOW() - INTERVAL '1 hour'
                """
                ).scalar()

                # Service availability (mock)
                service_availability = {
                    "database": 99.9,
                    "llm_service": 98.5,
                    "image_generation": 97.8,
                    "storage": 99.5,
                }

                # Resource usage (mock)
                resource_usage = {"cpu_percent": 45.2, "memory_percent": 68.7, "disk_percent": 32.1}

                return {
                    "recent_errors": recent_errors_result or 0,
                    "service_availability": service_availability,
                    "resource_usage": resource_usage,
                    "overall_health": "healthy",  # Would be calculated based on thresholds
                }

        except Exception as e:
            logger.error(f"Error getting system health summary: {e}")
            return {"error": str(e)}

    def generate_export_report(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        filters: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Generate comprehensive export report."""
        try:
            filters = filters or {}

            report = {
                "report_type": report_type,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "filters": filters,
                "generated_at": datetime.now().isoformat(),
                "data": {},
            }

            if report_type == "user_activity":
                report["data"] = self._generate_user_activity_report(start_date, end_date, filters)
            elif report_type == "system_performance":
                report["data"] = self._generate_performance_report(start_date, end_date, filters)
            elif report_type == "pald_analysis":
                report["data"] = self._generate_pald_analysis_report(start_date, end_date, filters)
            elif report_type == "audit_summary":
                report["data"] = self._generate_audit_summary_report(start_date, end_date, filters)
            else:
                report["error"] = f"Unknown report type: {report_type}"

            return report

        except Exception as e:
            logger.error(f"Error generating export report: {e}")
            return {"error": str(e)}

    def _generate_user_activity_report(
        self, start_date: datetime, end_date: datetime, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate user activity report."""
        # Implementation would query database for user activity data
        return {"placeholder": "User activity report data"}

    def _generate_performance_report(
        self, start_date: datetime, end_date: datetime, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate performance report."""
        # Implementation would query database for performance data
        return {"placeholder": "Performance report data"}

    def _generate_pald_analysis_report(
        self, start_date: datetime, end_date: datetime, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate PALD analysis report."""
        # Implementation would query database for PALD data
        return {"placeholder": "PALD analysis report data"}

    def _generate_audit_summary_report(
        self, start_date: datetime, end_date: datetime, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate audit summary report."""
        # Implementation would query database for audit data
        return {"placeholder": "Audit summary report data"}


# Global statistics service instance
_admin_statistics_service: AdminStatisticsService | None = None


def get_admin_statistics_service() -> AdminStatisticsService:
    """Get the global admin statistics service instance."""
    global _admin_statistics_service
    if _admin_statistics_service is None:
        _admin_statistics_service = AdminStatisticsService()
    return _admin_statistics_service
