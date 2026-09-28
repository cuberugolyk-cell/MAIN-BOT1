import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "")
PAYMENT_ENABLED = os.getenv("PAYMENT_ENABLED", "false").lower() == "true"
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "")
