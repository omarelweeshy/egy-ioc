# egy-ioc

Extract scam indicators from messages written in **Egyptian Arabic, Franco-Arab and English**: Egyptian mobile numbers in any format, the mobile wallet they belong to, InstaPay handles and links, lookalike domains of Egyptian banks and government services, WhatsApp and Telegram links, EGP amounts, app downloads, and requests for an OTP code. Every result carries the exact character offsets of its evidence in the original text.

> **Status: v0.1.0, alpha.** Rule-based and unit-tested on invented messages. It has **not** been measured on a labelled set of real scam messages yet, so there are no precision or recall figures. Not published to PyPI yet.

## Why

General IOC extractors are built for English threat reports. They miss what Egyptian scam messages actually contain:

| In the message | What generic tools do | What egy-ioc does |
|---|---|---|
| `٠١٠٠ ٠٠٠ ٠٠٠١` (Arabic-Indic digits, spaced) | No match | `+201000000001`, operator `vodafone` |
| `رقم01000000005` (number glued to Arabic text) | No match | Phone number |
| `فودافون كاش ٠١٠٠...` | A phone number at best | A **wallet**, provider `vodafone_cash` |
| `fake.handle@instapay` | No match, or a broken domain | InstaPay handle |
| `https://cіbeg-secure.test` (Cyrillic `і`) | A URL | URL flagged `lookalike_brand: cib`, reason `homoglyph` |
| `منحـــة تَكافُل وكَرامة` (tatweel and diacritics to dodge filters) | No match | Brand `takaful_karama` |
| `ابعتلي الكود اللي جالك` | Nothing | Signal `otp_request` |
| `لا تشارك هذا الرمز` (a real bank's warning) | n/a | **No** signal |

## Install

From source for now ([uv](https://docs.astral.sh/uv/)):

```bash
git clone https://github.com/omarelweeshy/egy-ioc && cd egy-ioc
uv sync
uv run egy-ioc --help
```

No runtime dependencies. Python 3.11+.

## Use

```python
from egy_ioc import extract, redact

msg = "ادفع ٦ جنيه على فودافون كاش ٠١٠٠ ٠٠٠ ٠٠٠١ او ادخل hxxps://instapay-verify[.]test/login وابعتلي الكود"
for i in extract(msg):
    print(i.type, i.value, i.attrs)
```

```bash
egy-ioc extract message.txt                    # JSON list
egy-ioc extract messages.txt --lines --unique  # one JSON line per message
egy-ioc extract message.txt --types wallet,url --defang
egy-ioc redact messages.txt --lines            # placeholders instead of numbers, emails, handles
egy-ioc normalize message.txt --folded         # see what the matchers see
```

Output for the message above (`--types amount,phone,wallet,url,signal`, trimmed):

```json
[
  {"type": "amount", "value": "6", "raw": "٦ جنيه", "start": 5, "end": 11, "attrs": {"currency": "EGP"}},
  {"type": "phone", "value": "+201000000001", "raw": "٠١٠٠ ٠٠٠ ٠٠٠١", "start": 28, "end": 41,
   "attrs": {"country": "EG", "operator": "vodafone"}},
  {"type": "wallet", "value": "+201000000001", "raw": "٠١٠٠ ٠٠٠ ٠٠٠١", "start": 28, "end": 41,
   "attrs": {"provider": "vodafone_cash"}},
  {"type": "url", "value": "https://instapay-verify.test/login", "raw": "hxxps://instapay-verify[.]test/login",
   "start": 50, "end": 86, "attrs": {"host": "instapay-verify.test", "site": "instapay-verify.test",
   "lookalike_brand": "instapay", "lookalike_reason": "contains_brand", "defanged": "true"}},
  {"type": "signal", "value": "otp_request", "raw": "ابعتلي الكود", "start": 88, "end": 100,
   "attrs": {"detail": "ابعتلي / الكود"}}
]
```

`raw` is always exactly `text[start:end]` of the input, including any tatweel or invisible characters inside it, so it can be shown as evidence.

## Indicator types

| Type | Value | Notes |
|---|---|---|
| `phone` | E.164 | Egyptian mobiles (010, 011, 012, 015) in any common format; other numbers written with `+` or `00` as `country: intl` |
| `wallet` | E.164 | A mobile number with a wallet keyword within 60 characters before or 40 after: Vodafone Cash, e& / Etisalat Cash, Orange Cash, WE Pay, InstaPay, or a generic "محفظة" (`unknown`) |
| `instapay_handle` | `name@instapay` | Lowercased |
| `instapay_link` | URL | Links on `ipn.eg` |
| `url`, `domain` | Refanged, lowercase host | Host analysis in `attrs`, see below |
| `email` | Lowercase | Same host analysis for its domain |
| `messaging_link` | URL | `wa.me`, `api.whatsapp.com`, `chat.whatsapp.com`, `t.me`; a number in the link is also reported as a `phone` |
| `amount` | Decimal string, EGP | Digits with جنيه / ج / ج.م / EGP / LE, and الف / آلاف / مليون multipliers |
| `file` | File name | `.apk`, `.xapk`, `.exe`, `.msi`, `.jar`, ... outside links (links get `file_ext`) |
| `brand` | Brand id | Mentions of 20 Egyptian banks, wallets, telecoms and government bodies |
| `signal` | `otp_request` or `mixed_script` | Behaviour, not an indicator |

### Host analysis

Each `url`, `domain` and `email` carries: `host` (ASCII, punycode for IDNs), `site` (approximate registrable domain), and when they apply `unicode_host`, `punycode`, `official_brand`, `lookalike_brand` + `lookalike_reason`, `shortener`, `free_hosting` (dynamic DNS, Vercel, Netlify, GitHub Pages, ...), `userinfo_in_url` (`https://instapay.eg@evil.test/` goes to `evil.test`), `defanged`, `file_ext`.

Lookalike reasons:

| Reason | Example |
|---|---|
| `official_domain_in_name` | `ipn.eg.verify-account.test`, `cibeg.com-secure.test` |
| `contains_brand` | `instapay-verify.test`, `evil-fawry.vercel.app` |
| `homoglyph` | `1nstapay.test`, `cіbeg-secure.test` (Cyrillic) |
| `typo` | `instapey-eg.test`, `vodafome-cash.test` |
| `brand_label` | `nbe-online.test` (short names match whole labels only) |

A domain is marked `official_brand` only if it's on the confirmed list below. Generic words (Orange) need a context word such as `cash`, `eg` or `login` before they count.

## Redaction and keyed hashing

`redact()` replaces phone numbers, wallets, emails, InstaPay handles and links with placeholders. Without a key they're numbered per message (`[PHONE_1]`). With a key (`--key-env NAME` reads it from an environment variable) they become `[PHONE:<HMAC-SHA256 prefix>]`, stable across messages, so you can still see that two messages used the same wallet.

Why not a plain hash: Egypt has about 400 million possible mobile numbers (4 prefixes x 10^8). Hashing all of them takes minutes on a laptop, so a plain SHA-256 of a phone number can be reversed. An HMAC can't be reversed without the key. Keep the key out of the repository.

## Official domains (confirmed 2026-10-25)

| Brand | Domain(s) | Source |
|---|---|---|
| InstaPay | instapay.eg, ipn.eg | App Store listing; ipn.eg from the [instapay-eg](https://github.com/MohamedMostafa259/instapay-eg) SDK (secondary) |
| CIB | cibeg.com | Wikipedia, World Economic Forum |
| National Bank of Egypt | nbe.com.eg | Site fetched |
| Banque Misr | banquemisr.com | Site fetched |
| QNB Egypt | qnb.com.eg, qnb.com | Wikipedia, bank site |
| Banque du Caire | bdc.com.eg | Site fetched |
| Central Bank of Egypt | cbe.org.eg | Wikipedia, Amwal Al Ghad |
| Fawry | fawry.com | Site fetched |
| Vodafone, e&, Orange, Telecom Egypt | vodafone.com.eg, etisalat.eg, orange.eg, te.eg | NTRA licensee list |
| NTRA | tra.gov.eg | Hosts the licensee list |
| Digital Egypt | digital.gov.eg | Guides (secondary) |
| Public Prosecution | ppo.gov.eg | Site fetched |
| Egypt Post | egyptpost.gov.eg | Al-Dostor (secondary; some sources say egyptpost.org, not confirmed) |

Takaful and Karama, the Ministry of Social Solidarity, NOSI and the Ministry of Interior get mention matching only: with no confirmed domain, a lookalike check would flag their real sites. Corrections with a source are welcome.

## Limits

- **Not measured on real data yet.** The tests use invented messages. Expect misses and false positives on real traffic.
- The operator is the one that issued the prefix. Egypt has number portability, so it may have changed.
- No landlines and no 5-digit hotlines (19xxx, 16xxx).
- Amounts written in words ("خمسمية جنيه") aren't found.
- URLs stop at the first Arabic letter, so Arabic text in a path is cut off. `.مصر` is the only Arabic-script TLD handled.
- `otp_request` is precision-first: it needs an imperative verb and a code word close together on one line, so paraphrases are missed.
- Lookalike detection is heuristic, and `site` is an approximation without the Public Suffix List.
- Arabic letter folding can merge words that differ only by hamza or ta marbuta. That's intended for matching, and values are never folded.
- No STIX output in this package.

## Development

```bash
uv sync
uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest
```

Strict pyright, ruff, and pytest including a seeded fuzz test that checks offsets on 3,000 random mixed-script messages. CI is configured for Python 3.11 and 3.13; so far the suite has been run locally on 3.13 only.

## Part of

`egy-ioc` is phase 1 of a wider open threat-intelligence project on scams that target Egyptians (a lookalike-domain watch, a labelled message dataset, campaign notes). It never visits the links it extracts.

## License

Apache-2.0. See [LICENSE](LICENSE).
