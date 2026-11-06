#!/usr/bin/env python3
"""Poseidon rescue: switch ReefBeat devices back to the Red Sea broker.

For a serious problem, when Home Assistant cannot do it any more (down,
relay broken, integration removed): run it from any computer on the devices'
network, with Python 3.8+ and nothing else.

    python3 poseidon_rescue.py              # devices on the relay, after a confirmation
    python3 poseidon_rescue.py --dry-run    # only show what would be done
    python3 poseidon_rescue.py --keystore keystore.json   # a keystore export instead
    python3 poseidon_rescue.py --scan 192.168.1.0/24      # where moved devices are

The copy downloaded from Home Assistant (Poseidon > Configure > Rescue script)
embeds the devices, their keys and the relay address: keep it as safe as a
keystore export.

Each device gets the sequence of the official app: POST /cloud/disable, POST
/cloud {url, api_key, api_secret}, POST /cloud/enable (sent even after a
failed write, never to leave a device cut off), then /cloud is read again.

Nothing is written before the device answering at the address proves to be
the right one (its hwid in /device-info): addresses change, and keys written
into another device would cut that one off. A device not found at its address
is looked for on the network: the /24 of every known device address and of
this computer, or the --scan subnets.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# Filled in by Home Assistant at download time (None: use --keystore)
EMBEDDED = None

NORMAL_URL = "mqtt.reef-beat.com:1883"
TIMEOUT_S = 8.0
SETTLE_S = 2.0
# Network scan for the devices whose address changed
SCAN_TIMEOUT_S = 1.5
SCAN_WORKERS = 64
SCAN_MAX_HOSTS = 4096


def broker_of(url: Any) -> str:
    """A broker address, normalised ("" when unknown)."""
    text = str(url or "").strip().lower()
    return text.split("://", 1)[-1].rstrip("/")


def normal_url(record: dict[str, Any], relay: str) -> str:
    """Broker of the normal mode: the one the keys were issued for."""
    url = str(record.get("mqtt_url") or "").strip()
    if not url or (relay and broker_of(url) == broker_of(relay)):
        return NORMAL_URL
    return url


def load_devices(keystore: str | None) -> dict[str, Any]:
    """Devices and relay address: from a keystore file, or embedded."""
    if keystore:
        with open(keystore, encoding="utf-8") as file:
            data = json.load(file)
        devices = data.get("devices") if isinstance(data, dict) else None
        if not isinstance(devices, dict):
            raise ValueError(f"{keystore}: not a keystore")
        records = [{**rec, "hwid": hwid} for hwid, rec in devices.items()]
        return {"relay": "", "devices": records}
    if EMBEDDED is None:
        raise ValueError(
            "no device embedded in this copy: pass --keystore <keystore.json>"
        )
    return EMBEDDED


def request(
    ip: str,
    method: str,
    endpoint: str,
    payload: Any = None,
    timeout: float = TIMEOUT_S,
) -> Any:
    """One local HTTP call; the decoded answer (None if not JSON)."""
    data = None if method == "GET" else b""
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"http://{ip}{endpoint}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body) if body else None
    except ValueError:
        return None


def get_cloud(ip: str) -> dict[str, Any] | None:
    try:
        cloud = request(ip, "GET", "/cloud")
    except (OSError, urllib.error.URLError):
        return None
    return cloud if isinstance(cloud, dict) else None


def identify(ip: str, timeout: float = TIMEOUT_S) -> str:
    """Hardware id of the ReefBeat device answering at ip ("" if none)."""
    try:
        info = request(ip, "GET", "/device-info", timeout=timeout)
    except (OSError, urllib.error.URLError, ValueError):
        return ""
    if not isinstance(info, dict):
        return ""
    return str(info.get("hwid") or "").strip().lower()


def host_of(address: str) -> str:
    """The IPv4 part of an address (port dropped), "" if it is none."""
    host = address.strip().rsplit(":", 1)[0] if address.count(":") == 1 else address
    try:
        return str(ipaddress.IPv4Address(host.strip()))
    except ValueError:
        return ""


def local_ip() -> str:
    """This computer's address on its default route ("" if none).

    A UDP socket connected to a documentation address: nothing is sent.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 9))
            return str(sock.getsockname()[0])
    except OSError:
        return ""


def scan_subnets(cidrs: list[str], known: list[str]) -> list[str]:
    """Subnets to scan: the given ones, else the /24 of every known address
    and of this computer."""
    if cidrs:
        return [str(ipaddress.ip_network(c.strip(), strict=False)) for c in cidrs]
    subnets: list[str] = []
    for address in [*known, local_ip()]:
        host = host_of(address)
        if not host or ipaddress.IPv4Address(host).is_loopback:
            continue
        subnet = str(ipaddress.ip_network(f"{host}/24", strict=False))
        if subnet not in subnets:
            subnets.append(subnet)
    return subnets


def subnet_hosts(subnets: list[str]) -> list[str]:
    hosts: list[str] = []
    for subnet in subnets:
        hosts.extend(str(ip) for ip in ipaddress.ip_network(subnet).hosts())
    if len(hosts) > SCAN_MAX_HOSTS:
        raise ValueError(
            f"{len(hosts)} addresses to scan (at most {SCAN_MAX_HOSTS}): "
            "give smaller --scan subnets"
        )
    return hosts


def scan(hosts: list[str]) -> dict[str, str]:
    """hwid -> address of every ReefBeat device answering among hosts."""
    found: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        for host, hwid in pool.map(lambda h: (h, identify(h, SCAN_TIMEOUT_S)), hosts):
            if hwid:
                found.setdefault(hwid, host)
    return found


def post(ip: str, endpoint: str, payload: Any = None) -> bool:
    try:
        request(ip, "POST", endpoint, payload)
    except (OSError, urllib.error.URLError) as err:
        print(f"    POST {endpoint}: {err}")
        return False
    return True


def switch_back(ip: str, url: str, api_key: str, api_secret: str) -> bool:
    disabled = post(ip, "/cloud/disable")
    written = post(
        ip, "/cloud", {"url": url, "api_key": api_key, "api_secret": api_secret}
    )
    # Enabled again even after a failed write
    enabled = post(ip, "/cloud/enable")
    return disabled and written and enabled


def label(record: dict[str, Any]) -> str:
    name = str(record.get("name") or "")
    hwid = str(record.get("hwid") or "")
    return f"{name} ({hwid})" if name else hwid


def parse_ips(values: list[str]) -> dict[str, str]:
    ips: dict[str, str] = {}
    for value in values:
        hwid, sep, ip = value.partition("=")
        if not sep or not ip:
            raise ValueError(f"--ip {value}: expected HWID=IP")
        ips[hwid.strip().lower()] = ip.strip()
    return ips


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Switch ReefBeat devices back to the Red Sea broker."
    )
    parser.add_argument("--keystore", help="keystore.json (export or CLI)")
    parser.add_argument("--relay", help="relay address host:port")
    parser.add_argument(
        "--all",
        action="store_true",
        help="every device, whatever broker it points at now",
    )
    parser.add_argument(
        "--only", action="append", default=[], help="hwid or name (repeatable)"
    )
    parser.add_argument(
        "--ip", action="append", default=[], help="HWID=IP when a device moved"
    )
    parser.add_argument(
        "--scan",
        action="append",
        default=[],
        help="subnet to look for moved devices in, CIDR (repeatable)",
    )
    parser.add_argument(
        "--no-scan", action="store_true", help="never look for moved devices"
    )
    parser.add_argument("--dry-run", action="store_true", help="change nothing")
    parser.add_argument("--yes", "-y", action="store_true", help="no confirmation")
    args = parser.parse_args(argv)

    try:
        data = load_devices(args.keystore)
        ips = parse_ips(args.ip)
    except (OSError, ValueError) as err:
        print(f"Error: {err}")
        return 2
    relay = str(args.relay or data.get("relay") or "")
    only = {value.strip().lower() for value in args.only}
    records = [
        rec
        for rec in data.get("devices") or []
        if isinstance(rec, dict) and rec.get("api_key") and rec.get("api_secret")
    ]
    if only:
        records = [
            rec
            for rec in records
            if str(rec.get("hwid", "")).lower() in only
            or str(rec.get("name", "")).lower() in only
        ]
    if not records:
        print("No device with keys to handle.")
        return 1

    print(f"Relay: {relay or 'unknown'}")
    # Where each device is: given, else its known address if it answers there
    # with its own hwid
    located: dict[str, str] = {}
    missing: list[dict[str, Any]] = []
    for rec in records:
        hwid = str(rec.get("hwid", "")).lower()
        ip = ips.get(hwid) or str(rec.get("ip") or "")
        found = identify(ip) if ip else ""
        if found == hwid:
            located[hwid] = ip
            continue
        if ip and found:
            print(f"- {label(rec)}: {ip} is another device now ({found})")
        elif ip:
            print(f"- {label(rec)}: no answer at {ip}")
        else:
            print(f"- {label(rec)}: no known address")
        missing.append(rec)
    if missing and not args.no_scan:
        try:
            known = [str(r.get("ip") or "") for r in records] + list(ips.values())
            subnets = scan_subnets(args.scan, known)
            hosts = subnet_hosts(subnets)
        except ValueError as err:
            print(f"Error: {err}")
            return 2
        if subnets:
            print(f"Looking for {len(missing)} device(s) in {', '.join(subnets)}...")
        else:
            print("No subnet to look for them in: pass --scan <CIDR>")
        found_at = scan(hosts)
        for rec in missing:
            hwid = str(rec.get("hwid", "")).lower()
            if hwid in found_at:
                located[hwid] = found_at[hwid]
                print(f"- {label(rec)}: found at {found_at[hwid]}")

    todo: list[dict[str, Any]] = []
    unreachable: list[str] = []
    for rec in records:
        hwid = str(rec.get("hwid", "")).lower()
        target = normal_url(rec, relay)
        ip = located.get(hwid, "")
        cloud = get_cloud(ip) if ip else None
        if cloud is None:
            print(f"- {label(rec)}: not found")
            unreachable.append(label(rec))
            continue
        current = broker_of(cloud.get("url"))
        if relay:
            wanted = args.all or current == broker_of(relay)
        else:
            wanted = args.all or current != broker_of(target)
        state = "to switch back" if wanted else "left as is"
        print(f"- {label(rec)} [{ip}]: {current or '?'} -> {state}")
        if wanted:
            todo.append({**rec, "ip": ip, "target": target})

    if not todo:
        print("Nothing to switch back.")
        return 1 if unreachable else 0
    if args.dry_run:
        for rec in todo:
            print(f"Would switch {label(rec)} to {rec['target']}")
        return 0
    if not args.yes:
        answer = input(f"Switch {len(todo)} device(s) back to normal mode? [y/N] ")
        if answer.strip().lower() not in ("y", "yes", "o", "oui"):
            print("Cancelled.")
            return 1

    failed: list[str] = list(unreachable)
    for rec in todo:
        print(f"{label(rec)}: switching to {rec['target']}")
        done = switch_back(
            rec["ip"], rec["target"], str(rec["api_key"]), str(rec["api_secret"])
        )
        time.sleep(SETTLE_S)
        cloud = get_cloud(rec["ip"]) or {}
        now = broker_of(cloud.get("url"))
        ok = done and now == broker_of(rec["target"])
        print(f"    {'OK' if ok else 'FAILED'}: /cloud url = {now or '?'}")
        if not ok:
            failed.append(label(rec))
    if failed:
        print("Not switched back: " + ", ".join(failed))
        return 1
    print("Every device is back in normal mode.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
