# config/config.py (central settings)
# All settings live here and are re-exported by src/config.py.
# Keep English comments and string literals for consistency.

from dataclasses import dataclass, field

# --- Database ---
POSTGRES_DSN: str = "postgresql://gitte:sicheres_passwort@localhost:5432/kiro_test"

# --- LLM & Images ---
OLLAMA_URL: str = "http://localhost:11434"
SD_URL: str = "http://localhost:7860"

# --- Feature Flags ---
DEFER_BIAS_SCAN: bool = True          # heavy stereotype analysis deferred
PALD_LIGHT_ONLY: bool = True          # extract only PALD light in UI path
MAX_RETRIES: int = 3
TIMEOUT_SECONDS: int = 30
LOG_LEVEL: str = "INFO"
