#!/usr/bin/env python
import json, sys, pathlib, re
root = pathlib.Path("hooks") if pathlib.Path("hooks").exists() else pathlib.Path(".")
bad=[]
for f in root.rglob("*.kiro.hook"):
    t = f.read_text(encoding="utf-8", errors="strict")
    # crude: refuse trailing commas (common VSCode edit accident)
    if re.search(r",\s*[}\]]", t) is None and ('{' not in t or '}' not in t):
        bad.append((f, "not an object?"))
        continue
    try:
        obj = json.loads(t)
    except Exception as e:
        bad.append((f, f"JSON error: {e}"))
        continue
    for k in ["enabled","name","triggers","runCommand"]:
        if k not in obj: bad.append((f, f"missing '{k}'"))
    rc = obj.get("runCommand", {})
    for k in ["shell","args"]:
        if k not in rc: bad.append((f, f"runCommand.{k} missing"))
if bad:
    print("Hook validation FAILED:")
    for f,msg in bad: print(f" - {f}: {msg}")
    sys.exit(1)
print("All hooks parse and contain required keys.")
