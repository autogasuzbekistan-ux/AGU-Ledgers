"""AGU Virtual Ofis - Telegram bot (aiogram 3.x).

TEXNIK_TOPSHIRIQ.md 6-bo'lim: bot muloqot oqimi. Bu modul ledger.py,
aliases.py, diff.py, sheets.py, notifications.py, bot_logic.py, audit.py
modullarini bog'laydi - ularning barchasi mustaqil, haqiqiy bot/tarmoqsiz
sinalgan (tests/). bot.py'ning o'zi aiogram Bot API va Google Sheets bilan
ishlaydi, shuning uchun haqiqiy BOT_TOKEN, service account va tarmoq
aloqasi bo'lmasa avtomatik sinalmaydi - bu modul faqat qo'lda, real
sozlamalar bilan sinalishi kerak.

Ishga tushirish: `.env` to'ldirilgach `python3 bot.py`.
"""
import asyncio
import calendar
import logging
import os
import sys
from datetime import date, timedelta

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    Document,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aliases import AliasRegistry
from audit import AuditLog
from bot_logic import (
    apply_entry,
    compute_pending_kontragents,
    daily_payments_detail,
    daily_payments_summary,
    days_since_last_payment,
    has_prior_entry,
    is_unusually_large_amount,
    monthly_summary,
    parse_manual_date,
    top_debtors,
)
from config import Config, load_config
from diff import diff_parsed_data, has_changes
from ledger import DailyEntry, monthly_commission, total_received_usd_equivalent
from notifications import (
    format_alert_debt_threshold,
    format_alert_no_payment,
    format_alert_past_day_corrected,
    format_entry_confirmation,
    format_month_end_summary,
    format_upload_diff,
)
from parsers import parse_click_file, parse_hisobot_file
from reports import build_debtors_report
from sheets import SheetsClient

# stream=sys.stdout - standart holatda logging stderr'ga yozadi, Railway
# (va ko'plab konteyner platformalari) esa stderr'ni log darajasidan
# qat'iy nazar QIZIL qilib ko'rsatadi. Oddiy INFO yozuvlari xato emas -
# stdout'ga yo'naltirib, bu chalkashlikni oldini olamiz.
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("agu_bot")

FIELD_QUESTIONS = [
    ("naqd_som", "Naqd so'm qancha?"),
    ("click", "Click qancha?"),
    ("naqd_dollar", "Naqd dollar (qog'oz) qancha?"),
    ("terminal", "Terminal (plastik + o'tkazma) qancha?"),
]
OY_NOMLARI_UZ = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]

MENU_UPLOAD = "\U0001F4E5 Fayl yuborish"
MENU_MANUAL = "✍️ Qo'lda kiritish"
MENU_EDIT = "✏️ Tahrirlash"
MENU_DEBTORS = "\U0001F4CA Qarzdorlar"
MENU_KURS = "\U0001F4B1 Kurs"


class EntryStates(StatesGroup):
    waiting_kurs = State()
    waiting_initial_qarz_dollar = State()
    waiting_field = State()
    waiting_delayed_date = State()
    confirm_summary = State()
    confirm_large_amount = State()


class KursStates(StatesGroup):
    updating = State()


class EditStates(StatesGroup):
    waiting_kontragent = State()
    waiting_date = State()


class ReuploadStates(StatesGroup):
    waiting_confirmation = State()


# ---------------------------------------------------------------------
# Ruxsat nazorati (9-bo'lim: faqat ro'yxatga olingan Telegram ID(lar))
# ---------------------------------------------------------------------
class AccessMiddleware(BaseMiddleware):
    def __init__(self, cfg: Config):
        super().__init__()
        self.cfg = cfg

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is not None and not self.cfg.is_allowed(user.id):
            logger.warning("Ruxsatsiz urinish: telegram_id=%s", user.id)
            return
        return await handler(event, data)


# ---------------------------------------------------------------------
# Kurs - kunning BIRINCHI harakatidan oldin so'raladi (6-bo'lim: kuniga
# bir marta so'raladi, keyin shu kunning barcha yozuvlariga qo'llanadi).
# Buyruq/tugma/fayl - nima bo'lishidan qat'iy nazar, kurs hali
# kiritilmagan bo'lsa, boshqa hech narsa qilinmasdan avval shu so'raladi.
# ---------------------------------------------------------------------
class KursGateMiddleware(BaseMiddleware):
    def __init__(self, sheets: SheetsClient):
        super().__init__()
        self.sheets = sheets

    async def __call__(self, handler, event, data):
        state: FSMContext = data.get("state")
        if state is not None:
            current_state = await state.get_state()
            if current_state == EntryStates.waiting_kurs.state:
                return await handler(event, data)  # bu - kursga javob

            sana = date.today()
            if self.sheets.get_kurs(sana) is None:
                await state.set_state(EntryStates.waiting_kurs)
                await state.update_data(kurs_sana=sana.isoformat(), flow="auto")
                await event.answer(f"Avval {sana.isoformat()} uchun bugungi kursni kiriting.")
                return

        return await handler(event, data)


def _parse_number(text):
    """Foydalanuvchi kiritgan sonni o'qiydi - bo'sh joy (minglik
    ajratgichi) va vergul/nuqta (kasr ajratgichi, ikkala format ham:
    "41850,00" YOKI "41.850,00" YOKI "41,850.00") bilan. Noto'g'ri bo'lsa
    yoki matn bo'lmasa (masalan foydalanuvchi rasm/sticker yuborsa,
    message.text None bo'ladi) None qaytaradi."""
    if text is None:
        return None
    cleaned = text.strip().replace(" ", "")
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            # vergul kasr ajratgichi ("41.850,00" - nuqta minglik)
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # nuqta kasr ajratgichi ("41,850.00" - vergul minglik)
            cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_UPLOAD), KeyboardButton(text=MENU_MANUAL)],
            [KeyboardButton(text=MENU_EDIT), KeyboardButton(text=MENU_DEBTORS)],
            [KeyboardButton(text=MENU_KURS)],
        ],
        resize_keyboard=True,
    )


def _cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Bugun to'lov yo'q", callback_data="skip_today")],
    ])


def _summary_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Tasdiqlash", callback_data="confirm_entry"),
            InlineKeyboardButton(text="Tuzatish", callback_data="edit_entry"),
        ],
    ])


def _large_amount_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Ha, to'g'ri", callback_data="confirm_large"),
            InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_large"),
        ],
    ])


def _reupload_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Tasdiqlash", callback_data="reupload_confirm"),
            InlineKeyboardButton(text="Bekor qilish", callback_data="reupload_cancel"),
        ],
    ])


def build_router():
    router = Router()

    # -------------------------------------------------------------
    # Umumiy buyruqlar
    # -------------------------------------------------------------
    @router.message(Command("start"))
    async def cmd_start(message: Message):
        await message.answer(
            "AGU Virtual Ofis botiga xush kelibsiz.\n"
            "Quyidagi tugmalardan foydalaning, yoki /kechiktirilgan bilan "
            "o'tgan kunga yozuv kiriting.",
            reply_markup=_main_menu_keyboard(),
        )

    # -------------------------------------------------------------
    # Kurs so'rash (kuniga bir marta)
    # -------------------------------------------------------------
    async def _ensure_kurs(message_or_cb, state: FSMContext, sheets: SheetsClient, sana: date):
        kurs = sheets.get_kurs(sana)
        if kurs is not None:
            return kurs
        await state.set_state(EntryStates.waiting_kurs)
        await state.update_data(kurs_sana=sana.isoformat())
        target = message_or_cb.message if isinstance(message_or_cb, CallbackQuery) else message_or_cb
        await target.answer(f"{sana.isoformat()} uchun bugungi kurs qancha?")
        return None

    async def _begin_questions_for(message: Message, state: FSMContext, sheets, aliases_registry, kontragent_id, sana, flow):
        """Berilgan kontragent+sana uchun savol-javob oqimini boshlaydi.
        flow="auto" - /kirim orqali, tasdiqdan keyin keyingi kontragentga
        o'tadi. flow="single" - "Tahrirlash" orqali, tasdiqdan keyin faqat
        shu bitta yozuv saqlanadi."""
        await state.update_data(
            kontragent_id=kontragent_id, sana=sana.isoformat(), field_index=0, answers={}, flow=flow,
        )
        nomi = aliases_registry.rasmiy_nom(kontragent_id)

        history = sheets.read_entries(kontragent_id)
        if not has_prior_entry(history, sana):
            await state.set_state(EntryStates.waiting_initial_qarz_dollar)
            await message.answer(
                f"{nomi} - bu birinchi yozuv. Boshlang'ich qarz (dollar) qancha? "
                f"(so'm qarzi 0 dan boshlanadi)"
            )
            return

        await state.set_state(EntryStates.waiting_field)
        field_key, question = FIELD_QUESTIONS[0]
        await message.answer(f"{nomi}\n{question}", reply_markup=_cancel_keyboard())

    async def _start_next_kontragent(message: Message, state: FSMContext, sheets, aliases_registry, sana):
        all_ids = [kid for kid, _ in aliases_registry.kontragentlar()]
        entries_today = sheets.read_all_entries()
        done_today = [
            kid for kid, entries in entries_today.items()
            if any(e.sana == sana for e in entries)
        ]
        pending = compute_pending_kontragents(all_ids, done_today)
        if not pending:
            await state.clear()
            await message.answer(
                f"{sana.isoformat()} uchun barcha kontragentlar kiritildi.",
                reply_markup=_main_menu_keyboard(),
            )
            return

        await _begin_questions_for(message, state, sheets, aliases_registry, pending[0], sana, flow="auto")

    async def _start_single_entry(message: Message, state: FSMContext, sheets, aliases_registry, kontragent_id, sana):
        await _begin_questions_for(message, state, sheets, aliases_registry, kontragent_id, sana, flow="single")

    async def _do_kirim(message: Message, state: FSMContext, sheets, aliases_registry):
        sana = date.today()
        # flow'ni _ensure_kurs'dan OLDIN "auto"ga o'rnatish shart - agar
        # kurs shu kun uchun hali noma'lum bo'lsa, _ensure_kurs
        # waiting_kurs holatiga o'tadi va on_kurs_answer keyinroq shu
        # "flow" qiymatiga qarab qaysi kontragentga davom etishni
        # tanlaydi. Agar bu yerda o'rnatilmasa, avvalgi (masalan
        # abandon qilingan "Tahrirlash") sessiyadan qolgan eski
        # flow="single" + edit_kontragent_id qiymatlari saqlanib qolib,
        # /kirim shu eski (noto'g'ri) kontragent uchun yakka yozuv
        # boshlab, qolgan barcha kontragentlarni jimgina o'tkazib
        # yuborishi mumkin edi.
        await state.update_data(flow="auto")
        kurs = await _ensure_kurs(message, state, sheets, sana)
        if kurs is None:
            return
        await state.update_data(sana=sana.isoformat())
        await _start_next_kontragent(message, state, sheets, aliases_registry, sana)

    @router.message(Command("kirim"))
    async def cmd_kirim(message: Message, state: FSMContext, sheets, aliases_registry):
        await _do_kirim(message, state, sheets, aliases_registry)

    @router.message(F.text == MENU_MANUAL)
    async def on_menu_manual(message: Message, state: FSMContext, sheets, aliases_registry):
        await _do_kirim(message, state, sheets, aliases_registry)

    @router.message(Command("kechiktirilgan"))
    async def cmd_kechiktirilgan(message: Message, state: FSMContext):
        await state.set_state(EntryStates.waiting_delayed_date)
        await message.answer("Qaysi sanaga yozuv kiritmoqchisiz? (KK.OO.YYYY, masalan 15.08.2026)")

    @router.message(EntryStates.waiting_delayed_date)
    async def on_delayed_date(message: Message, state: FSMContext, sheets, aliases_registry):
        sana = parse_manual_date(message.text)
        if sana is None:
            await message.answer("Sana tushunilmadi. Format: KK.OO.YYYY (masalan 15.08.2026)")
            return
        # _do_kirim'dagi kabi - flow'ni _ensure_kurs'dan oldin "auto"ga
        # o'rnatish, eski (masalan abandon qilingan "Tahrirlash")
        # sessiyadan qolgan flow="single" qiymati sizib chiqmasligi uchun.
        await state.update_data(flow="auto")
        kurs = await _ensure_kurs(message, state, sheets, sana)
        if kurs is None:
            return
        await state.update_data(sana=sana.isoformat())
        await _start_next_kontragent(message, state, sheets, aliases_registry, sana)

    @router.message(EntryStates.waiting_kurs)
    async def on_kurs_answer(message: Message, state: FSMContext, sheets, aliases_registry):
        kurs = _parse_number(message.text)
        if kurs is None or kurs <= 0:
            await message.answer("Noto'g'ri qiymat. Kursni raqam bilan yuboring.")
            return
        data = await state.get_data()
        sana = date.fromisoformat(data["kurs_sana"])
        sheets.set_kurs(sana, kurs)
        await message.answer(f"Kurs saqlandi: {kurs}")
        await state.update_data(sana=sana.isoformat())

        if data.get("flow") == "single":
            await _start_single_entry(message, state, sheets, aliases_registry, data["edit_kontragent_id"], sana)
        else:
            await _start_next_kontragent(message, state, sheets, aliases_registry, sana)

    @router.message(EntryStates.waiting_initial_qarz_dollar)
    async def on_initial_qarz(message: Message, state: FSMContext):
        qarz = _parse_number(message.text)
        if qarz is None:
            await message.answer("Noto'g'ri qiymat. Boshlang'ich qarzni (dollar) raqam bilan yuboring.")
            return
        await state.update_data(initial_qarz_dollar=qarz)
        await state.set_state(EntryStates.waiting_field)
        data = await state.get_data()
        field_key, question = FIELD_QUESTIONS[data["field_index"]]
        await message.answer(question, reply_markup=_cancel_keyboard())

    # -------------------------------------------------------------
    # 4 ta savol (naqd so'm / click / naqd dollar / terminal)
    # -------------------------------------------------------------
    async def _show_summary(message: Message, state: FSMContext, cfg, sheets, aliases_registry, audit):
        data = await state.get_data()
        sana = date.fromisoformat(data["sana"])
        kontragent_id = data["kontragent_id"]
        answers = data["answers"]
        kurs = sheets.get_kurs(sana)

        history = sheets.read_entries(kontragent_id)
        qarz_boshida_som, qarz_boshida_dollar = 0, data.get("initial_qarz_dollar", 0)
        if has_prior_entry(history, sana):
            prior = sorted((e for e in history if e.sana < sana), key=lambda e: e.sana)[-1]
            qarz_boshida_som, qarz_boshida_dollar = prior.qolgan_qarz_som, prior.qolgan_qarz_dollar

        entry = DailyEntry(
            sana=sana, kontragent_id=kontragent_id, kurs=kurs,
            qarz_boshida_som=qarz_boshida_som, qarz_boshida_dollar=qarz_boshida_dollar,
            **answers,
        ).compute()
        await state.update_data(pending_entry=_entry_to_dict(entry))

        nomi = aliases_registry.rasmiy_nom(kontragent_id)
        if is_unusually_large_amount(entry, cfg.large_amount_threshold_usd):
            await state.set_state(EntryStates.confirm_large_amount)
            await message.answer(
                format_entry_confirmation(entry, nomi) + "\n\nBu g'ayrioddiy katta summa. Tasdiqlaysizmi?",
                reply_markup=_large_amount_keyboard(),
            )
            return

        await state.set_state(EntryStates.confirm_summary)
        await message.answer(format_entry_confirmation(entry, nomi), reply_markup=_summary_keyboard())

    @router.message(EntryStates.waiting_field)
    async def on_field_answer(message: Message, state: FSMContext, cfg, sheets, aliases_registry, audit):
        value = _parse_number(message.text)
        if value is None:
            await message.answer("Noto'g'ri qiymat. Iltimos raqam yuboring.")
            return

        data = await state.get_data()
        field_index = data["field_index"]
        field_key, _ = FIELD_QUESTIONS[field_index]
        answers = data["answers"]
        answers[field_key] = value
        field_index += 1
        await state.update_data(answers=answers, field_index=field_index)

        if field_index < len(FIELD_QUESTIONS):
            _, question = FIELD_QUESTIONS[field_index]
            await message.answer(question)
            return

        await _show_summary(message, state, cfg, sheets, aliases_registry, audit)

    @router.callback_query(F.data == "skip_today", EntryStates.waiting_field)
    async def on_skip_today(callback: CallbackQuery, state: FSMContext, cfg, sheets, aliases_registry, audit):
        await state.update_data(answers={key: 0 for key, _ in FIELD_QUESTIONS}, field_index=len(FIELD_QUESTIONS))
        await callback.answer()
        await _show_summary(callback.message, state, cfg, sheets, aliases_registry, audit)

    async def _persist_and_continue(message: Message, state: FSMContext, cfg, sheets, aliases_registry, audit, actor_id):
        data = await state.get_data()
        entry = _entry_from_dict(data["pending_entry"])
        kontragent_id = entry.kontragent_id
        sana = entry.sana
        flow = data.get("flow", "auto")

        history = sheets.read_entries(kontragent_id)
        was_correction = any(e.sana == sana for e in history)
        chain = apply_entry(history, entry)
        sheets.update_entries([e for e in chain if e.sana >= sana])

        audit.log_action(actor_id, "tuzatish" if was_correction else "kiritish", {
            "kontragent_id": kontragent_id, "sana": sana.isoformat(),
        })

        nomi = aliases_registry.rasmiy_nom(kontragent_id)
        await message.answer(format_entry_confirmation(entry, nomi))

        if was_correction and sana < date.today():
            actor_nomi = f"telegram_id={actor_id}"
            alert = format_alert_past_day_corrected(nomi, sana, actor_nomi)
            for admin_id in [aid for aid in cfg.allowed_telegram_ids if aid != actor_id]:
                await message.bot.send_message(admin_id, alert)

        if flow == "single":
            await state.clear()
            await message.answer("Saqlandi.", reply_markup=_main_menu_keyboard())
        else:
            await _start_next_kontragent(message, state, sheets, aliases_registry, sana)

    @router.callback_query(F.data == "confirm_entry", EntryStates.confirm_summary)
    async def on_confirm_entry(callback: CallbackQuery, state: FSMContext, cfg, sheets, aliases_registry, audit):
        await callback.answer()
        await _persist_and_continue(callback.message, state, cfg, sheets, aliases_registry, audit, callback.from_user.id)

    @router.callback_query(F.data == "confirm_large", EntryStates.confirm_large_amount)
    async def on_confirm_large(callback: CallbackQuery, state: FSMContext, cfg, sheets, aliases_registry, audit):
        await callback.answer()
        await _persist_and_continue(callback.message, state, cfg, sheets, aliases_registry, audit, callback.from_user.id)

    @router.callback_query(F.data == "cancel_large", EntryStates.confirm_large_amount)
    async def on_cancel_large(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.set_state(EntryStates.waiting_field)
        await state.update_data(answers={}, field_index=0)
        await callback.message.answer(FIELD_QUESTIONS[0][1], reply_markup=_cancel_keyboard())

    @router.callback_query(F.data == "edit_entry", EntryStates.confirm_summary)
    async def on_edit_entry(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.set_state(EntryStates.waiting_field)
        await state.update_data(answers={}, field_index=0)
        await callback.message.answer(FIELD_QUESTIONS[0][1], reply_markup=_cancel_keyboard())

    # -------------------------------------------------------------
    # Qarzdorlar ro'yxati (qo'lda chaqirish) - professional Excel hisobot
    # sifatida, chat xabaridagi kabi 10 tagacha qisqartirilmagan.
    # -------------------------------------------------------------
    async def _do_qarzdorlar(message: Message, cfg, sheets, aliases_registry):
        entries_by_kontragent = sheets.read_all_entries()
        debtors = top_debtors(entries_by_kontragent, aliases_registry, top_n=None)
        daily_rows = daily_payments_summary(entries_by_kontragent)
        detail_rows = daily_payments_detail(entries_by_kontragent, aliases_registry)
        monthly_rows = monthly_summary(entries_by_kontragent, commission_rate=cfg.commission_rate)
        if not debtors and not daily_rows:
            await message.answer("Hali hech qanday ma'lumot yo'q.", reply_markup=_main_menu_keyboard())
            return

        sana = date.today()
        path = f"/tmp/qarzdorlar_{sana.isoformat()}.xlsx"
        try:
            build_debtors_report(debtors, daily_rows, detail_rows, monthly_rows, path, sana=sana)
            jami_qarz = sum(qarz for _, qarz, _, _ in debtors)
            await message.answer_document(
                FSInputFile(path, filename=f"qarzdorlar_{sana.isoformat()}.xlsx"),
                caption=f"Qarzdorlar: {len(debtors)} ta, jami ${jami_qarz:,.2f}",
                reply_markup=_main_menu_keyboard(),
            )
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    @router.message(Command("qarzdorlar"))
    async def cmd_qarzdorlar(message: Message, cfg, sheets, aliases_registry):
        await _do_qarzdorlar(message, cfg, sheets, aliases_registry)

    @router.message(F.text == MENU_DEBTORS)
    async def on_menu_debtors(message: Message, cfg, sheets, aliases_registry):
        await _do_qarzdorlar(message, cfg, sheets, aliases_registry)

    # -------------------------------------------------------------
    # Kurs: joriy kursni ko'rsatish va yangisini kiritish
    # -------------------------------------------------------------
    @router.message(F.text == MENU_KURS)
    async def on_menu_kurs(message: Message, state: FSMContext, sheets):
        sana = date.today()
        joriy = sheets.get_kurs(sana)
        await state.set_state(KursStates.updating)
        await state.update_data(kurs_sana=sana.isoformat())
        if joriy is not None:
            await message.answer(f"Joriy kurs ({sana.isoformat()}): {joriy}\nYangi qiymatni yuboring.")
        else:
            await message.answer(f"{sana.isoformat()} uchun kursni kiriting.")

    @router.message(KursStates.updating)
    async def on_kurs_update_answer(message: Message, state: FSMContext, sheets):
        kurs = _parse_number(message.text)
        if kurs is None or kurs <= 0:
            await message.answer("Noto'g'ri qiymat. Kursni raqam bilan yuboring.")
            return
        data = await state.get_data()
        sana = date.fromisoformat(data["kurs_sana"])
        sheets.set_kurs(sana, kurs)
        await state.clear()
        await message.answer(f"Kurs yangilandi: {kurs}", reply_markup=_main_menu_keyboard())

    # -------------------------------------------------------------
    # Tahrirlash: kontragent + sanani tanlab, mavjud yozuvni tuzatish
    # -------------------------------------------------------------
    @router.message(F.text == MENU_EDIT)
    async def on_menu_edit(message: Message, state: FSMContext):
        await state.set_state(EditStates.waiting_kontragent)
        await message.answer("Qaysi kontragentni tahrirlaysiz? Nomini yozing.")

    @router.message(EditStates.waiting_kontragent)
    async def on_edit_kontragent(message: Message, state: FSMContext, aliases_registry):
        kontragent_id = aliases_registry.resolve(message.text)
        if kontragent_id is None:
            await message.answer("Kontragent topilmadi. Rasmiy nomni aniqroq yozing.")
            return
        await state.update_data(edit_kontragent_id=kontragent_id)
        await state.set_state(EditStates.waiting_date)
        await message.answer("Qaysi sanani tahrirlaysiz? (KK.OO.YYYY, masalan 15.08.2026)")

    @router.message(EditStates.waiting_date)
    async def on_edit_date(message: Message, state: FSMContext, sheets, aliases_registry):
        sana = parse_manual_date(message.text)
        if sana is None:
            await message.answer("Sana tushunilmadi. Format: KK.OO.YYYY (masalan 15.08.2026)")
            return

        data = await state.get_data()
        kontragent_id = data["edit_kontragent_id"]
        nomi = aliases_registry.rasmiy_nom(kontragent_id)

        history = sheets.read_entries(kontragent_id)
        existing = next((e for e in history if e.sana == sana), None)
        if existing is not None:
            await message.answer(
                format_entry_confirmation(existing, nomi) + "\n\nHozirgi holat shu. Yangi qiymatlarni kiriting."
            )
        else:
            await message.answer(f"{nomi} uchun {sana.isoformat()} kunida hali yozuv yo'q - yangi kiritiladi.")

        await state.update_data(flow="single")
        kurs = await _ensure_kurs(message, state, sheets, sana)
        if kurs is None:
            return
        await _start_single_entry(message, state, sheets, aliases_registry, kontragent_id, sana)

    # -------------------------------------------------------------
    # Fayl yuklash (Click / hisobot / "Абдуллох" formatidagi fayllar)
    # -------------------------------------------------------------
    @router.message(F.text == MENU_UPLOAD)
    async def on_menu_upload(message: Message):
        await message.answer("Click yoki hisobot faylini (.xlsx) shu yerga yuboring.")

    def _detect_file_kind(filename):
        lowered = filename.lower()
        if lowered.startswith("click"):
            return "click"
        if lowered.startswith("hisobot"):
            return "hisobot"
        return "report"

    def _merge_upload_values(a, b):
        """Bitta faylda ikki xil nom (alias) bitta kontragent_id'ga mos
        kelib qolsa (masalan ikkala yozilishi ham bir kishiga bog'langan
        bo'lsa), ikkinchisi birinchisini USTIDAN YOZIB YUBORMASLIGI kerak -
        aks holda bitta summa jimgina yo'qolib qoladi. Shuning uchun
        to'qnashuvda qiymatlar bir-biriga QO'SHILADI (dict bo'lsa - har bir
        maydon alohida, skalyar bo'lsa - to'g'ridan-to'g'ri)."""
        if isinstance(a, dict):
            return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}
        return a + b

    @router.message(F.document)
    async def on_document(message: Message, state: FSMContext, bot: Bot, cfg, sheets, aliases_registry, audit):
        document: Document = message.document
        kind = _detect_file_kind(document.file_name or "")

        if kind == "report":
            # parse_report_file "kun_varag_nomi -> qiymat" ko'rinishida
            # qaytaradi (bitta kontragentning oylik fayli, 31 kunlik varaq) -
            # bu umumiy fayl-yuklash oqimi kutgan "kontragent_nomi -> qiymat"
            # shaklidan butunlay farq qiladi (fayl QAYSI kontragentga
            # tegishli ekani ham bu yerda aniqlanmaydi). Shu nomuvofiqlik
            # tufayli avval bu yo'l xatosiz, lekin NOTO'G'RI ishlar edi -
            # kun raqamlarini kontragent nomi sifatida hal qilishga urinib,
            # hech narsani mos kelmasdan "o'zgarish topilmadi" deb noto'g'ri
            # xabar berardi. Bu format uchun alohida oqim hali yozilmagan -
            # shuning uchun jim noto'g'ri ishlash o'rniga ochiq xabar beriladi.
            await message.answer(
                "Bu fayl 'Абдуллох' formatidagi (har kontragent uchun alohida "
                "oylik fayl) ko'rinadi - bu format uchun avtomatik yuklash hali "
                "ulanmagan (qaysi kontragentga tegishli ekani aniqlanmaydi). "
                "Iltimos loyiha egasiga murojaat qiling."
            )
            return

        tmp_path = f"/tmp/{document.file_id}_{document.file_name}"
        file = await bot.get_file(document.file_id)
        await bot.download_file(file.file_path, destination=tmp_path)

        try:
            try:
                if kind == "click":
                    # DIQQAT: Click fayldagi kurs Sheets'ga AVTOMATIK
                    # yozilmaydi - loyiha egasi kursni doim o'zi qo'lda
                    # kiritadi (bot.py 6-bo'lim: kurs kuniga bir marta
                    # so'raladi). Fayldagi kurs faqat solishtirish uchun
                    # ko'rsatiladi (pastda).
                    raw, kurs_faylda = parse_click_file(tmp_path)
                else:
                    raw = parse_hisobot_file(tmp_path)
            except ValueError as exc:
                await message.answer(f"Faylni o'qib bo'lmadi: {exc}")
                return
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        sana = date.today()
        kurs_bugun = sheets.get_kurs(sana)
        if kurs_bugun is None:
            # Kurs kuniga bir marta so'raladi va shu kunning BARCHA
            # yozuvlariga qo'llanadi (6-bo'lim) - agar bu yerda kurssiz
            # davom etilsa, fayldan yaratilgan yozuvlar kurs=None bilan
            # doimiy saqlanib qoladi va dollar ekvivalenti keyinchalik ham
            # to'g'rilanmaydi (Kurslar varag'iga keyinroq kurs kiritilsa
            # ham, allaqachon yozilgan qatorlar o'zgarmaydi).
            await message.answer(
                "Bu kun uchun hali kurs kiritilmagan - avval /kirim (yoki "
                "\"Qo'lda kiritish\") orqali bugungi kursni kiriting, so'ngra "
                "faylni qayta yuboring."
            )
            return

        if kind == "click" and kurs_faylda and kurs_faylda != kurs_bugun:
            await message.answer(
                f"Diqqat: fayldagi kurs ({kurs_faylda}) siz kiritgan kursdan "
                f"({kurs_bugun}) farq qiladi. Hisob-kitob siz kiritgan kurs "
                f"({kurs_bugun}) bo'yicha olib boriladi."
            )

        resolved, tekshirish_kerak = aliases_registry.resolve_many(raw.keys())
        by_id = {}
        for name in resolved:
            kontragent_id = aliases_registry.resolve(name)
            if kind == "click" and aliases_registry.is_click_fayldan_ozod(kontragent_id):
                # Bu kontragentning click summasi hisobot faylidan olinadi -
                # Click faylidagi qiymati ikki marta hisoblanib ketmasligi
                # uchun e'tiborsiz qoldiriladi.
                continue
            value = raw[name]
            by_id[kontragent_id] = (
                _merge_upload_values(by_id[kontragent_id], value)
                if kontragent_id in by_id
                else value
            )

        # Solishtirish - avvalgi Telegram sessiyasidagi keshdan emas, balki
        # Sheets'da bugun uchun HAQIQATDA saqlangan qiymatdan (bot qayta
        # ishga tushsa ham to'g'ri ishlaydi, sessiyaga bog'liq emas).
        today_entries = {
            kid: entry
            for kid, entries in sheets.read_all_entries().items()
            for entry in entries if entry.sana == sana
        }
        if kind == "click":
            previous = {kid: (today_entries[kid].click if kid in today_entries else 0) for kid in by_id}
        else:
            previous = {
                kid: (
                    {
                        "naqd_som": today_entries[kid].naqd_som, "click": today_entries[kid].click,
                        "naqd_dollar": today_entries[kid].naqd_dollar, "terminal": today_entries[kid].terminal,
                    }
                    if kid in today_entries
                    else {"naqd_som": 0, "click": 0, "naqd_dollar": 0, "terminal": 0}
                )
                for kid in by_id
            }

        diff = diff_parsed_data(previous, by_id)
        if not has_changes(diff):
            await message.answer("Fayl qayta tahlil qilindi - o'zgarish topilmadi.")
        else:
            # FAQAT o'zgargan/yangi kontragentlar tasdiqdan keyin yoziladi -
            # o'zgarmagan qolganlari tegilmaydi ("bitta kontragentda
            # o'zgarish bo'lganda, faqat o'sha bitta qator aniqlanadi, qolgan
            # hammasi tegilmaydi" - 6-bo'lim).
            changed_ids = set(diff["ozgargan"]) | set(diff["yangi"])
            pending_by_id = {kid: by_id[kid] for kid in changed_ids}
            await state.set_state(ReuploadStates.waiting_confirmation)
            await state.update_data(pending_upload={"kind": kind, "kontragent_ids": pending_by_id})
            names_by_id = {kid: aliases_registry.rasmiy_nom(kid) for kid in by_id}
            lines = format_upload_diff(diff, names_by_id, kind, kurs_bugun, title="O'zgarishlar aniqlandi:")
            await message.answer("\n".join(lines), reply_markup=_reupload_keyboard())

        if tekshirish_kerak:
            await message.answer(
                "Qo'lda tekshiring - mos kelmagan nomlar:\n" + "\n".join(tekshirish_kerak)
            )

    @router.callback_query(F.data == "reupload_confirm", ReuploadStates.waiting_confirmation)
    async def on_reupload_confirm(callback: CallbackQuery, state: FSMContext, sheets, aliases_registry, audit):
        data = await state.get_data()
        pending = data["pending_upload"]
        sana = date.today()

        # Butun jadval BIR MARTA o'qiladi (har bir kontragent uchun alohida
        # emas) va yozish uchun barcha yozuvlar bitta ro'yxatga yig'ilib,
        # OXIRIDA bitta guruhli chaqiruv bilan saqlanadi - fayl yuklashda
        # bir nechta kontragent o'zgargan bo'lsa, bu o'nlab ketma-ket
        # Sheets chaqiruvi o'rniga atigi 2-3 tasini qoladi (sekinlikning
        # asosiy sababi shu edi).
        all_entries = sheets.read_all_entries()
        kurs_bugun = sheets.get_kurs(sana)
        to_write = []

        for kontragent_id, value in pending["kontragent_ids"].items():
            history = all_entries.get(kontragent_id, [])
            existing = next((e for e in history if e.sana == sana), None)
            kwargs = dict(existing.__dict__) if existing else {}
            if pending["kind"] == "click":
                kwargs["click"] = value
            elif pending["kind"] in ("hisobot", "report"):
                kwargs.update(value)
            entry = DailyEntry(
                sana=sana, kontragent_id=kontragent_id,
                naqd_som=kwargs.get("naqd_som", 0), click=kwargs.get("click", 0),
                naqd_dollar=kwargs.get("naqd_dollar", 0), terminal=kwargs.get("terminal", 0),
                chegirma_som=kwargs.get("chegirma_som", 0), kurs=kurs_bugun,
                qarz_boshida_som=existing.qarz_boshida_som if existing else 0,
                qarz_boshida_dollar=existing.qarz_boshida_dollar if existing else 0,
            )
            chain = apply_entry(history, entry)
            to_write.extend(e for e in chain if e.sana >= sana)

        sheets.update_entries(to_write)

        await state.set_state(None)
        audit.log_action(callback.from_user.id, "fayl_tasdiqlash", {"kind": pending["kind"]})
        await callback.answer()
        await callback.message.answer("Saqlandi.", reply_markup=_main_menu_keyboard())

    @router.callback_query(F.data == "reupload_cancel", ReuploadStates.waiting_confirmation)
    async def on_reupload_cancel(callback: CallbackQuery, state: FSMContext):
        await state.set_state(None)
        await callback.answer()
        await callback.message.answer("Bekor qilindi - hech narsa yozilmadi.", reply_markup=_main_menu_keyboard())

    return router


def _entry_to_dict(entry):
    return {
        "sana": entry.sana.isoformat(), "kontragent_id": entry.kontragent_id,
        "naqd_som": entry.naqd_som, "click": entry.click, "naqd_dollar": entry.naqd_dollar,
        "terminal": entry.terminal, "chegirma_som": entry.chegirma_som, "kurs": entry.kurs,
        "qarz_boshida_som": entry.qarz_boshida_som, "qarz_boshida_dollar": entry.qarz_boshida_dollar,
    }


def _entry_from_dict(d):
    return DailyEntry(
        sana=date.fromisoformat(d["sana"]), kontragent_id=d["kontragent_id"],
        naqd_som=d["naqd_som"], click=d["click"], naqd_dollar=d["naqd_dollar"],
        terminal=d["terminal"], chegirma_som=d["chegirma_som"], kurs=d["kurs"],
        qarz_boshida_som=d["qarz_boshida_som"], qarz_boshida_dollar=d["qarz_boshida_dollar"],
    ).compute()


# ---------------------------------------------------------------------
# Rejalashtirilgan bildirishnomalar (8-bo'lim)
# ---------------------------------------------------------------------
async def send_morning_digest(bot: Bot, cfg: Config, sheets: SheetsClient, aliases_registry: AliasRegistry):
    entries_by_kontragent = sheets.read_all_entries()
    debtors = top_debtors(entries_by_kontragent, aliases_registry, top_n=None)
    daily_rows = daily_payments_summary(entries_by_kontragent)
    detail_rows = daily_payments_detail(entries_by_kontragent, aliases_registry)
    monthly_rows = monthly_summary(entries_by_kontragent, commission_rate=cfg.commission_rate)
    today = date.today()

    alerts = []
    for kontragent_id, entries in entries_by_kontragent.items():
        nomi = aliases_registry.rasmiy_nom(kontragent_id)
        gone_days = days_since_last_payment(entries, today)
        if gone_days is not None and gone_days >= cfg.no_payment_alert_days:
            alerts.append(format_alert_no_payment(nomi, gone_days))
        if entries:
            latest = sorted(entries, key=lambda e: e.sana)[-1]
            if latest.qolgan_qarz_dollar > cfg.debt_alert_threshold_usd:
                alerts.append(format_alert_debt_threshold(nomi, latest.qolgan_qarz_dollar, cfg.debt_alert_threshold_usd))

    if debtors or daily_rows:
        path = f"/tmp/qarzdorlar_{today.isoformat()}.xlsx"
        try:
            build_debtors_report(debtors, daily_rows, detail_rows, monthly_rows, path, sana=today)
            jami_qarz = sum(qarz for _, qarz, _, _ in debtors)
            caption = f"Ertalabki qarzdorlar hisoboti: {len(debtors)} ta, jami ${jami_qarz:,.2f}"
            for admin_id in cfg.allowed_telegram_ids:
                await bot.send_document(admin_id, FSInputFile(path, filename=f"qarzdorlar_{today.isoformat()}.xlsx"), caption=caption)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
    else:
        for admin_id in cfg.allowed_telegram_ids:
            await bot.send_message(admin_id, "Bugun qarzdorlar ro'yxati bo'sh.")

    for admin_id in cfg.allowed_telegram_ids:
        for alert in alerts:
            await bot.send_message(admin_id, alert)


async def send_month_end_summary(bot: Bot, cfg: Config, sheets: SheetsClient):
    today = date.today()
    last_day_prev_month = today.replace(day=1) - timedelta(days=1)
    entries_by_kontragent = sheets.read_all_entries()
    month_entries = [
        e for entries in entries_by_kontragent.values() for e in entries
        if e.sana.year == last_day_prev_month.year and e.sana.month == last_day_prev_month.month
    ]
    if not month_entries:
        return

    jami_usd = total_received_usd_equivalent(month_entries)
    komissiya = monthly_commission(month_entries, rate=cfg.commission_rate)
    jami_chegirma = sum(e.chegirma_som for e in month_entries)
    oy_nomi = OY_NOMLARI_UZ[last_day_prev_month.month - 1]
    text = format_month_end_summary(oy_nomi, jami_usd, komissiya, jami_chegirma)

    for admin_id in cfg.allowed_telegram_ids:
        await bot.send_message(admin_id, text)


def _is_last_day_of_month(d):
    return d.day == calendar.monthrange(d.year, d.month)[1]


async def main():
    cfg = load_config()
    bot = Bot(token=cfg.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    sheets = SheetsClient.from_service_account(cfg.google_sheets_id, cfg.google_service_account_json)
    audit = AuditLog(path=cfg.audit_log_path)
    try:
        aliases_registry = AliasRegistry.load_json(cfg.aliases_json_path)
    except FileNotFoundError:
        logger.warning("Alias fayli topilmadi (%s) - bo'sh registr bilan boshlanmoqda.", cfg.aliases_json_path)
        aliases_registry = AliasRegistry()

    dp["cfg"] = cfg
    dp["sheets"] = sheets
    dp["aliases_registry"] = aliases_registry
    dp["audit"] = audit

    router = build_router()
    dp.include_router(router)
    router.message.middleware(AccessMiddleware(cfg))
    router.callback_query.middleware(AccessMiddleware(cfg))
    router.message.middleware(KursGateMiddleware(sheets))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_morning_digest, "cron", hour=cfg.morning_digest_hour, minute=0,
        args=[bot, cfg, sheets, aliases_registry],
    )
    scheduler.add_job(
        send_month_end_summary, "cron", hour=0, minute=5,
        args=[bot, cfg, sheets],
    )
    scheduler.start()

    await bot.set_my_commands([
        BotCommand(command="kirim", description="Bugungi to'lovlarni kiritish"),
        BotCommand(command="kechiktirilgan", description="O'tgan kunga yozuv kiritish"),
        BotCommand(command="qarzdorlar", description="Joriy qarzdorlar ro'yxati"),
        BotCommand(command="start", description="Botni boshlash"),
    ])

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
