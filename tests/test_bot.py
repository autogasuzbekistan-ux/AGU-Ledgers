import bot


def test_parse_number_handles_none_without_crashing():
    # Telegram matn bo'lmagan xabar (rasm/sticker/ovozli xabar) yuborsa,
    # message.text None bo'ladi - _parse_number buni qulamasdan
    # qayta ishlashi kerak.
    assert bot._parse_number(None) is None


def test_parse_number_handles_valid_and_invalid_text():
    assert bot._parse_number("1 000,5") == 1000.5
    assert bot._parse_number("abc") is None


def test_parse_number_handles_plain_and_negative():
    assert bot._parse_number("41850") == 41850
    assert bot._parse_number("-41850") == -41850
    assert bot._parse_number("  ") is None


def test_parse_number_handles_european_format_dot_thousands_comma_decimal():
    assert bot._parse_number("41.850,00") == 41850.0
    assert bot._parse_number("-41.850,50") == -41850.50
    assert bot._parse_number("1.245,5") == 1245.5


def test_parse_number_handles_us_format_comma_thousands_dot_decimal():
    assert bot._parse_number("41,850.00") == 41850.0
    assert bot._parse_number("1,245.5") == 1245.5


def test_parse_number_handles_plain_decimal_point():
    assert bot._parse_number("41850.00") == 41850.0
    assert bot._parse_number("1245.5") == 1245.5


def test_build_router_constructs_without_error():
    router = bot.build_router()
    assert len(router.message.handlers) > 0
    assert len(router.callback_query.handlers) > 0
