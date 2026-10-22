"""Fakes shared by the Poseidon tests: device HTTP, coordinators, cloud."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

HWID = "083a8d2be9ec"
SECRET = "0123456789abcdef"


class FakeHttp:
    """Stands for DeviceHttp: canned GET answers, recorded writes."""

    def __init__(
        self,
        answers: dict[str, Any] | None = None,
        refuse: set[str] | None = None,
        cloud: dict[str, Any] | None = None,
        set_cloud_ok: bool = True,
        ip: str = "192.0.2.10",
    ) -> None:
        self.answers = dict(answers or {})
        self.refuse = set(refuse or set())
        self.cloud = cloud
        self.set_cloud_ok = set_cloud_ok
        self.ip = ip
        self.writes: list[tuple[str, Any, str]] = []
        self.cloud_writes: list[tuple[str, str, str]] = []
        # Answers given once, consumed in order: endpoint -> [answers]
        self.sequence: dict[str, list[Any]] = {}

    async def get_json(self, endpoint: str, timeout: float = 5.0) -> Any:
        queued = self.sequence.get(endpoint)
        if queued:
            return queued.pop(0)
        return self.answers.get(endpoint)

    async def write_json(
        self,
        endpoint: str,
        payload: Any = None,
        method: str = "POST",
        timeout: float = 8.0,
    ) -> bool:
        self.writes.append((endpoint, payload, method))
        return endpoint not in self.refuse

    async def get_cloud(self) -> dict[str, Any] | None:
        return self.cloud

    async def set_cloud(self, url: str, api_key: str, api_secret: str) -> bool:
        self.cloud_writes.append((url, api_key, api_secret))
        if self.set_cloud_ok and isinstance(self.cloud, dict):
            self.cloud = {**self.cloud, "url": url}
        return self.set_cloud_ok


class FakeCloudApi:
    """Stands for ReefBeatCloudAPI.http_send."""

    def __init__(
        self,
        delete_status: int = 204,
        created: Any = None,
    ) -> None:
        self.delete_status = delete_status
        self.created = (
            {"url": "mqtt.reef-beat.com:1883", "api_key": "key-1", "api_secret": SECRET}
            if created is None
            else created
        )
        self.calls: list[tuple[str, Any, str]] = []

    async def http_send(
        self, action: str, payload: Any = None, method: str = "post"
    ) -> Any:
        self.calls.append((action, payload, method))
        if method == "delete":
            return {"status": self.delete_status}
        if self.created == "none":
            return None
        return {"status": 200, "json": self.created}


@dataclass
class FakeCoordinator:
    """Stands for a device coordinator of the integration."""

    model_id: str = HWID
    model: str = "RSWAVE45"
    title: str = "Wave left"
    _ip: str = "192.0.2.10"
    last_update_success: bool = True
    cloud: dict[str, Any] | None = None
    devices: list[Any] | None = None
    data: dict[str, Any] = field(default_factory=dict)
    fetched: list[str] = field(default_factory=list)
    fail_fetch: bool = False

    def __post_init__(self) -> None:
        self._entry = SimpleNamespace(data=self.data)

    def get_data(self, path: str, is_None_possible: bool = False) -> Any:
        if "/cloud" in path:
            return self.cloud
        if "/device" in path:
            return self.devices
        return None

    async def fetch_config(self, config_path: str | None = None) -> None:
        if self.fail_fetch:
            raise RuntimeError("unreachable")
        self.fetched.append(str(config_path))


def cloud_coordinator(devices: list[Any] | None = None, api: Any = None) -> Any:
    """A cloud account coordinator (entry data with a username)."""
    coordinator = FakeCoordinator(
        model_id="cloud",
        title="me@example.com",
        devices=devices,
        data={"username": "me@example.com"},
    )
    coordinator.my_api = api or FakeCloudApi()  # type: ignore[attr-defined]
    return coordinator


def connect_packet(username: str, password: str = "", client_id: str = "dev") -> bytes:
    from custom_components.redsea.poseidon.mqtt import build_connect_packet

    return build_connect_packet(client_id, username, password)
