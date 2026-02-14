from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.button as button_mod
from custom_components.redsea.const import DOMAIN


@dataclass
class _FakeAPI:
    live_config_update: bool = False


@dataclass
class _FakeBaseDevice:
    serial: str = "SERIAL"
    title: str = "Title"
    my_api: _FakeAPI = field(default_factory=_FakeAPI)
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={(DOMAIN, "SERIAL")})
    )


@pytest.mark.asyncio
async def test_async_setup_entry_adds_entities_for_each_device_type(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Patch coordinator classes used for isinstance checks.
    class _Led(_FakeBaseDevice):
        pass

    class _LedG2(_FakeBaseDevice):
        pass

    class _Mat(_FakeBaseDevice):
        pass

    class _Ato(_FakeBaseDevice):
        pass

    class _Wave(_FakeBaseDevice):
        # used by ReefWaveButtonEntity (not invoked at setup time)
        pass

    class _Run(_FakeBaseDevice):
        pass

    class _Dose(_FakeBaseDevice):
        heads_nb: int = 2

    monkeypatch.setattr(button_mod, "ReefLedCoordinator", _Led)
    monkeypatch.setattr(button_mod, "ReefLedG2Coordinator", _LedG2)
    monkeypatch.setattr(button_mod, "ReefMatCoordinator", _Mat)
    monkeypatch.setattr(button_mod, "ReefATOCoordinator", _Ato)
    monkeypatch.setattr(button_mod, "ReefWaveCoordinator", _Wave)
    monkeypatch.setattr(button_mod, "ReefRunCoordinator", _Run)
    monkeypatch.setattr(button_mod, "ReefDoseCoordinator", _Dose)

    # Keep the described button sets small per branch to avoid depending on
    # complex device methods in `exists_fn`.
    minimal = (
        button_mod.ReefBeatButtonEntityDescription(
            key="k",
            translation_key="k",
            exists_fn=lambda _: True,
            press_fn=None,
        ),
    )
    monkeypatch.setattr(button_mod, "LED_BUTTONS", minimal)
    monkeypatch.setattr(button_mod, "MAT_BUTTONS", minimal)
    monkeypatch.setattr(button_mod, "ATO_BUTTONS", minimal)
    monkeypatch.setattr(button_mod, "PREVIEW_BUTTONS", cast(Any, minimal))
    monkeypatch.setattr(button_mod, "FETCH_CONFIG_BUTTON", minimal)
    monkeypatch.setattr(button_mod, "FIRMWARE_UPDATE_BUTTON", minimal)

    async def _run_for(device: Any) -> list[Any]:
        entry = MockConfigEntry(domain=DOMAIN, title="t", data={}, unique_id="u")
        entry.add_to_hass(hass)

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = device

        captured: list[Entity] = []

        def _add(
            new_entities: Iterable[Entity], update_before_add: bool = False
        ) -> None:
            captured.extend(list(new_entities))

        await button_mod.async_setup_entry(hass, cast(ConfigEntry, entry), _add)
        return captured

    # LED / G2
    assert await _run_for(_Led())
    assert await _run_for(_LedG2())

    # MAT / ATO
    assert await _run_for(_Mat())
    assert await _run_for(_Ato())

    # WAVE / RUN / DOSE
    assert await _run_for(_Wave())

    # RUN: cover both live_config_update states
    run_live = _Run()
    run_live.my_api.live_config_update = True
    assert await _run_for(run_live)

    run_static = _Run()
    run_static.my_api.live_config_update = False
    assert await _run_for(run_static)

    # DOSE: cover both live_config_update states
    dose_live = _Dose()
    dose_live.my_api.live_config_update = True
    assert await _run_for(dose_live)

    dose_static = _Dose()
    dose_static.my_api.live_config_update = False
    assert await _run_for(dose_static)


def test_get_supplement_helpers_success_and_errors() -> None:
    # Known UIDs
    one = button_mod._get_supplement("0e63ba83-3ec4-445e-a3dd-7f2dbdc7f964")
    assert one["uid"]

    bundle = button_mod._get_supplement_bundle("redsea-reefcare")
    assert isinstance(bundle, dict)

    with pytest.raises(ValueError, match=r"Unknown supplement uid"):
        button_mod._get_supplement("does-not-exist")

    # A non-bundle supplement should fail bundle retrieval.
    with pytest.raises(ValueError, match=r"has no valid bundle"):
        button_mod._get_supplement_bundle("0e63ba83-3ec4-445e-a3dd-7f2dbdc7f964")


@pytest.mark.asyncio
async def test_reefbeat_button_entity_press_fn_none_is_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakeBaseDevice()

    desc = button_mod.ReefBeatButtonEntityDescription(
        key="k",
        translation_key="k",
        press_fn=None,
    )

    seen: list[str] = []
    monkeypatch.setattr(
        button_mod._LOGGER,
        "debug",
        lambda msg, *args, **kwargs: seen.append(msg % args if args else msg),
    )

    entity = button_mod.ReefBeatButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert any("No press_fn" in s for s in seen)


@pytest.mark.asyncio
async def test_reefrun_button_entity_preview_save_and_preview_refresh_paths() -> None:
    # Fake run coordinator implementing the small surface used by ReefRunButtonEntity.
    class _Run:
        serial = "RUN"
        title = "Run"
        device_info = DeviceInfo(identifiers={(DOMAIN, "RUN")})
        my_api = _FakeAPI(live_config_update=False)

        deleted: list[str] = []
        pushed: list[tuple[str, int]] = []
        refreshed: list[str] = []
        intensities: list[tuple[int, int]] = []

        def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
            if "/preview" in name and ".ti" in name:
                return 33
            if "/dashboard" in name and ".state" in name:
                return "preview"
            return None

        async def delete(self, source: str) -> None:
            self.deleted.append(source)

        async def set_pump_intensity(self, pump: int, intensity: int) -> None:
            self.intensities.append((pump, intensity))

        async def push_values(
            self, source: str, method: str = "post", pump: int = 0
        ) -> None:
            self.pushed.append((source, pump))

        async def async_request_refresh(
            self, source: str | None = None, config: bool = False, wait: int = 2
        ) -> None:
            # self.refreshed.append("refresh")
            if source is None:
                source = "refresh"
            self.refreshed.append(source)

        async def fetch_config(self) -> None:
            self.refreshed.append("fetch_config")

    device = _Run()

    # preview_save path
    desc_save = button_mod.ReefRunButtonEntityDescription(
        key="preview_save_1",
        translation_key="preview_save",
        press_fn=None,
        pump=1,
    )
    ent = button_mod.ReefRunButtonEntity(cast(Any, device), desc_save)
    ent.async_write_ha_state = lambda *a, **k: None  # type: ignore[method-assign]

    await ent.async_press()
    assert device.deleted == ["/preview"]
    assert device.intensities == [(1, 33)]
    assert device.pushed == [("/pump/settings", 1)]
    assert device.refreshed == ["refresh"]

    # preview_start triggers quick refresh
    device.refreshed.clear()
    desc_start = button_mod.ReefRunButtonEntityDescription(
        key="preview_start_1",
        translation_key="preview_start",
        press_fn=lambda _d: None,
        pump=1,
    )
    ent2 = button_mod.ReefRunButtonEntity(cast(Any, device), desc_start)
    await ent2.async_press()
    assert "/dashboard" in device.refreshed


@pytest.mark.asyncio
async def test_reefrun_button_entity_fetch_config_and_press_fn_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Run:
        serial = "RUN"
        title = "Run"
        device_info = DeviceInfo(identifiers={(DOMAIN, "RUN")})
        my_api = _FakeAPI(live_config_update=False)

        fetched: int = 0
        quick: list[str] = []

        async def fetch_config(self) -> None:
            self.fetched += 1

        async def async_request_refresh(self, source: str) -> None:
            self.quick.append(source)

    device = _Run()

    # fetch_config_* branch
    desc_fetch = button_mod.ReefRunButtonEntityDescription(
        key="fetch_config_1",
        translation_key="fetch_config",
        press_fn=None,
        pump=1,
    )
    ent = button_mod.ReefRunButtonEntity(cast(Any, device), desc_fetch)
    await ent.async_press()
    assert device.fetched == 1
    assert device.quick == []

    # press_fn is None -> debug + return
    seen: list[str] = []
    monkeypatch.setattr(
        button_mod._LOGGER,
        "debug",
        lambda msg, *args, **kwargs: seen.append(msg % args if args else msg),
    )
    desc_none = button_mod.ReefRunButtonEntityDescription(
        key="x",
        translation_key="x",
        press_fn=None,
        pump=1,
    )
    ent2 = button_mod.ReefRunButtonEntity(cast(Any, device), desc_none)
    await ent2.async_press()
    assert any("No press_fn" in s for s in seen)

    # awaitable press_fn branch
    ran: list[bool] = []

    async def _press(_dev: Any) -> None:
        ran.append(True)

    desc_aw = button_mod.ReefRunButtonEntityDescription(
        key="preview_stop_1",
        translation_key="preview_stop",
        press_fn=_press,
        pump=1,
    )
    ent3 = button_mod.ReefRunButtonEntity(cast(Any, device), desc_aw)
    await ent3.async_press()
    assert ran == [True]
    assert "/dashboard" in device.quick


def test_reef_run_button_entity_device_info_uses_pump_device_info() -> None:
    from custom_components.redsea.button import (
        ReefRunButtonEntity,
        ReefRunButtonEntityDescription,
    )

    called: list[int] = []

    class _Device:
        serial = "SERIAL"
        device_info = DeviceInfo(identifiers={(DOMAIN, "SERIAL")})

        def pump_device_info(self, pump_id: int) -> DeviceInfo:
            called.append(pump_id)
            return DeviceInfo(identifiers={(DOMAIN, f"SERIAL_pump_{pump_id}")})

    desc = ReefRunButtonEntityDescription(key="x", translation_key="x", pump=3)
    entity = ReefRunButtonEntity(cast(Any, _Device()), desc)

    _ = entity.device_info
    assert called == [3]


@pytest.mark.asyncio
async def test_reefwave_button_entity_special_cases_and_mode_updates() -> None:
    class _Wave:
        serial = "WAVE"
        title = "Wave"
        device_info = DeviceInfo(identifiers={(DOMAIN, "WAVE")})
        my_api = _FakeAPI(live_config_update=True)

        data: dict[str, Any] = {
            "sources": [
                {"name": "/preview", "type": "data", "data": {"type": "nw"}},
                {"name": "/mode", "type": "data", "data": {"mode": "auto"}},
            ]
        }

        set_calls: list[tuple[str, Any]] = []
        cur_calls: list[tuple[str, str, Any]] = []
        listeners: int = 0
        refreshed: int = 0

        def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
            # minimal JSONPath-like switch for what the entity asks for
            if "'/preview'" in name and name.endswith(".data.type"):
                return self.data["sources"][0]["data"]["type"]
            if "'/preview'" in name and ".data." in name:
                key = name.split(".data.")[-1]
                return self.data["sources"][0]["data"].get(key)
            return None

        def set_data(self, name: str, value: Any) -> None:
            self.set_calls.append((name, value))

        def get_current_value(self, path: str, dn: str) -> Any:
            return 1 if dn == "type" else None

        def set_current_value(self, path: str, dn: str, value: Any) -> None:
            self.cur_calls.append((path, dn, value))

        async def set_wave(self) -> None:
            return

        def async_update_listeners(self) -> None:
            self.listeners += 1

        async def async_request_refresh(self) -> None:
            self.refreshed += 1

    device = _Wave()

    # preview_start with "nw" should early return.
    desc_start = button_mod.ReefWaveButtonEntityDescription(
        key="preview_start",
        translation_key="preview_start",
        press_fn=lambda _d: None,
    )
    ent = button_mod.ReefWaveButtonEntity(cast(Any, device), desc_start)
    ent.async_write_ha_state = lambda *a, **k: None  # type: ignore[method-assign]

    await ent.async_press()

    # preview_set_from_current writes preview values and returns.
    desc_set = button_mod.ReefWaveButtonEntityDescription(
        key="preview_set_from_current",
        translation_key="preview_set_from_current",
        press_fn=None,
    )
    ent2 = button_mod.ReefWaveButtonEntity(cast(Any, device), desc_set)
    ent2.async_write_ha_state = lambda *a, **k: None  # type: ignore[method-assign]

    await ent2.async_press()
    assert device.listeners >= 1

    # default press_fn path updates mode for preview_stop
    desc_stop = button_mod.ReefWaveButtonEntityDescription(
        key="preview_stop",
        translation_key="preview_stop",
        press_fn=lambda _d: None,
    )
    ent3 = button_mod.ReefWaveButtonEntity(cast(Any, device), desc_stop)
    ent3.async_write_ha_state = lambda *a, **k: None  # type: ignore[method-assign]

    await ent3.async_press()
    assert device.refreshed == 1
    assert any("/mode" in k for (k, _v) in device.set_calls)


@pytest.mark.asyncio
async def test_reefwave_button_entity_preview_save_and_default_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Wave:
        serial = "WAVE"
        title = "Wave"
        device_info = DeviceInfo(identifiers={(DOMAIN, "WAVE")})
        my_api = _FakeAPI(live_config_update=True)

        preview: dict[str, Any] = {"type": "nw", "name": "X"}
        set_calls: list[tuple[str, Any]] = []
        cur_calls: list[tuple[str, str, Any]] = []
        listeners: int = 0
        refreshed: int = 0
        wave_set: int = 0

        def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
            if name.endswith(".data.type") and "'/preview'" in name:
                return self.preview.get("type")
            if "'/preview'" in name and ".data." in name:
                key = name.split(".data.")[-1]
                return self.preview.get(key)
            return None

        def set_data(self, name: str, value: Any) -> None:
            self.set_calls.append((name, value))

        def set_current_value(self, path: str, dn: str, value: Any) -> None:
            self.cur_calls.append((path, dn, value))

        def async_update_listeners(self) -> None:
            self.listeners += 1

        async def set_wave(self) -> None:
            self.wave_set += 1

        async def async_request_refresh(self) -> None:
            self.refreshed += 1

    device = _Wave()

    # preview_save covers set_wave, set_current_value loop, and "No Wave" name override.
    desc_save = button_mod.ReefWaveButtonEntityDescription(
        key="preview_save",
        translation_key="preview_save",
        press_fn=lambda _d: None,
    )
    ent = button_mod.ReefWaveButtonEntity(cast(Any, device), desc_save)
    ent.async_write_ha_state = lambda *a, **k: None  # type: ignore[method-assign]
    await ent.async_press()
    assert device.wave_set == 1
    assert any(
        dn == "name" and value == "No Wave" for (_p, dn, value) in device.cur_calls
    )
    assert device.listeners == 1
    assert device.refreshed == 1

    # Default press_fn None branch
    seen: list[str] = []
    monkeypatch.setattr(
        button_mod._LOGGER,
        "debug",
        lambda msg, *args, **kwargs: seen.append(msg % args if args else msg),
    )
    desc_none = button_mod.ReefWaveButtonEntityDescription(
        key="x",
        translation_key="x",
        press_fn=None,
    )
    ent2 = button_mod.ReefWaveButtonEntity(cast(Any, device), desc_none)
    await ent2.async_press()
    assert any("No press_fn" in s for s in seen)

    # Default awaitable press_fn branch + mode update for preview_start
    ran: list[bool] = []

    async def _press(_dev: Any) -> None:
        ran.append(True)

    device.preview["type"] = "wc"  # not "nw" so preview_start proceeds
    desc_start = button_mod.ReefWaveButtonEntityDescription(
        key="preview_start",
        translation_key="preview_start",
        press_fn=_press,
    )
    ent3 = button_mod.ReefWaveButtonEntity(cast(Any, device), desc_start)
    await ent3.async_press()
    assert ran == [True]
    assert any("/mode" in k and v == "preview" for (k, v) in device.set_calls)


@pytest.mark.asyncio
async def test_reefdose_button_entity_remaining_branches_and_device_info() -> None:
    # Small fake coordinator to hit uncovered branches.
    class _Dose:
        serial: str = "DOSE"
        title: str = "Dose"
        my_api: _FakeAPI = _FakeAPI(live_config_update=False)
        device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, "DOSE")},
            manufacturer="m",
            model="model",
            sw_version=None,
            via_device=(DOMAIN, "PARENT"),
        )

        get_data_map: dict[str, Any] = {
            "$.sources[?(@.name=='/dashboard')].data.bundled_heads": False,
            "$.local.head.1.new_supplement": "0e63ba83-3ec4-445e-a3dd-7f2dbdc7f964",
        }

        deleted: list[str] = []
        pressed: list[tuple[str, int]] = []
        calibrated: list[tuple[str, int, dict[str, Any]]] = []
        refreshed: int = 0

        def head_device_info(self, head_id):
            """Return device info extended with the head identifier (non-mutating)."""
            if head_id <= 0:
                return self.device_info
            else:
                res = deepcopy(self.device_info)
                res["identifiers"] = {("redsea", f"{self.serial}_head_{head_id}")}
                res["name"] = f"{self.title} head {head_id}"
                return res

        def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
            return self.get_data_map.get(name)

        async def delete(self, source: str) -> None:
            self.deleted.append(source)

        async def press(self, action: str, head: int) -> None:
            self.pressed.append((action, head))

        async def calibration(
            self, action: str, head: int, payload: dict[str, Any]
        ) -> None:
            self.calibrated.append((action, head, payload))

        async def async_request_refresh(self) -> None:
            self.refreshed += 1

        async def set_bundle(self, payload: dict[str, Any]) -> None:
            return

        async def fetch_config(self, config_path: str | None = None) -> None:
            return

    device = _Dose()

    # delete branch with bundled_heads False -> delete(str(action))
    desc_del = button_mod.ReefDoseButtonEntityDescription(
        key="delete",
        translation_key="delete_supplement",
        action="/head/1/settings",
        delete=True,
        head=1,
    )
    ent = button_mod.ReefDoseButtonEntity(cast(Any, device), desc_del)
    await ent.async_press()
    assert device.deleted == ["/head/1/settings"]
    assert device.refreshed == 1

    # calibration-manual branch
    device.deleted.clear()
    desc_cal = button_mod.ReefDoseButtonEntityDescription(
        key="cal",
        translation_key="cal",
        action="calibration-manual",
        head=1,
    )
    ent2 = button_mod.ReefDoseButtonEntity(cast(Any, device), desc_cal)
    await ent2.async_press()
    assert ("calibration-manual", 1, {"volume": 4}) in device.calibrated

    # else press branch
    desc_press = button_mod.ReefDoseButtonEntityDescription(
        key="manual",
        translation_key="manual",
        action="manual",
        head=1,
    )
    ent3 = button_mod.ReefDoseButtonEntity(cast(Any, device), desc_press)
    await ent3.async_press()
    assert device.pressed[-1] == ("manual", 1)

    # _set_supplement non-special UID -> _get_supplement(uid) + calibration(action)
    device.calibrated.clear()
    desc_supp = button_mod.ReefDoseButtonEntityDescription(
        key="supp",
        translation_key="set_supplement",
        action=["setup-supplement"],
        head=1,
    )
    ent4 = button_mod.ReefDoseButtonEntity(cast(Any, device), desc_supp)
    await ent4.async_press()
    assert device.calibrated and device.calibrated[0][0] == "setup-supplement"

    # device_info cached_property branches
    assert cast(Any, ent4.device_info)["name"] == "Dose head 1"

    desc_head0 = button_mod.ReefDoseButtonEntityDescription(
        key="h0",
        translation_key="h0",
        action="manual",
        head=0,
    )
    ent0 = button_mod.ReefDoseButtonEntity(cast(Any, device), desc_head0)
    assert ent0.device_info == device.device_info
