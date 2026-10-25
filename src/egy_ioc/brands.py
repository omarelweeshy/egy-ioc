"""Egyptian brands that scams impersonate, and the words that name a mobile wallet.

Official domains are listed only when a source confirmed them on 2026-10-25 (noted per entry).
A brand with no confirmed domain still gets mention matching but no lookalike check: without an
allowlist, its real site would be flagged as a lookalike of itself.

Aliases are written as people write them and folded at import (see normalize.fold), so one
spelling covers hamza, alef maqsura and ta marbuta variants.
"""

from __future__ import annotations

from dataclasses import dataclass

from egy_ioc.normalize import fold


@dataclass(frozen=True, slots=True)
class Brand:
    id: str
    name: str
    aliases: tuple[str, ...]
    official: tuple[str, ...] = ()  # confirmed official domains
    tokens: tuple[str, ...] = ()  # in another domain's name: substring, homoglyph or typo match
    short_tokens: tuple[str, ...] = ()  # too short for substring matching: whole label only
    generic: bool = False  # token is an ordinary word, so a domain also needs a context word


BRANDS: tuple[Brand, ...] = (
    Brand(
        "instapay",
        "InstaPay",
        ("InstaPay", "insta pay", "إنستاباي", "انستا باي", "إنستا باى"),
        # instapay.eg: App Store listing of the official app. ipn.eg: InstaPay's payment-link
        # domain as parsed by the instapay-eg SDK (secondary source).
        official=("instapay.eg", "ipn.eg"),
        tokens=("instapay",),
        short_tokens=("ipn",),
    ),
    Brand(
        "cib",
        "Commercial International Bank (CIB)",
        ("CIB", "البنك التجاري الدولي", "سي آي بي"),
        official=("cibeg.com",),  # Wikipedia, World Economic Forum profile
        tokens=("cibeg",),
        short_tokens=("cib",),
    ),
    Brand(
        "nbe",
        "National Bank of Egypt",
        ("NBE", "National Bank of Egypt", "البنك الأهلي", "بنك الأهلي", "البنك الاهلي المصري"),
        official=("nbe.com.eg",),  # site fetched 2026-10-25, NBE branding
        short_tokens=("nbe",),
    ),
    Brand(
        "banque_misr",
        "Banque Misr",
        ("Banque Misr", "Bank Misr", "بنك مصر"),
        official=("banquemisr.com",),  # site fetched, title "Banquemisr - Home page"
        tokens=("banquemisr", "bankmisr"),
    ),
    Brand(
        "qnb_egypt",
        "QNB Egypt",
        ("QNB", "بنك قطر الوطني", "كيو إن بي"),
        # Wikipedia, bank site; QNB Egypt's pages are also served from the group's qnb.com.
        official=("qnb.com.eg", "qnb.com"),
        short_tokens=("qnb",),
    ),
    Brand(
        "banque_du_caire",
        "Banque du Caire",
        ("Banque du Caire", "بنك القاهرة"),
        official=("bdc.com.eg",),  # site fetched, title "Banque du Caire | Home Page"
        tokens=("banqueducaire",),
        short_tokens=("bdc",),
    ),
    Brand(
        "cbe",
        "Central Bank of Egypt",
        ("CBE", "Central Bank of Egypt", "البنك المركزي"),
        official=("cbe.org.eg",),  # Wikipedia, Amwal Al Ghad
        short_tokens=("cbe",),
    ),
    Brand(
        "fawry",
        "Fawry",
        # Arabic "فوري" alone also means "instant" (تحويل فوري), so only qualified forms match.
        ("Fawry", "فوري باي", "ماكينة فوري", "ماكينات فوري", "كود فوري", "رقم فوري", "خدمة فوري"),
        official=("fawry.com",),  # site fetched, footer "Fawry Banking and Payment ..."
        tokens=("fawry",),
    ),
    Brand(
        "vodafone",
        "Vodafone Egypt",
        ("Vodafone", "فودافون", "VF Cash", "فودا كاش"),
        official=("vodafone.com.eg",),  # NTRA licensee list (web.vodafone.com.eg)
        tokens=("vodafone", "vodafon"),
    ),
    Brand(
        "etisalat",
        "e& Egypt (Etisalat)",
        # Arabic "اتصالات" alone also means "calls", so only qualified forms match.
        ("Etisalat", "e& Egypt", "اتصالات مصر", "اتصالات كاش", "شركة اتصالات"),
        official=("etisalat.eg",),  # NTRA licensee list
        tokens=("etisalat",),
    ),
    Brand(
        "orange",
        "Orange Egypt",
        # Latin "orange" alone is a fruit or a colour, so only qualified forms match.
        ("Orange Egypt", "Orange Cash", "أورانج", "اورنج"),
        official=("orange.eg",),  # NTRA licensee list
        tokens=("orange",),
        generic=True,
    ),
    Brand(
        "telecom_egypt",
        "Telecom Egypt (WE)",
        ("Telecom Egypt", "WE Pay", "المصرية للاتصالات", "وي باي"),
        official=("te.eg",),  # NTRA licensee list
        tokens=("telecomegypt",),
    ),
    Brand(
        "ntra",
        "National Telecom Regulatory Authority",
        ("NTRA", "الجهاز القومي لتنظيم الاتصالات", "تنظيم الاتصالات"),
        official=("tra.gov.eg",),  # hosts NTRA's published licensee list
        short_tokens=("ntra",),
    ),
    Brand(
        "digital_egypt",
        "Digital Egypt",
        ("Digital Egypt", "مصر الرقمية"),
        official=("digital.gov.eg",),  # traffic-fine guides (secondary source)
        tokens=("digitalegypt", "egyptdigital"),
    ),
    Brand(
        "public_prosecution",
        "Public Prosecution",
        ("Public Prosecution", "النيابة العامة"),
        official=("ppo.gov.eg",),  # site fetched, footer names the Egyptian Public Prosecution
        short_tokens=("ppo",),
    ),
    Brand(
        "egypt_post",
        "Egypt Post",
        ("Egypt Post", "البريد المصري", "بريد مصر"),
        # Al-Dostor (secondary). Some sources still give egyptpost.org; not confirmed, so it
        # is left out and would be flagged.
        official=("egyptpost.gov.eg",),
        tokens=("egyptpost",),
    ),
    # Mention matching only: no official domain confirmed yet.
    Brand("takaful_karama", "Takaful and Karama", ("Takaful and Karama", "تكافل وكرامة")),
    Brand(
        "moss", "Ministry of Social Solidarity", ("وزارة التضامن", "Ministry of Social Solidarity")
    ),
    Brand("nosi", "National Organization for Social Insurance", ("التأمينات الاجتماعية", "NOSI")),
    Brand("moi", "Ministry of Interior", ("وزارة الداخلية", "Ministry of Interior")),
)

BRANDS_BY_ID: dict[str, Brand] = {b.id: b for b in BRANDS}

# Words that, next to a brand token in a domain, make a generic brand word suspicious.
CONTEXT_TOKENS = frozenset(
    {
        "eg",
        "egy",
        "egypt",
        "misr",
        "masr",
        "cash",
        "pay",
        "wallet",
        "bank",
        "login",
        "signin",
        "verify",
        "secure",
        "update",
        "account",
        "support",
        "gift",
        "prize",
        "bonus",
        "refund",
    }
)

# Wallet keyword -> provider. A mobile number near one of these is reported as a wallet.
WALLET_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("فودافون كاش", "vodafone_cash"),
    ("Vodafone Cash", "vodafone_cash"),
    ("VF Cash", "vodafone_cash"),
    ("فودا كاش", "vodafone_cash"),
    ("voda cash", "vodafone_cash"),
    ("اتصالات كاش", "etisalat_cash"),
    ("Etisalat Cash", "etisalat_cash"),
    ("e& cash", "etisalat_cash"),
    ("أورانج كاش", "orange_cash"),
    ("اورنج كاش", "orange_cash"),
    ("Orange Cash", "orange_cash"),
    ("وي باي", "we_pay"),
    ("WE Pay", "we_pay"),
    ("إنستاباي", "instapay"),
    ("انستا باي", "instapay"),
    ("InstaPay", "instapay"),
    ("insta pay", "instapay"),
    ("محفظة", "unknown"),
    ("المحفظة", "unknown"),
    ("wallet", "unknown"),
)


def folded_aliases() -> list[tuple[str, str]]:
    """(folded alias, brand id), longest first so the longest alias wins."""
    pairs = {(fold(a), b.id) for b in BRANDS for a in b.aliases}
    return sorted(pairs, key=lambda p: (-len(p[0]), p[0]))


def folded_wallet_keywords() -> list[tuple[str, str]]:
    pairs = {(fold(k), provider) for k, provider in WALLET_KEYWORDS}
    return sorted(pairs, key=lambda p: (-len(p[0]), p[0]))
