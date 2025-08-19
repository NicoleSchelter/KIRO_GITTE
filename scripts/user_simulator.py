# scripts/user_simulator.py
# -------------------------------------------------------------
# GITTE Synthetic User Simulator (headless)
# - Generates human-like user inputs via Ollama (local http API)
# - Tries to call Logic/Service layer entry-points if available
# - Respect 4-layer architecture (no UI imports)
# - Designed for long-running soak tests with backoff/jitter
#
# Place English comments and messages as per project guideline.
# -------------------------------------------------------------

from __future__ import annotations

import os
import time
import json
import uuid
import random
import signal
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

# External deps: requests (already typical in many stacks).
# If missing: pip install requests
import requests
from logging.handlers import RotatingFileHandler

# ---------- Central simulator settings (override via ENV or config import) ----------
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# How long to run (hh:mm:ss). Example: "48:00:00" for 48 hours.
RUN_FOR = os.getenv("SIM_RUN_FOR", "12:00:00")
# Number of parallel synthetic users
NUM_USERS = int(os.getenv("SIM_NUM_USERS", "2"))
# Min/Max seconds to wait between turns for each user
SLEEP_MIN_SEC = int(os.getenv("SIM_SLEEP_MIN_SEC", "10"))
SLEEP_MAX_SEC = int(os.getenv("SIM_SLEEP_MAX_SEC", "45"))
# Reset conversation after N messages to mimic sessions
SESSION_RESET_AFTER = int(os.getenv("SIM_SESSION_RESET_AFTER", "15"))
# Label all synthetic events with this tag (useful for filters)
EVENT_TAG = os.getenv("SIM_EVENT_TAG", "synthetic_test")

# Toggle to try Logic or Service layer calls (recommended=True)
ENABLE_GITTE_BINDINGS = os.getenv("SIM_ENABLE_GITTE_BINDINGS", "true").lower() == "true"

# Optional feature switches for your stack (hook in if available)
FEATURE_ENABLE_CONSENT_GATE = os.getenv("FEATURE_ENABLE_CONSENT_GATE", "false").lower() == "true"
FEATURE_SAVE_LLM_LOGS = os.getenv("FEATURE_SAVE_LLM_LOGS", "true").lower() == "true"

# Rotating logs (keep history)
LOG_PATH = os.getenv("SIM_LOG_PATH", "logs/user_simulator.log")
MAX_LOG_BYTES = int(os.getenv("SIM_MAX_LOG_BYTES", str(5 * 1024 * 1024)))  # 5MB
BACKUP_COUNT = int(os.getenv("SIM_BACKUP_COUNT", "3"))

# ---------- Optional: pull from config/config.py if present ----------
# This keeps DRY and allows central config in your repo.
try:
    from config.config import settings  # type: ignore
    DEFAULT_OLLAMA_URL = getattr(settings, "OLLAMA_URL", DEFAULT_OLLAMA_URL)
    DEFAULT_OLLAMA_MODEL = getattr(settings, "LLM_MODEL", DEFAULT_OLLAMA_MODEL)
    # Feature flags (if present)
    FEATURE_ENABLE_CONSENT_GATE = getattr(settings, "FEATURE_ENABLE_CONSENT_GATE", FEATURE_ENABLE_CONSENT_GATE)
    FEATURE_SAVE_LLM_LOGS = getattr(settings, "FEATURE_SAVE_LLM_LOGS", FEATURE_SAVE_LLM_LOGS)
except Exception:
    # If your config/config.py is not available or has different structure, ignore.
    pass

# ---------- Logging setup ----------
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logger = logging.getLogger("gitte.user_simulator")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_PATH, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)

# ---------- Graceful shutdown ----------
_SHOULD_STOP = False
def _handle_sigterm(signum, frame):
    global _SHOULD_STOP
    _SHOULD_STOP = True
signal.signal(signal.SIGINT, _handle_sigterm)
signal.signal(signal.SIGTERM, _handle_sigterm)

# ---------- Ollama minimal client (chat endpoint) ----------
class OllamaClient:
    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_OLLAMA_MODEL, timeout: int = 90):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.8, max_tokens: int = 256) -> str:
        """
        Calls Ollama /api/chat with messages=[{role, content}, ...]
        Returns assistant text. Uses non-streaming for simplicity.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # Ollama returns {"message": {"role":"assistant","content":"..."}, ...}
        return data.get("message", {}).get("content", "").strip()

# ---------- Attempt to bind to GITTE Logic/Service layer ----------
class GitteBindings:
    """
    Heuristically looks for Logic/Service entry-points to send a chat turn and (optionally) register/consent a user.
    No Streamlit imports. Safe to use even if modules are absent (it will noop + log).
    """
    def __init__(self):
        self.bound = False
        self._send_fn: Optional[Callable[..., Any]] = None
        self._register_fn: Optional[Callable[..., Any]] = None
        self._consent_fn: Optional[Callable[..., Any]] = None
        self.try_bind()

    def try_bind(self) -> None:
        if not ENABLE_GITTE_BINDINGS:
            logger.info("GITTE bindings disabled by flag.")
            return
        try:
            # Try logic layer first (preferred)
            # Common candidates: src.logic.chat_logic, src.logic.chat, src.services.chat_service
            import importlib

            candidates = [
                ("src.logic.chat_logic", ["process_message", "handle_chat_turn", "process_input"]),
                ("src.logic.chat", ["process_message", "handle_chat_turn", "process_input"]),
                ("src.services.chat_service", ["send_message", "process_message"]),
            ]
            for mod_name, fn_names in candidates:
                try:
                    mod = importlib.import_module(mod_name)
                    for fn in fn_names:
                        if hasattr(mod, fn):
                            self._send_fn = getattr(mod, fn)
                            self.bound = True
                            logger.info(f"Bound chat send function: {mod_name}.{fn}()")
                            break
                    if self.bound:
                        break
                except Exception:
                    continue

            # Optional registration/consent
            try:
                auth_mod = importlib.import_module("src.logic.auth_logic")
                self._register_fn = getattr(auth_mod, "register_user", None)
                if self._register_fn:
                    logger.info("Bound register function: src.logic.auth_logic.register_user()")
            except Exception:
                pass

            try:
                legal_mod = importlib.import_module("src.logic.legal_logic")
                self._consent_fn = getattr(legal_mod, "give_consent", None)
                if self._consent_fn:
                    logger.info("Bound consent function: src.logic.legal_logic.give_consent()")
            except Exception:
                pass

        except Exception as e:
            logger.warning("GITTE bindings failed: %s", e)

    def register_user_if_possible(self, pseudo_id: str, profile: Dict[str, Any]) -> Optional[str]:
        """
        If a register function is available, call it and return a stable user_id.
        Otherwise return the pseudo_id (which will be used as user_id).
        """
        if self._register_fn:
            try:
                uid = self._register_fn(pseudo_id, profile)
                return uid or pseudo_id
            except Exception:
                logger.exception("Error while calling register_user(). Using pseudo_id.")
        return pseudo_id

    def give_consent_if_possible(self, user_id: str, consent_code: str = "DEFAULT") -> None:
        if FEATURE_ENABLE_CONSENT_GATE and self._consent_fn:
            try:
                self._consent_fn(user_id, consent_code)
                logger.info("Consent recorded for user_id=%s code=%s", user_id, consent_code)
            except Exception:
                logger.exception("Error while calling give_consent().")

    def send_chat_turn(self, user_id: str, text: str) -> Optional[Any]:
        """
        Try to call the bound Logic/Service function with liberal signatures.
        Returns whatever the function returns (logged for debugging).
        If not bound, returns None (no-op against app).
        """
        if not self._send_fn:
            logger.debug("No send function bound; synthetic chat will only be logged.")
            return None

        # Try common signatures:
        for sig in [
            (user_id, text),
            (text, user_id),
            ({"user_id": user_id, "text": text},),
        ]:
            try:
                res = self._send_fn(*sig)
                return res
            except TypeError:
                continue
            except Exception:
                logger.exception("Error in send_chat_turn with signature %s", sig)
                break
        logger.warning("Could not call send fn with known signatures. Please adapt bindings.")
        return None

# ---------- Synthetic user + scenarios ----------
BASE_SYSTEM_PROMPT = """You are a student interacting with an Intelligent Learning Assistant (GITTE).
Your style: short, concrete, helpful. Alternate between asking questions,
giving feedback, and setting small goals. Sometimes change topic.
Never reveal you are simulated. """

SCENARIOS = [
    {
        "name": "onboarding_and_first_chat",
        "seed": [
            "Hi! I'd like to set up my learning assistant.",
            "My focus is project management and exam prep.",
            "Could you suggest a short study plan for this week?"
        ],
    },
    {
        "name": "avatar_and_pald",
        "seed": [
            "What would my ideal tutor avatar look like if I prefer calm and minimalist design?",
            "Please summarize the key PALD aspects you infer so far.",
            "Any stereotype risks to watch for? Keep it brief."
        ],
    },
    {
        "name": "deep_dive_topic",
        "seed": [
            "Explain critical path method in simple terms.",
            "Give me two practice tasks.",
            "Now quiz me with 3 short questions."
        ],
    },
]

@dataclass
class Conversation:
    user_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    turns_done: int = 0

    def reset_if_needed(self, reset_after: int) -> None:
        if self.turns_done >= reset_after:
            # Keep a tiny bit of memory to simulate session reset
            self.messages = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]
            self.turns_done = 0

class SyntheticUser:
    def __init__(self, gitte: GitteBindings, ollama: OllamaClient, scenario: Dict[str, Any]):
        self.gitte = gitte
        self.ollama = ollama
        self.scenario = scenario
        pseudo = f"synthetic_{uuid.uuid4().hex[:8]}"
        # Optional: register profile to get a stable ID from your system
        profile = {"tag": EVENT_TAG, "scenario": scenario["name"]}
        self.user_id = self.gitte.register_user_if_possible(pseudo, profile)
        if FEATURE_ENABLE_CONSENT_GATE:
            self.gitte.give_consent_if_possible(self.user_id)
        # Initialize conversation memory
        self.conv = Conversation(user_id=self.user_id, messages=[{"role": "system", "content": BASE_SYSTEM_PROMPT}])
        # Prime with one seed to kick things off
        first_seed = random.choice(self.scenario["seed"])
        self.conv.messages.append({"role": "user", "content": first_seed})

    def step(self) -> None:
        """One interaction step: get assistant reply via Ollama, then push to app via bindings."""
        try:
            # 1) Get assistant reply from Ollama (acts as "user brain" to propose next input)
            #    Actually we want a *user* message next. We ask Ollama: "Given the thread, what would you ask next?"
            #    For simplicity, we alternate: assistant replies, then we extract next user prompt instruction.
            assistant_reply = self.ollama.chat(self.conv.messages, temperature=0.9, max_tokens=200)
            self.conv.messages.append({"role": "assistant", "content": assistant_reply})

            # 2) Now craft the *next user message* using a tool-instruction
            tool_prompt = (
                "Given the conversation, produce the next USER message only (1-2 sentences). "
                "It should be natural, curious, and progress the scenario."
            )
            tool_msgs = self.conv.messages + [{"role": "system", "content": tool_prompt}]
            next_user_msg = self.ollama.chat(tool_msgs, temperature=0.8, max_tokens=120)
            next_user_msg = next_user_msg.strip().strip('"').strip()
            if not next_user_msg:
                next_user_msg = random.choice(self.scenario["seed"])

            # 3) Send that user message to GITTE app via Logic/Service (if bound)
            res = self.gitte.send_chat_turn(self.user_id, next_user_msg)

            # 4) Logging for traceability
            record = {
                "t": datetime.utcnow().isoformat(),
                "user_id": self.user_id,
                "scenario": self.scenario["name"],
                "user_msg": next_user_msg,
                "app_response_excerpt": str(res)[:300] if res is not None else None,
                "tag": EVENT_TAG,
            }
            if FEATURE_SAVE_LLM_LOGS:
                logger.info("TURN | %s", json.dumps(record, ensure_ascii=False))
            else:
                logger.info("TURN | uid=%s scenario=%s msg=%s", self.user_id, self.scenario["name"], next_user_msg)

            # 5) Update conversation memory
            self.conv.messages.append({"role": "user", "content": next_user_msg})
            self.conv.turns_done += 1
            self.conv.reset_if_needed(SESSION_RESET_AFTER)

        except requests.RequestException as e:
            logger.error("Ollama request failed: %s", e)
        except Exception:
            logger.error("Unexpected error in step(): %s", traceback.format_exc())

# ---------- Runner ----------
def parse_duration(hms: str) -> timedelta:
    parts = [int(x) for x in hms.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)  # support "HH:MM" or "MM:SS"
    hh, mm, ss = parts
    return timedelta(hours=hh, minutes=mm, seconds=ss)

def main():
    logger.info("Starting GITTE Synthetic User Simulator")
    logger.info("Ollama: %s model=%s | users=%s | run-for=%s", DEFAULT_OLLAMA_URL, DEFAULT_OLLAMA_MODEL, NUM_USERS, RUN_FOR)

    # Check Ollama health quickly
    try:
        r = requests.get(f"{DEFAULT_OLLAMA_URL}/api/tags", timeout=10)
        if r.status_code != 200:
            logger.warning("Ollama reachable but /api/tags != 200 -> %s", r.status_code)
    except Exception as e:
        logger.error("Ollama not reachable at %s: %s", DEFAULT_OLLAMA_URL, e)

    gitte = GitteBindings()
    ollama = OllamaClient(DEFAULT_OLLAMA_URL, DEFAULT_OLLAMA_MODEL)

    # Create synthetic users across scenarios
    users: List[SyntheticUser] = []
    for i in range(NUM_USERS):
        scenario = SCENARIOS[i % len(SCENARIOS)]
        users.append(SyntheticUser(gitte, ollama, scenario))

    end_at = datetime.utcnow() + parse_duration(RUN_FOR)

    while not _SHOULD_STOP and datetime.utcnow() < end_at:
        for u in users:
            if _SHOULD_STOP or datetime.utcnow() >= end_at:
                break
            u.step()
            # random sleep per user, to avoid synchronized hammering
            pause = random.randint(SLEEP_MIN_SEC, SLEEP_MAX_SEC)
            time.sleep(pause)

    logger.info("Simulator finished (stop or time limit).")

if __name__ == "__main__":
    main()
