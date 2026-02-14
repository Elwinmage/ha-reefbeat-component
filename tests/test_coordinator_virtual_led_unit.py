from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.coordinator as coord
from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    LINKED_LED,
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

        def get_data(self, _name: str, _is_None_possible: bool = False) -> Any:  # noqa: N803
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
    data: dict[str, Any] = {
        CONFIG_FLOW_IP_ADDRESS: ip,
        CONFIG_FLOW_HW_MODEL: hw_model,
        CONFIG_FLOW_CONFIG_TYPE: False,
        CONFIG_FLOW_INTENSITY_COMPENSATION: False,
    }
    if linked is not None:
        data[LINKED_LED] = linked
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

    my_api: Any = field(default_factory=_FakeAPI)

    get_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)
    pushed: list[tuple[str, str]] = field(default_factory=list)
    pressed: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    configs: list[str | None] = field(default_factory=list)
    posted: list[str] = field(default_factory=list)
    refresh_calls: list[tuple[str | None, int]] = field(default_factory=list)

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
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
    # This string format is only used by the init-time "split('-')[1]" check.
    entry = _make_entry(
        title="VLED", ip="192.0.2.10", hw_model="RSLED50", linked=["x-RSLED60"]
    )

    # Avoid auto-linking (so we don't need hass.data setup).
    hass.state = "STARTING"  # type: ignore[assignment]

    vled = coord.ReefVirtualLedCoordinator(hass, cast(Any, entry))
    assert vled.only_g1 is False


def test_virtual_led_init_running_calls_link_leds(hass: HomeAssistant) -> None:
    hass.data.setdefault(DOMAIN, {})
    led1 = _LinkedLed(title="LED1", is_g1=True)
    hass.data[DOMAIN]["id1"] = led1

    # Ensure parsing works and __init__ RUNNING path can call _link_leds.
    entry = _make_entry(
        title="VLED",
        ip="192.0.2.10",
        hw_model="RSLED50",
        linked=["0 LED1-RSLED50 (id1)"],
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
        linked=["0 LED1-RSLED50 (id1)"],
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
        _LinkedLed(title="A", is_g1=True, get_map={"$.u": [1, 2]})
    ]

    seen: list[str] = []

    def _warn(msg: str, *args: Any, **_kwargs: Any) -> None:
        seen.append(msg % args)

    monkeypatch.setattr(coord._LOGGER, "warning", _warn, raising=True)

    assert vled.get_data("$.u") == [1, 2]
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
