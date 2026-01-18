from __future__ import annotations

from typing import Any

import pytest

from custom_components.redsea.i18n import _lang_candidates, translate, translate_list


def test_lang_candidates_base_and_fallback_dedup() -> None:
    assert _lang_candidates("fr-CA") == ["fr", "en", "id"]


def test_lang_candidates_empty_lang_uses_fallbacks_only() -> None:
    assert _lang_candidates("") == ["en", "id"]


def test_translate_list_prefers_language_then_fallbacks() -> None:
    lst: list[dict[str, Any]] = [
        {"en": "one", "fr": "un"},
        {"en": "two"},
    ]

    assert translate_list(lst, "fr") == ["un"]
    assert translate_list(lst, "es") == ["one", "two"]


def test_translate_list_raises_when_no_keys_found() -> None:
    with pytest.raises(TypeError):
        translate_list([{"xx": "nope"}], "fr")


def test_translate_skips_non_mapping_entries_and_raises_when_missing() -> None:
    dictionary: list[Any] = [
        "not a dict",
        {"id": "foo", "en": "bar"},
    ]

    assert translate("foo", "en", dictionary=dictionary) == "bar"

    with pytest.raises(TypeError):
        translate("missing", "en", dictionary=dictionary)
