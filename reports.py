"""Professional ko'rinishdagi hisobot fayllarini (xlsx) shakllantirish.

Telegram chat xabari uzun ro'yxatlar uchun noqulay (qisqartirish kerak,
o'qish qiyin) - shuning uchun "Qarzdorlar" kabi to'liq ro'yxatlar
formatlangan Excel fayl sifatida yuboriladi (bot.py orqali).
"""
from datetime import date as _date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def build_debtors_report(debtors, path, sana=None):
    """debtors: [(kontragent_nomi, qarz_dollar, oxirgi_tolov_sana_yoki_None), ...]
    (bot_logic.top_debtors natijasi, eng katta qarzdan boshlab saralangan).

    `path`ga professional formatlashtirilgan xlsx fayl sifatida yozadi:
    sarlavha, ustun nomlari (qalin, rangli fon), valyuta formatlash,
    muzlatilgan sarlavha qatori va jami qator. `path`ni qaytaradi."""
    sana = sana or _date.today()
    wb = Workbook()
    ws = wb.active
    ws.title = "Qarzdorlar"

    ws["A1"] = f"Qarzdorlar ro'yxati - {sana.isoformat()}"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:D1")
    ws["A2"] = f"Jami qarzdorlar: {len(debtors)} ta"
    ws["A2"].font = Font(italic=True, color="666666")

    header_row = 4
    headers = ["№", "Kontragent", "Oxirgi to'lov", "Qarz ($)"]
    for col, text in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=text)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")

    total_qarz = 0
    r = header_row
    for i, (nomi, qarz, oxirgi_tolov) in enumerate(debtors, start=1):
        r = header_row + i
        ws.cell(row=r, column=1, value=i)
        ws.cell(row=r, column=2, value=nomi)
        ws.cell(row=r, column=3, value=oxirgi_tolov.isoformat() if oxirgi_tolov else "ma'lum emas")
        qarz_cell = ws.cell(row=r, column=4, value=qarz)
        qarz_cell.number_format = '$#,##0.00'
        total_qarz += qarz

    total_row = r + 1
    ws.cell(row=total_row, column=2, value="JAMI").font = Font(bold=True)
    total_cell = ws.cell(row=total_row, column=4, value=total_qarz)
    total_cell.font = Font(bold=True)
    total_cell.number_format = '$#,##0.00'

    for col, width in enumerate([6, 32, 16, 16], start=1):
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.freeze_panes = f"A{header_row + 1}"

    wb.save(path)
    return path
