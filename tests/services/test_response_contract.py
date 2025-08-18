from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List, Optional

from src.ui.contracts import UiJobStatus, PALDProcessingRequest, PALDProcessingResponse
from src.ui.chat_ui import banner_text, defer_text, error_text, pald_summary_lines


def _mk_response(
    status: UiJobStatus,
    *,
    diff_items: int = 0,
    pald: Optional[Dict[str, Any]] = None,
    defer: Optional[object] = None,
    err: Optional[str] = None
) -> PALDProcessingResponse:
    return PALDProcessingResponse(
        job_id=uuid4(),
        status=status,
        pald_light=pald or {},
        pald_diff_summary=[f"added:key{i}" for i in range(diff_items)],
        defer_notice=defer,
        error_message=err,
        started_at=datetime.utcnow(),
        completed_at=None if status in (UiJobStatus.PENDING, UiJobStatus.RUNNING) else datetime.utcnow(),
    )


def test_dataclasses_serialize_and_repr():
    req = PALDProcessingRequest(
        request_id=uuid4(),
        session_id="sess-1",
        defer_bias_scan=True,
        description_text="A person riding a bike.",
        embodiment_caption=None,
        pald_schema_version="1.0",
        created_at=datetime.utcnow(),
    )
    resp = _mk_response(UiJobStatus.COMPLETED, diff_items=2, pald={"global.gender": "female"})

    # to_dict should be JSON-serializable and include enum as value
    d_req = req.to_dict()
    d_resp = resp.to_dict()
    assert d_req["session_id"] == "sess-1"
    assert d_resp["status"] == UiJobStatus.COMPLETED.value
    assert "pald_light" in d_resp and isinstance(d_resp["pald_light"], dict)

    # __repr__ should be stable and informative
    r = repr(resp)
    assert "PALDProcessingResponse(" in r
    assert "status=" in r
    assert "diff_items=" in r


def test_banner_text_for_all_statuses():
    assert "Processing" in banner_text(UiJobStatus.PENDING)
    assert "progress" in banner_text(UiJobStatus.RUNNING)
    assert "completed" in banner_text(UiJobStatus.COMPLETED)
    assert "failed" in banner_text(UiJobStatus.FAILED)


def test_defer_and_error_texts():
    r1 = _mk_response(UiJobStatus.RUNNING, defer=True)
    assert defer_text(r1)  # default notice for bool True

    r2 = _mk_response(UiJobStatus.RUNNING, defer="Deferred due to config flag")
    assert defer_text(r2) == "Deferred due to config flag"

    r3 = _mk_response(UiJobStatus.FAILED, err="Something went wrong")
    assert error_text(r3) == "Something went wrong"


def test_pald_summary_truncates_and_shows_ellipsis():
    r = _mk_response(UiJobStatus.COMPLETED, diff_items=25, pald={})
    lines = pald_summary_lines(r, max_items=10)
    assert len(lines) == 11  # 10 items + "…"
    assert lines[-1] == "…"


def test_pald_summary_includes_sample_of_pald_light():
    r = _mk_response(
        UiJobStatus.COMPLETED,
        diff_items=0,
        pald={"global.gender": "female", "medium.context": "outdoor", "detail.face.eyes.color": "green"},
    )
    lines = pald_summary_lines(r, max_items=20)
    # Expect at least these samples to appear
    assert any("pald:global.gender -> female" in s for s in lines)
    assert any("pald:medium.context -> outdoor" in s for s in lines)
    assert any("pald:detail.face.eyes.color -> green" in s for s in lines)
