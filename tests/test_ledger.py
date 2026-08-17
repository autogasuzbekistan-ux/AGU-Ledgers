from datetime import date

from ledger import (
    DailyEntry,
    carry_over_to_next_month,
    monthly_commission,
    recalculate_chain,
    total_received_usd_equivalent,
)


def test_single_day_compute_basic_debt_reduction():
    entry = DailyEntry(
        sana=date(2026, 8, 1),
        kontragent_id="rashid",
        naqd_som=100000,
        click=50000,
        terminal=0,
        naqd_dollar=10,
        chegirma_som=20000,
        kurs=12800,
        qarz_boshida_som=0,
        qarz_boshida_dollar=500,
    ).compute()

    assert entry.jami_qabul_som == 150000
    assert entry.jami_qabul_dollar == 10
    # qolgan qarz som = 0 - 150000 - 20000 (chegirma) = -170000 -> avans
    assert entry.qolgan_qarz_som == -170000
    assert entry.is_avans_som is True
    # qolgan qarz dollar = 500 - 10 = 490
    assert entry.qolgan_qarz_dollar == 490
    assert entry.is_avans_dollar is False


def test_recalculate_chain_carries_debt_day_to_day():
    day1 = DailyEntry(
        sana=date(2026, 8, 1), kontragent_id="rashid",
        naqd_som=0, naqd_dollar=100,
        qarz_boshida_som=0, qarz_boshida_dollar=1000,
    )
    day2 = DailyEntry(
        sana=date(2026, 8, 2), kontragent_id="rashid",
        naqd_som=0, naqd_dollar=200,
    )
    day3 = DailyEntry(
        sana=date(2026, 8, 3), kontragent_id="rashid",
        naqd_som=0, naqd_dollar=50,
    )

    chain = recalculate_chain([day3, day1, day2])  # tartibsiz beriladi

    assert [e.sana for e in chain] == [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)]
    assert chain[0].qolgan_qarz_dollar == 900
    assert chain[1].qarz_boshida_dollar == 900
    assert chain[1].qolgan_qarz_dollar == 700
    assert chain[2].qarz_boshida_dollar == 700
    assert chain[2].qolgan_qarz_dollar == 650


def test_recalculate_chain_reflects_historical_correction():
    day1 = DailyEntry(
        sana=date(2026, 8, 1), kontragent_id="rashid",
        naqd_dollar=100, qarz_boshida_som=0, qarz_boshida_dollar=1000,
    )
    day2 = DailyEntry(sana=date(2026, 8, 2), kontragent_id="rashid", naqd_dollar=200)
    recalculate_chain([day1, day2])
    assert day2.qolgan_qarz_dollar == 700

    # 1-kun tuzatiladi (masalan qo'shimcha to'lov aniqlanadi)
    day1.naqd_dollar = 150
    recalculate_chain([day1, day2])
    assert day1.qolgan_qarz_dollar == 850
    assert day2.qarz_boshida_dollar == 850
    assert day2.qolgan_qarz_dollar == 650


def test_carry_over_to_next_month_only_carries_dollar():
    last_day = DailyEntry(
        sana=date(2026, 8, 31), kontragent_id="rashid",
        qarz_boshida_som=50000, qarz_boshida_dollar=300,
    ).compute()

    carried = carry_over_to_next_month(last_day)

    assert carried == {"qarz_boshida_som": 0, "qarz_boshida_dollar": 300}


def test_monthly_commission_uses_usd_equivalent_and_configurable_rate():
    entries = [
        DailyEntry(
            sana=date(2026, 8, 1), kontragent_id="rashid",
            naqd_som=128000, naqd_dollar=10, kurs=12800,
            qarz_boshida_som=0, qarz_boshida_dollar=1000,
        ).compute(),
        DailyEntry(
            sana=date(2026, 8, 1), kontragent_id="alisher",
            naqd_som=64000, naqd_dollar=5, kurs=12800,
            qarz_boshida_som=0, qarz_boshida_dollar=500,
        ).compute(),
    ]

    # jami qabul dollar ekvivalentida: (128000/12800 + 10) + (64000/12800 + 5) = 20 + 10 = 30
    assert total_received_usd_equivalent(entries) == 30
    assert monthly_commission(entries) == 0.3  # standart 1%
    assert monthly_commission(entries, rate=0.02) == 0.6
