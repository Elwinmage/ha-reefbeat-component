from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast

import pytest
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.entity import ReefBeatRestoreEntity, RestoreSpec


@dataclass
class _FakeCoordinator:
    last_update_success: bool = True

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        def _remove() -> None:
            return None

        return _remove


@dataclass
class _State:
    state: str
    attributes: dict[str, Any]


@pytest.mark.asyncio
async def test_restore_entity_available_reflects_last_update_success() -> None:
    ok = _FakeCoordinator(last_update_success=True)
    bad = _FakeCoordinator(last_update_success=False)

    e_ok = ReefBeatRestoreEntity(cast(Any, ok))
    e_bad = ReefBeatRestoreEntity(cast(Any, bad))

    assert e_ok.available is True
    assert e_bad.available is False


@pytest.mark.asyncio
async def test_restore_entity_no_restore_spec_returns_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop(self: Any) -> None:
        return None

    monkeypatch.setattr(CoordinatorEntity, "async_added_to_hass", _noop)
    monkeypatch.setattr(RestoreEntity, "async_added_to_hass", _noop)

    ent = ReefBeatRestoreEntity(cast(Any, _FakeCoordinator()))

    async def _none() -> None:
        return None

    ent.async_get_last_state = cast(Any, _none)

    await ent.async_added_to_hass()


@pytest.mark.asyncio
async def test_restore_entity_skips_unknown_unavailable_or_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop(self: Any) -> None:
        return None

    monkeypatch.setattr(CoordinatorEntity, "async_added_to_hass", _noop)
    monkeypatch.setattr(RestoreEntity, "async_added_to_hass", _noop)

    ent = ReefBeatRestoreEntity(
        cast(Any, _FakeCoordinator()),
        restore=RestoreSpec("_attr_dummy", int),
    )

    # last_state None
    async def _none() -> None:
        return None

    ent.async_get_last_state = cast(Any, _none)
    await ent.async_added_to_hass()
    assert not hasattr(ent, "_attr_dummy")

    # unknown/unavailable
    async def _state_unknown() -> _State:
        return _State(state="unknown", attributes={})

    ent.async_get_last_state = cast(Any, _state_unknown)
    await ent.async_added_to_hass()
    assert not hasattr(ent, "_attr_dummy")

    async def _state_unavailable() -> _State:
        return _State(state="unavailable", attributes={})

    ent.async_get_last_state = cast(Any, _state_unavailable)
    await ent.async_added_to_hass()
    assert not hasattr(ent, "_attr_dummy")

    # parser error
    ent2 = ReefBeatRestoreEntity(
        cast(Any, _FakeCoordinator()),
        restore=RestoreSpec("_attr_dummy", lambda s: 1 / 0),
    )

    async def _state_ok() -> _State:
        return _State(state="12", attributes={})

    ent2.async_get_last_state = cast(Any, _state_ok)
    await ent2.async_added_to_hass()
    assert not hasattr(ent2, "_attr_dummy")


@pytest.mark.asyncio
async def test_restore_entity_sets_attribute_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop(self: Any) -> None:
        return None

    monkeypatch.setattr(CoordinatorEntity, "async_added_to_hass", _noop)
    monkeypatch.setattr(RestoreEntity, "async_added_to_hass", _noop)

    ent = ReefBeatRestoreEntity(
        cast(Any, _FakeCoordinator()),
        restore=RestoreSpec("_attr_dummy", int),
    )

    async def _state_ok() -> _State:
        return _State(state="12", attributes={})

    ent.async_get_last_state = cast(Any, _state_ok)

    await ent.async_added_to_hass()

    assert getattr(ent, "_attr_dummy") == 12
