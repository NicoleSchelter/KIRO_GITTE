# Consent Write-Path Fixes - Quick Reference

## 🎯 What Was Fixed

### Core Issues Resolved
- ✅ **ForeignKeyViolation**: Added pseudonym existence checks
- ✅ **Session rollbacks**: Implemented fresh sessions with proper transactions  
- ✅ **Enum mismatches**: Added consent key normalization (`data_processing` → `data_protection`)
- ✅ **Import safety**: Verified no sessions created at import time
- ✅ **Layer boundaries**: Maintained clean architecture

## 🔧 Key Changes Made

### 1. Enhanced Repository (`src/data/repositories.py`)
```python
# NEW: FK validation before consent creation
pseudonym_exists = self.session.query(
    self.session.query(Pseudonym).filter(
        Pseudonym.pseudonym_id == pseudonym_id
    ).exists()
).scalar()

if not pseudonym_exists:
    raise MissingPseudonymError(f"Pseudonym {pseudonym_id} does not exist")
```

### 2. Consent Key Normalization (`src/logic/consent_logic.py`)
```python
# NEW: Centralized alias mapping
self._consent_aliases = {
    "data_processing": StudyConsentType.DATA_PROTECTION,  # UI → DB mapping
    "data_protection": StudyConsentType.DATA_PROTECTION,
    "ai_interaction": StudyConsentType.AI_INTERACTION,
    "study_participation": StudyConsentType.STUDY_PARTICIPATION,
}
```

### 3. Transaction Safety (`src/services/consent_service.py`)
```python
# NEW: Explicit transaction boundaries
with get_session() as session:
    with session.begin():  # Auto-commit on success, rollback on error
        self._session = session
        result = consent_logic.record_consent(...)
        return result
```

### 4. New Exception (`src/exceptions.py`)
```python
class MissingPseudonymError(DatabaseError):
    """Pseudonym does not exist for FK constraint."""
    # Provides clear error message for FK violations
```

## 📋 Usage Examples

### Consent Collection (UI → Service)
```python
# UI sends this payload:
consents = {
    "data_processing": True,      # Will normalize to "data_protection"
    "ai_interaction": True,       # Maps directly
    "study_participation": True   # Maps directly
}

# Service processes with normalization:
result = consent_service.process_consent_collection(pseudonym_id, consents)
```

### Error Handling
```python
try:
    consent_service.record_consent(pseudonym_id, consent_type, granted)
except MissingPseudonymError:
    # Handle missing pseudonym (FK violation)
    show_error("Invalid participant identifier")
except ConsentError as e:
    # Handle other consent-related errors
    show_error(f"Consent error: {e}")
```

## 🧪 Validation Commands

### Quick Smoke Test
```bash
python -c "
from src.data.models import StudyConsentType
from src.logic.consent_logic import ConsentLogic
from src.services.consent_service import ConsentService
print('✅ All imports successful')
"
```

### Full Validation
```bash
python scripts/validate_consent_fixes.py
python scripts/test_consent_e2e_dry.py
```

## 🎯 Key Mappings

### UI Keys → Database Enums
| UI Key | Database Enum | Notes |
|--------|---------------|-------|
| `data_processing` | `DATA_PROTECTION` | **Alias mapping** |
| `data_protection` | `DATA_PROTECTION` | Direct mapping |
| `ai_interaction` | `AI_INTERACTION` | Direct mapping |
| `study_participation` | `STUDY_PARTICIPATION` | Direct mapping |

### Config Reference
```python
# config/config.py
CONSENT_TYPES_UI = [
    ("data_protection", "Data protection (GDPR)"),
    ("ai_interaction", "AI interaction"), 
    ("study_participation", "Study participation"),
]
```

## 🚨 Important Notes

### Transaction Patterns
- ✅ **DO**: Use `with get_session() as session:` for each operation
- ✅ **DO**: Use `with session.begin():` for explicit transactions
- ❌ **DON'T**: Reuse sessions across operations
- ❌ **DON'T**: Create sessions at import time

### Error Handling
- ✅ **DO**: Catch `MissingPseudonymError` for FK violations
- ✅ **DO**: Use typed exceptions (`ConsentError`, `ConsentRequiredError`)
- ❌ **DON'T**: Catch raw SQLAlchemy exceptions in business logic
- ❌ **DON'T**: Ignore FK constraint errors

### Enum Usage
- ✅ **DO**: Use `StudyConsentType` as canonical source of truth
- ✅ **DO**: Normalize UI keys through `ConsentLogic._normalize_consent_key()`
- ❌ **DON'T**: Use raw strings for consent types in business logic
- ❌ **DON'T**: Bypass normalization in consent processing

## 🔍 Troubleshooting

### Common Issues & Solutions

**Issue**: `ForeignKeyViolation on pseudonym_id`
```python
# Solution: Check pseudonym exists first
if not pseudonym_exists:
    raise MissingPseudonymError(f"Pseudonym {pseudonym_id} does not exist")
```

**Issue**: `Session rollback errors`
```python
# Solution: Use fresh sessions with explicit transactions
with get_session() as session:
    with session.begin():
        # Your database operations here
        pass  # Auto-commit on success
```

**Issue**: `Invalid consent type 'data_processing'`
```python
# Solution: Use normalization
normalized_type = consent_logic._normalize_consent_key("data_processing")
# Result: StudyConsentType.DATA_PROTECTION
```

## 📚 Related Files

### Core Implementation
- `src/data/models.py` - StudyConsentType enum
- `src/data/repositories.py` - StudyConsentRepository with FK validation
- `src/logic/consent_logic.py` - ConsentLogic with normalization
- `src/services/consent_service.py` - ConsentService with transactions
- `src/ui/consent_ui.py` - ConsentUI with proper key handling
- `src/exceptions.py` - MissingPseudonymError and related exceptions

### Configuration
- `config/config.py` - CONSENT_TYPES_UI configuration
- `.kiro/hooks/` - All validation hooks (15 files, all validated ✅)

### Testing & Validation
- `scripts/validate_consent_fixes.py` - Core functionality tests
- `scripts/test_consent_e2e_dry.py` - End-to-end dry run tests
- `CONSENT_WRITE_PATH_FIXES_SUMMARY.md` - Detailed implementation summary

## ✅ Success Criteria Met

- [x] No more FK violations in logs
- [x] Consent operations succeed only with valid pseudonyms  
- [x] Invalid pseudonym → domain error, not DB traceback
- [x] Retries use fresh sessions, no rollback errors
- [x] UI keys ↔ Enums consistent and validated
- [x] No duplicate factories, forward-ref issues, or import-time sessions
- [x] All pre-commit hooks pass
- [x] Tests for contract/property/type pass
- [x] Coverage threshold maintained

🎉 **All consent write-path fixes implemented and validated successfully!**