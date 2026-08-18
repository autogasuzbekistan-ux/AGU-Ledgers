"""Google Sheets integratsiyasi - kunlik yozuvlarni saqlash va o'qish.

TEXNIK_TOPSHIRIQ.md 2-bo'lim: Google Sheets ma'lumotlar bazasi sifatida
ishlatiladi - faqat bot (service account) yozadi, odamlar to'g'ridan-
to'g'ri tahrirlamaydi, dashboard faqat o'qiydi (9-bo'lim).

Jadval tuzilishi (bitta spreadsheet, ikkita varaq):
- "Ledger"  - har bir qator = bitta kontragentning bitta kunlik yozuvi
  (ledger.DailyEntry'ga mos)
- "Kurslar" - sana -> o'sha kunning kursi (kuniga bir marta kiritiladi,
  6-bo'lim: "Kurs - kuniga bir marta so'raladi ... shu kunning barcha
  yozuvlariga avtomatik qo'llanadi")

SheetsClient - Google API ustida yupqa "repository" qatlami: haqiqiy
tarmoq chaqiruvisiz sinash uchun `values_service` parametri orqali
`spreadsheets().values()`ga mos (get/update/append) soxta obyekt berish
mumkin (tests/test_sheets.py'ga qarang). Ishlab chiqarishda
`SheetsClient.from_service_account(...)` chaqiriladi.
"""
import json
from datetime import date as _date

from google.oauth2 import service_account
from googleapiclient.discovery import build

from ledger import DailyEntry

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

LEDGER_SHEET = "Ledger"
KURS_SHEET = "Kurslar"

LEDGER_HEADERS = [
    "sana", "kontragent_id", "naqd_som", "click", "naqd_dollar", "terminal",
    "chegirma_som", "kurs", "qarz_boshida_som", "qarz_boshida_dollar",
    "jami_qabul_som", "jami_qabul_dollar", "qolgan_qarz_som", "qolgan_qarz_dollar",
]


def _column_letter(index):
    """1-asosli ustun raqamini spreadsheet harfiga aylantiradi (1->A,
    14->N, 27->AA, ...)."""
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


# LEDGER_HEADERS uzunligidan avtomatik hisoblanadi - qo'lda yozilgan
# harf bilan ro'yxat uzunligi orasida moslikni saqlash uchun (yangi
# maydon qo'shilsa-yu bu qiymat yangilanmasa, update_entry oxirgi
# ustun(lar)ni jimgina yozmay qoldirar edi).
LEDGER_LAST_COLUMN = _column_letter(len(LEDGER_HEADERS))


def is_inline_json(service_account_json):
    """GOOGLE_SERVICE_ACCOUNT_JSON qiymati fayl yo'li emas, JSON
    matnining o'zi ekanligini aniqlaydi (Railway kabi muhitlar uchun)."""
    return service_account_json.strip().startswith("{")


def _entry_to_row(entry):
    return [
        entry.sana.isoformat(), entry.kontragent_id, entry.naqd_som, entry.click,
        entry.naqd_dollar, entry.terminal, entry.chegirma_som, entry.kurs,
        entry.qarz_boshida_som, entry.qarz_boshida_dollar, entry.jami_qabul_som,
        entry.jami_qabul_dollar, entry.qolgan_qarz_som, entry.qolgan_qarz_dollar,
    ]


def _row_to_entry(row):
    values = dict(zip(LEDGER_HEADERS, row))

    def num(key):
        raw = values.get(key)
        return float(raw) if raw not in (None, "") else 0

    entry = DailyEntry(
        sana=_date.fromisoformat(values["sana"]),
        kontragent_id=values["kontragent_id"],
        naqd_som=num("naqd_som"),
        click=num("click"),
        naqd_dollar=num("naqd_dollar"),
        terminal=num("terminal"),
        chegirma_som=num("chegirma_som"),
        kurs=float(values["kurs"]) if values.get("kurs") not in (None, "") else None,
        qarz_boshida_som=num("qarz_boshida_som"),
        qarz_boshida_dollar=num("qarz_boshida_dollar"),
    )
    entry.compute()
    return entry


class SheetsClient:
    def __init__(self, spreadsheet_id, values_service):
        self.spreadsheet_id = spreadsheet_id
        self._values = values_service

    @classmethod
    def from_service_account(cls, spreadsheet_id, service_account_json):
        """service_account_json - fayl yo'li YOKI JSON matnining o'zi.

        Railway kabi platformalarda fayl yuklab bo'lmaydi - muhit
        o'zgaruvchisiga service account kalitining butun JSON matni
        to'g'ridan-to'g'ri qo'yiladi. Mahalliy ishlab chiqishda esa
        odatiy fayl yo'li ishlatiladi."""
        if is_inline_json(service_account_json):
            info = json.loads(service_account_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = service_account.Credentials.from_service_account_file(
                service_account_json, scopes=SCOPES
            )
        service = build("sheets", "v4", credentials=creds)
        return cls(spreadsheet_id, service.spreadsheets().values())

    def _get_all_rows(self, sheet_name):
        # valueRenderOption=UNFORMATTED_VALUE - katakchalarga valyuta/son
        # formatlash qo'llanilgan bo'lsa ham (masalan "$1,234.00"), xom
        # sonni qaytaradi, formatlangan matnni emas.
        result = self._values.get(
            spreadsheetId=self.spreadsheet_id, range=f"{sheet_name}!A2:Z",
            valueRenderOption="UNFORMATTED_VALUE",
        ).execute()
        return result.get("values", [])

    def append_entry(self, entry):
        self._values.append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{LEDGER_SHEET}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [_entry_to_row(entry)]},
        ).execute()

    def read_entries(self, kontragent_id):
        """Bitta kontragentning barcha yozuvlarini sana bo'yicha o'sish
        tartibida qaytaradi (ledger.recalculate_chain'ga berish uchun)."""
        rows = self._get_all_rows(LEDGER_SHEET)
        entries = [
            _row_to_entry(row) for row in rows if len(row) > 1 and row[1] == kontragent_id
        ]
        return sorted(entries, key=lambda e: e.sana)

    def read_all_entries(self):
        """Barcha kontragentlarning barcha yozuvlarini qaytaradi:
        {kontragent_id: [DailyEntry, ...]} (har biri sana bo'yicha
        tartiblangan). Kunlik holat ro'yxati va qarzdorlar reytingi
        uchun ishlatiladi."""
        rows = self._get_all_rows(LEDGER_SHEET)
        by_kontragent = {}
        for row in rows:
            if len(row) < 2:
                continue
            entry = _row_to_entry(row)
            by_kontragent.setdefault(entry.kontragent_id, []).append(entry)
        for entries in by_kontragent.values():
            entries.sort(key=lambda e: e.sana)
        return by_kontragent

    def update_entry(self, entry):
        """Mavjud (sana, kontragent_id) yozuvini topib, o'sha qatorni
        ustidan yozadi ('tuzatish' tugmasi uchun). Topilmasa - yangi
        qator sifatida qo'shadi.

        Bir nechta yozuvni birdaniga yangilash kerak bo'lsa (masalan
        zanjirli qayta hisoblash yoki fayl yuklash tasdig'i), buning
        o'rniga update_entries()'ni ishlating - har bir yozuv uchun
        alohida to'liq sheet o'qishning oldini oladi (sekinlik sababi)."""
        self.update_entries([entry])

    def update_entries(self, entries):
        """Bir nechta yozuvni BITTA sheet o'qish va BITTA guruhli yozish
        bilan yangilaydi - update_entry'ni ro'yxat bo'yicha aylanib
        chaqirishning o'rniga (bu holda har biri o'zining to'liq sheet
        o'qishini qilar edi, N ta yozuv uchun N marta to'liq jadval
        o'qilar edi - fayl yuklash tasdig'ida yoki uzoq zanjirli
        tuzatishda sezilarli sekinlikka olib kelardi)."""
        entries = list(entries)
        if not entries:
            return

        rows = self._get_all_rows(LEDGER_SHEET)
        row_number_by_key = {
            (row[0], row[1]): i + 2  # 1-qator sarlavha, ma'lumot A2'dan
            for i, row in enumerate(rows) if len(row) > 1
        }

        data = []
        to_append = []
        for entry in entries:
            key = (entry.sana.isoformat(), entry.kontragent_id)
            row_number = row_number_by_key.get(key)
            if row_number is None:
                to_append.append(entry)
            else:
                data.append({
                    "range": f"{LEDGER_SHEET}!A{row_number}:{LEDGER_LAST_COLUMN}{row_number}",
                    "values": [_entry_to_row(entry)],
                })

        if data:
            self._values.batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"valueInputOption": "RAW", "data": data},
            ).execute()
        if to_append:
            # Bitta guruhli append - har biri uchun alohida chaqiruv emas.
            self._values.append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{LEDGER_SHEET}!A:A",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [_entry_to_row(e) for e in to_append]},
            ).execute()

    def get_kurs(self, sana):
        rows = self._get_all_rows(KURS_SHEET)
        for row in rows:
            if len(row) > 1 and row[0] == sana.isoformat():
                return float(row[1])
        return None

    def set_kurs(self, sana, kurs):
        rows = self._get_all_rows(KURS_SHEET)
        for i, row in enumerate(rows):
            if row and row[0] == sana.isoformat():
                row_number = i + 2
                self._values.update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{KURS_SHEET}!A{row_number}:B{row_number}",
                    valueInputOption="RAW",
                    body={"values": [[sana.isoformat(), kurs]]},
                ).execute()
                return
        self._values.append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{KURS_SHEET}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [[sana.isoformat(), kurs]]},
        ).execute()
