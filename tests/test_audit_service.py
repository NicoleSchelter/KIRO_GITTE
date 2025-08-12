"""
Tests for audit service layer.
Tests comprehensive audit logging with write-ahead logging (WAL) for all AI interactions.
"""

import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.data.models import AuditLogStatus
from src.data.repositories import AuditLogRepository
from src.services.audit_service import (
    AuditLogEntry,
    AuditService,
    create_audit_context,
    export_audit_data,
    get_audit_service,
    get_audit_statistics,
    set_audit_service,
)


class TestAuditLogEntry:
    """Test audit log entry context manager."""

    def test_audit_log_entry_creation(self):
        """Test creating audit log entry."""
        request_id = str(uuid4())
        user_id = uuid4()

        entry = AuditLogEntry(
            request_id=request_id,
            operation="llm_generation",
            user_id=user_id,
            model_used="llama3.2",
            parameters={"temperature": 0.7},
            parent_log_id=None,
        )

        assert entry.request_id == request_id
        assert entry.operation == "llm_generation"
        assert entry.user_id == user_id
        assert entry.model_used == "llama3.2"
        assert entry.parameters == {"temperature": 0.7}
        assert entry.parent_log_id is None
        assert entry.audit_id is None
        assert entry._finalized is False

    def test_audit_log_entry_context_manager_success(self):
        """Test audit log entry context manager with successful operation."""
        mock_audit_service = Mock(spec=AuditService)
        audit_id = uuid4()
        mock_audit_service.initialize_log.return_value = audit_id

        entry = AuditLogEntry(
            request_id=str(uuid4()), operation="test_operation", audit_service=mock_audit_service
        )

        with entry:
            entry.set_input({"prompt": "test prompt"})
            entry.set_output({"response": "test response"})

        # Verify initialization and finalization were called
        mock_audit_service.initialize_log.assert_called_once()
        mock_audit_service.finalize_log.assert_called_once_with(
            audit_id=audit_id,
            input_data={"prompt": "test prompt"},
            output_data={"response": "test response"},
            status=AuditLogStatus.COMPLETED,
        )
        assert entry._finalized is True

    def test_audit_log_entry_context_manager_exception(self):
        """Test audit log entry context manager with exception."""
        mock_audit_service = Mock(spec=AuditService)
        audit_id = uuid4()
        mock_audit_service.initialize_log.return_value = audit_id

        entry = AuditLogEntry(
            request_id=str(uuid4()), operation="test_operation", audit_service=mock_audit_service
        )

        with pytest.raises(ValueError), entry:
            entry.set_input({"prompt": "test prompt"})
            raise ValueError("Test error")

        # Verify finalization was called with error
        mock_audit_service.finalize_log.assert_called_once_with(
            audit_id=audit_id,
            input_data={"prompt": "test prompt"},
            output_data=None,
            error_message="Test error",
            status=AuditLogStatus.FAILED,
        )

    def test_audit_log_entry_set_input_updates_service(self):
        """Test that setting input updates the audit service."""
        mock_audit_service = Mock(spec=AuditService)
        audit_id = uuid4()
        mock_audit_service.initialize_log.return_value = audit_id

        entry = AuditLogEntry(
            request_id=str(uuid4()), operation="test_operation", audit_service=mock_audit_service
        )
        entry.audit_id = audit_id

        input_data = {"prompt": "test prompt"}
        entry.set_input(input_data)

        assert entry.input_data == input_data
        mock_audit_service.update_log.assert_called_once_with(
            audit_id=audit_id, input_data=input_data, status=AuditLogStatus.IN_PROGRESS
        )

    def test_audit_log_entry_add_metadata(self):
        """Test adding metadata to audit log entry."""
        mock_audit_service = Mock(spec=AuditService)
        audit_id = uuid4()

        entry = AuditLogEntry(
            request_id=str(uuid4()),
            operation="test_operation",
            parameters={"initial": "value"},
            audit_service=mock_audit_service,
        )
        entry.audit_id = audit_id

        entry.add_metadata(device="cuda", batch_size=4)

        assert entry.parameters == {"initial": "value", "device": "cuda", "batch_size": 4}
        mock_audit_service.update_log.assert_called_once_with(
            audit_id=audit_id, parameters={"initial": "value", "device": "cuda", "batch_size": 4}
        )


class TestAuditService:
    """Test audit service."""

    def test_audit_service_creation(self):
        """Test creating audit service."""
        mock_session = Mock()
        service = AuditService(db_session=mock_session)

        assert service.db_session == mock_session
        assert service._own_session is False
        assert isinstance(service.repository, AuditLogRepository)

    def test_audit_service_default_session(self):
        """Test creating audit service with default session."""
        with patch("src.data.database.get_session_sync") as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value = mock_session

            service = AuditService()

            assert service.db_session == mock_session
            assert service._own_session is True

    def test_initialize_log_success(self):
        """Test successful log initialization."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)

        audit_id = uuid4()
        mock_audit_log = Mock()
        mock_audit_log.id = audit_id
        mock_repository.create.return_value = mock_audit_log

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        result = service.initialize_log(
            request_id="test-request",
            operation="llm_generation",
            user_id=uuid4(),
            model_used="llama3.2",
            parameters={"temperature": 0.7},
        )

        assert result == audit_id
        mock_repository.create.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_initialize_log_failure(self):
        """Test log initialization failure."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)
        mock_repository.create.return_value = None

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        result = service.initialize_log(request_id="test-request", operation="llm_generation")

        assert result is None
        mock_session.rollback.assert_not_called()  # No rollback on None return

    def test_initialize_log_exception(self):
        """Test log initialization with exception."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)
        mock_repository.create.side_effect = Exception("Database error")

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        result = service.initialize_log(request_id="test-request", operation="llm_generation")

        assert result is None
        mock_session.rollback.assert_called_once()

    def test_update_log_success(self):
        """Test successful log update."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)

        audit_id = uuid4()
        mock_audit_log = Mock()
        mock_repository.update.return_value = mock_audit_log

        # Mock current log for parameter merging
        current_log = Mock()
        current_log.parameters = {"existing": "value"}
        mock_repository.get_by_id.return_value = current_log

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        result = service.update_log(
            audit_id=audit_id,
            input_data={"prompt": "test"},
            output_data={"response": "test response"},
            token_usage=50,
            latency_ms=1500,
            status=AuditLogStatus.COMPLETED,
            parameters={"new": "parameter"},
        )

        assert result is True
        mock_repository.update.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify parameter merging
        update_call_args = mock_repository.update.call_args
        update_data = update_call_args[0][1]  # Second argument is the AuditLogUpdate object
        assert update_data.parameters["existing"] == "value"
        assert update_data.parameters["new"] == "parameter"

    def test_update_log_failure(self):
        """Test log update failure."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)
        mock_repository.update.return_value = None

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        result = service.update_log(audit_id=uuid4(), input_data={"prompt": "test"})

        assert result is False

    def test_finalize_log_success(self):
        """Test successful log finalization."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)

        audit_id = uuid4()

        # Mock current log for latency calculation
        current_log = Mock()
        current_log.created_at = datetime.utcnow() - timedelta(seconds=2)
        mock_repository.get_by_id.return_value = current_log

        mock_repository.update.return_value = Mock()
        mock_repository.finalize.return_value = True

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        result = service.finalize_log(
            audit_id=audit_id,
            input_data={"prompt": "test"},
            output_data={"response": "test response"},
            status=AuditLogStatus.COMPLETED,
        )

        assert result is True
        mock_repository.update.assert_called_once()
        mock_repository.finalize.assert_called_once_with(audit_id)
        mock_session.commit.assert_called()

    def test_finalize_log_with_provided_latency(self):
        """Test log finalization with provided latency."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)

        audit_id = uuid4()
        mock_repository.update.return_value = Mock()
        mock_repository.finalize.return_value = True

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        result = service.finalize_log(
            audit_id=audit_id, latency_ms=2500, status=AuditLogStatus.COMPLETED
        )

        assert result is True
        # Should not call get_by_id since latency was provided
        mock_repository.get_by_id.assert_not_called()

    def test_create_audit_context_success(self):
        """Test creating audit context."""
        mock_session = Mock()
        service = AuditService(db_session=mock_session)

        with patch.object(service, "initialize_log") as mock_init:
            with patch.object(service, "finalize_log") as mock_finalize:
                audit_id = uuid4()
                mock_init.return_value = audit_id

                with service.create_audit_context(
                    operation="test_operation", user_id=uuid4(), model_used="test_model"
                ) as entry:
                    # Use the entry as a context manager to trigger __enter__ and __exit__
                    with entry:
                        entry.set_input({"test": "input"})
                        entry.set_output({"test": "output"})

                # The initialize_log is called in AuditLogEntry.__enter__
                mock_init.assert_called_once()
                # The finalize_log is called in AuditLogEntry.__exit__
                mock_finalize.assert_called_once()

    def test_get_conversation_thread(self):
        """Test getting conversation thread."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        # Create mock conversation thread
        root_id = uuid4()
        child1_id = uuid4()
        child2_id = uuid4()

        root_log = Mock()
        root_log.id = root_id
        root_log.parent_log_id = None
        root_log.request_id = "root-request"
        root_log.operation = "start_conversation"
        root_log.model_used = "test-model"
        root_log.parameters = {}
        root_log.user_id = None
        root_log.input_data = None
        root_log.output_data = None
        root_log.token_usage = None
        root_log.latency_ms = None
        root_log.status = "completed"
        root_log.error_message = None
        root_log.created_at = datetime.utcnow()
        root_log.finalized_at = datetime.utcnow()

        child1_log = Mock()
        child1_log.id = child1_id
        child1_log.parent_log_id = root_id
        child1_log.request_id = "child1-request"
        child1_log.operation = "continue_conversation"
        child1_log.model_used = "test-model"
        child1_log.parameters = {}
        child1_log.user_id = None
        child1_log.input_data = None
        child1_log.output_data = None
        child1_log.token_usage = None
        child1_log.latency_ms = None
        child1_log.status = "completed"
        child1_log.error_message = None
        child1_log.created_at = datetime.utcnow()
        child1_log.finalized_at = datetime.utcnow()

        child2_log = Mock()
        child2_log.id = child2_id
        child2_log.parent_log_id = child1_id
        child2_log.request_id = "child2-request"
        child2_log.operation = "end_conversation"
        child2_log.model_used = "test-model"
        child2_log.parameters = {}
        child2_log.user_id = None
        child2_log.input_data = None
        child2_log.output_data = None
        child2_log.token_usage = None
        child2_log.latency_ms = None
        child2_log.status = "completed"
        child2_log.error_message = None
        child2_log.created_at = datetime.utcnow()
        child2_log.finalized_at = datetime.utcnow()

        # Mock repository responses
        def mock_get_by_id(log_id):
            if log_id == root_id:
                return root_log
            elif log_id == child1_id:
                return child1_log
            elif log_id == child2_id:
                return child2_log
            return None

        def mock_get_filtered(filters):
            if filters.parent_log_id == root_id:
                return [child1_log]
            elif filters.parent_log_id == child1_id:
                return [child2_log]
            return []

        mock_repository.get_by_id.side_effect = mock_get_by_id
        mock_repository.get_filtered.side_effect = mock_get_filtered

        thread = service.get_conversation_thread(child1_id)

        assert len(thread) == 3  # Root + child1 + child2
        assert thread[0].id == root_id
        assert thread[1].id == child1_id
        assert thread[2].id == child2_id

    def test_export_audit_data_json(self):
        """Test exporting audit data as JSON."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        # Create mock audit logs
        log1 = Mock()
        log1.id = uuid4()
        log1.request_id = "req1"
        log1.operation = "llm_generation"
        log1.status = "completed"

        log2 = Mock()
        log2.id = uuid4()
        log2.request_id = "req2"
        log2.operation = "image_generation"
        log2.status = "completed"

        mock_repository.get_filtered.return_value = [log1, log2]

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        # Mock the conversion to AuditLogResponse
        with patch.object(service, "get_conversation_thread") as mock_get_thread:
            mock_response1 = Mock()
            mock_response1.dict.return_value = {"id": str(log1.id), "operation": "llm_generation"}
            mock_response2 = Mock()
            mock_response2.dict.return_value = {"id": str(log2.id), "operation": "image_generation"}

            mock_get_thread.side_effect = [[mock_response1], [mock_response2]]

            result = service.export_audit_data(format="json")

            assert isinstance(result, str)
            data = json.loads(result)
            assert "export_timestamp" in data
            assert data["total_records"] == 2
            assert "audit_logs" in data

    def test_export_audit_data_csv(self):
        """Test exporting audit data as CSV."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)

        # Create mock audit log
        log1 = Mock()
        log1.id = uuid4()
        log1.request_id = "req1"
        log1.operation = "llm_generation"
        log1.status = "completed"

        mock_repository.get_filtered.return_value = [log1]

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        # Mock AuditLogResponse
        mock_response = Mock()
        mock_response.dict.return_value = {
            "id": str(log1.id),
            "request_id": "req1",
            "operation": "llm_generation",
            "model_used": "llama3.2",
            "user_id": None,
            "input_data": {"prompt": "test"},
            "output_data": {"response": "test response"},
            "parameters": {"temperature": 0.7},
            "token_usage": 50,
            "latency_ms": 1500,
            "parent_log_id": None,
            "status": "completed",
            "error_message": None,
            "created_at": datetime.utcnow(),
            "finalized_at": datetime.utcnow(),
        }

        with patch("src.services.audit_service.AuditLogResponse", return_value=mock_response):
            result = service.export_audit_data(format="csv", include_conversation_context=False)

            assert isinstance(result, str)
            assert "id,request_id,operation" in result
            assert "req1" in result
            assert "llm_generation" in result

    def test_export_audit_data_to_file(self):
        """Test exporting audit data to file."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)
        mock_repository.get_filtered.return_value = []

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            service.export_audit_data(format="json", output_file=f.name)

            # Verify file was created and contains valid JSON
            with open(f.name) as read_file:
                data = json.load(read_file)
                assert "export_timestamp" in data
                assert data["total_records"] == 0

    def test_get_audit_statistics(self):
        """Test getting audit statistics."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)

        # Create mock audit logs
        logs = []
        for i in range(5):
            log = Mock()
            log.status = "completed" if i < 4 else "failed"
            log.operation = "llm_generation" if i < 3 else "image_generation"
            log.latency_ms = 1000 + i * 100
            log.token_usage = 50 + i * 10
            logs.append(log)

        mock_repository.get_filtered.return_value = logs

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        stats = service.get_audit_statistics()

        assert stats["total_logs"] == 5
        assert stats["status_breakdown"]["completed"] == 4
        assert stats["status_breakdown"]["failed"] == 1
        assert stats["operation_breakdown"]["llm_generation"] == 3
        assert stats["operation_breakdown"]["image_generation"] == 2
        assert stats["average_latency_ms"] == 1200  # (1000+1100+1200+1300+1400)/5
        assert stats["total_tokens"] == 350  # 50+60+70+80+90

    def test_get_audit_statistics_empty(self):
        """Test getting audit statistics with no logs."""
        mock_session = Mock()
        mock_repository = Mock(spec=AuditLogRepository)
        mock_repository.get_filtered.return_value = []

        service = AuditService(db_session=mock_session)
        service.repository = mock_repository

        stats = service.get_audit_statistics()

        assert stats["total_logs"] == 0
        assert stats["completeness_percentage"] == 0.0
        assert stats["status_breakdown"] == {}
        assert stats["operation_breakdown"] == {}
        assert stats["average_latency_ms"] == 0.0
        assert stats["total_tokens"] == 0


class TestAuditServiceGlobalFunctions:
    """Test global audit service functions."""

    def test_get_audit_service_singleton(self):
        """Test that get_audit_service returns singleton."""
        service1 = get_audit_service()
        service2 = get_audit_service()

        assert service1 is service2

    def test_set_audit_service(self):
        """Test setting custom audit service."""
        mock_session = Mock()
        custom_service = AuditService(db_session=mock_session)
        set_audit_service(custom_service)

        retrieved_service = get_audit_service()
        assert retrieved_service is custom_service

        # Reset to None for other tests
        set_audit_service(None)

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Set up mock service
        mock_session = Mock()
        custom_service = AuditService(db_session=mock_session)
        set_audit_service(custom_service)

        # Mock repository
        mock_repository = Mock(spec=AuditLogRepository)
        mock_repository.get_filtered.return_value = []
        custom_service.repository = mock_repository

        # Test create_audit_context
        with patch.object(custom_service, "create_audit_context") as mock_create:
            mock_create.return_value.__enter__ = Mock()
            mock_create.return_value.__exit__ = Mock()

            with create_audit_context("test_operation"):
                pass

            mock_create.assert_called_once()

        # Test export_audit_data
        result = export_audit_data(format="json")
        assert isinstance(result, str)

        # Test get_audit_statistics
        stats = get_audit_statistics()
        assert isinstance(stats, dict)

        # Reset
        set_audit_service(None)


@pytest.fixture
def mock_audit_log():
    """Create mock audit log for testing."""
    log = Mock()
    log.id = uuid4()
    log.request_id = "test-request"
    log.operation = "llm_generation"
    log.model_used = "llama3.2"
    log.parameters = {"temperature": 0.7}
    log.user_id = uuid4()
    log.input_data = {"prompt": "test prompt"}
    log.output_data = {"response": "test response"}
    log.token_usage = 50
    log.latency_ms = 1500
    log.parent_log_id = None
    log.status = "COMPLETED"
    log.error_message = None
    log.created_at = datetime.utcnow()
    log.finalized_at = datetime.utcnow()
    return log


@pytest.fixture
def mock_audit_service():
    """Create mock audit service for testing."""
    mock_session = Mock()
    service = AuditService(db_session=mock_session)
    service.repository = Mock(spec=AuditLogRepository)
    return service
