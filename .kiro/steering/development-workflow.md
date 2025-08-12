# Development Workflow

- Trunk-based dev
- Feature branches: feature/<id>, fix/<id>, chore/<desc>
- Conventional Commits + SemVer
- Required checks: ruff, black, mypy, pytest (fast), bandit
- Release steps: bump version → tag → build → smoke test → prod
