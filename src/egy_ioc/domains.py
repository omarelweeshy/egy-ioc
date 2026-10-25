"""Host analysis: valid TLD, rough registrable site, shorteners, free hosting, official brand
domains and lookalikes.

Lookalike checks are heuristics with known false positives (a real but unlisted brand domain)
and false negatives (a lookalike that shares no token with the brand). They say why they fired,
so a reviewer can judge each hit. The Public Suffix List isn't used, to stay dependency-free;
`site` is an approximation that knows Egyptian second-level suffixes and common free hosts.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources

from egy_ioc.brands import BRANDS, CONTEXT_TOKENS, Brand
from egy_ioc.normalize import fold

# RFC 2606 reserved names: accepted so tests and docs never have to name a real domain.
_RESERVED_TLDS = frozenset({"test", "example", "invalid", "localhost"})

_SECOND_LEVEL = frozenset(
    {
        *(f"{s}.eg" for s in ("com", "gov", "org", "net", "edu", "sci", "eun", "name", "info")),
        *(f"{s}.sa" for s in ("com", "gov", "org", "net", "edu")),
        *(f"{s}.uk" for s in ("co", "org", "gov", "ac")),
        "com.tr",
        "com.br",
        "co.in",
        "com.ng",
        "co.za",
    }
)

SHORTENERS = frozenset(
    {
        "bit.ly",
        "bitly.com",
        "tinyurl.com",
        "t.ly",
        "cutt.ly",
        "rb.gy",
        "is.gd",
        "v.gd",
        "shorturl.at",
        "shorturl.asia",
        "tiny.cc",
        "ow.ly",
        "buff.ly",
        "s.id",
        "rebrand.ly",
        "goo.su",
        "surl.li",
        "clck.ru",
        "qrco.de",
        "lnkd.in",
        "forms.gle",
        "n9.cl",
        "linktr.ee",
    }
)

# Dynamic DNS and free hosting: anyone can get a subdomain in minutes.
FREE_HOSTING = frozenset(
    {
        "duckdns.org",
        "ddns.net",
        "hopto.org",
        "zapto.org",
        "sytes.net",
        "ngrok.io",
        "ngrok-free.app",
        "ngrok.app",
        "trycloudflare.com",
        "pages.dev",
        "workers.dev",
        "vercel.app",
        "netlify.app",
        "github.io",
        "gitlab.io",
        "web.app",
        "firebaseapp.com",
        "glitch.me",
        "replit.app",
        "repl.co",
        "onrender.com",
        "herokuapp.com",
        "blogspot.com",
        "wixsite.com",
        "weebly.com",
        "000webhostapp.com",
        "webflow.io",
        "framer.app",
        "godaddysites.com",
        "surge.sh",
        "azurewebsites.net",
        "sites.google.com",
    }
)

MESSAGING_HOSTS: dict[str, str] = {
    "wa.me": "whatsapp",
    "api.whatsapp.com": "whatsapp",
    "chat.whatsapp.com": "whatsapp",
    "web.whatsapp.com": "whatsapp",
    "whatsapp.com": "whatsapp",
    "t.me": "telegram",
    "telegram.me": "telegram",
    "telegram.dog": "telegram",
}

_SKELETON = str.maketrans(
    {"0": "o", "1": "l", "i": "l", "|": "l", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b"}
)


@cache
def tlds() -> frozenset[str]:
    """IANA root zone TLDs (lowercase, IDN TLDs in punycode) plus RFC 2606 reserved names."""
    raw = resources.files("egy_ioc").joinpath("data/tlds-alpha-by-domain.txt").read_text("utf-8")
    names = {x.strip().lower() for x in raw.splitlines() if x.strip() and not x.startswith("#")}
    return frozenset(names | _RESERVED_TLDS)


def to_ascii(host: str) -> str | None:
    """Lowercase ASCII (punycode) form of a host, or None if it can't be encoded."""
    host = host.lower().rstrip(".")
    if host.isascii():
        return host
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return None


def to_unicode(host: str) -> str:
    labels: list[str] = []
    for label in host.split("."):
        if label.startswith("xn--"):
            with contextlib.suppress(UnicodeError):
                label = label.encode("ascii").decode("idna")
        labels.append(label)
    return ".".join(labels)


def has_valid_tld(host: str) -> bool:
    return host.rsplit(".", 1)[-1] in tlds()


def _suffix(host: str, suffixes: frozenset[str]) -> str | None:
    for s in suffixes:
        if host == s or host.endswith("." + s):
            return s
    return None


def site_of(host: str) -> str:
    """Approximate registrable domain: the part a person had to register or claim."""
    labels = host.split(".")
    free = _suffix(host, FREE_HOSTING)
    if free is not None:
        n = free.count(".") + 2
        return ".".join(labels[-n:]) if len(labels) >= n else host
    if len(labels) >= 3 and ".".join(labels[-2:]) in _SECOND_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _name_tokens(host: str, site: str) -> list[str]:
    """Labels and hyphen parts of the host, without its public suffix."""
    labels = host.split(".")
    free = _suffix(host, FREE_HOSTING)
    if free is not None:
        keep = labels[: len(labels) - (free.count(".") + 1)]
    else:
        keep = labels[: len(labels) - (site.count("."))]
    return [t for label in keep for t in re.split(r"-+", label) if t and t != "www"]


def _skeleton(s: str) -> str:
    return s.translate(_SKELETON).replace("rn", "m").replace("vv", "w")


def _edit_distance_le1(a: str, b: str) -> bool:
    """True if a and b differ by at most one insertion, deletion, substitution or swap."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        i = diff[0]
        return len(diff) == 2 and diff[1] == i + 1 and a[i] == b[i + 1] and a[i + 1] == b[i]
    if la > lb:
        a, b = b, a
    return any(a == b[:i] + b[i + 1 :] for i in range(len(b)))


@dataclass(frozen=True, slots=True)
class HostInfo:
    host: str  # lowercase ASCII (punycode)
    unicode_host: str
    site: str
    official: str | None = None  # brand id when the host is a confirmed official domain
    lookalike: str | None = None  # brand id when the host looks like one
    reason: str | None = None  # why `lookalike` fired
    shortener: bool = False
    free_hosting: bool = False

    @property
    def punycode(self) -> bool:
        return "xn--" in self.host

    def attrs(self) -> dict[str, str]:
        out = {"host": self.host, "site": self.site}
        if self.unicode_host != self.host:
            out["unicode_host"] = self.unicode_host
        if self.punycode:
            out["punycode"] = "true"
        if self.official:
            out["official_brand"] = self.official
        if self.lookalike:
            out["lookalike_brand"] = self.lookalike
            out["lookalike_reason"] = self.reason or ""
        if self.shortener:
            out["shortener"] = "true"
        if self.free_hosting:
            out["free_hosting"] = "true"
        return out


def _official_brand(host: str) -> str | None:
    for b in BRANDS:
        if _suffix(host, frozenset(b.official)) is not None:
            return b.id
    return None


def _lookalike(host: str, unicode_host: str, site: str, b: Brand) -> str | None:
    if not b.official:
        return None
    for d in b.official:  # "ipn.eg.verify-account.top": the real domain worn as a costume
        if re.search(rf"(?:^|[.-]){re.escape(d)}(?:[.-]|$)", host):
            return "official_domain_in_name"
    tokens = _name_tokens(host, site)
    # Homoglyphs: compare the Unicode form with Cyrillic/Greek folded to Latin as well.
    folded_tokens = _name_tokens(fold(unicode_host), site_of(fold(unicode_host)))
    joined = "".join(tokens)
    joined_folded = "".join(folded_tokens)
    if b.generic and not any(t in CONTEXT_TOKENS for t in tokens):
        return None
    for t in b.tokens:
        if t in joined:
            return "contains_brand"
        if t in joined_folded or _skeleton(t) in _skeleton(joined_folded):
            return "homoglyph"
        if len(t) >= 6 and any(_edit_distance_le1(x, t) for x in folded_tokens if len(x) >= 5):
            return "typo"
    for st in b.short_tokens:
        if st in tokens or st in folded_tokens:
            return "brand_label"
    return None


def analyze_host(host: str) -> HostInfo | None:
    """None when the host can't be a real domain (no valid TLD and not an IP address)."""
    ascii_host = to_ascii(host)
    if ascii_host is None or "." not in ascii_host:
        return None
    bare = ascii_host[4:] if ascii_host.startswith("www.") else ascii_host
    is_ip = bool(re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", ascii_host))
    if not is_ip and not has_valid_tld(ascii_host):
        return None
    unicode_host = to_unicode(ascii_host)
    if is_ip:
        return HostInfo(ascii_host, unicode_host, ascii_host)
    site = site_of(bare)
    official = _official_brand(bare)
    lookalike = reason = None
    if official is None:
        for b in BRANDS:
            reason = _lookalike(bare, to_unicode(bare), site, b)
            if reason:
                lookalike = b.id
                break
    return HostInfo(
        host=ascii_host,
        unicode_host=unicode_host,
        site=site,
        official=official,
        lookalike=lookalike,
        reason=reason,
        shortener=site in SHORTENERS or bare in SHORTENERS,
        free_hosting=_suffix(bare, FREE_HOSTING) is not None,
    )
