from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN


@pytest.mark.parametrize(
    "entry_fixture",
    ["local_ato_config_entry", "local_mat_config_entry", "local_dose_config_entry"],
)
async def test_setup_and_unload_local_entries(
    hass: HomeAssistant, request: pytest.FixtureRequest, entry_fixture: str
) -> None:
    """Each local config entry should set up and unload cleanly."""
    entry: MockConfigEntry = request.getfixturevalue(entry_fixture)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Coordinator is stored under hass.data[DOMAIN][entry_id]
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_setup_cloud_entry(
    hass: HomeAssistant,
    cloud_config_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud entry should set up and expose aquarium/device payloads in coordinator data."""
    from custom_components.redsea.reefbeat.cloud import ReefBeatCloudAPI

    async def _fake_cloud_connect(self: ReefBeatCloudAPI) -> None:
        self._token = "test-token"
        self._header = {"Authorization": "Bearer test-token"}

    monkeypatch.setattr(ReefBeatCloudAPI, "connect", _fake_cloud_connect, raising=True)

    cloud_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(cloud_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][cloud_config_entry.entry_id]

    aquariums = coordinator.get_data("$.sources[?(@.name=='/aquarium')].data", True)
    devices = coordinator.get_data("$.sources[?(@.name=='/device')].data", True)

    assert isinstance(aquariums, list)
    assert len(cast(list[Any], aquariums)) >= 1
    assert isinstance(devices, list)
    assert len(cast(list[Any], devices)) >= 1


@pytest.mark.asyncio
async def test_async_setup_entry_returns_false_when_building_coordinator_fails(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea as integration

    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "1.2.3.4", "hw_model": "X"}
    )

    def _boom(_hass: Any, _entry: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(integration, "_build_coordinator", _boom, raising=True)

    assert await integration.async_setup_entry(hass, cast(Any, entry)) is False


@pytest.mark.asyncio
async def test_async_setup_entry_returns_false_when_coordinator_async_setup_fails(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea as integration

    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "1.2.3.4", "hw_model": "X"}
    )

    class _Coordinator:
        async def async_setup(self) -> None:
            raise RuntimeError("setup failed")

    monkeypatch.setattr(
        integration, "_build_coordinator", lambda _h, _e: _Coordinator()
    )

    assert await integration.async_setup_entry(hass, cast(Any, entry)) is False


@pytest.mark.asyncio
async def test_update_listener_triggers_reload(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea as integration

    called: list[str] = []

    async def _reload(entry_id: str) -> None:
        called.append(entry_id)

    monkeypatch.setattr(hass.config_entries, "async_reload", _reload, raising=True)

    entry = MockConfigEntry(domain=DOMAIN)
    await integration.update_listener(hass, cast(Any, entry))

    assert called == [entry.entry_id]


@pytest.mark.asyncio
async def test_async_unload_entry_returns_false_when_platform_unload_fails(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea as integration

    async def _unload_platforms(_entry: Any, _platforms: Any) -> bool:
        return False

    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", _unload_platforms, raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN)
    assert await integration.async_unload_entry(hass, cast(Any, entry)) is False


@pytest.mark.asyncio
async def test_request_service_returns_error_on_exception_and_on_empty_response(
    hass: HomeAssistant,
) -> None:
    import custom_components.redsea as integration

    await integration.async_setup(hass, {})

    class _API:
        async def http_get(self, _path: str) -> Any:
            raise RuntimeError("boom")

    class _Device:
        title = "MyDevice"
        my_api = _API()

    hass.data.setdefault(DOMAIN, {})["dev"] = _Device()

    resp = await hass.services.async_call(
        DOMAIN,
        "request",
        {"device_id": "dev", "access_path": "/x", "method": "get"},
        blocking=True,
        return_response=True,
    )
    assert resp == {"error": "request failed"}

    class _API2:
        async def http_get(self, _path: str) -> Any:
            return None

    class _Device2:
        title = "Title2"
        my_api = _API2()

    hass.data[DOMAIN]["dev2"] = _Device2()

    resp2 = await hass.services.async_call(
        DOMAIN,
        "request",
        {"device_id": "dev2", "access_path": "/x", "method": "get"},
        blocking=True,
        return_response=True,
    )
    assert resp2 == {"error": "can not access to device Title2"}
