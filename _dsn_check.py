from dotenv import load_dotenv; load_dotenv()
from config.config import config
print("Effective DSN:", config.database.dsn)
