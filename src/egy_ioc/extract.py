"""Find every indicator in one message.

Passes run in a fixed order and later passes skip spans that earlier ones claimed: links first
(so digits inside a URL aren't read as a phone number), then emails, InstaPay handles, phone
numbers, amounts and file names. Brand mentions skip links and handles too. Wallets and signals
are added on top and may overlap other indicators.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from functools import cache

from egy_ioc.amounts import find_amounts
from egy_ioc.brands import BRANDS_BY_ID, folded_aliases, folded_wallet_keywords
from egy_ioc.domains import MESSAGING_HOSTS, analyze_host
from egy_ioc.keywords import compile_alternation, find_words
from egy_ioc.model import Indicator, IndicatorType
from egy_ioc.normalize import Normalized, normalize
from egy_ioc.phones import PhoneMatch, egyptian_e164, find_phones, operator_of
from egy_ioc.signals import find_mixed_script, find_otp_requests

_ARABIC = "\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff"
_URL_CHAR = rf"[^\s<>\"'`{_ARABIC}]"
_DOT = r"(?:\.|\[\.\]|\(\.\)|\{\.\}|\[dot\]|\(dot\))"
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_TLD = r"(?:[a-z]{2,24}|xn--[a-z0-9-]{2,59})"
_AR_LABEL = r"[\u0621-\u064a0-9-]+"

_ARABIC_URL = re.compile(
    rf"(?<![\u0621-\u064a0-9.-])(?:https?://)?(?:{_AR_LABEL}\.)+مصر(?![\u0621-\u064a])"
    rf"(?:/{_URL_CHAR}*)?",
    re.I,
)
_SCHEME_URL = re.compile(rf"(?<![A-Za-z0-9])h(?:tt|xx)ps?(?:://|\[://\]|\[:\]//){_URL_CHAR}+", re.I)
_WWW_URL = re.compile(rf"(?<![A-Za-z0-9@./-])www{_DOT}{_URL_CHAR}+", re.I)
# Not followed by "@": "first.last@x.com" and "fake.shop@instapay" are an email and a handle.
_BARE = re.compile(
    rf"(?<![A-Za-z0-9@./_-])(?:{_LABEL}{_DOT})+{_TLD}(?![A-Za-z0-9@-]|{_DOT}[A-Za-z0-9])"
    rf"(?:[/?]{_URL_CHAR}*)?",
    re.I,
)
_EMAIL = re.compile(
    rf"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+(?:@|\[@\]|\[at\]|\(at\))"
    rf"(?:{_LABEL}{_DOT})+{_TLD}(?![A-Za-z0-9-])",
    re.I,
)
_HANDLE = re.compile(
    r"(?<![A-Za-z0-9._@-])[A-Za-z0-9][A-Za-z0-9._-]{1,63}@instapay(?![A-Za-z0-9]|\.[A-Za-z0-9])",
    re.I,
)
_FILE = re.compile(
    r"(?<![A-Za-z0-9_./-])[A-Za-z0-9_\-\u0621-\u064a.]{1,80}\.(?:apk|xapk|apks|exe|scr|msi|jar)"
    r"(?![A-Za-z0-9])",
    re.I,
)
_WA_PHONE = re.compile(r"(?:wa\.me/|[?&]phone=)(?:%2[bB]|\+)?(\d{8,15})")
_RISKY_EXT = re.compile(r"\.(apk|xapk|apks|exe|scr|msi|jar)(?:$|[?#])", re.I)

_DEFANG_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bhxxp(s?)", re.I), r"http\1"),
    (re.compile(r"\[\s*(?:\.|dot)\s*\]|\(\s*(?:\.|dot)\s*\)|\{\s*(?:\.|dot)\s*\}", re.I), "."),
    (re.compile(r"\[://\]"), "://"),
    (re.compile(r"\[:\]"), ":"),
    (re.compile(r"\[\s*(?:@|at)\s*\]|\(\s*(?:@|at)\s*\)", re.I), "@"),
)
_TRAILING = ".,;:!?)]}>'\"*"
_DEFANG_MARK = re.compile(r"\[\.\]|\(\.\)|\{\.\}|\[dot\]|\(dot\)|hxxp|\[:\]|\[://\]|\[@\]", re.I)
_FILE_LIKE_TLDS = frozenset({"py", "sh", "md", "rs", "pl", "ps", "js", "go", "cs", "zip", "mov"})
_ORDER: dict[str, int] = {"url": 0, "messaging_link": 0, "instapay_link": 0, "domain": 0}


def refang(text: str) -> str:
    for pattern, repl in _DEFANG_RULES:
        text = pattern.sub(repl, text)
    return text


@cache
def _brand_pattern() -> re.Pattern[str]:
    return compile_alternation(a for a, _ in folded_aliases())


@cache
def _brand_lookup() -> dict[str, str]:
    return {re.sub(r"\s+", " ", a): b for a, b in folded_aliases()}


@cache
def _wallet_pattern() -> re.Pattern[str]:
    return compile_alternation(k for k, _ in folded_wallet_keywords())


@cache
def _wallet_lookup() -> dict[str, str]:
    return {re.sub(r"\s+", " ", k): p for k, p in folded_wallet_keywords()}


class _Builder:
    def __init__(self, n: Normalized) -> None:
        self.n = n
        self.found: list[Indicator] = []
        self.taken: list[tuple[int, int]] = []

    def free(self, start: int, end: int) -> bool:
        return not any(start < e and s < end for s, e in self.taken)

    def add(
        self,
        kind: IndicatorType,
        value: str,
        start: int,
        end: int,
        attrs: dict[str, str] | None = None,
        claim: bool = True,
    ) -> None:
        s, e = self.n.span(start, end)
        self.found.append(Indicator(kind, value, self.n.source[s:e], s, e, attrs or {}))
        if claim:
            self.taken.append((start, end))


def _strip_trailing(text: str, start: int, end: int) -> int:
    while end > start and text[end - 1] in _TRAILING:
        if text[end - 1] in ")]}" and _DEFANG_MARK.search(text[max(start, end - 6) : end]):
            break
        end -= 1
    return end


def _split_url(url: str) -> tuple[str, str, str, bool]:
    """(scheme with '://' or '', host, rest, has_userinfo) of a refanged URL."""
    scheme = ""
    m = re.match(r"([a-z]+://)", url, re.I)
    if m:
        scheme = m.group(1).lower()
        url = url[m.end() :]
    cut = re.search(r"[/?#]", url)
    authority, rest = (url[: cut.start()], url[cut.start() :]) if cut else (url, "")
    userinfo = "@" in authority
    host = authority.rsplit("@", 1)[-1]
    host = re.sub(r":\d*$", "", host)
    return scheme, host, rest, userinfo


def _links(b: _Builder) -> None:
    text = b.n.text
    for pattern in (_ARABIC_URL, _SCHEME_URL, _WWW_URL, _BARE):
        for m in pattern.finditer(text):
            start = m.start()
            end = _strip_trailing(text, start, m.end())
            if end <= start or not b.free(start, end):
                continue
            raw = text[start:end]
            url = refang(raw)
            scheme, host, rest, userinfo = _split_url(url)
            info = analyze_host(host)
            if info is None:
                continue
            tld = info.host.rsplit(".", 1)[-1]
            defanged = url != raw
            if pattern is _BARE and not rest and tld in _FILE_LIKE_TLDS and not defanged:
                continue
            attrs = info.attrs()
            if defanged:
                attrs["defanged"] = "true"
            if userinfo:
                attrs["userinfo_in_url"] = (
                    "true"  # https://instapay.eg@evil.test/ goes to evil.test
                )
            ext = _RISKY_EXT.search(rest)
            if ext:
                attrs["file_ext"] = ext.group(1).lower()
            authority_end = len(scheme) + url[len(scheme) :].find(host) + len(host)
            value = (scheme + url[len(scheme) : authority_end]).lower() + url[authority_end:]
            platform = MESSAGING_HOSTS.get(info.host)
            if platform is not None:
                attrs["platform"] = platform
                b.add("messaging_link", value, start, end, attrs)
                _messaging_phone(b, start, raw)
            elif info.host == "ipn.eg":
                b.add("instapay_link", value, start, end, attrs)
            elif scheme or rest:
                b.add("url", value, start, end, attrs)
            else:
                b.add("domain", info.host, start, end, attrs)


def _messaging_phone(b: _Builder, url_start: int, raw: str) -> None:
    m = _WA_PHONE.search(raw)
    if m is None:
        return
    digits = m.group(1)
    e164 = egyptian_e164(digits)
    start, end = url_start + m.start(1), url_start + m.end(1)
    if e164 is not None:
        attrs = {"country": "EG", "operator": operator_of(e164), "in_link": "true"}
        b.add("phone", e164, start, end, attrs, claim=False)
    else:
        b.add("phone", "+" + digits, start, end, {"country": "intl", "in_link": "true"}, False)


def _emails_and_handles(b: _Builder) -> None:
    text = b.n.text
    for m in _EMAIL.finditer(text):
        if not b.free(m.start(), m.end()):
            continue
        value = refang(m.group(0)).lower()
        info = analyze_host(value.rsplit("@", 1)[-1])
        if info is not None:
            b.add("email", value, m.start(), m.end(), info.attrs())
    for m in _HANDLE.finditer(text):
        if b.free(m.start(), m.end()):
            b.add("instapay_handle", m.group(0).lower(), m.start(), m.end())


def _phones(b: _Builder) -> list[PhoneMatch]:
    kept: list[PhoneMatch] = []
    for p in find_phones(b.n.text):
        if not b.free(p.start, p.end):
            continue
        attrs = {"country": p.country}
        if p.operator:
            attrs["operator"] = p.operator
        b.add("phone", p.e164, p.start, p.end, attrs)
        kept.append(p)
    return kept


def _wallets(b: _Builder) -> None:
    folded = b.n.folded
    links = [(i.start, i.end) for i in b.found if i.type in {"url", "domain", "messaging_link"}]
    keywords = [
        m
        for m in find_words(folded, _wallet_pattern())
        if not any(b.n.index[m.start()] < e and s < b.n.index[m.end() - 1] + 1 for s, e in links)
    ]
    lookup = _wallet_lookup()
    phones = [i for i in b.found if i.type == "phone" and i.attrs.get("country") == "EG"]
    for p in phones:
        best: tuple[int, str] | None = None
        for k in keywords:
            ks, ke = b.n.span(k.start(), k.end())
            if ke <= p.start:
                gap, limit = p.start - ke, 60
            elif ks >= p.end:
                gap, limit = ks - p.end, 40
            else:
                continue
            if gap <= limit and (best is None or gap < best[0]):
                best = (gap, lookup[re.sub(r"\s+", " ", k.group(0))])
        if best is not None:
            b.found.append(
                Indicator("wallet", p.value, p.raw, p.start, p.end, {"provider": best[1]})
            )


def _amounts_and_files(b: _Builder) -> None:
    for a in find_amounts(b.n.folded):
        if b.free(a.start, a.end):
            b.add("amount", a.value, a.start, a.end, {"currency": "EGP"})
    for m in _FILE.finditer(b.n.text):
        if b.free(m.start(), m.end()):
            ext = m.group(0).rsplit(".", 1)[-1].lower()
            b.add("file", m.group(0), m.start(), m.end(), {"ext": ext})


def _brands(b: _Builder) -> None:
    lookup = _brand_lookup()
    for m in find_words(b.n.folded, _brand_pattern()):
        if b.free(m.start(), m.end()):
            brand = lookup[re.sub(r"\s+", " ", m.group(0))]
            b.add("brand", brand, m.start(), m.end(), {"name": BRANDS_BY_ID[brand].name}, False)


def _signals(b: _Builder) -> None:
    for s in find_otp_requests(b.n.folded) + find_mixed_script(b.n.text):
        b.add("signal", s.name, s.start, s.end, {"detail": s.detail}, claim=False)


def extract(text: str, types: Collection[IndicatorType] | None = None) -> list[Indicator]:
    """All indicators in `text`, ordered by position. `types` keeps only those types."""
    b = _Builder(normalize(text))
    if b.n.text:
        _links(b)
        _emails_and_handles(b)
        _phones(b)
        _wallets(b)
        _amounts_and_files(b)
        _brands(b)
        _signals(b)
    found = b.found if types is None else [i for i in b.found if i.type in types]
    return sorted(found, key=lambda i: (i.start, _ORDER.get(i.type, 1), i.type))
