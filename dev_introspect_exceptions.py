import inspect
from src.exceptions import (
    GITTEError,
    PrerequisiteCheckFailedError,
    RequiredPrerequisiteError,
    ServiceUnavailableError,
    ImageCorruptionError,
    ImageTimeoutError,
)

def dump(cls):
    print(f"\n=== {cls.__name__} MRO ===")
    for c in cls.mro():
        print("  ", c.__module__, c.__name__)
    try:
        src = inspect.getsource(cls.__init__)
        print(f"\n--- {cls.__name__}.__init__ source ---\n{src}")
    except Exception as e:
        print(f"(no __init__ source found: {e})")

for c in [
    GITTEError,
    PrerequisiteCheckFailedError,
    RequiredPrerequisiteError,
    ServiceUnavailableError,
    ImageCorruptionError,
    ImageTimeoutError,
]:
    dump(c)
