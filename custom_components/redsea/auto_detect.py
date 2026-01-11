#!/usr/bin/env python3
"""Network auto-detection for Red Sea ReefBeat devices.

This module can be used:
- as part of the integration import tree (package import)
- as a standalone script (python auto_detect.py)

It scans the local subnet (or a provided CIDR) and probes `/device-info`
and `/description.xml` to identify ReefBeat devices and extract their UUID.
"""

from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Iterable
from multiprocessing import Pool
from typing import TypedDict

import netifaces
import requests
from lxml import objectify  # type: ignore
from lxml.objectify import ObjectifiedElement  # type: ignore

try:
    # Package import (Home Assistant integration)
    from .const import HW_DEVICES_IDS
except Exception:  # pragma: no cover
    # Script usage fallback
    from const import HW_DEVICES_IDS  # type: ignore


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------
class ReefBeatInfo(TypedDict, total=False):
    """Basic information returned by network detection."""

    ip: str
    hw_model: str
    friendly_name: str
    uuid: str


# -----------------------------------------------------------------------------
# Network helpers
# -----------------------------------------------------------------------------
def _iter_ipv4s(cidr: str) -> Iterable[str]:
    """Yield IPv4 addresses in a CIDR."""
    net = ipaddress.ip_network(cidr, strict=False)
    if not isinstance(net, ipaddress.IPv4Network):
        return []
    return (str(ip) for ip in net)


def get_local_ips(subnetwork: str | None = None) -> list[str]:
    """Return IPv4 addresses for the local network or the given subnetwork.

    Args:
        subnetwork: CIDR like "192.168.1.0/24". If None, attempt to infer the
            local interface subnet.

    Returns:
        List of IPv4 addresses as strings.
    """
    if subnetwork:
        return list(_iter_ipv4s(subnetwork))

    # Infer local IP by connecting a UDP socket; no packets are sent.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
    except OSError:
        return []

    # Find the interface that owns local_ip and derive its subnet.
    for netif in netifaces.interfaces():
        try:
            inet_addrs = netifaces.ifaddresses(netif).get(netifaces.AF_INET, [])
            if not inet_addrs:
                continue
            addr = inet_addrs[0]
            if addr.get("addr") != local_ip:
                continue
            netmask = addr.get("netmask")
            if not isinstance(netmask, str) or not netmask:
                continue
            cidr = f"{local_ip}/{netmask}"
            return list(_iter_ipv4s(cidr))
        except Exception:
            continue

    return []


# -----------------------------------------------------------------------------
# Device probing
# -----------------------------------------------------------------------------
def get_unique_id(ip: str) -> str | None:
    """Fetch the device UDN from description.xml and return the UUID, or None."""
    try:
        r = requests.get(f"http://{ip}/description.xml", timeout=2)
        r.raise_for_status()
        tree: ObjectifiedElement = objectify.fromstring(r.text)  # type: ignore
        udn = str(tree.device.UDN)  # type: ignore[attr-defined]
        return udn.replace("uuid:", "")
    except Exception:
        return None


def is_reefbeat(ip: str) -> tuple[bool, str, str | None, str | None, str | None]:
    """Probe one IP and detect if it is a ReefBeat device.

    Returns:
        (status, ip, hw_model, friendly_name, uuid)
    """
    try:
        r = requests.get(f"http://{ip}/device-info", timeout=2)
        if r.status_code != 200:
            return False, ip, None, None, None
        data = r.json()
        hw_model = data.get("hw_model")
        if hw_model not in HW_DEVICES_IDS:
            return False, ip, None, None, None
        name = data.get("name")
        uuid = get_unique_id(ip)
        return True, ip, hw_model, name, uuid
    except Exception:
        return False, ip, None, None, None


def get_reefbeats(
    subnetwork: str | None = None, nb_of_threads: int = 64
) -> list[ReefBeatInfo]:
    """Scan the network and return detected ReefBeat devices.

    Args:
        subnetwork: CIDR like "192.168.1.0/24", or None to infer the local subnet.
        nb_of_threads: Process pool size. If 1, will scan in-process.

    Returns:
        List of device dicts, each containing ip/hw_model/friendly_name/uuid.
    """
    ips = get_local_ips(subnetwork)

    results: list[tuple[bool, str, str | None, str | None, str | None]]
    if nb_of_threads <= 1:
        results = [is_reefbeat(ip) for ip in ips]
    else:
        with Pool(nb_of_threads) as pool:
            results = pool.map(is_reefbeat, ips)

    reefbeats: list[ReefBeatInfo] = []
    for status, ip, hw_model, friendly_name, uuid in results:
        if status:
            reefbeats.append(
                {
                    "ip": ip,
                    "hw_model": hw_model or "",
                    "friendly_name": friendly_name or "",
                    "uuid": uuid or "",
                }
            )
    return reefbeats


# -----------------------------------------------------------------------------
# Script entry point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print(json.dumps(get_reefbeats(), sort_keys=True, indent=4))
