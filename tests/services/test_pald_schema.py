from typing import Any, Dict

from src.services.pald_schema import allowed_keys, validate_pald_light


def _fake_schema() -> Dict[str, Any]:
    # Minimal in-memory PALD schema for tests; no file I/O.
    # Only structure matters: derive dotted keys dynamically.
    return {
        "global": {
            "gender": {},
            "age": {},
        },
        "medium": {
            "context": {
                "scene": {},
                "lighting": {},
            }
        },
        "detail": {
            "face": {
                "eyes": {"color": {}},
                "mouth": {"state": {}},
            },
            "hair": {"style": {}},
        },
    }


def test_allowed_keys_builds_dotted_set():
    schema = _fake_schema()
    keys = allowed_keys(schema)
    # Leaves only (dotted)
    expected = {
        "global.gender",
        "global.age",
        "medium.context.scene",
        "medium.context.lighting",
        "detail.face.eyes.color",
        "detail.face.mouth.state",
        "detail.hair.style",
    }
    assert expected.issubset(keys)


def test_validate_pald_light_strips_disallowed_and_preserves_allowed_values():
    schema = _fake_schema()
    data = {
        "global.gender": "female",
        "global.unknown": "x",                      # disallowed
        "medium.context.scene": "indoor",
        "detail.face.eyes.color": "green",
        "detail.hair.style": "ponytail",
        "detail.hair.color": "brown",               # disallowed
    }
    out = validate_pald_light(data, schema)
    assert out == {
        "global.gender": "female",
        "medium.context.scene": "indoor",
        "detail.face.eyes.color": "green",
        "detail.hair.style": "ponytail",
    }


def test_validate_pald_light_handles_empty_and_non_dicts_gracefully():
    schema = _fake_schema()
    assert validate_pald_light({}, schema) == {}
    assert validate_pald_light(None, schema) == {}  # type: ignore[arg-type]
