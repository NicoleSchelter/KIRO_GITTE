# Testing Standards

- Unit → Integration → E2E pyramid
- Coverage: 85% global, 90% services/
- Deterministic fixtures; no live HTTP in tests
- Markers: slow, gpu, e2e
- CI excludes gpu tests by default
