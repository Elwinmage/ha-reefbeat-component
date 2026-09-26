"""A 12V port's schedule is polled only while the port is in schedule mode.

An uninstalled port (mode ``setup``) answers ``503`` to
``GET /port/<n>/schedule``, and a port that is on, off or probe-driven does
not use its schedule, so ``ReefControlAPI`` registers the source only for
ports in ``schedule`` mode, from ``/dashboard`` on polls and from
``/ports/config`` after a config fetch.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from custom_components.redsea.reefbeat.api import ReefBeatAPI
from custom_components.redsea.reefbeat.control import ReefControlAPI


def _api(dashboard_ports: Any = None, config_ports: Any = None) -> Any:
    api = ReefControlAPI.__new__(ReefControlAPI)
    sources: list[dict[str, Any]] = [
        {"name": "/dashboard", "type": "data", "data": {"probes": []}}
    ]
    if dashboard_ports is not None:
        sources[0]["data"]["ports"] = dashboard_ports
    if config_ports is not None:
        sources.append(
            {"name": "/ports/config", "type": "config", "data": config_ports}
        )
    api.data = {"sources": sources}
    api._data_db = {}
    api._base_url = "http://test"
    api.quick_refresh = None
    api._live_config_update = False
    return api


def _schedules(api: Any) -> list[str]:
    return sorted(
        s["name"]
        for s in api.data["sources"]
        if s["name"].startswith("/port/") and s["name"].endswith("/schedule")
    )


def test_only_ports_in_schedule_mode_are_polled() -> None:
    api = _api(
        dashboard_ports=[
            {"number": 0, "mode": "schedule"},
            {"number": 1, "mode": "setup"},
        ]
    )
    added = api._reconcile_port_schedule_sources(from_config=False)
    assert added == ["/port/0/schedule"]
    assert _schedules(api) == ["/port/0/schedule"]
    # Nothing new on a second pass
    assert api._reconcile_port_schedule_sources(from_config=False) == []


def test_a_port_leaving_schedule_mode_is_dropped() -> None:
    api = _api(dashboard_ports=[{"number": 0, "mode": "sensor"}])
    api.data["sources"].append(
        {"name": "/port/0/schedule", "type": "config", "data": {"intervals": []}}
    )
    assert api._reconcile_port_schedule_sources(from_config=False) == []
    assert _schedules(api) == []


def test_mode_source_depends_on_the_fetch() -> None:
    api = _api(
        dashboard_ports=[{"number": 0, "mode": "off"}],
        config_ports=[{"number": 0, "mode": "schedule"}],
    )
    assert api._port_modes(from_config=True) == {0: "schedule"}
    assert api._port_modes(from_config=False) == {0: "off"}


def test_modes_fall_back_and_skip_junk() -> None:
    # No dashboard ports yet: the config entries are used; the array index
    # stands in for a missing number; a non-integer number is ignored
    api = _api(config_ports=[{"mode": "schedule"}, "junk", {"number": "x"}])
    assert api._port_modes(from_config=False) == {0: "schedule"}
    assert _api()._port_modes(from_config=True) == {}


@pytest.mark.asyncio
async def test_fetch_config_fetches_new_schedules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api(config_ports=[{"number": 1, "mode": "schedule"}])
    base = AsyncMock()
    monkeypatch.setattr(ReefBeatAPI, "fetch_config", base)
    await api.fetch_config()
    assert [c.args for c in base.await_args_list] == [(None,), ("/port/1/schedule",)]
    # A targeted fetch does not reconcile
    base.reset_mock()
    await api.fetch_config("/ports/config")
    assert [c.args for c in base.await_args_list] == [("/ports/config",)]


@pytest.mark.asyncio
async def test_fetch_data_fetches_new_schedules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api(dashboard_ports=[{"number": 0, "mode": "schedule"}])
    monkeypatch.setattr(ReefBeatAPI, "fetch_data", AsyncMock(return_value={"ok": 1}))
    base = AsyncMock()
    monkeypatch.setattr(ReefBeatAPI, "fetch_config", base)
    assert await api.fetch_data() == {"ok": 1}
    base.assert_awaited_once_with("/port/0/schedule")
