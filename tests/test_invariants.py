"""Properties that must hold for every message, checked on the invented samples."""

import pytest

from egy_ioc import extract

from .samples import SAMPLES


@pytest.mark.parametrize("text", SAMPLES)
def test_raw_is_exact_evidence(text: str) -> None:
    for i in extract(text):
        assert text[i.start : i.end] == i.raw, i
        assert i.raw.strip() == i.raw, i  # no leading or trailing whitespace


@pytest.mark.parametrize("text", SAMPLES)
def test_results_are_sorted_and_deterministic(text: str) -> None:
    first = extract(text)
    assert first == extract(text)
    assert [i.start for i in first] == sorted(i.start for i in first)


@pytest.mark.parametrize("text", ["", "   ", "\n\n", "ـــ", "\u200b"])
def test_empty_input(text: str) -> None:
    assert extract(text) == []


def test_samples_cover_every_indicator_type() -> None:
    seen = {i.type for text in SAMPLES for i in extract(text)}
    expected = {
        "url",
        "domain",
        "email",
        "messaging_link",
        "instapay_handle",
        "phone",
        "wallet",
        "amount",
        "file",
        "brand",
        "signal",
    }
    assert expected <= seen, expected - seen


def test_bank_otp_message_raises_no_request_signal() -> None:
    legit = SAMPLES[6]
    assert [i for i in extract(legit) if i.value == "otp_request"] == []
