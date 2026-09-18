"""Tests for the RSPOWER socket-config control surface.

Covers the endpoints reverse-engineered from the ReefBeat app traffic:

- ``ReefPowerAPI.set_socket_mode``   → ``PUT /sockets/config``
- ``ReefPowerAPI.set_socket_schedule`` → ``PUT /socket/<n>/config/schedule``
- ``ReefPowerAPI.setup_finish``      → ``POST /setup-finish``
- the ``/sockets/config`` source registration
- ``ReefPowerCoordinator`` delegating methods (call API + refresh)
- the automatic "leave setup mode" trigger, which replaced the manual
  "Finish setup" button (see ``ReefPowerCoordinator._maybe_finish_setup``)
- the ``socket_N_mode`` sensor's ``schedule``/``sensor_config`` attributes

Mode selection itself (off/on/schedule/sensor) and the sensor-mode threshold
config (``/subscribe`` + ``/temperature/subscribe``) are configured from
ha-reef-card via the generic ``redsea.request`` service, not from an HA
entity — there is no select entity here to test.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import (
    DOMAIN,
)
from tests._switch_test_fakes import FakePowerCoordinator

# ===========================================================================
# ReefPowerAPI write methods
# ===========================================================================


def _make_api() -> Any:
    """Build a ReefPowerAPI with a stub session and a recording http_send."""
    from custom_components.redsea.reefbeat.power import ReefPowerAPI

    api = ReefPowerAPI("10.0.0.9", False, cast(Any, MagicMock(name="session")))
    api.http_send = AsyncMock(return_value=None)  # type: ignore[method-assign]
    return api


def test_sockets_config_source_registered() -> None:
    """The API registers /sockets/config so socket modes/names are readable."""
    api = _make_api()
    names = [s.get("name") for s in api.data["sources"]]
    assert "/sockets/config" in names
    assert "/configuration" in names


@pytest.mark.asyncio
async def test_set_socket_mode_puts_partial_sockets_config() -> None:
    """set_socket_mode sends only the changed socket to /sockets/config."""
    api = _make_api()
    await api.set_socket_mode(2, "schedule")
    api.http_send.assert_awaited_once_with(
        "/sockets/config", {"sockets": [{"mode": "schedule", "number": 2}]}, "put"
    )


@pytest.mark.asyncio
async def test_set_socket_mode_includes_name_when_renaming() -> None:
    """A name is only included when explicitly renaming the socket."""
    api = _make_api()
    await api.set_socket_mode(0, "off", name="t1")
    api.http_send.assert_awaited_once_with(
        "/sockets/config",
        {"sockets": [{"mode": "off", "number": 0, "name": "t1"}]},
        "put",
    )


@pytest.mark.asyncio
async def test_set_socket_schedule_puts_intervals() -> None:
    """set_socket_schedule targets the per-socket schedule endpoint."""
    api = _make_api()
    intervals = [{"time": 0, "duration": 539}, {"time": 1320, "duration": 119}]
    await api.set_socket_schedule(2, intervals)
    api.http_send.assert_awaited_once_with(
        "/socket/2/config/schedule", {"intervals": intervals}, "put"
    )


@pytest.mark.asyncio
async def test_setup_finish_posts_empty_body() -> None:
    """setup_finish POSTs /setup-finish with an empty JSON body."""
    api = _make_api()
    await api.setup_finish()
    api.http_send.assert_awaited_once_with("/setup-finish", {}, "post")


# ===========================================================================
# ReefPowerCoordinator delegating methods
# ===========================================================================


def _make_coordinator() -> Any:
    """Build a ReefPowerCoordinator without running __init__ (no aiohttp session).

    The delegating methods only touch ``self.my_api`` and
    ``self.async_request_refresh``, so we bypass the network-touching
    constructor and wire those two attributes directly.
    """
    from custom_components.redsea.coordinator import ReefPowerCoordinator

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock(
        set_socket_mode=AsyncMock(),
        set_socket_schedule=AsyncMock(),
        setup_finish=AsyncMock(),
    )
    coord.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    return coord


@pytest.mark.asyncio
async def test_coordinator_set_socket_schedule_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    intervals = [{"time": 0, "duration": 1439}]
    await coord.set_socket_schedule(1, intervals)
    coord.my_api.set_socket_schedule.assert_awaited_once_with(1, intervals)
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_setup_finish_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    await coord.setup_finish()
    coord.my_api.setup_finish.assert_awaited_once()
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_set_socket_name_sends_current_mode_with_name() -> None:
    """Renaming resends the socket's current mode alongside the new name."""
    coord = _make_coordinator()
    coord.get_data = MagicMock(return_value="schedule")  # type: ignore[method-assign]
    await coord.set_socket_name(2, "reactor")
    coord.my_api.set_socket_mode.assert_awaited_once_with(2, "schedule", name="reactor")
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_set_socket_name_falls_back_to_off_when_in_setup() -> None:
    """If the current mode isn't writable (e.g. 'setup'), fall back to 'off'."""
    coord = _make_coordinator()
    coord.get_data = MagicMock(return_value="setup")  # type: ignore[method-assign]
    await coord.set_socket_name(0, "t1")
    coord.my_api.set_socket_mode.assert_awaited_once_with(0, "off", name="t1")


@pytest.mark.asyncio
async def test_coordinator_set_socket_name_keeps_sensor_mode() -> None:
    """Renaming a "sensor"-mode socket must not silently kick it back to
    "off" — that would drop its threshold binding for no reason.
    """
    coord = _make_coordinator()
    coord.get_data = MagicMock(return_value="sensor")  # type: ignore[method-assign]
    await coord.set_socket_name(1, "chauffage")
    coord.my_api.set_socket_mode.assert_awaited_once_with(1, "sensor", name="chauffage")


# ===========================================================================
# Automatic setup-finish (replaces the old manual button)
# ===========================================================================


@pytest.mark.asyncio
async def test_maybe_finish_setup_triggers_when_a_socket_leaves_setup() -> None:
    """Main mode is still "setup" but one socket has been configured away
    from "setup" -> /finish-setup is called.
    """
    from custom_components.redsea.coordinator import ReefPowerCoordinator
    from custom_components.redsea.reefbeat.power import ReefPowerAPI

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock(spec=ReefPowerAPI, setup_finish=AsyncMock())
    coord.get_data = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda path, is_None_possible=False: {
            "$.sources[?(@.name=='/dashboard')].data.mode": "setup",
            "$.sources[?(@.name=='/dashboard')].data.sockets": [
                {"number": 0, "mode": "setup"},
                {"number": 1, "mode": "on"},  # just configured
            ],
        }[path]
    )

    await coord._maybe_finish_setup()
    coord.my_api.setup_finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_finish_setup_noop_while_all_sockets_still_setup() -> None:
    """Nothing configured yet -> no call, regardless of main mode."""
    from custom_components.redsea.coordinator import ReefPowerCoordinator
    from custom_components.redsea.reefbeat.power import ReefPowerAPI

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock(spec=ReefPowerAPI, setup_finish=AsyncMock())
    coord.get_data = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda path, is_None_possible=False: {
            "$.sources[?(@.name=='/dashboard')].data.mode": "setup",
            "$.sources[?(@.name=='/dashboard')].data.sockets": [
                {"number": 0, "mode": "setup"},
                {"number": 1, "mode": "setup"},
            ],
        }[path]
    )

    await coord._maybe_finish_setup()
    coord.my_api.setup_finish.assert_not_awaited()


@pytest.mark.asyncio
async def test_maybe_finish_setup_noop_once_already_auto() -> None:
    """Main mode already left "setup" -> nothing to do."""
    from custom_components.redsea.coordinator import ReefPowerCoordinator
    from custom_components.redsea.reefbeat.power import ReefPowerAPI

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock(spec=ReefPowerAPI, setup_finish=AsyncMock())
    coord.get_data = MagicMock(return_value="auto")  # type: ignore[method-assign]

    await coord._maybe_finish_setup()
    coord.my_api.setup_finish.assert_not_awaited()


@pytest.mark.asyncio
async def test_maybe_finish_setup_tolerates_missing_sockets_list() -> None:
    """A malformed/missing sockets list must not raise."""
    from custom_components.redsea.coordinator import ReefPowerCoordinator
    from custom_components.redsea.reefbeat.power import ReefPowerAPI

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock(spec=ReefPowerAPI, setup_finish=AsyncMock())
    coord.get_data = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda path, is_None_possible=False: {
            "$.sources[?(@.name=='/dashboard')].data.mode": "setup",
            "$.sources[?(@.name=='/dashboard')].data.sockets": None,
        }[path]
    )

    await coord._maybe_finish_setup()
    coord.my_api.setup_finish.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_update_data_runs_auto_finish_and_swallows_its_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_async_update_data() calls the check after every refresh, and a
    failure in that check must never break the refresh itself.
    """
    from custom_components.redsea import coordinator as coordinator_module
    from custom_components.redsea.coordinator import ReefPowerCoordinator

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord._title = "pwr"

    async def _base_update() -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(
        coordinator_module.ReefBeatCloudLinkedCoordinator,
        "_async_update_data",
        AsyncMock(side_effect=_base_update),
    )
    coord._maybe_finish_setup = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]

    result = await coord._async_update_data()
    assert result == {"ok": True}
    coord._maybe_finish_setup.assert_awaited_once()


# ===========================================================================
# Switch friendly name = socket name
# ===========================================================================


def _make_switch(device: FakePowerCoordinator, socket_idx: int) -> Any:
    import custom_components.redsea.switch as switch_platform

    desc = switch_platform.ReefPowerSocketSwitchEntityDescription(
        key=f"socket_{socket_idx}_on_off",
        translation_key="socket_on_off",
        translation_placeholders={"socket": str(socket_idx + 1)},
        icon="mdi:power-plug",
        icon_off="mdi:power-plug-off",
        socket=socket_idx,
    )
    entity = switch_platform.ReefPowerSocketSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    return entity


def _name_path(idx: int) -> str:
    return f"$.sources[?(@.name=='/dashboard')].data.sockets[{idx}].name"


def test_switch_name_uses_socket_name() -> None:
    device = FakePowerCoordinator()
    device.get_data_map[_name_path(0)] = "t1"
    entity = _make_switch(device, 0)
    assert entity.name == "t1"


def test_switch_name_falls_back_when_unnamed() -> None:
    device = FakePowerCoordinator()
    device.get_data_map[_name_path(3)] = None
    entity = _make_switch(device, 3)
    assert entity.name == "Socket 4"


# ===========================================================================
# Per-socket name text entity
# ===========================================================================


def _make_name_text(device: FakePowerCoordinator, socket_idx: int) -> Any:
    import custom_components.redsea.text as text_platform

    desc = text_platform.ReefPowerSocketNameTextEntityDescription(
        key=f"socket_{socket_idx}_name",
        translation_key="socket_name",
        translation_placeholders={"socket": str(socket_idx + 1)},
        value_name=_name_path(socket_idx),
        socket=socket_idx,
    )
    entity = text_platform.ReefPowerSocketNameTextEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    return entity


def test_name_text_reads_current_name() -> None:
    device = FakePowerCoordinator()
    device.get_data_map[_name_path(2)] = "reactor"
    entity = _make_name_text(device, 2)
    assert entity.native_value == "reactor"


@pytest.mark.asyncio
async def test_name_text_set_value_calls_set_socket_name() -> None:
    device = FakePowerCoordinator()
    entity = _make_name_text(device, 4)
    await entity.async_set_value("skimmer")
    assert device.name_calls == [(4, "skimmer")]
    assert entity.native_value == "skimmer"


@pytest.mark.asyncio
async def test_text_setup_entry_creates_one_name_per_socket(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    import custom_components.redsea.text as text_platform

    class _PowerDevice(FakePowerCoordinator):
        pass

    monkeypatch.setattr(
        text_platform, "ReefPowerCoordinator", _PowerDevice, raising=True
    )

    device = _PowerDevice(socket_count=6)
    device.hass = hass
    entry = MockConfigEntry(domain=DOMAIN, title="pwr", unique_id="pwr")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []

    def _add(new: Any, _update: bool = False) -> None:
        added.extend(list(new))

    await text_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    keys = {e.entity_description.key for e in added}
    # One name per socket, plus the (always-created) local temperature probe
    # name field.
    assert keys == {f"socket_{i}_name" for i in range(6)} | {"temperature_probe_name"}


# ===========================================================================
# socket_N_mode sensor: schedule + sensor_config attributes
# ===========================================================================


def test_socket_mode_sensor_carries_schedule_and_sensor_config_attributes() -> None:
    """The socket_N_mode sensor's mode travels with two attributes: its
    on/off programme (``schedule``, unconditionally present) and, once the
    socket is bound to the local temperature probe's sensor mode, the
    threshold rule (``sensor_config``) — mirroring the existing schedule
    pattern so a card reads both without a request of its own.
    """
    import custom_components.redsea.sensor as sensor_platform

    socket_idx = 1
    base = f"$.sources[?(@.name=='/dashboard')].data.sockets[{socket_idx}]"
    schedule_path = f"$.sources[?(@.name=='/socket/{socket_idx}/config/schedule')].data"
    subscription_path = (
        "$.sources[?(@.name=='/temperature/subscriptions')]"
        f".data.sockets[?(@.number=={socket_idx})]"
    )

    desc = sensor_platform.ReefBeatSensorEntityDescription(
        key=f"socket_{socket_idx}_mode",
        translation_key=f"socket_{socket_idx}_mode",
        value_fn=lambda d, p=f"{base}.mode": d.get_data(p, is_None_possible=True),
        attributes_fn=lambda d, i=socket_idx, sched=schedule_path: {
            "schedule": d.get_data(sched),
            "sensor_config": d.get_data(
                "$.sources[?(@.name=='/temperature/subscriptions')]"
                f".data.sockets[?(@.number=={i})]",
                is_None_possible=True,
            ),
        },
    )

    device = FakePowerCoordinator()
    device.get_data_map[f"{base}.mode"] = "sensor"
    device.get_data_map[schedule_path] = {"intervals": [{"time": 0, "duration": 1439}]}
    device.get_data_map[subscription_path] = {
        "sensor": {"default_state": False, "app_cache": "temperature"},
        "value": 24.2,
        "is_above": True,
        "turn_on": False,
    }

    entity = sensor_platform.ReefBeatSensorEntity(cast(Any, device), desc)
    entity._update_val()

    assert entity.native_value == "sensor"
    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["schedule"] == {"intervals": [{"time": 0, "duration": 1439}]}
    assert attrs["sensor_config"] == {
        "sensor": {"default_state": False, "app_cache": "temperature"},
        "value": 24.2,
        "is_above": True,
        "turn_on": False,
    }


def test_socket_mode_sensor_sensor_config_absent_without_probe() -> None:
    """No local temperature probe (source not reconciled in) -> sensor_config
    reads None quietly, not an error-logged crash.
    """
    import custom_components.redsea.sensor as sensor_platform

    socket_idx = 0
    base = f"$.sources[?(@.name=='/dashboard')].data.sockets[{socket_idx}]"
    schedule_path = f"$.sources[?(@.name=='/socket/{socket_idx}/config/schedule')].data"

    desc = sensor_platform.ReefBeatSensorEntityDescription(
        key=f"socket_{socket_idx}_mode",
        translation_key=f"socket_{socket_idx}_mode",
        value_fn=lambda d, p=f"{base}.mode": d.get_data(p, is_None_possible=True),
        attributes_fn=lambda d, i=socket_idx, sched=schedule_path: {
            "schedule": d.get_data(sched),
            "sensor_config": d.get_data(
                "$.sources[?(@.name=='/temperature/subscriptions')]"
                f".data.sockets[?(@.number=={i})]",
                is_None_possible=True,
            ),
        },
    )

    device = FakePowerCoordinator()
    device.get_data_map[f"{base}.mode"] = "schedule"
    device.get_data_map[schedule_path] = {"intervals": []}
    # /temperature/subscriptions simply absent from get_data_map.

    entity = sensor_platform.ReefBeatSensorEntity(cast(Any, device), desc)
    entity._update_val()

    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["schedule"] == {"intervals": []}
    assert attrs["sensor_config"] is None
