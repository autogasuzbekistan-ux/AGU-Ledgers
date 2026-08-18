"""Kunlik yozuv ma'lumotlar modeli va qarz/to'lov formulalari.

TEXNIK_TOPSHIRIQ.md 3-bo'lim (ma'lumotlar modeli) va 7-bo'lim (tarixiy
tuzatish - zanjir mantig'i) asosida.

MUHIM (loyiha egasi bilan tasdiqlash kerak bo'lgan taxmin): "Jami qabul"
faqat haqiqatda qabul qilingan pulni (naqd + click + terminal/naqd dollar)
o'z ichiga oladi - komissiya shu summadan hisoblanadi. "Chegirma" alohida
- u qarzni kamaytiradi, lekin komissiya bazasiga kirmaydi (chunki
komissiya haqiqiy qabul qilingan puldan olinadi, berilgan chegirmadan
emas). Bu 8-bo'limdagi bildirishnomada "jami topshirilgan ($)" va
"chegirmalar jami" alohida-alohida ko'rsatilishiga mos keladi.
"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class DailyEntry:
    sana: date
    kontragent_id: str

    naqd_som: float = 0
    click: float = 0
    naqd_dollar: float = 0
    terminal: float = 0
    chegirma_som: float = 0
    kurs: float | None = None

    # Kun 1: qo'lda kiritiladi (dollar - o'tgan oydan, so'm - 0).
    # Kun >1: recalculate_chain() oldingi kunning qolgan qarzidan oladi.
    qarz_boshida_som: float = 0
    qarz_boshida_dollar: float = 0

    jami_qabul_som: float = field(default=0, init=False)
    jami_qabul_dollar: float = field(default=0, init=False)
    qolgan_qarz_som: float = field(default=0, init=False)
    qolgan_qarz_dollar: float = field(default=0, init=False)

    def compute(self):
        """Qarz_boshida va kirim maydonlaridan jami qabul va qolgan
        qarzni hisoblaydi. Chaqiruvchi qarz_boshida'ni to'g'ri qiymatga
        o'rnatgandan keyin chaqirilishi kerak (recalculate_chain buni
        avtomatik qiladi)."""
        self.jami_qabul_som = self.naqd_som + self.click + self.terminal
        self.jami_qabul_dollar = self.naqd_dollar
        self.qolgan_qarz_som = (
            self.qarz_boshida_som - self.jami_qabul_som - self.chegirma_som
        )
        self.qolgan_qarz_dollar = self.qarz_boshida_dollar - self.jami_qabul_dollar
        return self

    @property
    def is_avans_som(self):
        """Qolgan qarz (so'm) manfiy chiqsa - bu qarz emas, avans."""
        return self.qolgan_qarz_som < 0

    @property
    def is_avans_dollar(self):
        """Qolgan qarz (dollar) manfiy chiqsa - bu qarz emas, avans."""
        return self.qolgan_qarz_dollar < 0


def recalculate_chain(entries):
    """Bitta kontragentning kunlari (sana bo'yicha, tartiblanmagan bo'lishi
    mumkin) ro'yxatini qabul qiladi. Har bir kunning qarz_boshida'sini
    oldingi kunning qolgan_qarz'idan avtomatik oladi (1-kundan tashqari -
    uning qarz_boshida'si chaqiruvchi tomonidan oldindan berilgan bo'lishi
    kerak) va hammasini qayta hisoblaydi.

    TEXNIK_TOPSHIRIQ.md 7-bo'lim: o'tgan kundagi yozuvni tuzatish -
    undan keyingi BARCHA kunlarni avtomatik qayta hisoblashi kerak. Shu
    funksiyani tuzatilgan kundan boshlab (yoki butun ro'yxat bilan)
    qayta chaqirish shu talabni qondiradi.

    Oy chegarasidan o'tganda (kun ro'yxati bir necha oyni qamrab olsa)
    avtomatik carry_over_to_next_month qoidasini qo'llaydi - FAQAT
    dollar o'tadi, so'm har oy 0'dan boshlanadi (3-bo'lim). Shu tufayli
    chaqiruvchi oylarni qo'lda ajratishi shart emas - butun tarixni
    berish kifoya.
    """
    ordered = sorted(entries, key=lambda e: e.sana)
    for i, entry in enumerate(ordered):
        if i > 0:
            prev = ordered[i - 1]
            if (prev.sana.year, prev.sana.month) != (entry.sana.year, entry.sana.month):
                carried = carry_over_to_next_month(prev)
                entry.qarz_boshida_som = carried["qarz_boshida_som"]
                entry.qarz_boshida_dollar = carried["qarz_boshida_dollar"]
            else:
                entry.qarz_boshida_som = prev.qolgan_qarz_som
                entry.qarz_boshida_dollar = prev.qolgan_qarz_dollar
        entry.compute()
    return ordered


def carry_over_to_next_month(last_entry_of_month):
    """Oy oxiridagi qolgan qarzdan keyingi oyning 1-kuni uchun boshlang'ich
    qarzni hisoblaydi. FAQAT dollar o'tadi - so'm qarzi har oy 0'dan
    boshlanadi (TEXNIK_TOPSHIRIQ.md 3-bo'lim)."""
    return {
        "qarz_boshida_som": 0,
        "qarz_boshida_dollar": last_entry_of_month.qolgan_qarz_dollar,
    }


def received_usd_equivalent(entry):
    """Bitta yozuvda haqiqatda qabul qilingan pulni dollar ekvivalentida
    qaytaradi (kurs bo'lmasa - faqat naqd dollar hisobga olinadi)."""
    total = entry.jami_qabul_dollar
    if entry.kurs:
        total += entry.jami_qabul_som / entry.kurs
    return total


def total_received_usd_equivalent(entries):
    """Bir nechta yozuv (turli kun/kontragent) bo'yicha haqiqatda qabul
    qilingan pulni dollar ekvivalentida jamlaydi (komissiya bazasi)."""
    return sum(received_usd_equivalent(e) for e in entries)


def monthly_commission(entries, rate=0.01):
    """Oylik komissiya = jami qabul qilingan pul (dollar ekvivalentida) x
    stavka. Stavka standart 1%, lekin kodga qattiq yozilmagan - chaqiruvchi
    (masalan Sheets'dagi sozlanadigan katakchadan o'qib) o'zgartira oladi."""
    return total_received_usd_equivalent(entries) * rate
