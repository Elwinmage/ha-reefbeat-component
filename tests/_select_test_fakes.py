from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.core import HomeAssistant


@dataclass
class FakeCoordinator:
    hass: HomeAssistant
    serial: str = "SERIAL"
    title: str = "Device"
    last_update_success: bool = True
    device_info: dict[str, Any] = field(default_factory=dict)
    _data: dict[str, Any] = field(default_factory=dict)

    # Observability
    pushed: list[dict[str, Any]] = field(default_factory=list)
    refreshed: int = 0
    updated_listeners: int = 0

    def __post_init__(self) -> None:
        if not self.device_info:
            self.device_info = {
                "identifiers": {("redsea", self.serial)},
                "name": self.title,
            }

    def async_add_listener(
        self, _update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        def _remove() -> None:
            return None

        return _remove

    def get_data(self, path: str, _is_None_possible: bool = False) -> Any:  # noqa: N803
        return self._data.get(path)

    def set_data(self, path: str, value: Any) -> None:
        self._data[path] = value

    async def push_values(
        self, source: str, method: str = "put", **kwargs: Any
    ) -> None:
        self.pushed.append({"source": source, "method": method, **kwargs})

    async def async_request_refresh(
        self, source: str | None = None, config: bool = False, wait: int = 2
    ) -> None:
        self.refreshed += 1

    def async_update_listeners(self) -> None:
        self.updated_listeners += 1


class FakeMatCoordinator(FakeCoordinator):
    pass


class FakeDoseCoordinator(FakeCoordinator):
    heads_nb: int = 2

    def head_device_info(self, head_id):
        """Return device info extended with the head identifier (non-mutating)."""
        if head_id <= 0:
            return self.device_info
        else:
            res = deepcopy(self.device_info)
            res["identifiers"] = {("redsea", f"{self.serial}_head_{head_id}")}
            res["name"] = f"{self.title} head {head_id}"
            return res


class FakeLedCoordinator(FakeCoordinator):
    pass


class FakeWaveCoordinator(FakeCoordinator):
    pass


class FakeRunCoordinator(FakeCoordinator):
    def pump_device_info(self, pump_id):
        """Return device info extended with the pump identifier (non-mutating)."""
        if pump_id <= 0:
            return self.device_info
        else:
            res = deepcopy(self.device_info)
            res["identifiers"] = {("redsea", f"{self.serial}_pump_{pump_id}")}
            res["name"] = f"{self.title} pump {pump_id}"
            return res
