import pytest

from egy_ioc import extract
from egy_ioc.brands import BRANDS
from egy_ioc.domains import has_valid_tld


def _brands(text: str) -> list[str]:
    return [i.value for i in extract(text) if i.type == "brand"]


@pytest.mark.parametrize(
    ("text", "brand"),
    [
        ("تم إيقاف حسابك على إنستاباي", "instapay"),
        ("حسابك على انستاباى", "instapay"),
        ("InstaPay account locked", "instapay"),
        ("حول بفودافون كاش", "vodafone"),
        ("ڤودافون بتقولك", "vodafone"),
        ("من البنك الأهلي المصري", "nbe"),
        ("والبنك الاهلي بيبلغك", "nbe"),
        ("ادفع من أي ماكينة فوري", "fawry"),
        ("منحة تكافل وكرامة", "takaful_karama"),
        ("منحـــة تَكافُل وكَرامة", "takaful_karama"),
        ("رسالة من مصر الرقمية", "digital_egypt"),
        ("Your CIB card", "cib"),
    ],
)
def test_brand_mentions(text: str, brand: str) -> None:
    assert _brands(text) == [brand]


@pytest.mark.parametrize(
    "text",
    [
        "الأهلي كسب الماتش",  # Al Ahly the football club, not the bank
        "تحويل فوري للفلوس",  # "instant", not Fawry
        "عندي اتصالات كتير النهارده",  # "calls", not Etisalat
        "I like orange juice",
        "ascii cibola",  # "cib" inside a word
    ],
)
def test_ambiguous_words_are_not_brands(text: str) -> None:
    assert _brands(text) == []


def test_brand_inside_a_link_is_left_to_the_link() -> None:
    assert _brands("https://instapay-verify.test") == []


def test_wallet_provider_from_nearest_keyword() -> None:
    text = "حسابك على إنستاباي اتقفل، ادفع على فودافون كاش ٠١٠٠ ٠٠٠ ٠٠٠١"
    (w,) = [i for i in extract(text) if i.type == "wallet"]
    assert (w.value, w.attrs["provider"]) == ("+201000000001", "vodafone_cash")


def test_wallet_keyword_after_the_number() -> None:
    (w,) = [i for i in extract("01200000003 اورنج كاش") if i.type == "wallet"]
    assert w.attrs["provider"] == "orange_cash"


def test_phone_without_wallet_keyword_is_not_a_wallet() -> None:
    assert [i for i in extract("كلمني على 01000000001") if i.type == "wallet"] == []


def test_far_keyword_is_ignored() -> None:
    text = "فودافون كاش " + "كلام " * 20 + "01000000001"
    assert [i for i in extract(text) if i.type == "wallet"] == []


def test_brand_data_is_consistent() -> None:
    ids = [b.id for b in BRANDS]
    assert len(ids) == len(set(ids))
    for b in BRANDS:
        assert b.aliases, b.id
        for d in b.official:
            assert d == d.lower(), d
            assert has_valid_tld(d), d
        if b.tokens or b.short_tokens:
            assert b.official, f"{b.id}: lookalike tokens need a confirmed official domain"
