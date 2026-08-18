from diff import diff_parsed_data, format_diff, has_changes


def test_diff_parsed_data_scalar_values_only_reports_real_changes():
    old = {"Rashid aka": 300000, "Alisher aka": 200000}
    new = {"Rashid aka": 300000, "Alisher aka": 250000}

    diff = diff_parsed_data(old, new)

    assert diff == {
        "ozgargan": {"Alisher aka": (200000, 250000)},
        "yangi": {},
        "yoqolgan": {},
    }
    assert has_changes(diff) is True


def test_diff_parsed_data_no_changes_returns_empty_diff():
    old = {"Rashid aka": 300000}
    new = {"Rashid aka": 300000}

    diff = diff_parsed_data(old, new)

    assert diff == {"ozgargan": {}, "yangi": {}, "yoqolgan": {}}
    assert has_changes(diff) is False


def test_diff_parsed_data_detects_new_and_missing_kontragents():
    old = {"Rashid aka": 300000, "Bobur aka": 100000}
    new = {"Rashid aka": 300000, "Alisher aka": 50000}

    diff = diff_parsed_data(old, new)

    assert diff["ozgargan"] == {}
    assert diff["yangi"] == {"Alisher aka": 50000}
    assert diff["yoqolgan"] == {"Bobur aka": 100000}
    assert has_changes(diff) is True


def test_diff_parsed_data_handles_nested_dict_values():
    old = {"Rashid aka": {"naqd_som": 100000, "click": 15000}}
    new = {"Rashid aka": {"naqd_som": 120000, "click": 15000}}

    diff = diff_parsed_data(old, new)

    assert diff["ozgargan"] == {
        "Rashid aka": (
            {"naqd_som": 100000, "click": 15000},
            {"naqd_som": 120000, "click": 15000},
        )
    }


def test_diff_parsed_data_only_touched_kontragent_is_reported():
    # real faylda sinalgan xatti-harakat: bitta kontragentda o'zgarish
    # bo'lsa, qolgan hammasi diff'ga chiqmasligi kerak.
    old = {"A": 1, "B": 2, "C": 3, "D": 4}
    new = {"A": 1, "B": 99, "C": 3, "D": 4}

    diff = diff_parsed_data(old, new)

    assert diff == {"ozgargan": {"B": (2, 99)}, "yangi": {}, "yoqolgan": {}}


def test_format_diff_produces_readable_lines():
    diff = {
        "ozgargan": {"Rashid aka": (100, 150)},
        "yangi": {"Alisher aka": 50},
        "yoqolgan": {"Bobur aka": 30},
    }

    lines = format_diff(diff, title="O'zgarishlar:")

    assert lines == [
        "O'zgarishlar:",
        "Rashid aka: 100 -> 150",
        "Alisher aka: (yo'q edi) -> 50",
        "Bobur aka: 30 -> (faylda endi yo'q)",
    ]
