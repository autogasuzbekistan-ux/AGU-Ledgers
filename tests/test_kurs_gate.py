import asyncio
from datetime import date

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

import bot


class _FakeEvent:
    def __init__(self):
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class _FakeSheets:
    def __init__(self, kurs=None):
        self._kurs = kurs

    def get_kurs(self, sana):
        return self._kurs


def _fsm_context():
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=1, user_id=1)
    return FSMContext(storage=storage, key=key)


def _run(coro):
    return asyncio.run(coro)


def test_kurs_gate_blocks_when_no_kurs_and_asks_for_it():
    async def scenario():
        handler_called = []

        async def handler(event, data):
            handler_called.append(True)

        middleware = bot.KursGateMiddleware(_FakeSheets(kurs=None))
        event = _FakeEvent()
        state = _fsm_context()

        await middleware(handler, event, {"state": state})

        assert handler_called == []
        assert event.answers and "kurs" in event.answers[0].lower()
        assert await state.get_state() == bot.EntryStates.waiting_kurs.state
        data = await state.get_data()
        assert data["kurs_sana"] == date.today().isoformat()
        assert data["flow"] == "auto"

    _run(scenario())


def test_kurs_gate_passes_through_when_kurs_already_set():
    async def scenario():
        handler_called = []

        async def handler(event, data):
            handler_called.append(True)

        middleware = bot.KursGateMiddleware(_FakeSheets(kurs=12800))
        event = _FakeEvent()
        state = _fsm_context()

        await middleware(handler, event, {"state": state})

        assert handler_called == [True]
        assert event.answers == []

    _run(scenario())


def test_kurs_gate_lets_the_kurs_answer_itself_through():
    async def scenario():
        handler_called = []

        async def handler(event, data):
            handler_called.append(True)

        middleware = bot.KursGateMiddleware(_FakeSheets(kurs=None))
        event = _FakeEvent()
        state = _fsm_context()
        await state.set_state(bot.EntryStates.waiting_kurs)

        await middleware(handler, event, {"state": state})

        # kurs hali None bo'lsa ham, bu holat aynan "kursga javob"
        # bo'lgani uchun handler'ga o'tkaziladi (aks holda cheksiz tsikl).
        assert handler_called == [True]
        assert event.answers == []

    _run(scenario())
