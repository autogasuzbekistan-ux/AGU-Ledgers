"""bot.py uchun sof (Telegram'siz sinaladigan) yordamchi mantiq.

aiogram handlerlari shu funksiyalarga tayanadi - shunda kunlik ro'yxat,
qarzdorlar reytingi, sana parsing kabi mantiq haqiqiy botsiz sinaladi.
"""
from datetime import datetime

from ledger import received_usd_equivalent, recalculate_chain

DATE_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y")

OY_NOMLARI_UZ = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]


def apply_entry(history, new_entry):
    """Bitta kontragentning to'liq tarixiga (`history`) yangi/tuzatilgan
    kunni (`new_entry`) qo'shib, butun zanjirni qayta hisoblaydi
    (TEXNIK_TOPSHIRIQ.md 7-bo'lim - "kechiktirilgan kun" yoki "tuzatish"
    orqali o'tgan kun o'zgarganda ham keyingi barcha kunlar avtomatik
    to'g'rilanadi).

    Qaytaradi: to'liq qayta hisoblangan tarix (sana bo'yicha tartiblangan).
    Chaqiruvchi Sheets'ga faqat `new_entry.sana`dan boshlab (shu kunni
    ham qo'shgan holda) keyingi yozuvlarni qayta yozishi kifoya - undan
    oldingi kunlar o'zgarmaydi."""
    replaced = [e for e in history if e.sana != new_entry.sana] + [new_entry]
    return recalculate_chain(replaced)


def has_prior_entry(history, sana):
    """Berilgan sanadan oldin kontragent uchun kamida bitta yozuv
    bor-yo'qligini tekshiradi. Yo'q bo'lsa - bu kontragentning birinchi
    yozuvi, boshlang'ich qarz (dollar) qo'lda so'ralishi kerak
    (3-bo'lim: "Kun 1: input")."""
    return any(e.sana < sana for e in history)


def compute_pending_kontragents(all_ids, ids_with_entry_today):
    """Bugun uchun hali yozuv kiritilmagan kontragentlar ro'yxati
    (6-bo'lim: har bir kontragent uchun "to'liq"/"to'liq emas" holati)."""
    entered = set(ids_with_entry_today)
    return [kid for kid in all_ids if kid not in entered]


def is_unusually_large_amount(entry, threshold_usd):
    """9-bo'lim: g'ayrioddiy katta summa kiritilsa - qo'shimcha tasdiq
    so'raladi."""
    return received_usd_equivalent(entry) > threshold_usd


def parse_manual_date(text):
    """"Kechiktirilgan kun" tugmasi uchun sana matnini o'qiydi
    (DD.MM.YYYY va yaqin formatlar). Mos kelmasa (yoki matn berilmasa -
    masalan foydalanuvchi rasm/sticker yuborsa) None qaytaradi - hech
    qachon taxmin qilinmaydi."""
    if text is None:
        return None
    text = text.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def top_debtors(entries_by_kontragent, aliases_registry, top_n=10):
    """entries_by_kontragent: {kontragent_id: [DailyEntry, ...]} (har
    kontragentning barcha tarixi). Qaytaradi: [(rasmiy_nom, qarz_dollar,
    oxirgi_tolov_sana_yoki_None, oxirgi_tolov_summa_dollar), ...] - eng
    katta qarzdan boshlab saralangan, faqat haqiqiy qarzi (musbat)
    borlar (avans chiqarilmaydi). To'lov umuman bo'lmagan bo'lsa
    oxirgi_tolov_summa 0.

    top_n=None - cheklovsiz, BARCHA qarzdorlar qaytariladi (masalan
    to'liq Excel hisobot uchun - chat xabaridagi qisqartirilgan
    ro'yxatdan farqli)."""
    debtors = []
    for kontragent_id, entries in entries_by_kontragent.items():
        if not entries:
            continue
        ordered = sorted(entries, key=lambda e: e.sana)
        latest = ordered[-1]
        if latest.qolgan_qarz_dollar <= 0:
            continue

        oxirgi_tolov_sana = None
        oxirgi_tolov_summa = 0
        for entry in reversed(ordered):
            if entry.jami_qabul_dollar > 0 or entry.jami_qabul_som > 0:
                oxirgi_tolov_sana = entry.sana
                oxirgi_tolov_summa = received_usd_equivalent(entry)
                break

        debtors.append((
            aliases_registry.rasmiy_nom(kontragent_id), latest.qolgan_qarz_dollar,
            oxirgi_tolov_sana, oxirgi_tolov_summa,
        ))

    debtors.sort(key=lambda t: t[1], reverse=True)
    return debtors if top_n is None else debtors[:top_n]


def daily_payments_summary(entries_by_kontragent):
    """Barcha kontragentlar bo'yicha kunlik jami tushumni jamlaydi.

    Qaytaradi: [(sana, naqd_som, click, terminal, naqd_dollar, jami_usd), ...]
    - sana bo'yicha KAMAYISH tartibida (eng so'nggi kun birinchi)."""
    daily = {}
    for entries in entries_by_kontragent.values():
        for entry in entries:
            acc = daily.setdefault(entry.sana, {
                "naqd_som": 0, "click": 0, "terminal": 0, "naqd_dollar": 0, "usd": 0,
            })
            acc["naqd_som"] += entry.naqd_som
            acc["click"] += entry.click
            acc["terminal"] += entry.terminal
            acc["naqd_dollar"] += entry.naqd_dollar
            acc["usd"] += received_usd_equivalent(entry)

    return [
        (sana, acc["naqd_som"], acc["click"], acc["terminal"], acc["naqd_dollar"], acc["usd"])
        for sana, acc in sorted(daily.items(), key=lambda item: item[0], reverse=True)
    ]


def daily_payments_detail(entries_by_kontragent, aliases_registry):
    """daily_payments_summary'dan farqli - kunlarni jamlamaydi, har bir
    kontragentning har kunlik yozuvini ALOHIDA qatorga chiqaradi (loyiha
    egasi so'ragan "hamma kontragent alohida ajralgan holda" ko'rinishi -
    pul topshirish oqimini kim-qachon-qancha darajasida nazorat qilish
    uchun). Faqat haqiqatda biror to'lov bo'lgan kunlar chiqariladi.

    Qaytaradi: [(sana, kontragent_nomi, naqd_som, click, terminal,
    naqd_dollar, jami_usd), ...] - sana bo'yicha KAMAYISH, bir xil sana
    ichida kontragent nomi bo'yicha O'SISH tartibida."""
    rows = []
    for kontragent_id, entries in entries_by_kontragent.items():
        nomi = aliases_registry.rasmiy_nom(kontragent_id)
        for entry in entries:
            if entry.naqd_som or entry.click or entry.terminal or entry.naqd_dollar:
                rows.append((
                    entry.sana, nomi, entry.naqd_som, entry.click,
                    entry.terminal, entry.naqd_dollar, received_usd_equivalent(entry),
                ))

    rows.sort(key=lambda r: r[1])  # avval kontragent nomi bo'yicha o'sish
    rows.sort(key=lambda r: r[0], reverse=True)  # keyin sana bo'yicha kamayish (stable)
    return rows


def monthly_summary(entries_by_kontragent, commission_rate=0.01):
    """Barcha kontragentlar bo'yicha OYLIK jami tushumni jamlaydi - "pul
    topshirish oqimi"ni oy kesimida kuzatish/nazorat qilish uchun
    (TEXNIK_TOPSHIRIQ.md 8-bo'lim: oy oxiridagi hisobot bilan bir xil
    mantiq, lekin bitta oy emas - butun tarix bo'yicha, trend ko'rish
    uchun).

    Qaytaradi: [(oy_label, naqd_som, click, terminal, naqd_dollar,
    jami_usd, komissiya_usd), ...] - oy bo'yicha KAMAYISH tartibida
    (eng so'nggi oy birinchi)."""
    monthly = {}
    for entries in entries_by_kontragent.values():
        for entry in entries:
            key = (entry.sana.year, entry.sana.month)
            acc = monthly.setdefault(key, {
                "naqd_som": 0, "click": 0, "terminal": 0, "naqd_dollar": 0, "usd": 0,
            })
            acc["naqd_som"] += entry.naqd_som
            acc["click"] += entry.click
            acc["terminal"] += entry.terminal
            acc["naqd_dollar"] += entry.naqd_dollar
            acc["usd"] += received_usd_equivalent(entry)

    result = []
    for (year, month), acc in sorted(monthly.items(), reverse=True):
        label = f"{year}-{month:02d} ({OY_NOMLARI_UZ[month - 1]})"
        komissiya = acc["usd"] * commission_rate
        result.append((
            label, acc["naqd_som"], acc["click"], acc["terminal"],
            acc["naqd_dollar"], acc["usd"], komissiya,
        ))
    return result


def days_since_last_payment(entries, today):
    """Oxirgi haqiqiy to'lovdan beri necha kun o'tganini hisoblaydi
    (3+ kun to'lovsiz signali uchun). To'lov umuman bo'lmagan bo'lsa,
    ro'yxatdagi eng birinchi kundan buyon hisoblanadi. Bo'sh ro'yxat uchun
    None qaytaradi."""
    if not entries:
        return None
    ordered = sorted(entries, key=lambda e: e.sana)
    last_payment_day = ordered[0].sana
    for entry in ordered:
        if entry.jami_qabul_dollar > 0 or entry.jami_qabul_som > 0:
            last_payment_day = entry.sana
    return (today - last_payment_day).days
