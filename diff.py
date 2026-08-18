"""Fayl qayta yuklanganda (tuzatilgan versiya) eski va yangi tahlil
natijalarini solishtirish mantig'i.

TEXNIK_TOPSHIRIQ.md 6-bo'lim: "Fayl qayta yuborilsa (tuzatilgan versiya) -
hech qachon jim yozib qo'yilmaydi." Bot: (1) yangi faylni tahlil qiladi,
(2) oldingi natija bilan solishtiradi, (3) FAQAT o'zgargan kontragentlarni
ko'rsatadi (eski qiymat -> yangi qiymat), (4) foydalanuvchi
tasdiqlamaguncha Sheets'da hech narsa yangilanmaydi.

Bu modul faqat solishtirish/formatlash mantig'ini o'z ichiga oladi -
Sheets'ga yozish yoki Telegram bilan aloqa bot.py'da, foydalanuvchi
tasdig'idan KEYIN amalga oshiriladi.

parse_click_file/parse_hisobot_file/parse_report_file natijalari bir xil
shaklda emas (ba'zisi skalyar qiymat, ba'zisi ichki dict) - shuning uchun
diff_parsed_data ikkalasini ham qo'llab-quvvatlaydi.
"""


def diff_parsed_data(old, new):
    """old, new: {kontragent_yoki_kun_nomi: qiymat}. Qiymat skalyar
    (masalan click_parser) yoki dict (masalan hisobot_parser/report_parser)
    bo'lishi mumkin - har ikkisi ham oddiy tenglik (==) bilan solishtiriladi.

    Qaytaradi:
        {
            "ozgargan": {nomi: (eski_qiymat, yangi_qiymat)},
            "yangi": {nomi: yangi_qiymat},     # eski faylda umuman yo'q edi
            "yoqolgan": {nomi: eski_qiymat},   # yangi faylda endi yo'q
        }

    Bir xil qiymatlar natijaga chiqarilmaydi - faqat haqiqiy farqlar.
    """
    ozgargan = {}
    yangi = {}
    yoqolgan = {}

    for name, new_val in new.items():
        if name not in old:
            yangi[name] = new_val
        elif old[name] != new_val:
            ozgargan[name] = (old[name], new_val)

    for name, old_val in old.items():
        if name not in new:
            yoqolgan[name] = old_val

    return {"ozgargan": ozgargan, "yangi": yangi, "yoqolgan": yoqolgan}


def has_changes(diff):
    """diff_parsed_data natijasida biror farq bor-yo'qligini tekshiradi.
    False bo'lsa - fayl qayta yuborilgan bo'lsa ham hech narsa
    o'zgarmagan, tasdiq so'rashning hojati yo'q."""
    return bool(diff["ozgargan"] or diff["yangi"] or diff["yoqolgan"])


def format_diff(diff, title=None):
    """diff_parsed_data natijasini foydalanuvchiga ko'rsatish uchun
    o'qilishi oson qatorlar ro'yxatiga aylantiradi (Telegram xabari
    uchun bot.py shu qatorlarni birlashtiradi)."""
    lines = []
    if title:
        lines.append(title)

    for name, (eski, yangi) in diff["ozgargan"].items():
        lines.append(f"{name}: {eski} -> {yangi}")
    for name, yangi in diff["yangi"].items():
        lines.append(f"{name}: (yo'q edi) -> {yangi}")
    for name, eski in diff["yoqolgan"].items():
        lines.append(f"{name}: {eski} -> (faylda endi yo'q)")

    return lines
