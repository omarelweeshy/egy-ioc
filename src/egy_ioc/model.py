"""The result type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

IndicatorType = Literal[
    "url",
    "domain",
    "email",
    "messaging_link",
    "instapay_link",
    "instapay_handle",
    "phone",
    "wallet",
    "amount",
    "file",
    "brand",
    "signal",
]
INDICATOR_TYPES: tuple[IndicatorType, ...] = (
    "url",
    "domain",
    "email",
    "messaging_link",
    "instapay_link",
    "instapay_handle",
    "phone",
    "wallet",
    "amount",
    "file",
    "brand",
    "signal",
)


@dataclass(frozen=True, slots=True)
class Indicator:
    """One finding. `raw` is exactly `text[start:end]` of the input, so it's the evidence."""

    type: IndicatorType
    value: str  # canonical form: E.164 phone, lowercase host, brand id, signal name, ...
    raw: str
    start: int
    end: int
    attrs: dict[str, str] = field(default_factory=dict[str, str])

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "value": self.value,
            "raw": self.raw,
            "start": self.start,
            "end": self.end,
            "attrs": dict(self.attrs),
        }
