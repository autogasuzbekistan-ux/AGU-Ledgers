from datetime import date

from aliases import AliasRegistry
from bot_logic import (
    apply_entry,
    compute_pending_kontragents,
    daily_payments_summary,
    days_since_last_payment,
    has_prior_entry,
    is_unusually_large_amount,
    parse_manual_date,
    top_debtors,
)
from ledger import DailyEntry


def test_compute_pending_kontragents():
    pending = compute_pending_kontragents(["rashid", "alisher", "bobur"], ["alisher"])
    assert pending == ["rashid", "bobur"]


def test_is_unusually_large_amount():
    entry = DailyEntry(
        sana=date(2026, 8, 1), kontragent_id="rashid",
        naqd_dollar=1000, qarz_boshida_dollar=2000,
    ).compute()

    assert is_unusually_large_amount(entry, threshold_usd=500) is True
    assert is_unusually_large_amount(entry, threshold_usd=5000) is False


def test_parse_manual_date_accepts_known_formats_and_rejects_garbage():
    assert parse_manual_date("15.08.2026") == date(2026, 8, 15)
    assert parse_manual_date(" 15.08.26 ") == date(2026, 8, 15)
    assert parse_manual_date("15-08-2026") == date(2026, 8, 15)
    assert parse_manual_date("ertaga") is None
    assert parse_manual_date("2026/08/15") is None
    # matn bo'lmagan xabar (rasm/sticker) uchun message.text None bo'ladi
    assert parse_manual_date(None) is None


def _registry():
    reg = AliasRegistry()
    reg.add_kontragent("rashid", "Rashid aka")
    reg.add_kontragent("alisher", "Alisher aka")
    reg.add_kontragent("bobur", "Bobur aka")  # avans, qarzdor emas
    return reg


def test_top_debtors_sorts_descending_and_excludes_non_debtors():
    entries_by_kontragent = {
        "rashid": [
            DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid", naqd_dollar=10, qarz_boshida_dollar=110).compute(),
        ],
        "alisher": [
            DailyEntry(sana=date(2026, 8, 1), kontragent_id="alisher", naqd_dollar=5, qarz_boshida_dollar=505).compute(),
        ],
        "bobur": [
            DailyEntry(sana=date(2026, 8, 1), kontragent_id="bobur", naqd_dollar=100, qarz_boshida_dollar=50).compute(),
        ],
    }

    result = top_debtors(entries_by_kontragent, _registry())

    assert result == [
        ("Alisher aka", 500, date(2026, 8, 1), 5),
        ("Rashid aka", 100, date(2026, 8, 1), 10),
    ]


def test_top_debtors_respects_top_n_and_finds_last_actual_payment_date():
    entries_by_kontragent = {
        "rashid": [
            DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid", naqd_dollar=50, qarz_boshida_dollar=500).compute(),
            DailyEntry(sana=date(2026, 8, 2), kontragent_id="rashid", naqd_dollar=0).compute(),
            DailyEntry(sana=date(2026, 8, 3), kontragent_id="rashid", naqd_dollar=0).compute(),
        ],
    }
    recalced = entries_by_kontragent["rashid"]
    recalced[1].qarz_boshida_dollar = recalced[0].qolgan_qarz_dollar
    recalced[1].compute()
    recalced[2].qarz_boshida_dollar = recalced[1].qolgan_qarz_dollar
    recalced[2].compute()

    result = top_debtors(entries_by_kontragent, _registry(), top_n=1)

    assert result == [("Rashid aka", 450, date(2026, 8, 1), 50)]


def test_top_debtors_top_n_none_returns_everyone():
    entries_by_kontragent = {
        "rashid": [DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid", qarz_boshida_dollar=100).compute()],
        "alisher": [DailyEntry(sana=date(2026, 8, 1), kontragent_id="alisher", qarz_boshida_dollar=50).compute()],
    }

    result = top_debtors(entries_by_kontragent, _registry(), top_n=None)

    assert len(result) == 2


def test_daily_payments_summary_aggregates_across_kontragents_and_sorts_descending():
    entries_by_kontragent = {
        "rashid": [
            DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid", naqd_som=128000, naqd_dollar=5, kurs=12800).compute(),
            DailyEntry(sana=date(2026, 8, 2), kontragent_id="rashid", naqd_som=64000, kurs=12800).compute(),
        ],
        "alisher": [
            DailyEntry(sana=date(2026, 8, 1), kontragent_id="alisher", click=12800, terminal=0, kurs=12800).compute(),
        ],
    }

    result = daily_payments_summary(entries_by_kontragent)

    assert [row[0] for row in result] == [date(2026, 8, 2), date(2026, 8, 1)]
    # 2026-08-02: faqat rashid, naqd_som=64000
    assert result[0] == (date(2026, 8, 2), 64000, 0, 0, 0, 5.0)
    # 2026-08-01: rashid (som=128000,dollar=5) + alisher (click=12800)
    naqd_som, click, terminal, naqd_dollar, jami_usd = result[1][1:]
    assert naqd_som == 128000
    assert click == 12800
    assert terminal == 0
    assert naqd_dollar == 5
    # rashid: 128000/12800 + 5 = 15; alisher: 12800/12800 = 1; jami = 16
    assert jami_usd == 16.0


def test_daily_payments_summary_empty():
    assert daily_payments_summary({}) == []


def test_apply_entry_inserts_new_day_and_cascades_recalculation():
    history = [
        DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid", naqd_dollar=10, qarz_boshida_dollar=100).compute(),
        DailyEntry(sana=date(2026, 8, 2), kontragent_id="rashid", naqd_dollar=10, qarz_boshida_dollar=90).compute(),
    ]
    new_day = DailyEntry(sana=date(2026, 8, 3), kontragent_id="rashid", naqd_dollar=5)

    chain = apply_entry(history, new_day)

    assert [e.sana for e in chain] == [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)]
    assert chain[2].qarz_boshida_dollar == 80
    assert chain[2].qolgan_qarz_dollar == 75


def test_apply_entry_replaces_existing_day_and_cascades_correction():
    day1 = DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid", naqd_dollar=10, qarz_boshida_dollar=100)
    day2 = DailyEntry(sana=date(2026, 8, 2), kontragent_id="rashid", naqd_dollar=10)
    history = apply_entry([day1], day2)  # boshlang'ich zanjirni tayyorlab olish

    corrected_day1 = DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid", naqd_dollar=50, qarz_boshida_dollar=100)
    result = apply_entry(history, corrected_day1)

    assert len(result) == 2
    assert result[0].naqd_dollar == 50
    assert result[0].qolgan_qarz_dollar == 50
    assert result[1].qarz_boshida_dollar == 50
    assert result[1].qolgan_qarz_dollar == 40


def test_has_prior_entry():
    history = [DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid")]

    assert has_prior_entry(history, date(2026, 8, 2)) is True
    assert has_prior_entry(history, date(2026, 8, 1)) is False
    assert has_prior_entry([], date(2026, 8, 1)) is False


def test_days_since_last_payment():
    entries = [
        DailyEntry(sana=date(2026, 8, 1), kontragent_id="rashid", naqd_dollar=10, qarz_boshida_dollar=100).compute(),
        DailyEntry(sana=date(2026, 8, 2), kontragent_id="rashid", naqd_dollar=0, qarz_boshida_dollar=90).compute(),
        DailyEntry(sana=date(2026, 8, 3), kontragent_id="rashid", naqd_dollar=0, qarz_boshida_dollar=90).compute(),
    ]

    assert days_since_last_payment(entries, today=date(2026, 8, 4)) == 3
    assert days_since_last_payment([], today=date(2026, 8, 4)) is None
