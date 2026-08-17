"""Amallar jurnali (TEXNIK_TOPSHIRIQ.md 9-bo'lim: "Har bir amal (kiritish,
tuzatish, o'chirish) - kim va qachon qilgani bilan birga log'ga
yoziladi").

Hozircha mahalliy faylga (append-only) yozadi. Railway'da fayl tizimi
har deploy'da tozalanishi mumkin - agar uzoq muddatli tarixiy jurnal
kerak bo'lsa, kelajakda shu interfeys (log_action) Sheets'dagi "Log"
varag'iga yozadigan implementatsiyaga almashtirilishi mumkin.
"""
import datetime
import json


class AuditLog:
    def __init__(self, path="audit.log"):
        self.path = path

    def log_action(self, actor_telegram_id, action, details=None):
        entry = {
            "vaqt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kim": actor_telegram_id,
            "amal": action,
            "tafsilot": details or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return entry
