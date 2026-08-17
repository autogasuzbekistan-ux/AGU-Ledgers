# AGU Virtual Ofis

To'liq reja va barcha qarorlar uchun `TEXNIK_TOPSHIRIQ.md`ni o'qing —
bu suhbatda qadam-baqadam belgilangan.

## Holat: nima tayyor, nima yo'q

**Tayyor va real fayllarda sinalgan** (`parsers/`):
- `click_parser.py` — Click hisobot fayli (jami qatorini dinamik topadi)
- `hisobot_parser.py` — kunlik naqd/dollar/plastik/click fayli
- `report_parser.py` — "Абдуллох" formatidagi fayldan faqat to'lov qismini o'qiydi

Uchalasi ham `python3 -m pytest` bilan emas, balki to'g'ridan-to'g'ri real
fayllarga qarshi qo'lda sinaldi (natijalar TEXNIK_TOPSHIRIQ.md'da).

**Hali yozilmagan**:
- `sheets.py` — Google Sheets integratsiyasi (service account kerak, shuning
  uchun bu yerda emas — o'zingizning kalitingiz bilan sozlanishi kerak)
- `bot.py` — aiogram asosidagi bot: kurs so'rash, kontragent bo'yicha 4 ta
  savol, "o'tkazish"/"tuzatish" tugmalari, bildirishnomalar
- Alias-jadval (turli fayllardagi bir xil kontragent nomlarini bog'lash)
- Fayl qayta yuklanganda "farqni ko'rsatib tasdiq so'rash" logikasi (mantig'i
  sinalgan, kod hali alohida modul qilinmagan)

## Ishga tushirish

```bash
pip install -r requirements.txt
cp .env.example .env   # va to'ldiring
```

## Keyingi qadam

Bu yerni (yoki Claude Code'ni) TEXNIK_TOPSHIRIQ.md bilan boshlang — u yerda
ma'lumotlar modeli, formulalar va barcha qoidalar bor. `sheets.py` va
`bot.py`ni yozish uchun Google Sheets service account kerak bo'ladi (Google
Cloud Console'dan bepul yaratiladi).
