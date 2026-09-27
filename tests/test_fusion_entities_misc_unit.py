"""Small coverage top-ups for the fusion-related entity plumbing:

- the fusion-method **select** built on RSCONTROL when >=2 temperature sources;
- the RSPower local-temperature reader helper (`_power_local_temperature`);
- the ``attributes_fn`` attribute-attaching branch on the base sensor and binary
  sensor entities (used by the fusion / coherence / anomaly entities).
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.binary_sensor as binary_platform
import custom_components.redsea.select as select_platform
import custom_components.redsea.sensor as sensor_platform
from custom_components.redsea.const import DOMAIN


@dataclass
class _Dev:
    serial: str = "CTL123"
    title: str = "RSCONTROL"
    port_count: int = 0
    src_count: int = 2
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "CTL123")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, cb: Any, ctx: Any = None) -> Any:
        self._listeners.append(cb)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(cb)

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def temperature_source_count(self) -> int:
        return self.src_count

    def fusion_attributes(self) -> dict[str, Any]:
        return {"count": self.src_count, "fused": 25.1}

    async def set_probe_unit(self, uid: str, unit: str) -> None:
        self.unit_calls.append((uid, unit))

    unit_calls: list[tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# select — fusion-method entity gated on >=2 sources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_select_builds_fusion_method_when_two_sources(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(select_platform, "ReefControlCoordinator", _Dev)

    device = _Dev(port_count=0, src_count=2)
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="sel-c")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await select_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, _u=False: added.extend(list(new))),
    )
    keys = {e._description.key for e in added}
    assert "temperature_fusion_method" in keys


@pytest.mark.asyncio
async def test_select_no_fusion_method_below_two_sources(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(select_platform, "ReefControlCoordinator", _Dev)

    device = _Dev(port_count=0, src_count=1)
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="sel-c1")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await select_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, _u=False: added.extend(list(new))),
    )
    assert added == []


# ---------------------------------------------------------------------------
# select — EC probe unit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_select_builds_ec_unit_for_ec_probes(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(select_platform, "ReefControlCoordinator", _Dev)

    device = _Dev(port_count=0, src_count=0)
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.probes"] = [
        {"type": "ec", "uid": "0xE1", "name": "EC"},
        {"type": "ph", "uid": "0xP1", "name": "pH"},  # not ec -> no unit select
    ]
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="sel-ec")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await select_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, _u=False: added.extend(list(new))),
    )
    keys = {e._description.key for e in added}
    assert "probe_ec_0xe1_unit" in keys
    assert not any(k.endswith("_unit") and "0xp1" in k for k in keys)

    unit_entity = next(e for e in added if e._description.key == "probe_ec_0xe1_unit")
    assert unit_entity._description.options == ["ec", "ppt", "sg"]


@pytest.mark.asyncio
async def test_ec_unit_select_writes_via_set_probe_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _Dev(port_count=0, src_count=0)
    desc = select_platform.ReefBeatSelectEntityDescription(
        key="probe_ec_0xe1_unit",
        translation_key="probe_ec_unit",
        options=["ec", "ppt", "sg"],
        value_name=(
            "$.sources[?(@.name=='/probe/config')].data[?(@.type=='ec' "
            "& @.uid=='0xE1')].unit"
        ),
    )
    ent = select_platform.ReefControlProbeECUnitSelectEntity(
        cast(Any, device), desc, uid="0xE1"
    )
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_select_option("sg")

    assert ent.current_option == "sg"
    assert device.unit_calls == [("0xE1", "sg")]


# ---------------------------------------------------------------------------
# sensor._power_local_temperature — object / bare-float / null payloads
# ---------------------------------------------------------------------------

_TEMP_PATH = "$.sources[?(@.name=='/dashboard')].data.temperature"


def test_power_local_temperature_shapes() -> None:
    dev = _Dev()

    dev.get_data_map[_TEMP_PATH] = {"value": 25.4, "status": "ok"}
    assert sensor_platform._power_local_temperature(cast(Any, dev)) == 25.4

    dev.get_data_map[_TEMP_PATH] = {"value": None}
    assert sensor_platform._power_local_temperature(cast(Any, dev)) is None

    dev.get_data_map[_TEMP_PATH] = 24.0  # legacy bare float
    assert sensor_platform._power_local_temperature(cast(Any, dev)) == 24.0

    dev.get_data_map[_TEMP_PATH] = None  # no probe
    assert sensor_platform._power_local_temperature(cast(Any, dev)) is None


# ---------------------------------------------------------------------------
# attributes_fn branch on base sensor + binary sensor
# ---------------------------------------------------------------------------


def test_sensor_entity_attaches_attributes_fn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dev = _Dev()
    desc = sensor_platform.ReefBeatSensorEntityDescription(
        key="temperature_anomaly_source",
        value_fn=lambda d: "ok",
        attributes_fn=lambda d: cast(Any, d).fusion_attributes(),
    )
    ent = sensor_platform.ReefBeatSensorEntity(cast(Any, dev), desc)
    ent._update_val()
    assert ent.native_value == "ok"
    assert ent.extra_state_attributes == {"count": 2, "fused": 25.1}


def test_binary_sensor_entity_attaches_attributes_fn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dev = _Dev()
    desc = binary_platform.ReefBeatBinarySensorEntityDescription(
        key="temperature_coherent",
        value_fn=lambda d: False,
        attributes_fn=lambda d: cast(Any, d).fusion_attributes(),
    )
    ent = binary_platform.ReefBeatBinarySensorEntity(cast(Any, dev), desc)
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)
    ent._handle_coordinator_update()
    assert ent.is_on is False
    assert ent.extra_state_attributes == {"count": 2, "fused": 25.1}
