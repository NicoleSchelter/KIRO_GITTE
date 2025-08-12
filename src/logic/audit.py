"""
Audit Logic Layer for GITTE system.
Handles business logic for audit logging, compliance monitoring, and reporting.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from src.services.audit_service import AuditService, get_audit_service

logger = logging.getLogger(__name__)


@dataclass
class ComplianceReport:
    """Compliance report for audit logging."""

    period_start: datetime
    period_end: datetime
    total_interactions: int
    logged_interactions: int
    completeness_percentage: float
    missing_logs: list[str]
    compliance_status: str
    recommendations: list[str]


@dataclass
class AuditSummary:
    """Summary of audit activities."""

    total_logs: int
    operations_breakdown: dict[str, int]
    models_breakdown: dict[str, int]
    status_breakdown: dict[str, int]
    average_latency_ms: float
    total_tokens_used: int
    most_active_users: list[tuple[UUID, int]]
    error_rate: float


class AuditLogic:
    """
    Logic layer for audit operations.
    Handles audit compliance monitoring, reporting, and analysis.
    """

    def __init__(self, audit_service: AuditService | None = None):
        """
        Initialize audit logic.

        Args:
            audit_service: Audit service instance
        """
        self.audit_service = audit_service or get_audit_service()

    def generate_compliance_report(
        self, start_date: datetime, end_date: datetime, target_completeness: float = 99.0
    ) -> ComplianceReport:
        """
        Generate compliance report for audit logging.

        Args:
            start_date: Report period start date
            end_date: Report period end date
            target_completeness: Target completeness percentage

        Returns:
            ComplianceReport: Compliance report
        """
        logger.info(f"Generating compliance report for period {start_date} to {end_date}")

        try:
            # Get audit statistics for the period
            stats = self.audit_service.get_audit_statistics(start_date, end_date)

            total_interactions = stats.get("total_logs", 0)
            completeness_percentage = stats.get("completeness_percentage", 0.0)

            # Identify missing logs (logs that are not finalized)
            from src.data.schemas import AuditLogFilters

            filters = AuditLogFilters(
                start_date=start_date, end_date=end_date, status="in_progress"  # Non-finalized logs
            )

            pending_logs = self.audit_service.repository.get_filtered(filters)
            missing_logs = [f"Request {log.request_id} - {log.operation}" for log in pending_logs]

            # Determine compliance status
            if completeness_percentage >= target_completeness:
                compliance_status = "COMPLIANT"
                recommendations = ["Maintain current audit logging practices"]
            elif completeness_percentage >= 90.0:
                compliance_status = "MOSTLY_COMPLIANT"
                recommendations = [
                    "Review and finalize pending audit logs",
                    "Investigate incomplete operations",
                ]
            else:
                compliance_status = "NON_COMPLIANT"
                recommendations = [
                    "Urgent: Review audit logging implementation",
                    "Investigate system failures causing incomplete logs",
                    "Implement additional monitoring for audit completeness",
                ]

            report = ComplianceReport(
                period_start=start_date,
                period_end=end_date,
                total_interactions=total_interactions,
                logged_interactions=int(total_interactions * completeness_percentage / 100),
                completeness_percentage=completeness_percentage,
                missing_logs=missing_logs,
                compliance_status=compliance_status,
                recommendations=recommendations,
            )

            logger.info(
                f"Compliance report generated: {compliance_status} ({completeness_percentage:.1f}%)"
            )
            return report

        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            raise

    def generate_audit_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        include_user_breakdown: bool = True,
    ) -> AuditSummary:
        """
        Generate comprehensive audit summary.

        Args:
            start_date: Summary period start date
            end_date: Summary period end date
            include_user_breakdown: Whether to include user activity breakdown

        Returns:
            AuditSummary: Audit summary
        """
        logger.info(f"Generating audit summary for period {start_date} to {end_date}")

        try:
            # Get basic statistics
            stats = self.audit_service.get_audit_statistics(start_date, end_date)

            # Get detailed breakdowns
            from src.data.schemas import AuditLogFilters

            filters = AuditLogFilters(start_date=start_date, end_date=end_date)
            logs = self.audit_service.repository.get_filtered(filters)

            # Calculate user activity if requested
            most_active_users = []
            if include_user_breakdown:
                user_activity = {}
                for log in logs:
                    if log.user_id:
                        user_activity[log.user_id] = user_activity.get(log.user_id, 0) + 1

                # Sort by activity and get top 10
                most_active_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]

            # Calculate error rate
            total_logs = len(logs)
            failed_logs = len([log for log in logs if log.status == "failed"])
            error_rate = (failed_logs / total_logs * 100) if total_logs > 0 else 0.0

            # Calculate total tokens
            total_tokens = sum(log.token_usage or 0 for log in logs)

            summary = AuditSummary(
                total_logs=stats.get("total_logs", 0),
                operations_breakdown=stats.get("operation_breakdown", {}),
                models_breakdown=self._get_models_breakdown(logs),
                status_breakdown=stats.get("status_breakdown", {}),
                average_latency_ms=stats.get("average_latency_ms", 0.0),
                total_tokens_used=total_tokens,
                most_active_users=most_active_users,
                error_rate=error_rate,
            )

            logger.info(
                f"Audit summary generated: {summary.total_logs} logs, {error_rate:.1f}% error rate"
            )
            return summary

        except Exception as e:
            logger.error(f"Failed to generate audit summary: {e}")
            raise

    def analyze_conversation_patterns(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """
        Analyze conversation patterns and threading.

        Args:
            start_date: Analysis period start date
            end_date: Analysis period end date

        Returns:
            Dict: Conversation pattern analysis
        """
        logger.info("Analyzing conversation patterns")

        try:
            from src.data.schemas import AuditLogFilters

            filters = AuditLogFilters(start_date=start_date, end_date=end_date)
            logs = self.audit_service.repository.get_filtered(filters)

            # Identify conversation threads
            root_conversations = [log for log in logs if log.parent_log_id is None]
            threaded_conversations = [log for log in logs if log.parent_log_id is not None]

            # Calculate conversation metrics
            conversation_lengths = []
            for root_log in root_conversations:
                thread = self.audit_service.get_conversation_thread(root_log.id)
                conversation_lengths.append(len(thread))

            avg_conversation_length = (
                sum(conversation_lengths) / len(conversation_lengths) if conversation_lengths else 0
            )
            max_conversation_length = max(conversation_lengths) if conversation_lengths else 0

            # Analyze operation sequences
            operation_sequences = {}
            for root_log in root_conversations:
                thread = self.audit_service.get_conversation_thread(root_log.id)
                sequence = " -> ".join([log.operation for log in thread])
                operation_sequences[sequence] = operation_sequences.get(sequence, 0) + 1

            # Get most common sequences
            common_sequences = sorted(
                operation_sequences.items(), key=lambda x: x[1], reverse=True
            )[:10]

            analysis = {
                "total_conversations": len(root_conversations),
                "threaded_interactions": len(threaded_conversations),
                "average_conversation_length": avg_conversation_length,
                "max_conversation_length": max_conversation_length,
                "common_operation_sequences": common_sequences,
                "threading_usage_percentage": (
                    (len(threaded_conversations) / len(logs) * 100) if logs else 0
                ),
            }

            logger.info(
                f"Conversation analysis completed: {len(root_conversations)} conversations analyzed"
            )
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze conversation patterns: {e}")
            raise

    def validate_audit_integrity(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """
        Validate audit log integrity and consistency.

        Args:
            start_date: Validation period start date
            end_date: Validation period end date

        Returns:
            Dict: Integrity validation results
        """
        logger.info("Validating audit log integrity")

        try:
            from src.data.schemas import AuditLogFilters

            filters = AuditLogFilters(start_date=start_date, end_date=end_date)
            logs = self.audit_service.repository.get_filtered(filters)

            issues = []
            warnings = []

            # Check for orphaned child logs
            for log in logs:
                if log.parent_log_id:
                    parent = self.audit_service.repository.get_by_id(log.parent_log_id)
                    if not parent:
                        issues.append(
                            f"Orphaned log {log.id}: parent {log.parent_log_id} not found"
                        )

            # Check for incomplete logs
            incomplete_logs = [log for log in logs if log.status in ["initialized", "in_progress"]]
            if incomplete_logs:
                old_threshold = datetime.utcnow() - timedelta(hours=1)
                old_incomplete = [log for log in incomplete_logs if log.created_at < old_threshold]
                if old_incomplete:
                    warnings.append(f"{len(old_incomplete)} logs incomplete for over 1 hour")

            # Check for missing required fields
            for log in logs:
                if not log.request_id:
                    issues.append(f"Log {log.id}: missing request_id")
                if not log.operation:
                    issues.append(f"Log {log.id}: missing operation")

            # Check for duplicate request IDs
            request_ids = [log.request_id for log in logs if log.request_id]
            duplicate_request_ids = set([rid for rid in request_ids if request_ids.count(rid) > 1])
            if duplicate_request_ids:
                warnings.append(f"Duplicate request IDs found: {list(duplicate_request_ids)}")

            integrity_score = max(0, 100 - len(issues) * 10 - len(warnings) * 5)

            validation_result = {
                "integrity_score": integrity_score,
                "total_logs_checked": len(logs),
                "issues_found": len(issues),
                "warnings_found": len(warnings),
                "issues": issues,
                "warnings": warnings,
                "validation_timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Integrity validation completed: score {integrity_score}/100")
            return validation_result

        except Exception as e:
            logger.error(f"Failed to validate audit integrity: {e}")
            raise

    def _get_models_breakdown(self, logs: list) -> dict[str, int]:
        """Get breakdown of models used in audit logs."""
        models_breakdown = {}
        for log in logs:
            if log.model_used:
                models_breakdown[log.model_used] = models_breakdown.get(log.model_used, 0) + 1
        return models_breakdown


# Global audit logic instance
_audit_logic: AuditLogic | None = None


def get_audit_logic() -> AuditLogic:
    """Get the global audit logic instance."""
    global _audit_logic
    if _audit_logic is None:
        _audit_logic = AuditLogic()
    return _audit_logic


def set_audit_logic(logic: AuditLogic) -> None:
    """Set the global audit logic instance (useful for testing)."""
    global _audit_logic
    _audit_logic = logic
