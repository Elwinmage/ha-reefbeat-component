from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN

from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_register_static_paths(hass):
    """Test the registration of frontend resources and custom icons."""

    # 1. Setup the Mock HTTP object
    mock_http = MagicMock()
    mock_register = AsyncMock()
    mock_http.async_register_static_paths = mock_register

    # 2. Assign the mock to hass.http BEFORE running the setup
    # In some versions of HA tests, you must set it directly:
    hass.http = mock_http

    # 3. Patch the 'add_extra_js_url' function
    # Note: Ensure the path points to your actual __init__.py location
    with patch("custom_components.redsea.add_extra_js_url") as mock_add_js:
        # 4. Import and run your setup function
        from custom_components.redsea import async_setup

        # Create a mock ConfigEntry (required for async_setup_entry)
        mock_entry = MagicMock()
        mock_entry.domain = DOMAIN
        mock_entry.entry_id = "test_entry"

        # Execute the function
        assert hass.http
        await async_setup(hass, mock_entry)

        # 5. Debugging: If this still fails, print hass.http to see if it's None
        # print(f"DEBUG: hass.http is {hass.http}")

        # 6. Assertions
        # Verify the registration method was actually called
        assert mock_register.called, (
            "The method async_register_static_paths was never called!"
        )

        # Verify specific arguments
        args = mock_register.call_args[0][0]  # Get the list of StaticPathConfig
        assert args[0].url_path == f"/{DOMAIN}/frontend"

        # Verify the JS icon registration
        assert mock_add_js.called
        assert mock_add_js.call_args[0][1].endswith("icons.js")


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


@pytest.mark.asyncio
async def test_migrate_head_device_names_updates_registry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    import custom_components.redsea as redsea_init

    entry = MockConfigEntry(domain=redsea_init.DOMAIN, title="Dose", data={})
    entry.add_to_hass(hass)

    updated: list[tuple[str, str]] = []

    class _FakeRegistry:
        def async_update_device(self, device_id: str, *, name: str) -> None:
            updated.append((device_id, name))

    fake_registry = _FakeRegistry()

    devices = [
        SimpleNamespace(id="d1", name="MyDose_head_2", name_by_user=None),
        SimpleNamespace(id="d2", name="Other", name_by_user=None),
        SimpleNamespace(id="d3", name="MyDose head 3", name_by_user=None),
        SimpleNamespace(id="d4", name="User_head_1", name_by_user="custom"),
        SimpleNamespace(id="d5", name="Bad_head_x", name_by_user=None),
    ]

    monkeypatch.setattr(redsea_init.dr, "async_get", lambda _h: fake_registry)
    monkeypatch.setattr(
        redsea_init.dr,
        "async_entries_for_config_entry",
        lambda _reg, _entry_id: devices,
    )

    await redsea_init._migrate_head_device_names(hass, cast(Any, entry))

    assert ("d1", "MyDose head 2") in updated
    assert all(did != "d2" for did, _name in updated)
    assert all(did != "d4" for did, _name in updated)


@pytest.mark.asyncio
async def test_services_clean_message_and_request_handlers(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    import custom_components.redsea as redsea_init

    handlers: dict[str, Any] = {}

    def _async_register(
        self: Any,
        domain: str,
        service: str,
        service_func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        handlers[f"{domain}.{service}"] = service_func

    monkeypatch.setattr(
        type(hass.services), "async_register", _async_register, raising=True
    )

    assert await redsea_init.async_setup(hass, {}) is True

    clean = handlers[f"{redsea_init.DOMAIN}.clean_message"]

    hass.data.setdefault(redsea_init.DOMAIN, {})
    resp = await clean(SimpleNamespace(data={"device_id": "missing"}))
    assert resp == {"error": "Device not enabled"}

    called: list[Any] = []

    class _Device:
        def clean_message(self, msg_type: Any) -> None:
            called.append(msg_type)

    hass.data[redsea_init.DOMAIN]["dev"] = _Device()
    resp2 = await clean(SimpleNamespace(data={"device_id": "dev", "msg_type": "All"}))
    assert resp2 is None
    assert called == ["All"]

    req = handlers[f"{redsea_init.DOMAIN}.request"]
    bad = await req(SimpleNamespace(data={"device_id": 123}))
    assert bad == {"error": "Invalid device_id"}
