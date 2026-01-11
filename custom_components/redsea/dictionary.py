"""Translation dictionary entries used by the integration.

Note: Home Assistant normally expects translations in `translations/*.json`.
This module is kept for legacy/static label mappings still used in code.
"""

from __future__ import annotations

from typing import Final, Literal, TypedDict


Lang = Literal["en", "fr"]


class DictionaryEntry(TypedDict):
    id: str
    en: str
    fr: str


DICTIONARY: Final[tuple[DictionaryEntry, ...]] = (
    {"id": "Empty", "en": "Empty", "fr": "Vide"},
    {"id": "other", "en": "Other", "fr": "Autre"},
)