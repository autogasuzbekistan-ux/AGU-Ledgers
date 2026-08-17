from datetime import date

from ledger import DailyEntry
from notifications import (
    format_alert_debt_threshold,
    format_alert_large_discount,
    format_alert_missing_from_list,
    format_alert_no_payment,
    format_alert_past_day_corrected,
    format_entry_confirmation,
    format_month_end_summary,
    format_morning_digest,
)


def test_format_entry_confirmation_shows_breakdown_and_totals():
    entry = DailyEntry(
        sana=date(2026, 8, 1), kontragent_id="rashid",
        naqd_som=128000, click=64000, terminal=0, naqd_dollar=5,
        chegirma_som=10000, kurs=12800,
        qarz_boshida_som=0, qarz_boshida_dollar=100,
    ).compute()

    text = format_entry_confirmation(entry, "Rashid aka")

    assert "Rashid aka - 2026-08-01" in text
    assert "Naqd so'm: 128 000" in text
    assert "Click: 64 000" in text
    assert "Naqd dollar: 5.00" in text
    assert "Chegirma: 10 000 so'm" in text
    # jami qabul = 128000/12800 + 64000/12800 + 5 = 10 + 5 + 5 = 20
    assert "Jami qabul: $20.00" in text
    # qolgan qarz dollar = 100 - 5 = 95 (musbat -> qarz)
    assert "Qolgan qarz: $95.00" in text


def test_format_entry_confirmation_shows_avans_when_negative():
    entry = DailyEntry(
        sana=date(2026, 8, 1), kontragent_id="rashid",
        naqd_dollar=200, qarz_boshida_dollar=50,
    ).compute()

    text = format_entry_confirmation(entry, "Rashid aka")

    assert "Qolgan avans: $150.00" in text


def test_format_morning_digest_empty_and_nonempty():
    assert format_morning_digest([]) == "Bugun qarzdorlar ro'yxati bo'sh."

    text = format_morning_digest([("Rashid aka", 950.5, date(2026, 8, 1)), ("Bobur aka", 200, None)])

    assert "1. Rashid aka - $950.50 (oxirgi to'lov: 2026-08-01)" in text
    assert "2. Bobur aka - $200.00 (oxirgi to'lov: ma'lum emas)" in text


def test_format_month_end_summary():
    text = format_month_end_summary("Avgust", 12345.678, 123.45678, 500000)

    assert "Avgust oyi yakuni:" in text
    assert "Jami topshirilgan: $12 345.68" in text
    assert "Komissiya: $123.46" in text
    assert "Jami chegirmalar: 500 000 so'm" in text


def test_alert_formatters():
    assert format_alert_no_payment("Rashid aka", 5) == "Diqqat: Rashid aka 5 kundan beri to'lov qilmadi."
    assert "g'ayrioddiy katta chegirma" in format_alert_large_discount("Rashid aka", 500000)
    assert "chegaradan oshdi" in format_alert_debt_threshold("Rashid aka", 5000, 3000)
    assert "kunlik ro'yxatga kiritilmadi" in format_alert_missing_from_list("Rashid aka", date(2026, 8, 1))
    assert "qayta hisoblandi" in format_alert_past_day_corrected("Rashid aka", date(2026, 8, 1), "Loyiha egasi")
