# AGU Virtual Ofis

To'liq reja va barcha qarorlar uchun `TEXNIK_TOPSHIRIQ.md`ni o'qing —
bu suhbatda qadam-baqadam belgilangan.

## Holat: nima tayyor

Barcha modullar yozilgan va pytest bilan sinalgan (51 test, `tests/`):

- `parsers/click_parser.py` — Click hisobot fayli (jami qatorini dinamik topadi)
- `parsers/hisobot_parser.py` — kunlik naqd/dollar/plastik/click fayli
- `parsers/report_parser.py` — "Абдуллох" formatidagi fayldan faqat to'lov qismini o'qiydi
- `ledger.py` — kunlik yozuv modeli va formulalar (jami qabul, qolgan qarz,
  avans, kunlik/oylik carryover zanjiri — oy chegarasida so'm 0'ga
  qaytadi/dollar davom etadi, komissiya) — TEXNIK_TOPSHIRIQ.md 3 va 7-bo'lim
- `aliases.py` — kontragent nomlarini moslashtirish (alias tizimi), hech
  qachon taxmin qilmaydi — TEXNIK_TOPSHIRIQ.md 5-bo'lim
- `diff.py` — fayl qayta yuklanganda eski/yangi natijani solishtirish,
  faqat o'zgargan qatorlarni chiqarish — TEXNIK_TOPSHIRIQ.md 6-bo'lim
- `sheets.py` — Google Sheets integratsiyasi (`SheetsClient`): "Ledger" va
  "Kurslar" varaqlari, service account orqali; haqiqiy tarmoqsiz
  sinalgan (`tests/fake_sheets_service.py`)
- `bot_logic.py` — bot uchun sof mantiq (kunlik holat, qarzdorlar
  reytingi, sana parsing, zanjirni qayta hisoblash)
- `notifications.py` — bildirishnoma matnlari (8-bo'lim: kiritish
  tasdig'i, ertalabki digest, oy yakuni, ogohlantirishlar)
- `audit.py` — amallar jurnali (9-bo'lim: kim, qachon, nima qildi)
- `config.py` — `.env`dan sozlamalarni yuklash
- `bot.py` — aiogram 3.x bot: kurs so'rash, kontragent bo'yicha 4 ta savol,
  "bugun to'lov yo'q"/"tuzatish" tugmalari, "kechiktirilgan kun", fayl
  yuklash (Click/hisobot/"Абдуллох" formatlari, diff-tasdiqlash bilan),
  rejalashtirilgan ertalabki digest va oy yakuni (APScheduler)

**Diqqat — tasdiqlash kerak bo'lgan bitta taxmin**: `ledger.py`da "jami
qabul" faqat haqiqatda qabul qilingan puldan (naqd/click/terminal)
hisoblanadi, "chegirma" qarzni kamaytiradi lekin komissiya bazasiga
kirmaydi. TEXNIK_TOPSHIRIQ.md bu ikkalasini alohida-alohida sanaydi, lekin
ularning formulaga aniq qanday kirishi so'zma-so'z yozilmagan — shuning
uchun mantiqiy talqin qilindi. Noto'g'ri bo'lsa `ledger.py`dagi
`DailyEntry.compute()`ni tuzatish kifoya.

**`bot.py` haqida muhim eslatma**: barcha ostidagi mantiq (`ledger.py`,
`aliases.py`, `diff.py`, `sheets.py`, `bot_logic.py`, `notifications.py`)
avtomatik testlar bilan sinalgan. `bot.py`ning o'zi — aiogram bilan
ishlaydigan qatlam — haqiqiy Telegram bot token, Google service account va
tarmoq aloqasi bo'lmagani uchun bu muhitda **jonli sinalmagan** (faqat
sintaksis/import darajasida tekshirildi). Real token va service account
kaliti bilan qo'lda sinab ko'rish, xatoliklarni tuzatish kerak bo'ladi.

## Ishga tushirish

```bash
pip install -r requirements-dev.txt   # yoki requirements.txt (faqat prod)
cp .env.example .env                  # va to'ldiring
cp aliases_data.example.json aliases_data.json   # kontragentlar ro'yxatini to'ldiring
python3 -m pytest                     # barcha testlarni ishga tushirish (51 ta)
python3 bot.py                        # botni ishga tushirish (.env to'ldirilgandan keyin)
```

Google Sheets service account: Google Cloud Console'da loyiha yaratib,
Sheets API'ni yoqing, service account kaliti (JSON) yarating va
spreadsheet'ni shu service account emailiga "Editor" huquqi bilan ulashing.

## Keyingi qadam

Real BOT_TOKEN, Google Sheets ID va service account kaliti bilan `bot.py`ni
ishga tushirib, har bir oqimni (kirim, tuzatish, kechiktirilgan kun, fayl
yuklash) qo'lda sinab, topilgan nomuvofiqliklarni tuzatish kerak. To'liq
reja va barcha qarorlar uchun `TEXNIK_TOPSHIRIQ.md`ni o'qing.
