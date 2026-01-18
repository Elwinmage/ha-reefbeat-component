from __future__ import annotations

from typing import Any

import pytest


class _Resp:
    def __init__(
        self, *, status_code: int = 200, json_data: Any = None, text: str = ""
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self) -> Any:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


def test_iter_ipv4s_and_get_local_ips_subnet() -> None:
    from custom_components.redsea import auto_detect

    assert list(auto_detect._iter_ipv4s("192.0.2.0/30")) == [
        "192.0.2.0",
        "192.0.2.1",
        "192.0.2.2",
        "192.0.2.3",
    ]
    assert auto_detect.get_local_ips("192.0.2.0/30") == [
        "192.0.2.0",
        "192.0.2.1",
        "192.0.2.2",
        "192.0.2.3",
    ]


def test_get_reefbeats_inprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.redsea import auto_detect

    monkeypatch.setattr(
        auto_detect, "get_local_ips", lambda _s=None: ["1.1.1.1", "2.2.2.2"]
    )

    def _is(ip: str) -> tuple[bool, str, str | None, str | None, str | None]:
        if ip == "1.1.1.1":
            return True, ip, "HW", "Name", "uuid"
        return False, ip, None, None, None

    monkeypatch.setattr(auto_detect, "is_reefbeat", _is)

    devices = auto_detect.get_reefbeats(subnetwork="192.0.2.0/30", nb_of_threads=1)
    assert len(devices) == 1
    dev0 = devices[0]
    dev0_dict = dev0 if isinstance(dev0, dict) else {}
    assert dev0_dict.get("ip") == "1.1.1.1"
    assert dev0_dict.get("uuid") == "uuid"


def test_get_unique_id_parses_udn(monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.redsea import auto_detect

    xml = """<?xml version='1.0'?>
    <root>
      <device>
        <UDN>uuid:abc-123</UDN>
      </device>
    </root>
    """

    def _get(url: str, timeout: int) -> _Resp:
        assert url.endswith("/description.xml")
        return _Resp(status_code=200, text=xml)

    monkeypatch.setattr(auto_detect.requests, "get", _get)

    assert auto_detect.get_unique_id("192.0.2.10") == "abc-123"


def test_is_reefbeat_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.redsea import auto_detect

    # Choose a real supported hw_model from integration constants.
    hw_ids = list(auto_detect.HW_DEVICES_IDS)
    if not hw_ids:
        pytest.skip("HW_DEVICES_IDS is empty")
    hw_model = hw_ids[0]

    def _get(url: str, timeout: int) -> _Resp:
        if url.endswith("/device-info"):
            return _Resp(status_code=200, json_data={"hw_model": hw_model, "name": "x"})
        raise AssertionError(url)

    monkeypatch.setattr(auto_detect.requests, "get", _get)
    monkeypatch.setattr(auto_detect, "get_unique_id", lambda ip: "uuid")

    status, ip, hw, name, uuid = auto_detect.is_reefbeat("192.0.2.11")
    assert status is True
    assert ip == "192.0.2.11"
    assert hw == hw_model
    assert name == "x"
    assert uuid == "uuid"


def test_is_reefbeat_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.redsea import auto_detect

    monkeypatch.setattr(
        auto_detect.requests,
        "get",
        lambda url, timeout: _Resp(status_code=404, json_data=None),
    )

    status, *_rest = auto_detect.is_reefbeat("192.0.2.12")
    assert status is False


def test_iter_ipv4s_non_ipv4_network_returns_empty() -> None:
    from custom_components.redsea import auto_detect

    assert list(auto_detect._iter_ipv4s("2001:db8::/126")) == []


def test_get_unique_id_exception_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.redsea import auto_detect

    def _get(url: str, timeout: int) -> _Resp:
        raise RuntimeError("boom")

    monkeypatch.setattr(auto_detect.requests, "get", _get)
    assert auto_detect.get_unique_id("192.0.2.13") is None


def test_is_reefbeat_unknown_hw_model_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea import auto_detect

    monkeypatch.setattr(
        auto_detect.requests,
        "get",
        lambda url, timeout: _Resp(
            status_code=200, json_data={"hw_model": "NOT-A-DEVICE", "name": "x"}
        ),
    )

    status, *_rest = auto_detect.is_reefbeat("192.0.2.14")
    assert status is False


def test_get_local_ips_socket_error_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea import auto_detect

    class _Sock:
        def __enter__(self) -> "_Sock":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        def connect(self, addr: Any) -> None:
            raise OSError("no net")

    monkeypatch.setattr(auto_detect.socket, "socket", lambda *a, **k: _Sock())
    assert auto_detect.get_local_ips(None) == []


def test_get_local_ips_infers_subnet_from_netifaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea import auto_detect

    class _Sock:
        def __enter__(self) -> "_Sock":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        def connect(self, addr: Any) -> None:
            return None

        def getsockname(self) -> tuple[str, int]:
            return ("192.0.2.1", 0)

    monkeypatch.setattr(auto_detect.socket, "socket", lambda *a, **k: _Sock())
    monkeypatch.setattr(auto_detect.netifaces, "interfaces", lambda: ["eth0"])
    monkeypatch.setattr(
        auto_detect.netifaces,
        "ifaddresses",
        lambda _iface: {
            auto_detect.netifaces.AF_INET: [
                {"addr": "192.0.2.1", "netmask": "255.255.255.252"}
            ]
        },
    )

    assert auto_detect.get_local_ips(None) == [
        "192.0.2.0",
        "192.0.2.1",
        "192.0.2.2",
        "192.0.2.3",
    ]


def _patch_socket_local_ip(
    monkeypatch: pytest.MonkeyPatch,
    *,
    local_ip: str,
) -> None:
    from custom_components.redsea import auto_detect

    class _Sock:
        def __enter__(self) -> "_Sock":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        def connect(self, addr: Any) -> None:
            return None

        def getsockname(self) -> tuple[str, int]:
            return (local_ip, 0)

    monkeypatch.setattr(auto_detect.socket, "socket", lambda *a, **k: _Sock())


def test_get_local_ips_netifaces_no_inet_addrs_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea import auto_detect

    _patch_socket_local_ip(monkeypatch, local_ip="192.0.2.1")
    monkeypatch.setattr(auto_detect.netifaces, "interfaces", lambda: ["eth0"])
    monkeypatch.setattr(auto_detect.netifaces, "ifaddresses", lambda _iface: {})

    assert auto_detect.get_local_ips(None) == []


def test_get_local_ips_netifaces_addr_mismatch_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea import auto_detect

    _patch_socket_local_ip(monkeypatch, local_ip="192.0.2.1")
    monkeypatch.setattr(auto_detect.netifaces, "interfaces", lambda: ["eth0"])
    monkeypatch.setattr(
        auto_detect.netifaces,
        "ifaddresses",
        lambda _iface: {
            auto_detect.netifaces.AF_INET: [
                {"addr": "192.0.2.99", "netmask": "255.255.255.0"}
            ]
        },
    )

    assert auto_detect.get_local_ips(None) == []


def test_get_local_ips_netifaces_missing_netmask_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea import auto_detect

    _patch_socket_local_ip(monkeypatch, local_ip="192.0.2.1")
    monkeypatch.setattr(auto_detect.netifaces, "interfaces", lambda: ["eth0"])
    monkeypatch.setattr(
        auto_detect.netifaces,
        "ifaddresses",
        lambda _iface: {auto_detect.netifaces.AF_INET: [{"addr": "192.0.2.1"}]},
    )

    assert auto_detect.get_local_ips(None) == []


def test_get_local_ips_netifaces_ifaddresses_exception_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea import auto_detect

    _patch_socket_local_ip(monkeypatch, local_ip="192.0.2.1")
    monkeypatch.setattr(auto_detect.netifaces, "interfaces", lambda: ["eth0"])

    def _boom(_iface: str) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(auto_detect.netifaces, "ifaddresses", _boom)

    assert auto_detect.get_local_ips(None) == []


def test_is_reefbeat_exception_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.redsea import auto_detect

    def _get(url: str, timeout: int) -> _Resp:
        raise RuntimeError("boom")

    monkeypatch.setattr(auto_detect.requests, "get", _get)

    status, *_rest = auto_detect.is_reefbeat("192.0.2.15")
    assert status is False


def test_get_reefbeats_uses_pool_when_threads_gt_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea import auto_detect

    monkeypatch.setattr(auto_detect, "get_local_ips", lambda _s=None: ["1.1.1.1"])

    class _FakePool:
        def __init__(self, n: int) -> None:
            self.n = n

        def __enter__(self) -> "_FakePool":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        def map(
            self, fn: Any, items: list[str]
        ) -> list[tuple[bool, str, str | None, str | None, str | None]]:
            assert items == ["1.1.1.1"]
            return [(True, "1.1.1.1", "HW", "Name", "uuid")]

    monkeypatch.setattr(auto_detect, "Pool", _FakePool)

    devices = auto_detect.get_reefbeats(subnetwork="192.0.2.0/30", nb_of_threads=2)
    assert devices == [
        {"ip": "1.1.1.1", "hw_model": "HW", "friendly_name": "Name", "uuid": "uuid"}
    ]
