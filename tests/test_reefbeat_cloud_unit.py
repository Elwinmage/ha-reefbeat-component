from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, cast

import pytest

import custom_components.redsea.reefbeat.cloud as cloud_mod
from custom_components.redsea.reefbeat.cloud import ReefBeatCloudAPI


@dataclass
class _FakeResponse:
    status: int
    text_body: str = ""
    json_body: Any | None = None

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        return None

    async def text(self) -> str:
        return self.text_body

    async def json(self, content_type: Any = None) -> Any:  # noqa: ARG002
        return self.json_body


@dataclass
class _FakeSession:
    response: _FakeResponse
    called: int = 0

    def post(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:  # noqa: ARG002
        self.called += 1
        return self.response


@pytest.mark.asyncio
async def test_cloud_connect_non_200_raises_invalidauth() -> None:
    # conftest.py patches ReefBeatCloudAPI.connect() for most tests; reload to get the real impl.
    mod = importlib.reload(cloud_mod)
    ReefBeatCloudAPI2 = mod.ReefBeatCloudAPI
    InvalidAuth = mod.InvalidAuth

    session = _FakeSession(_FakeResponse(status=401, text_body="nope", json_body={}))
    api = ReefBeatCloudAPI2(
        username="u",
        password="p",
        live_config_update=True,
        ip="cloud.example",
        session=cast(Any, session),
        disable_supplement=True,
    )

    with pytest.raises(InvalidAuth, match="nope"):
        await api.connect()


@pytest.mark.asyncio
async def test_cloud_connect_missing_token_raises_invalidauth() -> None:
    mod = importlib.reload(cloud_mod)
    ReefBeatCloudAPI2 = mod.ReefBeatCloudAPI
    InvalidAuth = mod.InvalidAuth

    session = _FakeSession(
        _FakeResponse(status=200, text_body="ok", json_body={"x": 1})
    )
    api = ReefBeatCloudAPI2(
        username="u",
        password="p",
        live_config_update=True,
        ip="cloud.example",
        session=cast(Any, session),
        disable_supplement=True,
    )

    with pytest.raises(InvalidAuth, match="access_token"):
        await api.connect()


@pytest.mark.asyncio
async def test_cloud_connect_sets_header_and_auth_date() -> None:
    mod = importlib.reload(cloud_mod)
    ReefBeatCloudAPI2 = mod.ReefBeatCloudAPI

    session = _FakeSession(
        _FakeResponse(status=200, text_body="ok", json_body={"access_token": "t"})
    )
    api = ReefBeatCloudAPI2(
        username="u",
        password="p",
        live_config_update=True,
        ip="cloud.example",
        session=cast(Any, session),
        disable_supplement=True,
    )

    assert api._header is None
    assert api._auth_date is None

    await api.connect()

    assert api._header == {"Authorization": "Bearer t"}
    assert api._auth_date is not None


@pytest.mark.asyncio
async def test_cloud_http_send_retries_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    api = ReefBeatCloudAPI(
        username="u",
        password="p",
        live_config_update=False,
        ip="cloud.example",
        session=cast(Any, object()),
        disable_supplement=True,
    )

    connect_called: list[str] = []

    async def _connect() -> None:
        connect_called.append("ok")

    monkeypatch.setattr(api, "connect", _connect)

    calls: list[tuple[str, Any, str]] = []

    async def _http_send(url: str, payload: Any = None, method: str = "post") -> Any:
        calls.append((url, payload, method))
        if len(calls) == 1:
            return {"status": 401}
        return {"status": 200}

    monkeypatch.setattr(api, "_http_send", _http_send)

    res = await api.http_send("/user")

    assert res is not None and res.get("status") == 200
    assert connect_called == ["ok"]
    assert len(calls) == 2
    assert calls[0][1] == {}, "payload should default to {} when None"


@pytest.mark.asyncio
async def test_cloud_connect_renew_branch_and_get_devices() -> None:
    mod = importlib.reload(cloud_mod)
    ReefBeatCloudAPI2 = mod.ReefBeatCloudAPI

    session = _FakeSession(
        _FakeResponse(status=200, text_body="ok", json_body={"access_token": "token"})
    )
    api = ReefBeatCloudAPI2(
        username="u",
        password="p",
        live_config_update=False,
        ip="cloud.example",
        session=cast(Any, session),
        disable_supplement=True,
    )

    await api.connect()

    # Force the "renew" log branch.
    api._auth_date = 123.0
    await api.connect()

    api.data["sources"] = [
        {"name": "/device", "type": "config", "data": [{"type": "led", "id": 1}]},
    ]
    matches = api.get_devices("led")
    assert len(matches) == 1
