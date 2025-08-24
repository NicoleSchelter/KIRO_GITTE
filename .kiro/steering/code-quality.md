# Code Quality Rules

- Ruff (E,F,I,B), Black (line-length 100)
- Mypy strict for services/
- Bandit fail on HIGH severity
- Google-style docstrings
- No `print()`, no secrets, no TODO/FIXME in committed code
- No hardcoded consent literals outside `config/config.py` and `src/data/models.py`.
- New files using forward type hints must include `from __future__ import annotations`.
