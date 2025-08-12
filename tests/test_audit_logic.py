"""
Tests for audit logic layer.
Tests business logic for audit logging, compliance monitoring, and reporting.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.logic.audit import (
    AuditLogic,
    AuditSummary,
    ComplianceReport,
    get_audit_logic,
    set_audit_logic,
)
from src.services.audit_service import AuditService


class TestComplianceReport:
    """Test compliance report data class."""

    def test_compliance_report_creation(self):
        """Test creating compliance report."""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        report = ComplianceReport(
            period_start=start_date,
            period_end=end_date,
            total_interactions=1000,
            logged_interactions=995,
            completeness_percentage=99.5,
            missing_logs=["req-123", "req-456"],
            compliance_status="COMPLIANT",
            recommendations=["Maintain current practices"],
        )

        assert report.period_start == start_date
        assert report.period_end == end_date
        assert report.total_interactions == 1000
        assert report.logged_interactions == 995
        assert report.completeness_percentage == 99.5
        assert report.missing_logs == ["req-123", "req-456"]
        assert report.compliance_status == "COMPLIANT"
        assert report.recommendations == ["Maintain current practices"]


class TestAuditSummary:
    """Test audit summary data class."""

    def test_audit_summary_creation(self):
        """Test creating audit summary."""
        user_id1 = uuid4()
        user_id2 = uuid4()

        summary = AuditSummary(
            total_logs=500,
            operations_breakdown={"llm_generation": 300, "image_generation": 200},
            models_breakdown={"llama3.2": 250, "mistral": 150, "stable-diffusion": 100},
            status_breakdown={"COMPLETED": 480, "FAILED": 20},
            average_latency_ms=1250.5,
            total_tokens_used=25000,
            most_active_users=[(user_id1, 150), (user_id2, 120)],
            error_rate=4.0,
        )

        assert summary.total_logs == 500
        assert summary.operations_breakdown["llm_generation"] == 300
        assert summary.models_breakdown["llama3.2"] == 250
        assert summary.status_breakdown["COMPLETED"] == 480
        assert summary.average_latency_ms == 1250.5
        assert summary.total_tokens_used == 25000
        assert summary.most_active_users[0] == (user_id1, 150)
        assert summary.error_rate == 4.0


class TestAuditLogic:
    """Test audit logic."""

    def test_audit_logic_creation(self):
        """Test creating audit logic with service."""
        mock_audit_service = Mock(spec=AuditService)
        logic = AuditLogic(audit_service=mock_audit_service)

        assert logic.audit_service == mock_audit_service

    def test_audit_logic_default_service(self):
        """Test creating audit logic with default service."""
        with patch("src.logic.audit.get_audit_service") as mock_get_service:
            mock_audit_service = Mock(spec=AuditService)
            mock_get_service.return_value = mock_audit_service

            logic = AuditLogic()

            assert logic.audit_service == mock_audit_service

    def test_generate_compliance_report_compliant(self):
        """Test generating compliance report for compliant system."""
        mock_audit_service = Mock(spec=AuditService)
        mock_audit_service.get_audit_statistics.return_value = {
            "total_logs": 1000,
            "completeness_percentage": 99.8,
        }
        mock_audit_service.repository = Mock()
        mock_audit_service.repository.get_filtered.return_value = []

        logic = AuditLogic(audit_service=mock_audit_service)

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        report = logic.generate_compliance_report(start_date, end_date, target_completeness=99.0)

        assert report.period_start == start_date
        assert report.period_end == end_date
        assert report.total_interactions == 1000
        assert report.logged_interactions == 998  # 1000 * 99.8 / 100
        assert report.completeness_percentage == 99.8
        assert report.compliance_status == "COMPLIANT"
        assert "Maintain current audit logging practices" in report.recommendations
        assert report.missing_logs == []

    def test_generate_compliance_report_mostly_compliant(self):
        """Test generating compliance report for mostly compliant system."""
        mock_audit_service = Mock(spec=AuditService)
        mock_audit_service.get_audit_statistics.return_value = {
            "total_logs": 1000,
            "completeness_percentage": 95.0,
        }

        # Mock pending logs
        pending_log1 = Mock()
        pending_log1.request_id = "req-123"
        pending_log1.operation = "llm_generation"
        pending_log2 = Mock()
        pending_log2.request_id = "req-456"
        pending_log2.operation = "image_generation"

        mock_audit_service.repository = Mock()
        mock_audit_service.repository.get_filtered.return_value = [pending_log1, pending_log2]

        logic = AuditLogic(audit_service=mock_audit_service)

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        report = logic.generate_compliance_report(start_date, end_date, target_completeness=99.0)

        assert report.compliance_status == "MOSTLY_COMPLIANT"
        assert "Review and finalize pending audit logs" in report.recommendations
        assert "Request req-123 - llm_generation" in report.missing_logs
        assert "Request req-456 - image_generation" in report.missing_logs

    def test_generate_compliance_report_non_compliant(self):
        """Test generating compliance report for non-compliant system."""
        mock_audit_service = Mock(spec=AuditService)
        mock_audit_service.get_audit_statistics.return_value = {
            "total_logs": 1000,
            "completeness_percentage": 75.0,
        }
        mock_audit_service.repository = Mock()
        mock_audit_service.repository.get_filtered.return_value = []

        logic = AuditLogic(audit_service=mock_audit_service)

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        report = logic.generate_compliance_report(start_date, end_date, target_completeness=99.0)

        assert report.compliance_status == "NON_COMPLIANT"
        assert "Urgent: Review audit logging implementation" in report.recommendations
        assert "Investigate system failures causing incomplete logs" in report.recommendations

    def test_generate_audit_summary_with_user_breakdown(self):
        """Test generating audit summary with user breakdown."""
        mock_audit_service = Mock(spec=AuditService)
        mock_audit_service.get_audit_statistics.return_value = {
            "total_logs": 500,
            "operation_breakdown": {"llm_generation": 300, "image_generation": 200},
            "status_breakdown": {"COMPLETED": 480, "FAILED": 20},
            "average_latency_ms": 1250.5,
        }

        # Mock audit logs for detailed analysis
        user_id1 = uuid4()
        user_id2 = uuid4()
        user_id3 = uuid4()

        logs = []
        # Create logs with different users and models
        for i in range(500):
            log = Mock()
            log.user_id = user_id1 if i < 200 else (user_id2 if i < 350 else user_id3)
            log.model_used = (
                "llama3.2" if i < 250 else ("mistral" if i < 400 else "stable-diffusion")
            )
            log.status = "completed" if i < 480 else "failed"
            log.token_usage = 50 + (i % 20)
            logs.append(log)

        mock_audit_service.repository = Mock()
        mock_audit_service.repository.get_filtered.return_value = logs

        logic = AuditLogic(audit_service=mock_audit_service)

        summary = logic.generate_audit_summary(include_user_breakdown=True)

        assert summary.total_logs == 500
        assert summary.operations_breakdown == {"llm_generation": 300, "image_generation": 200}
        assert summary.status_breakdown == {"COMPLETED": 480, "FAILED": 20}
        assert summary.average_latency_ms == 1250.5
        assert summary.error_rate == 4.0  # 20/500 * 100
        assert len(summary.most_active_users) <= 10  # Top 10 users
        assert summary.most_active_users[0] == (user_id1, 200)  # Most active user
        assert summary.total_tokens_used > 0

    def test_generate_audit_summary_without_user_breakdown(self):
        """Test generating audit summary without user breakdown."""
        mock_audit_service = Mock(spec=AuditService)
        mock_audit_service.get_audit_statistics.return_value = {
            "total_logs": 100,
            "operation_breakdown": {"llm_generation": 100},
            "status_breakdown": {"COMPLETED": 100},
            "average_latency_ms": 1000.0,
        }
        mock_audit_service.repository = Mock()
        mock_audit_service.repository.get_filtered.return_value = []

        logic = AuditLogic(audit_service=mock_audit_service)

        summary = logic.generate_audit_summary(include_user_breakdown=False)

        assert summary.total_logs == 100
        assert summary.most_active_users == []
        assert summary.error_rate == 0.0

    def test_analyze_conversation_patterns(self):
        """Test analyzing conversation patterns."""
        mock_audit_service = Mock(spec=AuditService)

        # Create mock conversation logs
        root_id1 = uuid4()
        root_id2 = uuid4()
        child_id1 = uuid4()
        child_id2 = uuid4()

        # Root conversations
        root_log1 = Mock()
        root_log1.id = root_id1
        root_log1.parent_log_id = None
        root_log1.operation = "start_conversation"

        root_log2 = Mock()
        root_log2.id = root_id2
        root_log2.parent_log_id = None
        root_log2.operation = "start_conversation"

        # Child conversations
        child_log1 = Mock()
        child_log1.id = child_id1
        child_log1.parent_log_id = root_id1
        child_log1.operation = "continue_conversation"

        child_log2 = Mock()
        child_log2.id = child_id2
        child_log2.parent_log_id = root_id2
        child_log2.operation = "end_conversation"

        all_logs = [root_log1, root_log2, child_log1, child_log2]
        mock_audit_service.repository = Mock()
        mock_audit_service.repository.get_filtered.return_value = all_logs

        # Mock conversation threads
        def mock_get_thread(log_id):
            if log_id == root_id1:
                thread1_log1 = Mock()
                thread1_log1.operation = "start_conversation"
                thread1_log2 = Mock()
                thread1_log2.operation = "continue_conversation"
                return [thread1_log1, thread1_log2]
            elif log_id == root_id2:
                thread2_log1 = Mock()
                thread2_log1.operation = "start_conversation"
                thread2_log2 = Mock()
                thread2_log2.operation = "end_conversation"
                return [thread2_log1, thread2_log2]
            return []

        mock_audit_service.get_conversation_thread.side_effect = mock_get_thread

        logic = AuditLogic(audit_service=mock_audit_service)

        analysis = logic.analyze_conversation_patterns()

        assert analysis["total_conversations"] == 2
        assert analysis["threaded_interactions"] == 2
        assert analysis["average_conversation_length"] == 2.0
        assert analysis["max_conversation_length"] == 2
        assert analysis["threading_usage_percentage"] == 50.0  # 2/4 * 100
        assert len(analysis["common_operation_sequences"]) > 0

    def test_validate_audit_integrity_clean_logs(self):
        """Test audit integrity validation with clean logs."""
        mock_audit_service = Mock(spec=AuditService)

        # Create clean audit logs
        logs = []
        for i in range(10):
            log = Mock()
            log.id = uuid4()
            log.request_id = f"req-{i}"
            log.operation = "llm_generation"
            log.parent_log_id = None
            log.status = "finalized"
            log.created_at = datetime.utcnow() - timedelta(minutes=30)
            logs.append(log)

        mock_audit_service.repository = Mock()
        mock_audit_service.repository.get_filtered.return_value = logs
        mock_audit_service.repository.get_by_id.return_value = None  # No parent lookups needed

        logic = AuditLogic(audit_service=mock_audit_service)

        validation = logic.validate_audit_integrity()

        assert validation["integrity_score"] == 100
        assert validation["total_logs_checked"] == 10
        assert validation["issues_found"] == 0
        assert validation["warnings_found"] == 0
        assert validation["issues"] == []
        assert validation["warnings"] == []

    def test_validate_audit_integrity_with_issues(self):
        """Test audit integrity validation with issues."""
        mock_audit_service = Mock(spec=AuditService)

        # Create problematic audit logs
        orphaned_log = Mock()
        orphaned_log.id = uuid4()
        orphaned_log.request_id = "req-orphaned"
        orphaned_log.operation = "llm_generation"
        orphaned_log.parent_log_id = uuid4()  # Non-existent parent
        orphaned_log.status = "completed"
        orphaned_log.created_at = datetime.utcnow() - timedelta(minutes=30)

        incomplete_log = Mock()
        incomplete_log.id = uuid4()
        incomplete_log.request_id = "req-incomplete"
        incomplete_log.operation = "image_generation"
        incomplete_log.parent_log_id = None
        incomplete_log.status = "in_progress"
        incomplete_log.created_at = datetime.utcnow() - timedelta(hours=2)  # Old incomplete

        missing_request_id_log = Mock()
        missing_request_id_log.id = uuid4()
        missing_request_id_log.request_id = None  # Missing request ID
        missing_request_id_log.operation = "llm_generation"
        missing_request_id_log.parent_log_id = None
        missing_request_id_log.status = "completed"
        missing_request_id_log.created_at = datetime.utcnow() - timedelta(minutes=30)

        duplicate_log1 = Mock()
        duplicate_log1.id = uuid4()
        duplicate_log1.request_id = "duplicate-req"
        duplicate_log1.operation = "llm_generation"
        duplicate_log1.parent_log_id = None
        duplicate_log1.status = "completed"
        duplicate_log1.created_at = datetime.utcnow() - timedelta(minutes=30)

        duplicate_log2 = Mock()
        duplicate_log2.id = uuid4()
        duplicate_log2.request_id = "duplicate-req"  # Duplicate request ID
        duplicate_log2.operation = "llm_generation"
        duplicate_log2.parent_log_id = None
        duplicate_log2.status = "completed"
        duplicate_log2.created_at = datetime.utcnow() - timedelta(minutes=25)

        logs = [
            orphaned_log,
            incomplete_log,
            missing_request_id_log,
            duplicate_log1,
            duplicate_log2,
        ]
        mock_audit_service.repository = Mock()
        mock_audit_service.repository.get_filtered.return_value = logs
        mock_audit_service.repository.get_by_id.return_value = None  # Parent not found

        logic = AuditLogic(audit_service=mock_audit_service)

        validation = logic.validate_audit_integrity()

        assert validation["integrity_score"] < 100
        assert validation["total_logs_checked"] == 5
        assert validation["issues_found"] >= 2  # Orphaned log + missing request ID
        assert validation["warnings_found"] >= 2  # Old incomplete + duplicates
        assert any("Orphaned log" in issue for issue in validation["issues"])
        assert any("missing request_id" in issue for issue in validation["issues"])
        assert any("incomplete for over 1 hour" in warning for warning in validation["warnings"])
        assert any("Duplicate request IDs" in warning for warning in validation["warnings"])

    def test_get_models_breakdown(self):
        """Test getting models breakdown from logs."""
        mock_audit_service = Mock(spec=AuditService)
        logic = AuditLogic(audit_service=mock_audit_service)

        # Create logs with different models
        logs = []
        models = ["llama3.2", "llama3.2", "mistral", "llama3.2", "stable-diffusion", "mistral"]
        for model in models:
            log = Mock()
            log.model_used = model
            logs.append(log)

        # Add log without model
        log_no_model = Mock()
        log_no_model.model_used = None
        logs.append(log_no_model)

        breakdown = logic._get_models_breakdown(logs)

        assert breakdown["llama3.2"] == 3
        assert breakdown["mistral"] == 2
        assert breakdown["stable-diffusion"] == 1
        assert None not in breakdown  # Should not count None models


class TestAuditLogicGlobalFunctions:
    """Test global audit logic functions."""

    def test_get_audit_logic_singleton(self):
        """Test that get_audit_logic returns singleton."""
        logic1 = get_audit_logic()
        logic2 = get_audit_logic()

        assert logic1 is logic2

    def test_set_audit_logic(self):
        """Test setting custom audit logic."""
        mock_audit_service = Mock(spec=AuditService)
        custom_logic = AuditLogic(audit_service=mock_audit_service)
        set_audit_logic(custom_logic)

        retrieved_logic = get_audit_logic()
        assert retrieved_logic is custom_logic

        # Reset to None for other tests
        set_audit_logic(None)


@pytest.fixture
def mock_audit_service():
    """Create mock audit service for testing."""
    service = Mock(spec=AuditService)
    service.repository = Mock()
    return service


@pytest.fixture
def sample_audit_logs():
    """Create sample audit logs for testing."""
    logs = []
    for i in range(10):
        log = Mock()
        log.id = uuid4()
        log.request_id = f"req-{i}"
        log.operation = "llm_generation" if i % 2 == 0 else "image_generation"
        log.model_used = "llama3.2" if i < 5 else "mistral"
        log.user_id = uuid4()
        log.status = "COMPLETED" if i < 9 else "FAILED"
        log.token_usage = 50 + i * 5
        log.latency_ms = 1000 + i * 100
        log.parent_log_id = None
        log.created_at = datetime.utcnow() - timedelta(minutes=i)
        logs.append(log)
    return logs
