"""Service-level PALD schema loader and validator."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Set

from src.utils.logging import get_logger

logger = get_logger(__name__)

_TOP_LEVEL_SECTIONS = ("global", "medium", "detail")


def _default_schema_path() -> Path:
    """Resolve schema path by precedence:
    1) PALD_SCHEMA_PATH env var
    2) config.paths.pald_schema (if available)
    3) fallback: Basic files/pald_schema.json
    """
    env_path = os.environ.get("PALD_SCHEMA_PATH")
    if env_path:
        return Path(env_path)

    # Try config.paths.pald_schema if present
    try:
        from config.config import config  # type: ignore
        cfg_paths = getattr(config, "paths", None)
        pald_path = getattr(cfg_paths, "pald_schema", None)
        if pald_path:
            return Path(str(pald_path))
    except Exception:
        # config is optional at runtime
        pass

    return Path("Basic files") / "pald_schema.json"


def load_pald_schema(path: "Path | str | None" = None) -> Dict[str, Any]:
    """Load PALD JSON schema from disk (UTF-8). Fail gracefully and log errors."""
    p = Path(path) if path else _default_schema_path()
    try:
        text = p.read_text(encoding="utf-8")
        schema = json.loads(text)
        logger.info("pald_schema_loaded path=%s", p.as_posix())
        return schema if isinstance(schema, dict) else {}
    except FileNotFoundError:
        logger.error("pald_schema_not_found path=%s", p.as_posix())
        return {}
    except json.JSONDecodeError as e:
        logger.error("pald_schema_invalid_json path=%s error=%s", p.as_posix(), e)
        return {}
    except Exception as e:  # pragma: no cover
        logger.error("pald_schema_load_failed path=%s error=%s", p.as_posix(), e)
        return {}


def _flatten_keys(prefix: str, node: Any) -> Iterable[str]:
    """Recursively build dotted keys from schema nodes (leaf dicts count as fields)."""
    if not isinstance(node, dict) or not node:
        # Leaf: current prefix is a full dotted key
        if prefix:
            yield prefix
        return

    for k, v in node.items():
        new_prefix = f"{prefix}.{k}" if prefix else k
        # Recurse; if v is {}, we still treat new_prefix as a leaf
        if isinstance(v, dict):
            if v:
                yield from _flatten_keys(new_prefix, v)
            else:
                yield new_prefix
        else:
            # Non-dict: treat as leaf
            yield new_prefix


def allowed_keys(schema: Dict[str, Any]) -> Set[str]:
    """Derive allowed dotted keys under top-level sections: global/medium/detail."""
    if not isinstance(schema, dict):
        return set()

    out: Set[str] = set()
    for top in _TOP_LEVEL_SECTIONS:
        node = schema.get(top)
        if node is None:
            continue
        for key in _flatten_keys(top, node):
            out.add(key)
    return out


def validate_pald_light(data: Dict[str, Any] | None, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Return a new dict stripped to allowed dotted keys. Non-dicts become {}."""
    if not isinstance(data, dict):
        return {}
    allowed = allowed_keys(schema)
    if not allowed:
        # No known keys -> nothing passes
        return {}

    cleaned: Dict[str, Any] = {}
    for k, v in data.items():
        # Accept only exact dotted keys
        if isinstance(k, str) and k in allowed:
            cleaned[k] = v
    return cleaned
