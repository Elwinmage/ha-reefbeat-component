from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast

import pytest
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    last_update_success: bool = True
    device_info: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.device_info is None:
            self.device_info = {"identifiers": {("redsea", self.serial)}}

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        def _remove() -> None:
            return None

        return _remove

    def get_data(self, _path: str, _is_None_possible: bool = False) -> Any:  # noqa: N803
        return None


def test_get_value_missing_description_logs_and_returns_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from custom_components.redsea.binary_sensor import (
        ReefBeatBinarySensorEntity,
        ReefBeatBinarySensorEntityDescription,
    )

    desc = ReefBeatBinarySensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=None,
        value_name=None,
    )

    caplog.clear()
    ent = ReefBeatBinarySensorEntity(cast(Any, _FakeCoordinator()), desc)

    # Construction calls _get_value() and should log the error path.
    assert ent.is_on is None
    assert any("no value_fn or value_name" in rec.message for rec in caplog.records)


def test_coerce_bool_non_bool_truthy_becomes_true() -> None:
    from custom_components.redsea.binary_sensor import ReefBeatBinarySensorEntity

    assert ReefBeatBinarySensorEntity._coerce_bool(1) is True


def test_get_value_prefers_value_fn_over_value_name() -> None:
    from custom_components.redsea.binary_sensor import (
        ReefBeatBinarySensorEntity,
        ReefBeatBinarySensorEntityDescription,
    )

    desc = ReefBeatBinarySensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=lambda _d: True,
        value_name="$.ignored",
    )

    ent = ReefBeatBinarySensorEntity(cast(Any, _FakeCoordinator()), desc)
    assert ent.is_on is True


def test_get_value_uses_value_name_when_no_value_fn() -> None:
    from custom_components.redsea.binary_sensor import (
        ReefBeatBinarySensorEntity,
        ReefBeatBinarySensorEntityDescription,
    )

    class _Device(_FakeCoordinator):
        def get_data(self, path: str, _is_None_possible: bool = False) -> Any:  # noqa: N803
            assert path == "$.x"
            return False

    desc = ReefBeatBinarySensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=None,
        value_name="$.x",
    )

    ent = ReefBeatBinarySensorEntity(cast(Any, _Device()), desc)
    assert ent.is_on is False


@pytest.mark.asyncio
async def test_async_added_to_hass_restores_last_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.binary_sensor import (
        ReefBeatBinarySensorEntity,
        ReefBeatBinarySensorEntityDescription,
    )

    async def _noop(self: Any) -> None:
        return None

    monkeypatch.setattr(CoordinatorEntity, "async_added_to_hass", _noop, raising=True)
    monkeypatch.setattr(RestoreEntity, "async_added_to_hass", _noop, raising=True)

    desc = ReefBeatBinarySensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=lambda _d: None,
    )
    ent = ReefBeatBinarySensorEntity(cast(Any, _FakeCoordinator()), desc)

    class _State:
        state = "on"

    async def _get_last_state() -> _State:
        return _State()

    ent.async_get_last_state = cast(Any, _get_last_state)

    await ent.async_added_to_hass()

    assert ent.is_on is True


def test_handle_coordinator_update_sets_is_on_and_writes_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.binary_sensor import (
        ReefBeatBinarySensorEntity,
        ReefBeatBinarySensorEntityDescription,
    )

    desc = ReefBeatBinarySensorEntityDescription(
        key="x",
        translation_key="x",
        value_fn=lambda _d: True,
    )
    ent = ReefBeatBinarySensorEntity(cast(Any, _FakeCoordinator()), desc)

    wrote: list[bool] = []

    def _write() -> None:
        wrote.append(True)

    monkeypatch.setattr(ent, "async_write_ha_state", _write, raising=True)

    ent._handle_coordinator_update()

    assert ent.is_on is True
    assert wrote == [True]
