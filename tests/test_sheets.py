from datetime import date

from fake_sheets_service import FakeValuesService

from ledger import DailyEntry
from sheets import SheetsClient, is_inline_json


def _entry(sana, naqd_som=0, naqd_dollar=0, qarz_boshida_dollar=0):
    return DailyEntry(
        sana=sana, kontragent_id="rashid",
        naqd_som=naqd_som, naqd_dollar=naqd_dollar,
        qarz_boshida_dollar=qarz_boshida_dollar,
    ).compute()


def _client():
    return SheetsClient("sheet123", FakeValuesService())


def test_append_and_read_entries_roundtrip():
    client = _client()
    entry = _entry(date(2026, 8, 1), naqd_som=100000, naqd_dollar=10, qarz_boshida_dollar=500)

    client.append_entry(entry)
    [read_back] = client.read_entries("rashid")

    assert read_back.sana == entry.sana
    assert read_back.kontragent_id == "rashid"
    assert read_back.naqd_som == 100000
    assert read_back.naqd_dollar == 10
    assert read_back.qarz_boshida_dollar == 500
    assert read_back.qolgan_qarz_dollar == 490


def test_read_entries_filters_by_kontragent_and_sorts_by_date():
    client = _client()
    client.append_entry(_entry(date(2026, 8, 2), naqd_dollar=10, qarz_boshida_dollar=100))
    client.append_entry(_entry(date(2026, 8, 1), naqd_dollar=5, qarz_boshida_dollar=100))
    other = DailyEntry(sana=date(2026, 8, 1), kontragent_id="alisher", qarz_boshida_dollar=50).compute()
    client.append_entry(other)

    entries = client.read_entries("rashid")

    assert [e.sana for e in entries] == [date(2026, 8, 1), date(2026, 8, 2)]
    assert all(e.kontragent_id == "rashid" for e in entries)


def test_update_entry_overwrites_existing_row_in_place():
    client = _client()
    client.append_entry(_entry(date(2026, 8, 1), naqd_dollar=10, qarz_boshida_dollar=500))
    client.append_entry(_entry(date(2026, 8, 2), naqd_dollar=20, qarz_boshida_dollar=490))

    corrected = _entry(date(2026, 8, 1), naqd_dollar=15, qarz_boshida_dollar=500)
    client.update_entry(corrected)

    entries = client.read_entries("rashid")
    assert len(entries) == 2  # yangi qator qo'shilmadi, mavjudi yangilandi
    assert entries[0].naqd_dollar == 15
    assert entries[1].naqd_dollar == 20  # boshqa kun tegilmagan


def test_update_entry_appends_when_no_existing_row_found():
    client = _client()

    client.update_entry(_entry(date(2026, 8, 1), naqd_dollar=10, qarz_boshida_dollar=500))

    entries = client.read_entries("rashid")
    assert len(entries) == 1
    assert entries[0].naqd_dollar == 10


def test_update_entries_batches_multiple_updates_and_appends_in_one_call():
    client = _client()
    client.append_entry(_entry(date(2026, 8, 1), naqd_dollar=10, qarz_boshida_dollar=500))
    client.append_entry(_entry(date(2026, 8, 2), naqd_dollar=20, qarz_boshida_dollar=490))
    other = DailyEntry(sana=date(2026, 8, 1), kontragent_id="alisher", qarz_boshida_dollar=50).compute()
    client.append_entry(other)

    corrected_day1 = _entry(date(2026, 8, 1), naqd_dollar=15, qarz_boshida_dollar=500)
    corrected_day2 = _entry(date(2026, 8, 2), naqd_dollar=25, qarz_boshida_dollar=485)
    new_day3 = _entry(date(2026, 8, 3), naqd_dollar=5, qarz_boshida_dollar=460)

    client.update_entries([corrected_day1, corrected_day2, new_day3])

    entries = client.read_entries("rashid")
    assert [e.sana for e in entries] == [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)]
    assert entries[0].naqd_dollar == 15
    assert entries[1].naqd_dollar == 25
    assert entries[2].naqd_dollar == 5
    # boshqa kontragent tegilmagan
    assert client.read_entries("alisher")[0].qarz_boshida_dollar == 50


def test_update_entries_empty_list_is_a_noop():
    client = _client()
    client.append_entry(_entry(date(2026, 8, 1), naqd_dollar=10, qarz_boshida_dollar=500))

    client.update_entries([])

    assert len(client.read_entries("rashid")) == 1


def test_read_all_entries_groups_by_kontragent_and_sorts():
    client = _client()
    client.append_entry(_entry(date(2026, 8, 2), naqd_dollar=10, qarz_boshida_dollar=100))
    client.append_entry(_entry(date(2026, 8, 1), naqd_dollar=5, qarz_boshida_dollar=100))
    other = DailyEntry(sana=date(2026, 8, 1), kontragent_id="alisher", qarz_boshida_dollar=50).compute()
    client.append_entry(other)

    result = client.read_all_entries()

    assert set(result.keys()) == {"rashid", "alisher"}
    assert [e.sana for e in result["rashid"]] == [date(2026, 8, 1), date(2026, 8, 2)]
    assert [e.sana for e in result["alisher"]] == [date(2026, 8, 1)]


def test_is_inline_json_distinguishes_path_from_json_content():
    assert is_inline_json('{"type": "service_account"}') is True
    assert is_inline_json('  {"type": "service_account"}  ') is True
    assert is_inline_json("service_account.json") is False
    assert is_inline_json("/path/to/service_account.json") is False


def test_get_and_set_kurs_roundtrip():
    client = _client()

    assert client.get_kurs(date(2026, 8, 1)) is None

    client.set_kurs(date(2026, 8, 1), 12800)
    assert client.get_kurs(date(2026, 8, 1)) == 12800

    client.set_kurs(date(2026, 8, 1), 12850)  # kunni tuzatish
    assert client.get_kurs(date(2026, 8, 1)) == 12850
    # boshqa kun uchun qator qo'shilmagan
    assert len(client._get_all_rows("Kurslar")) == 1
