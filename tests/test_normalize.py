from egy_ioc.normalize import fold, normalize


def test_arabic_and_persian_digits_become_ascii() -> None:
    assert normalize("٠١٢٣٤٥٦٧٨٩").text == "0123456789"
    assert normalize("۰۱۲۳۴۵۶۷۸۹").text == "0123456789"
    assert normalize("١٢٫٥٠ و ١٬٠٠٠").text == "12.50 و 1,000"


def test_invisible_characters_are_dropped_but_offsets_map_back() -> None:
    source = "منحـــة\u200b تَكافُل"
    n = normalize(source)
    assert n.text == "منحة تكافل"
    start = n.text.index("تكافل")
    s, e = n.span(start, start + len("تكافل"))
    assert source[s:e] == "تَكافُل"


def test_presentation_forms_become_ordinary_letters() -> None:
    # "انستاباي" typed with isolated/final presentation forms, a filter-evasion trick
    assert fold("ﺍﻧﺴﺘﺎﺑﺎﻱ") == fold("انستاباي")


def test_ligature_maps_both_letters_to_one_source_position() -> None:
    n = normalize("ﻻ")  # lam-alef ligature
    assert n.text == "لا"
    assert n.span(0, 2) == (0, 1)


def test_folding_merges_spelling_variants() -> None:
    assert fold("إنستاباى") == fold("انستاباي") == fold("أنستاباي")
    assert fold("مكافأة") == fold("مكافاه")
    assert fold("ڤودافون") == fold("فودافون")


def test_folding_maps_cyrillic_lookalikes_to_latin_and_lowercases() -> None:
    assert fold("Instаpay") == "instapay"  # Cyrillic а
    assert normalize("Instаpay").text == "Instаpay"  # values keep the original letters


def test_text_and_folded_stay_aligned() -> None:
    n = normalize("Ｆａｗｒｙ فوري ١٢٣ İ")
    assert len(n.text) == len(n.folded) == len(n.index)
