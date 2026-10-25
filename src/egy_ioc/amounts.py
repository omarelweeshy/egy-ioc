"""Money amounts in Egyptian pounds, written with digits.

Runs on the folded text, so "جنيه" and "جنية" are one form and "EGP" is lowercase. Amounts written
in words ("خمسمية جنيه") are not found.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

_NUM = r"(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<frac>\d{1,2}))?"
_MULT = r"(?:\s?(?P<mult>الف|الاف|مليون|k)(?![^\W\d_]))?"
_CUR = r"(?P<cur>جنيه(?:ا|ات)?|ج\s?\.\s?م\.?|جم|ج|egp|l\.e\.?|le|pounds?)(?![^\W\d_])"
_AFTER = re.compile(rf"(?<![0-9A-Za-z.,]){_NUM}{_MULT}\s?{_CUR}")
_BEFORE = re.compile(
    rf"(?<![0-9A-Za-z])(?P<cur>egp|l\.e\.?|le|ج\.م)\s?{_NUM}{_MULT}(?![0-9A-Za-z])"
)
_MULTIPLIERS = {"الف": 1000, "الاف": 1000, "k": 1000, "مليون": 1_000_000}


@dataclass(frozen=True, slots=True)
class AmountMatch:
    start: int
    end: int
    value: str  # decimal string in EGP, e.g. "5000" or "6.50"


def _value(m: re.Match[str]) -> str:
    amount = Decimal(m.group("num").replace(",", ""))
    if m.group("frac"):
        amount += Decimal(m.group("frac")) / Decimal(10 ** len(m.group("frac")))
    if m.group("mult"):
        amount *= _MULTIPLIERS[m.group("mult")]
    return str(int(amount)) if amount == amount.to_integral_value() else f"{amount:.2f}"


def find_amounts(folded: str) -> list[AmountMatch]:
    out: list[AmountMatch] = []
    for pattern in (_AFTER, _BEFORE):
        for m in pattern.finditer(folded):
            if not any(m.start() < a.end and a.start < m.end() for a in out):
                out.append(AmountMatch(m.start(), m.end(), _value(m)))
    return sorted(out, key=lambda a: a.start)
