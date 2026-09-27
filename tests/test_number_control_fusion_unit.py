"""Coverage for the RSCONTROL fusion and RSPOWER temperature-calibration paths
of `number.async_setup_entry`, plus the dedicated calibration entity classes.

Uses the same lightweight-fake / monkeypatched-isinstance harness as the other
control platform tests: a fake coordinator is patched onto the platform's
`ReefControlCoordinator` / `ReefPowerCoordinator` symbol so the dispatcher
takes the branch under test, and `/dashboard` reads are served from a map.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.number as number_platform
from custom_components.redsea.const import DOMAIN

_PROBES_PATH = "$.sources[?(@.name=='/dashboard')].data.probes"


@dataclass
class _FakeCtl:
    """Minimal RSCONTROL surface for the number dispatcher + calibration."""

    serial: str = "CTL123"
    title: str = "RSCONTROL"
    port_count: int = 2
    src_count: int = 2
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "CTL123")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    calibration_calls: list[tuple[str, str, float]] = field(default_factory=list)
    range_calls: list[tuple[str, str, str, float, bool]] = field(default_factory=list)
    connected: bool = True
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, cb: Any) -> Any:
        self._listeners.append(cb)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(cb)

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value

    def temperature_source_count(self) -> int:
        return self.src_count

    def probe_is_connected(self, ptype: str, uid: str) -> bool:
        return self.connected

    async def async_calibrate_probe(self, ptype: str, uid: str, value: float) -> None:
        self.calibration_calls.append((ptype, uid, value))

    async def set_probe_range(
        self, ptype: str, uid: str, field: str, value: float, *, is_temp: bool = False
    ) -> None:
        self.range_calls.append((ptype, uid, field, value, is_temp))

    async def async_request_refresh(self) -> None:
        return None


@dataclass
class _FakePower:
    """Minimal RSPOWER surface for the temperature-calibration number."""

    serial: str = "PWR123"
    title: str = "RSPOWER"
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "PWR123")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    local_probe: bool = True
    calibrated: float | None = None
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, cb: Any) -> Any:
        self._listeners.append(cb)
        return lambda: None

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value

    def has_local_temperature(self) -> bool:
        return self.local_probe

    async def async_calibrate_temperature(self, value: float) -> None:
        self.calibrated = value

    async def async_request_refresh(self) -> None:
        return None


async def _run_setup(hass: Any, entry: MockConfigEntry, device: Any) -> list[Any]:
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device
    added: list[Any] = []
    await number_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, update_before_add=False: added.extend(list(new))),
    )
    return added


# ---------------------------------------------------------------------------
# async_setup_entry — RSCONTROL branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_control_builds_probe_calibration_and_coherence_threshold(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(number_platform, "ReefControlCoordinator", _FakeCtl)

    device = _FakeCtl(src_count=2)
    device.get_data_map[_PROBES_PATH] = [
        {"type": "temperature", "uid": "0xT1", "name": "Sump Temp"},
        {"type": "ph", "uid": "0xP1"},  # its embedded temperature
        {"type": "orp", "uid": "0xO1", "name": "ORP"},
        {"type": "leak", "uid": "0xL1"},  # nothing to calibrate
    ]
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c1")
    added = await _run_setup(hass, entry, device)

    by_key = {e._description.key: e for e in added}
    keys = set(by_key)
    # The offsets gave way to the calibration against a reference
    assert not {k for k in keys if k.endswith("_offset")}
    temp = by_key["probe_temperature_0xt1_calibration"]._description
    assert temp.translation_key == "probe_temperature_calibration"
    assert temp.native_step == 0.1
    orp = by_key["probe_orp_0xo1_calibration"]._description
    assert orp.translation_key == "probe_orp_calibration"
    assert orp.native_unit_of_measurement == "mV"
    # pH: the embedded temperature, read from temp_value
    ph = by_key["probe_ph_0xp1_calibration"]._description
    assert ph.translation_key == "probe_temp_calibration"
    assert ph.value_name.endswith(".temp_value")
    assert temp.value_name.endswith(".value")
    assert "probe_leak_0xl1_calibration" not in keys
    # Two sources -> the coherence-threshold number is offered.
    assert "temperature_coherence_threshold" in keys


@pytest.mark.asyncio
async def test_control_no_coherence_threshold_below_two_sources(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(number_platform, "ReefControlCoordinator", _FakeCtl)

    device = _FakeCtl(src_count=1)
    device.get_data_map[_PROBES_PATH] = [
        {"type": "temperature", "uid": "0xT1", "name": "Only Temp"},
    ]
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c2")
    added = await _run_setup(hass, entry, device)

    keys = {e._description.key for e in added}
    assert "probe_temperature_0xt1_calibration" in keys
    assert "temperature_coherence_threshold" not in keys


@pytest.mark.asyncio
async def test_control_builds_global_buzzer_numbers(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Always-created numbers reading/writing /configuration: per-kind
    buzzer frequency/duty_cycle (leak, danger) and the danger debounce.
    """
    monkeypatch.setattr(number_platform, "ReefControlCoordinator", _FakeCtl)

    device = _FakeCtl(src_count=0)
    device.get_data_map[_PROBES_PATH] = []
    device.get_data_map[
        "$.sources[?(@.name=='/configuration')].data.leak_buzzer_config.frequency"
    ] = 12
    device.get_data_map[
        "$.sources[?(@.name=='/configuration')].data.leak_buzzer_config.duty_cycle"
    ] = 50
    device.get_data_map[
        "$.sources[?(@.name=='/configuration')].data.danger_buzzer_config.frequency"
    ] = 6
    device.get_data_map[
        "$.sources[?(@.name=='/configuration')].data.danger_buzzer_config.duty_cycle"
    ] = 20
    device.get_data_map[
        "$.sources[?(@.name=='/configuration')].data.danger_debounce_seconds"
    ] = 30
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c-buzz")
    added = await _run_setup(hass, entry, device)

    by_key = {e._description.key: e for e in added}
    for key in (
        "leak_buzzer_frequency",
        "leak_buzzer_duty_cycle",
        "danger_buzzer_frequency",
        "danger_buzzer_duty_cycle",
        "danger_debounce_seconds",
    ):
        assert key in by_key

    freq = by_key["leak_buzzer_frequency"]
    monkeypatch.setattr(freq, "async_write_ha_state", lambda: None, raising=False)
    freq._handle_coordinator_update()
    assert freq.native_value == 12
    assert freq.available is True

    debounce = by_key["danger_debounce_seconds"]
    monkeypatch.setattr(debounce, "async_write_ha_state", lambda: None, raising=False)
    debounce._handle_coordinator_update()
    assert debounce.native_value == 30


@pytest.mark.asyncio
async def test_control_builds_twelve_range_numbers_per_ec_probe(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One full range-number set (4 fields) per selectable unit (ec/ppt/sg)
    -> 12 entities for a single EC probe.
    """
    monkeypatch.setattr(number_platform, "ReefControlCoordinator", _FakeCtl)

    device = _FakeCtl(src_count=0)
    device.get_data_map[_PROBES_PATH] = [
        {"type": "ec", "uid": "0xE1", "name": "Salinity"},
    ]
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c-ec")
    added = await _run_setup(hass, entry, device)

    ec_entities = [
        e
        for e in added
        if e._description.key.startswith("probe_ec_0xe1_")
        and "_temp_" not in e._description.key
        and not e._description.key.endswith("_calibration")
    ]
    keys = {e._description.key for e in ec_entities}
    assert len(keys) == 12
    for unit in ("ec", "ppt", "sg"):
        for fname in (
            "acceptable_range_low",
            "desired_range_low",
            "desired_range_high",
            "acceptable_range_high",
        ):
            assert f"probe_ec_0xe1_{unit}_{fname}" in keys

    # Bounds match the unit, not a single shared value.
    sg_low = next(
        e
        for e in ec_entities
        if e._description.key == "probe_ec_0xe1_sg_acceptable_range_low"
    )
    assert sg_low._description.native_min_value == 1.0
    assert sg_low._description.native_max_value == 1.04
    ppt_low = next(
        e
        for e in ec_entities
        if e._description.key == "probe_ec_0xe1_ppt_acceptable_range_low"
    )
    assert ppt_low._description.native_min_value == 0
    assert ppt_low._description.native_max_value == 70


# ---------------------------------------------------------------------------
# async_setup_entry — RSPOWER branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_power_builds_temperature_calibration(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(number_platform, "ReefPowerCoordinator", _FakePower)

    entry = MockConfigEntry(domain=DOMAIN, title="pwr", data={}, unique_id="p1")
    added = await _run_setup(hass, entry, _FakePower())

    keys = {e._description.key for e in added}
    assert "temperature_calibration" in keys
    assert "temperature_offset" not in keys


# ---------------------------------------------------------------------------
# entity methods
# ---------------------------------------------------------------------------


def _probe_calibration_entity(device: Any) -> Any:
    desc = number_platform.ReefBeatNumberEntityDescription(
        key="probe_temperature_0xt1_calibration",
        translation_key="probe_temperature_calibration",
        value_name=(
            "$.sources[?(@.name=='/dashboard')].data.probes[?(@.uid=='0xT1')].value"
        ),
    )
    return number_platform.ReefControlProbeCalibrationNumberEntity(
        device, desc, uid="0xT1", ptype="temperature"
    )


@pytest.mark.asyncio
async def test_probe_calibration_entity_calibrates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakeCtl()
    ent = _probe_calibration_entity(device)
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_set_native_value(25.3)
    assert ent.native_value == 25.3
    assert device.calibration_calls == [("temperature", "0xT1", 25.3)]


def test_probe_calibration_entity_shows_the_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakeCtl()
    ent = _probe_calibration_entity(device)
    device.get_data_map[ent._description.value_name] = 25.1
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    ent._handle_coordinator_update()
    assert ent.native_value == 25.1
    assert ent.available is True

    # Unplugged probe: nothing to read, nothing to set
    device.connected = False
    assert ent.available is False


def _probe_range_entity(device: Any, ptype: str = "ph", is_temp: bool = False) -> Any:
    desc = number_platform.ReefBeatNumberEntityDescription(
        key=f"probe_{ptype}_0xp1_desired_range_high",
        translation_key="probe_desired_range_high",
        native_min_value=7.9,
        native_max_value=8.4,
        native_step=0.1,
        value_name=(
            f"$.sources[?(@.name=='/probe/config')].data[?(@.type=='{ptype}' "
            "& @.uid=='0xP1')].ranges[2]"
        ),
    )
    return number_platform.ReefControlProbeRangeNumberEntity(
        device, desc, ptype, "0xP1", "desired_range_high", is_temp=is_temp
    )


@pytest.mark.asyncio
async def test_probe_range_entity_writes_via_set_probe_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakeCtl()
    ent = _probe_range_entity(device)
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_set_native_value(8.3)

    assert ent.native_value == 8.3
    assert device.range_calls == [("ph", "0xP1", "desired_range_high", 8.3, False)]


@pytest.mark.asyncio
async def test_probe_range_entity_temp_sub_threshold_flag_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakeCtl()
    ent = _probe_range_entity(device, ptype="ec", is_temp=True)
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_set_native_value(25.0)

    assert device.range_calls == [("ec", "0xP1", "desired_range_high", 25.0, True)]


def _ec_unit_range_entity(device: Any, field: str, unit: str) -> Any:
    bounds = {
        "ec": (0, 100, 0.1),
        "ppt": (0, 70, 0.1),
        "sg": (1.0, 1.04, 0.001),
    }[unit]
    desc = number_platform.ReefBeatNumberEntityDescription(
        key=f"probe_ec_0xe1_{unit}_{field}",
        translation_key=f"probe_{field}",
        native_min_value=bounds[0],
        native_max_value=bounds[1],
        native_step=bounds[2],
        value_name=(
            "$.sources[?(@.name=='/probe/config')].data[?(@.type=='ec' "
            "& @.uid=='0xE1')].ranges[0]"
        ),
        dependency=(
            "$.sources[?(@.name=='/probe/config')]"
            ".data[?(@.type=='ec' & @.uid=='0xE1')].unit"
        ),
        dependency_values=[unit],
    )
    return number_platform.ReefControlProbeRangeNumberEntity(
        device, desc, "ec", "0xE1", field
    )


_EC_UNIT_PATH = (
    "$.sources[?(@.name=='/probe/config')].data[?(@.type=='ec' & @.uid=='0xE1')].unit"
)


def test_ec_unit_range_entity_available_only_for_current_unit() -> None:
    """The device stores one `ranges` array for whatever unit is currently
    selected — so only the matching unit's 4 entities are usable; the other
    two units' entities for the same bound stay disabled, not deleted (no
    unique_id churn/history loss when the user switches units). Relies on
    `available` being a plain (non-cached) property, so it reacts to a
    unit change instead of freezing at whatever it was on first access.
    """
    device = _FakeCtl()
    ec = _ec_unit_range_entity(device, "acceptable_range_low", "ec")
    ppt = _ec_unit_range_entity(device, "acceptable_range_low", "ppt")
    sg = _ec_unit_range_entity(device, "acceptable_range_low", "sg")

    device.get_data_map[_EC_UNIT_PATH] = "ec"
    assert ec.available is True
    assert ppt.available is False
    assert sg.available is False

    device.get_data_map[_EC_UNIT_PATH] = "sg"
    assert ec.available is False
    assert ppt.available is False
    assert sg.available is True


def test_ec_unit_range_entity_unavailable_when_unit_unknown() -> None:
    """No unit read yet (probe not confirmed, or config still empty) ->
    none of the 3 units' entities are available.
    """
    device = _FakeCtl()  # /probe/config unit path absent from get_data_map
    ent = _ec_unit_range_entity(device, "acceptable_range_high", "ec")
    assert ent.available is False


@pytest.mark.asyncio
async def test_ec_unit_range_entity_writes_via_set_probe_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whichever unit is active, a write still goes through the same
    set_probe_range() call — all 3 units' entities share one underlying
    ranges[idx] value, there is nothing unit-specific to pass along.
    """
    device = _FakeCtl()
    device.get_data_map[_EC_UNIT_PATH] = "sg"
    ent = _ec_unit_range_entity(device, "acceptable_range_high", "sg")
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_set_native_value(1.03)

    assert device.range_calls == [("ec", "0xE1", "acceptable_range_high", 1.03, False)]


@pytest.mark.asyncio
async def test_power_calibration_entity_available_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakePower(local_probe=True)
    desc = number_platform.ReefBeatNumberEntityDescription(
        key="temperature_calibration",
        translation_key="temperature_calibration",
        value_name="$.sources[?(@.name=='/dashboard')].data.temperature.value",
    )
    ent = number_platform.ReefPowerTemperatureCalibrationNumberEntity(
        cast(Any, device), desc
    )

    # Available only while a local probe is installed.
    assert ent.available is True
    device.local_probe = False
    assert ent.available is False

    # Re-paired (a different probe swapped in): the same entity becomes
    # available again — no new entity, no history loss across the swap.
    device.local_probe = True
    assert ent.available is True

    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)
    await ent.async_set_native_value(25.4)
    assert device.calibrated == 25.4
