# tools/apply_kiro_fixes_v3.py
# Robust patcher: auto-detects repo root & src/, rewrites tooltip_integration.py
# and injects minimal fixes into authentication.py and auth_ui.py.
from __future__ import annotations
import re
from pathlib import Path

TOOLTIP_CONTENT = r"""from __future__ import annotations
import re
import streamlit as st

__all__ = [
    "get_tooltip_integration",
    "tooltip_button",
    "tooltip_input",
    "tooltip_checkbox",
    "tooltip_selectbox",
    "tooltip_text_area",
    "tooltip_number_input",
    "tooltip_radio",
    "tooltip_multiselect",
]

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

class _NoopTooltipIntegration:
    def wrap(self, widget_fn, *args, **kwargs):
        return widget_fn(*args, **kwargs)

def get_tooltip_integration():
    return _NoopTooltipIntegration()

def tooltip_button(*args, **kwargs):
    label, kwargs = _resolve_label(None, kwargs, "Submit")
    return st.button(label, *args, **kwargs)

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

def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "src").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()

def write_backup(p: Path):
    bak = p.with_suffix(p.suffix + ".bak")
    if p.exists() and not bak.exists():
        bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

def patch_tooltip(ui_dir: Path):
    p = ui_dir / "tooltip_integration.py"
    if not p.exists():
        print(f"[WARN] {p} not found. Creating new.")
    write_backup(p)
    p.write_text(TOOLTIP_CONTENT, encoding="utf-8")
    print(f"[OK]  wrote {p}")

def patch_auth_logic(logic_dir: Path):
    p = logic_dir / "authentication.py"
    if not p.exists():
        print(f"[SKIP] {p} not found")
        return
    src = p.read_text(encoding="utf-8")
    write_backup(p)

    # inject explicit commit after create(...)
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
    new = re.sub(pattern, insert, src, count=1, flags=re.DOTALL)
    if new == src:
        print("[WARN] authentication.py: commit pattern not found (maybe already patched).")
    else:
        p.write_text(new, encoding="utf-8")
        print(f"[OK]  patched explicit commit in {p}")

def patch_auth_ui(ui_dir: Path):
    p = ui_dir / "auth_ui.py"
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
    new = re.sub(pattern, insert, src, count=1, flags=re.DOTALL)
    if new == src:
        print("[WARN] auth_ui.py: rerun pattern not found (maybe already patched).")
    else:
        p.write_text(new, encoding="utf-8")
        print(f"[OK]  patched session+rerun in {p}")

def main():
    here = Path(__file__).resolve()
    repo = find_repo_root(here.parent)
    src = repo / "src"
    ui = src / "ui"
    logic = src / "logic"

    print(f"[INFO] repo root = {repo}")
    print(f"[INFO] src dir   = {src}")
    patch_tooltip(ui)
    patch_auth_logic(logic)
    patch_auth_ui(ui)
    print("\nDone. Backups (.bak) created when files existed.")

if __name__ == "__main__":
    main()
