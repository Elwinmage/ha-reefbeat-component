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
import struct
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict

import requests

try:
    import netifaces  # type: ignore
except Exception:  # pragma: no cover
    netifaces = None  # type: ignore

try:
    # Package import (Home Assistant integration)
    from .const import HW_DEVICES_IDS
except Exception:  # pragma: no cover
    # Script usage fallback
    from const import HW_DEVICES_IDS  # type: ignore


# =============================================================================
# Types
# =============================================================================


class ReefBeatInfo(TypedDict, total=False):
    """Basic information returned by network detection."""

    ip: str
    hw_model: str
    friendly_name: str
    uuid: str


# Network helpers
_DEFAULT_PREFIXLEN = 24


def _iter_ipv4s(cidr: str) -> Iterable[str]:
    """Yield IPv4 addresses in a CIDR."""
    net = ipaddress.ip_network(cidr, strict=False)
    if not isinstance(net, ipaddress.IPv4Network):
        return []
    return (str(ip) for ip in net)


def get_local_ips(subnetwork: str | None = None) -> list[str]:
    """Return IPv4 addresses to probe for the given subnetwork, or all reachable.

    When ``subnetwork`` is provided, only that CIDR is expanded. When it is
    None, every reachable subnet is enumerated — both directly-attached
    interfaces and gateway-routed networks (from the kernel routing table) —
    so devices sitting behind a router (e.g. on ``10.3.141.0/24``) are found
    too, not just those on the primary interface's subnet.
    """
    if subnetwork:
        return list(_iter_ipv4s(subnetwork))

    # No explicit CIDR: walk every subnet we can reach. list_scannable_subnets
    # merges interface subnets (netifaces) with routed ones (/proc/net/route).
    scannable = list_scannable_subnets()
    if scannable:
        ips: list[str] = []
        seen: set[str] = set()
        for cidr in scannable:
            for ip in _iter_ipv4s(cidr):
                if ip not in seen:
                    seen.add(ip)
                    ips.append(ip)
        return ips

    # Fallback (no netifaces and no readable routing table): derive a single
    # /24 from the primary interface, as before.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
    except OSError as exc:
        # Log so HA logs show why detection returned nothing
        import logging

        logging.getLogger(__name__).warning(
            "auto_detect: cannot determine local IP (%s); "
            "pass an explicit subnetwork CIDR to bypass this.",
            exc,
        )
        return []

    return list(_iter_ipv4s(f"{local_ip}/{_DEFAULT_PREFIXLEN}"))


# =============================================================================
# Multi-subnet enumeration
# =============================================================================


# Only auto-scan networks of /24 or smaller (prefixlen >= 24). A /24 is the
# standard home LAN (255.255.255.0, 256 addresses, ~8 s to probe at 64
# threads). Anything larger — a /23, /22, docker's /16, or a 10.0.0.0/8 —
# is skipped so we never try to host-scan tens of thousands of addresses.
# Users on a genuinely larger LAN can still trigger a scan with an explicit
# CIDR from the options flow.
_MAX_AUTO_PREFIXLEN: int = 24  # /24 = 256 hosts, standard consumer subnet


def list_local_subnets() -> list[str]:
    """Return CIDRs for every routable IPv4 network the host is attached to.

    This is HA's answer to "which subnets can I reach directly?": each
    interface with an IPv4 address contributes one CIDR, and the caller can
    then scan them one after the other looking for a device that has just
    reconnected on a different LAN.

    The list excludes:
        - Loopback (127.0.0.0/8)
        - Link-local (169.254.0.0/16)
        - Point-to-point interfaces (netmask 255.255.255.255) — the /32 has
          no host range to probe.
        - Networks larger than :data:`_MAX_AUTO_PREFIXLEN` (default /24) —
          these would blow up the scan budget; users can still target them
          manually via the options flow.

    Duplicate CIDRs (two interfaces on the same subnet) are collapsed.
    Returns an empty list when :mod:`netifaces` is unavailable.
    """
    if netifaces is None:
        return []

    import logging

    logger = logging.getLogger(__name__)

    seen: set[str] = set()
    subnets: list[str] = []
    try:
        interfaces = list(netifaces.interfaces())
    except Exception:  # pragma: no cover — some platforms/netifaces builds
        return []
    for netif in interfaces:
        try:
            inet_addrs = netifaces.ifaddresses(netif).get(netifaces.AF_INET, [])
        except Exception:  # pragma: no cover — netifaces edge case
            continue
        for addr in inet_addrs:
            ip = addr.get("addr")
            netmask = addr.get("netmask")
            if not (isinstance(ip, str) and isinstance(netmask, str)):
                continue

            try:
                ip_obj = ipaddress.IPv4Address(ip)
            except (ipaddress.AddressValueError, ValueError):
                continue

            if ip_obj.is_loopback or ip_obj.is_link_local:
                continue

            try:
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
            except (ipaddress.AddressValueError, ValueError, TypeError):
                continue

            # Skip point-to-point (/32) and unreasonably large networks.
            if network.prefixlen == 32 or network.prefixlen < _MAX_AUTO_PREFIXLEN:
                logger.debug(
                    "list_local_subnets: skipping %s on %s "
                    "(prefixlen %d outside [%d, 31])",
                    network,
                    netif,
                    network.prefixlen,
                    _MAX_AUTO_PREFIXLEN,
                )
                continue

            cidr = str(network)
            if cidr not in seen:
                seen.add(cidr)
                subnets.append(cidr)

    return subnets


def is_valid_cidr(text: str) -> bool:
    """Return True if ``text`` parses as an IPv4 CIDR (strict=False).

    A bare address like ``"192.168.1.42"`` also parses (as a /32), but the
    caller should reject it separately if a full network was expected.
    """
    try:
        net = ipaddress.ip_network(text.strip(), strict=False)
    except (ValueError, TypeError):
        return False
    return isinstance(net, ipaddress.IPv4Network)


def list_routed_subnets(proc_route_path: str = "/proc/net/route") -> list[str]:
    """Return CIDRs for every IPv4 subnet reachable per the kernel routing table.

    Unlike :func:`list_local_subnets` (which only sees subnets *directly*
    attached to an interface via ``netifaces``), this reads the Linux routing
    table and therefore also returns subnets reached **through a gateway**
    (RTF_GATEWAY / the ``UG`` flag) — e.g. a ``10.3.141.0/24`` that lives
    behind a router. That is exactly the case where a device is pingable and
    the API works, yet interface-based detection never scans its subnet.

    The same size filters as the interface scan apply:
        - the default route (``0.0.0.0/0``) is skipped,
        - point-to-point ``/32`` routes are skipped,
        - networks larger than :data:`_MAX_AUTO_PREFIXLEN` (default /24) are
          skipped (this drops docker/bridge ``/16`` routes that would blow up
          the scan budget).

    Returns an empty list on non-Linux hosts or if the table can't be read.
    ``/proc/net/route`` stores the destination and mask as little-endian hex.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        with open(proc_route_path, encoding="ascii") as handle:
            lines = handle.readlines()
    except OSError:
        # Non-Linux, container without /proc, or permission issue.
        return []

    seen: set[str] = set()
    subnets: list[str] = []
    for line in lines[1:]:  # first line is the header
        fields = line.split()
        if len(fields) < 8:
            continue
        dest_hex, mask_hex = fields[1], fields[7]
        try:
            dest_int = int(dest_hex, 16)
            mask_int = int(mask_hex, 16)
        except ValueError:
            continue

        if mask_int == 0:
            # Default route (0.0.0.0/0) — never enumerate the whole internet.
            continue

        try:
            ip = socket.inet_ntoa(struct.pack("<L", dest_int))
            mask = socket.inet_ntoa(struct.pack("<L", mask_int))
            network = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
        except (OSError, struct.error, ipaddress.AddressValueError, ValueError):
            continue

        if network.prefixlen == 32 or network.prefixlen < _MAX_AUTO_PREFIXLEN:
            logger.debug(
                "list_routed_subnets: skipping %s (prefixlen %d outside [%d, 31])",
                network,
                network.prefixlen,
                _MAX_AUTO_PREFIXLEN,
            )
            continue

        cidr = str(network)
        if cidr not in seen:
            seen.add(cidr)
            subnets.append(cidr)

    return subnets


def list_scannable_subnets() -> list[str]:
    """Return every IPv4 subnet worth scanning for devices.

    Union of the directly-attached subnets (:func:`list_local_subnets`) and
    the gateway-routed ones (:func:`list_routed_subnets`), de-duplicated while
    preserving order (locals first). This is the comprehensive list a full
    discovery pass should walk so that devices behind a router are found too.
    """
    seen: set[str] = set()
    result: list[str] = []
    try:
        local = list_local_subnets()
    except Exception:  # pragma: no cover — defensive
        local = []
    try:
        routed = list_routed_subnets()
    except Exception:  # pragma: no cover — defensive
        routed = []
    for cidr in (*local, *routed):
        if cidr not in seen:
            seen.add(cidr)
            result.append(cidr)
    return result


# Device probing
def get_unique_id(ip: str) -> str | None:
    """Fetch the device UDN from description.xml and return the UUID, or None."""
    try:
        r = requests.get(f"http://{ip}/description.xml", timeout=2)
        r.raise_for_status()
        root = ET.fromstring(r.text)

        udn_text: str | None = None
        for el in root.iter():
            # Handle namespaces by looking at the localname.
            if isinstance(el.tag, str) and el.tag.split("}")[-1] == "UDN":
                if el.text:
                    udn_text = el.text.strip()
                break

        if not udn_text:
            return None
        return udn_text.replace("uuid:", "")
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


# APRÈS — utiliser ThreadPoolExecutor au lieu de multiprocessing.Pool


def get_reefbeats(
    subnetwork: str | None = None, nb_of_threads: int = 64
) -> list[ReefBeatInfo]:
    """Scan the network and return detected ReefBeat devices.

    Uses ThreadPoolExecutor instead of multiprocessing.Pool to avoid
    fork() issues when called from within a Home Assistant executor thread
    (forking from an asyncio process corrupts open sockets/event loops).
    """
    ips = get_local_ips(subnetwork)

    if nb_of_threads <= 1:
        results = [is_reefbeat(ip) for ip in ips]
    else:
        with ThreadPoolExecutor(max_workers=nb_of_threads) as executor:
            results = list(executor.map(is_reefbeat, ips))

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


# Script entry point
if __name__ == "__main__":
    print(json.dumps(get_reefbeats(), sort_keys=True, indent=4))
