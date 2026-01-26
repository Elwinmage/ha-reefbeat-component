from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from conftest import read_device_endpoint
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN
from custom_components.redsea.coordinator import (
    ReefBeatCloudLinkedCoordinator,
    ReefDoseCoordinator,
)


@pytest.fixture(scope="session")
def dose_hwid(devices_dir: Path) -> str:
    di = cast(
        dict[str, Any], read_device_endpoint(devices_dir, "DOSE4", "/device-info")
    )
    return str(di.get("hwid") or di.get("id") or "unknown")


async def test_dose_creates_parent_and_head_devices(
    hass: HomeAssistant,
    dose_hwid: str,
    local_dose_config_entry: MockConfigEntry,
) -> None:
    """ReefDose should create a parent device and per-head devices.

    Protects the "entities attach to default device instead of heads" regression.
    """
    local_dose_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(local_dose_config_entry.entry_id)
    await hass.async_block_till_done()

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    parent = None
    for dev in dev_reg.devices.values():
        if (DOMAIN, dose_hwid) in dev.identifiers:
            parent = dev
            break
    assert parent is not None

    head3 = None
    head4 = None
    for dev in dev_reg.devices.values():
        if (DOMAIN, f"{dose_hwid}_head_3") in dev.identifiers:
            head3 = dev
        if (DOMAIN, f"{dose_hwid}_head_4") in dev.identifiers:
            head4 = dev

    assert head3 is not None
    assert head4 is not None

    head_device_ids = {head3.id, head4.id}
    attached = [
        ent for ent in ent_reg.entities.values() if ent.device_id in head_device_ids
    ]
    assert len(attached) >= 1


class _FakeAPI:
    def __init__(
        self,
        *,
        fetch_data_result: dict[str, Any] | None = None,
        get_data_map: dict[str, Any] | None = None,
    ) -> None:
        self.fetch_data_result = (
            fetch_data_result if fetch_data_result is not None else {}
        )
        self.get_data_map = get_data_map if get_data_map is not None else {}

    async def fetch_data(self) -> dict[str, Any] | None:
        return self.fetch_data_result

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)


@pytest.mark.asyncio
async def test_dose_prefills_local_editable_fields(
    hass: HomeAssistant,
    local_dose_config_entry: MockConfigEntry,
) -> None:
    coordinator = ReefDoseCoordinator(hass, cast(Any, local_dose_config_entry))

    base1 = "$.sources[?(@.name=='/head/1/settings')].data.supplement."
    base2 = "$.sources[?(@.name=='/head/2/settings')].data.supplement."

    fake = _FakeAPI(
        fetch_data_result={"local": {"head": {"2": {"new_supplement_name": "KEEP"}}}},
        get_data_map={
            base1 + "brand_name": "Acme",
            base1 + "name": "Buffer",
            base1 + "short_name": "BUF",
            base2 + "brand_name": "Other",
            base2 + "name": "ShouldNotOverwrite",
            base2 + "short_name": "SNO",
        },
    )
    coordinator.my_api = cast(Any, fake)

    res = await coordinator._async_update_data()
    local = cast(dict[str, Any], res.get("local"))
    head_local = cast(dict[str, Any], local.get("head"))

    head1 = cast(dict[str, Any], head_local["1"])
    assert head1["new_supplement_brand_name"] == "Acme"
    assert head1["new_supplement_name"] == "Buffer"
    assert head1["new_supplement_short_name"] == "BUF"

    head2 = cast(dict[str, Any], head_local["2"])
    assert head2["new_supplement_name"] == "KEEP"


@pytest.mark.asyncio
async def test_dose_delegate_methods_and_hw_version_none(
    hass: HomeAssistant,
    local_dose_config_entry: MockConfigEntry,
) -> None:
    dose = ReefDoseCoordinator(hass, cast(Any, local_dose_config_entry))

    class _DoseAPI:
        def __init__(self) -> None:
            self.cal: list[tuple[str, int, Any]] = []
            self.bundles: list[Any] = []
            self.pressed: list[tuple[str, int | None]] = []
            self.pushed: list[tuple[str, str, int | None]] = []

        async def calibration(self, action: str, head: int, param: Any) -> None:
            self.cal.append((action, head, param))

        async def set_bundle(self, param: Any) -> None:
            self.bundles.append(param)

        async def press(self, action: str, head: int | None = None) -> None:
            self.pressed.append((action, head))

        async def push_values(
            self,
            source: str,
            method: str = "put",
            head: int | None = None,
        ) -> None:
            self.pushed.append((source, method, head))

    api = _DoseAPI()
    dose.my_api = cast(Any, api)

    await dose.calibration("start", 1, {"x": 1})
    await dose.set_bundle({"bundle": True})
    await dose.press("prime", head=2)
    await dose.push_values("/configuration", "put", head=2)

    assert api.cal == [("start", 1, {"x": 1})]
    assert api.bundles == [{"bundle": True}]
    assert api.pressed == [("prime", 2)]
    assert api.pushed == [("/configuration", "put", 2)]
    assert dose.hw_version is None


@pytest.mark.asyncio
async def test_dose_async_update_data_guard_and_continue_paths(
    hass: HomeAssistant,
    local_dose_config_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dose = ReefDoseCoordinator(hass, cast(Any, local_dose_config_entry))

    results: list[dict[str, Any]] = [
        {"local": "not-a-dict"},
        {"local": {"head": "not-a-dict"}},
        {"local": {"head": {"1": "not-a-dict"}}},
    ]

    async def _fake_super_update(self: Any) -> dict[str, Any]:
        return results.pop(0)

    monkeypatch.setattr(
        ReefBeatCloudLinkedCoordinator,
        "_async_update_data",
        _fake_super_update,
        raising=True,
    )

    out1 = await dose._async_update_data()
    assert out1["local"] == "not-a-dict"

    out2 = await dose._async_update_data()
    assert out2["local"] == {"head": "not-a-dict"}

    out3 = await dose._async_update_data()
    assert out3["local"]["head"]["1"] == "not-a-dict"
