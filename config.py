import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "8815353069:AAGU7Q63quYEo26jRzZ82279NxDfHbFMqlM")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7932259359"))

# SMM Panel API (Standart SMM Reseller v2 API)
SMM_API_URL = os.getenv("SMM_API_URL", "").strip()
SMM_API_KEY = os.getenv("SMM_API_KEY", "").strip()
PRICE_MARGIN_PERCENT = float(os.getenv("PRICE_MARGIN_PERCENT", "20"))

# Virtual SIM (SMS-Activate API)
SMS_API_KEY = os.getenv("SMS_API_KEY", "").strip()
SMS_MARGIN_PERCENT = float(os.getenv("SMS_MARGIN_PERCENT", "25"))

# FixHamyon to'lov tizimi sozlamalari
FIXHAMYON_API_KEY = os.getenv("FIXHAMYON_API_KEY", "").strip()
FIXHAMYON_MERCHANT_ID = os.getenv("FIXHAMYON_MERCHANT_ID", "").strip()

# Ma'lumotlar bazasi
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "smm_bot.db"

# Referal keshbek foizi
REFERRAL_BONUS_PERCENT = 5.0
