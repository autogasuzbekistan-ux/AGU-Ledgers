import bot


def test_parse_number_handles_none_without_crashing():
    # Telegram matn bo'lmagan xabar (rasm/sticker/ovozli xabar) yuborsa,
    # message.text None bo'ladi - _parse_number buni qulamasdan
    # qayta ishlashi kerak.
    assert bot._parse_number(None) is None


def test_parse_number_handles_valid_and_invalid_text():
    assert bot._parse_number("1 000,5") == 1000.5
    assert bot._parse_number("abc") is None


def test_build_router_constructs_without_error():
    router = bot.build_router()
    assert len(router.message.handlers) > 0
    assert len(router.callback_query.handlers) > 0
