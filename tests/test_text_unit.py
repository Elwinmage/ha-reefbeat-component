from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    last_update_success: bool = True
    device_info: dict[str, Any] = field(default_factory=dict)
    _data: dict[str, Any] = field(default_factory=dict)

    def head_device_info(self, head_id):
        """Return device info extended with the head identifier (non-mutating)."""
        if head_id <= 0:
            return self.device_info
        else:
            return {
                "identifiers": {("redsea", f"{self.serial}_head_{head_id}")},
                "name": f"Dose head {head_id}",
                "manufacturer": "Red Sea",
                "model": None,
                "model_id": "mid",
                "hw_version": "1",
                "sw_version": "2",
                "via_device": ("redsea", "IDENT"),
            }

    def __post_init__(self) -> None:
        if not self.device_info:
            self.device_info = {"identifiers": {("redsea", self.serial)}}

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        def _remove() -> None:
            return None

        return _remove

    def get_data(self, path: str, _is_None_possible: bool = False) -> Any:  # noqa: N803
        return self._data.get(path)

    def set_data(self, path: str, value: Any) -> None:
        self._data[path] = value

    def async_update_listeners(self) -> None:
        return None


@pytest.mark.asyncio
async def test_reefbeat_text_async_added_to_hass_sets_available_and_primes_from_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.entity import ReefBeatRestoreEntity
    from custom_components.redsea.text import (
        ReefBeatTextEntity,
        ReefBeatTextEntityDescription,
    )

    async def _noop_added_to_hass(self: Any) -> None:
        return None

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_added_to_hass
    )

    wrote: list[bool] = []

    def _noop_handle_update(self: Any) -> None:
        wrote.append(True)

    monkeypatch.setattr(
        CoordinatorEntity,
        "_handle_coordinator_update",
        _noop_handle_update,
        raising=True,
    )

    device = _FakeCoordinator(last_update_success=True, _data={"$.x": "abc"})
    desc = ReefBeatTextEntityDescription(key="x", translation_key="x", value_name="$.x")

    ent = ReefBeatTextEntity(cast(Any, device), desc)
    assert ent.native_value == "abc"

    await ent.async_added_to_hass()

    assert ent.available is True
    assert ent.native_value == "abc"
    assert wrote == [True]


@pytest.mark.asyncio
async def test_reefbeat_text_async_set_value_mirrors_to_coordinator_and_writes_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.text import (
        ReefBeatTextEntity,
        ReefBeatTextEntityDescription,
    )

    device = _FakeCoordinator(_data={"$.x": "old"})
    desc = ReefBeatTextEntityDescription(key="x", translation_key="x", value_name="$.x")
    ent = ReefBeatTextEntity(cast(Any, device), desc)

    wrote: list[str] = []

    def _write() -> None:
        wrote.append(cast(str, ent.native_value))

    monkeypatch.setattr(ent, "async_write_ha_state", _write, raising=True)

    await ent.async_set_value("new")

    assert device.get_data("$.x") == "new"
    assert ent.native_value == "new"
    assert wrote == ["new"]


@pytest.mark.asyncio
async def test_reefdose_text_async_added_to_hass_registers_dependency_listener(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.entity import ReefBeatRestoreEntity
    from custom_components.redsea.text import (
        ReefDoseTextEntity,
        ReefDoseTextEntityDescription,
    )

    async def _noop_added_to_hass(self: Any) -> None:
        return None

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_added_to_hass
    )

    def _noop_handle_update(self: Any) -> None:
        return None

    monkeypatch.setattr(
        CoordinatorEntity,
        "_handle_coordinator_update",
        _noop_handle_update,
        raising=True,
    )

    device = _FakeCoordinator()
    desc = ReefDoseTextEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.x",
        head=1,
        dependency="redsea.dependency",
    )

    ent = ReefDoseTextEntity(cast(Any, device), desc)
    ent.hass = hass

    listened: list[tuple[str, Any]] = []

    def _listen(_bus: Any, event_type: str, listener: Any) -> Callable[[], None]:
        listened.append((event_type, listener))

        def _unsub() -> None:
            return None

        return _unsub

    monkeypatch.setattr(type(hass.bus), "async_listen", _listen, raising=True)

    removed: list[bool] = []

    def _on_remove(_unsub: Callable[[], None]) -> None:
        removed.append(True)

    monkeypatch.setattr(ent, "async_on_remove", _on_remove, raising=True)

    await ent.async_added_to_hass()

    assert listened and listened[0][0] == "redsea.dependency"
    assert removed == [True]


@pytest.mark.asyncio
async def test_reefbeat_text_async_added_to_hass_sets_available_if_value_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.entity import ReefBeatRestoreEntity
    from custom_components.redsea.text import (
        ReefBeatTextEntity,
        ReefBeatTextEntityDescription,
    )

    async def _noop_added_to_hass(self: Any) -> None:
        return None

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_added_to_hass
    )

    device = _FakeCoordinator(last_update_success=False, _data={"$.x": "value"})
    desc = ReefBeatTextEntityDescription(key="x", translation_key="x", value_name="$.x")

    ent = ReefBeatTextEntity(cast(Any, device), desc)
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    ent._attr_available = False
    assert ent.native_value == "value"

    await ent.async_added_to_hass()
    assert ent._attr_available is True


def test_reefdose_text_handle_update_sets_available_for_bool_and_non_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.text import (
        ReefDoseTextEntity,
        ReefDoseTextEntityDescription,
    )

    device = _FakeCoordinator()
    desc = ReefDoseTextEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.x",
        head=1,
    )

    ent = ReefDoseTextEntity(cast(Any, device), desc)

    wrote: list[bool] = []

    def _write() -> None:
        wrote.append(True)

    monkeypatch.setattr(ent, "async_write_ha_state", _write, raising=True)

    class _Event:
        def __init__(self, other: Any) -> None:
            self.data = {"other": other}

    ent._handle_update(_Event(True))
    assert ent.available is True

    ent._handle_update(_Event(1))
    assert ent.available is True

    assert wrote == [True, True]


def test_reefdose_text_device_info_head_zero_returns_base() -> None:
    from custom_components.redsea.text import (
        ReefDoseTextEntity,
        ReefDoseTextEntityDescription,
    )

    base_di = {"identifiers": {("redsea", "BASE")}, "manufacturer": "Red Sea"}
    device = _FakeCoordinator(serial="BASE", device_info=base_di)

    desc = ReefDoseTextEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.x",
        head=0,
    )

    ent = ReefDoseTextEntity(cast(Any, device), desc)

    assert ent.device_info == base_di


def test_reefdose_text_device_info_builds_head_device_and_copies_fields_and_via_device() -> (
    None
):
    from custom_components.redsea.text import (
        ReefDoseTextEntity,
        ReefDoseTextEntityDescription,
    )

    base_di = {
        "identifiers": {("redsea", "IDENT")},
        "manufacturer": "Red Sea",
        "model": None,
        "model_id": "mid",
        "hw_version": "1",
        "sw_version": "2",
        "via_device": ("redsea", "IDENT"),
    }
    device = _FakeCoordinator(serial="SERIAL", title="Dose", device_info=base_di)

    desc = ReefDoseTextEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.x",
        head=3,
    )

    ent = ReefDoseTextEntity(cast(Any, device), desc)
    di = cast(dict[str, Any], ent.device_info)

    assert di["identifiers"] == {("redsea", "SERIAL_head_3")}
    assert di["name"] == "Dose head 3"
    assert di["manufacturer"] == "Red Sea"
    assert di["model"] is None
    assert di["model_id"] == "mid"
    assert di["via_device"] == ("redsea", "IDENT")


def test_reefdose_text_device_info_falls_back_to_default_identifiers_when_missing() -> (
    None
):
    from custom_components.redsea.text import (
        ReefDoseTextEntity,
        ReefDoseTextEntityDescription,
    )

    device = _FakeCoordinator(serial="SER123", title="Dose", device_info={})

    desc = ReefDoseTextEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.x",
        head=1,
    )

    ent = ReefDoseTextEntity(cast(Any, device), desc)
    di = cast(dict[str, Any], ent.device_info)

    assert di["identifiers"] == {("redsea", "SER123_head_1")}


def test_reefbeat_text_restore_value_returns_state() -> None:
    from custom_components.redsea.text import ReefBeatTextEntity

    assert ReefBeatTextEntity._restore_value("hello") == "hello"


def test_reefbeat_text_device_info_returns_base_device_info() -> None:
    from custom_components.redsea.text import (
        ReefBeatTextEntity,
        ReefBeatTextEntityDescription,
    )

    base_di = {"identifiers": {("redsea", "BASE")}, "manufacturer": "Red Sea"}
    device = _FakeCoordinator(serial="BASE", device_info=base_di)
    desc = ReefBeatTextEntityDescription(key="x", translation_key="x", value_name="$.x")

    ent = ReefBeatTextEntity(cast(Any, device), desc)
    assert ent.device_info == base_di


def test_text_handle_coordinator_update_refreshes_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Couvre _handle_coordinator_update : lignes 203-204."""
    from custom_components.redsea.text import (
        ReefBeatTextEntity,
        ReefBeatTextEntityDescription,
    )

    device = _FakeCoordinator()
    device._data["$.wifi.ssid"] = "InitialNetwork"

    desc = ReefBeatTextEntityDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        value_name="$.wifi.ssid",
    )

    wrote: list[bool] = []
    monkeypatch.setattr(
        CoordinatorEntity,
        "_handle_coordinator_update",
        lambda self: wrote.append(True),
    )

    entity = ReefBeatTextEntity(cast(Any, device), desc)
    assert entity.native_value == "InitialNetwork"

    # Changer la valeur dans le coordinator puis déclencher la mise à jour
    device._data["$.wifi.ssid"] = "UpdatedNetwork"
    entity._handle_coordinator_update()  # lignes 203-204

    assert entity.native_value == "UpdatedNetwork"
    assert wrote == [True]


def test_text_available_with_dependency_false() -> None:
    """Couvre la propriété available avec dependency : ligne 221."""
    from custom_components.redsea.text import (
        ReefBeatTextEntity,
        ReefBeatTextEntityDescription,
    )

    device = _FakeCoordinator()
    # La dependency retourne False
    device._data["$.local.head.1.new_supplement"] = False
    device._data["$.local.head.1.new_supplement_brand_name"] = "Brand"

    desc = ReefBeatTextEntityDescription(
        key="new_supplement_brand_name_1",
        translation_key="new_supplement_brand_name",
        value_name="$.local.head.1.new_supplement_brand_name",
        dependency="$.local.head.1.new_supplement",  # dependency présente
    )

    entity = ReefBeatTextEntity(cast(Any, device), desc)

    # available doit retourner False car la dependency est False (ligne 221)
    assert entity.available is False


def test_text_available_with_dependency_true() -> None:
    """Couvre la propriété available avec dependency : ligne 221 (branche True)."""
    from custom_components.redsea.text import (
        ReefBeatTextEntity,
        ReefBeatTextEntityDescription,
    )

    device = _FakeCoordinator()
    device._data["$.local.head.1.new_supplement"] = True
    device._data["$.local.head.1.new_supplement_brand_name"] = "Brand"

    desc = ReefBeatTextEntityDescription(
        key="new_supplement_brand_name_1",
        translation_key="new_supplement_brand_name",
        value_name="$.local.head.1.new_supplement_brand_name",
        dependency="$.local.head.1.new_supplement",
    )

    entity = ReefBeatTextEntity(cast(Any, device), desc)

    assert entity.available is True
