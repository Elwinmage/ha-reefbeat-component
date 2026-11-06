"""Poseidon rescue script: generation, download, and a run against a device."""

from __future__ import annotations

import importlib.abc
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.poseidon import const, rescue_script
from custom_components.redsea.poseidon.keystore import DeviceKeys
from custom_components.redsea.poseidon.manager import Poseidon

SECRET = "0123456789abcdef"
RELAY = "192.0.2.1:1884"


class FakeDevice:
    """A local /cloud API on 127.0.0.1, recording the writes."""

    def __init__(self, url: str, hwid: str, refuse: str = "") -> None:
        self.hwid = hwid
        self.cloud: dict[str, Any] = {"url": url, "api_key": "k"}
        self.refuse = refuse
        self.posts: list[tuple[str, Any]] = []
        device = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any, **kwargs: Any) -> None:
                return

            def _send(self, status: int, body: Any = None) -> None:
                data = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                if self.path == "/device-info":
                    self._send(200, {"hwid": device.hwid, "hw_model": "RSWAVE45"})
                else:
                    self._send(200, device.cloud)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                payload: Any = json.loads(raw) if raw else None
                device.posts.append((self.path, payload))
                if self.path == device.refuse:
                    self._send(500)
                    return
                if self.path == "/cloud":
                    device.cloud = {**device.cloud, "url": payload["url"]}
                self._send(200, {"success": True})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.ip = f"127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def _poseidon(hass: HomeAssistant, devices: dict[str, DeviceKeys]) -> Poseidon:
    entry = MockConfigEntry(
        domain="redsea",
        data={"poseidon": True, "port": 1884, "host": "192.0.2.1"},
    )
    hass.data["redsea"] = {}
    poseidon = Poseidon(hass, entry)
    poseidon.keystore.devices = devices
    return poseidon


TEMPLATE = Path(rescue_script.__file__)


class _GeneratedLoader(importlib.abc.SourceLoader):
    """Serves a generated script under the template's path.

    The generated script differs from the template by its EMBEDDED line only
    (same line count), so running it under that path credits the template's
    lines to coverage.
    """

    def __init__(self, text: str) -> None:
        self.text = text

    def get_filename(self, fullname: str | None = None) -> str:
        return str(TEMPLATE)

    def get_data(self, path: str) -> bytes:
        return self.text.encode("utf-8")


def _load(text: str) -> Any:
    """Import a generated script as its own module."""
    template = TEMPLATE.read_text(encoding="utf-8")
    assert text.count("\n") == template.count("\n")
    loader = _GeneratedLoader(text)
    spec = importlib.util.spec_from_loader("poseidon_rescue", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def no_settle(monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    monkeypatch.setattr(time, "sleep", lambda _s: None)


def test_rescue_data_and_script(hass: HomeAssistant) -> None:
    poseidon = _poseidon(
        hass,
        {
            "aa": DeviceKeys(
                hwid="aa", name="Wave", api_key="k", api_secret=SECRET, ip="10.0.0.2"
            ),
            "bb": DeviceKeys(
                hwid="bb",
                api_key="k",
                api_secret=SECRET,
                mqtt_url="mqtt.example:1883",
            ),
            "nokeys": DeviceKeys(hwid="nokeys"),
        },
    )
    data = poseidon.rescue_data()
    assert data["relay"] == RELAY
    by_hwid = {d["hwid"]: d for d in data["devices"]}
    assert set(by_hwid) == {"aa", "bb"}
    assert by_hwid["aa"]["mqtt_url"] == const.NORMAL_MQTT_URL
    assert by_hwid["aa"]["ip"] == "10.0.0.2"
    assert by_hwid["bb"]["mqtt_url"] == "mqtt.example:1883"
    module = _load(poseidon.rescue_script())
    assert module.EMBEDDED["devices"] == data["devices"]
    assert module.EMBEDDED["relay"] == RELAY


def test_rescue_template_must_have_its_line(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    poseidon = _poseidon(hass, {})
    original = Path.read_text

    def _read(self: Path, *args: Any, **kwargs: Any) -> str:
        if self.name == "rescue_script.py":
            return "EMBEDDED = {}\n"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _read)
    with pytest.raises(ValueError):
        poseidon.rescue_script()


def test_rescue_run(
    hass: HomeAssistant,
    socket_enabled: Any,
    no_settle: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    on_relay = FakeDevice(RELAY, "aa")
    normal = FakeDevice(const.NORMAL_MQTT_URL, "bb")
    try:
        poseidon = _poseidon(
            hass,
            {
                "aa": DeviceKeys(
                    hwid="aa", name="Wave", api_key="ka", api_secret=SECRET, ip="x"
                ),
                "bb": DeviceKeys(
                    hwid="bb", api_key="kb", api_secret=SECRET, ip=normal.ip
                ),
                "cc": DeviceKeys(hwid="cc", api_key="kc", api_secret=SECRET),
            },
        )
        module = _load(poseidon.rescue_script())
        # The device moved: its address given on the command line
        ip = ["--ip", f"aa={on_relay.ip}", "--no-scan"]
        assert module.main([*ip, "--dry-run"]) == 0
        assert on_relay.posts == []
        out = capsys.readouterr().out
        assert "to switch back" in out and "left as is" in out
        assert "no known address" in out and "cc: not found" in out

        assert module.main([*ip, "--yes"]) == 1  # cc is nowhere
        assert on_relay.posts == [
            ("/cloud/disable", None),
            (
                "/cloud",
                {"url": const.NORMAL_MQTT_URL, "api_key": "ka", "api_secret": SECRET},
            ),
            ("/cloud/enable", None),
        ]
        assert on_relay.cloud["url"] == const.NORMAL_MQTT_URL
        assert normal.posts == []
        out = capsys.readouterr().out
        assert "OK" in out and "Not switched back: cc" in out

        # Nothing left on the relay
        assert module.main([*ip, "--only", "aa", "--yes"]) == 0
        assert "Nothing to switch back" in capsys.readouterr().out
    finally:
        on_relay.close()
        normal.close()


def test_rescue_never_writes_into_another_device(
    hass: HomeAssistant,
    socket_enabled: Any,
    no_settle: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Two devices swapped their addresses: each found by scan, by hwid."""
    first = FakeDevice(RELAY, "bb")
    second = FakeDevice(RELAY, "aa")
    try:
        poseidon = _poseidon(
            hass,
            {
                "aa": DeviceKeys(
                    hwid="aa", api_key="ka", api_secret=SECRET, ip=first.ip
                ),
                "bb": DeviceKeys(
                    hwid="bb", api_key="kb", api_secret=SECRET, ip=second.ip
                ),
            },
        )
        module = _load(poseidon.rescue_script())
        scanned: list[list[str]] = []

        def _hosts(subnets: list[str]) -> list[str]:
            scanned.append(subnets)
            return ["127.0.0.1:1", first.ip, second.ip] if subnets else []

        module.subnet_hosts = _hosts
        module.local_ip = lambda: ""
        # Loopback addresses only: nothing to scan without --scan
        assert module.main(["--dry-run"]) == 1
        assert "pass --scan" in capsys.readouterr().out
        assert module.main(["--scan", "10.9.8.0/30", "--yes"]) == 0
        out = capsys.readouterr().out
        assert "is another device now" in out
        assert f"aa: found at {second.ip}" in out
        # Keys of each device written into that device only
        assert second.posts[1][1]["api_key"] == "ka"
        assert first.posts[1][1]["api_key"] == "kb"
        assert scanned == [[], ["10.9.8.0/30"]]
    finally:
        first.close()
        second.close()


def test_rescue_with_keystore_and_failures(
    socket_enabled: Any,
    no_settle: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from custom_components.redsea.poseidon import rescue_script as module

    refusing = FakeDevice(RELAY, "aa", refuse="/cloud")
    try:
        keystore = tmp_path / "keystore.json"
        keystore.write_text(
            json.dumps(
                {
                    "devices": {
                        "aa": {"api_key": "k", "api_secret": SECRET, "ip": refusing.ip},
                        "dead": {
                            "api_key": "k",
                            "api_secret": SECRET,
                            "ip": "127.0.0.1:1",
                        },
                        "nokeys": {"ip": "x"},
                    }
                }
            ),
            encoding="utf-8",
        )
        ks = ["--keystore", str(keystore), "--no-scan"]
        # Not embedded: a keystore is needed
        assert module.main([]) == 2
        assert module.main(["--keystore", str(tmp_path / "missing.json")]) == 2
        bad = tmp_path / "bad.json"
        bad.write_text("[]", encoding="utf-8")
        assert module.main(["--keystore", str(bad)]) == 2
        assert module.main([*ks, "--ip", "nope"]) == 2
        assert module.main([*ks, "--only", "zz"]) == 1
        # Too many addresses to scan
        assert module.main(["--keystore", str(keystore), "--scan", "10.0.0.0/16"]) == 2
        # No relay known: anything not on its normal broker is switched back
        monkeypatch.setattr("builtins.input", lambda _prompt: "n")
        assert module.main(ks) == 1
        assert "Cancelled" in capsys.readouterr().out
        assert refusing.posts == []
        monkeypatch.setattr("builtins.input", lambda _prompt: "oui")
        assert module.main(ks) == 1
        # The write refused: enabled again all the same
        assert [path for path, _ in refusing.posts] == [
            "/cloud/disable",
            "/cloud",
            "/cloud/enable",
        ]
        out = capsys.readouterr().out
        assert "FAILED" in out and "no answer at 127.0.0.1:1" in out
        # Every device on its normal broker, --all forces them
        refusing.cloud["url"] = const.NORMAL_MQTT_URL
        refusing.refuse = ""
        assert module.main([*ks, "--only", "aa", "-y"]) == 0
        assert module.main([*ks, "--only", "aa", "--all", "-y"]) == 0
        assert "Every device is back" in capsys.readouterr().out
    finally:
        refusing.close()


def test_scan_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.redsea.poseidon import rescue_script as module

    assert module.host_of("192.168.1.20") == "192.168.1.20"
    assert module.host_of("192.168.1.20:8080") == "192.168.1.20"
    assert module.host_of("wave.local") == ""
    monkeypatch.setattr(module, "local_ip", lambda: "10.0.0.5")
    assert module.scan_subnets(
        [], ["192.168.1.20", "192.168.1.30", "127.0.0.1", ""]
    ) == [
        "192.168.1.0/24",
        "10.0.0.0/24",
    ]
    assert module.scan_subnets(["10.3.141.7/24"], ["192.168.1.20"]) == ["10.3.141.0/24"]
    assert len(module.subnet_hosts(["10.0.0.0/24", "10.0.1.0/30"])) == 256
    with pytest.raises(ValueError):
        module.subnet_hosts(["10.0.0.0/16"])
    assert module.identify("") == ""
    assert isinstance(module.local_ip(), str)


def test_local_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.redsea.poseidon import rescue_script as module

    class _Sock:
        def __init__(self, *args: Any) -> None:
            return

        def __enter__(self) -> _Sock:
            return self

        def __exit__(self, *args: Any) -> None:
            return

        def connect(self, address: Any) -> None:
            return

        def getsockname(self) -> tuple[str, int]:
            return ("10.0.0.5", 5000)

    monkeypatch.setattr(module.socket, "socket", _Sock)
    assert module.local_ip() == "10.0.0.5"

    def _fail(*args: Any) -> Any:
        raise OSError("no route")

    monkeypatch.setattr(module.socket, "socket", _fail)
    assert module.local_ip() == ""


def test_identify_rejects_non_reefbeat(
    socket_enabled: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.poseidon import rescue_script as module

    monkeypatch.setattr(module, "request", lambda *a, **k: ["not", "a", "dict"])
    assert module.identify("10.0.0.1") == ""


def test_rescue_helpers() -> None:
    from custom_components.redsea.poseidon import rescue_script as module

    assert module.broker_of(" MQTT://Host:1883/ ") == "host:1883"
    assert module.label({"hwid": "aa"}) == "aa"
    assert module.normal_url({"mqtt_url": RELAY}, RELAY) == module.NORMAL_URL


async def test_rescue_view_and_step(hass: HomeAssistant) -> None:
    from types import SimpleNamespace

    from homeassistant.components.http.const import KEY_HASS_USER
    from homeassistant.helpers.http import KEY_HASS

    from custom_components.redsea.poseidon.http_view import PoseidonRescueView

    class _Request(dict):
        def __init__(self, user: object) -> None:
            super().__init__({KEY_HASS_USER: user})
            self.app = {KEY_HASS: hass}

    view = PoseidonRescueView()
    admin = SimpleNamespace(is_admin=True)
    assert view.url == const.RESCUE_VIEW_URL
    assert (await view.get(_Request(admin))).status == 404  # type: ignore[arg-type]
    poseidon = _poseidon(
        hass, {"aa": DeviceKeys(hwid="aa", api_key="k", api_secret=SECRET)}
    )
    hass.data[const.DATA_POSEIDON] = poseidon
    try:
        response = await view.get(_Request(admin))  # type: ignore[arg-type]
        assert response.status == 200
        assert response.headers["Content-Disposition"] == (
            f'attachment; filename="{const.RESCUE_FILE}"'
        )
        module = _load(response.body.decode())  # type: ignore[union-attr]
        assert module.EMBEDDED["devices"][0]["api_secret"] == SECRET

        from custom_components.redsea.poseidon.flow import PoseidonOptionsFlowMixin

        class _Flow(PoseidonOptionsFlowMixin):
            def __init__(self) -> None:
                self.hass = hass

            def async_abort(self, **kwargs: Any) -> dict[str, Any]:
                return kwargs

        poseidon.signed_url = lambda path: f"{path}?authSig=x"  # type: ignore[method-assign]
        flow: Any = _Flow()
        result = await flow.async_step_rescue_script()
        assert result["reason"] == "poseidon_rescue_link"
        placeholders = result["description_placeholders"]
        assert const.RESCUE_VIEW_URL in placeholders["link_start"]
        assert placeholders["count"] == "1"
        assert placeholders["file"] == const.RESCUE_FILE
    finally:
        hass.data.pop(const.DATA_POSEIDON)
    hass.data.pop(const.DATA_POSEIDON, None)
    flow = _Flow()
    assert (await flow.async_step_rescue_script())["reason"] == "poseidon_not_running"


def test_request_and_get_cloud_edge_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: Any) -> None:
            return

        def read(self) -> bytes:
            return self.body

    sent: list[Any] = []

    def _urlopen(req: Any, timeout: float) -> _Resp:
        sent.append((req.get_method(), req.full_url, req.data))
        return _Resp(b"<html>not json</html>")

    monkeypatch.setattr(rescue_script.urllib.request, "urlopen", _urlopen)
    # An answer that is not JSON: None
    assert rescue_script.request("10.0.0.1", "POST", "/cloud/enable") is None
    assert sent == [("POST", "http://10.0.0.1/cloud/enable", b"")]

    def _down(*args: Any, **kwargs: Any) -> Any:
        raise OSError("unreachable")

    monkeypatch.setattr(rescue_script, "request", _down)
    assert rescue_script.get_cloud("10.0.0.1") is None
