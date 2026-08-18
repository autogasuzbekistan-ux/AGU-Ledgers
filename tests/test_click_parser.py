from openpyxl import Workbook

from parsers import parse_click_file


def _build_click_file(path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Rashid aka", "Alisher aka", "Bobur aka"])
    ws.append([100000, 50000, 70000])
    ws.append([200000, 150000, 30000])
    ws.append([300000, 200000, 100000])  # "jami" qatori - dinamik topiladi
    ws.append([None, None, None])
    ws.append([None, None, None])
    ws.append(["Курс", 12800, None])
    wb.save(path)


def test_parse_click_file_finds_totals_row_and_kurs(tmp_path):
    path = tmp_path / "click_01_08_2026.xlsx"
    _build_click_file(path)

    totals, kurs = parse_click_file(path)

    assert totals == {
        "Rashid aka": 300000,
        "Alisher aka": 200000,
        "Bobur aka": 100000,
    }
    assert kurs == 12800


def test_parse_click_file_raises_when_totals_row_missing(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Rashid aka", "Alisher aka", "Bobur aka"])
    ws.append([100000, 50000, 70000])
    path = tmp_path / "click_broken.xlsx"
    wb.save(path)

    try:
        parse_click_file(path)
        assert False, "ValueError kutilgan edi"
    except ValueError:
        pass
