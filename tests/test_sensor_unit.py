from __future__ import annotations

import importlib
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, cast

import pytest
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

import custom_components.redsea.sensor as sensor_platform
from custom_components.redsea.entity import ReefBeatRestoreEntity
from custom_components.redsea.sensor import (
    ReefBeatCloudSensorEntityDescription,
    ReefBeatSensorEntity,
    ReefBeatSensorEntityDescription,
    RestoreSensorEntity,
    RestoreSensorEntityDescription,
)


@dataclass
class _FakeBus:
    fired: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    listeners: list[tuple[str, Callable[[Any], None]]] = field(default_factory=list)

    def fire(self, event_type: str, event_data: dict[str, Any] | None = None) -> None:
        self.fired.append((event_type, dict(event_data or {})))

    def async_listen(
        self, event_type: str, listener: Callable[[Any], None]
    ) -> Callable[[], None]:
        self.listeners.append((event_type, listener))

        def _remove() -> None:
            with suppress(Exception):
                self.listeners.remove((event_type, listener))

        return _remove


@dataclass
class _FakeHass:
    language: str = "en"
    bus: _FakeBus = field(default_factory=_FakeBus)

    @property
    def config(self) -> Any:
        return SimpleNamespace(language=self.language)


@dataclass
class _FakeApi:
    data: dict[str, Any] = field(default_factory=dict)

    def get_data(self, path: str) -> Any:
        return self.data.get(path, [])


@dataclass
class _FakeCoordinator:
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
    last_update_success: bool = False

    hass: Any | None = None
    my_api: _FakeApi = field(default_factory=_FakeApi)

    get_data_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)

    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def cloud_link(self) -> Any:
        return True

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

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value


@dataclass
class _FakeWaveCoordinator(_FakeCoordinator):
    current_values: dict[tuple[str, str], Any] = field(default_factory=dict)

    def get_current_value(self, basename: str, name: str) -> Any:
        return self.current_values.get((basename, name))


@dataclass
class _State:
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 12.5 ", 12.5),
        ("-3", -3.0),
        ("abc", "abc"),
    ],
)
def test_restore_native_value_best_effort_parse(raw: str, expected: Any) -> None:
    assert ReefBeatSensorEntity._restore_native_value(raw) == expected


def test_restore_native_value_numeric_hits_float_return() -> None:
    # Dedicated test to ensure the `return float(state)` line is hit.
    assert ReefBeatSensorEntity._restore_native_value("12") == 12.0


def test_restore_native_value_exception_path_returns_original_state() -> None:
    # Force `float(state)` to raise (TypeError) while still matching the regex via strip().
    class _Weird:
        def strip(self) -> str:  # type: ignore[override]
            return "12"

    weird = _Weird()
    assert ReefBeatSensorEntity._restore_native_value(cast(Any, weird)) is weird


@pytest.mark.asyncio
async def test_sensor_async_added_to_hass_marks_available_when_restored(
    monkeypatch: Any,
) -> None:
    async def _noop_async_added_to_hass(self: Any) -> None:
        return

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_async_added_to_hass
    )

    device = _FakeCoordinator(last_update_success=False)
    desc = ReefBeatSensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=lambda _: 1,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), desc)
    entity._attr_native_value = 1
    entity._attr_available = False

    await entity.async_added_to_hass()
    assert entity.available is False  # CoordinatorEntity availability
    assert entity._attr_available is True


@pytest.mark.asyncio
async def test_sensor_async_added_to_hass_primes_from_cache(monkeypatch: Any) -> None:
    async def _noop_async_added_to_hass(self: Any) -> None:
        return

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_async_added_to_hass
    )

    called: list[str] = []

    def _noop_handle_update(self: Any) -> None:
        called.append("handle")

    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", _noop_handle_update
    )

    device = _FakeCoordinator(last_update_success=True)
    desc = ReefBeatSensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=lambda _: 1,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), desc)

    def _update_val() -> None:
        called.append("update")

    entity._update_val = _update_val  # type: ignore[assignment]

    await entity.async_added_to_hass()
    assert called == ["update", "handle"]


@pytest.mark.parametrize(
    ("signal", "expected_value", "expected_icon"),
    [
        (-81, "poor", "mdi:wifi-strength-outline"),
        (-71, "low", "mdi:wifi-strength-1"),
        (-61, "medium", "mdi:wifi-strength-2"),
        (-51, "good", "mdi:wifi-strength-3"),
        (-45, "excellent", None),
    ],
)
def test_wifi_quality_thresholds(
    signal: int, expected_value: str, expected_icon: str | None
) -> None:
    device = _FakeCoordinator()
    device.get_data_map["$.sources[?(@.name=='/wifi')].data.signal_dBm"] = signal

    desc = ReefBeatSensorEntityDescription(
        key="wifi_quality",
        translation_key="wifi_quality",
        value_fn=lambda _: None,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), desc)
    entity._update_val()

    assert entity.native_value == expected_value
    if expected_icon is not None:
        assert entity.icon == expected_icon


@pytest.mark.parametrize("signal", [None, "n/a"])
def test_wifi_quality_without_signal_is_unavailable(signal: Any) -> None:
    """A missing/non-numeric signal_dBm must not crash on a None comparison."""
    device = _FakeCoordinator()
    # signal is None (key absent) or a non-numeric placeholder.
    if signal is not None:
        device.get_data_map["$.sources[?(@.name=='/wifi')].data.signal_dBm"] = signal

    desc = ReefBeatSensorEntityDescription(
        key="wifi_quality",
        translation_key="wifi_quality",
        value_fn=lambda _: None,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), desc)
    entity._update_val()

    assert entity.native_value is None
    assert entity.available is False


def test_handle_coordinator_update_updates_and_calls_base(monkeypatch: Any) -> None:
    called: list[str] = []

    def _noop_handle_update(self: Any) -> None:
        called.append("base")

    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", _noop_handle_update
    )

    device = _FakeCoordinator(last_update_success=True)
    desc = ReefBeatSensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=lambda _: 1,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), desc)

    def _update_val() -> None:
        called.append("update")

    entity._update_val = _update_val  # type: ignore[assignment]

    entity._handle_coordinator_update()
    assert called == ["update", "base"]


def test_get_value_uses_value_fn_for_reefbeat_description() -> None:
    device = _FakeCoordinator()
    desc = ReefBeatSensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=lambda _: 42,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), desc)
    assert entity._get_value() == 42


def test_get_value_uses_value_name_when_present() -> None:
    device = _FakeCoordinator()
    device.get_data_map["$.value"] = "v"

    desc = ReefBeatCloudSensorEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.value",
    )
    entity = ReefBeatSensorEntity(cast(Any, device), cast(Any, desc))
    assert entity._get_value() == "v"


def test_base_device_info_property_returns_coordinator_device_info() -> None:
    device = _FakeCoordinator()
    desc = ReefBeatSensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=lambda _: 1,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), desc)
    assert entity.device_info == device.device_info


def test_get_value_logs_error_when_no_method(monkeypatch: Any) -> None:
    device = _FakeCoordinator()

    logged: list[tuple[str, Any]] = []

    def _err(msg: str, *args: Any, **kwargs: Any) -> None:
        logged.append((msg, args))

    monkeypatch.setattr(sensor_platform._LOGGER, "error", _err)

    desc = SensorEntityDescription(key="x")
    entity = ReefBeatSensorEntity(cast(Any, device), cast(Any, desc))

    assert entity._get_value() is None
    assert logged


@pytest.mark.asyncio
async def test_restore_sensor_entity_restores_and_syncs_cache(monkeypatch: Any) -> None:
    async def _noop_async_added_to_hass(self: Any) -> None:
        return

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_async_added_to_hass
    )

    fake_hass = _FakeHass(language="en")
    device = _FakeCoordinator(hass=fake_hass)

    desc = RestoreSensorEntityDescription(
        key="restored",
        translation_key="restored",
        head=0,
        value_name="$.restored",
        dependency="dep.event",
    )

    entity = RestoreSensorEntity(cast(Any, device), desc)

    async def _get_last_state() -> Any:
        return _State(state="12", attributes={"native_value": 12})

    entity.async_get_last_state = _get_last_state  # type: ignore[assignment]

    await entity.async_added_to_hass()

    assert ("$.restored", 12) in device.set_calls
    assert entity.native_value == 12
    assert ("dep.event", entity._handle_restore_event) in fake_hass.bus.listeners


@pytest.mark.asyncio
async def test_restore_sensor_entity_unknown_state_clears_value(
    monkeypatch: Any,
) -> None:
    async def _noop_async_added_to_hass(self: Any) -> None:
        return

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_async_added_to_hass
    )

    device = _FakeCoordinator(hass=_FakeHass(language="en"))
    desc = RestoreSensorEntityDescription(
        key="restored",
        translation_key="restored",
        head=0,
        value_name="$.restored",
        dependency=None,
    )

    entity = RestoreSensorEntity(cast(Any, device), desc)

    async def _get_last_state() -> Any:
        return _State(state="unknown", attributes={})

    entity.async_get_last_state = _get_last_state  # type: ignore[assignment]

    await entity.async_added_to_hass()

    assert entity.native_value is None


def test_restore_sensor_handle_event_updates_cache_and_state(monkeypatch: Any) -> None:
    device = _FakeCoordinator(hass=_FakeHass(language="en"))
    desc = RestoreSensorEntityDescription(
        key="restored",
        translation_key="restored",
        head=0,
        value_name="$.restored",
        dependency="dep.event",
    )

    entity = RestoreSensorEntity(cast(Any, device), desc)

    wrote: list[bool] = []
    entity.async_write_ha_state = lambda: wrote.append(True)  # type: ignore[assignment]

    evt = SimpleNamespace(data={"value": 7})
    entity._handle_restore_event(cast(Any, evt))

    assert ("$.restored", 7) in device.set_calls
    assert entity.native_value == 7
    assert wrote == [True]


def test_reload_sensor_module_covers_import_time_lines() -> None:
    # Some lines (e.g. class statements) can be imported before coverage starts.
    # Reloading here ensures those import-time statements are counted.
    importlib.reload(sensor_platform)
    assert hasattr(sensor_platform, "ReefBeatCloudSensorEntity")


# -----------------------------------------------------------------------------
# ENUM guard
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        # Real RSCONTROLPRO payload: an ATO port that never ran reports the
        # reserved HA state as its cause, which can never be an option.
        ("unknown", None),
        # A cause added by a later firmware, absent from our list.
        ("ec_sensor_s3", None),
        # A declared value passes through untouched.
        ("manual", "manual"),
        (None, None),
    ],
)
def test_enum_sensor_drops_values_outside_its_options(
    reported: Any, expected: Any
) -> None:
    """An unlisted ENUM value becomes unknown instead of raising.

    Home Assistant raises `ValueError` when an ENUM sensor writes a state
    outside `options`, which killed the entity and every other listener of the
    coordinator with it.
    """
    from homeassistant.components.sensor import SensorDeviceClass

    options: list[str] = ["none", "manual", "ec_sensor_s1", "ec_sensor_s2"]

    # `test_reload_sensor_module_covers_import_time_lines` swaps the module's
    # classes, so resolve them through the module rather than the names bound
    # at import time: `_get_value` isinstance-checks the current ones.
    device = _FakeCoordinator()
    desc = sensor_platform.ReefBeatSensorEntityDescription(
        key="port_0_last_pump_on_cause",
        translation_key="port_last_pump_on_cause",
        device_class=SensorDeviceClass.ENUM,
        options=options,
        value_fn=lambda _: reported,
    )
    entity = sensor_platform.ReefBeatSensorEntity(cast(Any, device), desc)
    entity._update_val()

    assert entity.native_value == expected
    # What used to raise: HA rejects any ENUM state outside `options`.
    assert entity.native_value is None or entity.native_value in options


def test_non_enum_sensor_keeps_unlisted_values() -> None:
    """Without `device_class=ENUM` the raw firmware string is preserved.

    The device-level `last_pump_on_cause` is deliberately not an ENUM, so it
    must keep reporting causes we have not catalogued.
    """
    device = _FakeCoordinator()
    desc = sensor_platform.ReefBeatSensorEntityDescription(
        key="last_pump_on_cause",
        translation_key="last_pump_on_cause",
        value_fn=lambda _: "ec_sensor_s3",
    )
    entity = sensor_platform.ReefBeatSensorEntity(cast(Any, device), desc)
    entity._update_val()

    assert entity.native_value == "ec_sensor_s3"
