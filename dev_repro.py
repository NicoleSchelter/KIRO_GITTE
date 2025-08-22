from src.exceptions import PrerequisiteCheckFailedError

try:
    raise PrerequisiteCheckFailedError("PostgreSQL Database", "db fail", user_message="UM passed directly")
except Exception as e:
    import traceback
    traceback.print_exc()
