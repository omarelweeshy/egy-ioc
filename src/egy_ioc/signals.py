"""Behaviour signals that aren't indicators but matter for triage.

- ``otp_request``: the message asks the reader to send or tell a code, OTP or password. Built for
  precision: a request verb and a code word on the same line, close together, and not negated.
  Banks' own "don't share this code" messages are skipped. Paraphrases are missed.
- ``mixed_script``: a word mixes Latin letters with Cyrillic or Greek lookalikes ("Instаpay" with
  a Cyrillic "а"), a common way to slip past keyword filters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from egy_ioc.keywords import compile_alternation, find_words
from egy_ioc.normalize import fold

_CODE_WORDS = compile_alternation(
    fold(w)
    for w in (
        "كود",
        "الكود",
        "رمز التحقق",
        "رمز التفعيل",
        "الرمز",
        "رقم سري",
        "الرقم السري",
        "باسورد",
        "الباسورد",
        "كلمة السر",
        "كلمة المرور",
        "otp",
        "code",
        "verification code",
        "activation code",
        "password",
        "pin code",
    )
)
# Imperatives only. Arabic verbs take Egyptian suffixes (ابعتلي, ابعتهولي, قوليلي). The noun
# "ارسال" is left out because legit messages say "سيتم ارسال رمز التحقق" (a code will be sent),
# and English needs an object, so "we will send you a code" doesn't fire.
_VERBS = re.compile(
    r"(?:ابعت|ارسل|اكتب|قول)[^\W\d_]*|ادي(?:ني|لي|نا)|هات(?:ي|وا)?"
    r"|(?:send|tell|give|forward)\s+(?:me|us)|(?:send|share)\s+(?:the|your|it|this)"
)
_NEGATIONS = frozenset({"لا", "مش", "ممنوع", "متشاركش", "don't", "dont", "not", "never", "no"})
_MAX_GAP = 30
_MIXED = re.compile(r"[A-Za-z\u0370-\u03ff\u0400-\u04ff]+")


@dataclass(frozen=True, slots=True)
class SignalMatch:
    name: str
    start: int
    end: int
    detail: str


def _negated(folded: str, verb_start: int) -> bool:
    """Only the word right before the verb counts: "لا خلاص، ابعتلي الكود" ("no wait, send me
    the code") is still a request."""
    line_start = folded.rfind("\n", 0, verb_start) + 1
    before = folded[line_start:verb_start].split()[-1:]
    return any(w.strip(".,!?،؟") in _NEGATIONS for w in before)


def find_otp_requests(folded: str) -> list[SignalMatch]:
    out: list[SignalMatch] = []
    verbs = list(find_words(folded, _VERBS))
    codes = list(find_words(folded, _CODE_WORDS))
    for v in verbs:
        if _negated(folded, v.start()):
            continue
        for c in codes:
            lo, hi = min(v.start(), c.start()), max(v.end(), c.end())
            gap = max(c.start() - v.end(), v.start() - c.end())
            if gap <= _MAX_GAP and "\n" not in folded[lo:hi]:
                out.append(SignalMatch("otp_request", lo, hi, f"{v.group(0)} / {c.group(0)}"))
                break
    return out


def find_mixed_script(text: str) -> list[SignalMatch]:
    out: list[SignalMatch] = []
    for m in _MIXED.finditer(text):
        word = m.group(0)
        latin = any("a" <= c.lower() <= "z" for c in word)
        other = any("\u0370" <= c <= "\u04ff" for c in word)
        if latin and other:
            out.append(SignalMatch("mixed_script", m.start(), m.end(), word))
    return out
