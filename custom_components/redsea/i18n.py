"""Very small translation helpers for legacy mapping dictionaries.

Home Assistant normally expects translations in `translations/*.json`.
This file remains for internal legacy label mappings (e.g. wave type names).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .dictionary import DICTIONARY

_LOGGER = logging.getLogger(__name__)

# Fallback order when resolving language keys.
# NOTE: "id" here is the dictionary entry identifier key, not Indonesian.
DEFAULT_LANG_FALLBACKS: tuple[str, ...] = ("en", "id")


def _lang_candidates(
    lang: str, fallbacks: Sequence[str] = DEFAULT_LANG_FALLBACKS
) -> list[str]:
    """Return candidate keys to try for a BCP47-like language tag."""
    base = (lang or "").split("-")[0]
    # Keep order, avoid duplicates
    out: list[str] = []
    if base:
        out.append(base)
    for f in fallbacks:
        if f not in out:
            out.append(f)
    return out


def translate_list(lst: Sequence[dict[str, Any]], lang: str) -> list[Any]:
    """Translate a list of dict entries into a list of values for the best language key.

    This expects `lst` entries like: {"en": "...", "fr": "..."}.
    """
    langs = _lang_candidates(lang)

    for key in langs:
        values: list[Any] = []
        found_any = False
        for item in lst:
            if key in item:
                values.append(item[key])
                found_any = True
        if found_any:
            return values

    raise TypeError(
        f"redsea.i18n.translate_list cannot find translation keys {langs} in {lst!r}"
    )


def translate(
    word: str,
    dest_lang: str,
    dictionary: Iterable[Mapping[str, Any]] = DICTIONARY,
    src_lang: str = "id",
) -> Any:
    """Translate a word using a list of mapping dictionaries.

    Each dictionary entry is expected to contain at least an identifier key ("id")
    and one or more language keys ("en", "fr", ...).

    Raises:
        TypeError: if no translation can be found (kept for backward compatibility).
    """
    src_langs = _lang_candidates(src_lang)
    dest_langs = _lang_candidates(dest_lang)

    for src_key in src_langs:
        for entry in dictionary:
            try:
                if entry.get(src_key) != word:
                    continue
            except AttributeError:
                # Non-dict entry in dictionary iterable
                continue

            for dest_key in dest_langs:
                if dest_key in entry:
                    return entry[dest_key]

    raise TypeError(
        "redsea.i18n.translate cannot find translation "
        f"for {word!r} from {src_langs} to {dest_langs}"
    )
