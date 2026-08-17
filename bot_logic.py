"""bot.py uchun sof (Telegram'siz sinaladigan) yordamchi mantiq.

aiogram handlerlari shu funksiyalarga tayanadi - shunda kunlik ro'yxat,
qarzdorlar reytingi, sana parsing kabi mantiq haqiqiy botsiz sinaladi.
"""
from datetime import datetime

from ledger import received_usd_equivalent, recalculate_chain

DATE_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y")


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
    (DD.MM.YYYY va yaqin formatlar). Mos kelmasa None qaytaradi - hech
    qachon taxmin qilinmaydi."""
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
    oxirgi_tolov_sana_yoki_None), ...] - eng katta qarzdan boshlab
    saralangan, faqat haqiqiy qarzi (musbat) borlar (avans chiqarilmaydi).
    """
    debtors = []
    for kontragent_id, entries in entries_by_kontragent.items():
        if not entries:
            continue
        ordered = sorted(entries, key=lambda e: e.sana)
        latest = ordered[-1]
        if latest.qolgan_qarz_dollar <= 0:
            continue

        oxirgi_tolov = None
        for entry in reversed(ordered):
            if entry.jami_qabul_dollar > 0 or entry.jami_qabul_som > 0:
                oxirgi_tolov = entry.sana
                break

        debtors.append(
            (aliases_registry.rasmiy_nom(kontragent_id), latest.qolgan_qarz_dollar, oxirgi_tolov)
        )

    debtors.sort(key=lambda t: t[1], reverse=True)
    return debtors[:top_n]


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
