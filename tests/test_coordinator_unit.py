from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)
from custom_components.redsea.coordinator import (
    ReefBeatCloudLinkedCoordinator,
    ReefBeatCoordinator,
)


@dataclass
class _FakeAPI:
    """Small fake API surface for coordinator unit tests."""

    get_data_map: dict[str, Any] = field(default_factory=dict)
    fetch_data_result: dict[str, Any] | None = field(default_factory=dict)
    fetch_data_exc: BaseException | None = None

    _timeout: int = 1
    quick_refresh: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    async def fetch_data(self) -> dict[str, Any] | None:
        if self.fetch_data_exc is not None:
            raise self.fetch_data_exc
        return self.fetch_data_result

    async def fetch_config(self, config_path: str | None = None) -> None:
        return None

    async def get_initial_data(self) -> None:
        return None

    async def push_values(self, source: str, method: str = "put", *args: Any) -> None:
        return None

    async def press(self, action: str, *args: Any) -> None:
        return None

    async def delete(self, source: str) -> None:
        return None

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value


def _make_entry(*, title: str, ip: str, hw_model: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={
            CONFIG_FLOW_IP_ADDRESS: ip,
            CONFIG_FLOW_HW_MODEL: hw_model,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
    )


@dataclass
class _FakeCloudCoordinator:
    title: str = "CloudAccount"
    _title: str = "CloudAccount"
    listened: list[tuple[str | None, str]] = field(default_factory=list)

    async def listen_for_firmware(self, url: str | None, device_title: str) -> None:
        self.listened.append((url, device_title))


class _Event:
    def __init__(self, data: dict[str, Any]):
        self.data = data


@pytest.mark.asyncio
async def test_coordinator_async_update_data_none_raises(hass: HomeAssistant) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    coordinator.my_api = cast(Any, _FakeAPI(fetch_data_result=None))

    with pytest.raises(UpdateFailed, match="No data received from API"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_async_update_data_timeout_wraps(hass: HomeAssistant) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    coordinator.my_api = cast(Any, _FakeAPI(fetch_data_exc=asyncio.TimeoutError()))

    with pytest.raises(UpdateFailed, match=r"update failed: TimeoutError"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_async_update_data_generic_exception_wraps(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    coordinator.my_api = cast(Any, _FakeAPI(fetch_data_exc=ValueError("boom")))

    with pytest.raises(UpdateFailed, match=r"update failed: ValueError: boom"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_serial_property_returns_title(hass: HomeAssistant) -> None:
    entry = _make_entry(title="MyDevice", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))
    assert coordinator.serial == "MyDevice"


@pytest.mark.asyncio
async def test_cloud_linked_handle_ask_for_link_calls_ask(hass: HomeAssistant) -> None:
    entry = _make_entry(title="MyDevice", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCloudLinkedCoordinator(hass, cast(Any, entry))

    called: list[bool] = []

    def _fake_ask_for_link() -> None:
        called.append(True)

    coordinator._ask_for_link = _fake_ask_for_link  # type: ignore[assignment]
    coordinator._handle_ask_for_link(_Event({}))  # type: ignore[attr-defined]
    assert called == [True]


@pytest.mark.asyncio
async def test_coordinator_update_fetch_config_and_actions(hass: HomeAssistant) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    class _RecordingAPI(_FakeAPI):
        def __init__(self) -> None:
            super().__init__()
            self.fetched = 0
            self.configs: list[str | None] = []
            self.pushed: list[tuple[str, str]] = []
            self.pressed: list[str] = []
            self.deleted: list[str] = []
            self.data = {"k": 1}

        async def fetch_data(self) -> dict[str, Any] | None:
            self.fetched += 1
            return {}

        async def fetch_config(self, config_path: str | None = None) -> None:
            self.configs.append(config_path)

        async def push_values(
            self, source: str, method: str = "put", *args: Any
        ) -> None:
            self.pushed.append((source, method))

        async def press(self, action: str, *args: Any) -> None:
            self.pressed.append(action)

        async def delete(self, source: str) -> None:
            self.deleted.append(source)

    api = _RecordingAPI()
    coordinator.my_api = cast(Any, api)

    called = 0

    def _fake_update_listeners() -> None:
        nonlocal called
        called += 1

    coordinator.async_update_listeners = _fake_update_listeners  # type: ignore[assignment]

    await coordinator.update()
    assert api.fetched == 1

    await coordinator.fetch_config("/x")
    assert api.configs == ["/x"]
    assert called == 1

    await coordinator.push_values("/configuration", "put")
    await coordinator.press("do")
    await coordinator.delete("/preview")
    assert api.pushed == [("/configuration", "put")]
    assert api.pressed == ["do"]
    assert api.deleted == ["/preview"]

    assert coordinator.data_exist("k") is True
    assert coordinator.data_exist("missing") is False


@pytest.mark.asyncio
async def test_coordinator_async_setup_calls_get_initial_data_once(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    class _RecordingAPI(_FakeAPI):
        def __init__(self) -> None:
            super().__init__()
            self.initial = 0

        async def get_initial_data(self) -> None:
            self.initial += 1

    api = _RecordingAPI()
    coordinator.my_api = cast(Any, api)

    await coordinator.async_setup()
    await coordinator.async_setup()
    assert api.initial == 1


@pytest.mark.asyncio
async def test_async_request_refresh_wait_calls_sleep_and_super(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    sleeps: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    called = 0

    async def _fake_super_refresh(self: DataUpdateCoordinator[Any]) -> None:
        nonlocal called
        called += 1

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep, raising=True)
    monkeypatch.setattr(
        DataUpdateCoordinator,
        "async_request_refresh",
        _fake_super_refresh,
        raising=True,
    )

    await coordinator.async_request_refresh(wait=2)

    assert sleeps == [2]
    assert called == 1


@pytest.mark.asyncio
async def test_async_quick_request_refresh_sets_quick_refresh_and_calls_super(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    fake_api = _FakeAPI()
    coordinator.my_api = cast(Any, fake_api)

    called = 0

    async def _fake_super_refresh(self: DataUpdateCoordinator[Any]) -> None:
        nonlocal called
        called += 1

    async def _fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep, raising=True)
    monkeypatch.setattr(
        DataUpdateCoordinator,
        "async_request_refresh",
        _fake_super_refresh,
        raising=True,
    )

    await coordinator.async_request_refresh("/dashboard", wait=1)

    assert fake_api.quick_refresh == "/dashboard"
    assert called == 1


@pytest.mark.asyncio
async def test_async_request_refresh_with_config_fetches_config(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    class _RecordingAPI(_FakeAPI):
        def __init__(self) -> None:
            super().__init__()
            self.configs: list[str | None] = []

        async def fetch_config(self, config_path: str | None = None) -> None:
            self.configs.append(config_path)

    fake_api = _RecordingAPI()
    coordinator.my_api = cast(Any, fake_api)

    async def _fake_sleep(_: float) -> None:
        return None

    called = 0

    async def _fake_super_refresh(self: DataUpdateCoordinator[Any]) -> None:
        nonlocal called
        called += 1

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep, raising=True)
    monkeypatch.setattr(
        DataUpdateCoordinator,
        "async_request_refresh",
        _fake_super_refresh,
        raising=True,
    )

    await coordinator.async_request_refresh("/configuration", config=True, wait=1)

    assert fake_api.quick_refresh == "/configuration"
    assert fake_api.configs == [None]
    assert called == 1


@pytest.mark.asyncio
async def test_clean_message_updates_listeners(hass: HomeAssistant) -> None:
    entry = _make_entry(title="Test", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    called: list[str] = []

    class _MsgAPI(_FakeAPI):
        def clean_message(self, msg_type: str) -> None:
            called.append(msg_type)

    coordinator.my_api = cast(Any, _MsgAPI())

    updated = 0

    def _listener() -> None:
        nonlocal updated
        updated += 1

    coordinator.async_add_listener(_listener)
    coordinator.clean_message("last_message")

    assert called == ["last_message"]
    assert updated == 1


@pytest.mark.asyncio
async def test_device_info_properties_and_fallbacks(hass: HomeAssistant) -> None:
    entry = _make_entry(title="My Device", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefBeatCoordinator(hass, cast(Any, entry))

    fake = _FakeAPI(
        get_data_map={
            # model_id: prefer hwid; treat "null" as missing and fall back to /.uuid
            "$.sources[?(@.name=='/device-info')].data.hwid": "null",
            "$.sources[?(@.name=='/')].data.uuid": "uuid-123",
            # model/hw/sw
            "$.sources[?(@.name=='/device-info')].data.hw_model": "RSLED50",
            "$.sources[?(@.name=='/device-info')].data.hw_revision": None,
            "$.sources[?(@.name=='/firmware')].data.chip_version": "chip-v",
            "$.sources[?(@.name=='/firmware')].data.version": None,
            # board/framework default when falsey
            "$.sources[?(@.name=='/firmware')].data.board": "",
            "$.sources[?(@.name=='/firmware')].data.framework": None,
        }
    )
    coordinator.my_api = cast(Any, fake)

    assert coordinator.model_id == "uuid-123"
    assert coordinator.board == "esp32"
    assert coordinator.framework == "i"
    assert coordinator.hw_version == "chip-v"
    assert coordinator.sw_version == "unknown"

    device_info = coordinator.device_info
    assert (DOMAIN, "uuid-123") in cast(
        set[tuple[str, str]], device_info.get("identifiers")
    )
    assert device_info.get("model") == "RSLED50"

    assert coordinator.detected_id == "192.0.2.10 RSLED50 My Device"
    assert coordinator.unload() is None


@pytest.mark.asyncio
async def test_cloud_link_builds_firmware_url_and_listens(
    hass: HomeAssistant,
) -> None:
    class _TestLinked(ReefBeatCloudLinkedCoordinator):
        pass

    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    device = _TestLinked(hass, cast(Any, entry))

    device.my_api = cast(
        Any,
        _FakeAPI(
            get_data_map={
                "$.sources[?(@.name=='/firmware')].data.board": "esp32",
                "$.sources[?(@.name=='/firmware')].data.framework": "i",
            }
        ),
    )

    cloud = _FakeCloudCoordinator(title="MyCloud")
    await device.set_cloud_link(cast(Any, cloud))

    assert device.latest_firmware_url == (
        "/firmware/api/reef-lights/latest?board=esp32&framework=i"
    )
    assert cloud.listened == [(device.latest_firmware_url, "LED")]
    assert device.cloud_link() == "MyCloud"


@pytest.mark.asyncio
async def test_get_model_type_mapping_and_unknown(hass: HomeAssistant) -> None:
    class _TestLinked(ReefBeatCloudLinkedCoordinator):
        pass

    entry = _make_entry(title="X", ip="192.0.2.10", hw_model="RSLED50")
    device = _TestLinked(hass, cast(Any, entry))

    assert device.get_model_type("RSLED50") == "reef-lights"
    assert device.get_model_type("RSDOSE4") == "reef-dosing"
    assert device.get_model_type("RSMAT") == "reef-mat"
    assert device.get_model_type("RSATO+") == "reef-ato"
    assert device.get_model_type("RSRUN") == "reef-run"
    assert device.get_model_type("RSWAVE25") == "reef-wave"
    assert device.get_model_type("NOT_A_MODEL") is None


@pytest.mark.asyncio
async def test_cloud_link_unknown_model_type_sets_no_url(
    hass: HomeAssistant,
) -> None:
    class _TestLinked(ReefBeatCloudLinkedCoordinator):
        pass

    entry = _make_entry(title="X", ip="192.0.2.10", hw_model="NOT_A_MODEL")
    device = _TestLinked(hass, cast(Any, entry))
    device.my_api = cast(Any, _FakeAPI(get_data_map={}))

    cloud = _FakeCloudCoordinator(title="MyCloud")
    await device.set_cloud_link(cast(Any, cloud))

    assert device.latest_firmware_url is None
    assert cloud.listened == [(None, "X")]


@pytest.mark.asyncio
async def test_cloud_link_ready_off_event_clears_link(
    hass: HomeAssistant,
) -> None:
    class _TestLinked(ReefBeatCloudLinkedCoordinator):
        pass

    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    device = _TestLinked(hass, cast(Any, entry))
    device.my_api = cast(Any, _FakeAPI())

    cloud = _FakeCloudCoordinator(title="MyCloud")
    await device.set_cloud_link(cast(Any, cloud))
    assert device.cloud_coordinator is not None

    device._handle_ask_for_link_ready(_Event({"state": "off", "account": "MyCloud"}))
    assert device.cloud_coordinator is None
    assert device.cloud_link() == "None"


@pytest.mark.asyncio
async def test_cloud_linked_async_setup_requests_link_when_running(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _TestLinked(ReefBeatCloudLinkedCoordinator):
        pass

    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    device = _TestLinked(hass, cast(Any, entry))

    initial = 0

    async def _get_initial_data() -> None:
        nonlocal initial
        initial += 1

    device.my_api = cast(Any, _FakeAPI())
    device.my_api.get_initial_data = _get_initial_data  # type: ignore[method-assign]

    asked: list[bool] = []

    def _ask() -> None:
        asked.append(True)

    monkeypatch.setattr(device, "_ask_for_link", _ask, raising=True)

    listens: list[str] = []

    def _fake_listen(self: Any, event_type: str, listener: Any) -> Any:
        listens.append(event_type)
        return lambda: None

    monkeypatch.setattr(type(hass.bus), "async_listen", _fake_listen, raising=True)

    hass.state = "RUNNING"  # type: ignore[assignment]
    await device.async_setup()

    assert initial == 1
    assert asked == [True]
    assert "redsea_ask_for_cloud_link_ready" in listens


@pytest.mark.asyncio
async def test_cloud_link_ready_non_off_event_asks_for_link(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _TestLinked(ReefBeatCloudLinkedCoordinator):
        pass

    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    device = _TestLinked(hass, cast(Any, entry))

    asked: list[bool] = []

    def _ask() -> None:
        asked.append(True)

    monkeypatch.setattr(device, "_ask_for_link", _ask, raising=True)

    device._handle_ask_for_link_ready(_Event({"state": "on"}))
    assert asked == [True]


@pytest.mark.asyncio
async def test_ask_for_link_fires_bus_event(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _TestLinked(ReefBeatCloudLinkedCoordinator):
        pass

    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    device = _TestLinked(hass, cast(Any, entry))

    fired: list[tuple[str, dict[str, Any]]] = []

    def _fake_fire(
        self: Any, event_type: str, event_data: dict[str, Any] | None = None
    ) -> None:
        fired.append((event_type, dict(event_data or {})))

    monkeypatch.setattr(type(hass.bus), "fire", _fake_fire, raising=True)

    device._ask_for_link()
    assert fired == [("redsea_ask_for_cloud_link", {"device_id": entry.entry_id})]


def test_device_info_helpers_include_via_device_and_skip_non_str(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    import custom_components.redsea.coordinator as coord

    monkeypatch.setattr(coord, "async_get_clientsession", lambda _h: object())

    class _DoseAPI:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            self.data: dict[str, Any] = {"sources": []}

        async def fetch_data(self) -> dict[str, Any] | None:
            return {}

        async def fetch_config(self, _config_path: str | None = None) -> None:
            return None

        async def get_initial_data(self) -> None:
            return None

        def get_data(self, _name: str, _is_None_possible: bool = False) -> Any:  # noqa: N803
            return None

        def set_data(self, _name: str, _value: Any) -> None:
            return None

    monkeypatch.setattr(coord, "ReefDoseAPI", _DoseAPI)

    class _RunAPI(_DoseAPI):
        async def push_values(self, *_a: Any, **_k: Any) -> None:
            return None

    monkeypatch.setattr(coord, "ReefRunAPI", _RunAPI)

    class _CloudAPI(_DoseAPI):
        async def connect(self) -> None:
            return None

    monkeypatch.setattr(coord, "ReefBeatCloudAPI", lambda *_a, **_k: _CloudAPI())

    entry_dose = MockConfigEntry(
        domain=coord.DOMAIN,
        title="Dose",
        data={
            coord.CONFIG_FLOW_IP_ADDRESS: "192.0.2.10",
            coord.CONFIG_FLOW_HW_MODEL: "RSDOSE4",
            coord.CONFIG_FLOW_CONFIG_TYPE: False,
        },
    )
    dose = coord.ReefDoseCoordinator(hass, cast(Any, entry_dose))

    entry_run = MockConfigEntry(
        domain=coord.DOMAIN,
        title="Run",
        data={
            coord.CONFIG_FLOW_IP_ADDRESS: "192.0.2.11",
            coord.CONFIG_FLOW_HW_MODEL: "RSRUN",
            coord.CONFIG_FLOW_CONFIG_TYPE: False,
        },
    )
    run = coord.ReefRunCoordinator(hass, cast(Any, entry_run))

    entry_cloud = MockConfigEntry(
        domain=coord.DOMAIN,
        title="Cloud",
        data={
            coord.CONFIG_FLOW_IP_ADDRESS: "192.0.2.12",
            coord.CONFIG_FLOW_HW_MODEL: "ReefBeat",
            coord.CONFIG_FLOW_CONFIG_TYPE: False,
            coord.CONFIG_FLOW_CLOUD_USERNAME: "u",
            coord.CONFIG_FLOW_CLOUD_PASSWORD: "p",
            coord.CONFIG_FLOW_DISABLE_SUPPLEMENT: True,
        },
    )
    cloud = coord.ReefBeatCloudCoordinator(hass, cast(Any, entry_cloud))

    def _di(_: Any) -> DeviceInfo:
        return cast(
            DeviceInfo,
            {
                "identifiers": {(coord.DOMAIN, "IDENT")},
                "manufacturer": "Red Sea",
                "model": 123,  # should be skipped
                "model_id": None,
                "hw_version": "1",
                "sw_version": "2",
                "via_device": (coord.DOMAIN, "PARENT"),
                "name": "Base",
            },
        )

    monkeypatch.setattr(type(dose), "device_info", property(_di))
    monkeypatch.setattr(type(run), "device_info", property(_di))
    monkeypatch.setattr(type(cloud), "device_info", property(_di))

    head_di = cast(DeviceInfo, dose.head_device_info(1))
    assert head_di.get("via_device") == (coord.DOMAIN, "PARENT")
    assert head_di.get("model") is None

    pump_di = cast(DeviceInfo, run.pump_device_info(1))
    assert pump_di.get("via_device") == (coord.DOMAIN, "PARENT")
    assert pump_di.get("model") is None

    aq_di = cast(DeviceInfo, cloud.aquarium_device_info("Tank"))
    assert aq_di.get("via_device") == (coord.DOMAIN, "PARENT")
    assert aq_di.get("model") is None
