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


def format_upload_diff(diff, names_by_id, kind, kurs, title=None):
    """Fayl qayta yuklanganda (6-bo'lim) tasdiqlash uchun diff'ni o'qiladigan
    matnga aylantiradi. "click" turi uchun so'm summasi kursga bo'linib
    dollar ekvivalenti ham ko'rsatiladi - shu orqali operator qancha pul
    haqida gap ketayotganini $ da ham ko'radi, faqat xom so'mni emas.
    "hisobot"/"report" uchun qiymatlar allaqachon {naqd_som, click,
    naqd_dollar, terminal} ko'rinishidagi dict - har bir maydon alohida
    ko'rsatiladi, jami esa dollar ekvivalentida hisoblanadi."""
    lines = []
    if title:
        lines.append(title)

    if kind == "click":
        if kurs:
            lines.append(f"Kurs: {kurs}")
        else:
            lines.append("Kurs hali kiritilmagan - dollar ekvivalenti ko'rsatilmaydi.")

        def fmt_click(som):
            usd = f" (${_fmt(som / kurs, 2)})" if kurs else ""
            return f"{_fmt(som)} so'm{usd}"

        for kid, (eski, yangi) in diff["ozgargan"].items():
            lines.append(f"{names_by_id.get(kid, kid)}: {fmt_click(eski)} -> {fmt_click(yangi)}")
        for kid, yangi in diff["yangi"].items():
            lines.append(f"{names_by_id.get(kid, kid)}: (yo'q edi) -> {fmt_click(yangi)}")
        for kid, eski in diff["yoqolgan"].items():
            lines.append(f"{names_by_id.get(kid, kid)}: {fmt_click(eski)} -> (faylda endi yo'q)")
        return lines

    def fmt_breakdown(d):
        usd = d.get("naqd_dollar", 0) + (
            (d.get("naqd_som", 0) + d.get("click", 0) + d.get("terminal", 0)) / kurs if kurs else 0
        )
        return (
            f"so'm={_fmt(d.get('naqd_som', 0))}, click={_fmt(d.get('click', 0))}, "
            f"terminal={_fmt(d.get('terminal', 0))}, dollar={_fmt(d.get('naqd_dollar', 0), 2)} "
            f"(jami ${_fmt(usd, 2)})"
        )

    for kid, (eski, yangi) in diff["ozgargan"].items():
        lines.append(f"{names_by_id.get(kid, kid)}:\n  eski: {fmt_breakdown(eski)}\n  yangi: {fmt_breakdown(yangi)}")
    for kid, yangi in diff["yangi"].items():
        lines.append(f"{names_by_id.get(kid, kid)}: (yo'q edi) -> {fmt_breakdown(yangi)}")
    for kid, eski in diff["yoqolgan"].items():
        lines.append(f"{names_by_id.get(kid, kid)}: {fmt_breakdown(eski)} -> (faylda endi yo'q)")
    return lines


def format_morning_digest(top_debtors):
    """Har kuni ertalab: eng katta qarzdorlar (oy bo'yicha jami + oxirgi
    to'lov sanasi va summasi), to'liq ro'yxat dashboard'da.

    top_debtors: [(kontragent_nomi, qarz_dollar, oxirgi_tolov_sana_yoki_None,
    oxirgi_tolov_summa_dollar), ...] eng kattadan boshlab saralangan
    (bot_logic.top_debtors natijasi)."""
    if not top_debtors:
        return "Bugun qarzdorlar ro'yxati bo'sh."

    lines = ["Eng katta qarzdorlar:"]
    for i, (nomi, qarz, oxirgi_tolov, oxirgi_tolov_summa) in enumerate(top_debtors, start=1):
        oxirgi = oxirgi_tolov.isoformat() if oxirgi_tolov else "ma'lum emas"
        lines.append(
            f"{i}. {nomi} - ${_fmt(qarz, 2)} "
            f"(oxirgi to'lov: {oxirgi}, ${_fmt(oxirgi_tolov_summa, 2)})"
        )
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
