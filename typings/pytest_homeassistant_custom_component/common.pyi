from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from homeassistant.core import HomeAssistant


class MockConfigEntry:
    entry_id: str
    domain: str
    title: str
    data: MutableMapping[str, Any]
    options: MutableMapping[str, Any]
    unique_id: str | None
    version: int

    def __init__(
        self,
        *,
        domain: str,
        title: str | None = ...,
        data: Mapping[str, Any] | None = ...,
        options: Mapping[str, Any] | None = ...,
        unique_id: str | None = ...,
        version: int = ...,
        source: str | None = ...,
    ) -> None: ...

    def add_to_hass(self, hass: HomeAssistant) -> None: ...
