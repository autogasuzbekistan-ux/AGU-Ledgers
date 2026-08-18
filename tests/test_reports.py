from datetime import date

from openpyxl import load_workbook

from reports import build_debtors_report


def test_build_debtors_report_writes_sorted_rows_with_total(tmp_path):
    debtors = [
        ("Alisher aka", 950.5, date(2026, 8, 1)),
        ("Bobur aka", 200.0, None),
    ]
    path = tmp_path / "qarzdorlar.xlsx"

    build_debtors_report(debtors, path, sana=date(2026, 8, 18))

    wb = load_workbook(path)
    ws = wb.active

    assert ws["A1"].value == "Qarzdorlar ro'yxati - 2026-08-18"
    assert ws["A2"].value == "Jami qarzdorlar: 2 ta"

    header_row = 4
    assert [ws.cell(row=header_row, column=c).value for c in range(1, 5)] == [
        "№", "Kontragent", "Oxirgi to'lov", "Qarz ($)",
    ]

    assert ws.cell(row=5, column=2).value == "Alisher aka"
    assert ws.cell(row=5, column=3).value == "2026-08-01"
    assert ws.cell(row=5, column=4).value == 950.5

    assert ws.cell(row=6, column=2).value == "Bobur aka"
    assert ws.cell(row=6, column=3).value == "ma'lum emas"
    assert ws.cell(row=6, column=4).value == 200.0

    assert ws.cell(row=7, column=2).value == "JAMI"
    assert ws.cell(row=7, column=4).value == 1150.5


def test_build_debtors_report_empty_list(tmp_path):
    path = tmp_path / "qarzdorlar_bosh.xlsx"

    build_debtors_report([], path, sana=date(2026, 8, 18))

    wb = load_workbook(path)
    ws = wb.active
    assert ws["A2"].value == "Jami qarzdorlar: 0 ta"
    assert ws.cell(row=5, column=2).value == "JAMI"
    assert ws.cell(row=5, column=4).value == 0
