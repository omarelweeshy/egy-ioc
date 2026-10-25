import pytest

from egy_ioc import extract
from egy_ioc.phones import egyptian_e164, find_phones


@pytest.mark.parametrize(
    ("text", "e164"),
    [
        ("01000000001", "+201000000001"),
        ("0100 000 0001", "+201000000001"),
        ("0100-000-0001", "+201000000001"),
        ("0100.000.0001", "+201000000001"),
        ("+201000000001", "+201000000001"),
        ("+20 100 000 0001", "+201000000001"),
        ("+20 (0)100 000 0001", "+201000000001"),
        ("+2001000000001", "+201000000001"),
        ("00201000000001", "+201000000001"),
        ("201000000001", "+201000000001"),
        ("٠١٠٠٠٠٠٠٠٠١", "+201000000001"),
        ("٠١٠٠ ٠٠٠ ٠٠٠١", "+201000000001"),
    ],
)
def test_egyptian_mobile_formats(text: str, e164: str) -> None:
    phones = [i for i in extract(f"كلمني على {text} شكرا") if i.type == "phone"]
    assert [p.value for p in phones] == [e164]
    assert phones[0].raw == text


@pytest.mark.parametrize(
    ("number", "operator"),
    [
        ("01000000001", "vodafone"),
        ("01100000001", "etisalat"),
        ("01200000001", "orange"),
        ("01500000001", "we"),
    ],
)
def test_operator_from_prefix(number: str, operator: str) -> None:
    (p,) = [i for i in extract(number) if i.type == "phone"]
    assert p.attrs["operator"] == operator


@pytest.mark.parametrize(
    "text",
    [
        "01300000001",  # 013 isn't a mobile prefix
        "0100000000",  # 10 digits
        "010000000012",  # 12 digits
        "رقم الطلب 1234567",
        "ID01000000001",  # digits glued to Latin letters (an order or account ID)
    ],
)
def test_not_phone_numbers(text: str) -> None:
    assert [i for i in extract(text) if i.type == "phone"] == []


def test_number_touching_arabic_letters() -> None:
    (p,) = [i for i in extract("على رقم01000000005 بسرعة") if i.type == "phone"]
    assert p.value == "+201000000005"
    assert p.raw == "01000000005"


def test_two_numbers_separated_by_a_space_stay_two() -> None:
    values = [i.value for i in extract("01000000001 01100000002") if i.type == "phone"]
    assert values == ["+201000000001", "+201100000002"]


def test_international_number() -> None:
    (p,) = [i for i in extract("كلم المالك +44 7700 900123") if i.type == "phone"]
    assert p.value == "+447700900123"
    assert p.attrs == {"country": "intl"}


def test_find_phones_does_not_double_count_egyptian_as_international() -> None:
    assert len(find_phones("+201000000001")) == 1


def test_egyptian_e164() -> None:
    assert egyptian_e164("01000000001") == "+201000000001"
    assert egyptian_e164("201500000001") == "+201500000001"
    assert egyptian_e164("01400000001") is None
