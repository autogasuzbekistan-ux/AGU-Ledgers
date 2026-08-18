"""Kontragent nomlarini moslashtirish (alias tizimi).

TEXNIK_TOPSHIRIQ.md 5-bo'lim: bir xil kontragent turli faylda turlicha
yozilishi mumkin (masalan "Alisher aka agu" / "Alisher aka do'kon").
Avtomatik fuzzy matching ishonchli emas - shuning uchun bu modul HECH
QACHON taxmin qilmaydi: mos kelmagan nom "qo'lda tekshirish" ro'yxatiga
chiqadi, boshqa hech narsa qilinmaydi.

Hozircha JSON fayl orqali saqlanadi (bir martalik sozlash). Kelajakda
xuddi shu interfeys Google Sheets'dagi alias-jadvalga ulanishi mumkin -
chaqiruvchi kod (bot.py) faqat AliasRegistry orqali ishlaydi, saqlash
usuli almashtirilsa ham o'zgarmaydi.
"""
import json


def _normalize(name):
    """Katta/kichik harf va ortiqcha bo'shliqlarni bir xillashtiradi.
    Bu FUZZY matching emas - faqat aniq mos kelishni tekshirish uchun
    yordamchi normalizatsiya (masalan "  Rashid aka " == "rashid aka")."""
    return " ".join(name.strip().lower().split())


class AliasRegistry:
    def __init__(self):
        self._kontragentlar = {}  # id -> rasmiy_nom
        self._aliaslar = {}  # normalized_alias -> id
        # Click faylida ham, hisobot faylida ham click summasi ko'rsatilgan
        # kontragentlar - hisobot fayl ularning "har kuni keladigan"
        # ro'yxatida bo'lgani uchun (TEXNIK_TOPSHIRIQ.md 4.2-bo'lim).
        # Click faylidan kelgan click qiymati ular uchun E'TIBORSIZ
        # qoldiriladi (ikki marta hisoblanib ketmasligi uchun) - haqiqiy
        # click summasi hisobot faylidan olinadi.
        self._click_fayldan_ozod = set()

    def add_kontragent(self, kontragent_id, rasmiy_nom):
        if kontragent_id in self._kontragentlar:
            raise ValueError(f"Kontragent allaqachon mavjud: {kontragent_id}")
        self._kontragentlar[kontragent_id] = rasmiy_nom
        self.add_alias(rasmiy_nom, kontragent_id)

    def mark_click_fayldan_ozod(self, kontragent_id):
        """Bu kontragentning click summasi Click faylidan emas, hisobot
        faylidan olinishi kerakligini belgilaydi (ikki marta
        hisoblanmasligi uchun)."""
        if kontragent_id not in self._kontragentlar:
            raise ValueError(f"Noma'lum kontragent ID: {kontragent_id}")
        self._click_fayldan_ozod.add(kontragent_id)

    def is_click_fayldan_ozod(self, kontragent_id):
        return kontragent_id in self._click_fayldan_ozod

    def add_alias(self, alias_text, kontragent_id):
        if kontragent_id not in self._kontragentlar:
            raise ValueError(f"Noma'lum kontragent ID: {kontragent_id}")
        key = _normalize(alias_text)
        existing = self._aliaslar.get(key)
        if existing is not None and existing != kontragent_id:
            raise ValueError(
                f"'{alias_text}' allaqachon boshqa kontragentga bog'langan: {existing}"
            )
        self._aliaslar[key] = kontragent_id

    def resolve(self, name):
        """Nomni rasmiy kontragent ID'ga bog'laydi. Aniq mos kelmasa,
        yoki `name` berilmagan bo'lsa (None) - HECH QACHON taxmin
        qilmaydi, None qaytaradi."""
        if name is None:
            return None
        return self._aliaslar.get(_normalize(name))

    def resolve_many(self, names):
        """Qaytaradi: (resolved: {nom: id}, tekshirish_kerak: [nom, ...])

        `tekshirish_kerak` ro'yxati - 6-bo'limdagi "mos kelmaganlarni
        ko'rsatish" talabiga mos - bot shu ro'yxatni foydalanuvchiga
        ko'rsatadi, o'zi hech narsani taxmin qilmaydi."""
        resolved = {}
        tekshirish_kerak = []
        for name in names:
            kontragent_id = self.resolve(name)
            if kontragent_id is None:
                tekshirish_kerak.append(name)
            else:
                resolved[name] = kontragent_id
        return resolved, tekshirish_kerak

    def rasmiy_nom(self, kontragent_id):
        return self._kontragentlar[kontragent_id]

    def kontragentlar(self):
        """Barcha kontragentlar ro'yxati: [(id, rasmiy_nom), ...]"""
        return list(self._kontragentlar.items())

    def to_dict(self):
        return {
            "kontragentlar": self._kontragentlar,
            "aliaslar": self._aliaslar,
            "click_fayldan_ozod": sorted(self._click_fayldan_ozod),
        }

    @classmethod
    def from_dict(cls, data):
        registry = cls()
        registry._kontragentlar = dict(data.get("kontragentlar", {}))
        registry._aliaslar = dict(data.get("aliaslar", {}))
        registry._click_fayldan_ozod = set(data.get("click_fayldan_ozod", []))
        return registry

    def save_json(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)

    @classmethod
    def load_json(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
