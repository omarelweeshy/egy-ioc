import pytest

from egy_ioc import extract


def _values(text: str, kind: str) -> list[str]:
    return [i.value for i in extract(text) if i.type == kind]


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("ادفع ٦ جنيه", "6"),
        ("ادفع 6 جنية", "6"),
        ("رسوم 350ج فقط", "350"),
        ("رسوم 350 ج.م", "350"),
        ("10,000 جنيه عربون", "10000"),
        ("5 آلاف جنيه", "5000"),
        ("2 مليون جنيها", "2000000"),
        ("EGP 1,500", "1500"),
        ("pay 99.50 EGP", "99.50"),
        ("1500 LE", "1500"),
        ("١٬٥٠٠ جنيهات", "1500"),
    ],
)
def test_amounts(text: str, value: str) -> None:
    assert _values(text, "amount") == [value]


@pytest.mark.parametrize("text", ["عندي 3 جوابات", "الطلب رقم 500", "سنة 2026"])
def test_not_amounts(text: str) -> None:
    assert _values(text, "amount") == []


@pytest.mark.parametrize(
    "text",
    [
        "ابعتلي الكود اللي جالك",
        "ممكن تبعت ... لا خلاص، ابعتلي رمز التحقق بسرعة",
        "قوليلي الكود اللي وصلك على الموبايل",
        "اديني الكود يا باشا",
        "can you send me the code please",
        "share your OTP to unlock",
    ],
)
def test_otp_requests(text: str) -> None:
    assert _values(text, "signal") == ["otp_request"]


@pytest.mark.parametrize(
    "text",
    [
        "رمز التحقق الخاص بك هو 482913. لا تشارك هذا الرمز مع أي شخص.",
        "سيتم ارسال رمز التحقق إلى هاتفك",
        "Do not share this code with anyone.",
        "We will send you a verification code.",
        "هنبعتلك الكود في رسالة",
        "لا ابعت الكود لأي حد",
        "ابعتلي العنوان\nوالكود هيوصلك",  # verb and code word on different lines
    ],
)
def test_not_otp_requests(text: str) -> None:
    assert _values(text, "signal") == []


def test_mixed_script_word() -> None:
    found = [i for i in extract("حسابك على Instаpay موقوف") if i.type == "signal"]
    assert [(i.value, i.raw) for i in found] == [("mixed_script", "Instаpay")]
