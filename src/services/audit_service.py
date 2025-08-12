"""
Audit Service Layer for GITTE system.
Provides comprehensive audit logging with write-ahead logging (WAL) for all AI interactions.
"""

import csv
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import IO, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.data.models import AuditLog, AuditLogStatus
from src.data.repositories import AuditLogRepository
from src.data.schemas import AuditLogCreate, AuditLogFilters, AuditLogResponse, AuditLogUpdate

logger = logging.getLogger(__name__)


class AuditLogEntry:
    """
    Write-ahead log entry for AI interactions.
    Provides context management for audit logging lifecycle.
    """

    def __init__(
        self,
        request_id: str,
        operation: str,
        user_id: UUID | None = None,
        model_used: str | None = None,
        parameters: dict[str, Any] | None = None,
        parent_log_id: UUID | None = None,
        audit_service: Optional["AuditService"] = None,
    ):
        self.request_id = request_id
        self.operation = operation
        self.user_id = user_id
        self.model_used = model_used
        self.parameters = parameters or {}
        self.parent_log_id = parent_log_id
        self.audit_service = audit_service
        self.audit_id: UUID | None = None
        self.start_time = datetime.utcnow()
        self.input_data: dict[str, Any] | None = None
        self.output_data: dict[str, Any] | None = None
        self.error_message: str | None = None
        self._finalized = False

    def __enter__(self):
        """Initialize write-ahead log entry."""
        if self.audit_service:
            self.audit_id = self.audit_service.initialize_log(
                request_id=self.request_id,
                operation=self.operation,
                user_id=self.user_id,
                model_used=self.model_used,
                parameters=self.parameters,
                parent_log_id=self.parent_log_id,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finalize audit log entry."""
        if not self._finalized and self.audit_service and self.audit_id:
            if exc_type is not None:
                # Exception occurred
                self.error_message = str(exc_val)
                self.audit_service.finalize_log(
                    audit_id=self.audit_id,
                    input_data=self.input_data,
                    output_data=self.output_data,
                    error_message=self.error_message,
                    status=AuditLogStatus.FAILED,
                )
            else:
                # Success
                self.audit_service.finalize_log(
                    audit_id=self.audit_id,
                    input_data=self.input_data,
                    output_data=self.output_data,
                    status=AuditLogStatus.COMPLETED,
                )
            self._finalized = True

    def set_input(self, input_data: dict[str, Any]):
        """Set input data for the audit log."""
        self.input_data = input_data
        if self.audit_service and self.audit_id:
            self.audit_service.update_log(
                audit_id=self.audit_id, input_data=input_data, status=AuditLogStatus.IN_PROGRESS
            )

    def set_output(self, output_data: dict[str, Any]):
        """Set output data for the audit log."""
        self.output_data = output_data

    def add_metadata(self, **metadata):
        """Add metadata to parameters."""
        self.parameters.update(metadata)
        if self.audit_service and self.audit_id:
            self.audit_service.update_log(audit_id=self.audit_id, parameters=self.parameters)


class AuditService:
    """
    Service for comprehensive audit logging with write-ahead logging (WAL).
    Handles audit log lifecycle, parent-child linking, and data export.
    """

    def __init__(self, db_session: Session | None = None):
        """
        Initialize audit service.

        Args:
            db_session: Database session (optional, will create if not provided)
        """
        self.db_session = db_session
        self._own_session = db_session is None
        if self._own_session:
            # get_session() returns a context manager, we need to use it properly
            from src.data.database import get_session_sync

            self.db_session = get_session_sync()

        self.repository = AuditLogRepository(self.db_session)

    def __del__(self):
        """Clean up database session if we own it."""
        if self._own_session and self.db_session:
            self.db_session.close()

    @contextmanager
    def create_audit_context(
        self,
        operation: str,
        user_id: UUID | None = None,
        model_used: str | None = None,
        parameters: dict[str, Any] | None = None,
        parent_log_id: UUID | None = None,
        request_id: str | None = None,
    ) -> AuditLogEntry:
        """
        Create audit context for write-ahead logging.

        Args:
            operation: Operation being performed
            user_id: User performing the operation
            model_used: AI model being used
            parameters: Operation parameters
            parent_log_id: Parent audit log ID for conversation threading
            request_id: Unique request ID (generated if not provided)

        Returns:
            AuditLogEntry: Context manager for audit logging
        """
        if request_id is None:
            request_id = str(uuid4())

        entry = AuditLogEntry(
            request_id=request_id,
            operation=operation,
            user_id=user_id,
            model_used=model_used,
            parameters=parameters,
            parent_log_id=parent_log_id,
            audit_service=self,
        )

        try:
            yield entry
        finally:
            # Ensure finalization happens even if not done in __exit__
            if not entry._finalized and entry.audit_id:
                self.finalize_log(
                    audit_id=entry.audit_id,
                    input_data=entry.input_data,
                    output_data=entry.output_data,
                    error_message=entry.error_message,
                    status=(
                        AuditLogStatus.COMPLETED
                        if not entry.error_message
                        else AuditLogStatus.FAILED
                    ),
                )

    def initialize_log(
        self,
        request_id: str,
        operation: str,
        user_id: UUID | None = None,
        model_used: str | None = None,
        parameters: dict[str, Any] | None = None,
        parent_log_id: UUID | None = None,
    ) -> UUID | None:
        """
        Initialize write-ahead log entry.

        Args:
            request_id: Unique request identifier
            operation: Operation being performed
            user_id: User performing the operation
            model_used: AI model being used
            parameters: Operation parameters
            parent_log_id: Parent audit log ID for conversation threading

        Returns:
            UUID: Audit log ID if successful, None otherwise
        """
        try:
            audit_data = AuditLogCreate(
                request_id=request_id,
                operation=operation,
                model_used=model_used,
                parameters=parameters or {},
                user_id=user_id,
                parent_log_id=parent_log_id,
            )

            audit_log = self.repository.create(audit_data)
            if audit_log:
                self.db_session.commit()
                logger.debug(f"Initialized audit log {audit_log.id} for operation {operation}")
                return audit_log.id
            else:
                logger.error(f"Failed to initialize audit log for operation {operation}")
                return None

        except Exception as e:
            logger.error(f"Error initializing audit log: {e}")
            self.db_session.rollback()
            return None

    def update_log(
        self,
        audit_id: UUID,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        token_usage: int | None = None,
        latency_ms: int | None = None,
        status: AuditLogStatus | None = None,
        error_message: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update audit log entry.

        Args:
            audit_id: Audit log ID
            input_data: Input data for the operation
            output_data: Output data from the operation
            token_usage: Number of tokens used
            latency_ms: Operation latency in milliseconds
            status: Current status
            error_message: Error message if operation failed
            parameters: Updated parameters

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            update_data = AuditLogUpdate()

            if input_data is not None:
                update_data.input_data = input_data
            if output_data is not None:
                update_data.output_data = output_data
            if token_usage is not None:
                update_data.token_usage = token_usage
            if latency_ms is not None:
                update_data.latency_ms = latency_ms
            if status is not None:
                update_data.status = status
            if error_message is not None:
                update_data.error_message = error_message
            if parameters is not None:
                # Get current audit log to merge parameters
                current_log = self.repository.get_by_id(audit_id)
                if current_log and current_log.parameters:
                    merged_params = current_log.parameters.copy()
                    merged_params.update(parameters)
                    update_data.parameters = merged_params
                else:
                    update_data.parameters = parameters

            updated_log = self.repository.update(audit_id, update_data)
            if updated_log:
                self.db_session.commit()
                logger.debug(f"Updated audit log {audit_id}")
                return True
            else:
                logger.error(f"Failed to update audit log {audit_id}")
                return False

        except Exception as e:
            logger.error(f"Error updating audit log {audit_id}: {e}")
            self.db_session.rollback()
            return False

    def finalize_log(
        self,
        audit_id: UUID,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        token_usage: int | None = None,
        latency_ms: int | None = None,
        status: AuditLogStatus = AuditLogStatus.COMPLETED,
        error_message: str | None = None,
    ) -> bool:
        """
        Finalize audit log entry.

        Args:
            audit_id: Audit log ID
            input_data: Final input data
            output_data: Final output data
            token_usage: Total tokens used
            latency_ms: Total operation latency
            status: Final status
            error_message: Error message if failed

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Calculate latency if not provided
            if latency_ms is None:
                audit_log = self.repository.get_by_id(audit_id)
                if audit_log and audit_log.created_at:
                    latency_ms = int(
                        (datetime.utcnow() - audit_log.created_at).total_seconds() * 1000
                    )

            # Update with final data
            success = self.update_log(
                audit_id=audit_id,
                input_data=input_data,
                output_data=output_data,
                token_usage=token_usage,
                latency_ms=latency_ms,
                status=status,
                error_message=error_message,
            )

            if success:
                # Mark as finalized
                finalized = self.repository.finalize(audit_id)
                if finalized:
                    self.db_session.commit()
                    logger.info(f"Finalized audit log {audit_id} with status {status.value}")
                    return True
                else:
                    logger.error(f"Failed to finalize audit log {audit_id}")
                    return False
            else:
                return False

        except Exception as e:
            logger.error(f"Error finalizing audit log {audit_id}: {e}")
            self.db_session.rollback()
            return False

    def get_conversation_thread(self, audit_id: UUID) -> list[AuditLogResponse]:
        """
        Get complete conversation thread for an audit log.

        Args:
            audit_id: Audit log ID

        Returns:
            List[AuditLogResponse]: Complete conversation thread
        """
        try:
            # Find root of conversation
            current_log = self.repository.get_by_id(audit_id)
            if not current_log:
                return []

            # Traverse up to find root
            root_log = current_log
            while root_log.parent_log_id:
                parent = self.repository.get_by_id(root_log.parent_log_id)
                if parent:
                    root_log = parent
                else:
                    break

            # Get all logs in the conversation thread
            thread_logs = self._get_thread_recursive(root_log.id)

            # Convert to response schemas
            return [
                AuditLogResponse(
                    id=log.id,
                    request_id=log.request_id,
                    operation=log.operation,
                    model_used=log.model_used,
                    parameters=log.parameters or {},
                    user_id=log.user_id,
                    input_data=log.input_data,
                    output_data=log.output_data,
                    token_usage=log.token_usage,
                    latency_ms=log.latency_ms,
                    parent_log_id=log.parent_log_id,
                    status=AuditLogStatus(log.status),
                    error_message=log.error_message,
                    created_at=log.created_at,
                    finalized_at=log.finalized_at,
                )
                for log in thread_logs
            ]

        except Exception as e:
            logger.error(f"Error getting conversation thread for {audit_id}: {e}")
            return []

    def _get_thread_recursive(self, log_id: UUID) -> list[AuditLog]:
        """Recursively get all logs in a conversation thread."""
        logs = []
        current_log = self.repository.get_by_id(log_id)
        if current_log:
            logs.append(current_log)
            # Get all children
            children = self.repository.get_filtered(AuditLogFilters(parent_log_id=log_id))
            for child in children:
                logs.extend(self._get_thread_recursive(child.id))
        return logs

    def export_audit_data(
        self,
        format: str = "json",
        filters: AuditLogFilters | None = None,
        include_conversation_context: bool = True,
        output_file: str | Path | IO | None = None,
    ) -> str | bytes:
        """
        Export audit data in CSV or JSON format.

        Args:
            format: Export format ("json" or "csv")
            filters: Filters to apply to audit logs
            include_conversation_context: Whether to include full conversation context
            output_file: Output file path or file-like object

        Returns:
            Union[str, bytes]: Exported data as string/bytes or writes to file
        """
        try:
            # Get audit logs based on filters
            audit_logs = self.repository.get_filtered(filters or AuditLogFilters())

            if include_conversation_context:
                # Group by conversation threads
                processed_ids = set()
                export_data = []

                for log in audit_logs:
                    if log.id not in processed_ids:
                        thread = self.get_conversation_thread(log.id)
                        export_data.extend(thread)
                        processed_ids.update(t.id for t in thread)
            else:
                # Convert individual logs
                export_data = [
                    AuditLogResponse(
                        id=log.id,
                        request_id=log.request_id,
                        operation=log.operation,
                        model_used=log.model_used,
                        parameters=log.parameters or {},
                        user_id=log.user_id,
                        input_data=log.input_data,
                        output_data=log.output_data,
                        token_usage=log.token_usage,
                        latency_ms=log.latency_ms,
                        parent_log_id=log.parent_log_id,
                        status=AuditLogStatus(log.status),
                        error_message=log.error_message,
                        created_at=log.created_at,
                        finalized_at=log.finalized_at,
                    )
                    for log in audit_logs
                ]

            # Export in requested format
            if format.lower() == "json":
                return self._export_json(export_data, output_file)
            elif format.lower() == "csv":
                return self._export_csv(export_data, output_file)
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error(f"Error exporting audit data: {e}")
            raise

    def _export_json(
        self, data: list[AuditLogResponse], output_file: str | Path | IO | None = None
    ) -> str:
        """Export data as JSON."""
        json_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_records": len(data),
            "audit_logs": [log.dict() for log in data],
        }

        json_str = json.dumps(json_data, indent=2, default=str)

        if output_file:
            if hasattr(output_file, "write"):
                output_file.write(json_str)
            else:
                with open(output_file, "w") as f:
                    f.write(json_str)

        return json_str

    def _export_csv(
        self, data: list[AuditLogResponse], output_file: str | Path | IO | None = None
    ) -> str:
        """Export data as CSV."""
        if not data:
            return ""

        # Define CSV headers
        headers = [
            "id",
            "request_id",
            "operation",
            "model_used",
            "user_id",
            "input_data",
            "output_data",
            "parameters",
            "token_usage",
            "latency_ms",
            "parent_log_id",
            "status",
            "error_message",
            "created_at",
            "finalized_at",
        ]

        # Create CSV content
        if output_file and hasattr(output_file, "write"):
            writer = csv.DictWriter(output_file, fieldnames=headers)
            writer.writeheader()
            for log in data:
                row = log.dict()
                # Convert complex fields to JSON strings
                for field in ["input_data", "output_data", "parameters"]:
                    if row[field]:
                        row[field] = json.dumps(row[field])
                writer.writerow(row)
            return ""
        else:
            # Return as string
            import io

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            for log in data:
                row = log.dict()
                # Convert complex fields to JSON strings
                for field in ["input_data", "output_data", "parameters"]:
                    if row[field]:
                        row[field] = json.dumps(row[field])
                writer.writerow(row)

            csv_content = output.getvalue()
            output.close()

            if output_file:
                with open(output_file, "w", newline="") as f:
                    f.write(csv_content)

            return csv_content

    def get_audit_statistics(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """
        Get audit logging statistics.

        Args:
            start_date: Start date for statistics
            end_date: End date for statistics

        Returns:
            Dict: Audit statistics
        """
        try:
            filters = AuditLogFilters()
            if start_date:
                filters.start_date = start_date
            if end_date:
                filters.end_date = end_date

            logs = self.repository.get_filtered(filters)

            total_logs = len(logs)
            if total_logs == 0:
                return {
                    "total_logs": 0,
                    "completeness_percentage": 0.0,
                    "status_breakdown": {},
                    "operation_breakdown": {},
                    "average_latency_ms": 0.0,
                    "total_tokens": 0,
                }

            # Calculate statistics
            status_counts = {}
            operation_counts = {}
            total_latency = 0
            total_tokens = 0
            finalized_count = 0

            for log in logs:
                # Status breakdown
                status = log.status
                status_counts[status] = status_counts.get(status, 0) + 1

                # Operation breakdown
                operation = log.operation
                operation_counts[operation] = operation_counts.get(operation, 0) + 1

                # Latency and tokens
                if log.latency_ms:
                    total_latency += log.latency_ms
                if log.token_usage:
                    total_tokens += log.token_usage

                # Finalization tracking
                if log.status == AuditLogStatus.FINALIZED.value:
                    finalized_count += 1

            # Calculate completeness (finalized logs / total logs)
            completeness_percentage = (finalized_count / total_logs) * 100 if total_logs > 0 else 0

            # Calculate average latency
            logs_with_latency = [log for log in logs if log.latency_ms]
            average_latency = total_latency / len(logs_with_latency) if logs_with_latency else 0

            return {
                "total_logs": total_logs,
                "completeness_percentage": completeness_percentage,
                "status_breakdown": status_counts,
                "operation_breakdown": operation_counts,
                "average_latency_ms": average_latency,
                "total_tokens": total_tokens,
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None,
            }

        except Exception as e:
            logger.error(f"Error getting audit statistics: {e}")
            return {}


# Global audit service instance
_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    """Get the global audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


def set_audit_service(service: AuditService) -> None:
    """Set the global audit service instance (useful for testing)."""
    global _audit_service
    _audit_service = service


# Convenience functions for common audit operations
def create_audit_context(
    operation: str,
    user_id: UUID | None = None,
    model_used: str | None = None,
    parameters: dict[str, Any] | None = None,
    parent_log_id: UUID | None = None,
    request_id: str | None = None,
):
    """Create audit context using the global audit service."""
    return get_audit_service().create_audit_context(
        operation=operation,
        user_id=user_id,
        model_used=model_used,
        parameters=parameters,
        parent_log_id=parent_log_id,
        request_id=request_id,
    )


def export_audit_data(
    format: str = "json",
    filters: AuditLogFilters | None = None,
    include_conversation_context: bool = True,
    output_file: str | Path | IO | None = None,
) -> str | bytes:
    """Export audit data using the global audit service."""
    return get_audit_service().export_audit_data(
        format=format,
        filters=filters,
        include_conversation_context=include_conversation_context,
        output_file=output_file,
    )


def get_audit_statistics(
    start_date: datetime | None = None, end_date: datetime | None = None
) -> dict[str, Any]:
    """Get audit statistics using the global audit service."""
    return get_audit_service().get_audit_statistics(start_date=start_date, end_date=end_date)
