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

    def is_allowed(self, telegram_id):
        return telegram_id in self.allowed_telegram_ids


def load_config():
    return Config()
