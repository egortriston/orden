import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "").split(",") if admin_id.strip()]

# Robokassa configuration
ROBOKASSA_MERCHANT_LOGIN = os.getenv("ROBOKASSA_MERCHANT_LOGIN")
ROBOKASSA_PASSWORD_1 = os.getenv("ROBOKASSA_PASSWORD_1")
ROBOKASSA_PASSWORD_2 = os.getenv("ROBOKASSA_PASSWORD_2")
ROBOKASSA_TEST_MODE = os.getenv("ROBOKASSA_TEST_MODE", "True").lower() == "true"
ROBOKASSA_BASE_URL = "https://auth.robokassa.ru/Merchant/Index.aspx" if not ROBOKASSA_TEST_MODE else "https://auth.robokassa.ru/Merchant/Index.aspx"

# Channels
CHANNEL_1_ID = os.getenv("CHANNEL_1_ID", "@orden_demiurgov")
CHANNEL_2_ID = os.getenv("CHANNEL_2_ID", "@roditeli_demiurgi")

# Database (PostgreSQL)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "demiurg_bot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Links
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/lnhvvu")
OFFER_LINK = os.getenv("OFFER_LINK", "https://disk.yandex.ru/client/disk/Договор%20оферты%20")

# Prices
CHANNEL_1_PRICE = 1990
CHANNEL_2_PRICE = 1990

# Subscription periods (in days)
FREE_TRIAL_DAYS = 14
PAID_SUBSCRIPTION_DAYS = 30
REMINDER_DAYS_BEFORE = 3

