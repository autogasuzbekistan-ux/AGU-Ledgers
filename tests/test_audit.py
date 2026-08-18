import json

from audit import AuditLog


def test_log_action_appends_json_lines(tmp_path):
    path = tmp_path / "audit.log"
    log = AuditLog(path=str(path))

    log.log_action(123456, "kiritish", {"kontragent": "rashid", "sana": "2026-08-01"})
    log.log_action(123456, "tuzatish", {"kontragent": "rashid", "sana": "2026-08-01"})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["kim"] == 123456
    assert first["amal"] == "kiritish"
    assert first["tafsilot"]["kontragent"] == "rashid"
    assert "vaqt" in first
