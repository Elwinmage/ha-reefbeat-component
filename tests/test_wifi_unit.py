"""Unit tests for the Wi-Fi provisioning helpers (custom_components.redsea.wifi)."""

from __future__ import annotations

import asyncio
from typing import Any, cast
from unittest.mock import MagicMock

import aiohttp
import pytest

from custom_components.redsea import wifi as wifi_module
from custom_components.redsea.auto_detect import ReefBeatInfo
from custom_components.redsea.wifi import (
    _match_device,
    connect_wifi,
    get_current_ssid,
    rediscover_device,
    reset_device,
    scan_wifi,
)

# =============================================================================
# aiohttp session fakes
# =============================================================================


class _FakeResponse:
    """Minimal async context manager mimicking aiohttp response objects."""

    def __init__(
        self,
        *,
        status: int = 200,
        json_body: Any = None,
        text: str = "",
        raise_on_call: Exception | None = None,
    ) -> None:
        self.status = status
        self._json = json_body
        self._text = text
        self._raise = raise_on_call

    async def __aenter__(self) -> _FakeResponse:  # noqa: PYI034
        if self._raise is not None:
            raise self._raise
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=self.status,
            )

    async def json(self, content_type: Any = None) -> Any:
        return self._json

    async def text(self) -> str:
        return self._text


class _FakeSession:
    """Records calls and returns pre-programmed responses."""

    def __init__(
        self,
        *,
        get_response: _FakeResponse | None = None,
        post_response: _FakeResponse | None = None,
        raise_on_get: Exception | None = None,
        raise_on_post: Exception | None = None,
    ) -> None:
        self._get_response = get_response
        self._post_response = post_response
        self._raise_on_get = raise_on_get
        self._raise_on_post = raise_on_post
        self.get_calls: list[tuple[str, dict[str, Any]]] = []
        self.post_calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.get_calls.append((url, kwargs))
        if self._raise_on_get is not None:
            # Simulate a "cannot even start the request" error.
            resp = _FakeResponse(raise_on_call=self._raise_on_get)
            return resp
        assert self._get_response is not None
        return self._get_response

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.post_calls.append((url, kwargs))
        if self._raise_on_post is not None:
            resp = _FakeResponse(raise_on_call=self._raise_on_post)
            return resp
        assert self._post_response is not None
        return self._post_response


# =============================================================================
# scan_wifi
# =============================================================================


@pytest.mark.asyncio
async def test_scan_wifi_success() -> None:
    """A valid /wifi/scan payload is parsed, sorted, and deduplicated."""
    payload = {
        "networks": [
            {
                "ssid": "WEAK",
                "channel": 1,
                "bssid": "00:00:00:00:00:01",
                "signal_dBm": -80,
                "security": "WPA2_PSK",
            },
            {
                "ssid": "ELWINMAGE",
                "channel": 9,
                "bssid": "9A:18:65:72:D8:70",
                "signal_dBm": -36,
                "security": "WPA2_PSK",
            },
            {
                "ssid": "ELWINMAGE",
                "channel": 9,
                "bssid": "9A:18:65:72:F0:C9",
                "signal_dBm": -71,
                "security": "WPA2_PSK",
            },
        ],
        "total_networks_found": 3,
        "success": True,
    }

    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    networks = await scan_wifi(cast(Any, session), "10.0.0.5")

    assert [n["ssid"] for n in networks] == ["ELWINMAGE", "WEAK"]
    # De-duplication kept the stronger signal (-36 vs -71).
    elwin = next(n for n in networks if n["ssid"] == "ELWINMAGE")
    assert elwin["signal_dBm"] == -36
    # Session called the expected URL.
    assert session.get_calls[0][0] == "http://10.0.0.5/wifi/scan"


@pytest.mark.asyncio
async def test_scan_wifi_skips_hidden_ssids() -> None:
    """Networks with an empty or missing SSID are dropped."""
    payload = {
        "networks": [
            {"ssid": "", "signal_dBm": -50, "security": "WPA2_PSK"},
            {"signal_dBm": -55, "security": "WPA2_PSK"},
            {"ssid": "OK", "signal_dBm": -60, "security": "WPA2_PSK"},
        ]
    }
    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    networks = await scan_wifi(cast(Any, session), "10.0.0.5")

    assert [n["ssid"] for n in networks] == ["OK"]


@pytest.mark.asyncio
async def test_scan_wifi_empty_list() -> None:
    """An empty networks list is returned as an empty result (no error)."""
    session = _FakeSession(get_response=_FakeResponse(json_body={"networks": []}))
    networks = await scan_wifi(cast(Any, session), "10.0.0.5")
    assert networks == []


@pytest.mark.asyncio
async def test_scan_wifi_bad_payload_type_raises() -> None:
    """Non-dict payloads raise so the caller can surface a friendly error."""
    session = _FakeSession(get_response=_FakeResponse(json_body=["not", "a", "dict"]))
    with pytest.raises(TypeError):
        await scan_wifi(cast(Any, session), "10.0.0.5")


@pytest.mark.asyncio
async def test_scan_wifi_bad_networks_type_raises() -> None:
    """Non-list `networks` raises."""
    session = _FakeSession(
        get_response=_FakeResponse(json_body={"networks": "not-a-list"})
    )
    with pytest.raises(TypeError):
        await scan_wifi(cast(Any, session), "10.0.0.5")


@pytest.mark.asyncio
async def test_scan_wifi_http_error_raises() -> None:
    """HTTP errors bubble up so the caller can decide how to react."""
    session = _FakeSession(get_response=_FakeResponse(status=500, json_body={}))
    with pytest.raises(aiohttp.ClientResponseError):
        await scan_wifi(cast(Any, session), "10.0.0.5")


@pytest.mark.asyncio
async def test_scan_wifi_signal_missing_still_ranks() -> None:
    """Networks with a missing signal go to the bottom of the list."""
    payload = {
        "networks": [
            {"ssid": "A", "signal_dBm": -70, "security": "WPA2_PSK"},
            {"ssid": "B", "security": "WPA2_PSK"},  # no signal_dBm
        ]
    }
    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    networks = await scan_wifi(cast(Any, session), "10.0.0.5")
    assert [n["ssid"] for n in networks] == ["A", "B"]


@pytest.mark.asyncio
async def test_scan_wifi_skips_non_dict_entries() -> None:
    """Non-dict entries in the networks list are silently dropped."""
    payload = {
        "networks": [
            {"ssid": "OK", "signal_dBm": -50, "security": "WPA2_PSK"},
            "not-a-dict",
            42,
        ]
    }
    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    networks = await scan_wifi(cast(Any, session), "10.0.0.5")
    assert [n["ssid"] for n in networks] == ["OK"]


@pytest.mark.asyncio
async def test_scan_wifi_dedup_keeps_higher_signal_only() -> None:
    """When the second occurrence has a weaker signal, the first stays."""
    payload = {
        "networks": [
            {"ssid": "X", "signal_dBm": -30, "security": "WPA2_PSK"},
            {"ssid": "X", "signal_dBm": -80, "security": "WPA2_PSK"},
        ]
    }
    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    networks = await scan_wifi(cast(Any, session), "10.0.0.5")
    assert len(networks) == 1
    assert networks[0]["signal_dBm"] == -30


# =============================================================================
# get_current_ssid
# =============================================================================


@pytest.mark.asyncio
async def test_get_current_ssid_returns_connected_ssid() -> None:
    """A connected /wifi payload yields the active SSID."""
    payload = {
        "ssid": "ELWINMAGE",
        "is_connected": True,
        "signal_dBm": -59,
        "ip": "10.40.101.50",
    }
    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    ssid = await get_current_ssid(cast(Any, session), "10.0.0.5")
    assert ssid == "ELWINMAGE"
    # Reads the /wifi endpoint, not /wifi/scan.
    assert session.get_calls[0][0] == "http://10.0.0.5/wifi"


@pytest.mark.asyncio
async def test_get_current_ssid_accepts_camelcase_flag() -> None:
    """Firmwares exposing only isConnected (camelCase) still work."""
    payload = {"ssid": "ELWINMAGE", "isConnected": True}
    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    assert await get_current_ssid(cast(Any, session), "10.0.0.5") == "ELWINMAGE"


@pytest.mark.asyncio
async def test_get_current_ssid_missing_flag_trusts_ssid() -> None:
    """When no connected flag is present, a non-empty ssid is trusted."""
    payload = {"ssid": "ELWINMAGE"}
    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    assert await get_current_ssid(cast(Any, session), "10.0.0.5") == "ELWINMAGE"


@pytest.mark.asyncio
async def test_get_current_ssid_not_connected_returns_none() -> None:
    """An explicitly disconnected device yields None (stale ssid ignored)."""
    payload = {"ssid": "OLD_SSID", "is_connected": False}
    session = _FakeSession(get_response=_FakeResponse(json_body=payload))
    assert await get_current_ssid(cast(Any, session), "10.0.0.5") is None


@pytest.mark.asyncio
async def test_get_current_ssid_empty_ssid_returns_none() -> None:
    """A blank or missing ssid yields None."""
    session = _FakeSession(
        get_response=_FakeResponse(json_body={"ssid": "", "is_connected": True})
    )
    assert await get_current_ssid(cast(Any, session), "10.0.0.5") is None

    session2 = _FakeSession(
        get_response=_FakeResponse(json_body={"is_connected": True})
    )
    assert await get_current_ssid(cast(Any, session2), "10.0.0.5") is None


@pytest.mark.asyncio
async def test_get_current_ssid_http_error_returns_none() -> None:
    """HTTP errors are swallowed (older firmware may lack /wifi)."""
    session = _FakeSession(get_response=_FakeResponse(status=404, json_body={}))
    assert await get_current_ssid(cast(Any, session), "10.0.0.5") is None


@pytest.mark.asyncio
async def test_get_current_ssid_network_error_returns_none() -> None:
    """Connection errors never propagate out of get_current_ssid."""
    session = _FakeSession(raise_on_get=aiohttp.ClientError("boom"))
    assert await get_current_ssid(cast(Any, session), "10.0.0.5") is None


@pytest.mark.asyncio
async def test_get_current_ssid_bad_payload_returns_none() -> None:
    """A non-dict payload yields None instead of raising."""
    session = _FakeSession(get_response=_FakeResponse(json_body=["not", "a", "dict"]))
    assert await get_current_ssid(cast(Any, session), "10.0.0.5") is None


# =============================================================================
# connect_wifi
# =============================================================================


@pytest.mark.asyncio
async def test_connect_wifi_success() -> None:
    """A 2xx response counts as success and the URL/body are honoured."""
    session = _FakeSession(post_response=_FakeResponse(status=200, text="ok"))
    ok = await connect_wifi(cast(Any, session), "10.0.0.5", "MYSSID", "s3cret")

    assert ok is True
    assert session.post_calls[0][0] == "http://10.0.0.5/wifi/connect"
    kwargs = session.post_calls[0][1]
    assert kwargs["json"] == {"ssid": "MYSSID", "password": "s3cret"}


@pytest.mark.asyncio
async def test_connect_wifi_non_2xx() -> None:
    """Non-2xx status returns False without raising."""
    session = _FakeSession(post_response=_FakeResponse(status=401, text="denied"))
    ok = await connect_wifi(cast(Any, session), "10.0.0.5", "MYSSID", "wrong")
    assert ok is False


@pytest.mark.asyncio
async def test_connect_wifi_network_error() -> None:
    """A network error returns False (never propagates)."""
    session = _FakeSession(raise_on_post=aiohttp.ClientConnectionError("boom"))
    ok = await connect_wifi(cast(Any, session), "10.0.0.5", "MYSSID", "pw")
    assert ok is False


@pytest.mark.asyncio
async def test_connect_wifi_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """A timeout is caught and the function returns False."""

    # Patch WIFI_CONNECT_TIMEOUT so this test remains fast even under pressure.
    monkeypatch.setattr(wifi_module, "WIFI_CONNECT_TIMEOUT", 0.01)

    class _SlowPostCM:
        """Async CM whose entry blocks long enough to trip the timeout."""

        async def __aenter__(self) -> Any:
            await asyncio.sleep(1)
            raise RuntimeError("should not reach here")

        async def __aexit__(self, *_exc: Any) -> bool:
            return False

    session = MagicMock()
    session.post = MagicMock(return_value=_SlowPostCM())

    ok = await connect_wifi(cast(Any, session), "10.0.0.5", "MYSSID", "pw")
    assert ok is False


# =============================================================================
# reset_device
# =============================================================================


@pytest.mark.asyncio
async def test_reset_device_success() -> None:
    """A 2xx response counts as success."""
    session = _FakeSession(post_response=_FakeResponse(status=200))
    ok = await reset_device(cast(Any, session), "10.0.0.5")
    assert ok is True
    assert session.post_calls[0][0] == "http://10.0.0.5/reset"


@pytest.mark.asyncio
async def test_reset_device_connection_error_is_success() -> None:
    """A dropped connection is the expected reboot outcome — treat as success."""
    session = _FakeSession(raise_on_post=aiohttp.ClientConnectionError("closed"))
    ok = await reset_device(cast(Any, session), "10.0.0.5")
    assert ok is True


@pytest.mark.asyncio
async def test_reset_device_timeout_is_success() -> None:
    """A timeout also counts as success (device restarting mid-response)."""
    session = _FakeSession(raise_on_post=asyncio.TimeoutError())
    ok = await reset_device(cast(Any, session), "10.0.0.5")
    assert ok is True


@pytest.mark.asyncio
async def test_reset_device_unexpected_error() -> None:
    """A truly unexpected error is reported as failure."""
    session = _FakeSession(raise_on_post=RuntimeError("unexpected"))
    ok = await reset_device(cast(Any, session), "10.0.0.5")
    assert ok is False


# =============================================================================
# _match_device
# =============================================================================


def test_match_device_by_uuid_wins() -> None:
    """UUID takes precedence over other fields."""
    devices: list[ReefBeatInfo] = [
        {"ip": "1.2.3.4", "hw_model": "RSLED160", "friendly_name": "A", "uuid": "u1"},
        {"ip": "1.2.3.5", "hw_model": "RSLED160", "friendly_name": "A", "uuid": "u2"},
    ]
    match = _match_device(devices, uuid="u2", hw_model=None, friendly_name=None)
    assert match is not None
    assert match.get("ip") == "1.2.3.5"


def test_match_device_falls_back_to_hw_and_name() -> None:
    """When UUID is unknown, hw_model + friendly_name are used."""
    devices: list[ReefBeatInfo] = [
        {
            "ip": "1.2.3.4",
            "hw_model": "RSLED160",
            "friendly_name": "Sump",
            "uuid": "u1",
        },
        {
            "ip": "1.2.3.5",
            "hw_model": "RSLED160",
            "friendly_name": "Display",
            "uuid": "u2",
        },
    ]
    match = _match_device(
        devices, uuid=None, hw_model="RSLED160", friendly_name="Display"
    )
    assert match is not None
    assert match.get("ip") == "1.2.3.5"


def test_match_device_none_when_no_criteria() -> None:
    """Without a UUID or hw+name we refuse to guess."""
    devices: list[ReefBeatInfo] = [
        {"ip": "1.2.3.4", "hw_model": "RSLED160", "friendly_name": "A", "uuid": "u1"},
    ]
    assert _match_device(devices, uuid=None, hw_model=None, friendly_name=None) is None


def test_match_device_none_when_hw_alone_would_collide() -> None:
    """We never fall back to hw_model alone: two matches would be dangerous."""
    devices: list[ReefBeatInfo] = [
        {"ip": "1.2.3.4", "hw_model": "RSLED160", "friendly_name": "A", "uuid": "u1"},
        {"ip": "1.2.3.5", "hw_model": "RSLED160", "friendly_name": "B", "uuid": "u2"},
    ]
    # Only friendly_name known — refuse.
    assert _match_device(devices, uuid=None, hw_model=None, friendly_name="B") is None
    # Only hw_model known — refuse.
    assert (
        _match_device(devices, uuid=None, hw_model="RSLED160", friendly_name=None)
        is None
    )


def test_match_device_none_when_no_device_matches() -> None:
    """Empty devices list gracefully returns None."""
    assert _match_device([], uuid="u1", hw_model="X", friendly_name="Y") is None


# =============================================================================
# rediscover_device
# =============================================================================


class _HassStub:
    """Minimal stand-in for Home Assistant supporting only executor_job."""

    async def async_add_executor_job(self, func: Any, *args: Any) -> Any:
        # Directly invoke the target; the test double is synchronous.
        return func(*args)


@pytest.mark.asyncio
async def test_rediscover_device_finds_on_first_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single scan is enough when the device is already back on the LAN."""
    devices: list[ReefBeatInfo] = [
        {
            "ip": "10.0.0.42",
            "hw_model": "RSLED160",
            "friendly_name": "Sump",
            "uuid": "u1",
        },
    ]

    def _fake_get_reefbeats(subnetwork: Any = None) -> list[ReefBeatInfo]:
        return devices

    sleep_calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(wifi_module, "get_reefbeats", _fake_get_reefbeats)
    monkeypatch.setattr(wifi_module.asyncio, "sleep", _fake_sleep)

    ip = await rediscover_device(
        hass=_HassStub(),
        uuid="u1",
        hw_model="RSLED160",
        friendly_name="Sump",
        max_attempts=5,
        interval=10,
    )

    assert ip == "10.0.0.42"
    # Found on the first attempt — no sleep should have been called.
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_rediscover_device_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Device shows up after a couple of failed attempts."""
    attempts = {"n": 0}

    def _fake_get_reefbeats(subnetwork: Any = None) -> list[ReefBeatInfo]:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return []
        return [
            {"ip": "10.0.0.99", "hw_model": "X", "friendly_name": "Y", "uuid": "u42"},
        ]

    async def _fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(wifi_module, "get_reefbeats", _fake_get_reefbeats)
    monkeypatch.setattr(wifi_module.asyncio, "sleep", _fake_sleep)

    ip = await rediscover_device(
        hass=_HassStub(),
        uuid="u42",
        hw_model=None,
        friendly_name=None,
        max_attempts=5,
        interval=1,
    )
    assert ip == "10.0.0.99"
    assert attempts["n"] == 3


@pytest.mark.asyncio
async def test_rediscover_device_gives_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns None after max_attempts exhausted."""
    calls: list[int] = []

    def _fake_get_reefbeats(subnetwork: Any = None) -> list[ReefBeatInfo]:
        calls.append(1)
        return []

    async def _fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(wifi_module, "get_reefbeats", _fake_get_reefbeats)
    monkeypatch.setattr(wifi_module.asyncio, "sleep", _fake_sleep)

    ip = await rediscover_device(
        hass=_HassStub(),
        uuid="u1",
        hw_model="X",
        friendly_name="Y",
        max_attempts=3,
        interval=1,
    )
    assert ip is None
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_rediscover_device_tolerates_scan_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raised exception in one scan is treated as an empty result."""
    calls = {"n": 0}

    def _fake_get_reefbeats(subnetwork: Any = None) -> list[ReefBeatInfo]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("nic offline")
        return [
            {"ip": "10.0.0.7", "hw_model": "X", "friendly_name": "Y", "uuid": "u1"},
        ]

    async def _fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(wifi_module, "get_reefbeats", _fake_get_reefbeats)
    monkeypatch.setattr(wifi_module.asyncio, "sleep", _fake_sleep)

    ip = await rediscover_device(
        hass=_HassStub(),
        uuid="u1",
        hw_model=None,
        friendly_name=None,
        max_attempts=3,
        interval=1,
    )
    assert ip == "10.0.0.7"


@pytest.mark.asyncio
async def test_rediscover_device_ignores_empty_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A match with an empty IP does not count as found."""
    calls = {"n": 0}

    def _fake_get_reefbeats(subnetwork: Any = None) -> list[ReefBeatInfo]:
        calls["n"] += 1
        if calls["n"] == 1:
            # Match by uuid but empty IP — should be ignored and retried.
            return [{"ip": "", "hw_model": "X", "friendly_name": "Y", "uuid": "u1"}]
        return [{"ip": "10.0.0.7", "hw_model": "X", "friendly_name": "Y", "uuid": "u1"}]

    async def _fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(wifi_module, "get_reefbeats", _fake_get_reefbeats)
    monkeypatch.setattr(wifi_module.asyncio, "sleep", _fake_sleep)

    ip = await rediscover_device(
        hass=_HassStub(),
        uuid="u1",
        hw_model=None,
        friendly_name=None,
        max_attempts=3,
        interval=1,
    )
    assert ip == "10.0.0.7"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_rediscover_device_iterates_subnetworks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every subnet in the list is scanned within each attempt."""
    seen_subnets: list[Any] = []

    def _fake_get_reefbeats(subnetwork: Any = None) -> list[ReefBeatInfo]:
        seen_subnets.append(subnetwork)
        # Only the third subnet contains the device.
        if subnetwork == "10.0.0.0/24":
            return [
                {
                    "ip": "10.0.0.42",
                    "hw_model": "X",
                    "friendly_name": "Y",
                    "uuid": "u1",
                },
            ]
        return []

    async def _fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(wifi_module, "get_reefbeats", _fake_get_reefbeats)
    monkeypatch.setattr(wifi_module.asyncio, "sleep", _fake_sleep)

    ip = await rediscover_device(
        hass=_HassStub(),
        uuid="u1",
        hw_model=None,
        friendly_name=None,
        max_attempts=3,
        interval=1,
        subnetworks=[None, "192.168.1.0/24", "10.0.0.0/24"],
    )
    assert ip == "10.0.0.42"
    # We scanned in order; found on the third subnet of the first attempt.
    assert seen_subnets == [None, "192.168.1.0/24", "10.0.0.0/24"]


@pytest.mark.asyncio
async def test_rediscover_device_multi_subnet_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multi-subnet mode gives up after ``max_attempts`` cycles like single-subnet."""
    scan_count = {"n": 0}

    def _fake_get_reefbeats(subnetwork: Any = None) -> list[ReefBeatInfo]:
        scan_count["n"] += 1
        return []

    async def _fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(wifi_module, "get_reefbeats", _fake_get_reefbeats)
    monkeypatch.setattr(wifi_module.asyncio, "sleep", _fake_sleep)

    ip = await rediscover_device(
        hass=_HassStub(),
        uuid="u1",
        hw_model=None,
        friendly_name=None,
        max_attempts=2,
        interval=1,
        subnetworks=[None, "192.168.1.0/24"],
    )
    assert ip is None
    # 2 attempts × 2 subnets = 4 scans in total.
    assert scan_count["n"] == 4


# =============================================================================
# auto_detect.list_local_subnets / is_valid_cidr
# =============================================================================


def test_is_valid_cidr_accepts_typical_forms() -> None:
    """Standard CIDRs, bare addresses, and various masks are accepted."""
    from custom_components.redsea.auto_detect import is_valid_cidr

    assert is_valid_cidr("10.0.0.0/24") is True
    assert is_valid_cidr("192.168.1.0/16") is True
    assert is_valid_cidr("172.20.0.0/12") is True
    # Bare address is accepted (strict=False → interpreted as /32).
    assert is_valid_cidr("192.168.1.42") is True
    # Leading/trailing whitespace tolerated.
    assert is_valid_cidr("  10.0.0.0/24  ") is True


def test_is_valid_cidr_rejects_bogus_input() -> None:
    """Non-CIDR strings, IPv6, and non-string input are rejected."""
    from custom_components.redsea.auto_detect import is_valid_cidr

    assert is_valid_cidr("not-a-cidr") is False
    assert is_valid_cidr("") is False
    assert is_valid_cidr("192.168.1.256/24") is False  # invalid octet
    assert is_valid_cidr("10.0.0.0/33") is False  # invalid prefix
    # IPv6 is intentionally NOT accepted — the integration is IPv4-only.
    assert is_valid_cidr("2001:db8::/32") is False


def test_list_local_subnets_returns_empty_when_netifaces_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When netifaces is unavailable the function degrades cleanly."""
    from custom_components.redsea import auto_detect

    monkeypatch.setattr(auto_detect, "netifaces", None)
    assert auto_detect.list_local_subnets() == []


def _make_netifaces_stub(interfaces_data: dict[str, list[dict[str, str]]]) -> Any:
    """Build a fake netifaces module exposing the tiny subset we consume."""
    from types import SimpleNamespace

    def _ifaddresses(iface: str) -> dict[int, list[dict[str, str]]]:
        return {2: interfaces_data.get(iface, [])}  # 2 == AF_INET

    return SimpleNamespace(
        interfaces=lambda: list(interfaces_data.keys()),
        ifaddresses=_ifaddresses,
        AF_INET=2,
    )


def test_list_local_subnets_enumerates_ipv4_networks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every valid, sane IPv4 interface contributes exactly one CIDR."""
    from custom_components.redsea import auto_detect

    stub = _make_netifaces_stub(
        {
            "eth0": [{"addr": "192.168.1.10", "netmask": "255.255.255.0"}],
            "eth1": [{"addr": "10.0.0.5", "netmask": "255.255.255.0"}],
        }
    )
    monkeypatch.setattr(auto_detect, "netifaces", stub)

    subnets = auto_detect.list_local_subnets()
    assert set(subnets) == {"192.168.1.0/24", "10.0.0.0/24"}


def test_list_local_subnets_skips_loopback_and_linklocal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loopback and 169.254/16 are excluded from the returned CIDRs."""
    from custom_components.redsea import auto_detect

    stub = _make_netifaces_stub(
        {
            "lo": [{"addr": "127.0.0.1", "netmask": "255.0.0.0"}],
            "link": [{"addr": "169.254.10.20", "netmask": "255.255.0.0"}],
            "eth0": [{"addr": "192.168.1.10", "netmask": "255.255.255.0"}],
        }
    )
    monkeypatch.setattr(auto_detect, "netifaces", stub)

    subnets = auto_detect.list_local_subnets()
    assert subnets == ["192.168.1.0/24"]


def test_list_local_subnets_skips_oversized_and_p2p(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """/32 (point-to-point) and networks larger than /24 are dropped for auto-scan."""
    from custom_components.redsea import auto_detect

    stub = _make_netifaces_stub(
        {
            "docker0": [{"addr": "172.17.0.1", "netmask": "255.255.0.0"}],  # /16
            "ppp0": [{"addr": "10.100.0.1", "netmask": "255.255.255.255"}],  # /32
            "eth0": [{"addr": "192.168.1.10", "netmask": "255.255.255.0"}],  # /24
        }
    )
    monkeypatch.setattr(auto_detect, "netifaces", stub)

    subnets = auto_detect.list_local_subnets()
    assert subnets == ["192.168.1.0/24"]


def test_list_local_subnets_deduplicates_identical_cidrs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two interfaces on the same subnet contribute a single CIDR."""
    from custom_components.redsea import auto_detect

    stub = _make_netifaces_stub(
        {
            "eth0": [{"addr": "192.168.1.10", "netmask": "255.255.255.0"}],
            "eth1": [{"addr": "192.168.1.20", "netmask": "255.255.255.0"}],
        }
    )
    monkeypatch.setattr(auto_detect, "netifaces", stub)

    assert auto_detect.list_local_subnets() == ["192.168.1.0/24"]


def test_list_local_subnets_tolerates_broken_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing/misformatted addresses do not break enumeration of the rest."""
    from custom_components.redsea import auto_detect

    stub = _make_netifaces_stub(
        {
            "broken1": [{"addr": None, "netmask": "255.255.255.0"}],  # type: ignore[dict-item]
            "broken2": [{"addr": "not-an-ip", "netmask": "255.255.255.0"}],
            "broken3": [{"addr": "192.168.1.10", "netmask": "bad-mask"}],
            "eth0": [{"addr": "10.0.0.5", "netmask": "255.255.255.0"}],
        }
    )
    monkeypatch.setattr(auto_detect, "netifaces", stub)

    assert auto_detect.list_local_subnets() == ["10.0.0.0/24"]


# =============================================================================
# auto_detect.list_routed_subnets / list_scannable_subnets / get_local_ips
# =============================================================================


def _write_proc_route(tmp_path: Any, rows: list[tuple[str, str, str, str]]) -> str:
    """Write a fake /proc/net/route file and return its path.

    Each row is (iface, dest_hex, mask_hex, flags_hex); destination and mask
    are little-endian hex as the kernel exposes them.
    """
    header = (
        "Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\t"
        "Window\tIRTT\n"
    )
    body = ""
    for iface, dest, mask, flags in rows:
        body += f"{iface}\t{dest}\t00000000\t{flags}\t0\t0\t0\t{mask}\t0\t0\t0\n"
    path = tmp_path / "route"
    path.write_text(header + body, encoding="ascii")
    return str(path)


def test_list_routed_subnets_includes_gateway_routes(tmp_path: Any) -> None:
    """A gateway-routed subnet (UG) like 10.3.141.0/24 is enumerated."""
    from custom_components.redsea import auto_detect

    # 10.3.141.0/24 little-endian dest = 0x008D030A, mask /24 = 0x00FFFFFF.
    # 192.168.0.0/24 dest = 0x0000A8C0. Default route dest=0 mask=0.
    rows = [
        ("bond0", "00000000", "00000000", "0003"),  # default (UG) → skipped
        ("bond0", "008D030A", "00FFFFFF", "0003"),  # 10.3.141.0/24 via gateway
        ("bond0", "0000A8C0", "00FFFFFF", "0001"),  # 192.168.0.0/24 direct
    ]
    path = _write_proc_route(tmp_path, rows)

    subnets = auto_detect.list_routed_subnets(path)
    assert "10.3.141.0/24" in subnets
    assert "192.168.0.0/24" in subnets
    # The default route must never be enumerated.
    assert "0.0.0.0/0" not in subnets


def test_list_routed_subnets_skips_oversized(tmp_path: Any) -> None:
    """docker/bridge /16 routes are dropped (too big to host-scan)."""
    from custom_components.redsea import auto_detect

    # 172.17.0.0/16 dest = 0x000011AC, mask /16 = 0x0000FFFF.
    rows = [
        ("docker0", "000011AC", "0000FFFF", "0001"),  # 172.17.0.0/16 → skipped
        ("bond0", "0000A8C0", "00FFFFFF", "0001"),  # 192.168.0.0/24 kept
    ]
    path = _write_proc_route(tmp_path, rows)

    assert auto_detect.list_routed_subnets(path) == ["192.168.0.0/24"]


def test_list_routed_subnets_cap_is_slash24(tmp_path: Any) -> None:
    """The auto-scan cap is /24: a /23 is dropped, a /24 is kept."""
    from custom_components.redsea import auto_detect

    # 192.168.0.0/23 mask = 255.255.254.0 → little-endian hex 00FEFFFF.
    # 192.168.2.0/24 dest = 0x0002A8C0, mask /24 = 00FFFFFF.
    rows = [
        ("bond0", "0000A8C0", "00FEFFFF", "0001"),  # 192.168.0.0/23 → skipped
        ("bond0", "0002A8C0", "00FFFFFF", "0001"),  # 192.168.2.0/24 → kept
    ]
    path = _write_proc_route(tmp_path, rows)

    assert auto_detect.list_routed_subnets(path) == ["192.168.2.0/24"]


def test_list_routed_subnets_missing_file_returns_empty() -> None:
    """A non-Linux host (no /proc/net/route) yields an empty list."""
    from custom_components.redsea import auto_detect

    assert auto_detect.list_routed_subnets("/nonexistent/route/file") == []


def test_list_scannable_subnets_merges_local_and_routed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The union keeps locals first and de-duplicates overlaps."""
    from custom_components.redsea import auto_detect

    monkeypatch.setattr(auto_detect, "list_local_subnets", lambda: ["192.168.0.0/24"])
    monkeypatch.setattr(
        auto_detect,
        "list_routed_subnets",
        lambda: ["192.168.0.0/24", "10.3.141.0/24"],
    )

    assert auto_detect.list_scannable_subnets() == [
        "192.168.0.0/24",
        "10.3.141.0/24",
    ]


def test_get_local_ips_scans_all_scannable_subnets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no explicit CIDR, IPs from every scannable subnet are returned."""
    from custom_components.redsea import auto_detect

    monkeypatch.setattr(
        auto_detect,
        "list_scannable_subnets",
        lambda: ["192.168.0.0/30", "10.3.141.0/30"],
    )

    ips = auto_detect.get_local_ips()
    # /30 usable hosts: .1 and .2 for each subnet.
    assert "192.168.0.1" in ips
    assert "192.168.0.2" in ips
    assert "10.3.141.1" in ips
    assert "10.3.141.2" in ips


def test_get_local_ips_explicit_cidr_bypasses_enumeration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit CIDR is expanded directly without touching the routing table."""
    from custom_components.redsea import auto_detect

    def _boom() -> list[str]:
        raise AssertionError("scannable enumeration must not run for explicit CIDR")

    monkeypatch.setattr(auto_detect, "list_scannable_subnets", _boom)

    ips = auto_detect.get_local_ips("10.3.141.0/30")
    # _iter_ipv4s yields every address in the network (incl. .0 and .3).
    assert set(ips) == {
        "10.3.141.0",
        "10.3.141.1",
        "10.3.141.2",
        "10.3.141.3",
    }
