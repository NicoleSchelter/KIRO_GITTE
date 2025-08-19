# scripts/auto_user_sim.py
"""
Headless automation runner that simulates a human user end-to-end.
This version auto-discovers real module/function names in the repo to avoid
hand-tuning when names differ (e.g., LLM_API vs Ollama_API, Pic_API vs sd_API).

Key features:
- Import discovery over src/services and src/logic with multiple candidates
- Probe mode (--probe) prints a compatibility report and writes JSON to exports/auto_runs/
- Uses Service/Logic/Data layers when present; otherwise falls back to JSONL exports
- No Streamlit imports; strict layer separation
- Ollama via HTTP when no LLM_API adapter is present
"""

from __future__ import annotations
import os
import sys
import json
import time
import uuid
import random
import argparse
import importlib
import importlib.util
import pkgutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ----- Repo paths (do not import UI) ----------------------------------------
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ----- Minimal external deps for safe fallback ------------------------------
import urllib.request
import urllib.error

# ----- Defaults (override in config.py or ENV) ------------------------------
DEFAULTS = {
    "OLLAMA_URL": os.getenv("OLLAMA_URL", "http://localhost:11434"),
    "CHAT_MODEL": "llama3.2",
    "VISION_MODEL": "llava:13b",
    "RUN_MINUTES": int(os.getenv("AUTO_RUN_MINUTES", "5")),
    "FEEDBACK_ROUNDS": int(os.getenv("AUTO_FEEDBACK_ROUNDS", "2")),
    "PALD_SCHEMA_PATH": os.getenv("PALD_SCHEMA_PATH", str(ROOT / "Basic files" / "pald_schema.json")),
    "EXPORT_DIR": str(ROOT / "exports" / "auto_runs"),
}

# ----- Utilities -------------------------------------------------------------
def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def log(msg: str):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ----- Import discovery ------------------------------------------------------
@dataclass
class DiscoveryResult:
    module: Optional[Any]
    module_path: Optional[str]
    chosen_attr: Optional[str]
    found_attrs: List[str]

def _find_spec(mod_path: str) -> bool:
    try:
        return importlib.util.find_spec(mod_path) is not None
    except Exception:
        return False

def _import_optional(mod_path: str) -> Optional[Any]:
    try:
        return importlib.import_module(mod_path)
    except Exception:
        return None

def list_available_under(prefix: str) -> List[str]:
    """List modules/packages under a given import prefix (e.g., 'src.services')."""
    mods = []
    try:
        spec = importlib.util.find_spec(prefix)
        if spec and spec.submodule_search_locations:
            for m in pkgutil.iter_modules(spec.submodule_search_locations):
                mods.append(f"{prefix}.{m.name}")
    except Exception:
        pass
    return sorted(mods)

# Candidate modules (multiple names supported to match your repo)
CANDIDATE_MODULES: Dict[str, List[str]] = {
    "student_service": [
        "src.services.student_service", "src.services.students", "src.services.user_service",
    ],
    "pald_service": [
        "src.services.PALD_service", "src.services.pald_service", "src.services.pald",
    ],
    "chat_service": [
        "src.services.chat_service", "src.services.conversation_service", "src.services.messages",
    ],
    "pic_api": [
        "src.services.Pic_API", "src.services.sd_API", "src.services.image_service",
    ],
    "llm_api": [
        "src.services.LLM_API", "src.services.Ollama_API", "src.services.llm_service",
    ],
    "gitte_logic": [
        "src.logic.GITTE_logic",
    ],
    "legal_logic": [
        "src.logic.legal_logic", "src.logic.Consent_logic",
    ],
    "config": [
        "config", "src.config",
    ],
}

# Candidate attribute names for each role (first match wins)
CANDIDATE_ATTRS: Dict[str, List[str]] = {
    "student_create": ["create_student", "create_user", "register_student"],
    "student_set_consent": ["set_consent", "store_consent", "save_consent"],
    "legal_store_consent": ["store_consent", "save_consent"],
    "chat_store_message": ["store_message", "save_message", "log_message"],
    "pald_save": ["save_pald", "store_pald", "persist_pald"],
    "llm_chat": ["chat", "ollama_chat", "generate"],
    "pic_class": ["StableDiffusionGenerator", "ImageGenerator", "Generator"],
}

def resolve_module(role: str) -> Optional[Any]:
    # ENV override: e.g., AUTO_MOD_student_service=src.services.student_service
    env_key = f"AUTO_MOD_{role}"
    forced = os.getenv(env_key)
    paths = [forced] if forced else CANDIDATE_MODULES.get(role, [])
    for p in paths:
        if not p:
            continue
        if _find_spec(p):
            mod = _import_optional(p)
            if mod:
                return mod
    return None

def discover_role(role: str, attr_candidates: List[str]) -> DiscoveryResult:
    module = resolve_module(role)
    module_path = None
    chosen_attr = None
    found_attrs: List[str] = []
    if module:
        module_path = module.__name__
        for name in attr_candidates:
            if hasattr(module, name):
                chosen_attr = name
                break
        # collect present attrs
        for name in attr_candidates:
            if hasattr(module, name):
                found_attrs.append(name)
    else:
        # not found
        pass
    return DiscoveryResult(module, module_path, chosen_attr, found_attrs)

def discover_all() -> Dict[str, DiscoveryResult]:
    return {
        "config": DiscoveryResult(resolve_module("config"), None, None, []),
        "student_service": discover_role("student_service", CANDIDATE_ATTRS["student_create"]),
        "pald_service": discover_role("pald_service", CANDIDATE_ATTRS["pald_save"]),
        "chat_service": discover_role("chat_service", CANDIDATE_ATTRS["chat_store_message"]),
        "pic_api": discover_role("pic_api", CANDIDATE_ATTRS["pic_class"]),
        "llm_api": discover_role("llm_api", CANDIDATE_ATTRS["llm_chat"]),
        "gitte_logic": DiscoveryResult(resolve_module("gitte_logic"), None, None, []),
        "legal_logic": discover_role("legal_logic", CANDIDATE_ATTRS["legal_store_consent"]),
    }

def write_compat_report(report_path: Path, info: Dict[str, Any]):
    ensure_dir(report_path.parent)
    report_path.write_text(json.dumps(info, indent=2), encoding="utf-8")

# ----- Config access ---------------------------------------------------------
def cfg_get(config_mod: Any, dotted: str, default: Any) -> Any:
    """Read config attribute like 'LLM_MODELS.chat'."""
    try:
        if not config_mod:
            return default
        cur = config_mod
        for part in dotted.split("."):
            cur = getattr(cur, part)
        return cur
    except Exception:
        return default

# ----- Ollama HTTP fallback --------------------------------------------------
def ollama_up(base: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=5):
            return True
    except Exception:
        return False

def ollama_chat_http(messages, model: str, base: str) -> str:
    req = urllib.request.Request(
        f"{base}/api/chat",
        data=json.dumps({"model": model, "messages": messages, "stream": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("message", {}).get("content", "")

# ----- PALD prompt builders --------------------------------------------------
def build_pald_light_prompt(user_text: str, schema_json: dict | None):
    schema_hint = ""
    if isinstance(schema_json, dict):
        keys = list(schema_json.keys())
        schema_hint = f"\nSchema keys (hint): {keys[:30]}\n"
    sysmsg = (
        "You are a parser that extracts a minimal 'PALD-Light' JSON from a natural language description. "
        "Only include fields that are clearly stated by the user. Do not invent values. "
        "Output strictly valid, compact JSON with keys grouped under 'global','medium','detail'."
        + schema_hint
    )
    usrmsg = (
        "Description:\n"
        f"{user_text}\n\n"
        "Return JSON object with keys: {\"global\":{...},\"medium\":{...},\"detail\":{...}}. "
        "Omit empty keys; do not include explanations."
    )
    return [{"role": "system", "content": sysmsg}, {"role": "user", "content": usrmsg}]

# ----- Persistence (duck-typed to discovered modules) -----------------------
class RepoAdapters:
    """Holds discovered modules and chosen attribute names."""
    def __init__(self, disc: Dict[str, DiscoveryResult], config_mod: Any):
        self.disc = disc
        self.config_mod = config_mod

    # --- student
    def create_student(self, pseudonym: str) -> str | None:
        d = self.disc["student_service"]
        if d.module and d.chosen_attr:
            try:
                fn = getattr(d.module, d.chosen_attr)
                sid = fn(pseudonym)
                return str(sid)
            except Exception as e:
                log(f"student_service.{d.chosen_attr} failed: {e}")
        return None

    # --- consent
    def store_consent(self, student_id: str, payload: dict) -> bool:
        # prefer legal_logic
        d_leg = self.disc["legal_logic"]
        if d_leg.module and d_leg.chosen_attr:
            try:
                fn = getattr(d_leg.module, d_leg.chosen_attr)
                fn(student_id, payload)
                return True
            except Exception as e:
                log(f"legal_logic.{d_leg.chosen_attr} failed: {e}")
        # fallback to student_service.set_consent-like
        d_stu = self.disc["student_service"]
        if d_stu.module:
            for name in CANDIDATE_ATTRS["student_set_consent"]:
                if hasattr(d_stu.module, name):
                    try:
                        getattr(d_stu.module, name)(student_id, payload)
                        return True
                    except Exception as e:
                        log(f"student_service.{name} failed: {e}")
        return False

    # --- chat messages
    def store_message(self, msg: dict) -> bool:
        d = self.disc["chat_service"]
        if d.module:
            for name in CANDIDATE_ATTRS["chat_store_message"]:
                if hasattr(d.module, name):
                    try:
                        getattr(d.module, name)(msg)
                        return True
                    except Exception as e:
                        log(f"chat_service.{name} failed: {e}")
        return False

    # --- pald save
    def save_pald(self, student_id: str, pald_json: dict, parent_id: Optional[str]) -> Optional[str]:
        d = self.disc["pald_service"]
        if d.module:
            for name in CANDIDATE_ATTRS["pald_save"]:
                if hasattr(d.module, name):
                    try:
                        res = getattr(d.module, name)(student_id, pald_json, parent_id=parent_id)
                        return str(res) if res else None
                    except Exception as e:
                        log(f"pald_service.{name} failed: {e}")
        return None

    # --- image generation (optional)
    def generate_image(self, pald_json: dict) -> Optional[dict]:
        d = self.disc["pic_api"]
        if d.module:
            for name in CANDIDATE_ATTRS["pic_class"]:
                if hasattr(d.module, name):
                    try:
                        klass = getattr(d.module, name)
                        gen = klass()  # expect default config inside
                        prompt = json.dumps(pald_json, ensure_ascii=False)
                        # We try a few likely method names:
                        for m in ["generate_image_from_prompt", "generate", "run", "create"]:
                            if hasattr(gen, m):
                                path = getattr(gen, m)(prompt)
                                return {"path": path, "prompt": prompt}
                    except Exception as e:
                        log(f"Pic API present but failed: {e}")
        log("Pic API not available; skipping image generation.")
        return None

    # --- LLM access (use LLM_API if present; else HTTP)
    def chat(self, messages: List[dict], model_fallback: str, base_url: str) -> str:
        d = self.disc["llm_api"]
        if d.module:
            for name in CANDIDATE_ATTRS["llm_chat"]:
                if hasattr(d.module, name):
                    try:
                        return getattr(d.module, name)(messages)
                    except Exception as e:
                        log(f"LLM_API.{name} failed, using HTTP fallback: {e}")
                        break
        # HTTP fallback to Ollama
        if not ollama_up(base_url):
            raise RuntimeError(f"Ollama not reachable at {base_url}")
        return ollama_chat_http(messages, model_fallback, base_url)

# ----- JSONL fallbacks -------------------------------------------------------
def append_jsonl(path: Path, obj: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ----- Core session ----------------------------------------------------------
def run_single_session(ad: RepoAdapters, cfg: dict, feedback_rounds: int = 2):
    export_dir = ensure_dir(Path(cfg["EXPORT_DIR"]))
    # Load schema hint
    schema_json = None
    try:
        p = Path(cfg["PALD_SCHEMA_PATH"])
        if p.exists():
            schema_json = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass

    # Create student
    pseudonym = f"auto_{random.randint(1000,9999)}"
    sid = ad.create_student(pseudonym)
    if not sid:
        sid = str(uuid.uuid4())
        append_jsonl(export_dir / "students.jsonl", {"student_id": sid, "pseudonym": pseudonym, "ts": now_iso()})
    log(f"student_id={sid}")

    # Consent
    consent = {"privacy": True, "study": True, "ai_use": True, "ts": now_iso()}
    if not ad.store_consent(sid, consent):
        append_jsonl(export_dir / "consents.jsonl", {"student_id": sid, **consent})

    # Initial intent via LLM
    system = "You create short, concrete design wishes for a pedagogical agent avatar."
    user = (
        "Please write a single-paragraph wish for how my learning assistant should look & act "
        "(style, age, realism, attire, cultural neutrality). Keep it factual."
    )
    initial_text = ad.chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                           model_fallback=cfg["CHAT_MODEL"], base_url=cfg["OLLAMA_URL"])
    msg0 = {"student_id": sid, "role": "user", "content": initial_text, "ts": now_iso()}
    if not ad.store_message(msg0):
        append_jsonl(export_dir / "chat_messages.jsonl", msg0)

    # PALD light
    pald_prompt = build_pald_light_prompt(initial_text, schema_json)
    pald_raw = ad.chat(pald_prompt, model_fallback=cfg["CHAT_MODEL"], base_url=cfg["OLLAMA_URL"])
    try:
        pald_json = json.loads(pald_raw)
    except json.JSONDecodeError:
        pald_json = {"global": {}, "medium": {}, "detail": {}}

    parent_id = ad.save_pald(sid, pald_json, parent_id=None)
    if not parent_id:
        parent_id = str(uuid.uuid4())
        append_jsonl(export_dir / "pald.jsonl", {
            "student_id": sid, "pald_id": parent_id, "parent_id": None, "pald": pald_json, "ts": now_iso()
        })

    # optional image
    img_info = ad.generate_image(pald_json)
    if img_info:
        msgi = {"student_id": sid, "role": "assistant", "content": f"[image] {img_info.get('path','')}",
                "kind": "image", "ts": now_iso()}
        if not ad.store_message(msgi):
            append_jsonl(export_dir / "chat_messages.jsonl", msgi)

    # feedback rounds
    for i in range(min(2, max(0, feedback_rounds))):
        fb_user = ad.chat(
            [
                {"role": "system", "content": "You are a picky student giving concise feedback to improve an avatar."},
                {"role": "user", "content": "Suggest one concrete change (age/style/neutrality/accessibility)."},
            ],
            model_fallback=cfg["CHAT_MODEL"], base_url=cfg["OLLAMA_URL"]
        )
        msgu = {"student_id": sid, "role": "user", "content": fb_user, "round": i+1, "ts": now_iso()}
        if not ad.store_message(msgu):
            append_jsonl(export_dir / "chat_messages.jsonl", msgu)

        fb_prompt = [
            {"role": "system",
             "content": "Update the previous PALD-Light JSON with the user's new feedback. Only change implied fields. Return full JSON."},
            {"role": "user", "content": f"Previous PALD:\n{json.dumps(pald_json, ensure_ascii=False)}\n\nFeedback:\n{fb_user}"},
        ]
        fb_raw = ad.chat(fb_prompt, model_fallback=cfg["CHAT_MODEL"], base_url=cfg["OLLAMA_URL"])
        try:
            pald_json = json.loads(fb_raw)
        except json.JSONDecodeError:
            pass  # keep previous if parse fails

        new_id = ad.save_pald(sid, pald_json, parent_id=parent_id)
        if not new_id:
            new_id = str(uuid.uuid4())
            append_jsonl(export_dir / "pald.jsonl", {
                "student_id": sid, "pald_id": new_id, "parent_id": parent_id, "pald": pald_json, "ts": now_iso()
            })
        parent_id = new_id

        img_info = ad.generate_image(pald_json)
        if img_info:
            msgi = {"student_id": sid, "role": "assistant", "content": f"[image] {img_info.get('path','')}",
                    "kind": "image", "round": i+1, "ts": now_iso()}
            if not ad.store_message(msgi):
                append_jsonl(export_dir / "chat_messages.jsonl", msgi)

    # closing summary
    summary = ad.chat(
        [{"role": "system", "content": "Summarize the final avatar in 2 sentences, factual tone."},
         {"role": "user", "content": json.dumps(pald_json, ensure_ascii=False)}],
        model_fallback=cfg["CHAT_MODEL"], base_url=cfg["OLLAMA_URL"]
    )
    msga = {"student_id": sid, "role": "assistant", "content": summary, "ts": now_iso()}
    if not ad.store_message(msga):
        append_jsonl(export_dir / "chat_messages.jsonl", msga)

    log(f"Session complete. student_id={sid}")

# ----- CLI / Main -----------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Auto user simulator for GITTE")
    parser.add_argument("--minutes", type=int, default=DEFAULTS["RUN_MINUTES"], help="Total runtime in minutes")
    parser.add_argument("--rounds", type=int, default=DEFAULTS["FEEDBACK_ROUNDS"], help="Feedback rounds per session")
    parser.add_argument("--probe", action="store_true", help="Only probe repo modules and exit")
    args = parser.parse_args()

    # Discovery
    disc = discover_all()
    # Config module (if present)
    config_mod = disc["config"].module if "config" in disc and disc["config"].module else None

    # Effective config (prefer config_mod values)
    cfg = {
        "OLLAMA_URL": os.getenv("OLLAMA_URL") or (getattr(config_mod, "LLM_BASE_URL", None) if config_mod else None) or DEFAULTS["OLLAMA_URL"],
        "CHAT_MODEL": (getattr(config_mod, "LLM_MODELS", {}).get("chat") if (config_mod and hasattr(config_mod, "LLM_MODELS")) else None) or DEFAULTS["CHAT_MODEL"],
        "VISION_MODEL": (getattr(config_mod, "LLM_MODELS", {}).get("vision") if (config_mod and hasattr(config_mod, "LLM_MODELS")) else None) or DEFAULTS["VISION_MODEL"],
        "PALD_SCHEMA_PATH": DEFAULTS["PALD_SCHEMA_PATH"],
        "EXPORT_DIR": DEFAULTS["EXPORT_DIR"],
    }

    # Report for probe
    report = {
        "found_services": {
            k: {
                "module": (v.module.__name__ if v.module else None),
                "chosen_attr": v.chosen_attr,
                "found_attrs": v.found_attrs,
            } for k, v in disc.items()
        },
        "available_under": {
            "src.services": list_available_under("src.services"),
            "src.logic": list_available_under("src.logic"),
        },
        "effective_config": cfg,
        "hints": {
            "env_overrides": {
                "AUTO_MOD_student_service": "src.services.student_service",
                "AUTO_MOD_pald_service": "src.services.PALD_service",
                "AUTO_MOD_chat_service": "src.services.chat_service",
                "AUTO_MOD_pic_api": "src.services.Pic_API",
                "AUTO_MOD_llm_api": "src.services.LLM_API",
                "AUTO_MOD_legal_logic": "src.logic.legal_logic",
            },
            "attr_aliases": CANDIDATE_ATTRS,
        },
        "ts": now_iso(),
    }
    report_path = Path(DEFAULTS["EXPORT_DIR"]) / "compat_report.json"
    write_compat_report(report_path, report)

    if args.probe:
        log("== PROBE RESULT ==")
        for k, v in report["found_services"].items():
            log(f"{k:15s} module={v['module']!r} chosen_attr={v['chosen_attr']!r} found={v['found_attrs']}")
        log(f"Report written to: {report_path}")
        return

    # Run sessions for N minutes
    end_ts = time.time() + 60 * int(args.minutes)
    rounds = int(args.rounds)
    ad = RepoAdapters(disc, config_mod)

    log(f"Auto-run started for ~{args.minutes} minutes, feedback_rounds={rounds}")
    while time.time() < end_ts:
        try:
            run_single_session(ad, cfg, feedback_rounds=rounds)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Session failed: {e}")
        time.sleep(5)
    log("Auto-run finished.")

if __name__ == "__main__":
    main()
