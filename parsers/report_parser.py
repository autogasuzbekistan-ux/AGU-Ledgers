"""'Абдуллох' formatidagi (har kontragent uchun alohida workbook, 31 kunlik
varaq, har varaqda tovar jadvali + qarz/to'lov bloki) fayldan FAQAT
'келган пул' bo'limini o'qiydigan modul (4-modul).

DIQQAT: bu formatda 'доллар' so'zi uchta bo'limda takrorlanadi (Карз,
келган пул, колган карз). Shuning uchun butun varaqni qidirish EMAS -
faqat 'келган пул' satridan keyingi 4 qatorni o'qish kerak. Bu xato
avval ushbu loyihada aniqlangan va shu yerda tuzatilgan.
"""
from openpyxl import load_workbook

SECTION_LABEL = 'келган пул'
FIELD_MAP = {'сум': 'naqd_som', 'click': 'click', 'доллар': 'naqd_dollar', 'пластик': 'terminal'}
SKIP_SHEETS = {'Ойлик %', 'Разработка '}


def parse_report_file(path):
    """Qaytaradi: {kun_varag_nomi: {naqd_som, click, naqd_dollar, terminal}}
    faqat kamida bitta qiymati bor kunlar uchun."""
    wb = load_workbook(path, data_only=True)
    result = {}

    for sheet_name in wb.sheetnames:
        if sheet_name in SKIP_SHEETS:
            continue
        ws = wb[sheet_name]

        section_row = None
        for r in range(1, ws.max_row + 1):
            if ws.cell(row=r, column=9).value == SECTION_LABEL:  # I ustuni
                section_row = r
                break
        if section_row is None:
            continue

        vals = {}
        for r in range(section_row, section_row + 4):
            label = ws.cell(row=r, column=10).value   # J ustuni
            value = ws.cell(row=r, column=11).value    # K ustuni
            if label and str(label).strip() in FIELD_MAP:
                vals[FIELD_MAP[str(label).strip()]] = value or 0

        if any(vals.get(k, 0) for k in ('naqd_som', 'click', 'naqd_dollar', 'terminal')):
            result[sheet_name] = {k: vals.get(k, 0) for k in ('naqd_som', 'click', 'naqd_dollar', 'terminal')}

    return result
