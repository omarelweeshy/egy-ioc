"""Replace personal identifiers in a message with placeholders, for datasets and reports.

Without a key, each distinct value gets a numbered placeholder ([PHONE_1], [PHONE_2], ...) that
is only stable within one message. With a key, placeholders carry a keyed hash ([PHONE:3f9a...])
that is stable across messages, so campaigns can still be linked after redaction.

Why a key: Egypt has about 400 million possible mobile numbers (4 prefixes x 10^8). A plain
SHA-256 of a number is reversed by hashing all of them, which takes minutes on a laptop. An HMAC
can't be reversed without the key, so keep the key secret and out of the repository.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Collection

from egy_ioc.extract import extract
from egy_ioc.model import IndicatorType

DEFAULT_TYPES: frozenset[IndicatorType] = frozenset(
    {"phone", "wallet", "email", "instapay_handle", "instapay_link"}
)
_LABELS: dict[str, str] = {
    "phone": "PHONE",
    "wallet": "PHONE",
    "email": "EMAIL",
    "instapay_handle": "INSTAPAY",
    "instapay_link": "INSTAPAY_LINK",
    "url": "URL",
    "domain": "DOMAIN",
    "messaging_link": "LINK",
}


def keyed_id(value: str, key: bytes, length: int = 12) -> str:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()[:length]


def redact(
    text: str,
    types: Collection[IndicatorType] = DEFAULT_TYPES,
    key: bytes | None = None,
) -> str:
    chosen = sorted(
        (i for i in extract(text) if i.type in types and i.type in _LABELS),
        key=lambda i: (i.start, -(i.end - i.start)),
    )
    spans: list[tuple[int, int, str, str]] = []  # start, end, label, value
    for i in chosen:
        if spans and i.start < spans[-1][1]:
            continue  # inside an earlier span (a wallet repeats its phone's span)
        spans.append((i.start, i.end, _LABELS[i.type], i.value))
    numbers: dict[tuple[str, str], int] = {}
    out: list[str] = []
    pos = 0
    for start, end, label, value in spans:
        if key is not None:
            placeholder = f"[{label}:{keyed_id(value, key)}]"
        else:
            n = numbers.setdefault((label, value), sum(1 for k in numbers if k[0] == label) + 1)
            placeholder = f"[{label}_{n}]"
        out.append(text[pos:start])
        out.append(placeholder)
        pos = end
    out.append(text[pos:])
    return "".join(out)
