from __future__ import annotations

from datetime import time as dt_time
from typing import Any, cast

import pytest


class _FakeMatCoordinator:
    def __init__(self) -> None:
        self.serial = "SERIAL"
        self.last_update_success = True
        self._set: list[tuple[str, Any]] = []
        self._listeners_called = 0
        self.pushed = 0
        self._data: dict[tuple[str, bool], Any] = {}

        # Minimal device_info surface for the `device_info` cached_property.
        self.device_info = {"identifiers": {("redsea", "SERIAL")}}

    def get_data(self, path: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self._data.get((path, bool(is_None_possible)))

    def set_data(self, path: str, value: Any) -> None:
        self._set.append((path, value))

    def async_update_listeners(self) -> None:
        self._listeners_called += 1

    async def push_values(self) -> None:
        self.pushed += 1


def test_restore_value_parses_isoformat() -> None:
    from custom_components.redsea.time import ReefMatTimeEntity

    assert ReefMatTimeEntity._restore_value("12:34:00") == dt_time(12, 34)


def test_minutes_to_time_none_returns_none() -> None:
    from custom_components.redsea.time import ReefMatTimeEntity

    assert ReefMatTimeEntity._seconds_to_time(None) is None


@pytest.mark.asyncio
async def test_async_set_value_updates_device_and_pushes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.time import MAT_TIMES, ReefMatTimeEntity

    device = _FakeMatCoordinator()
    desc = MAT_TIMES[0]

    # Ensure entity starts with a real native value.
    device._data[(desc.value_name, False)] = 0

    ent = ReefMatTimeEntity(cast(Any, device), desc)

    wrote: list[bool] = []

    def _fake_write_state() -> None:
        wrote.append(True)

    monkeypatch.setattr(ent, "async_write_ha_state", _fake_write_state, raising=True)

    await ent.async_set_value(dt_time(1, 23))

    assert ent.native_value == dt_time(1, 23)
    assert device._set == [(desc.value_name, 4980)]
    assert device._listeners_called == 1
    assert wrote == [True]
    assert device.pushed == 1


@pytest.mark.asyncio
async def test_async_setup_entry_skips_non_mat_device() -> None:
    from custom_components.redsea.const import DOMAIN
    from custom_components.redsea.time import async_setup_entry

    class _Hass:
        def __init__(self) -> None:
            self.data: dict[str, dict[str, Any]] = {DOMAIN: {"entry": object()}}

    class _Entry:
        entry_id = "entry"

    added: list[Any] = []

    def _add(entities: list[Any], _update: bool) -> None:
        added.extend(entities)

    await async_setup_entry(cast(Any, _Hass()), cast(Any, _Entry()), cast(Any, _add))
    assert added == []


@pytest.mark.asyncio
async def test_async_setup_entry_adds_mat_time_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea.time as time_mod
    from custom_components.redsea.const import DOMAIN

    device = _FakeMatCoordinator()
    device._data[(time_mod.MAT_TIMES[0].value_name, False)] = 3600

    # Make the platform treat our fake as a ReefMatCoordinator for isinstance().
    monkeypatch.setattr(
        time_mod, "ReefMatCoordinator", _FakeMatCoordinator, raising=True
    )

    class _Hass:
        def __init__(self) -> None:
            self.data: dict[str, dict[str, Any]] = {DOMAIN: {"entry": device}}

    class _Entry:
        entry_id = "entry"

    added: list[Any] = []
    updates: list[bool] = []

    def _add(entities: list[Any], update_before_add: bool) -> None:
        added.extend(entities)
        updates.append(update_before_add)

    await time_mod.async_setup_entry(
        cast(Any, _Hass()), cast(Any, _Entry()), cast(Any, _add)
    )

    assert len(added) == 1
    assert updates == [True]
    assert isinstance(added[0], time_mod.ReefMatTimeEntity)


@pytest.mark.asyncio
async def test_async_added_to_hass_primes_and_calls_super_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea.time as time_mod

    device = _FakeMatCoordinator()
    desc = time_mod.MAT_TIMES[0]
    device._data[(desc.value_name, False)] = 3600
    device._data[(desc.value_name, True)] = 7200

    ent = time_mod.ReefMatTimeEntity(cast(Any, device), desc)

    super_added: list[bool] = []
    super_updated: list[bool] = []

    async def _fake_super_added(self: Any) -> None:
        super_added.append(True)

    def _fake_super_update(self: Any) -> None:
        super_updated.append(True)

    monkeypatch.setattr(
        time_mod.ReefBeatRestoreEntity,
        "async_added_to_hass",
        _fake_super_added,
        raising=True,
    )
    monkeypatch.setattr(
        time_mod.ReefBeatRestoreEntity,
        "_handle_coordinator_update",
        _fake_super_update,
        raising=True,
    )

    assert ent._attr_available is False
    assert ent.native_value == dt_time(1, 0)

    await ent.async_added_to_hass()

    assert super_added == [True]
    assert ent._attr_available is True
    assert ent.native_value == dt_time(2, 0)
    assert super_updated == [True]


def test_handle_coordinator_update_updates_and_calls_super(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea.time as time_mod

    device = _FakeMatCoordinator()
    desc = time_mod.MAT_TIMES[0]
    device._data[(desc.value_name, False)] = 0
    device._data[(desc.value_name, True)] = 1800

    ent = time_mod.ReefMatTimeEntity(cast(Any, device), desc)

    called: list[bool] = []

    def _fake_super(self: Any) -> None:
        called.append(True)

    monkeypatch.setattr(
        time_mod.ReefBeatRestoreEntity,
        "_handle_coordinator_update",
        _fake_super,
        raising=True,
    )

    ent._handle_coordinator_update()

    assert ent.native_value == dt_time(0, 30)
    assert called == [True]


def test_device_info_is_forwarded() -> None:
    from custom_components.redsea.time import MAT_TIMES, ReefMatTimeEntity

    device = _FakeMatCoordinator()
    desc = MAT_TIMES[0]
    device._data[(desc.value_name, False)] = 0

    ent = ReefMatTimeEntity(cast(Any, device), desc)
    assert ent.device_info == device.device_info
