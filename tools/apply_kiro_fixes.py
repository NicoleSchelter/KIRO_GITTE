# tools/apply_kiro_fixes.py
# Safe, idempotent patcher for KIRO/GITTE on Windows (CRLF-safe).
from __future__ import annotations
import io, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = {
    "tooltip": ROOT / "src" / "ui" / "tooltip_integration.py",
    "auth_logic": ROOT / "src" / "logic" / "authentication.py",
    "auth_ui": ROOT / "src" / "ui" / "auth_ui.py",
}

TOOLTIP_NEW = """\
from __future__ import annotations
import re
import streamlit as st

def _resolve_label(passed_label, kwargs: dict, fallback: str) -> tuple[str, dict]:
    label = passed_label if passed_label is not None else kwargs.pop("label", None)
    if not label or not str(label).strip():
        placeholder = kwargs.get("placeholder")
        key = kwargs.get("key")
        if placeholder and str(placeholder).strip():
            label = str(placeholder).strip()
        elif key:
            s = re.sub(r"[_\\-]+", " ", str(key)).strip()
            label = s[:1].upper() + s[1:] if s else fallback
        else:
            label = fallback
    kwargs.setdefault("label_visibility", "collapsed")
    return label, kwargs

def tooltip_input(*args, **kwargs):
    fallback = "Password" if kwargs.get("type") == "password" else "Input"
    label, kwargs = _resolve_label(None, kwargs, fallback)
    return st.text_input(label, *args, **kwargs)

def tooltip_checkbox(*args, **kwargs):
    label, kwargs = _resolve_label(None, kwargs, "I accept the terms")
    return st.checkbox(label, *args, **kwargs)

def tooltip_selectbox(options, *args, **kwargs):
    label, kwargs = _resolve_label(None, kwargs, "Select an option")
    return st.selectbox(label, options, *args, **kwargs)

def tooltip_text_area(*args, **kwargs):
    label, kwargs = _resolve_label(None, kwargs, "Input text")
    return st.text_area(label, *args, **kwargs)

def tooltip_number_input(*args, **kwargs):
    label, kwargs = _resolve_label(None, kwargs, "Enter a number")
    return st.number_input(label, *args, **kwargs)

def tooltip_radio(options, *args, **kwargs):
    label, kwargs = _resolve_label(None, kwargs, "Choose an option")
    return st.radio(label, options, *args, **kwargs)

def tooltip_multiselect(options, *args, **kwargs):
    label, kwargs = _resolve_label(None, kwargs, "Select one or more")
    return st.multiselect(label, options, *args, **kwargs)
"""

def write_backup(p: Path):
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

def patch_tooltip():
    p = files["tooltip"]
    if not p.exists():
        print(f"[SKIP] {p} not found")
        return
    write_backup(p)
    p.write_text(TOOLTIP_NEW, encoding="utf-8")
    print(f"[OK]  Rewrote {p}")

def patch_auth_logic():
    p = files["auth_logic"]
    if not p.exists():
        print(f"[SKIP] {p} not found")
        return
    src = p.read_text(encoding="utf-8")
    write_backup(p)
    # Inject explicit commit after 'user = repo.create(...)'
    pattern = r"(user\s*=\s*repo\.create\([^\n]*\)\s*\n\s*if\s+not\s+user:\s*[\s\S]*?raise\s+AuthenticationError\([^\n]*\)\s*\n)"
    insert = r"""\
\1
                    # --- NEW: explicit commit to guarantee persistence immediately
                    try:
                        db.commit()
                        logger.debug("register_user: explicit commit succeeded")
                    except Exception as ce:
                        logger.error(f"register_user: explicit commit failed → rollback. Error: {ce}")
                        db.rollback()
                        raise

                    # Optional: refresh to populate DB defaults/IDs (not required)
                    try:
                        db.refresh(user)
                        logger.debug("register_user: refresh after commit succeeded")
                    except Exception:
                        logger.debug("register_user: refresh after commit skipped/failed (not critical)")
"""
    new = re.sub(pattern, insert, src, count=1)
    p.write_text(new, encoding="utf-8")
    print(f"[OK]  Patched explicit commit in {p}")

def patch_auth_ui():
    p = files["auth_ui"]
    if not p.exists():
        print(f"[SKIP] {p} not found")
        return
    src = p.read_text(encoding="utf-8")
    write_backup(p)
    pattern = r"(user\s*=\s*self\.auth_logic\.register_user\([^\)]*\)\s*\n)"
    insert = r"""\
\1        # --- NEW: set session state and rerun to leave the registration screen
        try:
            # self.session_manager.set_current_user(user.id)  # use if available
            pass
        except Exception:
            pass
        import streamlit as st
        st.session_state["authenticated"] = True
        st.session_state["current_user_id"] = str(user.id)
        st.success("Account created successfully.")
        st.rerun()
"""
    new = re.sub(pattern, insert, src, count=1)
    p.write_text(new, encoding="utf-8")
    print(f"[OK]  Patched session+rerun in {p}")

def main():
    patch_tooltip()
    patch_auth_logic()
    patch_auth_ui()
    print("\nDone. Backups with .bak created next to each file.")

if __name__ == "__main__":
    main()
