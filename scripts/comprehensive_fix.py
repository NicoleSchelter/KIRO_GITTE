#!/usr/bin/env python3
"""
Comprehensive fix for all onboarding issues.
"""

def fix_onboarding_step_enum():
    """Fix the OnboardingStep enum to include INTRO_CHAT."""
    file_path = "src/logic/onboarding.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add INTRO_CHAT to the enum
    old_enum = '''class OnboardingStep(str, Enum):
    """Onboarding step enumeration."""

    CONSENT = "consent"
    SURVEY = "survey"
    DESIGN = "design"
    CHAT = "chat"
    IMAGE_GENERATION = "image_generation"
    FEEDBACK = "feedback"
    COMPLETE = "complete"'''
    
    new_enum = '''class OnboardingStep(str, Enum):
    """Onboarding step enumeration."""

    CONSENT = "consent"
    SURVEY = "survey"
    INTRO_CHAT = "intro_chat"  # Added to match database
    DESIGN = "design"
    CHAT = "chat"
    IMAGE_GENERATION = "image_generation"
    FEEDBACK = "feedback"
    COMPLETE = "complete"'''
    
    content = content.replace(old_enum, new_enum)
    
    # Update flow_steps to include INTRO_CHAT
    old_flow = '''        # Define onboarding flow steps
        self.flow_steps = [
            OnboardingStep.CONSENT,
            OnboardingStep.SURVEY,
            OnboardingStep.DESIGN,
            OnboardingStep.CHAT,
            OnboardingStep.IMAGE_GENERATION,
            OnboardingStep.FEEDBACK,
            OnboardingStep.COMPLETE,
        ]'''
    
    new_flow = '''        # Define onboarding flow steps
        self.flow_steps = [
            OnboardingStep.CONSENT,
            OnboardingStep.SURVEY,
            OnboardingStep.INTRO_CHAT,
            OnboardingStep.DESIGN,
            OnboardingStep.CHAT,
            OnboardingStep.IMAGE_GENERATION,
            OnboardingStep.FEEDBACK,
            OnboardingStep.COMPLETE,
        ]'''
    
    content = content.replace(old_flow, new_flow)
    
    # Update consent requirements
    old_consent = '''        # Define required consents for each step
        self.step_consent_requirements = {
            OnboardingStep.CONSENT: [],  # No prior consent needed
            OnboardingStep.SURVEY: [ConsentType.DATA_PROCESSING],
            OnboardingStep.DESIGN: [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION],
            OnboardingStep.CHAT: [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION],
            OnboardingStep.IMAGE_GENERATION: [
                ConsentType.DATA_PROCESSING,
                ConsentType.IMAGE_GENERATION,
            ],
            OnboardingStep.FEEDBACK: [ConsentType.DATA_PROCESSING],
            OnboardingStep.COMPLETE: [],
        }'''
    
    new_consent = '''        # Define required consents for each step
        self.step_consent_requirements = {
            OnboardingStep.CONSENT: [],  # No prior consent needed
            OnboardingStep.SURVEY: [ConsentType.DATA_PROCESSING],
            OnboardingStep.INTRO_CHAT: [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION],
            OnboardingStep.DESIGN: [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION],
            OnboardingStep.CHAT: [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION],
            OnboardingStep.IMAGE_GENERATION: [
                ConsentType.DATA_PROCESSING,
                ConsentType.IMAGE_GENERATION,
            ],
            OnboardingStep.FEEDBACK: [ConsentType.DATA_PROCESSING],
            OnboardingStep.COMPLETE: [],
        }'''
    
    content = content.replace(old_consent, new_consent)
    
    # Fix session management issues
    content = content.replace('with get_session() as db_session:', 'with get_session_sync() as db_session:')
    
    # Fix the logic issue in get_user_onboarding_state
    old_logic = '''            # Determine current step
            if not onboarding_complete and not progress:
                for step in self.flow_steps:
                    if step not in completed_steps:
                        current_step = step
                        break
                else:
                    current_step = OnboardingStep.COMPLETE
            else:
                if not progress:
                    current_step = OnboardingStep.CONSENT
                current_step = OnboardingStep.COMPLETE'''
    
    new_logic = '''            # Determine current step
            if not progress:
                for step in self.flow_steps:
                    if step not in completed_steps:
                        current_step = step
                        break
                else:
                    current_step = OnboardingStep.COMPLETE
            elif onboarding_complete:
                current_step = OnboardingStep.COMPLETE
            # else: current_step wurde oben aus progress.current_step bereits korrekt abgeleitet'''
    
    content = content.replace(old_logic, new_logic)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed OnboardingStep enum and logic in {file_path}")

def fix_onboarding_service_transitions():
    """Fix the onboarding service to use correct step names."""
    file_path = "src/services/onboarding_service.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update the transition map to use correct step names
    old_transitions = '''# Explicit onboarding step transition map
ONBOARDING_TRANSITIONS = {
    "survey": "intro_chat",
    "intro_chat": "consent", 
    "consent": "preferences",
    "preferences": "tutorial",
    "tutorial": "first_interaction",
    "first_interaction": "complete",
    "complete": "complete"  # Terminal state
}'''
    
    new_transitions = '''# Explicit onboarding step transition map
ONBOARDING_TRANSITIONS = {
    "survey": "intro_chat",
    "intro_chat": "design", 
    "design": "chat",
    "chat": "image_generation",
    "image_generation": "feedback",
    "feedback": "complete",
    "complete": "complete"  # Terminal state
}'''
    
    content = content.replace(old_transitions, new_transitions)
    
    # Update progress percentages
    old_progress = '''# Progress percentage mapping
STEP_PROGRESS = {
    "survey": 20,
    "intro_chat": 35,
    "consent": 50,
    "preferences": 65,
    "tutorial": 80,
    "first_interaction": 95,
    "complete": 100
}'''
    
    new_progress = '''# Progress percentage mapping
STEP_PROGRESS = {
    "survey": 15,
    "intro_chat": 30,
    "design": 45,
    "chat": 60,
    "image_generation": 75,
    "feedback": 90,
    "complete": 100
}'''
    
    content = content.replace(old_progress, new_progress)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed onboarding transitions in {file_path}")

def remove_preferences_service():
    """Remove the duplicate PreferencesService and ensure all calls use UserPreferencesService."""
    import os
    
    # Remove the duplicate preferences_service.py file
    file_path = "src/services/preferences_service.py"
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Removed duplicate {file_path}")
    
    # Search for any imports of PreferencesService and replace them
    import glob
    
    for py_file in glob.glob("src/**/*.py", recursive=True):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'PreferencesService' in content and 'UserPreferencesService' not in content:
                # Replace imports
                content = content.replace(
                    'from src.services.preferences_service import PreferencesService',
                    'from src.services.user_preferences_service import UserPreferencesService'
                )
                content = content.replace('PreferencesService', 'UserPreferencesService')
                
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Updated imports in {py_file}")
        except Exception as e:
            print(f"Error processing {py_file}: {e}")

if __name__ == "__main__":
    print("Applying comprehensive fixes...")
    fix_onboarding_step_enum()
    fix_onboarding_service_transitions()
    remove_preferences_service()
    print("All fixes applied successfully!")