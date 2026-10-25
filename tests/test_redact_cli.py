import json
from pathlib import Path

import pytest

from egy_ioc import keyed_id, redact
from egy_ioc.cli import defang, main


def test_redact_numbers_values_consistently() -> None:
    text = "كلم 01000000001 او 0100 000 0001 او 01100000002"
    assert redact(text) == "كلم [PHONE_1] او [PHONE_1] او [PHONE_2]"


def test_redact_with_key_is_stable_across_messages() -> None:
    key = b"test-key"
    a = redact("رقم 01000000001", key=key)
    b = redact("الرقم +20 100 000 0001 تاني", key=key)
    tag = keyed_id("+201000000001", key)
    assert f"[PHONE:{tag}]" in a
    assert f"[PHONE:{tag}]" in b
    assert "01000000001" not in a


def test_redact_keeps_link_but_hides_its_number() -> None:
    assert redact("wa.me/201100000002") == "wa.me/[PHONE_1]"


def test_redact_email_and_handle() -> None:
    out = redact("راسل a@cibeg-help.test او حول omar.test@instapay")
    assert out == "راسل [EMAIL_1] او حول [INSTAPAY_1]"


def test_keyed_id_differs_by_key() -> None:
    assert keyed_id("+201000000001", b"a") != keyed_id("+201000000001", b"b")


def test_defang() -> None:
    assert defang("https://evil.test/a") == "hxxps://evil[.]test/a"
    assert defang("x@evil.test") == "x[@]evil[.]test"
    assert defang("hxxps://evil[.]test/a") == "hxxps://evil[.]test/a"  # not defanged twice


def test_cli_extract_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "m.txt"
    p.write_text("ادفع على فودافون كاش 01000000001 من https://x-pay.test", encoding="utf-8")
    assert main(["extract", str(p), "--types", "wallet,url", "--defang"]) == 0
    items = json.loads(capsys.readouterr().out)
    assert [i["type"] for i in items] == ["wallet", "url"]
    assert items[1]["value"] == "hxxps://x-pay[.]test"


def test_cli_extract_lines_unique(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "m.txt"
    p.write_text("01000000001 و 01000000001\n\nbit.ly/a\n", encoding="utf-8")
    assert main(["extract", str(p), "--lines", "--unique"]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [r["line"] for r in rows] == [1, 3]
    assert rows[0]["indicators"][0]["count"] == 2


def test_cli_redact_with_key_env(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "m.txt"
    p.write_text("رقم 01000000001", encoding="utf-8")
    monkeypatch.setenv("EGY_IOC_TEST_KEY", "k")
    assert main(["redact", str(p), "--key-env", "EGY_IOC_TEST_KEY"]) == 0
    assert capsys.readouterr().out.strip() == f"رقم [PHONE:{keyed_id('+201000000001', b'k')}]"


def test_cli_rejects_unknown_type(tmp_path: Path) -> None:
    p = tmp_path / "m.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["extract", str(p), "--types", "nope"])
