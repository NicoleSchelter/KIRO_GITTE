"""
Data deletion service for GDPR compliance.
Provides secure data deletion with 72-hour compliance and audit trails.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from src.data.database import get_session
from src.data.models import AuditLog, ConsentRecord, FederatedLearningUpdate, PALDData, User
from src.exceptions import PrivacyError
from src.security.encryption import SecureStorage
from src.utils.error_handler import handle_errors

logger = logging.getLogger(__name__)


class DeletionStatus(str, Enum):
    """Data deletion status."""

    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeletionScope(str, Enum):
    """Scope of data deletion."""

    USER_DATA = "user_data"  # All user-related data
    PALD_DATA = "pald_data"  # Only PALD/personalization data
    CONSENT_DATA = "consent_data"  # Only consent records
    AUDIT_DATA = "audit_data"  # Only audit logs
    FL_DATA = "fl_data"  # Only federated learning data
    COMPLETE = "complete"  # Complete user account deletion


@dataclass
class DeletionRequest:
    """Data deletion request."""

    user_id: UUID
    scope: DeletionScope
    requested_at: datetime
    requested_by: UUID  # User or admin who requested deletion
    reason: str
    scheduled_for: datetime | None = None
    status: DeletionStatus = DeletionStatus.REQUESTED
    metadata: dict[str, Any] | None = None


class DataDeletionError(PrivacyError):
    """Data deletion specific error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(f"Data deletion error: {message}", **kwargs)
        self.user_message = "Data deletion failed. Please contact support."


class DataDeletionService:
    """Service for managing GDPR-compliant data deletion."""

    def __init__(self):
        self.secure_storage = SecureStorage()
        self.deletion_requests: list[DeletionRequest] = []
        self.compliance_deadline_hours = 72  # GDPR requirement

    @handle_errors(context={"service": "data_deletion"})
    def request_data_deletion(
        self,
        user_id: UUID,
        scope: DeletionScope,
        requested_by: UUID,
        reason: str,
        immediate: bool = False,
    ) -> str:
        """
        Request data deletion for a user.

        Args:
            user_id: User whose data should be deleted
            scope: Scope of deletion
            requested_by: User or admin requesting deletion
            reason: Reason for deletion
            immediate: Whether to delete immediately or schedule

        Returns:
            Deletion request ID
        """
        try:
            # Validate user exists
            with get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise DataDeletionError(f"User {user_id} not found")

            # Create deletion request
            request = DeletionRequest(
                user_id=user_id,
                scope=scope,
                requested_at=datetime.now(),
                requested_by=requested_by,
                reason=reason,
                scheduled_for=datetime.now() if immediate else datetime.now() + timedelta(hours=24),
                metadata={
                    "immediate": immediate,
                    "compliance_deadline": (
                        datetime.now() + timedelta(hours=self.compliance_deadline_hours)
                    ).isoformat(),
                },
            )

            # Store request securely
            request_id = self._store_deletion_request(request)

            # Schedule deletion
            if immediate:
                asyncio.create_task(self._execute_deletion(request_id))
            else:
                self._schedule_deletion(request)

            logger.info(
                f"Data deletion requested for user {user_id}, scope: {scope.value}, request_id: {request_id}"
            )

            return request_id

        except Exception as e:
            logger.error(f"Failed to request data deletion for user {user_id}: {e}")
            raise DataDeletionError(f"Failed to request data deletion: {e}")

    @handle_errors(context={"service": "data_deletion"})
    def cancel_deletion_request(self, request_id: str, cancelled_by: UUID) -> bool:
        """
        Cancel a pending deletion request.

        Args:
            request_id: Deletion request ID
            cancelled_by: User cancelling the request

        Returns:
            True if successfully cancelled
        """
        try:
            request = self._get_deletion_request(request_id)

            if request.status not in [DeletionStatus.REQUESTED, DeletionStatus.SCHEDULED]:
                raise DataDeletionError(
                    f"Cannot cancel deletion request in status: {request.status}"
                )

            request.status = DeletionStatus.CANCELLED
            request.metadata = request.metadata or {}
            request.metadata.update(
                {"cancelled_at": datetime.now().isoformat(), "cancelled_by": str(cancelled_by)}
            )

            self._update_deletion_request(request_id, request)

            logger.info(f"Deletion request {request_id} cancelled by {cancelled_by}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel deletion request {request_id}: {e}")
            raise DataDeletionError(f"Failed to cancel deletion request: {e}")

    @handle_errors(context={"service": "data_deletion"})
    async def execute_scheduled_deletions(self) -> int:
        """
        Execute all scheduled deletions that are due.

        Returns:
            Number of deletions executed
        """
        executed_count = 0
        current_time = datetime.now()

        try:
            # Find due deletions
            due_requests = [
                req
                for req in self.deletion_requests
                if req.status == DeletionStatus.SCHEDULED
                and req.scheduled_for
                and req.scheduled_for <= current_time
            ]

            for request in due_requests:
                try:
                    request_id = self._get_request_id(request)
                    await self._execute_deletion(request_id)
                    executed_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to execute scheduled deletion for user {request.user_id}: {e}"
                    )
                    request.status = DeletionStatus.FAILED
                    request.metadata = request.metadata or {}
                    request.metadata["error"] = str(e)

            if executed_count > 0:
                logger.info(f"Executed {executed_count} scheduled deletions")

            return executed_count

        except Exception as e:
            logger.error(f"Error executing scheduled deletions: {e}")
            raise DataDeletionError(f"Failed to execute scheduled deletions: {e}")

    async def _execute_deletion(self, request_id: str) -> None:
        """Execute a specific deletion request."""
        try:
            request = self._get_deletion_request(request_id)
            request.status = DeletionStatus.IN_PROGRESS
            self._update_deletion_request(request_id, request)

            logger.info(
                f"Starting deletion execution for user {request.user_id}, scope: {request.scope.value}"
            )

            # Execute deletion based on scope
            if request.scope == DeletionScope.COMPLETE:
                await self._delete_complete_user_data(request.user_id)
            elif request.scope == DeletionScope.USER_DATA:
                await self._delete_user_data(request.user_id)
            elif request.scope == DeletionScope.PALD_DATA:
                await self._delete_pald_data(request.user_id)
            elif request.scope == DeletionScope.CONSENT_DATA:
                await self._delete_consent_data(request.user_id)
            elif request.scope == DeletionScope.AUDIT_DATA:
                await self._delete_audit_data(request.user_id)
            elif request.scope == DeletionScope.FL_DATA:
                await self._delete_fl_data(request.user_id)

            # Mark as completed
            request.status = DeletionStatus.COMPLETED
            request.metadata = request.metadata or {}
            request.metadata.update(
                {
                    "completed_at": datetime.now().isoformat(),
                    "execution_duration": "calculated_duration",  # Would calculate actual duration
                }
            )

            self._update_deletion_request(request_id, request)

            # Create audit log
            self._create_deletion_audit_log(request)

            logger.info(
                f"Completed deletion for user {request.user_id}, scope: {request.scope.value}"
            )

        except Exception as e:
            logger.error(f"Deletion execution failed for request {request_id}: {e}")
            request = self._get_deletion_request(request_id)
            request.status = DeletionStatus.FAILED
            request.metadata = request.metadata or {}
            request.metadata["error"] = str(e)
            self._update_deletion_request(request_id, request)
            raise

    async def _delete_complete_user_data(self, user_id: UUID) -> None:
        """Delete all data for a user (complete account deletion)."""
        with get_session() as session:
            try:
                # Delete in order to respect foreign key constraints

                # 1. Delete federated learning updates
                session.query(FederatedLearningUpdate).filter(
                    FederatedLearningUpdate.user_id == user_id
                ).delete()

                # 2. Delete PALD data
                session.query(PALDData).filter(PALDData.user_id == user_id).delete()

                # 3. Delete consent records
                session.query(ConsentRecord).filter(ConsentRecord.user_id == user_id).delete()

                # 4. Anonymize audit logs (don't delete for compliance)
                session.query(AuditLog).filter(AuditLog.user_id == user_id).update(
                    {"user_id": None}
                )

                # 5. Delete user account
                session.query(User).filter(User.id == user_id).delete()

                session.commit()
                logger.info(f"Complete user data deleted for user {user_id}")

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete complete user data for {user_id}: {e}")
                raise DataDeletionError(f"Failed to delete user data: {e}")

    async def _delete_user_data(self, user_id: UUID) -> None:
        """Delete user data but keep account."""
        with get_session() as session:
            try:
                # Delete user-generated data but keep account structure
                session.query(PALDData).filter(PALDData.user_id == user_id).delete()
                session.query(FederatedLearningUpdate).filter(
                    FederatedLearningUpdate.user_id == user_id
                ).delete()

                # Anonymize audit logs
                session.query(AuditLog).filter(AuditLog.user_id == user_id).update(
                    {"user_id": None}
                )

                session.commit()
                logger.info(f"User data deleted for user {user_id}")

            except Exception as e:
                session.rollback()
                raise DataDeletionError(f"Failed to delete user data: {e}")

    async def _delete_pald_data(self, user_id: UUID) -> None:
        """Delete only PALD/personalization data."""
        with get_session() as session:
            try:
                deleted_count = session.query(PALDData).filter(PALDData.user_id == user_id).delete()
                session.commit()
                logger.info(f"Deleted {deleted_count} PALD records for user {user_id}")

            except Exception as e:
                session.rollback()
                raise DataDeletionError(f"Failed to delete PALD data: {e}")

    async def _delete_consent_data(self, user_id: UUID) -> None:
        """Delete consent records."""
        with get_session() as session:
            try:
                deleted_count = (
                    session.query(ConsentRecord).filter(ConsentRecord.user_id == user_id).delete()
                )
                session.commit()
                logger.info(f"Deleted {deleted_count} consent records for user {user_id}")

            except Exception as e:
                session.rollback()
                raise DataDeletionError(f"Failed to delete consent data: {e}")

    async def _delete_audit_data(self, user_id: UUID) -> None:
        """Anonymize audit data (don't actually delete for compliance)."""
        with get_session() as session:
            try:
                updated_count = (
                    session.query(AuditLog)
                    .filter(AuditLog.user_id == user_id)
                    .update({"user_id": None})
                )
                session.commit()
                logger.info(f"Anonymized {updated_count} audit records for user {user_id}")

            except Exception as e:
                session.rollback()
                raise DataDeletionError(f"Failed to anonymize audit data: {e}")

    async def _delete_fl_data(self, user_id: UUID) -> None:
        """Delete federated learning data."""
        with get_session() as session:
            try:
                deleted_count = (
                    session.query(FederatedLearningUpdate)
                    .filter(FederatedLearningUpdate.user_id == user_id)
                    .delete()
                )
                session.commit()
                logger.info(f"Deleted {deleted_count} FL records for user {user_id}")

            except Exception as e:
                session.rollback()
                raise DataDeletionError(f"Failed to delete FL data: {e}")

    def _store_deletion_request(self, request: DeletionRequest) -> str:
        """Store deletion request securely."""
        request_data = {
            "user_id": str(request.user_id),
            "scope": request.scope.value,
            "requested_at": request.requested_at.isoformat(),
            "requested_by": str(request.requested_by),
            "reason": request.reason,
            "scheduled_for": request.scheduled_for.isoformat() if request.scheduled_for else None,
            "status": request.status.value,
            "metadata": request.metadata,
        }

        request_id = self.secure_storage.store_sensitive_data(
            request_data,
            f"deletion_request_{request.user_id}_{int(request.requested_at.timestamp())}",
        )

        # Also store in memory for quick access
        self.deletion_requests.append(request)

        return request_id

    def _get_deletion_request(self, request_id: str) -> DeletionRequest:
        """Retrieve deletion request."""
        try:
            request_data = self.secure_storage.retrieve_sensitive_data(request_id)

            return DeletionRequest(
                user_id=UUID(request_data["user_id"]),
                scope=DeletionScope(request_data["scope"]),
                requested_at=datetime.fromisoformat(request_data["requested_at"]),
                requested_by=UUID(request_data["requested_by"]),
                reason=request_data["reason"],
                scheduled_for=(
                    datetime.fromisoformat(request_data["scheduled_for"])
                    if request_data["scheduled_for"]
                    else None
                ),
                status=DeletionStatus(request_data["status"]),
                metadata=request_data.get("metadata"),
            )

        except Exception as e:
            raise DataDeletionError(f"Failed to retrieve deletion request: {e}")

    def _update_deletion_request(self, request_id: str, request: DeletionRequest) -> None:
        """Update deletion request."""
        # In a real implementation, this would update the stored request
        # For now, we'll update the in-memory copy
        for i, req in enumerate(self.deletion_requests):
            if self._get_request_id(req) == request_id:
                self.deletion_requests[i] = request
                break

    def _get_request_id(self, request: DeletionRequest) -> str:
        """Generate request ID from request data."""
        # This is a simplified implementation
        return f"deletion_request_{request.user_id}_{int(request.requested_at.timestamp())}"

    def _schedule_deletion(self, request: DeletionRequest) -> None:
        """Schedule deletion for later execution."""
        # In a real implementation, this would use a job queue or scheduler
        logger.info(f"Scheduled deletion for user {request.user_id} at {request.scheduled_for}")

    def _create_deletion_audit_log(self, request: DeletionRequest) -> None:
        """Create audit log for deletion."""
        with get_session() as session:
            try:
                audit_log = AuditLog(
                    request_id=f"deletion_{request.user_id}",
                    user_id=None,  # Anonymized since user might be deleted
                    operation="data_deletion",
                    input_data={
                        "user_id": str(request.user_id),
                        "scope": request.scope.value,
                        "reason": request.reason,
                    },
                    output_data={
                        "status": request.status.value,
                        "completed_at": datetime.now().isoformat(),
                    },
                    status="completed",
                )

                session.add(audit_log)
                session.commit()

            except Exception as e:
                logger.error(f"Failed to create deletion audit log: {e}")

    def get_deletion_status(self, user_id: UUID) -> list[dict[str, Any]]:
        """Get deletion status for a user."""
        user_requests = [
            {
                "user_id": str(req.user_id),
                "scope": req.scope.value,
                "status": req.status.value,
                "requested_at": req.requested_at.isoformat(),
                "scheduled_for": req.scheduled_for.isoformat() if req.scheduled_for else None,
                "reason": req.reason,
            }
            for req in self.deletion_requests
            if req.user_id == user_id
        ]

        return user_requests

    def get_compliance_report(self) -> dict[str, Any]:
        """Generate compliance report for data deletions."""
        now = datetime.now()

        # Calculate compliance metrics
        total_requests = len(self.deletion_requests)
        completed_requests = len(
            [req for req in self.deletion_requests if req.status == DeletionStatus.COMPLETED]
        )
        overdue_requests = []

        for req in self.deletion_requests:
            if req.status in [
                DeletionStatus.REQUESTED,
                DeletionStatus.SCHEDULED,
                DeletionStatus.IN_PROGRESS,
            ]:
                deadline = req.requested_at + timedelta(hours=self.compliance_deadline_hours)
                if now > deadline:
                    overdue_requests.append(req)

        return {
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "pending_requests": total_requests - completed_requests,
            "overdue_requests": len(overdue_requests),
            "compliance_rate": (
                (completed_requests / total_requests * 100) if total_requests > 0 else 100
            ),
            "average_completion_time": "calculated_average",  # Would calculate actual average
            "report_generated_at": now.isoformat(),
        }


# Global data deletion service instance
data_deletion_service = DataDeletionService()


# Convenience functions
def request_user_data_deletion(
    user_id: UUID,
    scope: DeletionScope = DeletionScope.USER_DATA,
    requested_by: UUID | None = None,
    reason: str = "User requested deletion",
    immediate: bool = False,
) -> str:
    """Request data deletion for a user."""
    if requested_by is None:
        requested_by = user_id

    return data_deletion_service.request_data_deletion(
        user_id=user_id, scope=scope, requested_by=requested_by, reason=reason, immediate=immediate
    )


def get_user_deletion_status(user_id: UUID) -> list[dict[str, Any]]:
    """Get deletion status for a user."""
    return data_deletion_service.get_deletion_status(user_id)


def cancel_user_deletion_request(request_id: str, cancelled_by: UUID) -> bool:
    """Cancel a deletion request."""
    return data_deletion_service.cancel_deletion_request(request_id, cancelled_by)


async def execute_scheduled_deletions() -> int:
    """Execute all scheduled deletions."""
    return await data_deletion_service.execute_scheduled_deletions()


def get_deletion_compliance_report() -> dict[str, Any]:
    """Get compliance report for data deletions."""
    return data_deletion_service.get_compliance_report()
