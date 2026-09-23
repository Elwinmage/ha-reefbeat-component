"""Unit tests for the HTTP status policy of the ReefBeat API clients.

A 503 is a firmware *refusal* on local devices (e.g. a probe disconnected from
a RSControl): a definitive failure, not retried, and never mistaken for a
success. Only the RSWAVE45 firmware quirk (503 on writes and on ``GET /``)
is accepted as a success, and only on ReefWave. The cloud API keeps treating
503 as a transient outage worth retrying.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest

import custom_components.redsea.reefbeat.api as api_mod
from custom_components.redsea.reefbeat.api import ReefBeatAPI
from custom_components.redsea.reefbeat.wave import ReefWaveAPI

# conftest.py monkeypatches `_http_get` to serve fixtures: keep the real one.
_ORIG_HTTP_GET = ReefBeatAPI._http_get


@dataclass
class _Resp:
    status: int
    reason: str = ""
    headers: dict[str, str] = field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )
    body: Any = None

    async def __aenter__(self) -> _Resp:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def text(self) -> str:
        return "" if self.body is None else str(self.body)

    async def json(self, content_type: Any = None) -> Any:
        return self.body


@dataclass
class _Session:
    status: int
    body: Any = None
    calls: list[str] = field(default_factory=list)

    def _answer(self, method: str) -> _Resp:
        self.calls.append(method)
        return _Resp(self.status, body=self.body)

    def get(self, url: str, *a: Any, **k: Any) -> _Resp:
        return self._answer("get")

    def post(self, url: str, *a: Any, **k: Any) -> _Resp:
        return self._answer("post")

    def put(self, url: str, *a: Any, **k: Any) -> _Resp:
        return self._answer("put")

    def delete(self, url: str, *a: Any, **k: Any) -> _Resp:
        return self._answer("delete")


class _Match:
    def __init__(self, value: dict[str, Any]) -> None:
        self.value = value
        self.context = None
        self.path = "/"


def _api(session: _Session, *, secure: bool = False) -> ReefBeatAPI:
    return ReefBeatAPI("192.0.2.1", False, cast(Any, session), secure=secure)


def _wave(session: _Session) -> ReefWaveAPI:
    return ReefWaveAPI("192.0.2.1", False, cast(Any, session))


@pytest.fixture(autouse=True)
def _no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_mod, "HTTP_DELAY_BETWEEN_RETRY", 0)
    monkeypatch.setattr(ReefBeatAPI, "_http_get", _ORIG_HTTP_GET, raising=True)


# ===========================================================================
# Pure policy
# ===========================================================================


@pytest.mark.parametrize(
    ("status", "method", "path", "base_ok", "wave_ok"),
    [
        (200, "get", "/dashboard", True, True),
        (204, "delete", "/probe", True, True),
        (503, "put", "/probe/config", False, True),
        (503, "post", "/preview", False, True),
        (503, "get", "/", False, True),
        (503, "get", "/auto", False, False),
        (500, "put", "/x", False, False),
        (404, "get", "/", False, False),
    ],
)
def test_is_status_ok(
    status: int, method: str, path: str, base_ok: bool, wave_ok: bool
) -> None:
    assert _api(_Session(200))._is_status_ok(status, path, method) is base_ok
    assert _wave(_Session(200))._is_status_ok(status, path, method) is wave_ok


@pytest.mark.parametrize(
    ("status", "secure", "expected"),
    [
        (503, False, True),
        (503, True, False),
        (400, False, True),
        (404, True, True),
        (401, False, False),
        (500, False, False),
    ],
)
def test_is_definitive_failure(status: int, secure: bool, expected: bool) -> None:
    api = _api(_Session(200), secure=secure)
    assert api._is_definitive_failure(status) is expected


def test_path_of() -> None:
    api = _api(_Session(200))
    assert api._path_of("http://192.0.2.1/probe?type=ph") == "/probe?type=ph"
    assert api._path_of("http://192.0.2.1") == "/"
    assert api._path_of("http://other/x") == "http://other/x"


def test_policy_tolerates_bare_instances() -> None:
    # Objects built with __new__ (as many unit tests do) lack the attributes.
    api = ReefBeatAPI.__new__(ReefBeatAPI)
    assert api._path_of("/x") == "/x"
    assert api._is_definitive_failure(503) is True


# ===========================================================================
# Writes (_http_send)
# ===========================================================================


@pytest.mark.asyncio
async def test_local_503_write_is_a_single_failed_attempt() -> None:
    session = _Session(503, {"success": False, "message": "probe disconnected"})
    api = _api(session)

    result = await api.http_send("/probe/config", [{"uid": "0x1"}], "put")

    assert result is not None and result.get("ok") is False
    assert session.calls == ["put"]  # not retried
    assert "alert" in api.data["message"]


@pytest.mark.asyncio
async def test_wave_503_write_is_a_success() -> None:
    session = _Session(503, {"success": True})
    api = _wave(session)

    result = await api.http_send("/preview", {}, "post")

    assert result is not None and result.get("ok") is True
    assert session.calls == ["post"]


@pytest.mark.asyncio
async def test_cloud_503_write_is_retried() -> None:
    session = _Session(503)
    api = _api(session, secure=True)

    result = await api.http_send("/x", {}, "post")

    assert result is not None and result.get("ok") is False
    assert len(session.calls) == api_mod.HTTP_MAX_RETRY


# ===========================================================================
# Reads (_http_get, one-off http_get)
# ===========================================================================


@pytest.mark.asyncio
async def test_local_503_poll_is_definitive() -> None:
    api = _api(_Session(503))
    source = _Match({"name": "/probe/offset?type=temperature&uid=0x1", "data": 1})

    assert await api._http_get(cast(Any, api._session), source) is None
    assert source.value["data"] == 1


@pytest.mark.asyncio
async def test_local_503_poll_does_not_mark_device_in_error() -> None:
    session = _Session(503)
    api = _api(session)

    await api._call_url(cast(Any, session), _Match({"name": "/probe/offset"}))

    assert api._in_error is False
    assert session.calls == ["get"]


@pytest.mark.asyncio
async def test_cloud_503_poll_is_transient() -> None:
    api = _api(_Session(503), secure=True)
    assert await api._http_get(cast(Any, api._session), _Match({"name": "/x"})) is False


@pytest.mark.asyncio
async def test_wave_503_on_root_is_accepted() -> None:
    api = _wave(_Session(503, {"uuid": "abc"}))
    source = _Match({"name": "/", "data": ""})

    assert await api._http_get(cast(Any, api._session), source) is True
    assert source.value["data"] == {"uuid": "abc"}


@pytest.mark.asyncio
async def test_wave_503_on_other_read_is_rejected() -> None:
    api = _wave(_Session(503))
    source = _Match({"name": "/auto", "data": "keep"})

    assert await api._http_get(cast(Any, api._session), source) is None
    assert source.value["data"] == "keep"


@pytest.mark.asyncio
async def test_one_off_get_reports_local_503_as_failure() -> None:
    api = _api(_Session(503, {"success": False}))

    result = await api.http_get("/probe?type=ph&uid=0x1")

    assert result is not None and result.get("ok") is False
