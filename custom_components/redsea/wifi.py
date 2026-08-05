"""Wi-Fi provisioning helpers for ReefBeat devices.

This module encapsulates the low-level HTTP calls used by the options flow
Wi-Fi step:

- :func:`scan_wifi` — GET  ``/wifi/scan``  (list available networks)
- :func:`connect_wifi` — POST ``/wifi/connect`` (submit SSID+password)
- :func:`reset_device` — POST ``/reset`` (reboot to apply new credentials)
- :func:`rediscover_device` — after reboot, scan the LAN and locate the
  device on its new IP address, primarily by UUID (stable across reboots)
  and, as a fallback, by ``(hw_model, friendly_name)``.

Design notes:
    - We deliberately avoid the ``ReefBeatAPI._http_send`` retry loop for
      the ``/reset`` call because the device restarts mid-response, so
      retrying would just waste ~10 seconds. A single short call, best-effort.
    - Rediscovery re-uses :func:`.auto_detect.get_reefbeats` so we have a
      single implementation of subnet scanning across the integration.
"""

from __future__ import annotations

import asyncio
import logging
from asyncio import timeout
from typing import Any

import aiohttp

from .auto_detect import ReefBeatInfo, get_reefbeats
from .const import (
    WIFI_CONNECT_TIMEOUT,
    WIFI_RESET_TIMEOUT,
    WIFI_SCAN_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# HTTP helpers
# =============================================================================


async def scan_wifi(session: aiohttp.ClientSession, ip: str) -> list[dict[str, Any]]:
    """Return the list of Wi-Fi networks visible from the device.

    Args:
        session: Shared aiohttp session (typically ``async_get_clientsession``).
        ip: Current IP address of the device.

    Returns:
        The ``networks`` list from the device response, sorted by signal
        strength (strongest first) and de-duplicated by SSID. Empty list if
        the device responded but reported no networks.

    Raises:
        Exception: On network error, non-2xx status, or malformed response.
            Callers should catch broadly and surface a friendly message.
    """
    url = f"http://{ip}/wifi/scan"
    _LOGGER.debug("wifi.scan_wifi GET %s", url)

    async with timeout(WIFI_SCAN_TIMEOUT):
        async with session.get(url, ssl=False) as resp:
            resp.raise_for_status()
            payload = await resp.json(content_type=None)

    if not isinstance(payload, dict):
        raise TypeError(f"unexpected /wifi/scan payload type: {type(payload)!r}")

    raw = payload.get("networks") or []
    if not isinstance(raw, list):
        raise TypeError(f"unexpected /wifi/scan networks type: {type(raw)!r}")

    # De-duplicate by SSID keeping the best signal (some SSIDs are broadcast
    # by multiple BSSIDs; the /wifi/connect endpoint only cares about SSID).
    by_ssid: dict[str, dict[str, Any]] = {}
    for net in raw:
        if not isinstance(net, dict):
            continue
        ssid = net.get("ssid")
        if not isinstance(ssid, str) or not ssid:
            # Skip hidden or malformed networks: we can't connect to them
            # via the SSID+password form anyway.
            continue
        signal = net.get("signal_dBm")
        current = by_ssid.get(ssid)
        if current is None or (
            isinstance(signal, (int, float))
            and isinstance(current.get("signal_dBm"), (int, float))
            and signal > current["signal_dBm"]
        ):
            by_ssid[ssid] = net

    def _signal_sort_key(n: dict[str, Any]) -> float:
        # Networks without a numeric signal sort last. Narrowing the value
        # into a local keeps the return type a plain float for the type
        # checker (a double dict.get() would defeat the isinstance narrowing).
        value = n.get("signal_dBm")
        if isinstance(value, (int, float)):
            return float(value)
        return -999.0

    networks = sorted(by_ssid.values(), key=_signal_sort_key, reverse=True)
    _LOGGER.debug("wifi.scan_wifi: %d unique SSIDs found on %s", len(networks), ip)
    return networks


async def get_current_ssid(session: aiohttp.ClientSession, ip: str) -> str | None:
    """Return the SSID the device is currently connected to, or None.

    Reads the device ``/wifi`` endpoint (distinct from ``/wifi/scan``): it
    describes the *active* connection and exposes ``ssid`` alongside an
    ``is_connected`` flag. We use this to pre-select the current network in
    the options form so the user only has to (re)enter the password when
    they just want to fix credentials, and can still switch to another SSID
    from the drop-down if they mean to move the device.

    Never raises: any error (endpoint missing on older firmware, timeout,
    malformed payload) simply yields None so the form falls back to "no
    default", keeping Wi-Fi provisioning usable regardless.
    """
    url = f"http://{ip}/wifi"
    try:
        async with timeout(WIFI_SCAN_TIMEOUT):
            async with session.get(url, ssl=False) as resp:
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
    except Exception as err:
        _LOGGER.debug("wifi.get_current_ssid: %s unavailable (%s)", url, err)
        return None

    if not isinstance(payload, dict):
        return None

    # Some firmwares expose both is_connected and isConnected; treat a
    # missing flag as "trust the ssid field" rather than discarding it.
    connected = payload.get("is_connected")
    if connected is None:
        connected = payload.get("isConnected")

    ssid = payload.get("ssid")
    if not isinstance(ssid, str) or not ssid:
        return None
    if connected is False:
        # Explicitly not connected — the ssid may be a stale last-known
        # value, so don't present it as the active network.
        return None

    _LOGGER.debug("wifi.get_current_ssid: %s currently on ssid=%r", ip, ssid)
    return ssid


async def connect_wifi(
    session: aiohttp.ClientSession, ip: str, ssid: str, password: str
) -> bool:
    """POST new Wi-Fi credentials to the device.

    Returns True on 2xx response, False otherwise. Does not raise on network
    errors — the caller decides how to react.
    """
    url = f"http://{ip}/wifi/connect"
    payload = {"ssid": ssid, "password": password}
    # Never log the password.
    _LOGGER.debug("wifi.connect_wifi POST %s ssid=%r", url, ssid)

    try:
        async with timeout(WIFI_CONNECT_TIMEOUT):
            async with session.post(url, json=payload, ssl=False) as resp:
                text = await resp.text()
                ok = 200 <= resp.status < 300
                if not ok:
                    _LOGGER.error(
                        "wifi.connect_wifi: %s returned %s: %s",
                        url,
                        resp.status,
                        text,
                    )
                return ok
    except Exception as err:
        _LOGGER.error("wifi.connect_wifi failed for %s: %s", url, err)
        return False


async def reset_device(session: aiohttp.ClientSession, ip: str) -> bool:
    """POST /reset to reboot the device.

    Best-effort: the device restarts as soon as it accepts the call, so
    the request may or may not return cleanly. Any 2xx counts as success;
    a connection error is silently swallowed and reported as success, since
    the device rebooting mid-response is the expected behaviour.
    """
    url = f"http://{ip}/reset"
    _LOGGER.debug("wifi.reset_device POST %s", url)

    try:
        async with timeout(WIFI_RESET_TIMEOUT):
            async with session.post(url, ssl=False) as resp:
                # Any status is fine as long as the device received the request.
                _LOGGER.debug("wifi.reset_device: %s -> %s", url, resp.status)
                return True
    except (asyncio.TimeoutError, aiohttp.ClientError) as err:
        # A dropped connection here almost certainly means the device is
        # rebooting — that's exactly what we asked for.
        _LOGGER.debug("wifi.reset_device: %s disconnected as expected: %s", url, err)
        return True
    except Exception as err:
        _LOGGER.error("wifi.reset_device failed for %s: %s", url, err)
        return False


# =============================================================================
# Rediscovery
# =============================================================================


def _match_device(
    devices: list[ReefBeatInfo],
    uuid: str | None,
    hw_model: str | None,
    friendly_name: str | None,
) -> ReefBeatInfo | None:
    """Return the first device matching the given identifiers.

    Match order:
        1. UUID (stable across reboots, primary key)
        2. hw_model + friendly_name (fallback when UUID is missing)

    We never fall back to hw_model alone because two devices of the same
    model would collide — updating the wrong entry would be worse than
    failing to find one.
    """
    if uuid:
        for dev in devices:
            if dev.get("uuid") == uuid:
                return dev

    if hw_model and friendly_name:
        for dev in devices:
            if (
                dev.get("hw_model") == hw_model
                and dev.get("friendly_name") == friendly_name
            ):
                return dev

    return None


async def rediscover_device(
    hass: Any,
    uuid: str | None,
    hw_model: str | None,
    friendly_name: str | None,
    max_attempts: int,
    interval: int,
    subnetworks: list[str | None] | None = None,
) -> str | None:
    """Scan the LAN repeatedly until the device is located, then return its IP.

    Args:
        hass: Home Assistant instance (used to schedule the blocking scan in
            the executor).
        uuid: Preferred identifier — the device UUID exposed in
            ``description.xml``, stable across reboots.
        hw_model: Hardware model, used as fallback.
        friendly_name: Device friendly name, used as fallback.
        max_attempts: How many scans to attempt before giving up.
        interval: Sleep in seconds between two consecutive attempts.
        subnetworks: Ordered list of CIDRs to scan on each attempt. A
            ``None`` entry means "let :func:`get_reefbeats` pick the local
            subnet". When omitted, defaults to ``[None]`` (single-subnet
            scan — legacy behaviour). Useful for multi-homed Home Assistant
            hosts or when the device may have joined a different LAN after
            reboot.

    Returns:
        The new IP address as a string, or None if the device could not be
        found after all attempts.
    """
    subnets_to_scan: list[str | None] = (
        list(subnetworks) if subnetworks is not None else [None]
    )
    _LOGGER.debug(
        "wifi.rediscover_device: uuid=%s hw_model=%s friendly_name=%s "
        "attempts=%d subnets=%s",
        uuid,
        hw_model,
        friendly_name,
        max_attempts,
        subnets_to_scan,
    )

    for attempt in range(1, max_attempts + 1):
        for subnet in subnets_to_scan:
            try:
                devices: list[ReefBeatInfo] = await hass.async_add_executor_job(
                    get_reefbeats, subnet
                )
            except Exception as err:
                _LOGGER.warning(
                    "wifi.rediscover_device: attempt %d/%d subnet=%s failed: %s",
                    attempt,
                    max_attempts,
                    subnet,
                    err,
                )
                devices = []

            match = _match_device(devices, uuid, hw_model, friendly_name)
            if match is not None:
                new_ip = str(match.get("ip") or "")
                if new_ip:
                    _LOGGER.info(
                        "wifi.rediscover_device: found on attempt %d/%d "
                        "subnet=%s at %s",
                        attempt,
                        max_attempts,
                        subnet,
                        new_ip,
                    )
                    return new_ip

        if attempt < max_attempts:
            _LOGGER.debug(
                "wifi.rediscover_device: not found on attempt %d/%d, sleeping %ds",
                attempt,
                max_attempts,
                interval,
            )
            await asyncio.sleep(interval)

    _LOGGER.warning(
        "wifi.rediscover_device: device not found after %d attempts", max_attempts
    )
    return None
