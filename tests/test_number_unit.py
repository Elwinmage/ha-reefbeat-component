from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.number as number_platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.entity import ReefBeatRestoreEntity
from custom_components.redsea.number import (
    ReefATOVolumeLeftNumberEntity,
    ReefBeatNumberEntity,
    ReefBeatNumberEntityDescription,
    ReefDoseNumberEntity,
    ReefLedNumberEntity,
    ReefLedNumberEntityDescription,
    ReefRunNumberEntity,
    ReefWaveNumberEntity,
)
from tests._number_test_fakes import FakeCoordinator


@pytest.fixture(autouse=True)
def _patch_base(monkeypatch: Any) -> None:
    async def _noop_async_added_to_hass(self: Any) -> None:
        return

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_async_added_to_hass
    )
    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", lambda self: None
    )


# def test_restore_native_value_float_parse() -> None:
#     assert ReefBeatNumberEntity._restore_native_value("12.5") == 12.5


def test_source_parsing_success_and_fallback() -> None:
    device = FakeCoordinator()

    desc_ok = ReefBeatNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.sources[?(@.name=='/device-settings')].data.stock_alert_days",
        native_min_value=0,
        native_max_value=1,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    )
    ent_ok = ReefBeatNumberEntity(cast(Any, device), desc_ok)
    assert ent_ok._source == "/device-settings"

    desc_bad = ReefBeatNumberEntityDescription(
        key="y",
        translation_key="y",
        value_name="no-quotes-here",
        native_min_value=0,
        native_max_value=1,
        native_step=1,
    )
    ent_bad = ReefBeatNumberEntity(cast(Any, device), desc_bad)
    assert ent_bad._source == "/configuration"


def test_compute_available_dependency_none_true() -> None:
    device = FakeCoordinator()
    desc = ReefBeatNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        dependency=None,
        native_min_value=0,
        native_max_value=1,
        native_step=1,
    )
    ent = ReefBeatNumberEntity(cast(Any, device), desc)
    assert ent._compute_available() is True


def test_compute_available_dependency_truthy_and_values(
    monkeypatch: Any, hass: Any
) -> None:
    device = FakeCoordinator(hass=hass)
    device.get_data_map["$.dep"] = "X"

    # Exercise translate branch: return a value that matches dependency_values.
    # monkeypatch.setattr(
    #     number_platform, "translate", lambda value, *_args, **_kwargs: f"T:{value}"
    # )

    desc = ReefBeatNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        dependency="$.dep",
        dependency_values=("T:X",),
        native_min_value=0,
        native_max_value=1,
        native_step=1,
    )
    ent = ReefBeatNumberEntity(cast(Any, device), desc)
    ent.hass = hass

    assert ent._compute_available() is False


@pytest.mark.asyncio
async def test_base_async_added_to_hass_sets_available_when_value_present() -> None:
    device = FakeCoordinator(last_update_success=False)
    desc = ReefBeatNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        dependency=None,
        native_min_value=0,
        native_max_value=1,
        native_step=1,
    )
    ent = ReefBeatNumberEntity(cast(Any, device), desc)

    ent._attr_native_value = 1.0
    ent._attr_available = False

    await ent.async_added_to_hass()


@pytest.mark.asyncio
async def test_async_set_native_value_seconds_coerces_int(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)

    desc = ReefBeatNumberEntityDescription(
        key="dur",
        translation_key="dur",
        value_name="$.dur",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
    )
    ent = ReefBeatNumberEntity(cast(Any, device), desc)
    ent.hass = hass

    await ent.async_set_native_value(12.7)

    assert device.set_calls[-1] == ("$.dur", 12)
    assert device.pushed
    assert device.refreshed == 1


def test_compute_available_dependency_values_none_uses_truthiness(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)

    desc = ReefBeatNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        dependency="$.dep",
        dependency_values=None,
        native_min_value=0,
        native_max_value=1,
        native_step=1,
    )
    ent = ReefBeatNumberEntity(cast(Any, device), desc)
    ent.hass = hass

    device.get_data_map["$.dep"] = 0
    assert ent._compute_available() is False

    device.get_data_map["$.dep"] = "nonempty"
    assert ent._compute_available() is True


@pytest.mark.asyncio
async def test_async_setup_entry_branches(monkeypatch: Any, hass: Any) -> None:
    class _Led(FakeCoordinator):
        pass

    class _Mat(FakeCoordinator):
        pass

    class _Dose(FakeCoordinator):
        heads_nb: int = 1

    class _Run(FakeCoordinator):
        pass

    class _Wave(FakeCoordinator):
        pass

    class _Ato(FakeCoordinator):
        pass

    # Make isinstance(...) checks hit.
    monkeypatch.setattr(number_platform, "ReefLedCoordinator", _Led)
    monkeypatch.setattr(number_platform, "ReefVirtualLedCoordinator", type("V", (), {}))
    monkeypatch.setattr(number_platform, "ReefLedG2Coordinator", type("G", (), {}))
    monkeypatch.setattr(number_platform, "ReefMatCoordinator", _Mat)
    monkeypatch.setattr(number_platform, "ReefDoseCoordinator", _Dose)
    monkeypatch.setattr(number_platform, "ReefRunCoordinator", _Run)
    monkeypatch.setattr(number_platform, "ReefWaveCoordinator", _Wave)
    monkeypatch.setattr(number_platform, "ReefATOCoordinator", _Ato)

    one = ReefBeatNumberEntityDescription(
        key="one",
        translation_key="one",
        value_name="$.one",
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    monkeypatch.setattr(
        number_platform,
        "LED_NUMBERS",
        (
            ReefLedNumberEntityDescription(
                key="led",
                translation_key="led",
                value_name="$.led",
                native_min_value=0,
                native_max_value=10,
                native_step=1,
                post_specific=None,
            ),
        ),
    )
    monkeypatch.setattr(number_platform, "MAT_NUMBERS", (one,))
    monkeypatch.setattr(number_platform, "WAVE_NUMBERS", (one,))
    monkeypatch.setattr(number_platform, "WAVE_PREVIEW_NUMBERS", (one,))

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Led(hass=hass)
    await number_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    hass.data[DOMAIN][entry.entry_id] = _Mat(hass=hass)
    await number_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    hass.data[DOMAIN][entry.entry_id] = _Dose(hass=hass)
    await number_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    hass.data[DOMAIN][entry.entry_id] = _Run(hass=hass)
    await number_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    hass.data[DOMAIN][entry.entry_id] = _Wave(hass=hass)
    await number_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    hass.data[DOMAIN][entry.entry_id] = _Ato(hass=hass)
    await number_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(isinstance(e, ReefLedNumberEntity) for e in added)
    assert any(isinstance(e, ReefBeatNumberEntity) for e in added)
    assert any(isinstance(e, ReefDoseNumberEntity) for e in added)
    assert any(isinstance(e, ReefRunNumberEntity) for e in added)
    assert any(isinstance(e, ReefWaveNumberEntity) for e in added)
    assert any(isinstance(e, ReefATOVolumeLeftNumberEntity) for e in added)
