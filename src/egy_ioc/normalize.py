"""Normalization for Egyptian Arabic, Franco-Arab and English message text.

One pass builds two views of the input. Both are index-aligned with each other, and every
character keeps the position it came from, so any match maps back to exact offsets in the
original string (the evidence).

- ``text``: Unicode NFKC per character (Arabic presentation forms become ordinary letters),
  Arabic-Indic and Persian digits become ASCII, and invisible characters are removed: tatweel,
  harakat, zero-width and direction marks. Values are read from this view, so a URL or a handle
  keeps its letters and case as written.
- ``folded``: ``text`` lowercased, with Arabic letter variants folded (أ إ آ to ا, ى to ي, ة to ه,
  ڤ to ف, ...) and Cyrillic or Greek lookalikes mapped to Latin. Keywords and brands are matched
  here, so "إنستاباي", "انستاباى" and "انستـــاباي" all match one alias.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

_DIGITS: dict[str, str] = {
    **{chr(0x0660 + i): str(i) for i in range(10)},  # Arabic-Indic ٠-٩
    **{chr(0x06F0 + i): str(i) for i in range(10)},  # Persian ۰-۹
    "\u066b": ".",  # Arabic decimal separator
    "\u066c": ",",  # Arabic thousands separator
}

_FOLD = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ئ": "ي",
        "ی": "ي",  # Persian yeh
        "ة": "ه",
        "ھ": "ه",
        "ہ": "ه",
        "ؤ": "و",
        "ک": "ك",  # Persian keheh
        "ڤ": "ف",  # Egyptian "v", as in ڤودافون
        "گ": "ج",  # hard g
        "پ": "ب",
        # Cyrillic and Greek letters that look like Latin ones (after lowercasing)
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "у": "y",
        "х": "x",
        "і": "i",
        "ј": "j",
        "ѕ": "s",
        "ԁ": "d",
        "һ": "h",
        "ӏ": "l",
        "α": "a",
        "ο": "o",
        "ρ": "p",
        "ι": "i",
        "κ": "k",
        "ν": "v",
    }
)


def _is_dropped(c: str) -> bool:
    """Characters that change how text looks to a filter but not to a reader."""
    o = ord(c)
    return (
        o == 0x0640  # tatweel
        or 0x064B <= o <= 0x065F  # harakat
        or o == 0x0670  # superscript alef
        or 0x0610 <= o <= 0x061A  # Quranic annotation marks
        or 0x06D6 <= o <= 0x06ED
        or 0x200B <= o <= 0x200F  # zero-width space/joiners, LRM, RLM
        or 0x202A <= o <= 0x202E  # bidi embeddings and overrides
        or 0x2060 <= o <= 0x2069  # word joiner, bidi isolates
        or o in (0x061C, 0xFEFF, 0x00AD)  # Arabic letter mark, BOM, soft hyphen
    )


@dataclass(frozen=True, slots=True)
class Normalized:
    source: str
    text: str
    folded: str
    index: tuple[int, ...]  # index[i] is the position in `source` that text[i] came from

    def span(self, start: int, end: int) -> tuple[int, int]:
        """Map a [start, end) span of `text` / `folded` back to `source`."""
        if not 0 <= start < end <= len(self.text):
            raise ValueError(f"bad span {start}:{end} for text of length {len(self.text)}")
        return self.index[start], self.index[end - 1] + 1


def normalize(source: str) -> Normalized:
    text: list[str] = []
    folded: list[str] = []
    index: list[int] = []
    for i, ch in enumerate(source):
        if _is_dropped(ch):
            continue
        mapped = _DIGITS.get(ch)
        if mapped is None:
            mapped = unicodedata.normalize("NFKC", ch)
        for c in mapped:
            if _is_dropped(c):
                continue
            if unicodedata.category(c) == "Zs":
                c = " "
            c = _DIGITS.get(c, c)
            lower = c.lower()
            text.append(c)
            folded.append((lower if len(lower) == 1 else c).translate(_FOLD))
            index.append(i)
    return Normalized(source, "".join(text), "".join(folded), tuple(index))


def fold(text: str) -> str:
    """The folded view of a string on its own (used for aliases and keywords)."""
    return normalize(text).folded
