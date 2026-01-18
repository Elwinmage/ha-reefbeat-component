from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.helpers.device_registry import DeviceInfo


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
            via_device=("redsea", "hub"),
        )
    )
    last_update_success: bool = True

    hass: Any | None = None

    get_data_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)
    pushed: list[tuple[tuple[Any, ...], dict[str, Any]]] = field(default_factory=list)
    refreshed: int = 0

    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        self._listeners.append(update_callback)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(update_callback)

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value

    async def push_values(
        self,
        source: str = "/configuration",
        method: str = "put",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.pushed.append(((source, method) + args, dict(kwargs)))

    async def async_request_refresh(self, *, wait: int = 2) -> None:
        self.refreshed += 1


@dataclass
class FakeLedPostSpecific(FakeCoordinator):
    posted: list[str] = field(default_factory=list)

    async def post_specific(self, source: str) -> None:
        self.posted.append(source)


@dataclass
class FakeRunWithPumpIntensity(FakeCoordinator):
    set_intensity_calls: list[tuple[int, int]] = field(default_factory=list)

    async def set_pump_intensity(self, pump: int, intensity: int) -> None:
        self.set_intensity_calls.append((pump, intensity))

    async def push_values(
        self,
        source: str = "/configuration",
        method: str = "put",
        pump: int | None = None,
    ) -> None:  # type: ignore[override]
        self.pushed.append(((source, method), {"pump": pump}))


@dataclass
class FakeAtoWithVolumeLeft(FakeCoordinator):
    set_volume_left_calls: list[int] = field(default_factory=list)

    async def set_volume_left(self, volume_ml: int) -> None:
        self.set_volume_left_calls.append(volume_ml)
