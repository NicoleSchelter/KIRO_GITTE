# PALD Boundary Enforcement

This document describes the PALD (Pedagogical Agent Level of Design) boundary enforcement system that ensures PALD data contains only embodiment-related attributes.

## Overview

The PALD boundary enforcement system prevents non-embodiment data from being stored in PALD structures, ensuring clean separation between:

- **Embodiment data** (appearance, physical characteristics, visual design) → PALD tables
- **Survey responses** (learning preferences, user feedback) → `survey_responses` table  
- **Onboarding workflow** (progress, step completion) → `onboarding_progress` table
- **User preferences** (UI settings, personalization) → `user_preferences` table

## Allowed vs Forbidden Data

### ✅ Allowed in PALD (Embodiment-Related)

```json
{
  "global_design_level": {
    "type": "human",
    "cartoon": {"animation": "static"}
  },
  "middle_design_level": {
    "lifelikeness": 6,
    "realism": 5,
    "role": "teacher"
  },
  "detailed_level": {
    "age": "adult",
    "gender": "female", 
    "clothing": "professional attire"
  },
  "design_elements_not_in_PALD": ["background_color"]
}
```

### ❌ Forbidden in PALD (Non-Embodiment)

```json
{
  "survey_completed_at": "2024-01-01",
  "learning_preferences": {"style": "visual"},
  "onboarding_completed_at": "2024-01-01", 
  "step_data": {"current": "survey"},
  "personalization_level": "high",
  "ui_preferences": {"theme": "dark"},
  "chat_history": [...],
  "session_metadata": {...}
}
```

## Architecture

### Boundary Enforcer (`src/logic/pald_boundary.py`)

The `PALDBoundaryEnforcer` class provides:

- `filter_to_pald_attributes()` - Filters input to embodiment-only attributes
- `validate_pald_boundary()` - Validates data against boundary rules  
- `is_embodiment_data()` - Detects if data represents embodiment content
- `get_embodiment_deny_list()` - Returns list of forbidden keys

### Data Services

Separate services handle non-embodiment data:

- `SurveyResponseService` - Manages survey responses
- `OnboardingProgressService` - Tracks onboarding workflow
- `UserPreferencesService` - Stores user preferences
- `PALDSchemaRegistryService` - Handles runtime schema loading

### Schema Evolution (`src/logic/pald_evolution.py`)

The evolution system:

- Detects out-of-schema fields during processing
- Harvests field candidates for governance review
- Stores candidates in `schema_field_candidates` table
- Provides approval/rejection workflow for new fields

## Usage Examples

### Survey Data Processing

```python
# ❌ Old way (writes to PALD)
pald_manager.create_pald_data(user_id, survey_data)

# ✅ New way (writes to survey_responses)
survey_service.save_survey_response(user_id, survey_data)
```

### Onboarding Progress

```python
# ❌ Old way (writes to PALD)
pald_manager.create_pald_data(user_id, {"step_completed": "survey"})

# ✅ New way (writes to onboarding_progress)
onboarding_service.mark_step_completed(user_id, "survey")
```

### Embodiment Data (Still uses PALD)

```python
# ✅ Correct (embodiment data goes to PALD)
embodiment_data = {
    "global_design_level": {"type": "human"},
    "detailed_level": {"age": "adult", "gender": "female"}
}

# Validate first
result = boundary_enforcer.validate_pald_boundary(embodiment_data)
if result.is_valid:
    pald_manager.create_pald_data(user_id, embodiment_data)
```

## Configuration

Boundary enforcement is controlled by feature flags in `config.py`:

```python
# Feature flags
mandatory_pald_extraction: bool = True           # Always True
enable_pald_boundary_enforcement: bool = True    # Enable boundary checks
enable_pald_schema_evolution: bool = True        # Enable candidate harvesting

# Schema settings
pald_schema_file_path: str = "config/pald_schema.json"
pald_schema_cache_ttl: int = 300                 # 5 minutes
pald_candidate_min_support: int = 5              # Min occurrences for candidates
```

## Error Handling

Boundary violations result in clear error messages:

```python
result = boundary_enforcer.validate_pald_boundary(invalid_data)

if not result.is_valid:
    for error in result.validation_errors:
        print(f"Boundary violation: {error}")
    
    for key in result.rejected_keys:
        print(f"Rejected key: {key} (non-embodiment)")
```

## Testing

Key test scenarios:

- ✅ Writing non-embodiment keys to PALD fails with clear errors
- ✅ Survey UI stores responses without creating PALD entries  
- ✅ Onboarding logic stores metadata without PALD writes
- ✅ Out-of-schema fields become candidates, not PALD data
- ✅ Migration splits data correctly without loss

## Monitoring

The system logs:

- Boundary violations with context
- Schema loading events with checksums
- Migration progress and results
- Candidate field detection and harvesting

Check logs for boundary enforcement activity:

```bash
grep "boundary" logs/gitte.log
grep "schema.*checksum" logs/gitte.log  
grep "candidate.*harvested" logs/gitte.log
```