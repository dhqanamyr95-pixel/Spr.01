import os
from dotenv import load_dotenv

load_dotenv()  # برای تست روی سیستم شخصی؛ در GitHub Actions مقادیر از Secrets می‌آیند

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "bot.db"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN تنظیم نشده است.")
if not ADMIN_IDS:
    raise RuntimeError("ADMIN_IDS تنظیم نشده است.")
