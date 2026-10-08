from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.coordinator as coord
from custom_components.redsea.const import (
    CONF_GROUP_MEMBERS,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def _patch_network(monkeypatch: pytest.MonkeyPatch) -> None:
    # Avoid aiohttp connector creation in sync tests.
    monkeypatch.setattr(
        coord, "async_get_clientsession", lambda _hass: object(), raising=True
    )

    class _FakeLedAPI:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.data: dict[str, Any] = {"sources": [], "local": {"manual_trick": {}}}
            self.quick_refresh: str | None = None
            self._timeout = 1
            self._g1 = True

        async def fetch_data(self) -> dict[str, Any] | None:
            return {}

        async def fetch_config(self, _config_path: str | None = None) -> None:
            return None

        async def get_initial_data(self) -> None:
            return None

        async def push_values(
            self, _source: str = "/configuration", _method: str = "put", *_a: Any
        ) -> None:
            return None

        async def press(self, _action: str, *_a: Any) -> None:
            return None

        async def delete(self, _source: str) -> None:
            return None

        async def post_specific(self, _source: str) -> None:
            return None

        def get_data(self, _name: str, _is_None_possible: bool = False) -> Any:
            return None

        def set_data(self, _name: str, _value: Any) -> None:
            return None

        def force_status_update(self, _state: bool = False) -> None:
            return None

        def update_light_wb(self) -> None:
            return None

        def update_light_ki(self) -> None:
            return None

    monkeypatch.setattr(coord, "ReefLedAPI", _FakeLedAPI, raising=True)


def _make_entry(
    *, title: str, ip: str, hw_model: str, linked: list[Any] | None = None
) -> MockConfigEntry:
    """A virtual LED entry; ``linked`` are the member entry ids, in order."""
    data: dict[str, Any] = {
        CONFIG_FLOW_IP_ADDRESS: ip,
        CONFIG_FLOW_HW_MODEL: hw_model,
        CONFIG_FLOW_CONFIG_TYPE: False,
        CONFIG_FLOW_INTENSITY_COMPENSATION: False,
    }
    if linked is not None:
        data[CONF_GROUP_MEMBERS] = linked
    return MockConfigEntry(domain=DOMAIN, title=title, data=data)


@dataclass
class _FakeAPI:
    fetch_data_result: dict[str, Any] | None = field(default_factory=dict)
    fetch_data_exc: BaseException | None = None

    async def fetch_data(self) -> dict[str, Any] | None:
        if self.fetch_data_exc is not None:
            raise self.fetch_data_exc
        return self.fetch_data_result


@dataclass
class _LinkedLed:
    title: str
    is_g1: bool
    # Hardware id and model, as a real coordinator exposes them
    model_id: str = ""
    model: str = ""

    my_api: Any = field(default_factory=_FakeAPI)

    get_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)
    pushed: list[tuple[str, str]] = field(default_factory=list)
    pressed: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    configs: list[str | None] = field(default_factory=list)
    posted: list[str] = field(default_factory=list)
    refresh_calls: list[tuple[str | None, int]] = field(default_factory=list)

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))

    async def push_values(
        self, source: str = "/configuration", method: str = "post"
    ) -> None:
        self.pushed.append((source, method))

    def data_exist(self, name: str) -> bool:
        return name in self.get_map

    async def press(self, action: str) -> None:
        self.pressed.append(action)

    async def delete(self, source: str) -> None:
        self.deleted.append(source)

    async def post_specific(self, source: str) -> None:
        self.posted.append(source)

    async def async_request_refresh(
        self, src: str | None = None, config: bool = False, wait: int = 2
    ) -> None:
        self.refresh_calls.append((src, wait))


@pytest.mark.asyncio
async def test_virtual_led_only_g1_flag_detects_g2(hass: HomeAssistant) -> None:
    """The generation of each member is read from its config entry."""
    g1 = _make_entry(title="G1", ip="192.0.2.11", hw_model="RSLED50")
    g2 = _make_entry(title="G2", ip="192.0.2.12", hw_model="RSLED60")
    g1.add_to_hass(hass)
    g2.add_to_hass(hass)

    only_g1 = _make_entry(
        title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[g1.entry_id]
    )
    assert coord.ReefVirtualLedCoordinator(hass, cast(Any, only_g1)).only_g1 is True

    # A member not configured (any more) does not make the group a G2
    mixed = _make_entry(
        title="VLED",
        ip="192.0.2.10",
        hw_model="RSLED50",
        linked=[g1.entry_id, "unknown", g2.entry_id],
    )
    assert coord.ReefVirtualLedCoordinator(hass, cast(Any, mixed)).only_g1 is False


def test_virtual_led_init_running_calls_link_leds(hass: HomeAssistant) -> None:
    hass.data.setdefault(DOMAIN, {})
    led1 = _LinkedLed(title="LED1", is_g1=True)
    hass.data[DOMAIN]["id1"] = led1

    # Ensure parsing works and __init__ RUNNING path can call _link_leds.
    entry = _make_entry(
        title="VLED",
        ip="192.0.2.10",
        hw_model="RSLED50",
        linked=["id1"],
    )
    hass.state = "RUNNING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))
    assert len(vled._linked) == 1  # type: ignore[attr-defined]


def test_virtual_led_device_info_and_no_linked_get_data_returns_none(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))

    assert vled.device_info.get("model") == coord.VIRTUAL_LED
    assert vled.get_data("$.anything") is None


def test_virtual_led_link_leds_missing_key_logs_and_returns(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=None)
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))

    # Should just return without raising.
    vled._link_leds()  # type: ignore[attr-defined]


def test_virtual_led_link_leds_empty_and_single_linked(hass: HomeAssistant) -> None:
    hass.state = "STARTING"  # type: ignore[assignment]

    hass.data.setdefault(DOMAIN, {})

    entry0 = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    v0 = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry0))
    v0._link_leds()  # type: ignore[attr-defined]
    assert v0._linked == []  # type: ignore[attr-defined]

    led1 = _LinkedLed(title="LED1", is_g1=True)
    hass.data[DOMAIN]["id1"] = led1

    entry1 = _make_entry(
        title="VLED",
        ip="192.0.2.10",
        hw_model="RSLED50",
        linked=["id1"],
    )
    v1 = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry1))
    v1._link_leds()  # type: ignore[attr-defined]
    assert len(v1._linked) == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_virtual_led_async_update_data_aggregates_and_ignores_errors(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))

    ok = _LinkedLed(title="A", is_g1=True)
    ok.my_api = _FakeAPI(fetch_data_result={"k": 1})

    bad = _LinkedLed(title="B", is_g1=True)
    bad.my_api = _FakeAPI(fetch_data_exc=RuntimeError("boom"))

    vled._linked = [ok, bad]  # type: ignore[attr-defined]

    res = await vled._async_update_data()  # type: ignore[attr-defined]
    assert res == {"k": 1}


def test_virtual_led_get_data_dispatches_by_type_and_fallback(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))

    l1 = _LinkedLed(title="A", is_g1=True, get_map={"$.b": True})
    l2 = _LinkedLed(title="B", is_g1=True, get_map={"$.b": True})
    vled._linked = [l1, l2]  # type: ignore[attr-defined]

    assert vled.get_data("$.b") is True

    l1.get_map = {"$.i": 1}
    l2.get_map = {"$.i": 3}
    assert vled.get_data("$.i") == 2

    l1.get_map = {"$.f": 1.0}
    l2.get_map = {"$.f": 3.0}
    assert vled.get_data("$.f") == 2.0

    l1.get_map = {"$.s": "x"}
    l2.get_map = {"$.s": "x"}
    assert vled.get_data("$.s") == "x"

    l1.get_map = {"$.n": None}
    l2.get_map = {"$.n": None}
    assert vled.get_data("$.n") is None

    # Unhandled type falls back to returning the value.
    l1.get_map = {"$.u": [1, 2]}
    l2.get_map = {"$.u": [1, 2]}
    assert vled.get_data("$.u") == [1, 2]


def test_virtual_led_get_data_dict_passthrough(hass: HomeAssistant) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))
    vled._linked = [  # type: ignore[attr-defined]
        _LinkedLed(title="A", is_g1=True, get_map={"$.d": {"k": 1}})
    ]

    assert vled.get_data("$.d") == {"k": 1}


def test_virtual_led_get_data_unknown_type_logs_warning(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))
    vled._linked = [  # type: ignore[attr-defined]
        _LinkedLed(title="A", is_g1=True, get_map={"$.u": (1, 2), "$.names": [1, 2]})
    ]

    seen: list[str] = []

    def _warn(msg: str, *args: Any, **_kwargs: Any) -> None:
        seen.append(msg % args)

    monkeypatch.setattr(coord._LOGGER, "warning", _warn, raising=True)

    # A whole source (a program, the list of the names) is given as it is
    assert vled.get_data("$.names") == [1, 2]
    assert seen == []
    assert vled.get_data("$.u") == (1, 2)
    assert any("Not implemented" in s for s in seen)


def test_virtual_led_get_data_kelvin_and_no_light_defaults(hass: HomeAssistant) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))

    g1 = _LinkedLed(
        title="A",
        is_g1=True,
        get_map={"$.g1.kelvin": 9000, "$.g1.intensity": 10},
    )
    g2 = _LinkedLed(
        title="B",
        is_g1=False,
        get_map={"$.g2.kelvin": 15000, "$.g2.intensity": 30},
    )
    vled._linked = [g1, g2]  # type: ignore[attr-defined]

    res = vled.get_data_kelvin("$.g1 $.g2")
    assert res["kelvin"] == (9000 + 15000) / 2
    assert res["intensity"] == (10 + 30) / 2

    # Also cover the get_data() dispatch path that detects the split name.
    assert vled.get_data("$.g1 $.g2") == res

    vled._linked = []  # type: ignore[attr-defined]
    assert vled.get_data_kelvin("$.g1 $.g2") == {"kelvin": 23000, "intensity": 0}


def test_virtual_led_direct_helpers_cover_empty_and_false_paths(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    hass.state = "STARTING"  # type: ignore[assignment]
    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))

    # Empty-linked fallbacks
    vled._linked = []  # type: ignore[attr-defined]
    assert vled.get_data_str("$.x") == "Error"
    assert vled.get_data_int("$.x") == 0
    assert vled.get_data_float("$.x") == 0.0

    # Bool short-circuit False
    l1 = _LinkedLed(title="A", is_g1=True, get_map={"$.b": True})
    l2 = _LinkedLed(title="B", is_g1=True, get_map={"$.b": False})
    vled._linked = [l1, l2]  # type: ignore[attr-defined]
    assert vled.get_data_bool("$.b") is False


@pytest.mark.asyncio
async def test_virtual_led_broadcasts_to_linked_leds(
    monkeypatch: pytest.MonkeyPatch, hass: HomeAssistant
) -> None:
    entry = _make_entry(title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=[])
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))

    l1 = _LinkedLed(title="A", is_g1=True)
    l2 = _LinkedLed(title="B", is_g1=False)
    vled._linked = [l1, l2]  # type: ignore[attr-defined]

    # set_data resolves "g1_path g2_path" to the correct path per linked LED.
    vled.set_data("$.g1.white $.g2.white", 12)
    # For G1 devices, the implementation appends the final key of the G2 path.
    assert l1.set_calls[-1][0] == "$.g1.white.white"
    assert l2.set_calls[-1][0] == "$.g2.white"

    # Also cover single-path set_data.
    vled.set_data("$.single", 1)
    assert l1.set_calls[-1][0] == "$.single"
    assert l2.set_calls[-1][0] == "$.single"

    await vled.push_values("/configuration", "post")
    assert l1.pushed == [("/configuration", "post")]
    assert l2.pushed == [("/configuration", "post")]

    # Cover fetch_config broadcast loop.
    cfg_calls: list[tuple[str, str | None]] = []

    class _Api:
        def __init__(self, label: str) -> None:
            self._label = label

        async def fetch_config(self, config_path: str | None = None) -> None:
            cfg_calls.append((self._label, config_path))

    l1.my_api = _Api("l1")
    l2.my_api = _Api("l2")
    await vled.fetch_config("/x")
    assert cfg_calls == [("l1", "/x"), ("l2", "/x")]

    assert vled.data_exist("$.missing") is False
    l2.get_map["$.exists"] = True
    assert vled.data_exist("$.exists") is True

    await vled.press("go")
    await vled.delete("/x")
    await vled.post_specific("/timer")
    assert l1.pressed == ["go"] and l2.pressed == ["go"]
    assert l1.deleted == ["/x"] and l2.deleted == ["/x"]
    assert l1.posted == ["/timer"] and l2.posted == ["/timer"]

    await vled.async_request_refresh(wait=0)
    await vled.async_request_refresh(source="/dashboard", wait=0)
    assert l1.refresh_calls == ([(None, 0), ("/dashboard", 0)])
    assert l2.refresh_calls == ([(None, 0), ("/dashboard", 0)])

    # Cover force_status_update override (no-op).
    assert vled.force_status_update() is None

    # Keep coordinator super calls inert.
    async def _fake_super_refresh(self: DataUpdateCoordinator[Any]) -> None:
        return None

    monkeypatch.setattr(
        DataUpdateCoordinator,
        "async_request_refresh",
        _fake_super_refresh,
        raising=True,
    )


def test_virtual_led_linked_leds_describes_each_lamp(hass: HomeAssistant) -> None:
    """linked_leds() gives the card what it needs to list and write to lamps."""
    hass.state = "STARTING"  # type: ignore[assignment]
    hass.data.setdefault(DOMAIN, {})
    led1 = _LinkedLed(title="LED1", is_g1=True, model_id="hw1", model="RSLED160")
    led2 = _LinkedLed(title="LED2", is_g1=False, model_id="hw2", model="RSLED170")
    # LED2 has /offset: its staggered sunrise is listed
    led2.get_map[coord.LED_OFFSET_INTERNAL_NAME] = 10.0
    hass.data[DOMAIN]["id1"] = led1
    hass.data[DOMAIN]["id2"] = led2

    entry = _make_entry(
        title="VLED",
        ip="192.0.2.10",
        hw_model="RSLED50",
        linked=["id1", "id2"],
    )
    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))
    vled._link_leds()  # type: ignore[attr-defined]

    assert vled.linked_leds() == [
        {
            "hwid": "hw1",
            "name": "LED1",
            "model": "RSLED160",
            "g2": False,
            "offset": None,
            "entry_id": "id1",
        },
        {
            "hwid": "hw2",
            "name": "LED2",
            "model": "RSLED170",
            "g2": True,
            "offset": 10,
            "entry_id": "id2",
        },
    ]
    # A value that is not a number (a flag) is no offset
    led2.get_map[coord.LED_OFFSET_INTERNAL_NAME] = True
    assert vled.linked_leds()[1]["offset"] is None
    # A lamp linked without its entry (defensive): no entry id
    vled._linked_entries = []  # type: ignore[attr-defined]
    assert vled.linked_leds()[0]["entry_id"] is None

    # The sensor exposes the count and the list
    import custom_components.redsea.sensor as sensor_platform

    desc = sensor_platform.VIRTUAL_LED_SENSORS[0]
    assert desc.value_fn(vled) == 2
    assert desc.attributes_fn is not None
    assert len(desc.attributes_fn(vled)["leds"]) == 2


def test_virtual_led_library_link_uses_first_linked_cloud(
    hass: HomeAssistant,
) -> None:
    """A virtual LED keeps its programs in its first cloud-linked lamp's library."""
    hass.state = "STARTING"  # type: ignore[assignment]
    entry = _make_entry(
        title="VLED",
        ip="192.0.2.10",
        hw_model="RSLED50",
        linked=["id1"],
    )
    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))

    class _Unlinked:
        def library_link(self) -> Any:
            return None

    class _Linked:
        def library_link(self) -> Any:
            return ("cloud", "aq")

    vled._linked = []  # type: ignore[attr-defined]
    assert vled.library_link() is None
    # Only G1 lamps: the aquarium library; a G2 among them: the G2 one
    vled._only_g1 = True  # type: ignore[attr-defined]
    assert vled.library_g2() is False
    vled._only_g1 = False  # type: ignore[attr-defined]
    assert vled.library_g2() is True
    vled._linked = [object(), _Unlinked(), _Linked()]  # type: ignore[attr-defined]
    assert vled.library_link() == ("cloud", "aq")
    # A weather program goes to each lamp of the group
    assert vled.weather_targets() == vled._linked  # type: ignore[attr-defined]
    assert vled.weather_targets() is not vled._linked  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# Groups: a member routes its shared writes to its group
# -----------------------------------------------------------------------------

WHITE = "$.sources[?(@.name=='/manual')].data.white"


class _RecApi:
    """LED API recording what a lamp was sent."""

    def __init__(self, g1: bool = True) -> None:
        self._g1 = g1
        self.data: dict[str, Any] = {"sources": [], "local": {"manual_trick": {}}}
        self.sets: list[tuple[str, Any]] = []
        self.values: dict[str, Any] = {}
        self.pushes: list[tuple[str, str]] = []
        self.posts: list[str] = []
        self.presses: list[str] = []
        self.deletes: list[str] = []
        self.expected: list[tuple[str, bool]] = []

    def set_data(self, name: str, value: Any) -> None:
        self.sets.append((name, value))
        self.values[name] = value

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        return self.values.get(name)

    async def push_values(self, source: str, method: str = "post") -> None:
        self.pushes.append((source, method))

    async def post_specific(self, source: str) -> None:
        self.posts.append(source)

    async def fetch_data(self) -> dict[str, Any]:
        return {}

    async def press(self, action: str) -> None:
        self.presses.append(action)

    async def delete(self, source: str) -> None:
        self.deletes.append(source)

    def expect_settings(self, source: str, enabled: bool) -> None:
        self.expected.append((source, enabled))

    def update_light_wb(self) -> None:
        return None

    def update_light_ki(self) -> None:
        return None

    def written(self) -> int:
        return (
            len(self.pushes) + len(self.posts) + len(self.presses) + len(self.deletes)
        )


def _member(
    hass: HomeAssistant, title: str, hw_model: str = "RSLED90", g2: bool = False
) -> Any:
    """A loaded lamp (config entry + coordinator in hass.data)."""
    entry = _make_entry(title=title, ip="192.0.2.20", hw_model=hw_model)
    entry.add_to_hass(hass)
    cls = coord.ReefLedG2Coordinator if g2 else coord.ReefLedCoordinator
    led = cls(hass, cast(Any, entry))
    led.my_api = _RecApi(g1=not g2)  # type: ignore[assignment]
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = led
    return led


def _group(hass: HomeAssistant, members: list[Any]) -> Any:
    entry = _make_entry(
        title="VLED",
        ip=coord.VIRTUAL_LED,
        hw_model=coord.VIRTUAL_LED,
        linked=[m._entry.entry_id for m in members],
    )
    entry.add_to_hass(hass)
    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))
    hass.data[DOMAIN][entry.entry_id] = vled
    return vled


async def test_member_routes_only_shared_writes_to_its_group(
    hass: HomeAssistant,
) -> None:
    led = _member(hass, "LED1")
    api = cast(_RecApi, led.my_api)

    # Alone: everything stays on the lamp
    assert led.led_group() is None
    led.set_data(WHITE, 10)
    await led.push_values("/manual", "post")
    await led.post_specific("/timer")
    assert api.sets == [(WHITE, 10)]
    assert api.pushes == [("/manual", "post")]
    assert api.posts == ["/timer"]

    class _Group:
        def __init__(self) -> None:
            self.member_ids = [led._entry.entry_id]
            self.calls: list[tuple[Any, ...]] = []

        def route_set_data(self, name: str, value: Any) -> None:
            self.calls.append(("set", name, value))

        async def push_values(self, source: str, method: str) -> None:
            self.calls.append(("push", source, method))

        async def post_specific(self, source: str) -> None:
            self.calls.append(("post", source))

    group = _Group()
    hass.data[DOMAIN]["group"] = group
    assert led.led_group() is group

    # Shared: routed to the group
    led.set_data(WHITE, 20)
    await led.push_values("/manual", "post")
    await led.post_specific("/timer")
    assert group.calls == [
        ("set", WHITE, 20),
        ("push", "/manual", "post"),
        ("post", "/timer"),
    ]
    # Not shared: kept on the lamp
    led.set_data("$.local.status", True)
    await led.push_values("/device-settings", "put")
    await led.post_specific("/unknown")
    assert api.sets[-1] == ("$.local.status", True)
    assert api.pushes[-1] == ("/device-settings", "put")
    assert api.posts[-1] == "/unknown"
    # Written by its group: never routed back
    with coord.group_dispatch():
        assert led.led_group() is None
        led.set_data(WHITE, 30)
    assert api.sets[-1] == (WHITE, 30)
    assert len(group.calls) == 3


async def test_g2_member_writes_locally_without_g1_updates(
    hass: HomeAssistant,
) -> None:
    led = _member(hass, "LED2", hw_model="RSLED60", g2=True)
    led.set_data(WHITE, 5)
    assert cast(_RecApi, led.my_api).sets == [(WHITE, 5)]


async def test_group_applies_a_member_write_to_every_member(
    hass: HomeAssistant,
) -> None:
    led1 = _member(hass, "LED1")
    led2 = _member(hass, "LED2")
    vled = _group(hass, [led1, led2])
    api1, api2 = cast(_RecApi, led1.my_api), cast(_RecApi, led2.my_api)
    assert vled.only_g1 is True
    assert vled._linked == [led1, led2]  # type: ignore[attr-defined]

    updates: list[str] = []
    led2.async_add_listener(lambda: updates.append("led2"))

    # A white value set on one lamp is set on both, then pushed by both
    led1.set_data(WHITE, 40)
    await led1.push_values("/manual", "post")
    assert api1.sets == [(WHITE, 40)] and api2.sets == [(WHITE, 40)]
    assert api1.pushes == [("/manual", "post")] == api2.pushes
    assert updates == ["led2"]

    # Kelvin set on a G1 lamp: the G1 path on each lamp
    led2.set_data("$.local.manual_trick.kelvin", 9000)
    assert api1.sets[-1] == ("$.local.manual_trick.kelvin", 9000)
    assert api2.sets[-1] == ("$.local.manual_trick.kelvin", 9000)

    await led2.post_specific("/timer")
    assert api1.posts == ["/timer"] == api2.posts

    # A group holding a G2: white/blue cannot be set on the whole group
    vled._only_g1 = False  # type: ignore[attr-defined]
    with pytest.raises(HomeAssistantError) as err:
        led1.set_data(WHITE, 50)
    assert err.value.translation_key == "group_channel_unavailable"
    assert api2.sets[-1] == ("$.local.manual_trick.kelvin", 9000)


async def test_mixed_group_kelvin_reaches_the_g2(hass: HomeAssistant) -> None:
    """Colour and intensity set on a G1 reach the G2 of its group."""
    g1 = _member(hass, "LED1")
    g2 = _member(hass, "LED2", hw_model="RSLED60", g2=True)
    _group(hass, [g1, g2])
    api1, api2 = cast(_RecApi, g1.my_api), cast(_RecApi, g2.my_api)
    g2_path = "$.sources[?(@.name=='/manual')].data"
    manual: dict[str, Any] = {"moon": 0}
    api2.values[g2_path] = manual

    # Not reported by the G2: added to its manual levels, on its scale
    g1.set_data("$.local.manual_trick.kelvin", 15100)
    g1.set_data("$.local.manual_trick.intensity", 60)
    assert api1.sets[-2:] == [
        ("$.local.manual_trick.kelvin", 15100),
        ("$.local.manual_trick.intensity", 60),
    ]
    assert manual == {"moon": 0, "kelvin": 15000, "intensity": 60}
    assert api2.sets == []

    # Reported: written, 200 K steps under 10000 K
    manual["kelvin"] = 15000
    g1.set_data("$.local.manual_trick.kelvin", 9850)
    assert api2.sets == [(g2_path + ".kelvin", 9800)]
    # Bounded to the G2's range
    g1.set_data("$.local.manual_trick.kelvin", 30000)
    assert api2.sets[-1] == (g2_path + ".kelvin", 23000)

    # The G2's other values, or a G2 written on its own: as given
    with coord.group_dispatch():
        g2.set_data(g2_path + ".moon", 5)
    api2.values[g2_path] = None
    with coord.group_dispatch():
        g2.set_data(g2_path + ".kelvin", 9850)
    assert api2.sets[-2:] == [(g2_path + ".moon", 5), (g2_path + ".kelvin", 9800)]
    g2._set_data_local(g2_path + ".kelvin", 15100)
    assert api2.sets[-1] == (g2_path + ".kelvin", 15100)


def test_g2_kelvin_scale() -> None:
    assert coord.g2_kelvin(9850) == 9800
    assert coord.g2_kelvin(10100) == 10000
    assert coord.g2_kelvin(15300) == 15500
    assert coord.g2_kelvin(5000) == 8000


async def test_group_refuses_a_write_when_a_member_is_missing(
    hass: HomeAssistant,
) -> None:
    led1 = _member(hass, "LED1")
    led2 = _member(hass, "LED2")
    vled = _group(hass, [led1, led2])
    api1 = cast(_RecApi, led1.my_api)
    assert vled.unavailable_members() == []

    # A member not answering
    led2.last_update_success = False
    with pytest.raises(HomeAssistantError) as err:
        await led1.push_values("/manual", "post")
    assert err.value.translation_key == "group_member_unavailable"
    assert err.value.translation_placeholders == {"group": "VLED", "members": "LED2"}
    assert api1.written() == 0

    # A member not loaded (its entry title is shown), one without entry
    led2.last_update_success = True
    del hass.data[DOMAIN][led2._entry.entry_id]
    vled.member_ids.append("gone")
    assert vled.unavailable_members() == ["LED2", "gone"]
    for action in (
        vled.press("identify"),
        vled.delete("/x"),
        vled.post_specific("/timer"),
        vled.push_values("/manual", "post"),
    ):
        with pytest.raises(HomeAssistantError):
            await action
    assert api1.written() == 0


async def test_group_follows_its_members_being_loaded(hass: HomeAssistant) -> None:
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    led1 = _member(hass, "LED1")
    led2 = _member(hass, "LED2")
    entry2 = led2._entry.entry_id
    # LED2 not loaded yet when the group starts
    del hass.data[DOMAIN][entry2]
    vled = _group(hass, [led1, led2])
    assert vled._linked == [led1]  # type: ignore[attr-defined]
    assert vled._linked_entries == [led1._entry.entry_id]  # type: ignore[attr-defined]

    updates: list[int] = []
    vled.async_add_listener(lambda: updates.append(1))

    # A device outside the group: ignored
    async_dispatcher_send(hass, coord.SIGNAL_GROUP_MEMBER_READY, "other")
    await hass.async_block_till_done()
    assert updates == []

    # LED2 loaded (a new coordinator): followed
    hass.data[DOMAIN][entry2] = led2
    async_dispatcher_send(hass, coord.SIGNAL_GROUP_MEMBER_READY, entry2)
    await hass.async_block_till_done()
    assert vled._linked == [led1, led2]  # type: ignore[attr-defined]
    assert updates == [1]

    # LED1 unloaded: dropped
    del hass.data[DOMAIN][led1._entry.entry_id]
    async_dispatcher_send(hass, coord.SIGNAL_GROUP_MEMBER_GONE, led1._entry.entry_id)
    await hass.async_block_till_done()
    assert vled._linked == [led2]  # type: ignore[attr-defined]

    # Group unloaded: no longer listening
    vled.unload()
    hass.data[DOMAIN][led1._entry.entry_id] = led1
    async_dispatcher_send(hass, coord.SIGNAL_GROUP_MEMBER_READY, led1._entry.entry_id)
    await hass.async_block_till_done()
    assert vled._linked == [led2]  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# Groups: staggered sunrise and shared weather program
# -----------------------------------------------------------------------------

OFFSET = coord.LED_OFFSET_INTERNAL_NAME


async def _grouped(hass: HomeAssistant, count: int = 3) -> tuple[Any, list[Any]]:
    """A group of lamps having /offset, with its GroupStore."""
    from custom_components.redsea.groups import GroupStore

    leds = [_member(hass, f"LED{n + 1}") for n in range(count)]
    for led in leds:
        cast(_RecApi, led.my_api).values[OFFSET] = 0
    vled = _group(hass, leds)
    store = GroupStore(hass, vled._entry.entry_id)
    await store.async_load()
    vled.group_store = store
    return vled, leds


def _offsets(leds: list[Any]) -> list[Any]:
    return [cast(_RecApi, led.my_api).values.get(OFFSET) for led in leds]


async def test_lamp_offset_is_written_to_the_lamp_only(hass: HomeAssistant) -> None:
    led = _member(hass, "LED1")
    api = cast(_RecApi, led.my_api)
    # No /offset on this lamp: nothing sent
    assert led.supports_offset is False
    await led.set_offset(10)
    assert api.pushes == []

    api.values[OFFSET] = 0
    assert led.supports_offset is True
    await led.set_offset(12)
    assert api.values[OFFSET] == 12
    assert api.pushes == [(coord.LED_OFFSET_SOURCE, "post")]


async def test_group_staggered_sunrise(hass: HomeAssistant) -> None:
    vled, leds = await _grouped(hass)
    store = vled.group_store

    # Never turned on: the lamps' offsets are left alone
    assert vled.offsets_pending() is False
    vled.async_reconcile_staggered()
    await hass.async_block_till_done()
    assert all(cast(_RecApi, led.my_api).pushes == [] for led in leds)

    # On, 10 minutes (the app's default): 0, 10, 20 in the group order
    await vled.async_set_staggered(staggered=True)
    assert _offsets(leds) == [0, 10, 20]
    assert store.applied == {
        led._entry.entry_id: off for led, off in zip(leds, (0, 10, 20), strict=True)
    }
    assert vled.offsets_pending() is False

    # A delay out of the app's range is kept within it
    await vled.async_set_staggered(delay=40)
    assert store.delay == 15
    assert _offsets(leds) == [0, 15, 30]

    # Off: every lamp back to its own program
    await vled.async_set_staggered(staggered=False)
    assert _offsets(leds) == [0, 0, 0]


async def test_group_staggered_refused_when_a_lamp_is_missing(
    hass: HomeAssistant,
) -> None:
    vled, leds = await _grouped(hass, 2)
    leds[1].last_update_success = False
    with pytest.raises(HomeAssistantError):
        await vled.async_set_staggered(staggered=True)
    # Nothing changed nor sent
    assert vled.group_store.staggered is False
    assert _offsets(leds) == [0, 0]

    # Without a store (not set up): nothing to do
    vled.group_store = None
    await vled.async_set_staggered(staggered=True)
    await vled.async_apply_staggered()
    assert vled.staggered_offsets() == {}
    assert vled.offsets_pending() is False


async def test_group_staggered_follows_the_members_and_their_order(
    hass: HomeAssistant,
) -> None:
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    vled, leds = await _grouped(hass)
    await vled.async_set_staggered(staggered=True)
    assert _offsets(leds) == [0, 10, 20]

    # New order, LED3 left the group: offsets written again once all the
    # lamps are there, LED3 back to 0
    ids = [led._entry.entry_id for led in leds]
    vled.member_ids = [ids[1], ids[0]]
    vled._link_leds()  # type: ignore[attr-defined]
    vled.async_reconcile_staggered()
    await hass.async_block_till_done()
    assert _offsets(leds) == [10, 0, 0]

    # A lamp missing: waits for it (no write), then writes when it is back
    vled.member_ids = [ids[0], ids[1]]
    led2 = hass.data[DOMAIN].pop(ids[1])
    vled.async_reconcile_staggered()
    await hass.async_block_till_done()
    assert _offsets(leds) == [10, 0, 0]
    hass.data[DOMAIN][ids[1]] = led2
    async_dispatcher_send(hass, coord.SIGNAL_GROUP_MEMBER_READY, ids[1])
    await hass.async_block_till_done()
    assert _offsets(leds) == [0, 10, 0]


async def test_group_staggered_reconcile_failure_is_logged(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    vled, _leds = await _grouped(hass, 2)
    vled.group_store.staggered = True

    async def _refused() -> None:
        raise HomeAssistantError("LED2 gone")

    vled.async_apply_staggered = _refused  # type: ignore[method-assign]
    vled.async_reconcile_staggered()
    await hass.async_block_till_done()
    assert "staggered sunrise not written" in caplog.text


async def test_grouped_lamps_share_the_group_weather(hass: HomeAssistant) -> None:
    vled, leds = await _grouped(hass, 2)
    own, shared = object(), object()
    leds[0].weather = own
    # No weather on the group: the lamp keeps its own
    assert leds[0].weather is own
    vled.weather = shared
    assert leds[0].weather is shared
    assert leds[1].weather is shared
    assert vled.weather is shared
    # A weather week goes to every lamp of the group
    assert leds[0].weather_targets() == leds
    # Out of the group: its own again
    del hass.data[DOMAIN][vled._entry.entry_id]
    assert leds[0].weather is own
    assert leds[0].weather_targets() == [leds[0]]


# -----------------------------------------------------------------------------
# Groups: what blocks a group write, the cloud round trip, Repairs
# -----------------------------------------------------------------------------

AQ = "aq-1"


class _Cloud(coord.ReefBeatCloudCoordinator):
    """A cloud account holding lamps, answering as the ReefBeat cloud does."""

    def __init__(self, devices: list[dict[str, Any]]) -> None:  # no HA setup
        self.devices = devices
        self.aquariums: list[dict[str, Any]] = [
            {"uid": AQ, "properties": {"groups": []}}
        ]
        self.sent: list[tuple[str, Any, str]] = []
        self.fetched: list[str | None] = []
        self.accept = True
        self.my_api = cast(Any, SimpleNamespace(quick_refresh=None, fetch_data=_noop))

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        if "/aquarium" in name:
            return self.aquariums
        found = re.search(r"hwid=='([^']*)'", name)
        if found:
            return next((d for d in self.devices if d["hwid"] == found[1]), None)
        return self.devices

    async def send_cmd(self, action: str, payload: Any, method: str = "post") -> Any:
        self.sent.append((action, payload, method))
        if not self.accept:
            return {"ok": False}
        if action == "/device/manage":
            for item in payload:
                device = next(d for d in self.devices if d["hwid"] == item["hwid"])
                device.update(grouped=item["grouped"], group_index=item["group_index"])
        elif "/group/" in action:
            groups = self.aquariums[0]["properties"]["groups"]
            groups[:] = [{"name": action.rsplit("/", 1)[1], **payload}]
        return {"ok": True}

    async def fetch_config(self, config_path: str | None = None) -> None:
        self.fetched.append(config_path)


async def _noop(*_a: Any, **_k: Any) -> None:
    return None


def _device(hwid: str, model: str = "RSLED90", **extra: Any) -> dict[str, Any]:
    return {
        "hwid": hwid,
        "name": hwid,
        "model": model,
        "aquarium_uid": AQ,
        "grouped": False,
        "group_index": 0,
        "in_service": True,
        **extra,
    }


async def _cloud_group(
    hass: HomeAssistant, count: int = 2, models: tuple[str, ...] = ()
) -> tuple[Any, list[Any], _Cloud]:
    """A group of lamps listed by a cloud account (hwid = lamp title)."""
    from custom_components.redsea.groups import GroupStore

    leds = [
        _member(hass, f"LED{n + 1}", hw_model=models[n] if models else "RSLED90")
        for n in range(count)
    ]
    for led in leds:
        cast(_RecApi, led.my_api).values[OFFSET] = 0
    cloud = _Cloud([_device(led.model_id, led.model) for led in leds])
    hass.data[DOMAIN]["cloud"] = cloud
    vled = _group(hass, leds)
    vled.group_store = GroupStore(hass, vled._entry.entry_id)
    await vled.group_store.async_load()
    return vled, leds, cloud


def _issue(hass: HomeAssistant, kind: str, vled: Any) -> Any:
    from homeassistant.helpers import issue_registry as ir

    return ir.async_get(hass).async_get_issue(DOMAIN, f"{kind}_{vled._entry.entry_id}")


async def test_group_blocking_members_and_out_of_service(hass: HomeAssistant) -> None:
    vled, leds, cloud = await _cloud_group(hass, 3)
    # A lamp off, or held by a shortcut: the group waits for it
    cast(_RecApi, leds[1].my_api).values[coord.LED_MODE_INTERNAL_NAME] = "off"
    cast(_RecApi, leds[2].my_api).values[coord.LED_MODE_INTERNAL_NAME] = "auto"
    assert vled.unavailable_members() == ["LED2 (off)"]
    with pytest.raises(HomeAssistantError):
        await vled.push_values("/manual", "post")
    # Out of service (ReefBeat app): left out of the writes, blocks nothing
    cloud.devices[1]["in_service"] = False
    assert vled.unavailable_members() == []
    assert vled._targets() == [leds[0], leds[2]]
    assert vled.weather_targets() == [leds[0], leds[2]]
    await vled.push_values("/manual", "post")
    assert cast(_RecApi, leds[1].my_api).pushes == []
    assert cast(_RecApi, leds[2].my_api).pushes == [("/manual", "post")]
    # Nor counted in the staggered sunrise
    vled.group_store.staggered = True
    assert list(vled.staggered_offsets().values()) == [0, 10]


async def test_group_written_to_the_cloud_then_kept_in_sync(
    hass: HomeAssistant,
) -> None:
    vled, leds, cloud = await _cloud_group(hass)
    hwids = [led.model_id for led in leds]
    await vled.group_store.async_set(staggered=True, delay=5)
    assert vled.cloud_context() == (cloud, AQ, "RSLED90")

    # First time: the cloud has no group, it gets this one
    await vled._async_update_data()
    manage = cloud.sent[0]
    assert manage[0] == "/device/manage"
    assert [(i["hwid"], i["grouped"], i["group_index"]) for i in manage[1]] == [
        (hwids[0], True, 0),
        (hwids[1], True, 1),
    ]
    assert cloud.sent[1] == (
        f"/aquarium/{AQ}/group/rsled90",
        {"properties": {"staggered": True, "staggered_delay": 5}},
        "put",
    )
    assert cloud.sent[2:] == [
        (f"/device/{hwids[0]}", {"offset": 0}, "put"),
        (f"/device/{hwids[1]}", {"offset": 5}, "put"),
    ]
    assert cloud.fetched == ["/device"] and cloud.my_api.quick_refresh == "/aquarium"
    assert vled.group_store.snapshot == {
        "members": hwids,
        "staggered": True,
        "delay": 5,
    }
    # Nothing changed: nothing sent
    cloud.sent.clear()
    await vled._async_update_data()
    assert cloud.sent == []

    # Changed in Home Assistant: written
    await vled.group_store.async_set(delay=7)
    await vled._async_update_data()
    assert cloud.sent[1][1] == {"properties": {"staggered": True, "staggered_delay": 7}}

    # Changed in the app (only the staggered sunrise): taken, offsets written
    cloud.sent.clear()
    cloud.aquariums[0]["properties"]["groups"] = [
        {"name": "rsled90", "properties": {"staggered": False, "staggered_delay": 0}}
    ]
    await vled._async_update_data()
    await hass.async_block_till_done()
    assert cloud.sent == []
    assert (vled.group_store.staggered, vled.group_store.delay) == (False, 10)
    assert _offsets(leds) == [0, 0]

    # The app changed the order: the group is set up again with it
    cloud.devices[0]["group_index"], cloud.devices[1]["group_index"] = 1, 0
    await vled._async_update_data()
    assert vled._entry.data[coord.CONF_GROUP_MEMBERS] == [
        leds[1]._entry.entry_id,
        leds[0]._entry.entry_id,
    ]
    # Being set up again: nothing more is checked meanwhile
    await vled._async_update_data()
    assert cloud.sent == []


async def test_group_cloud_refusal_and_lamp_leaving(hass: HomeAssistant) -> None:
    vled, leds, cloud = await _cloud_group(hass, 3)
    cloud.accept = False
    await vled._async_update_data()
    sent = len(cloud.sent)
    assert sent > 0 and vled.group_store.snapshot is None
    # Refused: not sent again until the group changes
    await vled._async_update_data()
    assert len(cloud.sent) == sent
    cloud.accept = True
    await vled.group_store.async_set(delay=3)
    await vled._async_update_data()
    assert vled.group_store.snapshot is not None

    # LED3 leaves the group (options): ungrouped in the cloud
    cloud.sent.clear()
    vled.member_ids = vled.member_ids[:2]
    vled._link_leds()
    await vled._async_update_data()
    ungrouped = [i for i in cloud.sent[0][1] if not i["grouped"]]
    assert [i["hwid"] for i in ungrouped] == [leds[2].model_id]


async def test_group_conflict_is_settled_by_the_user(hass: HomeAssistant) -> None:
    from custom_components.redsea.groups import ISSUE_CONFLICT

    vled, leds, cloud = await _cloud_group(hass)
    # The app already has another group of these lamps: conflict
    cloud.devices[1].update(grouped=True, group_index=0)
    await vled._async_update_data()
    assert _issue(hass, ISSUE_CONFLICT, vled) is not None
    assert cloud.sent == []
    # Home Assistant's kept: written
    await vled.async_resolve_conflict(True)
    assert cloud.sent[0][0] == "/device/manage"
    assert _issue(hass, ISSUE_CONFLICT, vled) is None
    assert cloud.devices[0]["grouped"] is True

    # Both changed since: conflict again, the app's kept this time
    cloud.devices[0]["grouped"] = False
    await vled.group_store.async_set(staggered=True)
    await vled._async_update_data()
    assert _issue(hass, ISSUE_CONFLICT, vled) is not None
    await vled.async_resolve_conflict(False)
    assert vled._entry.data[coord.CONF_GROUP_MEMBERS] == [leds[1]._entry.entry_id]
    assert _issue(hass, ISSUE_CONFLICT, vled) is None

    # Nothing to settle without the cloud
    del hass.data[DOMAIN]["cloud"]
    await vled.async_resolve_conflict(True)


async def test_group_without_cloud_account(hass: HomeAssistant) -> None:
    from custom_components.redsea.groups import ISSUE_CONFLICT, ISSUE_NO_CLOUD

    vled, _leds, cloud = await _cloud_group(hass)
    del hass.data[DOMAIN]["cloud"]
    await vled._async_update_data()
    issue = _issue(hass, ISSUE_NO_CLOUD, vled)
    assert issue is not None and issue.translation_placeholders == {"group": "VLED"}
    assert _issue(hass, ISSUE_CONFLICT, vled) is None
    # Kept local: the issue goes and does not come back
    await vled.async_keep_local()
    await vled._async_update_data()
    assert _issue(hass, ISSUE_NO_CLOUD, vled) is None
    # Nor is the group written, even once the account is there
    hass.data[DOMAIN]["cloud"] = cloud
    await vled._async_update_data()
    assert cloud.sent == []


@pytest.mark.parametrize(
    "change",
    ["other_account", "other_aquarium", "not_listed"],
)
async def test_group_the_cloud_cannot_hold(hass: HomeAssistant, change: str) -> None:
    from custom_components.redsea.groups import ISSUE_NO_CLOUD

    vled, _leds, cloud = await _cloud_group(hass)
    if change == "other_account":
        other = _Cloud([cloud.devices.pop()])
        hass.data[DOMAIN]["cloud2"] = other
    elif change == "other_aquarium":
        cloud.devices[1]["aquarium_uid"] = "aq-2"
    else:
        cloud.devices.pop()
    assert vled.cloud_context() is None
    await vled._async_update_data()
    assert _issue(hass, ISSUE_NO_CLOUD, vled) is not None


async def test_group_of_several_models(hass: HomeAssistant) -> None:
    from custom_components.redsea.groups import ISSUE_MIXED

    vled, _leds, cloud = await _cloud_group(hass, 3, ("RSLED90", "RSLED60", "RSLED90"))
    assert vled.cloud_context() is None
    # None grouped in the app: nothing to say
    await vled._async_update_data()
    assert _issue(hass, ISSUE_MIXED, vled) is None
    cloud.devices[0]["grouped"] = True
    cloud.devices[2]["grouped"] = True
    await vled._async_update_data()
    issue = _issue(hass, ISSUE_MIXED, vled)
    assert issue.translation_placeholders == {"group": "VLED", "leds": "LED1, LED3"}
    # Ungrouped in the app
    await vled.async_ungroup_in_cloud()
    assert cloud.sent[0][0] == "/device/manage"
    assert [i["hwid"] for i in cloud.sent[0][1]] == ["LED1", "LED3"]
    assert _issue(hass, ISSUE_MIXED, vled) is None
    assert not any(d["grouped"] for d in cloud.devices)


async def test_group_checks_wait_and_errors(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    vled, leds, cloud = await _cloud_group(hass)
    # Without its store, or a lamp missing: nothing checked
    store, vled.group_store = vled.group_store, None
    await vled._async_update_data()
    vled.group_store = store
    vled.member_ids.append("missing")
    assert vled.cloud_context() is None
    await vled._async_update_data()
    assert cloud.sent == []
    vled.member_ids.pop()

    # The app already holds the same group: only remembered
    for n, device in enumerate(cloud.devices):
        device.update(grouped=True, group_index=n)
    await vled._async_update_data()
    assert cloud.sent == []
    assert vled.group_store.snapshot["members"] == [led.model_id for led in leds]

    async def _boom() -> None:
        raise RuntimeError("boom")

    vled._async_group_checks = _boom  # type: ignore[method-assign]
    await vled._async_update_data()
    assert "group checks failed" in caplog.text


async def test_group_repair_flows(hass: HomeAssistant) -> None:
    from homeassistant.helpers import issue_registry as ir

    from custom_components.redsea import repairs
    from custom_components.redsea.groups import (
        ISSUE_CONFLICT,
        ISSUE_MIXED,
        ISSUE_NO_CLOUD,
    )

    vled, _leds, _cloud = await _cloud_group(hass)
    entry_id = vled._entry.entry_id
    calls: list[Any] = []

    async def _record(*args: Any) -> None:
        calls.append(args)

    vled.async_keep_local = lambda: _record("local")  # type: ignore[method-assign]
    vled.async_ungroup_in_cloud = lambda: _record("ungroup")  # type: ignore[method-assign]
    vled.async_resolve_conflict = lambda keep: _record("resolve", keep)  # type: ignore[method-assign]

    async def flow(kind: str) -> Any:
        fix = await repairs.async_create_fix_flow(
            hass, "x", {"kind": kind, "entry_id": entry_id}
        )
        fix.hass = hass
        fix.issue_id = f"{kind}_{entry_id}"  # as the repairs flow manager does
        return fix

    # The steps show the issue's text: its placeholders are given to them
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_NO_CLOUD}_{entry_id}",
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_NO_CLOUD,
        translation_placeholders={"group": "VLED"},
    )
    fix = await flow(ISSUE_NO_CLOUD)
    step = await fix.async_step_init()
    assert step["step_id"] == "keep_local"
    assert step["description_placeholders"] == {"group": "VLED"}
    assert (await fix.async_step_keep_local({}))["type"] == "create_entry"
    fix = await flow(ISSUE_MIXED)
    assert (await fix.async_step_init())["step_id"] == "ungroup"
    assert (await fix.async_step_ungroup({}))["type"] == "create_entry"
    fix = await flow(ISSUE_CONFLICT)
    menu = await fix.async_step_init()
    assert menu["menu_options"] == ["keep_home_assistant", "keep_reefbeat"]
    assert menu["description_placeholders"] == {}  # no issue (any more)
    await fix.async_step_keep_home_assistant()
    await fix.async_step_keep_reefbeat()
    assert calls == [("local",), ("ungroup",), ("resolve", True), ("resolve", False)]

    # The group not loaded (any more): nothing to fix
    del hass.data[DOMAIN][entry_id]
    fix = await flow(ISSUE_NO_CLOUD)
    for step in (
        fix.async_step_init(),
        fix.async_step_keep_local({}),
        fix.async_step_keep_reefbeat(),
    ):
        assert (await step)["reason"] == "group_not_loaded"
    fix = await repairs.async_create_fix_flow(hass, "x", None)
    assert cast(Any, fix)._entry_id == "None"


async def test_lamp_lists_the_lamps_of_its_group(hass: HomeAssistant) -> None:
    led1 = _member(hass, "LED1")
    led2 = _member(hass, "LED2")
    assert led1.linked_leds() == []
    vled = _group(hass, [led2, led1])
    listed = led1.linked_leds()
    assert listed == vled.linked_leds()
    assert [lamp["name"] for lamp in listed] == ["LED2", "LED1"]


async def test_new_group_takes_the_one_of_the_app(hass: HomeAssistant) -> None:
    """A group made in HA of the lamps the app groups: the app's order and
    staggered sunrise are taken (as the ReefBeat cloud gives them)."""
    vled, leds, cloud = await _cloud_group(hass)
    cloud.devices[0].update(grouped=True, group_index=1)
    cloud.devices[1].update(grouped=True, group_index=0)
    cloud.aquariums[0]["properties"]["groups"] = [
        {"name": "rsled90", "properties": {"staggered": True, "staggered_delay": 10}}
    ]
    await vled._async_update_data()
    assert cloud.sent == []
    assert (vled.group_store.staggered, vled.group_store.delay) == (True, 10)
    assert vled._entry.data[coord.CONF_GROUP_MEMBERS] == [
        leds[1]._entry.entry_id,
        leds[0]._entry.entry_id,
    ]


async def test_cloud_proposes_the_groups_of_the_app(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A group of the ReefBeat app no virtual LED drives is proposed once;
    again when the virtual LED that took it goes away."""
    leds = [_member(hass, f"LED{n + 1}") for n in range(3)]
    cloud = _Cloud(
        [
            _device("LED1", grouped=True, group_index=1),
            _device("LED2", grouped=True, group_index=0),
            _device("LED3", "RSLED160", grouped=True),  # alone of its model
            _device("unknown", grouped=True),
        ]
    )
    cloud._hass = hass
    cloud._proposed = set()
    # Device IPs are not followed here (see test_cloud_devices_unit.py)
    cloud._entry = cast(Any, SimpleNamespace(data={"ip_update": "off"}))
    cloud.aquariums[0]["name"] = "Reef"
    hass.data[DOMAIN]["cloud"] = cloud
    started: list[tuple[Any, ...]] = []

    async def _init(domain: str, *, context: Any, data: Any) -> None:
        started.append((domain, context, data))

    monkeypatch.setattr(hass.config_entries.flow, "async_init", _init)

    async def _fetched(_self: Any) -> dict[str, Any]:
        return {"fetched": True}

    monkeypatch.setattr(coord.ReefBeatCoordinator, "_async_update_data", _fetched)

    assert await cloud._async_update_data() == {"fetched": True}
    await hass.async_block_till_done()
    assert started == [
        (
            DOMAIN,
            {"source": "integration_discovery"},
            {
                "aquarium_uid": AQ,
                "aquarium": "Reef",
                "model": "RSLED90",
                CONF_GROUP_MEMBERS: [
                    leds[1]._entry.entry_id,
                    leds[0]._entry.entry_id,
                ],
            },
        )
    ]
    # Proposed once
    await cloud._async_update_data()
    await hass.async_block_till_done()
    assert len(started) == 1

    # A virtual LED takes a lamp of it: no longer proposed...
    vled = _group(hass, [leds[0], leds[2]])
    await cloud._async_update_data()
    assert cloud._proposed == set()
    # ... until it goes away (an unnamed aquarium: its uid)
    await hass.config_entries.async_remove(vled._entry.entry_id)
    del cloud.aquariums[0]["name"]
    await cloud._async_update_data()
    await hass.async_block_till_done()
    assert len(started) == 2
    assert started[1][2]["aquarium"] == AQ


async def test_settings_turned_off_and_shown_on_the_whole_group(
    hass: HomeAssistant,
) -> None:
    """The acclimation (or the moon phase) is shared: turned off on a lamp,
    it is on each lamp of its group, and what they make of a write is shown
    at once on all of them (optimistic update)."""
    alone = _member(hass, "ALONE")
    await alone.delete("/acclimation")
    alone.expect_settings("/acclimation", False)
    api = cast(_RecApi, alone.my_api)
    assert (api.deletes, api.expected) == (
        ["/acclimation"],
        [("/acclimation", False)],
    )

    vled, leds = await _grouped(hass, 2)
    apis = [cast(_RecApi, led.my_api) for led in leds]
    await leds[1].delete("/acclimation")
    assert [a.deletes for a in apis] == [["/acclimation"], ["/acclimation"]]
    # Not shared: on the lamp only
    await leds[1].delete("/firmware")
    assert [a.deletes[1:] for a in apis] == [[], ["/firmware"]]

    told: list[str] = []
    for lamp in (*leds, vled):
        lamp.async_add_listener(lambda name=lamp.title: told.append(name))
    leds[0].expect_settings("/moonphase", True)
    assert [a.expected for a in apis] == [[("/moonphase", True)]] * 2
    assert sorted(told) == sorted([leds[0].title, leds[1].title, vled.title])
    # Written on the group itself
    vled.expect_settings("/acclimation", True)
    assert [a.expected[-1] for a in apis] == [("/acclimation", True)] * 2


async def test_group_colour_light_reaches_g1_and_g2(hass: HomeAssistant) -> None:
    """The group's colour light, moved alone, is posted to each of its lamps."""
    from custom_components.redsea.light import VIRTUAL_LIGHTS, ReefLedLightEntity
    from custom_components.redsea.reefbeat.led import ReefLedAPI

    sent: dict[str, list[Any]] = {}

    def _lamp(title: str, hw: str, g2: bool) -> Any:
        led = _member(hass, title, hw_model=hw, g2=g2)
        api = ReefLedAPI("192.0.2.20", False, cast(Any, object()), hw)
        manual = {"white": 10, "blue": 20, "moon": 0}
        if g2:
            manual |= {"kelvin": 12000, "intensity": 30}
        else:
            api.data["local"]["manual_trick"] = {"kelvin": 12000, "intensity": 30}
        api.add_source("/manual", "data", manual)
        sent[title] = []

        async def _send(_url: str, payload: Any, _method: str) -> Any:
            sent[title].append(dict(payload))
            return {"ok": True}

        api._http_send = _send  # type: ignore[method-assign]
        led.my_api = api
        return led

    g1 = _lamp("LED1", "RSLED160", False)
    g2 = _lamp("LED2", "RSLED115", True)
    vled = _group(hass, [g1, g2])
    vled.async_request_refresh = _noop  # type: ignore[method-assign]
    light = ReefLedLightEntity(vled, VIRTUAL_LIGHTS[0])
    light.hass = hass
    light.async_write_ha_state = lambda: None  # type: ignore[method-assign]

    await light.async_turn_on(color_temp_kelvin=15000)
    assert sent["LED2"][-1] == {"kelvin": 15000, "intensity": 30, "moon": 0}
    # Set through the G1 path only (an older group light): each lamp at its
    # own path all the same
    vled.set_data("$.local.manual_trick.intensity", 50)
    await vled.push_values("/manual", "post")
    assert sent["LED2"][-1] == {"kelvin": 15000, "intensity": 50, "moon": 0}
    await light.async_turn_on(brightness=200)
    assert sent["LED2"][-1] == {"kelvin": 15000, "intensity": 78, "moon": 0}
    assert len(sent["LED1"]) == 3
