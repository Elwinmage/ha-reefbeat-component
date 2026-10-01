from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN


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

    # Unload the entry so the coordinator's Debouncer timer is cancelled before teardown.
    assert await hass.config_entries.async_unload(cloud_config_entry.entry_id)
    await hass.async_block_till_done()


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
async def test_async_setup_entry_not_ready_when_coordinator_async_setup_fails(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea as integration

    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "1.2.3.4", "hw_model": "X"}
    )

    class _Coordinator:
        async def async_setup(self) -> None:
            raise RuntimeError("Initialization failed, is your device on?")

    monkeypatch.setattr(
        integration, "_build_coordinator", lambda _h, _e: _Coordinator()
    )

    # Unreachable device: Home Assistant retries the setup with backoff.
    with pytest.raises(ConfigEntryNotReady, match="is your device on"):
        await integration.async_setup_entry(hass, cast(Any, entry))


@pytest.mark.asyncio
async def test_async_setup_entry_returns_false_on_cloud_invalid_auth(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea as integration
    from custom_components.redsea.reefbeat.cloud import InvalidAuth

    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "1.2.3.4", "hw_model": "X"}
    )

    class _Coordinator:
        async def async_setup(self) -> None:
            raise InvalidAuth("bad credentials")

    monkeypatch.setattr(
        integration, "_build_coordinator", lambda _h, _e: _Coordinator()
    )

    # Wrong credentials: no retry loop.
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


@pytest.mark.asyncio
async def test_get_control_probes_service_handler(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """redsea.get_control_probes looks a RSCONTROL hub up by hwid — not a
    Home Assistant device_id, since the RSPower card only knows the paired
    hub's hardware id (from its own connected_device.hwid).
    """
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
    handler = handlers[f"{redsea_init.DOMAIN}.get_control_probes"]

    class _StubControl:
        def __init__(self, hwid: str, probes: Any) -> None:
            self.model_id = hwid
            self._probes = probes

        def get_data(self, _path: str, is_None_possible: bool = False) -> Any:
            return self._probes

    monkeypatch.setattr(redsea_init, "ReefControlCoordinator", _StubControl)

    probes = [
        {"type": "ph", "uid": "0x00B39", "name": "pH", "value": 8.13},
        {"type": "orp", "uid": "0x0071F", "name": "ORP", "value": 161},
    ]
    hass.data.setdefault(redsea_init.DOMAIN, {})
    hass.data[redsea_init.DOMAIN]["ctl"] = _StubControl("d4e9f4e89208", probes)
    # A non-ReefControlCoordinator entry (e.g. an unrelated RSPower/cloud
    # coordinator sharing hass.data[DOMAIN]) must be skipped, not matched.
    hass.data[redsea_init.DOMAIN]["other"] = object()

    resp = await handler(SimpleNamespace(data={"hwid": "d4e9f4e89208"}))
    assert resp == {"hwid": "d4e9f4e89208", "probes": probes}

    # Unknown hwid.
    resp2 = await handler(SimpleNamespace(data={"hwid": "unknown"}))
    assert resp2 == {"error": "No RSCONTROL hub found for hwid 'unknown'"}

    # Missing/blank hwid.
    resp3 = await handler(SimpleNamespace(data={}))
    assert resp3 == {"error": "hwid is required"}

    # Probes data present but not a list (e.g. dashboard not yet fetched,
    # still the "" placeholder) -> an empty list, not a crash.
    hass.data[redsea_init.DOMAIN]["ctl2"] = _StubControl("hwid2", "")
    resp4 = await handler(SimpleNamespace(data={"hwid": "hwid2"}))
    assert resp4 == {"hwid": "hwid2", "probes": []}


@pytest.mark.asyncio
async def test_get_control_subscriptions_service_handler(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """redsea.get_control_subscriptions reads the hub's socket rules live
    (GET /subscription-info), addressed by hwid like get_control_probes.
    """
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
    handler = handlers[f"{redsea_init.DOMAIN}.get_control_subscriptions"]

    class _StubControl:
        def __init__(self, hwid: str, result: Any) -> None:
            self.model_id = hwid
            self.my_api = SimpleNamespace(http_get=AsyncMock(return_value=result))

    monkeypatch.setattr(redsea_init, "ReefControlCoordinator", _StubControl)

    external = [
        {
            "number": 1,
            "type": "temperature",
            "uid": "0x000F7",
            "sensor": "value",
            "is_above": True,
            "value": 26.5,
            "hysteresis": 0.2,
            "trigger_op": "on",
            "last_sock_op": "off",
        }
    ]
    internal = [{"number": 1, "type": "ato"}]
    ok = _StubControl(
        "hub1",
        {
            "ok": True,
            "status": 200,
            "json": {"external": external, "internal": internal},
        },
    )
    hass.data.setdefault(redsea_init.DOMAIN, {})
    hass.data[redsea_init.DOMAIN]["ctl"] = ok
    hass.data[redsea_init.DOMAIN]["other"] = object()

    # Nominal: both rule lists returned, read live from the hub.
    resp = await handler(SimpleNamespace(data={"hwid": "hub1"}))
    assert resp == {"hwid": "hub1", "external": external, "internal": internal}
    ok.my_api.http_get.assert_awaited_once_with("/subscription-info")

    # Missing/blank hwid.
    assert await handler(SimpleNamespace(data={})) == {"error": "hwid is required"}
    assert await handler(SimpleNamespace(data={"hwid": ""})) == {
        "error": "hwid is required"
    }

    # Unknown hwid.
    assert await handler(SimpleNamespace(data={"hwid": "nope"})) == {
        "error": "No RSCONTROL hub found for hwid 'nope'"
    }

    # Request raising.
    boom = _StubControl("hub2", None)
    boom.my_api.http_get.side_effect = RuntimeError("down")
    hass.data[redsea_init.DOMAIN]["ctl2"] = boom
    assert await handler(SimpleNamespace(data={"hwid": "hub2"})) == {
        "error": "request failed"
    }

    # Failed request, no answer, or a non-dict payload.
    for i, result in enumerate(
        (
            {"ok": False, "status": 503},
            None,
            {"ok": True, "status": 200, "json": ["not", "a", "dict"]},
        )
    ):
        hwid = f"bad{i}"
        hass.data[redsea_init.DOMAIN][hwid] = _StubControl(hwid, result)
        assert await handler(SimpleNamespace(data={"hwid": hwid})) == {
            "error": f"can not read the subscriptions of hub '{hwid}'"
        }

    # Lists missing or malformed -> empty lists, not a crash.
    hass.data[redsea_init.DOMAIN]["partial"] = _StubControl(
        "partial", {"ok": True, "json": {"external": "x"}}
    )
    assert await handler(SimpleNamespace(data={"hwid": "partial"})) == {
        "hwid": "partial",
        "external": [],
        "internal": [],
    }


@pytest.mark.asyncio
async def test_led_convert_service_handler(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """redsea.led_convert converts G1 points with the lamp's own API."""
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
    handler = handlers[f"{redsea_init.DOMAIN}.led_convert"]

    class _Api:
        def kelvin_to_white_and_blue(self, kelvin: Any, intensity: int) -> Any:
            return {
                "kelvin": kelvin,
                "intensity": intensity,
                "white": 100,
                "blue": 0,
                "moon": 1,
            }

        def white_and_blue_to_kelvin(self, white: Any, blue: Any) -> Any:
            return {"kelvin": 23000, "intensity": 100, "white": white, "blue": blue}

    class _G1(redsea_init.ReefLedCoordinator):
        def __init__(self) -> None:  # no HA setup needed
            self.my_api = _Api()

    class _G2(redsea_init.ReefLedG2Coordinator):
        def __init__(self) -> None:
            self.my_api = _Api()

    hass.data.setdefault(redsea_init.DOMAIN, {})
    hass.data[redsea_init.DOMAIN]["g1"] = _G1()
    hass.data[redsea_init.DOMAIN]["g2"] = _G2()

    resp = await handler(
        SimpleNamespace(
            data={
                "device_id": "g1",
                "points": [
                    {"kelvin": 9000, "intensity": 50},
                    {"kelvin": 12000},
                    {"white": 10, "blue": 100},
                    "junk",
                ],
            }
        )
    )
    assert resp == {
        "points": [
            {"kelvin": 9000, "intensity": 50, "white": 100, "blue": 0},
            {"kelvin": 12000, "intensity": 100, "white": 100, "blue": 0},
            {"kelvin": 23000, "intensity": 100, "white": 10, "blue": 100},
            {},
        ]
    }

    bad = await handler(SimpleNamespace(data={"device_id": "g1", "points": "x"}))
    assert bad == {"error": "points must be a list"}
    for device_id in ("g2", "unknown"):
        resp2 = await handler(SimpleNamespace(data={"device_id": device_id}))
        assert resp2 == {"error": "Not a G1 ReefLED"}


@pytest.mark.asyncio
async def test_led_library_service_handlers(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """redsea.led_library lists and redsea.led_library_save adds programs."""
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
    listing = handlers[f"{redsea_init.DOMAIN}.led_library"]
    saving = handlers[f"{redsea_init.DOMAIN}.led_library_save"]

    saved: list[tuple[str, Any, Any]] = []
    updated: list[str | None] = []
    deleted: list[str] = []

    class _Led(redsea_init.ReefLedCoordinator):
        def __init__(self, linked: bool) -> None:  # no HA setup needed
            self._linked_to_cloud = linked

        def library_link(self) -> Any:
            return ("cloud", "aq") if self._linked_to_cloud else None

        def light_library(self) -> Any:
            if not self._linked_to_cloud:
                return None
            return [
                {"uid": "u1", "name": "Perso", "default": False},
                {"uid": "rs", "name": "23K", "default": True},
            ]

        async def save_light_program(
            self, name: str, program: Any, clouds: Any, uid: str | None = None
        ) -> str | None:
            saved.append((name, program, clouds))
            updated.append(uid)
            return uid or "new-uid"

        async def delete_light_program(self, uid: str) -> bool:
            deleted.append(uid)
            return True

    hass.data.setdefault(redsea_init.DOMAIN, {})
    hass.data[redsea_init.DOMAIN]["linked"] = _Led(True)
    hass.data[redsea_init.DOMAIN]["alone"] = _Led(False)

    def call(data: dict[str, Any]) -> Any:
        return SimpleNamespace(data=data)

    assert await listing(call({"device_id": "linked"})) == {
        "linked": True,
        "programs": [
            {"uid": "u1", "name": "Perso", "default": False},
            {"uid": "rs", "name": "23K", "default": True},
        ],
    }
    assert await listing(call({"device_id": "alone"})) == {
        "linked": False,
        "programs": [],
    }
    assert await listing(call({"device_id": "nope"})) == {"error": "Not a ReefLED"}

    prog = {"white": {"rise": 600, "set": 1200, "points": []}}
    assert await saving(
        call({"device_id": "linked", "name": " prog-1 ", "program": prog})
    ) == {"uid": "new-uid"}
    assert saved[-1] == ("prog-1", prog, None)
    clouds = {"from": 700, "to": 800, "intensity": "Low"}
    await saving(
        call({"device_id": "linked", "name": "p", "program": prog, "clouds": clouds})
    )
    assert saved[-1] == ("p", prog, clouds)

    for data, error in (
        ({"device_id": "nope"}, "Not a ReefLED"),
        ({"device_id": "linked", "name": " ", "program": prog}, "name is required"),
        (
            {"device_id": "linked", "name": "p", "program": []},
            "program must be an object",
        ),
        (
            {"device_id": "alone", "name": "p", "program": prog},
            "Not linked to a ReefBeat cloud account",
        ),
    ):
        assert await saving(call(data)) == {"error": error}
    assert len(saved) == 2

    # Update one of the user's programs; not a Red Sea one
    assert await saving(
        call({"device_id": "linked", "name": "P2", "program": prog, "uid": "u1"})
    ) == {"uid": "u1"}
    assert updated[-1] == "u1"
    for uid, error in (
        (12, "uid must be a string"),
        ("zz", "Program not found"),
        ("rs", "Red Sea programs cannot be edited"),
    ):
        assert await saving(
            call({"device_id": "linked", "name": "p", "program": prog, "uid": uid})
        ) == {"error": error}
    assert len(saved) == 3

    deleting = handlers[f"{redsea_init.DOMAIN}.led_library_delete"]
    assert await deleting(call({"device_id": "linked", "uid": "u1"})) == {
        "deleted": True
    }
    assert deleted == ["u1"]
    for data, error in (
        ({"device_id": "nope"}, "Not a ReefLED"),
        ({"device_id": "alone", "uid": "u1"}, "Not linked to a ReefBeat cloud account"),
        ({"device_id": "linked"}, "uid is required"),
        ({"device_id": "linked", "uid": "zz"}, "Program not found"),
        ({"device_id": "linked", "uid": "rs"}, "Red Sea programs cannot be deleted"),
    ):
        assert await deleting(call(data)) == {"error": error}
    assert deleted == ["u1"]


@pytest.mark.asyncio
async def test_led_weather_setup_nightly_run_and_service(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ReefLED gets its weather store, a nightly run and a service."""
    import custom_components.redsea as integration

    class _Led(integration.ReefLedCoordinator):
        def __init__(self) -> None:  # no HA setup needed
            pass

        async def async_setup(self) -> None:
            return None

    led = _Led()
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "1.2.3.4", "hw_model": "RSLED160"}
    )
    entry.add_to_hass(hass)
    # What a lamp needs to find its group (none here)
    led._hass = hass  # type: ignore[attr-defined]
    led._entry = entry  # type: ignore[attr-defined]
    monkeypatch.setattr(integration, "_build_coordinator", lambda _h, _e: led)
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    ticks: list[Any] = []

    def _track(_hass: Any, action: Any, **when: Any) -> Any:
        ticks.append((action, when))
        return lambda: None

    monkeypatch.setattr(integration, "async_track_time_change", _track)
    runs: list[Any] = []

    async def _run(_hass: Any, device: Any) -> Any:
        runs.append(device)
        return {"status": "ok"}

    monkeypatch.setattr(integration, "run_weather", _run)
    shows: list[Any] = []

    async def _show(_hass: Any, device: Any) -> Any:
        shows.append(device)
        return {"status": "ok"}

    monkeypatch.setattr(integration, "publish_weather", _show)

    later: list[Any] = []

    def _call_later(_hass: Any, delay: float, action: Any) -> Any:
        cancelled: list[bool] = []
        later.append((delay, action, cancelled))
        return lambda: cancelled.append(True)

    monkeypatch.setattr(integration, "async_call_later", _call_later)

    assert await integration.async_setup_entry(hass, cast(Any, entry)) is True
    store = led.weather  # type: ignore[attr-defined]
    assert isinstance(store, integration.WeatherStore)
    action, when = ticks[0]
    assert when == {"hour": 0, "minute": 10, "second": 0}
    # Nothing in standard mode
    action(None)
    await hass.async_block_till_done()
    assert runs == []
    # Weather mode, never fetched: due
    await store.async_set_mode(True, {})
    action(None)
    await hass.async_block_till_done()
    assert runs == [led]
    # Fetched today: not due before refresh_days
    store.last_success = integration.dt_util.now().date().isoformat()
    action(None)
    await hass.async_block_till_done()
    assert runs == [led]
    # A lamp of a group: its group runs the weather (the lamp's own store,
    # even due, is left)
    store.last_success = None
    hass.data[DOMAIN]["group"] = SimpleNamespace(
        member_ids=[entry.entry_id], _weather=object()
    )
    action(None)
    await hass.async_block_till_done()
    assert runs == [led]
    del hass.data[DOMAIN]["group"]
    store.last_success = integration.dt_util.now().date().isoformat()

    # Changed settings: the new week shown at once, sent once they settle
    await store.async_set("location", "1, 2")
    await store.async_set("max_intensity", 80)
    assert [d for d, _, _ in later] == [1, 30, 1, 30]
    assert later[0][2] == [True] and later[1][2] == [True]  # put off
    later[2][1](None)
    await hass.async_block_till_done()
    assert shows == [led]
    assert runs == [led]
    later[3][1](None)
    await hass.async_block_till_done()
    assert runs == [led, led]
    # A change pending at unload is dropped
    await store.async_set("min_intensity", 5)
    assert later[4][2] == [] and later[5][2] == []
    await entry._async_process_on_unload(hass)  # pyright: ignore[reportAttributeAccessIssue]
    assert later[4][2] == [True] and later[5][2] == [True]

    # The service
    handlers: dict[str, Any] = {}

    def _async_register(
        self: Any, domain: str, service: str, func: Any, *a: Any, **k: Any
    ) -> None:
        handlers[service] = func

    monkeypatch.setattr(type(hass.services), "async_register", _async_register)
    assert await integration.async_setup(hass, {}) is True
    apply = handlers["led_weather_apply"]
    assert await apply(SimpleNamespace(data={"device_id": entry.entry_id})) == {
        "status": "ok"
    }
    assert await apply(SimpleNamespace(data={"device_id": "nope"})) == {
        "error": "Not a ReefLED"
    }

    # The preview writes nothing: its own function
    async def _preview(hass: Any, dev: Any, settings: Any = None) -> Any:
        return {"status": "ok", "days": [], "standard": {}}

    monkeypatch.setattr(integration, "preview_weather", _preview)
    preview = handlers["led_weather_preview"]
    assert (await preview(SimpleNamespace(data={"device_id": entry.entry_id})))[
        "standard"
    ] == {}
    assert await preview(SimpleNamespace(data={"device_id": "nope"})) == {
        "error": "Not a ReefLED"
    }
    seen: list[Any] = []

    async def _preview2(hass: Any, dev: Any, settings: Any = None) -> Any:
        seen.append(settings)
        return {}

    monkeypatch.setattr(integration, "preview_weather", _preview2)
    await preview(
        SimpleNamespace(
            data={"device_id": entry.entry_id, "settings": {"anchor": "both"}}
        )
    )
    await preview(SimpleNamespace(data={"device_id": entry.entry_id, "settings": "x"}))
    assert seen == [{"anchor": "both"}, None]

    saved: list[Any] = []

    async def _save(
        hass: Any, dev: Any, settings: Any, enabled: bool, wait: bool
    ) -> Any:
        saved.append((settings, enabled, wait))
        return {"status": "ok"}

    monkeypatch.setattr(integration, "save_weather", _save)
    save = handlers["led_weather_save"]
    await save(
        SimpleNamespace(
            data={
                "device_id": entry.entry_id,
                "settings": {"period": "last_week"},
                "enabled": True,
            }
        )
    )
    await save(SimpleNamespace(data={"device_id": entry.entry_id}))
    assert saved == [({"period": "last_week"}, True, False), (None, False, False)]
    assert await save(SimpleNamespace(data={"device_id": "nope"})) == {
        "error": "Not a ReefLED"
    }
