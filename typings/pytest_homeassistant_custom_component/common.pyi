from collections.abc import Mapping
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# The real MockConfigEntry subclasses ConfigEntry: keep that relation so a mock
# entry can be passed where a ConfigEntry is expected (and exposes .state).
class MockConfigEntry(ConfigEntry[Any]):
    entry_id: str
    domain: str
    title: str
    unique_id: str | None
    version: int
    minor_version: int

    def __init__(
        self,
        *,
        domain: str,
        title: str | None = ...,
        data: Mapping[str, Any] | None = ...,
        options: Mapping[str, Any] | None = ...,
        unique_id: str | None = ...,
        version: int = ...,
        minor_version: int = ...,
        source: str | None = ...,
        entry_id: str | None = ...,
    ) -> None: ...
    def add_to_hass(self, hass: HomeAssistant) -> None: ...

def async_fire_time_changed(
    hass: HomeAssistant, datetime_: datetime | None = ..., fire_all: bool = ...
) -> None: ...
