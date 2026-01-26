from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.helpers.device_registry import DeviceInfo


@dataclass
class State:
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(
            identifiers={("redsea", "SERIAL")},
            name="Device",
            manufacturer="Red Sea",
            model="X",
        )
    )
    last_update_success: bool = True

    hass: Any | None = None

    get_data_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)
    pressed: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)
    pushed: list[tuple[str, str]] = field(default_factory=list)
    refreshed: list[str] = field(default_factory=list)

    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        self._listeners.append(update_callback)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(update_callback)

        return _remove

    def async_update_listeners(self) -> None:
        for cb in list(self._listeners):
            cb()

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value

    async def press(self, cmd: str) -> None:
        self.pressed.append(cmd)

    async def delete(self, path: str) -> None:
        self.deleted.append(path)

    async def fetch_config(self, path: str) -> None:
        self.fetched.append(path)

    async def push_values(self, source: str, method: str = "put") -> None:
        self.pushed.append((source, method))

    async def async_quick_request_refresh(self, source: str) -> None:
        self.refreshed.append(source)


@dataclass
class FakeDoseCoordinator(FakeCoordinator):
    head_pushed: list[int] = field(default_factory=list)

    async def push_values(self, head: int) -> None:  # type: ignore[override]
        self.head_pushed.append(head)
