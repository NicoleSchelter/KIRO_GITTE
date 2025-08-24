# Consent Enum/Key Mismatch Fixes - Implementation Summary

## Overview
This implementation addresses repository-wide data/enum/key mismatches causing consent and onboarding failures by implementing comprehensive root-cause fixes with strict layer architecture enforcement.

## Root Cause Analysis
1. **Enum/Key Mismatches**: UI used keys like `data_processing` while DB/Model expected `data_protection`
2. **Inconsistent String vs Enum Usage**: Mixed `.value` calls on strings and passing Enum where strings needed
3. **UI/Logic Contract Violations**: UI posted dicts with free-form keys; Logic expected enums
4. **Missing Validation**: No early failure with actionable errors before DB write
5. **Duplicate Factories/Circular Imports**: Multiple factory functions and forward reference issues

## Implementation Strategy

### 1. Canonical Consent Constants (src/data/models.py)
- **UNCHANGED**: StudyConsentType enum remains the single source of truth
- Enum values: `data_protection`, `ai_interaction`, `study_participation`

### 2. Central Key Normalization (src/logic/consent_logic.py)
**Changes Made:**
- Added `from __future__ import annotations`
- Implemented `_normalize_consent_key()` method with alias mapping:
  ```python
  self._consent_aliases = {
      "data_processing": StudyConsentType.DATA_PROTECTION,  # UI alias
      "data_protection": StudyConsentType.DATA_PROTECTION,  # Canonical
      "ai_interaction": StudyConsentType.AI_INTERACTION,
      "study_participation": StudyConsentType.STUDY_PARTICIPATION,
  }
  ```
- Added `InvalidConsentTypeError` with clear error messages listing valid enum values
- Enhanced `process_consent_collection()` to use normalization with debug logging
- Updated `record_bulk_consent()` to handle string-to-enum conversion

### 3. Configuration Centralization (config/config.py)
**Changes Made:**
- Added centralized consent configuration:
  ```python
  CONSENT_TYPES_UI = [
      ("data_protection", "Data protection (GDPR)"),
      ("ai_interaction", "AI interaction"),
      ("study_participation", "Study participation"),
  ]
  DEBUG_UI_CONSENT_KEYS = True
  ```

### 4. UI Layer Updates (src/ui/consent_ui.py)
**Changes Made:**
- Added `from __future__ import annotations`
- Updated imports to use `StudyConsentType` and `get_study_consent_service()`
- Modified `render_onboarding_consent()` to:
  - Read consent types from `CONSENT_TYPES_UI` config
  - Use canonical keys for consent payload
  - Add debug display when `DEBUG_UI_CONSENT_KEYS` enabled
  - Call `process_consent_collection()` with normalization
- Added `_get_consent_description_by_key()` for config-driven descriptions

### 5. Service Layer Enhancements (src/services/consent_service.py)
**Changes Made:**
- Enhanced `record_bulk_consent()` with transaction wrapping:
  ```python
  session.begin()
  try:
      result = consent_logic.record_bulk_consent(pseudonym_id, consents, metadata)
      session.commit()
      return result
  except Exception:
      session.rollback()
      raise
  ```

### 6. Repository Validation (src/data/repositories.py)
**Changes Made:**
- Enhanced `create_consent()` with strict enum validation:
  ```python
  if isinstance(consent_type, str):
      try:
          consent_type = StudyConsentType(consent_type)
      except ValueError:
          valid_types = [e.value for e in StudyConsentType]
          raise ValueError(f"Invalid study consent type '{consent_type}'. Valid: {valid_types}")
  ```
- Updated `get_by_pseudonym_and_type()` and `withdraw_consent()` with same validation
- Added early failure with actionable error messages

## Validation Results

### Import Smoke Test
✅ All core modules import successfully:
- `src.data.models`
- `src.data.repositories` 
- `src.logic.consent_logic`
- `src.services.consent_service`
- `src.ui.consent_ui`

### Consent E2E Dry Test
✅ Key normalization working:
- `data_processing` → `data_protection`
- `data_protection` → `data_protection`
- `ai_interaction` → `ai_interaction`
- `study_participation` → `study_participation`

✅ Invalid key handling:
- Invalid keys properly rejected with clear error messages
- Valid enum values listed in error messages

✅ Bulk processing:
- Transaction wrapping for database operations
- Partial failure handling with rollback
- Structured error reporting

### Layer Audit
✅ **UI Level**: Streamlit only in `src/ui/*`
✅ **Logic Level**: No UI imports in services/logic
✅ **Service Level**: Proper session management with `get_session()`
✅ **Data Level**: Strict enum validation in repositories

## Key Benefits

1. **DRY Principle**: Centralized constants/labels in `config/config.py`
2. **Early Validation**: Invalid consent types fail fast with clear messages
3. **Backward Compatibility**: UI aliases supported through normalization
4. **Transaction Safety**: Bulk operations wrapped in transactions
5. **Debug Support**: Normalization logging and debug UI display
6. **Type Safety**: Strict enum validation throughout pipeline

## Files Modified

1. **src/logic/consent_logic.py** - Central normalization and error handling
2. **config/config.py** - Centralized consent configuration
3. **src/ui/consent_ui.py** - Config-driven UI with normalization
4. **src/services/consent_service.py** - Transaction wrapping
5. **src/data/repositories.py** - Strict enum validation

## Testing Verification

All changes have been validated through:
- Import smoke tests (no circular dependencies)
- Consent normalization tests (key mapping works)
- Invalid key handling tests (proper error messages)
- Layer architecture audit (proper separation maintained)

The implementation successfully resolves all identified root causes while maintaining backward compatibility and adding robust error handling.