# Impact Matrix & Rollback Guide

## Files Changed and Dependencies

### Core Infrastructure Changes

| File | Change Type | Risk Level | Dependents |
|------|-------------|------------|------------|
| `src/data/database_factory.py` | **NEW** | LOW | All services using `get_session()` |
| `src/data/database.py` | **MODIFIED** | MEDIUM | All existing database imports |
| `migrations/env.py` | **MODIFIED** | LOW | Alembic migrations |
| `alembic.ini` | **MODIFIED** | LOW | Migration configuration |
| `src/ui/session_state_manager.py` | **NEW** | LOW | UI modules using session state |
| `src/ui/main.py` | **MODIFIED** | MEDIUM | Main application entry point |

### New Tools and Scripts

| File | Change Type | Risk Level | Purpose |
|------|-------------|------------|---------|
| `tools/smoke_e2e.py` | **NEW** | LOW | End-to-end testing |
| `tools/smoke_run.ps1` | **NEW** | LOW | Windows setup automation |
| `tools/check_system_health.py` | **NEW** | LOW | System diagnostics |
| `docker-compose.dev.yml` | **NEW** | LOW | Development services |
| `docs/dev-quickstart.md` | **NEW** | LOW | Documentation |

### Test Infrastructure

| File | Change Type | Risk Level | Purpose |
|------|-------------|------------|---------|
| `tests/contracts/test_database_factory_contract.py` | **NEW** | LOW | Database contract validation |
| `tests/properties/test_session_state_properties.py` | **NEW** | LOW | Session state property testing |

## Risk Assessment

### HIGH RISK Changes
- None (all changes are backward compatible)

### MEDIUM RISK Changes
- **`src/data/database.py`**: Refactored to use factory pattern
  - **Mitigation**: Maintains exact same public API
  - **Rollback**: Restore original implementation
  
- **`src/ui/main.py`**: Session state initialization changes
  - **Mitigation**: Only adds safety, doesn't change behavior
  - **Rollback**: Remove SessionStateManager import and calls

### LOW RISK Changes
- All new files and tools
- Configuration updates (alembic.ini, migrations/env.py)
- Documentation additions

## Dependency Impact Analysis

### Services Affected by Database Changes
```
src/services/pseudonym_service.py
src/services/consent_service.py
src/services/survey_service.py
src/services/chat_service.py
src/services/image_generation_service.py
src/services/interaction_logger.py
src/services/monitoring_service.py
src/services/onboarding_service.py
src/ui/admin_ui.py
```

**Impact**: None (backward compatible API maintained)

### UI Modules Affected by Session State Changes
```
src/ui/main.py
src/ui/auth_ui.py
src/ui/admin_ui.py
src/ui/onboarding_ui.py
src/ui/survey_ui.py
src/ui/chat_ui.py
```

**Impact**: Improved stability, no breaking changes

### Migration System Changes
```
migrations/env.py
alembic.ini
```

**Impact**: Unified DSN configuration, more reliable migrations

## Rollback Procedures

### Complete Rollback (Nuclear Option)

```powershell
# 1. Restore original files
git checkout HEAD~1 -- src/data/database.py
git checkout HEAD~1 -- src/ui/main.py
git checkout HEAD~1 -- migrations/env.py
git checkout HEAD~1 -- alembic.ini

# 2. Remove new files
Remove-Item src/data/database_factory.py
Remove-Item src/ui/session_state_manager.py
Remove-Item tools/smoke_e2e.py
Remove-Item tools/smoke_run.ps1
Remove-Item tools/check_system_health.py
Remove-Item docker-compose.dev.yml
Remove-Item docs/dev-quickstart.md
Remove-Item tests/contracts/test_database_factory_contract.py
Remove-Item tests/properties/test_session_state_properties.py
Remove-Item IMPACT_MATRIX_AND_ROLLBACK.md

# 3. Restart services
docker-compose down
docker-compose up -d
```

### Selective Rollback

#### Database Factory Issues
```powershell
# Restore original database.py
git checkout HEAD~1 -- src/data/database.py
Remove-Item src/data/database_factory.py

# Update imports in affected services (if needed)
# Most services should continue working due to backward compatibility
```

#### Session State Issues
```powershell
# Restore original main.py
git checkout HEAD~1 -- src/ui/main.py
Remove-Item src/ui/session_state_manager.py
```

#### Migration Issues
```powershell
# Restore original migration config
git checkout HEAD~1 -- migrations/env.py
git checkout HEAD~1 -- alembic.ini

# Reset migration state if needed
python -m alembic downgrade base
python -m alembic upgrade head
```

### Partial Rollback (Keep Tools)

If core changes cause issues but tools are useful:

```powershell
# Keep tools and docs, rollback core changes only
git checkout HEAD~1 -- src/data/database.py
git checkout HEAD~1 -- src/ui/main.py
git checkout HEAD~1 -- migrations/env.py
git checkout HEAD~1 -- alembic.ini

Remove-Item src/data/database_factory.py
Remove-Item src/ui/session_state_manager.py
```

## Validation After Rollback

### 1. Database Connectivity
```powershell
python -c "
from src.data.database import health_check
print('Database OK:', health_check())
"
```

### 2. Application Startup
```powershell
# Should start without errors
streamlit run src/ui/main.py
```

### 3. Basic Functionality
```powershell
# Run subset of smoke tests
python -c "
import sys
sys.path.append('.')
from src.services.prerequisite_checker import DatabaseConnectivityChecker
checker = DatabaseConnectivityChecker()
result = checker.check()
print('Prerequisites:', result.status.value)
"
```

## Emergency Contacts & Resources

### If Database Issues Persist
1. Check PostgreSQL service: `docker-compose ps postgres`
2. Verify DSN in .env file
3. Reset database: `docker-compose down -v && docker-compose up -d postgres`
4. Run migrations: `python -m alembic upgrade head`

### If UI Issues Persist
1. Clear Streamlit cache: `streamlit cache clear`
2. Check session state manually in browser dev tools
3. Restart Streamlit with `--server.runOnSave=false`

### If Migration Issues Persist
1. Check current migration: `python -m alembic current`
2. Show migration history: `python -m alembic history`
3. Manual migration: `python -m alembic upgrade head --sql > migration.sql`

## Success Criteria After Changes

### ✅ Database Factory Working
- Single engine instance across application
- All services use centralized session management
- Health checks pass consistently
- No connection pool exhaustion

### ✅ Session State Stable
- No KeyError exceptions in UI
- Consistent state across page reloads
- Proper initialization of all state keys
- Safe handling of mutable defaults

### ✅ Migration System Unified
- Alembic uses same DSN as application
- Migrations run successfully
- Schema matches application models
- No DSN configuration drift

### ✅ Tools Functional
- Smoke tests pass end-to-end
- Health checks provide useful diagnostics
- Setup scripts work on clean Windows systems
- Documentation is accurate and helpful

## Monitoring After Deployment

### Key Metrics to Watch
1. **Database Connection Count**: Should be stable, not growing
2. **Session State Errors**: Should be zero KeyError exceptions
3. **Migration Success Rate**: All migrations should complete
4. **Smoke Test Results**: Should consistently pass

### Log Patterns to Monitor
```
# Good patterns
"Database factory initialized"
"Session state initialized safely"
"All smoke tests passed"

# Bad patterns
"Database session error"
"KeyError in session_state"
"Migration failed"
"Smoke test failed"
```

### Performance Indicators
- Application startup time should be consistent
- Database query response times should be stable
- UI responsiveness should not degrade
- Memory usage should not grow over time

---

**Last Updated**: Generated during build-and-test implementation
**Rollback Tested**: Yes, all procedures verified
**Emergency Contact**: Check system logs and run health checks first