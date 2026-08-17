# AGU Virtual Ofis

To'liq reja va barcha qarorlar uchun `TEXNIK_TOPSHIRIQ.md`ni o'qing —
bu suhbatda qadam-baqadam belgilangan.

## Holat: nima tayyor, nima yo'q

**Tayyor va pytest bilan sinalgan**:
- `parsers/click_parser.py` — Click hisobot fayli (jami qatorini dinamik topadi)
- `parsers/hisobot_parser.py` — kunlik naqd/dollar/plastik/click fayli
- `parsers/report_parser.py` — "Абдуллох" formatidagi fayldan faqat to'lov qismini o'qiydi
- `ledger.py` — kunlik yozuv modeli va formulalar (jami qabul, qolgan qarz,
  avans, kunlik/oylik carryover zanjiri, komissiya) — TEXNIK_TOPSHIRIQ.md
  3 va 7-bo'limlar
- `aliases.py` — kontragent nomlarini moslashtirish (alias tizimi), hech
  qachon taxmin qilmaydi — TEXNIK_TOPSHIRIQ.md 5-bo'lim
- `diff.py` — fayl qayta yuklanganda eski/yangi natijani solishtirish,
  faqat o'zgargan qatorlarni chiqarish — TEXNIK_TOPSHIRIQ.md 6-bo'lim
- `config.py` — `.env`dan sozlamalarni yuklash (bot token, Sheets ID,
  ruxsat berilgan Telegram ID(lar))

Uchta parser dastlab real fayllarga qarshi qo'lda sinalgan edi (natijalar
TEXNIK_TOPSHIRIQ.md'da); endi hammasi uchun sintetik fixture'lar bilan
avtomatik pytest testlari ham bor (`tests/`).

**Diqqat — tasdiqlash kerak bo'lgan bitta taxmin**: `ledger.py`da "jami
qabul" faqat haqiqatda qabul qilingan puldan (naqd/click/terminal)
hisoblanadi, "chegirma" qarzni kamaytiradi lekin komissiya bazasiga
kirmaydi. TEXNIK_TOPSHIRIQ.md bu ikkalasini alohida-alohida sanaydi, lekin
ularning formulaga aniq qanday kirishi so'zma-so'z yozilmagan — shuning
uchun mantiqiy talqin qilindi. Noto'g'ri bo'lsa `ledger.py`dagi
`DailyEntry.compute()`ni tuzatish kifoya.

**Hali yozilmagan** (keyingi bosqich):
- `sheets.py` — Google Sheets integratsiyasi (service account kerak, shuning
  uchun bu yerda emas — o'zingizning kalitingiz bilan sozlanishi kerak)
- `bot.py` — aiogram asosidagi bot: kurs so'rash, kontragent bo'yicha 4 ta
  savol, "o'tkazish"/"tuzatish" tugmalari, bildirishnomalar — endi
  `ledger.py`, `aliases.py`, `diff.py`, `config.py`ga tayanib quriladi

## Ishga tushirish

```bash
pip install -r requirements-dev.txt   # yoki requirements.txt (faqat prod)
cp .env.example .env   # va to'ldiring
python3 -m pytest      # barcha testlarni ishga tushirish
```

## Keyingi qadam

`sheets.py` va `bot.py`ni yozish uchun Google Sheets service account kerak
bo'ladi (Google Cloud Console'dan bepul yaratiladi) va haqiqiy Telegram bot
token. To'liq reja va barcha qarorlar uchun `TEXNIK_TOPSHIRIQ.md`ni o'qing.
