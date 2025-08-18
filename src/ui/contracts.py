"""UI contracts for PALD processing requests and responses."""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID


class UiJobStatus(str, Enum):
    """Lifecycle status for UI-level jobs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class PALDProcessingRequest:
    """Request envelope sent from UI to the processing service."""
    request_id: UUID
    session_id: str
    defer_bias_scan: bool
    description_text: str
    embodiment_caption: Optional[str]
    pald_schema_version: Optional[str]
    created_at: datetime  # UTC, naive

    def to_dict(self) -> dict:
        """Serialize to a JSON-ready dict."""
        data = asdict(self)
        return data

    def __repr__(self) -> str:
        return (
            f"PALDProcessingRequest(request_id={self.request_id}, "
            f"session_id={self.session_id}, "
            f"defer_bias_scan={self.defer_bias_scan})"
        )


@dataclass
class PALDProcessingResponse:
    """Response envelope rendered by the UI layer."""
    job_id: Optional[UUID]
    status: UiJobStatus
    pald_light: dict[str, Any]
    pald_diff_summary: list[str]
    defer_notice: Optional[str] | bool
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    def to_dict(self) -> dict:
        """Serialize to a JSON-ready dict (enums as values)."""
        data = asdict(self)
        # normalize enum to its value
        data["status"] = self.status.value
        return data

    def __repr__(self) -> str:
        """Stable string representation for logging."""
        return (
            f"PALDProcessingResponse(job_id={self.job_id}, "
            f"status={self.status.value}, "
            f"pald_keys={len(self.pald_light)}, "
            f"diff_items={len(self.pald_diff_summary)})"
        )
