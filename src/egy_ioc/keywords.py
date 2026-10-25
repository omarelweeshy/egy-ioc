"""Keyword matching on folded text with Arabic-aware word boundaries.

Arabic attaches short words to the next one: "بفودافون كاش" is "with Vodafone Cash", "والبنك" is
"and the bank". A plain word boundary misses those, so a match may also start right after a
proclitic (و ب ف ل ك, ال, لل and their combinations) that itself starts a word.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

_PROCLITICS = (
    "و",
    "ب",
    "ف",
    "ل",
    "ك",
    "وب",
    "ول",
    "فب",
    "ال",
    "بال",
    "وال",
    "فال",
    "كال",
    "لل",
    "ولل",
)


def _is_word_char(c: str) -> bool:
    return c.isalnum()


def _arabic_start(s: str) -> bool:
    return bool(s) and "\u0600" <= s[0] <= "\u06ff"


def left_ok(text: str, start: int, word: str) -> bool:
    if start == 0 or not _is_word_char(text[start - 1]):
        return True
    if not _arabic_start(word):
        return False
    for p in _PROCLITICS:
        k = start - len(p)
        if k >= 0 and text[k:start] == p and (k == 0 or not _is_word_char(text[k - 1])):
            return True
    return False


def right_ok(text: str, end: int) -> bool:
    return end == len(text) or not _is_word_char(text[end])


def compile_alternation(words: Iterable[str]) -> re.Pattern[str]:
    """One pattern for many words, longest first; a space in a word matches any whitespace."""
    parts = sorted(set(words), key=len, reverse=True)
    return re.compile("|".join(re.escape(w).replace(r"\ ", r"\s+") for w in parts))


def find_words(text: str, pattern: re.Pattern[str]) -> Iterator[re.Match[str]]:
    """Matches of `pattern` that start and end on word boundaries (proclitics allowed)."""
    pos = 0
    while True:
        m = pattern.search(text, pos)
        if m is None:
            return
        if left_ok(text, m.start(), m.group(0)) and right_ok(text, m.end()):
            yield m
            pos = m.end()
        else:
            pos = m.start() + 1
