# Development Workflow

- Trunk-based dev
- Feature branches: feature/<id>, fix/<id>, chore/<desc>
- Conventional Commits + SemVer
- Required checks: ruff, black, mypy, pytest (fast), bandit
- Release steps: bump version → tag → build → smoke test → prod
- Local cycle: format → lint → typecheck → targeted tests → layer audit → consent audit. 
- Pre-commit blocks on: ruff, black, mypy (strict in services/), layer audit, consent audit, forward-ref audit, DB import guard.