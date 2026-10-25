"""Phone numbers: Egyptian mobiles in any common format, and other international numbers.

Patterns run on the normalized text, where Arabic-Indic digits are already ASCII. A number may
be split by single spaces, dots or dashes ("0100 000 0001", "+20 10-0000-0001"), and may touch
Arabic letters ("رقمي01000000001"), which sloppy messages often do.

The operator comes from the prefix the number was issued with. Egypt has mobile number
portability, so the current operator can differ.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SEP = r"[ .-]?"
_EG_MOBILE = re.compile(
    r"(?<![0-9A-Za-z+])"
    r"(?:"
    rf"(?:\+|00)[ ]?20{_SEP}(?:\(0\){_SEP}|0{_SEP})?"  # +20 / 0020, optional trunk 0
    r"|20(?=1[0125]\d{8}(?!\d))"  # bare 20 only when written as one 12-digit run
    r"|0"  # national trunk prefix
    r")"
    rf"1{_SEP}[0125](?:{_SEP}\d){{8}}"
    r"(?![0-9A-Za-z])"
)
_INTL = re.compile(r"(?<![0-9A-Za-z+])(?:\+|00)(?!20)[1-9](?:[ .-]?\d){7,13}(?![0-9A-Za-z])")

OPERATORS = {"0": "vodafone", "1": "etisalat", "2": "orange", "5": "we"}


@dataclass(frozen=True, slots=True)
class PhoneMatch:
    start: int
    end: int
    e164: str
    country: str  # "EG" or "intl" (the country of other numbers isn't resolved)
    operator: str | None


def operator_of(e164: str) -> str:
    """Issuing operator of an Egyptian mobile in E.164 form (+20 1X ...)."""
    return OPERATORS[e164[4]]


def egyptian_e164(digits: str) -> str | None:
    """+201XXXXXXXXX for any digit-only form of an Egyptian mobile number, else None."""
    m = re.fullmatch(r"(?:0020|20)?0?(1[0125]\d{8})", digits)
    return f"+20{m.group(1)}" if m else None


def find_phones(text: str) -> list[PhoneMatch]:
    out: list[PhoneMatch] = []
    for m in _EG_MOBILE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        e164 = egyptian_e164(digits)
        if e164 is not None:
            out.append(PhoneMatch(m.start(), m.end(), e164, "EG", operator_of(e164)))
    for m in _INTL.finditer(text):
        if any(m.start() < p.end and p.start < m.end() for p in out):
            continue
        digits = re.sub(r"\D", "", m.group(0))
        if digits.startswith("00"):
            digits = digits[2:]
        if 8 <= len(digits) <= 15:
            out.append(PhoneMatch(m.start(), m.end(), "+" + digits, "intl", None))
    return sorted(out, key=lambda p: p.start)
