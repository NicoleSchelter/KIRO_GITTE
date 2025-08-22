# Quality, Coding Standards & CI

Generated: 2025-08-21 12:13

## Coding Standards

- **Type hints** required for public functions
- **Docstrings** (Google or NumPy style)
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- **DRY & layering rules** strictly enforced

## Tooling

- **Formatter**: black
- **Import sorter**: isort
- **Linter**: ruff (or flake8)
- **Static typing**: mypy
- **Security**: bandit
- **Tests**: pytest + coverage

### Suggested Commands (PowerShell)

```powershell
ruff check src
black src
isort src
mypy src
bandit -r src
pytest --cov=src --cov-report=term-missing
```

## UX & Accessibility

- Use `src/ui/accessibility.py` to apply ARIA roles and keyboard navigation hints
- Keep user-facing messages in **UI layer**; translate texts centrally

## Error Handling

- Route exceptions through `src/utils/error_handler.py`
- Service outages → `src/utils/circuit_breaker.py` + `get_unhealthy_services()`
