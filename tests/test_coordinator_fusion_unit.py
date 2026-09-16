"""Unit tests for the temperature-fusion surface on the coordinators.

`ReefControlCoordinator` grows a whole fusion/coherence subsystem on top of the
raw ``/dashboard`` probes (candidates, history, anomaly attribution, fused
value, rich attributes) plus per-probe calibration/maintenance delegation.
`ReefPowerCoordinator` carries the simpler local-probe temperature helpers.

The fusion logic is driven through a *real* ``ReefControlAPI`` (built without
network I/O) so the JSONPath reads/writes exercise the same engine as
production; the thin delegation methods are checked against a mock API.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.redsea.coordinator import (
    ReefControlCoordinator,
    ReefPowerCoordinator,
)
from custom_components.redsea.reefbeat import fusion
from custom_components.redsea.reefbeat.control import ReefControlAPI

# ---------------------------------------------------------------------------
# Builders (no HA / no network)
# ---------------------------------------------------------------------------


def _control_with_real_api(
    probes: list[dict[str, Any]],
    method: str = fusion.DEFAULT_METHOD,
    threshold: float = fusion.DEFAULT_THRESHOLD,
) -> ReefControlCoordinator:
    """A ReefControlCoordinator backed by a real (offline) ReefControlAPI.

    The coordinator's inherited get_data/set_data resolve real JSONPaths against
    the API's ``data`` bag, so fusion methods run exactly as in production.
    """
    api = ReefControlAPI.__new__(ReefControlAPI)
    api.data = {
        "sources": [{"name": "/dashboard", "data": {"probes": probes}}],
        "local": {"fusion": {"method": method, "threshold": threshold}},
    }
    api._data_db = {}
    api._base_url = "http://test"

    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = api
    coord._temp_history = {}
    coord._temp_history_last = 0.0
    coord._probe_maintenance = set()
    coord.port_count = 2
    coord._listeners = {}  # async_update_listeners -> no-op
    return coord


def _control_with_mock_api() -> tuple[Any, MagicMock]:
    """A ReefControlCoordinator whose API and refresh are mocks (delegation)."""
    api = MagicMock()
    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = api
    coord.async_request_refresh = AsyncMock()
    return coord, api


def _temp(uid: str, value: float | None, status: str = "connected") -> dict[str, Any]:
    return {
        "type": "temperature",
        "uid": uid,
        "name": uid,
        "value": value,
        "status": status,
    }


# ---------------------------------------------------------------------------
# _probes / fusion_method / fusion_threshold
# ---------------------------------------------------------------------------


def test_probes_returns_list_and_empty_fallback() -> None:
    coord = _control_with_real_api([_temp("a", 25.0)])
    assert [p["uid"] for p in coord._probes()] == ["a"]

    # Missing/malformed probes -> empty list.
    empty = _control_with_real_api([])
    empty.my_api.data["sources"][0]["data"]["probes"] = "not-a-list"
    assert empty._probes() == []


def test_fusion_method_valid_and_fallback() -> None:
    coord = _control_with_real_api([], method="mean")
    assert coord.fusion_method() == "mean"
    coord.set_data("$.local.fusion.method", "bogus")
    assert coord.fusion_method() == fusion.DEFAULT_METHOD


def test_fusion_threshold_valid_and_fallback() -> None:
    coord = _control_with_real_api([], threshold=0.8)
    assert coord.fusion_threshold() == 0.8
    coord.set_data("$.local.fusion.threshold", "not-a-number")
    assert coord.fusion_threshold() == fusion.DEFAULT_THRESHOLD


# ---------------------------------------------------------------------------
# maintenance flag surface
# ---------------------------------------------------------------------------


def test_probe_maintenance_toggle_and_listing() -> None:
    coord = _control_with_real_api([_temp("a", 25.0), _temp("b", 25.2)])
    assert coord.probe_in_maintenance("a") is False

    coord.set_probe_maintenance("a", True)
    assert coord.probe_in_maintenance("a") is True
    assert coord.temperature_maintenance_uids() == ["a"]

    # Candidate 'a' is tagged, excluded from the active set/sources.
    cands = {c["uid"]: c for c in coord.temperature_candidates()}
    assert cands["a"]["maintenance"] is True
    assert {c["uid"] for c in coord._active_candidates()} == {"b"}
    assert {c["uid"] for c in coord.temperature_sources()} == {"b"}

    coord.set_probe_maintenance("a", False)
    assert coord.probe_in_maintenance("a") is False
    assert coord.temperature_maintenance_uids() == []


def test_temperature_source_count_includes_maintenance() -> None:
    coord = _control_with_real_api([_temp("a", 25.0), _temp("b", 25.2)])
    coord.set_probe_maintenance("a", True)
    # Count is over all candidates (maintenance included) so entities still exist.
    assert coord.temperature_source_count() == 2
    # ...but only one *usable* source remains.
    assert len(coord.temperature_sources()) == 1


# ---------------------------------------------------------------------------
# history recording & pruning
# ---------------------------------------------------------------------------


def test_record_history_debounce_prune_and_uidless_skip() -> None:
    # One valued probe with a uid, one available reading with no uid (skipped).
    probes = [
        _temp("a", 25.0),
        {"type": "temperature", "name": "nouid", "value": 25.1, "status": "connected"},
    ]
    coord = _control_with_real_api(probes)

    t0 = 1_000_000.0
    coord._record_history(now=t0)
    assert coord._temp_history["a"] == [(t0, 25.0)]
    assert None not in coord._temp_history  # uid-less source not recorded

    # Within 20s -> debounced: no new sample appended.
    coord._record_history(now=t0 + 5)
    assert coord._temp_history["a"] == [(t0, 25.0)]

    # Far in the future -> old sample pruned out; uid dropped when empty.
    coord._record_history(now=t0 + fusion.HISTORY_WINDOW_S + 100)
    assert "a" in coord._temp_history  # a fresh sample was just added
    assert all(
        t >= t0 + fusion.HISTORY_WINDOW_S + 100 - fusion.HISTORY_WINDOW_S
        for (t, _v) in coord._temp_history["a"]
    )


def test_prune_history_drops_aged_out_uid() -> None:
    # A uid whose only samples fall outside the window is removed entirely
    # (the probe went away, so no fresh sample replaces them).
    coord = _control_with_real_api([])
    coord._temp_history = {"gone": [(0.0, 25.0)]}
    coord._prune_history(now=fusion.HISTORY_WINDOW_S + 10)
    assert "gone" not in coord._temp_history


# ---------------------------------------------------------------------------
# fused value / spread / incoherence / anomaly state
# ---------------------------------------------------------------------------


def test_fusion_temperature_and_spread_coherent() -> None:
    coord = _control_with_real_api(
        [_temp("a", 25.0), _temp("b", 25.2), _temp("c", 25.1)], method="median"
    )
    assert coord.fusion_temperature() == 25.1
    assert round(coord.temperature_spread() or 0.0, 3) == 0.2
    assert coord.temperature_incoherent() is False
    assert coord.temperature_anomaly_state() == "ok"


def test_temperature_incoherent_none_below_two_sources() -> None:
    coord = _control_with_real_api([_temp("a", 25.0)])
    assert coord.temperature_incoherent() is None


def test_anomaly_state_unknown_when_unattributable() -> None:
    # Two probes disagree, no history to attribute -> incoherent but "unknown".
    coord = _control_with_real_api([_temp("a", 24.0), _temp("b", 26.0)])
    assert coord.temperature_incoherent() is True
    assert coord.temperature_anomaly_state() == "unknown"


def test_anomaly_state_names_structural_culprit() -> None:
    # A disconnected probe is a structural culprit even while the rest agree.
    probes = [
        _temp("a", 25.0),
        _temp("b", 25.1),
        _temp("bad", None, status="disconnected"),
    ]
    coord = _control_with_real_api(probes)
    state = coord.temperature_anomaly_state()
    assert "bad" in state


def test_fusion_attributes_shape() -> None:
    probes = [
        _temp("a", 25.0),
        _temp("b", 25.2),
        _temp("svc", 25.1),
    ]
    coord = _control_with_real_api(probes)
    coord.set_probe_maintenance("svc", True)
    attrs = coord.fusion_attributes()

    assert attrs["count"] == 3
    assert attrs["available"] == 2  # svc excluded by maintenance
    assert attrs["maintenance_probes"] == ["svc"]
    assert set(attrs["source_names"]) == {"a", "b", "svc"}
    assert attrs["fused"] is not None
    assert attrs["method"] == fusion.DEFAULT_METHOD
    assert attrs["threshold"] == fusion.DEFAULT_THRESHOLD
    # change_1h is None on first observation (single sample per source).
    assert all(s["change_1h"] is None for s in attrs["sources"])


# ---------------------------------------------------------------------------
# probe calibration / maintenance delegation (mock API)
# ---------------------------------------------------------------------------


def test_probe_offset_delegation() -> None:
    coord, api = _control_with_mock_api()
    api.probe_offset.return_value = 0.3
    assert coord.probe_offset("uid") == 0.3
    api.probe_offset.assert_called_once_with("uid")


@pytest.mark.asyncio
async def test_set_and_reset_probe_offset_refresh() -> None:
    coord, api = _control_with_mock_api()
    api.set_probe_offset = AsyncMock()
    api.reset_probe_offset = AsyncMock()

    await coord.set_probe_offset("uid", 0.4)
    api.set_probe_offset.assert_awaited_once_with("uid", 0.4)

    await coord.reset_probe_offset("uid")
    api.reset_probe_offset.assert_awaited_once_with("uid")
    assert coord.async_request_refresh.await_count == 2


def test_list_probes_filters_invalid() -> None:
    probes = [
        {"type": "ph", "uid": "0xP", "name": "pH"},
        {"type": "temperature", "uid": "0xT"},  # name falls back to uid
        {"type": "ec"},  # no uid -> skipped
        "garbage",  # non-dict -> skipped
    ]
    coord = _control_with_real_api(probes)
    listed = coord.list_probes()
    assert {p["uid"] for p in listed} == {"0xP", "0xT"}
    assert next(p for p in listed if p["uid"] == "0xT")["name"] == "0xT"


def test_list_probes_non_list_returns_empty() -> None:
    coord = _control_with_real_api([])
    coord.my_api.data["sources"][0]["data"]["probes"] = None
    assert coord.list_probes() == []


@pytest.mark.asyncio
async def test_install_probe_success_and_failure() -> None:
    coord, api = _control_with_mock_api()

    api.install_probe = AsyncMock(
        return_value={"json": {"uid": "0xNEW", "success": True}}
    )
    assert await coord.async_install_probe("ph") == "0xNEW"

    # Nothing paired -> None; also covers the non-dict result branch.
    api.install_probe = AsyncMock(return_value=None)
    assert await coord.async_install_probe("ph") is None


@pytest.mark.asyncio
async def test_delete_probe_refreshes() -> None:
    coord, api = _control_with_mock_api()
    api.delete_probe = AsyncMock()
    await coord.async_delete_probe("ph", "0xP")
    api.delete_probe.assert_awaited_once_with("ph", "0xP")
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_probe_buzzer_notify_enabled_delegation() -> None:
    coord, api = _control_with_mock_api()
    api.set_probe_buzzer = AsyncMock()
    api.set_probe_notify = AsyncMock()
    api.set_probe_enabled = AsyncMock()
    api.buzzer_path.return_value = "$.buzzer"
    api.notify_path.return_value = "$.notify"
    api.get_data.side_effect = lambda path, is_None_possible=False: {
        "$.buzzer": True,
        "$.notify": False,
    }[path]

    await coord.set_probe_buzzer("ph", "0xP", True)
    api.set_probe_buzzer.assert_awaited_once_with("ph", "0xP", True)

    await coord.set_probe_notify("ph", "0xP", False)
    api.set_probe_notify.assert_awaited_once_with("ph", "0xP", False)

    assert coord.probe_buzzer("ph", "0xP") is True
    assert coord.probe_notify("ph", "0xP") is False

    await coord.set_probe_enabled("ph", "0xP", True)
    api.set_probe_enabled.assert_awaited_once_with("ph", "0xP", True)


# ---------------------------------------------------------------------------
# ReefPowerCoordinator local-temperature helpers
# ---------------------------------------------------------------------------


def _power_with_mock_api() -> tuple[Any, MagicMock]:
    api = MagicMock()
    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = api
    coord.async_request_refresh = AsyncMock()
    return coord, api


def test_power_has_local_temperature() -> None:
    coord, api = _power_with_mock_api()
    api.get_data.return_value = 25.0
    assert coord.has_local_temperature() is True
    api.get_data.return_value = None
    assert coord.has_local_temperature() is False


def test_power_temperature_offset_delegation() -> None:
    coord, api = _power_with_mock_api()
    api.temperature_offset.return_value = -0.2
    assert coord.temperature_offset() == -0.2


@pytest.mark.asyncio
async def test_power_temperature_offset_writes_refresh() -> None:
    coord, api = _power_with_mock_api()
    api.set_temperature_offset = AsyncMock()
    api.reset_temperature_offset = AsyncMock()
    api.install_temperature = AsyncMock()
    api.remove_temperature = AsyncMock()

    await coord.set_temperature_offset(0.5)
    api.set_temperature_offset.assert_awaited_once_with(0.5)

    await coord.reset_temperature_offset()
    api.reset_temperature_offset.assert_awaited_once()

    await coord.async_install_temperature()
    api.install_temperature.assert_awaited_once()

    await coord.async_remove_temperature()
    api.remove_temperature.assert_awaited_once()

    assert coord.async_request_refresh.await_count == 4
