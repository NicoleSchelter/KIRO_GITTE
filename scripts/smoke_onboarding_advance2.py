# scripts/smoke_onboarding_advance.py
from uuid import UUID
from src.services.survey_service import save_complete_survey, upsert_user_preferences
from src.services.onboarding_service import advance_onboarding_step
from src.utils.jsonify import to_jsonable
from datetime import datetime
from uuid import uuid4

user = UUID("REPLACE-MIT-DEINER-TEST-UUID")  # oder uuid4() + Nutzer vorher anlegen

survey = {
    "learning_preferences": {"learning_style": "Auditory"},
    "meta": {"now": datetime.utcnow(), "id": uuid4()},
}

ok1 = save_complete_survey(user_id=user, survey_dict=to_jsonable(survey), version="1.0")
print("save_complete_survey:", ok1)

ok2 = upsert_user_preferences(user_id=user, category="onboarding_step_survey",
                              prefs=to_jsonable({"from_survey": True}))
print("upsert_user_preferences:", ok2)

ok3 = advance_onboarding_step(user_id=user, completed_step="survey")
print("advance_onboarding_step:", ok3)
