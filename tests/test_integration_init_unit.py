from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea as redsea_init
from custom_components.redsea.const import (
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    HW_ATO_IDS,
    HW_CONTROL_IDS,
    HW_DOSE_IDS,
    HW_G1_LED_IDS,
    HW_G2_LED_IDS,
    HW_MAT_IDS,
    HW_POWER_IDS,
    HW_RUN_IDS,
    HW_WAVE_IDS,
    REFRESH_DEVICE_DELAY,
    VIRTUAL_LED,
)
from custom_components.redsea.coordinator import (
    ReefATOCoordinator,
    ReefControlCoordinator,
    ReefDoseCoordinator,
    ReefLedCoordinator,
    ReefLedG2Coordinator,
    ReefMatCoordinator,
    ReefPowerCoordinator,
    ReefRunCoordinator,
    ReefVirtualLedCoordinator,
    ReefWaveCoordinator,
)


def _entry(*, ip: str, hw: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test",
        data={
            CONFIG_FLOW_IP_ADDRESS: ip,
            CONFIG_FLOW_HW_MODEL: hw,
        },
    )


@pytest.mark.asyncio
async def test_build_coordinator_maps_hw_models(hass: HomeAssistant) -> None:
    # Virtual LED uses IP prefix
    entry = _entry(ip=f"{VIRTUAL_LED}:1", hw=HW_G1_LED_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefVirtualLedCoordinator)

    entry = _entry(ip="192.0.2.1", hw=HW_G1_LED_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefLedCoordinator)

    entry = _entry(ip="192.0.2.2", hw=HW_G2_LED_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefLedG2Coordinator)

    entry = _entry(ip="192.0.2.3", hw=HW_DOSE_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefDoseCoordinator)

    entry = _entry(ip="192.0.2.4", hw=HW_MAT_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefMatCoordinator)

    entry = _entry(ip="192.0.2.5", hw=HW_ATO_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefATOCoordinator)

    entry = _entry(ip="192.0.2.6", hw=HW_RUN_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefRunCoordinator)

    entry = _entry(ip="192.0.2.7", hw=HW_WAVE_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefWaveCoordinator)

    entry = _entry(ip="192.0.2.8", hw=HW_POWER_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefPowerCoordinator)
    # First entry is RSPOWER6 -> 6 sockets
    assert c.socket_count == 6

    entry = _entry(ip="192.0.2.9", hw="RSPOWER8")
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefPowerCoordinator)
    assert c.socket_count == 8

    entry = _entry(ip="192.0.2.10", hw=HW_CONTROL_IDS[0])
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefControlCoordinator)
    # First entry is RSCONTROLPRO -> 2 ports
    assert c.port_count == 2

    entry = _entry(ip="192.0.2.11", hw="RSCONTROLLITE")
    c = redsea_init._build_coordinator(hass, cast(Any, entry))
    assert isinstance(c, ReefControlCoordinator)
    assert c.port_count == 1


@pytest.mark.asyncio
async def test_build_coordinator_unsupported_raises(hass: HomeAssistant) -> None:
    entry = _entry(ip="192.0.2.99", hw="UNKNOWN")
    with pytest.raises(ValueError):
        redsea_init._build_coordinator(hass, cast(Any, entry))


@dataclass
class _FakeAPI:
    get_called: list[str]
    send_called: list[tuple[str, Any, str]]

    async def http_get(self, access_path: str) -> dict[str, Any]:
        self.get_called.append(access_path)
        return {
            "ok": True,
            "status": 200,
            "reason": "OK",
            "method": "get",
            "url": f"http://dev{access_path}",
            "elapsed_ms": 1,
            "headers": {"x": "y"},
            "json": {"a": 1},
        }

    async def http_send(
        self, access_path: str, payload: Any, method: str
    ) -> dict[str, Any]:
        self.send_called.append((access_path, payload, method))
        return {
            "ok": True,
            "status": 201,
            "reason": "Created",
            "method": method,
            "url": f"http://dev{access_path}",
            "elapsed_ms": 2,
            "headers": {"x": "y"},
            "text": "ok",
        }


@dataclass
class _FakeDevice:
    my_api: _FakeAPI
    title: str = "DeviceTitle"

    refreshed: list[str | None] = field(default_factory=list)
    # How each refresh was asked for, so the service's opt-in re-read can be
    # checked rather than just its occurrence.
    refresh_calls: list[tuple[bool, int]] = field(default_factory=list)

    async def async_request_refresh(
        self, source: str | None = None, config: bool = False, wait: int = 2
    ) -> None:
        self.refreshed.append(source)
        self.refresh_calls.append((config, wait))


@pytest.mark.asyncio
async def test_request_service_error_branches(hass: HomeAssistant) -> None:
    assert await redsea_init.async_setup(hass, {})

    # Invalid device_id
    resp = await hass.services.async_call(
        DOMAIN,
        "request",
        {"device_id": 123, "access_path": "/x", "method": "get"},
        blocking=True,
        return_response=True,
    )
    assert resp == {"error": "Invalid device_id"}

    # Device not enabled
    resp = await hass.services.async_call(
        DOMAIN,
        "request",
        {"device_id": "missing", "access_path": "/x", "method": "get"},
        blocking=True,
        return_response=True,
    )
    assert resp == {"error": "Device not enabled"}

    # Add a fake device
    get_called: list[str] = []
    send_called: list[tuple[str, Any, str]] = []
    fake = _FakeDevice(my_api=_FakeAPI(get_called=get_called, send_called=send_called))
    hass.data.setdefault(DOMAIN, {})["dev1"] = fake

    # Invalid access_path or method
    resp = await hass.services.async_call(
        DOMAIN,
        "request",
        {"device_id": "dev1", "access_path": 1, "method": "get"},
        blocking=True,
        return_response=True,
    )
    assert resp == {"error": "Invalid access_path or method"}


@pytest.mark.asyncio
async def test_request_service_get_and_send(hass: HomeAssistant) -> None:
    assert await redsea_init.async_setup(hass, {})

    get_called: list[str] = []
    send_called: list[tuple[str, Any, str]] = []
    fake = _FakeDevice(my_api=_FakeAPI(get_called=get_called, send_called=send_called))
    hass.data.setdefault(DOMAIN, {})["dev1"] = fake

    resp = await hass.services.async_call(
        DOMAIN,
        "request",
        {"device_id": "dev1", "access_path": "/device-info", "method": "get"},
        blocking=True,
        return_response=True,
    )

    assert isinstance(resp, dict)

    assert get_called == ["/device-info"]
    assert resp["ok"] is True
    assert resp["status"] == 200
    assert resp["json"] == {"a": 1}

    resp2 = await hass.services.async_call(
        DOMAIN,
        "request",
        {
            "device_id": "dev1",
            "access_path": "/x",
            "method": "post",
            "data": {"v": 1},
        },
        blocking=True,
        return_response=True,
    )

    assert isinstance(resp2, dict)

    assert send_called == [("/x", {"v": 1}, "post")]
    assert resp2["ok"] is True
    assert resp2["status"] == 201
    assert "text" in resp2


# ---------------------------------------------------------------------------
# request service: choosing how the coordinator is re-read
# ---------------------------------------------------------------------------
#
# The handler has always re-read the device before returning, so a caller
# never sees the data it just replaced. `refresh` and `wait` only steer that
# existing read: which sources it covers, and how long to let the device
# settle first — several endpoints acknowledge a write before they serve the
# new value back, a socket schedule among them.


async def _call_request(hass: HomeAssistant, **data: Any) -> _FakeDevice:
    """Register a fake device, call the service against it, return the fake."""
    assert await redsea_init.async_setup(hass, {})
    fake = _FakeDevice(my_api=_FakeAPI(get_called=[], send_called=[]))
    hass.data.setdefault(DOMAIN, {})["dev1"] = fake

    payload: dict[str, Any] = {"device_id": "dev1", "access_path": "/x"}
    payload.update(data)
    await hass.services.async_call(
        DOMAIN, "request", payload, blocking=True, return_response=True
    )
    return fake


@pytest.mark.asyncio
async def test_request_refreshes_config_by_default(hass: HomeAssistant) -> None:
    """Asking for nothing keeps the behaviour callers have always had."""
    fake = await _call_request(hass, method="put")

    assert fake.refresh_calls == [(True, REFRESH_DEVICE_DELAY)]


@pytest.mark.asyncio
async def test_request_refresh_honours_an_explicit_wait(
    hass: HomeAssistant,
) -> None:
    """A caller that knows its endpoint is slow can lengthen the wait."""
    fake = await _call_request(hass, method="put", refresh="config", wait=3)

    assert fake.refresh_calls == [(True, 3)]


@pytest.mark.asyncio
async def test_request_refresh_data_skips_config_sources(
    hass: HomeAssistant,
) -> None:
    """Asking for a data read leaves the config sources alone."""
    fake = await _call_request(hass, method="put", refresh="data")

    assert fake.refresh_calls == [(False, REFRESH_DEVICE_DELAY)]


@pytest.mark.asyncio
async def test_request_refresh_unknown_kind_reads_data(hass: HomeAssistant) -> None:
    """Only "config" selects the config sources; anything else is a data read."""
    fake = await _call_request(hass, method="put", refresh="whatever")

    assert fake.refresh_calls == [(False, REFRESH_DEVICE_DELAY)]


@pytest.mark.asyncio
async def test_request_refresh_unusable_wait_falls_back(
    hass: HomeAssistant,
) -> None:
    """A wait that is not a number must not take the whole call down."""
    fake = await _call_request(hass, method="put", refresh="config", wait="soon")

    assert fake.refresh_calls == [(True, REFRESH_DEVICE_DELAY)]


@pytest.mark.asyncio
async def test_request_refresh_negative_wait_is_clamped(
    hass: HomeAssistant,
) -> None:
    """A negative wait means no wait, not a delay running backwards."""
    fake = await _call_request(hass, method="put", refresh="config", wait=-5)

    assert fake.refresh_calls == [(True, 0)]


@pytest.mark.asyncio
async def test_request_get_also_refreshes(hass: HomeAssistant) -> None:
    """Reads re-read too, as they always have."""
    fake = await _call_request(hass, method="get", refresh="config")

    assert fake.refresh_calls == [(True, REFRESH_DEVICE_DELAY)]
