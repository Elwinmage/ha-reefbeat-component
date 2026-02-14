from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest

import custom_components.redsea.reefbeat.api as api_mod
from custom_components.redsea.reefbeat.api import ReefBeatAPI

# tests/conftest.py has an autouse fixture that monkeypatches `ReefBeatAPI._http_get`
# to serve fixture data. For unit-testing the real implementation in api.py, keep
# a reference to the original function object and temporarily restore it.
_ORIG_HTTP_GET = ReefBeatAPI._http_get


@dataclass
class _FakeResponse:
    status: int
    reason: str = ""
    headers: dict[str, str] = field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )
    body_text: str = "OK"
    body_json: Any | None = None
    json_raises: bool = False

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
        return self.body_text

    async def json(self, content_type: Any = None) -> Any:
        if self.json_raises:
            raise ValueError("no json")
        return self.body_json


@dataclass
class _FakeSession:
    responses: dict[str, list[_FakeResponse]] = field(default_factory=dict)
    calls: list[tuple[str, str, Any | None]] = field(default_factory=list)

    def _pop(self, method: str) -> _FakeResponse:
        queue = self.responses.get(method, [])
        if not queue:
            raise AssertionError(f"No queued responses for method={method}")
        return queue.pop(0)

    def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("get", url, None))
        return self._pop("get")

    def post(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("post", url, kwargs.get("json")))
        return self._pop("post")

    def put(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("put", url, kwargs.get("json")))
        return self._pop("put")

    def delete(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("delete", url, None))
        return self._pop("delete")


def _make_api(session: _FakeSession) -> ReefBeatAPI:
    return ReefBeatAPI(
        ip="192.0.2.1",
        live_config_update=False,
        session=cast(Any, session),
        secure=False,
    )


def _make_secure_api(session: _FakeSession) -> ReefBeatAPI:
    return ReefBeatAPI(
        ip="192.0.2.1",
        live_config_update=False,
        session=cast(Any, session),
        secure=True,
    )


def test_get_data_caches_eval_path() -> None:
    session = _FakeSession()
    api = _make_api(session)

    # Add a custom source so we can fetch a predictable field
    api.add_source("/manual", "data", {"white": 12})

    key = "$.sources[?(@.name=='/manual')].data.white"
    assert api.get_data(key) == 12
    assert key in api._data_db


def test_set_data_clears_cached_path_on_update_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    bad_path = "$.sources[0].data.foo"
    api._data_db[bad_path] = "self.data['sources'][0]['data']['foo']"

    class _Expr:
        def update(self, data: Any, value: Any) -> Any:
            raise RuntimeError("boom")

    monkeypatch.setattr(api_mod, "parse", lambda _: cast(Any, _Expr()))

    api.set_data(bad_path, 1)

    assert bad_path not in api._data_db


def test_clean_message_clears_last_message_and_alert() -> None:
    session = _FakeSession()
    api = _make_api(session)

    api.data["message"] = {"message": "x", "alert": {"message": "y"}}

    api.clean_message("last_message")
    assert api.data["message"]["message"] == ""

    api.clean_message("last_alert_message")
    assert api.data["message"]["alert"] == {"message": ""}


@pytest.mark.asyncio
async def test_push_values_no_payload_does_not_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    sent: list[str] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append(url)
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/does-not-exist", method="post")
    assert sent == []


@pytest.mark.asyncio
async def test_http_send_sets_message_dict_and_adds_alert() -> None:
    session = _FakeSession(
        responses={
            "post": [
                _FakeResponse(status=200, body_json={"ok": True}),
            ]
        }
    )
    api = _make_api(session)

    res = await api.http_send("/action", payload={"x": 1}, method="post")

    assert res is not None and res.get("ok") is True
    assert api.data["message"] == {"ok": True, "alert": ""}


@pytest.mark.asyncio
async def test_http_send_sets_message_for_non_dict_json() -> None:
    session = _FakeSession(
        responses={
            "post": [
                _FakeResponse(status=200, body_json=["x"]),
            ]
        }
    )
    api = _make_api(session)

    await api.http_send("/action", payload={"x": 1}, method="post")

    assert api.data["message"] == {"data": ["x"], "alert": ""}


@pytest.mark.asyncio
async def test_http_send_sets_empty_message_when_no_json() -> None:
    session = _FakeSession(
        responses={
            "post": [
                _FakeResponse(status=200, body_json=None, json_raises=True),
            ]
        }
    )
    api = _make_api(session)

    await api.http_send("/action", payload={"x": 1}, method="post")

    assert api.data["message"] == {}


@pytest.mark.asyncio
async def test_http_send_400_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession(
        responses={
            "post": [
                _FakeResponse(status=400, body_text="bad"),
                _FakeResponse(status=200, body_json={"ok": True}),
            ]
        }
    )
    api = _make_api(session)

    sleeps: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(api_mod.asyncio, "sleep", _fake_sleep)

    await api.http_send("/action", payload={"x": 1}, method="post")

    # Ensure only the first (400) response was used.
    assert [c[0] for c in session.calls] == ["post"]
    # One sleep can still occur on the failed attempt.
    assert len(sleeps) == 1


@pytest.mark.asyncio
async def test_http_get_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession(
        responses={
            "get": [
                _FakeResponse(
                    status=200,
                    reason="OK",
                    body_text='{"ok": true}',
                    body_json={"ok": True},
                ),
            ]
        }
    )
    api = _make_api(session)

    res = await api.http_get("/dashboard")

    assert res is not None
    assert "ok" in res and res["ok"] is True
    assert "method" in res and res["method"] == "get"
    assert "status" in res and res["status"] == 200
    assert "elapsed_ms" in res

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("nope")

    monkeypatch.setattr(session, "get", _boom)
    res2 = await api.http_get("/dashboard")
    assert res2 is None


@pytest.mark.asyncio
async def test__http_get_handles_missing_endpoint_and_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    monkeypatch.setattr(ReefBeatAPI, "_http_get", _ORIG_HTTP_GET, raising=True)

    class _Match:
        def __init__(self, value: dict[str, Any]):
            self.value = value
            self.context = None
            self.path = "/"

    assert await api._http_get(cast(Any, session), _Match({})) is False

    import aiohttp

    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise aiohttp.ClientError("boom")

    monkeypatch.setattr(session, "get", _raise)
    assert (
        await api._http_get(cast(Any, session), _Match({"name": "/dashboard"})) is False
    )


@pytest.mark.asyncio
async def test__http_get_parses_non_json_content_type_and_sets_source_data() -> None:
    session = _FakeSession(
        responses={
            "get": [
                _FakeResponse(
                    status=200,
                    headers={"Content-Type": "text/plain"},
                    body_text='{"a": 1}',
                ),
                _FakeResponse(
                    status=200,
                    headers={"Content-Type": "text/plain"},
                    body_text="not json",
                ),
            ]
        }
    )
    api = _make_api(session)

    # Restore the real implementation (autouse fixture patches it).
    ReefBeatAPI._http_get = _ORIG_HTTP_GET  # type: ignore[method-assign]

    class _Match:
        def __init__(self, value: dict[str, Any]):
            self.value = value
            self.context = None
            self.path = "/"

    m1 = _Match({"name": "/x", "data": None})
    ok1 = await api._http_get(cast(Any, session), m1)
    assert ok1 is True
    assert m1.value["data"] == {"a": 1}

    m2 = _Match({"name": "/y", "data": None})
    ok2 = await api._http_get(cast(Any, session), m2)
    assert ok2 is True
    assert m2.value["data"] == "not json"


@pytest.mark.asyncio
async def test__http_get_secure_401_triggers_connect_and_retries() -> None:
    session = _FakeSession(
        responses={
            "get": [
                _FakeResponse(status=401, reason="unauthorized"),
                _FakeResponse(status=200, body_json={"ok": True}),
            ]
        }
    )
    api = _make_secure_api(session)

    # Restore the real implementation (autouse fixture patches it).
    ReefBeatAPI._http_get = _ORIG_HTTP_GET  # type: ignore[method-assign]

    called: list[str] = []

    async def _connect() -> None:
        called.append("connect")

    api.connect = _connect  # type: ignore[method-assign]

    class _Match:
        def __init__(self, value: dict[str, Any]):
            self.value = value
            self.context = None
            self.path = "/"

    m = _Match({"name": "/secure", "data": None})
    ok = await api._http_get(cast(Any, session), m)
    assert ok is True
    assert called == ["connect"]
    assert m.value["data"] == {"ok": True}
    # Ensure the 401 path performed a second GET.
    assert [c[0] for c in session.calls] == ["get", "get"]


@pytest.mark.asyncio
async def test__http_get_status_ge_400_returns_false() -> None:
    session = _FakeSession(
        responses={
            "get": [
                _FakeResponse(status=500, reason="server error"),
            ]
        }
    )
    api = _make_api(session)

    # Restore the real implementation (autouse fixture patches it).
    ReefBeatAPI._http_get = _ORIG_HTTP_GET  # type: ignore[method-assign]

    class _Match:
        def __init__(self, value: dict[str, Any]):
            self.value = value
            self.context = None
            self.path = "/"

    m = _Match({"name": "/bad", "data": None})
    ok = await api._http_get(cast(Any, session), m)
    assert ok is False


@pytest.mark.asyncio
async def test_connect_is_noop_and_fetch_data_default_data_only_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    await api.connect()

    called: list[str] = []

    async def _call_url(_session: Any, source: Any) -> None:
        called.append(str(source.value.get("name")))

    monkeypatch.setattr(api, "_call_url", _call_url)
    api.set_live_config_update(False)
    api.quick_refresh = None

    api.data["sources"] = [
        {"name": "/device-info", "type": "device-info", "data": ""},
        {"name": "/mode", "type": "config", "data": ""},
        {"name": "/wifi", "type": "data", "data": ""},
        {"name": "/dashboard", "type": "data", "data": ""},
    ]

    await api.fetch_data()
    assert set(called) == {"/wifi", "/dashboard"}


@pytest.mark.asyncio
async def test_push_values_with_payload_calls_http_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)
    api.add_source("/manual", "data", {"x": 1})

    called: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        called.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/manual", method="put")

    assert called == [(api._base_url + "/manual", {"x": 1}, "put")]


def test__get_data_slow_path_and_missing_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    api = _make_api(session)

    errs: list[str] = []

    monkeypatch.setattr(
        api_mod._LOGGER,
        "error",
        lambda msg, *args, **kwargs: errs.append(msg % args if args else msg),
    )

    assert api._get_data("$.does.not.exist") is None
    assert errs

    errs.clear()
    assert api._get_data("$.does.not.exist", is_None_possible=True) is None
    assert errs == []

    api.add_source("/manual", "data", {"white": 12})
    assert api._get_data("$.sources[?(@.name=='/manual')].data.white") == 12


@pytest.mark.asyncio
async def test_push_values_missing_payload_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    # Force payload to None and assert the error branch runs.
    errs: list[str] = []
    monkeypatch.setattr(
        api_mod._LOGGER,
        "error",
        lambda msg, *args, **kwargs: errs.append(msg % args if args else msg),
    )

    monkeypatch.setattr(api, "get_data", lambda *_a, **_k: None)

    await api.push_values("/definitely-missing")
    assert any("push_values: no payload" in e for e in errs)


def test_add_source_when_sources_missing_or_not_list() -> None:
    session = _FakeSession()
    api = _make_api(session)

    api.data.pop("sources", None)
    api.add_source("/x", "data", {"a": 1})
    assert api.get_data("$.sources[?(@.name=='/x')].data.a") == 1

    api.data["sources"] = "not-a-list"
    api.add_source("/y", "data", {"b": 2})
    assert api.get_data("$.sources[?(@.name=='/y')].data.b") == 2


@pytest.mark.asyncio
async def test__call_url_retries_and_sets_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    monkeypatch.setattr(api_mod, "HTTP_MAX_RETRY", 2)
    monkeypatch.setattr(api_mod, "HTTP_DELAY_BETWEEN_RETRY", 0)

    sleeps: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(api_mod.asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(api, "_http_get", lambda *_a, **_k: False)

    class _Match:
        def __init__(self, value: dict[str, Any]):
            self.value = value
            self.context = None
            self.path = "/"

    await api._call_url(cast(Any, session), _Match({"name": "/fail"}))
    assert api._in_error is True
    assert sleeps


@pytest.mark.asyncio
async def test_get_initial_data_success_and_in_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    called: list[str] = []

    async def _call_url(_session: Any, source: Any) -> None:
        called.append(str(source.value.get("name")))

    async def _fetch_config(config_path: str | None = None) -> None:
        called.append(f"config:{config_path}")

    async def _fetch_data() -> dict[str, Any]:
        called.append("data")
        return api.data

    monkeypatch.setattr(api, "_call_url", _call_url)
    monkeypatch.setattr(api, "fetch_config", _fetch_config)
    monkeypatch.setattr(api, "fetch_data", _fetch_data)

    # Ensure we have at least one device-info source.
    api.data["sources"] = [
        {"name": "/device-info", "type": "device-info", "data": ""},
        {"name": "/dashboard", "type": "data", "data": ""},
    ]

    await api.get_initial_data()
    assert "/device-info" in called
    assert "config:None" in called
    assert "data" in called

    api._in_error = True
    with pytest.raises(Exception, match=r"Initialization failed"):
        await api.get_initial_data()


@pytest.mark.asyncio
async def test_fetch_config_and_fetch_data_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    called: list[str] = []

    async def _call_url(_session: Any, source: Any) -> None:
        called.append(str(source.value.get("name")))

    monkeypatch.setattr(api, "_call_url", _call_url)

    api.data["sources"] = [
        {"name": "/device-info", "type": "device-info", "data": ""},
        {"name": "/firmware", "type": "config", "data": ""},
        {"name": "/mode", "type": "config", "data": ""},
        {"name": "/wifi", "type": "data", "data": ""},
        {"name": "/dashboard", "type": "data", "data": ""},
        {"name": "/preview", "type": "preview", "data": ""},
    ]

    await api.fetch_config()
    assert set(called) == {"/firmware", "/mode"}

    called.clear()
    await api.fetch_config("/mode")
    assert called == ["/mode"]

    # quick_refresh path
    called.clear()
    api.quick_refresh = "/dashboard"
    await api.fetch_data()
    assert called == ["/dashboard"]
    assert api.quick_refresh is None

    # live_config_update path
    called.clear()
    api.set_live_config_update(True)
    await api.fetch_data()
    assert "/device-info" not in called
    assert "/preview" not in called
    assert "/firmware" in called and "/mode" in called and "/wifi" in called


@pytest.mark.asyncio
async def test_press_delete_and_http_send_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(
        responses={
            "put": [_FakeResponse(status=200, body_json={"ok": True})],
            "delete": [_FakeResponse(status=200, body_json={"ok": True})],
        }
    )
    api = _make_api(session)

    sent: list[tuple[str, str]] = []

    async def _send(url: str, payload: Any = None, method: str = "post") -> Any:
        sent.append((method, url))
        return {"status": 200}

    monkeypatch.setattr(api, "_http_send", _send)

    await api.press("do", head=2)
    await api.delete("/x")
    assert sent[0][0] == "post" and sent[0][1].endswith("/do/2")
    assert sent[1][0] == "delete" and sent[1][1].endswith("/x")

    # Exercise _http_send delete branch with real fake session.
    api2 = _make_api(session)
    res_del = await api2._http_send(api2._base_url + "/x", method="delete")
    assert res_del is not None and res_del.get("status") == 200

    # Unsupported method is handled via the exception/retry path.
    monkeypatch.setattr(api_mod, "HTTP_MAX_RETRY", 1)
    monkeypatch.setattr(api_mod, "HTTP_DELAY_BETWEEN_RETRY", 0)

    async def _fake_sleep(_delay: float) -> None:
        return

    monkeypatch.setattr(api_mod.asyncio, "sleep", _fake_sleep)
    res_bad = await api2._http_send(api2._base_url + "/x", method="patch")
    assert res_bad is None


def test_get_data_missing_logs_and_eval_error_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    api = _make_api(session)

    errs: list[str] = []

    monkeypatch.setattr(
        api_mod._LOGGER,
        "error",
        lambda msg, *args, **kwargs: errs.append(msg % args if args else msg),
    )

    assert api.get_data("$.does.not.exist") is None
    assert errs

    # is_None_possible=True suppresses logging and returns None
    errs.clear()
    assert api.get_data("$.still.missing", is_None_possible=True) is None
    assert errs == []

    # Cached eval path that fails: returns None when is_None_possible
    api._data_db["$.bad"] = "self.data['nope']"
    assert api.get_data("$.bad", is_None_possible=True) is None

    with pytest.raises(Exception):
        api.get_data("$.bad", is_None_possible=False)


def test_add_remove_source_cache_and_live_config_update_helpers() -> None:
    session = _FakeSession()
    api = _make_api(session)

    api.add_source("/x", "data", {"a": 1})
    assert api.get_data("$.sources[?(@.name=='/x')].data.a") == 1

    api.remove_source("/x")
    assert (
        api.get_data("$.sources[?(@.name=='/x')].data.a", is_None_possible=True) is None
    )

    api._data_db["k"] = "v"
    api.clear_cache()
    assert api._data_db == {}

    api._in_error = True
    api.reset_error_state()
    assert api._in_error is False

    api.set_live_config_update(True)
    assert api.live_config_update is True
