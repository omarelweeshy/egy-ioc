import pytest

from egy_ioc import Indicator, analyze_host, extract


def _one(text: str, kind: str) -> Indicator:
    found = [i for i in extract(text) if i.type == kind]
    assert len(found) == 1, found
    return found[0]


def test_url_stops_at_arabic_text() -> None:
    u = _one("اضغط هنا https://instapay-verify.test/loginبسرعة", "url")
    assert u.value == "https://instapay-verify.test/login"


def test_url_touching_arabic_on_the_left() -> None:
    u = _one("الرابطhttps://x-pay.test/a", "url")
    assert u.raw == "https://x-pay.test/a"


def test_trailing_punctuation_is_not_part_of_the_url() -> None:
    assert _one("ادخل (https://x-pay.test/a).", "url").value == "https://x-pay.test/a"
    assert _one("ادخل https://x-pay.test/a، بسرعة", "url").value == "https://x-pay.test/a"


def test_defanged_url_is_refanged_in_value_and_flagged() -> None:
    u = _one("hxxps://instapay-verify[.]test/login", "url")
    assert u.value == "https://instapay-verify.test/login"
    assert u.raw == "hxxps://instapay-verify[.]test/login"
    assert u.attrs["defanged"] == "true"


def test_bare_domain_and_bare_url() -> None:
    assert _one("زور cib-egypt.test حالا", "domain").value == "cib-egypt.test"
    u = _one("من bit.ly/3xYz", "url")
    assert u.value == "bit.ly/3xYz"
    assert u.attrs["shortener"] == "true"


def test_file_names_are_not_domains() -> None:
    assert [i for i in extract("شغل script.py و notes.md") if i.type == "domain"] == []


def test_word_with_invalid_tld_is_not_a_domain() -> None:
    assert [i for i in extract("hello.notatld") if i.type == "domain"] == []


def test_official_domain_is_marked_and_not_a_lookalike() -> None:
    d = _one("الموقع الرسمي www.cibeg.com", "domain")
    assert d.attrs["official_brand"] == "cib"
    assert "lookalike_brand" not in d.attrs


@pytest.mark.parametrize(
    ("host", "brand", "reason"),
    [
        ("instapay-verify.test", "instapay", "contains_brand"),
        ("ipn.eg.verify-account.test", "instapay", "official_domain_in_name"),
        ("cibeg.com-secure.test", "cib", "official_domain_in_name"),
        ("1nstapay.test", "instapay", "homoglyph"),
        ("instapey-eg.test", "instapay", "typo"),
        ("vodafome-cash.test", "vodafone", "typo"),
        ("nbe-online.test", "nbe", "brand_label"),
        ("orange-cash-eg.test", "orange", "contains_brand"),
        ("evil-fawry.vercel.app", "fawry", "contains_brand"),
    ],
)
def test_lookalikes(host: str, brand: str, reason: str) -> None:
    info = analyze_host(host)
    assert info is not None
    assert (info.lookalike, info.reason) == (brand, reason)


@pytest.mark.parametrize(
    "host", ["orange-recipes.test", "cibeg.com", "www.banquemisr.com", "ipn.eg", "example.test"]
)
def test_not_lookalikes(host: str) -> None:
    info = analyze_host(host)
    assert info is not None
    assert info.lookalike is None


def test_punycode_homoglyph() -> None:
    # "cіbeg" with a Cyrillic і, written as Unicode in the message
    u = _one("Verify at https://cіbeg-secure.test now", "url")
    assert u.attrs["host"].startswith("xn--")
    assert u.attrs["punycode"] == "true"
    assert u.attrs["lookalike_brand"] == "cib"
    assert u.attrs["lookalike_reason"] == "homoglyph"


def test_free_hosting_site() -> None:
    u = _one("https://digital-egypt-pay.vercel.app/fine", "url")
    assert u.attrs["free_hosting"] == "true"
    assert u.attrs["site"] == "digital-egypt-pay.vercel.app"
    assert u.attrs["lookalike_brand"] == "digital_egypt"


def test_userinfo_trick() -> None:
    u = _one("https://instapay.eg@ipn-update.test/login", "url")
    assert u.attrs["host"] == "ipn-update.test"
    assert u.attrs["userinfo_in_url"] == "true"
    assert u.attrs["lookalike_brand"] == "instapay"


def test_arabic_domain_under_misr_tld() -> None:
    u = _one("زوروا https://بنك-مزيف.مصر/دخول", "url")
    assert u.attrs["host"].endswith(".xn--wgbh1c")


def test_risky_download_in_url() -> None:
    assert _one("نزل https://x-pay.test/app.apk", "url").attrs["file_ext"] == "apk"


def test_whatsapp_link_with_egyptian_number() -> None:
    found = extract("كلمنا wa.me/201100000002")
    link = next(i for i in found if i.type == "messaging_link")
    phone = next(i for i in found if i.type == "phone")
    assert link.attrs["platform"] == "whatsapp"
    assert phone.value == "+201100000002"
    assert phone.attrs["in_link"] == "true"
    assert link.start <= phone.start < phone.end <= link.end


def test_whatsapp_api_link_and_telegram() -> None:
    found = extract("https://api.whatsapp.com/send?phone=201000000001 و t.me/fake_support_eg")
    assert [i.type for i in found if i.type != "phone"] == ["messaging_link", "messaging_link"]
    assert any(i.type == "phone" and i.value == "+201000000001" for i in found)


def test_instapay_link_and_handle() -> None:
    assert (
        _one("ادفع هنا https://ipn.eg/S/omar.test/instapay/2Dc", "instapay_link").attrs[
            "official_brand"
        ]
        == "instapay"
    )
    h = _one("حول على Omar.Test@InstaPay لو سمحت", "instapay_handle")
    assert h.value == "omar.test@instapay"


def test_email_gets_domain_analysis() -> None:
    e = _one("راسلنا support@cibeg-help.test", "email")
    assert e.value == "support@cibeg-help.test"
    assert e.attrs["lookalike_brand"] == "cib"


def test_email_local_part_is_not_a_domain() -> None:
    found = extract("mail omar.shop@example.test")
    assert [i.type for i in found] == ["email"]


def test_digits_in_urls_are_not_phones() -> None:
    found = extract("https://x-pay.test/?ref=01000000001")
    assert [i.type for i in found] == ["url"]
