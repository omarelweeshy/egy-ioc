"""Command line: egy-ioc extract | redact | normalize."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import cast

from egy_ioc import __version__
from egy_ioc.extract import extract, refang
from egy_ioc.model import INDICATOR_TYPES, Indicator, IndicatorType
from egy_ioc.normalize import normalize
from egy_ioc.redact import DEFAULT_TYPES, redact

_DEFANG_TYPES = frozenset({"url", "domain", "email", "messaging_link", "instapay_link"})


def defang(value: str) -> str:
    """Make a link unclickable for sharing: hxxp, [.] and [@]. Already-defanged input is
    refanged first, so it isn't defanged twice."""
    value = re.sub(r"^http", "hxxp", refang(value), flags=re.I)
    return value.replace(".", "[.]").replace("@", "[@]")


def _read(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.buffer.read().decode("utf-8-sig")
    return Path(path).read_text(encoding="utf-8-sig")


def _messages(path: str | None, lines: bool) -> Iterator[tuple[int | None, str]]:
    text = _read(path)
    if not lines:
        yield None, text
        return
    for n, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            yield n, line


def _types(arg: str | None) -> list[IndicatorType] | None:
    if not arg:
        return None
    names = [t.strip() for t in arg.split(",") if t.strip()]
    bad = [t for t in names if t not in INDICATOR_TYPES]
    if bad:
        raise SystemExit(f"unknown type(s): {', '.join(bad)}. Known: {', '.join(INDICATOR_TYPES)}")
    return [cast(IndicatorType, t) for t in names]


def _as_dict(i: Indicator, defanged: bool) -> dict[str, object]:
    d = i.to_dict()
    if defanged and i.type in _DEFANG_TYPES:
        d["value"] = defang(i.value)
        d["raw"] = defang(i.raw)
    return d


def _unique(found: list[Indicator], defanged: bool) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], dict[str, object]] = {}
    for i in found:
        key = (i.type, i.value)
        if key not in groups:
            groups[key] = {**_as_dict(i, defanged), "count": 0}
        groups[key]["count"] = cast(int, groups[key]["count"]) + 1
    return list(groups.values())


def _cmd_extract(args: argparse.Namespace) -> int:
    types = _types(args.types)
    for line_no, text in _messages(args.path, args.lines):
        found = extract(text, types)
        items = (
            _unique(found, args.defang)
            if args.unique
            else [_as_dict(i, args.defang) for i in found]
        )
        if line_no is None:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"line": line_no, "indicators": items}, ensure_ascii=False))
    return 0


def _cmd_redact(args: argparse.Namespace) -> int:
    key: bytes | None = None
    if args.key_env:
        value = os.environ.get(args.key_env)
        if not value:
            raise SystemExit(f"environment variable {args.key_env} is empty or not set")
        key = value.encode("utf-8")
    types = _types(args.types) or sorted(DEFAULT_TYPES)
    for line_no, text in _messages(args.path, args.lines):
        out = redact(text, types, key)
        print(out if line_no is None else out.replace("\n", " "))
    return 0


def _cmd_normalize(args: argparse.Namespace) -> int:
    n = normalize(_read(args.path))
    print(n.folded if args.folded else n.text)
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="egy-ioc",
        description="Scam indicators from Egyptian Arabic, Franco-Arab and English messages.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("path", nargs="?", help="input file (UTF-8); stdin when omitted or '-'")
        sp.add_argument("--lines", action="store_true", help="treat each line as one message")
        sp.add_argument("--types", help="comma-separated indicator types to keep")

    ex = sub.add_parser("extract", help="print indicators as JSON")
    common(ex)
    ex.add_argument("--unique", action="store_true", help="one entry per type and value")
    ex.add_argument("--defang", action="store_true", help="defang links in the output")
    ex.set_defaults(func=_cmd_extract)

    rd = sub.add_parser("redact", help="replace phone numbers, emails and handles")
    common(rd)
    rd.add_argument(
        "--key-env",
        metavar="NAME",
        help="environment variable holding an HMAC key: placeholders become stable keyed hashes",
    )
    rd.set_defaults(func=_cmd_redact)

    nm = sub.add_parser("normalize", help="print the normalized (or folded) text")
    nm.add_argument("path", nargs="?")
    nm.add_argument("--folded", action="store_true")
    nm.set_defaults(func=_cmd_normalize)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")  # Windows consoles default to a code page
    args = _parser().parse_args(argv)
    return cast(int, args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
