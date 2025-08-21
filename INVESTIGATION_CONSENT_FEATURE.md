# Investigation Participation Consent Feature

## Overview
This document describes the new investigation participation consent feature added to the GITTE onboarding flow.

## Features Added

### 1. New Consent Type
- Added `INVESTIGATION_PARTICIPATION` to the `ConsentType` enum
- This consent is now **required** for onboarding (alongside data processing and AI interaction)
- Students must agree to participate in the research investigation to use the system

### 2. Detailed Consent Texts
Created comprehensive markdown files in `consent_texts/` directory:
- `data_processing.md` - GDPR-compliant data processing information
- `ai_interaction.md` - AI systems and privacy protections
- `investigation_participation.md` - Research study details and participant rights
- `image_generation.md` - Image creation and storage policies
- `analytics.md` - Usage analytics and improvements
- `federated_learning.md` - Privacy-preserving collaborative learning

### 3. Enhanced Consent UI
- Added expandable sections showing detailed consent information
- Each consent type now has a "View detailed information" expander
- Integrated consent text loader utility for efficient file loading
- Updated consent form introduction to mention research study

### 4. Consent Text Loader Utility
New utility module `src/utils/consent_text_loader.py` provides:
- `load_consent_text(consent_type)` - Load individual consent texts
- `get_all_consent_texts()` - Load all available consent texts
- `render_consent_text_expander()` - Render expandable consent sections
- Caching support for better performance
- Error handling for missing files

## File Structure
```
consent_texts/
├── data_processing.md
├── ai_interaction.md
├── investigation_participation.md
├── image_generation.md
├── analytics.md
└── federated_learning.md

src/utils/
├── __init__.py
└── consent_text_loader.py
```

## Updated Components

### ConsentType Enum (`src/data/models.py`)
```python
class ConsentType(str, Enum):
    DATA_PROCESSING = "data_processing"
    AI_INTERACTION = "ai_interaction"
    IMAGE_GENERATION = "image_generation"
    FEDERATED_LEARNING = "federated_learning"
    ANALYTICS = "analytics"
    INVESTIGATION_PARTICIPATION = "investigation_participation"  # NEW
```

### Consent UI (`src/ui/consent_ui.py`)
- Added investigation participation to required consents
- Enhanced display names and descriptions
- Integrated detailed consent text viewing
- Added research study context to introduction

## Usage
Students will now see:
1. Three **required** consents (previously two):
   - Data Processing
   - AI Interaction
   - **Investigation Participation** (NEW)

2. Two **optional** consents:
   - Image Generation
   - Analytics & Improvements

3. **Detailed information** for each consent type available via expandable sections

4. **Research context** explaining the investigation purpose

## Customization
To customize consent texts:
1. Edit the relevant `.md` files in `consent_texts/` directory
2. The system automatically loads updated content
3. Support for multiple languages can be added by creating subdirectories

## Testing
- All existing unit tests pass
- Consent text loading functionality verified
- New consent type properly integrated into system
- Button activation logic unchanged (works with new required consent)

## Technical Notes
- Follows memory guidance: no expensive operations in form loops
- Maintains error handling best practices
- Uses caching for performance optimization
- Backward compatible with existing consent records