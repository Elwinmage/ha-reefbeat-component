from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, cast

import pytest
from collections.abc import Iterable

from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.const import (
    EVENT_KELVIN_LIGHT_UPDATED,
    EVENT_WB_LIGHT_UPDATED,
    LED_CONVERSION_COEF,
)
from custom_components.redsea.light import (
    ReefLedLightEntity,
    ReefLedLightEntityDescription,
)


@dataclass
class _FakeBus:
    fired: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def fire(self, event_type: str, event_data: dict[str, Any]) -> None:
        self.fired.append((event_type, event_data))

    def async_listen(self, event_type: str, listener: Any) -> None:  # pragma: no cover
        return None


@dataclass
class _FakeHass:
    bus: _FakeBus = field(default_factory=_FakeBus)


@dataclass
class _FakeLedCoordinator:
    serial: str = "LED-SERIAL"
    title: str = "LED"
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "LED-SERIAL")})
    )
    last_update_success: bool = True

    is_g1: bool = False
    only_g1: bool = False

    get_data_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)
    pushed: list[tuple[str, str]] = field(default_factory=list)
    forced: int = 0
    quick_refreshed: list[str | None] = field(default_factory=list)

    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        self._listeners.append(update_callback)

        def _remove() -> None:
            return None

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value

    async def push_values(self, source: str, method: str = "post") -> None:
        self.pushed.append((source, method))

    def force_status_update(self) -> None:
        self.forced += 1

    async def async_request_refresh(
        self, source: str | None = None, config: bool = False, wait: int = 2
    ) -> None:
        self.quick_refreshed.append(source)


@pytest.mark.asyncio
async def test_light_async_setup_entry_adds_entities_for_g2_and_virtual_only_g1(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Cover async_setup_entry branches for G2 and virtual-only_g1."""

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    import custom_components.redsea.light as light_mod
    from custom_components.redsea.const import DOMAIN

    class ReefLedCoordinator(_FakeLedCoordinator):
        pass

    class ReefLedG2Coordinator(_FakeLedCoordinator):
        pass

    class ReefVirtualLedCoordinator(_FakeLedCoordinator):
        pass

    monkeypatch.setattr(light_mod, "ReefLedCoordinator", ReefLedCoordinator)
    monkeypatch.setattr(light_mod, "ReefLedG2Coordinator", ReefLedG2Coordinator)
    monkeypatch.setattr(
        light_mod, "ReefVirtualLedCoordinator", ReefVirtualLedCoordinator
    )

    # G2 branch
    entry_g2 = MockConfigEntry(domain=DOMAIN, title="g2", data={}, unique_id="g2")
    entry_g2.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry_g2.entry_id] = ReefLedG2Coordinator(is_g1=False)

    added_g2: list[Any] = []

    def _add_g2(
        new_entities: Iterable[Entity], update_before_add: bool = False
    ) -> None:
        assert update_before_add is True
        added_g2.extend(new_entities)

    await light_mod.async_setup_entry(hass, cast(ConfigEntry, entry_g2), _add_g2)
    assert len(added_g2) == 2  # COMMON_LIGHTS + G2_LIGHTS

    # Virtual only_g1 branch
    entry_v = MockConfigEntry(domain=DOMAIN, title="virt", data={}, unique_id="v")
    entry_v.add_to_hass(hass)
    hass.data[DOMAIN][entry_v.entry_id] = ReefVirtualLedCoordinator(
        only_g1=True,
        is_g1=True,
        title="Virtual",
    )

    added_v: list[Any] = []

    def _add_v(new_entities: Iterable[Entity], update_before_add: bool = False) -> None:
        assert update_before_add is True
        added_v.extend(new_entities)

    caplog.clear()
    await light_mod.async_setup_entry(hass, cast(ConfigEntry, entry_v), _add_v)
    assert len(added_v) == 4  # VIRTUAL_LIGHTS + LIGHTS
    assert any("G1 protocol activated" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_light_update_from_device_kelvin_payload_sets_attrs() -> None:
    device = _FakeLedCoordinator()

    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )

    entity = ReefLedLightEntity(cast(Any, device), desc)

    device.get_data_map[desc.value_name] = {"intensity": 50, "kelvin": 12000}
    entity._update_from_device()

    assert entity.brightness == int(float(50) / LED_CONVERSION_COEF)
    assert entity.color_temp_kelvin == 12000
    assert entity.is_on is True


@pytest.mark.asyncio
async def test_light_turn_on_rounds_kelvin_and_sets_intensity_and_events() -> None:
    device = _FakeLedCoordinator(is_g1=False)

    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )

    entity = ReefLedLightEntity(cast(Any, device), desc)
    entity.hass = cast(Any, _FakeHass())
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    # Current kelvin influences rounding step.
    entity._attr_color_temp_kelvin = 15000

    await entity.async_turn_on(
        **{
            ATTR_COLOR_TEMP_KELVIN: 15123,
            ATTR_BRIGHTNESS: 200,
        }
    )

    # 15123 should round down to 15000 at 500K steps.
    assert (desc.value_name + ".kelvin", 15000) in device.set_calls

    expected_intensity = round(200 * LED_CONVERSION_COEF)
    assert (desc.value_name + ".intensity", expected_intensity) in device.set_calls

    assert (EVENT_KELVIN_LIGHT_UPDATED, {}) in cast(_FakeHass, entity.hass).bus.fired
    assert device.pushed == [("/manual", "post")]


@pytest.mark.asyncio
async def test_light_turn_on_rounds_kelvin_down_across_10000_boundary() -> None:
    device = _FakeLedCoordinator(is_g1=False)

    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )

    entity = ReefLedLightEntity(cast(Any, device), desc)
    entity.hass = cast(Any, _FakeHass())
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    entity._attr_color_temp_kelvin = 11000

    await entity.async_turn_on(
        **{
            ATTR_COLOR_TEMP_KELVIN: 9900,
            ATTR_BRIGHTNESS: 10,
        }
    )

    # 9900 should round down to 9800 (200K steps below 10k).
    assert (desc.value_name + ".kelvin", 9800) in device.set_calls


@pytest.mark.asyncio
async def test_light_turn_on_rounds_kelvin_down_with_500k_steps_above_10k() -> None:
    """Cover the (kelvin // 500) rounding branch when current_kelvin > 10000."""

    device = _FakeLedCoordinator(is_g1=False)

    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )

    entity = ReefLedLightEntity(cast(Any, device), desc)
    entity.hass = cast(Any, _FakeHass())
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    entity._attr_color_temp_kelvin = 15000

    await entity.async_turn_on(
        **{
            ATTR_COLOR_TEMP_KELVIN: 12001,
            ATTR_BRIGHTNESS: 1,
        }
    )

    # 12001 should round down to 12000 at 500K steps.
    assert (desc.value_name + ".kelvin", 12000) in device.set_calls


@pytest.mark.asyncio
async def test_light_turn_on_rounds_kelvin_down_with_200k_steps_below_or_equal_10k() -> (
    None
):
    """Cover the (kelvin // 200) rounding branch when current_kelvin <= 10000."""

    device = _FakeLedCoordinator(is_g1=False)

    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )

    entity = ReefLedLightEntity(cast(Any, device), desc)
    entity.hass = cast(Any, _FakeHass())
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    entity._attr_color_temp_kelvin = 9000

    await entity.async_turn_on(
        **{
            ATTR_COLOR_TEMP_KELVIN: 8501,
            ATTR_BRIGHTNESS: 1,
        }
    )

    # 8501 should round down to 8400 at 200K steps.
    assert (desc.value_name + ".kelvin", 8400) in device.set_calls


def test_light_update_from_device_invalid_kelvin_payload_sets_brightness_zero() -> None:
    device = _FakeLedCoordinator()

    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )

    entity = ReefLedLightEntity(cast(Any, device), desc)
    device.get_data_map[desc.value_name] = "oops"
    entity._update_from_device()

    assert entity.brightness == 0
    assert entity.is_on is False


def test_light_update_from_device_virtual_led_hides_white_blue_when_not_only_g1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force isinstance(..., ReefVirtualLedCoordinator) to match our fake.
    from custom_components.redsea import light as light_mod

    @dataclass
    class _FakeVirtual(_FakeLedCoordinator):
        only_g1: bool = False

    monkeypatch.setattr(light_mod, "ReefVirtualLedCoordinator", _FakeVirtual)

    device = _FakeVirtual()
    desc = ReefLedLightEntityDescription(
        key="white",
        translation_key="white",
        value_name="$.local.white",
    )
    entity = ReefLedLightEntity(cast(Any, device), desc)
    device.get_data_map[desc.value_name] = 100

    entity._update_from_device()

    assert entity.brightness == 0
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_light_async_added_to_hass_swallow_restore_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover the try/except in async_added_to_hass restore parsing."""

    device = _FakeLedCoordinator(is_g1=False)
    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )
    entity = ReefLedLightEntity(cast(Any, device), desc)

    async def _noop_added(self: Any) -> None:
        return None

    monkeypatch.setattr(
        CoordinatorEntity,
        "async_added_to_hass",
        _noop_added,
        raising=True,
    )

    entity.hass = cast(Any, _FakeHass())

    class _BadState:
        state = "on"

        @property
        def attributes(self) -> Any:
            raise RuntimeError("boom")

    async def _get_last_state() -> _BadState:
        return _BadState()

    entity.async_get_last_state = cast(Any, _get_last_state)

    updated: list[bool] = []

    def _noop_update() -> None:
        updated.append(True)

    monkeypatch.setattr(entity, "_update_from_device", _noop_update, raising=True)

    await entity.async_added_to_hass()

    assert updated == [True]


@pytest.mark.asyncio
async def test_light_turn_off_sets_zero_and_refreshes() -> None:
    device = _FakeLedCoordinator(is_g1=False)

    desc = ReefLedLightEntityDescription(
        key="white",
        translation_key="white",
        value_name="$.local.white",
    )

    entity = ReefLedLightEntity(cast(Any, device), desc)
    entity.hass = cast(Any, _FakeHass())
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()

    assert ("$.local.white", 0) in device.set_calls
    assert (EVENT_WB_LIGHT_UPDATED, {}) in cast(_FakeHass, entity.hass).bus.fired
    assert device.forced == 1
    assert device.pushed == [("/manual", "post")]
    assert device.quick_refreshed == ["/manual"]


@pytest.mark.asyncio
async def test_light_async_added_to_hass_restores_brightness_and_color_temp_and_listens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover async_added_to_hass restore path + event selection + update_from_device call."""

    device = _FakeLedCoordinator(is_g1=False)
    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )
    entity = ReefLedLightEntity(cast(Any, device), desc)

    # Avoid CoordinatorEntity's real behavior (needs platform/entity_id).
    async def _noop_added(self: Any) -> None:
        return None

    monkeypatch.setattr(
        CoordinatorEntity,
        "async_added_to_hass",
        _noop_added,
        raising=True,
    )

    entity.hass = cast(Any, _FakeHass())

    class _State:
        state = "on"
        attributes = {"brightness": 12, "color_temp_kelvin": 12345}

    async def _get_last_state() -> _State:
        return _State()

    entity.async_get_last_state = cast(Any, _get_last_state)

    updated: list[bool] = []

    def _noop_update() -> None:
        updated.append(True)

    # async_added_to_hass calls _update_from_device(), which would override restored values.
    monkeypatch.setattr(entity, "_update_from_device", _noop_update, raising=True)

    await entity.async_added_to_hass()

    assert updated == [True]
    assert entity.is_on is True
    assert entity.brightness == 12
    assert entity.color_temp_kelvin == 12345


def test_light_handle_event_update_calls_super_handle_coordinator_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakeLedCoordinator()
    desc = ReefLedLightEntityDescription(
        key="white",
        translation_key="white",
        value_name="$.local.white",
    )
    entity = ReefLedLightEntity(cast(Any, device), desc)

    called: list[bool] = []

    def _super(self: Any) -> None:
        called.append(True)

    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", _super, raising=True
    )

    device.get_data_map[desc.value_name] = 0
    entity._handle_event_update(None)

    assert called == [True]


@pytest.mark.asyncio
async def test_light_turn_on_without_brightness_reads_from_device_for_kelvin_and_white() -> (
    None
):
    """Cover async_turn_on branches where ATTR_BRIGHTNESS is omitted."""

    # Kelvin intensity: reads value_name + '.intensity'
    dev_k = _FakeLedCoordinator(is_g1=False)
    desc_k = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )
    ent_k = ReefLedLightEntity(cast(Any, dev_k), desc_k)
    ent_k.hass = cast(Any, _FakeHass())
    ent_k.async_write_ha_state = lambda: None  # type: ignore[assignment]

    dev_k.get_data_map[desc_k.value_name + ".intensity"] = 7
    await ent_k.async_turn_on(**{ATTR_COLOR_TEMP_KELVIN: 9000})
    assert ent_k.brightness == 7

    # White: reads value_name
    dev_w = _FakeLedCoordinator(is_g1=True)
    desc_w = ReefLedLightEntityDescription(
        key="white",
        translation_key="white",
        value_name="$.local.white",
    )
    ent_w = ReefLedLightEntity(cast(Any, dev_w), desc_w)
    ent_w.hass = cast(Any, _FakeHass())
    ent_w.async_write_ha_state = lambda: None  # type: ignore[assignment]

    dev_w.get_data_map[desc_w.value_name] = 9
    await ent_w.async_turn_on()
    assert ent_w.brightness == 9


@pytest.mark.asyncio
async def test_light_turn_on_white_sets_value_and_fires_event() -> None:
    """Cover non-kelvin async_turn_on set_data + WB event fire."""

    device = _FakeLedCoordinator(is_g1=True)
    desc = ReefLedLightEntityDescription(
        key="white",
        translation_key="white",
        value_name="$.local.white",
    )
    entity = ReefLedLightEntity(cast(Any, device), desc)
    entity.hass = cast(Any, _FakeHass())
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on(**{ATTR_BRIGHTNESS: 10})

    assert (desc.value_name, round(10 * LED_CONVERSION_COEF)) in device.set_calls
    assert (EVENT_WB_LIGHT_UPDATED, {}) in cast(_FakeHass, entity.hass).bus.fired


@pytest.mark.asyncio
async def test_light_turn_off_kelvin_intensity_sets_intensity_zero_and_fires_kelvin_event() -> (
    None
):
    """Cover kelvin_intensity async_turn_off branch."""

    device = _FakeLedCoordinator(is_g1=False)
    desc = ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
    )
    entity = ReefLedLightEntity(cast(Any, device), desc)
    entity.hass = cast(Any, _FakeHass())
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()

    assert (desc.value_name + ".intensity", 0) in device.set_calls
    assert (EVENT_KELVIN_LIGHT_UPDATED, {}) in cast(_FakeHass, entity.hass).bus.fired
