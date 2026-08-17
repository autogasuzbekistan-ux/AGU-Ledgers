from openpyxl import Workbook

from parsers import parse_report_file


def _set_kelgan_pul_block(ws, start_row, values):
    """start_row'da 'келган пул' belgisini (I ustuni) va undan keyingi 4
    qatorda (label J ustunida, qiymat K ustunida) yozadi."""
    ws.cell(row=start_row, column=9, value="келган пул")
    for offset, (label, value) in enumerate(values):
        ws.cell(row=start_row + offset, column=10, value=label)
        ws.cell(row=start_row + offset, column=11, value=value)


def test_parse_report_file_reads_only_kelgan_pul_block(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "1"
    _set_kelgan_pul_block(
        ws,
        start_row=10,
        values=[
            ("сум", 500000),
            ("click", 200000),
            ("доллар", 15),
            ("пластик", 100000),
        ],
    )
    # boshqa bo'limlarda ham "доллар" so'zi takrorlanadi (Карз, колган карз) -
    # parser bularni chalkashtirmasligi kerak.
    ws.cell(row=2, column=9, value="Карз")
    ws.cell(row=2, column=10, value="доллар")
    ws.cell(row=2, column=11, value=999999)
    ws.cell(row=20, column=9, value="колган карз")
    ws.cell(row=20, column=10, value="доллар")
    ws.cell(row=20, column=11, value=888888)

    path = tmp_path / "report.xlsx"
    wb.save(path)

    result = parse_report_file(path)

    assert result == {
        "1": {
            "naqd_som": 500000,
            "click": 200000,
            "naqd_dollar": 15,
            "terminal": 100000,
        }
    }


def test_parse_report_file_skips_known_sheets_and_sheets_without_section(tmp_path):
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Ойлик %"
    _set_kelgan_pul_block(ws1, start_row=10, values=[("сум", 111), ("click", 0), ("доллар", 0), ("пластик", 0)])

    wb.create_sheet("2")
    # bu varaqda 'келган пул' bo'limi umuman yo'q

    ws3 = wb.create_sheet("3")
    _set_kelgan_pul_block(ws3, start_row=5, values=[("сум", 0), ("click", 0), ("доллар", 0), ("пластик", 0)])

    path = tmp_path / "report_skip.xlsx"
    wb.save(path)

    result = parse_report_file(path)

    # "Ойлик %" - SKIP_SHEETS ro'yxatida => e'tiborsiz
    # "2" - bo'lim topilmadi => e'tiborsiz
    # "3" - bo'lim bor, lekin barcha qiymatlar 0 => natijaga chiqmaydi
    assert result == {}
