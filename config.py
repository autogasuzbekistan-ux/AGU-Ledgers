"""Muhit o'zgaruvchilarini yuklash (.env). TEXNIK_TOPSHIRIQ.md 9-bo'lim:
faqat ro'yxatga olingan Telegram ID(lar) botga kiradi."""
import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = (
    "BOT_TOKEN",
    "GOOGLE_SHEETS_ID",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "ALLOWED_TELEGRAM_ID",
)


def _parse_allowed_ids(raw):
    """Vergul bilan ajratilgan bitta yoki bir nechta Telegram ID
    ('ID(lar)' - 9-bo'lim)."""
    return {int(part.strip()) for part in raw.split(",") if part.strip()}


class Config:
    def __init__(self, env=None):
        env = env if env is not None else os.environ
        missing = [name for name in REQUIRED_VARS if not env.get(name)]
        if missing:
            raise RuntimeError(
                f"Muhit o'zgaruvchilari yetishmayapti: {', '.join(missing)} "
                f"(.env.example'ga qarang)"
            )
        self.bot_token = env["BOT_TOKEN"]
        self.google_sheets_id = env["GOOGLE_SHEETS_ID"]
        self.google_service_account_json = env["GOOGLE_SERVICE_ACCOUNT_JSON"]
        self.allowed_telegram_ids = _parse_allowed_ids(env["ALLOWED_TELEGRAM_ID"])

        # Ixtiyoriy sozlamalar - standart qiymatlar bilan, .env'da bo'lmasa
        # ham bot ishga tushadi.
        self.aliases_json_path = env.get("ALIASES_JSON_PATH", "aliases_data.json")
        self.audit_log_path = env.get("AUDIT_LOG_PATH", "audit.log")
        self.commission_rate = float(env.get("COMMISSION_RATE", "0.01"))
        self.large_amount_threshold_usd = float(env.get("LARGE_AMOUNT_THRESHOLD_USD", "5000"))
        self.debt_alert_threshold_usd = float(env.get("DEBT_ALERT_THRESHOLD_USD", "10000"))
        self.no_payment_alert_days = int(env.get("NO_PAYMENT_ALERT_DAYS", "3"))
        self.morning_digest_hour = int(env.get("MORNING_DIGEST_HOUR", "8"))

    def is_allowed(self, telegram_id):
        return telegram_id in self.allowed_telegram_ids


def load_config():
    return Config()
