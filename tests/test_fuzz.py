"""Random mixed-script input: extraction must never crash, and evidence must stay exact."""

import random

from egy_ioc import extract, redact

_PIECES = (
    "٠١٠٠",
    "٠٠٠",
    "0100",
    "+20",
    "011",
    " ",
    "-",
    ".",
    "\n",
    "ـ",
    "\u200f",
    "\u200b",
    "َ",
    "فودافون كاش",
    "إنستاباي",
    "البنك الأهلي",
    "جنيه",
    "آلاف",
    "ابعتلي",
    "الكود",
    "https://",
    "hxxps://",
    "[.]",
    "www.",
    "bit.ly/",
    "wa.me/2010",
    "@instapay",
    "@",
    "cib",
    "eg",
    "test",
    "xn--",
    "ﻻ",
    "ﺍﻧﺴﺘﺎﺑﺎﻱ",
    "а",
    "Ｆ",
    "İ",
    "/",
    "?",
    "=",
    "%2B",
    "(",
    ")",
    "،",
    "؟",
    "مصر",
    "apk",
    "EGP",
    "5",
    "7",
    "9",
    "00",
    "a",
    "z",
)


def test_random_messages() -> None:
    rng = random.Random(20261025)  # noqa: S311 - seeded test data, not security
    for _ in range(3000):
        text = "".join(rng.choice(_PIECES) for _ in range(rng.randint(0, 25)))
        for i in extract(text):
            assert text[i.start : i.end] == i.raw, (text, i)
        redact(text)
