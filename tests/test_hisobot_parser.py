from openpyxl import Workbook

from parsers import parse_hisobot_file


def _build_hisobot_file(path):
    wb = Workbook()
    ws = wb.active
    ws.append([None, "Rashid aka", "Alisher aka"])
    ws.append(["naqt", 100000, 50000])
    ws.append(["Qog'oz", 20, 10])
    ws.append(["Plastik", 30000, 0])
    ws.append(["click", 15000, 25000])
    wb.save(path)


def test_parse_hisobot_file_maps_row_labels_per_kontragent(tmp_path):
    path = tmp_path / "hisobot_01_08_2026.xlsx"
    _build_hisobot_file(path)

    result = parse_hisobot_file(path)

    assert result == {
        "Rashid aka": {
            "naqd_som": 100000,
            "naqd_dollar": 20,
            "plastik": 30000,
            "click": 15000,
        },
        "Alisher aka": {
            "naqd_som": 50000,
            "naqd_dollar": 10,
            "plastik": 0,
            "click": 25000,
        },
    }


def test_parse_hisobot_file_row_labels_are_case_insensitive(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append([None, "Rashid aka"])
    ws.append(["NAQT", 100000])
    ws.append(["qog'oz", 20])
    ws.append(["PLASTIK", 0])
    ws.append(["Click", 5000])
    path = tmp_path / "hisobot_case.xlsx"
    wb.save(path)

    result = parse_hisobot_file(path)

    assert result["Rashid aka"] == {
        "naqd_som": 100000,
        "naqd_dollar": 20,
        "plastik": 0,
        "click": 5000,
    }
