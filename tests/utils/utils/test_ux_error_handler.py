import pytest
from src.utils.ux_error_handler import (
    RetryConfig, retry_call, with_retry,
    with_image_error_handling, image_error_boundary,
    get_ux_error_stats, reset_ux_error_stats,
    PrerequisiteError, ImageProcessingError
)

def test_retry_call_exhaustion_increments_counter(monkeypatch):
    reset_ux_error_stats()
    class Boom(Exception): pass
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        raise Boom("x")
    cfg = RetryConfig(max_retries=1, initial_backoff=0.0, max_backoff=0.0, jitter=0.0, retry_on=(Boom,))
    with pytest.raises(Boom):
        retry_call(fn, cfg=cfg)
    stats = get_ux_error_stats()
    # retry_exhaustions should increase
    assert stats["retry_exhaustions"] >= 1
    assert calls["n"] == 2  # initial + one retry

def test_with_retry_decorator():
    reset_ux_error_stats()
    class Temporary(Exception): pass
    calls = {"n": 0}
    @with_retry(cfg=RetryConfig(max_retries=1, initial_backoff=0.0, max_backoff=0.0, jitter=0.0, retry_on=(Temporary,)))
    def f():
        calls["n"] += 1
        if calls["n"] < 2:
            raise Temporary()
        return 42
    assert f() == 42
    assert calls["n"] == 2

def test_image_error_boundary_counts():
    reset_ux_error_stats()
    with pytest.raises(ImageProcessingError):
        with image_error_boundary({"op": "demo"}):
            raise ImageProcessingError("fail")
    s = get_ux_error_stats()
    assert s["image_processing_failures"] >= 1

def test_with_image_error_handling_counts_and_reraises():
    reset_ux_error_stats()
    class S:
        @with_image_error_handling(operation="x", fallback_to_original=False)
        def run(self):
            raise PrerequisiteError("p")
    with pytest.raises(PrerequisiteError):
        S().run()
    s = get_ux_error_stats()
    assert s["prerequisite_failures"] >= 1
