from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    LED_BLUE_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
)
from custom_components.redsea.coordinator import (
    ReefLedCoordinator,
    ReefLedG2Coordinator,
)


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
class _FakeAPI:
    get_data_map: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    # G1 protocol, as ReefLedAPI reports it
    _g1: bool = True

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value


@pytest.mark.asyncio
async def test_led_set_data_updates_wb_and_manual_trick(hass: HomeAssistant) -> None:
    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefLedCoordinator(hass, cast(Any, entry))

    wb_calls: list[bool] = []
    ki_calls: int = 0

    class _LedAPI(_FakeAPI):
        def __init__(self) -> None:
            super().__init__(get_data_map={})
            self.data = {"local": {"manual_trick": {}}}

        def update_light_wb(self) -> None:
            wb_calls.append(True)

        def update_light_ki(self) -> None:
            nonlocal ki_calls
            ki_calls += 1

    coordinator.my_api = cast(Any, _LedAPI())

    coordinator.set_data(str(LED_WHITE_INTERNAL_NAME), 10)
    coordinator.set_data(str(LED_BLUE_INTERNAL_NAME), 20)
    assert len(wb_calls) == 2

    coordinator.set_data("$.local.manual_trick.foo", "bar")
    assert coordinator.my_api.data["local"]["manual_trick"]["foo"] == "bar"
    assert ki_calls == 1


@pytest.mark.asyncio
async def test_led_misc_helpers_and_g2_set_data_passthrough(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    led = ReefLedCoordinator(hass, cast(Any, entry))

    calls: dict[str, Any] = {"force": [], "post": []}

    class _LedAPI(_FakeAPI):
        daily_prog = {"x": 1}

        def __init__(self) -> None:
            super().__init__()
            self._g1 = False

        def force_status_update(self, state: bool = False) -> None:
            calls["force"].append(state)

        async def post_specific(self, source: str) -> None:
            calls["post"].append(source)

    led.my_api = cast(Any, _LedAPI())

    led.force_status_update(True)
    assert calls["force"] == [True]

    assert led.daily_prog() == {"x": 1}
    await led.post_specific("/timer")
    assert calls["post"] == ["/timer"]

    assert led.is_g1 is False

    g2 = ReefLedG2Coordinator(hass, cast(Any, entry))

    set_calls: list[tuple[str, Any]] = []

    class _G2API(_FakeAPI):
        def set_data(self, name: str, value: Any) -> None:
            set_calls.append((name, value))

    g2.my_api = cast(Any, _G2API())
    g2.set_data("$.x", 123)
    assert set_calls == [("$.x", 123)]


class _FakeCloud:
    """Cloud account holding a device list and both light libraries."""

    def __init__(self, aquarium: Any, library: Any, g2_library: Any = None) -> None:
        self.aquarium = aquarium
        self.library = library
        self.g2_library = g2_library
        self.sent: list[tuple[str, Any, str]] = []
        self.fetched: list[str | None] = []

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        if "/device" in name:
            return self.aquarium
        if "/v2/reef-lights/library" in name:
            return self.g2_library
        return self.library

    async def send_cmd(self, action: str, payload: Any, method: str = "post") -> Any:
        self.sent.append((action, payload, method))
        # The cloud gives the new entry an id
        if action.startswith("/v2/"):
            self.g2_library = [*(self.g2_library or []), {"id": "new2", **payload}]
        else:
            self.library = [*self.library, {"uid": "new", **payload}]

    async def fetch_config(self, config_path: str | None = None) -> None:
        self.fetched.append(config_path)


LIBRARY = [
    {"uid": "a", "aquarium_uid": "aq1", "name": "Perso", "program": {"x": 1}},
    {"uid": "b", "aquarium_uid": "aq2", "name": "Other", "program": {}},
    {"uid": "c", "aquarium_uid": "aq1", "name": "cyano", "clouds": {"from": 1}},
    "junk",
]
G2_LIBRARY = [
    {
        "id": "d",
        "name": "Deep reef",
        "color": {"rise": 540, "set": 1260, "points": []},
        "moon": {"rise": 1245, "set": 1410, "points": []},
        "clouds": None,
    },
    {"id": "e", "name": "No moon", "color": {"rise": 1, "set": 2, "points": []}},
]


def _led(hass: HomeAssistant, g1: bool = True) -> ReefLedCoordinator:
    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED160")
    led = ReefLedCoordinator(hass, cast(Any, entry))
    api = _FakeAPI(get_data_map={}, _g1=g1)
    led.my_api = cast(Any, api)
    return led


@pytest.mark.asyncio
async def test_led_light_library_of_the_lamp_aquarium(hass: HomeAssistant) -> None:
    led = _led(hass)

    # Not linked to a cloud account
    assert led.library_link() is None
    assert led.light_library() is None
    assert await led.save_light_program("p", {}, None) is None

    cloud = _FakeCloud("aq1", list(LIBRARY))
    led._cloud_link = cast(Any, cloud)
    assert led.library_g2() is False
    # A weather program goes to the lamp itself
    assert led.weather_targets() == [led]
    assert led.library_link() == (cloud, "aq1")
    assert led.light_library() == [
        {
            "uid": "a",
            "name": "Perso",
            "program": {"x": 1},
            "clouds": None,
            "default": False,
        },
        {
            "uid": "c",
            "name": "cyano",
            "program": None,
            "clouds": {"from": 1},
            "default": False,
        },
    ]
    # The Red Sea programs are known by name
    cloud.library = [{"uid": "r", "aquarium_uid": "aq1", "name": "18K"}]
    assert (led.light_library() or [])[0]["default"] is True
    # A single entry comes back unwrapped; no library at all
    cloud.library = LIBRARY[0]
    assert [e["uid"] for e in led.light_library() or []] == ["a"]
    cloud.library = None
    assert led.light_library() == []

    # The lamp is not in the account's device list
    cloud.aquarium = None
    assert led.library_link() is None


@pytest.mark.asyncio
async def test_led_g2_light_library_is_the_user_one(hass: HomeAssistant) -> None:
    led = _led(hass, g1=False)
    cloud = _FakeCloud("aq1", list(LIBRARY), list(G2_LIBRARY))
    led._cloud_link = cast(Any, cloud)
    assert led.library_g2() is True
    library = led.light_library() or []
    # The Red Sea programs built into the app come first
    assert [e["name"] for e in library if e["default"]] == [
        "15K",
        "23K",
        "Shallow Reef",
        "Deep Reef",
    ]
    deep = library[3]
    assert deep["uid"] == "default:Deep Reef"
    assert deep["program"]["color"]["rise"] == 480
    assert deep["program"]["color"]["points"][0] == {
        "t": 60,
        "i1": 50,
        "i2": 50,
        "k1": 16000,
        "k2": 16000,
    }
    assert deep["program"]["moon"]["points"] == [
        {"t": 75, "i": 10},
        {"t": 105, "i": 10},
    ]
    assert library[4:] == [
        {
            "uid": "d",
            "name": "Deep reef",
            "program": {
                "color": G2_LIBRARY[0]["color"],
                "moon": G2_LIBRARY[0]["moon"],
            },
            "clouds": None,
            "default": False,
        },
        {
            "uid": "e",
            "name": "No moon",
            "program": {"color": G2_LIBRARY[1]["color"]},
            "clouds": None,
            "default": False,
        },
    ]


@pytest.mark.asyncio
async def test_led_save_light_program_posts_and_reads_back(
    hass: HomeAssistant,
) -> None:
    led = _led(hass)
    cloud = _FakeCloud("aq1", list(LIBRARY))
    led._cloud_link = cast(Any, cloud)

    prog = {"white": {"rise": 600, "set": 1200, "points": []}}
    assert await led.save_light_program("prog-1", prog, None) == "new"
    clouds = {"from": 700, "to": 800, "intensity": "Low"}
    assert await led.save_light_program("prog-2", prog, clouds) == "new"
    assert cloud.sent == [
        (
            "/reef-lights/library",
            {"aquarium_uid": "aq1", "name": "prog-1", "program": prog},
            "post",
        ),
        (
            "/reef-lights/library",
            {
                "aquarium_uid": "aq1",
                "name": "prog-2",
                "program": prog,
                "clouds": clouds,
            },
            "post",
        ),
    ]
    assert cloud.fetched == ["/reef-lights/library?include=all"] * 2

    # The entry does not show up: no uid to give back
    async def _lost(action: str, payload: Any, method: str = "post") -> Any:
        return None

    cloud.send_cmd = _lost  # type: ignore[method-assign]
    assert await led.save_light_program("ghost", prog, None) is None


@pytest.mark.asyncio
async def test_led_g2_save_light_program_is_flat(hass: HomeAssistant) -> None:
    led = _led(hass, g1=False)
    cloud = _FakeCloud("aq1", [], None)
    led._cloud_link = cast(Any, cloud)
    prog = {
        "color": {"rise": 540, "set": 1260, "points": []},
        "moon": {"rise": 1245, "set": 1410, "points": []},
    }
    clouds = {"from": 601, "to": 1182, "intensity": "Medium"}
    assert await led.save_light_program("Deep", prog, clouds) == "new2"
    assert cloud.sent == [
        (
            "/v2/reef-lights/library",
            {"name": "Deep", **prog, "clouds": clouds},
            "post",
        )
    ]
    assert cloud.fetched == ["/v2/reef-lights/library"]


@pytest.mark.asyncio
async def test_led_update_and_delete_light_program(hass: HomeAssistant) -> None:
    led = _led(hass)
    library = [
        {"uid": "a", "aquarium_uid": "aq1", "name": "Perso", "program": {}},
        {"uid": "r", "aquarium_uid": "aq1", "name": "23K", "program": {}},
    ]
    cloud = _FakeCloud("aq1", library)
    led._cloud_link = cast(Any, cloud)
    prog = {"white": {"rise": 600, "set": 1200, "points": []}}

    # Update: PUT without the aquarium, as the app
    assert await led.save_light_program("Perso 2", prog, None, "a") == "a"
    assert cloud.sent[-1] == (
        "/reef-lights/library/a",
        {"name": "Perso 2", "program": prog},
        "put",
    )
    # A Red Sea program, or an unknown one, is not updated
    assert await led.save_light_program("x", prog, None, "r") is None
    assert await led.save_light_program("x", prog, None, "zz") is None
    assert len(cloud.sent) == 1

    assert await led.delete_light_program("a") is True
    assert cloud.sent[-1] == ("/reef-lights/library/a", {}, "delete")
    assert cloud.fetched[-1] == "/reef-lights/library?include=all"
    assert await led.delete_light_program("r") is False
    assert await led.delete_light_program("zz") is False
    assert len(cloud.sent) == 2

    # Not linked
    led._cloud_link = None
    assert await led.delete_light_program("a") is False


@pytest.mark.asyncio
async def test_led_g2_update_and_delete_light_program(hass: HomeAssistant) -> None:
    led = _led(hass, g1=False)
    cloud = _FakeCloud("aq1", [], list(G2_LIBRARY))
    led._cloud_link = cast(Any, cloud)
    prog = {"color": {"rise": 1, "set": 2, "points": []}}
    assert await led.save_light_program("Deep", prog, None, "d") == "d"
    assert cloud.sent[-1] == (
        "/v2/reef-lights/library/d",
        {"name": "Deep", **prog},
        "put",
    )
    assert await led.delete_light_program("d") is True
    assert cloud.sent[-1] == ("/v2/reef-lights/library/d", {}, "delete")
    # The built-in Red Sea programs are not in the cloud
    assert await led.delete_light_program("default:Deep Reef") is False
    assert await led.save_light_program("x", prog, None, "default:15K") is None
