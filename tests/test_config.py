import pytest

from config import Config


def _valid_env(**overrides):
    env = {
        "BOT_TOKEN": "123:abc",
        "GOOGLE_SHEETS_ID": "sheet123",
        "GOOGLE_SERVICE_ACCOUNT_JSON": "service_account.json",
        "ALLOWED_TELEGRAM_ID": "111111",
    }
    env.update(overrides)
    return env


def test_config_loads_all_fields_from_env():
    cfg = Config(env=_valid_env())

    assert cfg.bot_token == "123:abc"
    assert cfg.google_sheets_id == "sheet123"
    assert cfg.google_service_account_json == "service_account.json"
    assert cfg.allowed_telegram_ids == {111111}


def test_config_supports_multiple_allowed_ids():
    cfg = Config(env=_valid_env(ALLOWED_TELEGRAM_ID="111, 222 ,333"))

    assert cfg.allowed_telegram_ids == {111, 222, 333}
    assert cfg.is_allowed(222) is True
    assert cfg.is_allowed(999) is False


def test_config_raises_on_missing_required_vars():
    env = _valid_env()
    del env["BOT_TOKEN"]

    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        Config(env=env)
