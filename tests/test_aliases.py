import pytest

from aliases import AliasRegistry


def _sample_registry():
    reg = AliasRegistry()
    reg.add_kontragent("rashid", "Rashid aka")
    reg.add_kontragent("alisher", "Alisher aka")
    reg.add_alias("Alisher aka agu", "alisher")
    reg.add_alias("Alisher aka do'kon", "alisher")
    return reg


def test_resolve_matches_official_name_and_aliases():
    reg = _sample_registry()

    assert reg.resolve("Rashid aka") == "rashid"
    assert reg.resolve("Alisher aka agu") == "alisher"
    assert reg.resolve("Alisher aka do'kon") == "alisher"


def test_resolve_is_case_and_whitespace_insensitive_but_not_fuzzy():
    reg = _sample_registry()

    assert reg.resolve("  ALISHER AKA AGU  ") == "alisher"
    assert reg.resolve("Alisher  aka   agu") == "alisher"
    # deyarli o'xshash, lekin aniq mos kelmaydi (na rasmiy nom, na alias) -
    # taxmin qilinmaydi
    assert reg.resolve("Alisher") is None
    assert reg.resolve("Alisher aka dokoni") is None


def test_resolve_none_input_returns_none_without_crashing():
    reg = _sample_registry()
    # matn bo'lmagan Telegram xabari (rasm/sticker) uchun message.text None bo'ladi
    assert reg.resolve(None) is None


def test_resolve_many_splits_matched_and_needs_review():
    reg = _sample_registry()

    resolved, tekshirish_kerak = reg.resolve_many(
        ["Rashid aka", "Alisher aka agu", "Nomalum kontragent"]
    )

    assert resolved == {"Rashid aka": "rashid", "Alisher aka agu": "alisher"}
    assert tekshirish_kerak == ["Nomalum kontragent"]


def test_add_alias_conflict_raises():
    reg = _sample_registry()
    with pytest.raises(ValueError):
        reg.add_alias("Alisher aka agu", "rashid")


def test_add_kontragent_duplicate_id_raises():
    reg = _sample_registry()
    with pytest.raises(ValueError):
        reg.add_kontragent("rashid", "Boshqa nom")


def test_add_alias_unknown_kontragent_raises():
    reg = AliasRegistry()
    with pytest.raises(ValueError):
        reg.add_alias("Rashid aka", "rashid")


def test_json_roundtrip(tmp_path):
    reg = _sample_registry()
    path = tmp_path / "aliases.json"
    reg.save_json(path)

    loaded = AliasRegistry.load_json(path)

    assert loaded.resolve("Alisher aka do'kon") == "alisher"
    assert loaded.rasmiy_nom("rashid") == "Rashid aka"
    assert sorted(loaded.kontragentlar()) == sorted(reg.kontragentlar())
