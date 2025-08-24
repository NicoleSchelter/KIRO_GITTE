#!/usr/bin/env python3
"""
ASCII-sanitize all KIRO hooks:
- Rename non-ASCII filenames to safe ASCII.
- Strip BOM / zero-width / NBSP and normalize newlines.
- Parse JSON and rewrite with ensure_ascii=True.
- Warn if required keys are missing so you can fix those files.
"""

from __future__ import annotations
import json, re, sys, shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".kiro" / "hooks"

HIDDEN_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2066-\u2069\uFEFF\u00A0]")  # zero-widths, bidi, NBSP
TRAILING_COMMAS_RE = re.compile(r",\s*(?=[}\]])")  # naive but effective for trailing commas

DASHES = dict.fromkeys([chr(c) for c in (0x2010,0x2011,0x2012,0x2013,0x2014,0x2212)], "-")
QUOTES = {**dict.fromkeys([chr(c) for c in (0x2018,0x2019,0x201A)], "'"),
          **dict.fromkeys([chr(c) for c in (0x201C,0x201D,0x201E)], '"')}
UMLAUTS = {
    "ä":"ae","ö":"oe","ü":"ue","Ä":"Ae","Ö":"Oe","Ü":"Ue","ß":"ss",
}

REQUIRED_KEYS = ("triggers","runCommand")
REQUIRED_RUNCMD_KEYS = ("shell","args")

def to_ascii_filename(name: str) -> str:
    n = "".join(DASHES.get(ch, ch) for ch in name)
    n = "".join(QUOTES.get(ch, ch) for ch in n)
    for k,v in UMLAUTS.items(): n = n.replace(k, v)
    n = HIDDEN_RE.sub("", n)
    # keep only ASCII; replace others with '-'
    n = "".join(ch if ord(ch) < 128 else "-" for ch in n)
    # collapse duplicate '-'s
    n = re.sub(r"-{2,}", "-", n)
    return n

def clean_text(txt: str) -> str:
    # normalize newlines
    txt = txt.replace("\r\n","\n").replace("\r","\n")
    # strip BOM if present
    if txt and txt[0] == "\ufeff": txt = txt[1:]
    # remove hidden chars
    txt = HIDDEN_RE.sub("", txt)
    return txt

def try_parse_json(s: str):
    try:
        return json.loads(s), None
    except json.JSONDecodeError as e1:
        # attempt to remove trailing commas and retry
        s2 = TRAILING_COMMAS_RE.sub("", s)
        if s2 != s:
            try:
                return json.loads(s2), None
            except json.JSONDecodeError as e2:
                return None, f"JSON parse failed (after trailing-comma fix): line {e2.lineno} col {e2.colno}: {e2.msg}"
        return None, f"JSON parse failed: line {e1.lineno} col {e1.colno}: {e1.msg}"

def check_required_keys(obj, path) -> list[str]:
    problems = []
    for k in REQUIRED_KEYS:
        if k not in obj: problems.append(f"missing '{k}'")
    rc = obj.get("runCommand")
    if isinstance(rc, dict):
        for k in REQUIRED_RUNCMD_KEYS:
            if k not in rc: problems.append(f"runCommand.{k} missing")
    else:
        problems.append("runCommand missing or not an object")
    if problems:
        problems.append("NOTE: Script did not auto-fix schema; adjust this hook manually.")
    return problems

def main():
    if not HOOKS_DIR.exists():
        print(f"ERROR: hooks directory not found: {HOOKS_DIR}", file=sys.stderr)
        sys.exit(2)

    print(f"Scanning: {HOOKS_DIR}")
    any_errors = False
    for f in sorted(HOOKS_DIR.glob("*.kiro.hook")):
        orig_name = f.name
        ascii_name = to_ascii_filename(orig_name)
        # rename if needed
        if ascii_name != orig_name:
            target = f.with_name(ascii_name)
            if target.exists(): target.unlink()
            print(f"Rename: '{orig_name}' -> '{ascii_name}'")
            f = f.rename(target)

        raw = f.read_bytes()
        try:
            text = raw.decode("utf-8", errors="ignore")
        except Exception:
            text = raw.decode("latin-1", errors="ignore")

        text = clean_text(text)
        obj, parse_err = try_parse_json(text)
        if obj is None:
            any_errors = True
            # write a .bad backup and continue
            bad = f.with_suffix(f.suffix + ".bad")
            bad.write_text(text, encoding="utf-8")
            print(f"!! JSON error in {f.name}: {parse_err}")
            print(f"   Kept original; wrote diagnostic copy: {bad.name}")
            continue

        # schema warnings
        problems = check_required_keys(obj, f)
        for p in problems:
            any_errors = True
            print(f"!! {f.name}: {p}")

        # stable ASCII dump
        ascii_text = json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True)
        f.write_text(ascii_text + "\n", encoding="ascii")
        print(f"Sanitized: {f.name}")

    # nudge file watchers
    HOOKS_DIR.touch()

    print("\nDone.")
    if any_errors:
        print("Some hooks need manual schema fixes (see warnings above).")
        sys.exit(1)

if __name__ == "__main__":
    main()
