"""Bildirishnoma matnlarini shakllantirish (TEXNIK_TOPSHIRIQ.md 8-bo'lim).

Sof funksiyalar - Telegram bilan aloqa qilmaydi, faqat matn qaytaradi.
bot.py shu matnlarni tayyorlab, keyin yuboradi. Shu tarzda bildirishnoma
matnini haqiqiy botsiz sinash mumkin.
"""
from ledger import received_usd_equivalent


def _fmt(n, decimals=0):
    return f"{n:_.{decimals}f}".replace("_", " ")


def format_entry_confirmation(entry, kontragent_nomi):
    """Har kiritishdan keyin loyiha egasiga: qabul qilingan (so'm/click/
    terminal breakdown) + jami qabul ($) + qolgan qarz ($)."""
    lines = [f"{kontragent_nomi} - {entry.sana.isoformat()}"]
    lines.append(f"Naqd so'm: {_fmt(entry.naqd_som)}")
    lines.append(f"Click: {_fmt(entry.click)}")
    lines.append(f"Terminal: {_fmt(entry.terminal)}")
    lines.append(f"Naqd dollar: {_fmt(entry.naqd_dollar, 2)}")
    if entry.chegirma_som:
        lines.append(f"Chegirma: {_fmt(entry.chegirma_som)} so'm")

    lines.append(f"Jami qabul: ${_fmt(received_usd_equivalent(entry), 2)}")
    holat = "avans" if entry.is_avans_dollar else "qarz"
    lines.append(f"Qolgan {holat}: ${_fmt(abs(entry.qolgan_qarz_dollar), 2)}")
    return "\n".join(lines)


def format_morning_digest(top_debtors):
    """Har kuni ertalab: eng katta qarzdorlar (oy bo'yicha jami + oxirgi
    to'lov), to'liq ro'yxat dashboard'da.

    top_debtors: [(kontragent_nomi, qarz_dollar, oxirgi_tolov_sana_yoki_None), ...]
    eng kattadan boshlab saralangan (bot_logic.top_debtors natijasi)."""
    if not top_debtors:
        return "Bugun qarzdorlar ro'yxati bo'sh."

    lines = ["Eng katta qarzdorlar:"]
    for i, (nomi, qarz, oxirgi_tolov) in enumerate(top_debtors, start=1):
        oxirgi = oxirgi_tolov.isoformat() if oxirgi_tolov else "ma'lum emas"
        lines.append(f"{i}. {nomi} - ${_fmt(qarz, 2)} (oxirgi to'lov: {oxirgi})")
    return "\n".join(lines)


def format_month_end_summary(oy_nomi, jami_topshirilgan_usd, komissiya_usd, jami_chegirma_som):
    """Oy oxirida: jami topshirilgan ($), komissiya, chegirmalar jami."""
    return (
        f"{oy_nomi} oyi yakuni:\n"
        f"Jami topshirilgan: ${_fmt(jami_topshirilgan_usd, 2)}\n"
        f"Komissiya: ${_fmt(komissiya_usd, 2)}\n"
        f"Jami chegirmalar: {_fmt(jami_chegirma_som)} so'm"
    )


def format_alert_no_payment(kontragent_nomi, kun_soni):
    """3+ kun to'lovsiz."""
    return f"Diqqat: {kontragent_nomi} {kun_soni} kundan beri to'lov qilmadi."


def format_alert_large_discount(kontragent_nomi, chegirma_som):
    """G'ayrioddiy katta chegirma."""
    return f"Diqqat: {kontragent_nomi}ga g'ayrioddiy katta chegirma berildi - {_fmt(chegirma_som)} so'm."


def format_alert_debt_threshold(kontragent_nomi, qarz_dollar, chegara_dollar):
    """Qarz belgilangan chegaradan oshsa."""
    return (
        f"Diqqat: {kontragent_nomi}ning qarzi belgilangan chegaradan oshdi - "
        f"${_fmt(qarz_dollar, 2)} (chegara: ${_fmt(chegara_dollar, 2)})."
    )


def format_alert_missing_from_list(kontragent_nomi, sana):
    """Kontragent kunlik ro'yxatga kiritilmay qolsa."""
    return f"Diqqat: {kontragent_nomi} {sana.isoformat()} kunlik ro'yxatga kiritilmadi."


def format_alert_past_day_corrected(kontragent_nomi, sana, tahrirlagan):
    """O'tgan kun tuzatilsa."""
    return (
        f"Diqqat: {tahrirlagan} {sana.isoformat()} kunidagi {kontragent_nomi} "
        f"yozuvini tuzatdi. Keyingi barcha kunlar qayta hisoblandi."
    )
