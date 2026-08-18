from datetime import date

from openpyxl import load_workbook

from reports import build_debtors_report


def _build(debtors=None, daily_rows=None, detail_rows=None, monthly_rows=None, path=None, sana=None):
    return build_debtors_report(
        debtors or [], daily_rows or [], detail_rows or [], monthly_rows or [],
        path, sana=sana,
    )


def test_build_debtors_report_writes_sorted_rows_with_total(tmp_path):
    debtors = [
        ("Alisher aka", 950.5, date(2026, 8, 1), 50.0),
        ("Bobur aka", 200.0, None, 0),
    ]
    path = tmp_path / "qarzdorlar.xlsx"

    _build(debtors=debtors, path=path, sana=date(2026, 8, 18))

    wb = load_workbook(path)
    ws = wb["Qarzdorlar"]

    assert ws["A1"].value == "Qarzdorlar ro'yxati - 2026-08-18"
    assert ws["A2"].value == "Jami qarzdorlar: 2 ta"

    header_row = 4
    assert [ws.cell(row=header_row, column=c).value for c in range(1, 6)] == [
        "№", "Kontragent", "Oxirgi to'lov sanasi", "Oxirgi to'lov summasi ($)", "Qarz ($)",
    ]

    assert ws.cell(row=5, column=2).value == "Alisher aka"
    assert ws.cell(row=5, column=3).value == "2026-08-01"
    assert ws.cell(row=5, column=4).value == 50.0
    assert ws.cell(row=5, column=5).value == 950.5

    assert ws.cell(row=6, column=2).value == "Bobur aka"
    assert ws.cell(row=6, column=3).value == "ma'lum emas"
    assert ws.cell(row=6, column=4).value == 0
    assert ws.cell(row=6, column=5).value == 200.0

    assert ws.cell(row=7, column=2).value == "JAMI"
    assert ws.cell(row=7, column=5).value == 1150.5


def test_build_debtors_report_empty_debtors(tmp_path):
    path = tmp_path / "qarzdorlar_bosh.xlsx"

    _build(path=path, sana=date(2026, 8, 18))

    wb = load_workbook(path)
    ws = wb["Qarzdorlar"]
    assert ws["A2"].value == "Jami qarzdorlar: 0 ta"
    assert ws.cell(row=5, column=2).value == "JAMI"
    assert ws.cell(row=5, column=5).value == 0


def test_build_debtors_report_daily_payments_sheet(tmp_path):
    daily_rows = [
        (date(2026, 8, 2), 64000, 0, 0, 0, 5.0),
        (date(2026, 8, 1), 128000, 12800, 0, 5, 16.0),
    ]
    path = tmp_path / "qarzdorlar_kunlik.xlsx"

    _build(daily_rows=daily_rows, path=path, sana=date(2026, 8, 18))

    wb = load_workbook(path)
    assert "Kunlik to'lovlar" in wb.sheetnames
    ws = wb["Kunlik to'lovlar"]

    header_row = 3
    assert [ws.cell(row=header_row, column=c).value for c in range(1, 7)] == [
        "Sana", "Naqd so'm", "Click", "Terminal", "Naqd dollar", "Jami ($)",
    ]

    assert ws.cell(row=4, column=1).value == "2026-08-02"
    assert ws.cell(row=4, column=2).value == 64000
    assert ws.cell(row=4, column=6).value == 5.0

    assert ws.cell(row=5, column=1).value == "2026-08-01"
    assert ws.cell(row=5, column=2).value == 128000
    assert ws.cell(row=5, column=3).value == 12800
    assert ws.cell(row=5, column=6).value == 16.0

    total_row = 6
    assert ws.cell(row=total_row, column=1).value == "JAMI"
    assert ws.cell(row=total_row, column=2).value == 192000
    assert ws.cell(row=total_row, column=3).value == 12800
    assert ws.cell(row=total_row, column=6).value == 21.0


def test_build_debtors_report_daily_detail_sheet(tmp_path):
    detail_rows = [
        (date(2026, 8, 2), "Alisher aka", 0, 0, 0, 3, 3.0),
        (date(2026, 8, 1), "Alisher aka", 0, 0, 0, 1, 1.0),
        (date(2026, 8, 1), "Rashid aka", 0, 0, 0, 2, 2.0),
    ]
    path = tmp_path / "qarzdorlar_tafsilot.xlsx"

    _build(detail_rows=detail_rows, path=path, sana=date(2026, 8, 18))

    wb = load_workbook(path)
    assert "Kunlik tafsilot" in wb.sheetnames
    ws = wb["Kunlik tafsilot"]

    header_row = 3
    assert [ws.cell(row=header_row, column=c).value for c in range(1, 8)] == [
        "Sana", "Kontragent", "Naqd so'm", "Click", "Terminal", "Naqd dollar", "Jami ($)",
    ]

    assert ws.cell(row=4, column=1).value == "2026-08-02"
    assert ws.cell(row=4, column=2).value == "Alisher aka"
    assert ws.cell(row=4, column=6).value == 3

    assert ws.cell(row=5, column=1).value == "2026-08-01"
    assert ws.cell(row=5, column=2).value == "Alisher aka"

    assert ws.cell(row=6, column=1).value == "2026-08-01"
    assert ws.cell(row=6, column=2).value == "Rashid aka"


def test_build_debtors_report_monthly_summary_sheet(tmp_path):
    monthly_rows = [
        ("2026-08 (Avgust)", 128000, 0, 0, 50, 60.0, 0.6),
        ("2026-07 (Iyul)", 0, 0, 0, 100, 100.0, 1.0),
    ]
    path = tmp_path / "qarzdorlar_oylik.xlsx"

    _build(monthly_rows=monthly_rows, path=path, sana=date(2026, 8, 18))

    wb = load_workbook(path)
    assert "Oylik tahlil" in wb.sheetnames
    ws = wb["Oylik tahlil"]

    header_row = 3
    assert [ws.cell(row=header_row, column=c).value for c in range(1, 8)] == [
        "Oy", "Naqd so'm", "Click", "Terminal", "Naqd dollar", "Jami ($)", "Komissiya ($)",
    ]

    assert ws.cell(row=4, column=1).value == "2026-08 (Avgust)"
    assert ws.cell(row=4, column=6).value == 60.0
    assert ws.cell(row=4, column=7).value == 0.6

    assert ws.cell(row=5, column=1).value == "2026-07 (Iyul)"

    total_row = 6
    assert ws.cell(row=total_row, column=1).value == "JAMI"
    assert ws.cell(row=total_row, column=5).value == 150
    assert ws.cell(row=total_row, column=6).value == 160.0
    assert round(ws.cell(row=total_row, column=7).value, 2) == 1.6
