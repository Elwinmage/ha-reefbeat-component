"""Poseidon keystore merge, export and import."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.poseidon.keystore import DeviceKeys, KeyStore
from custom_components.redsea.poseidon.manager import Poseidon

SECRET = "0123456789abcdef"


def _record(
    hwid: str, updated_at: str = "", secret: str = SECRET, ip: str = ""
) -> dict:
    return {
        "hwid": hwid,
        "api_key": "k",
        "api_secret": secret,
        "updated_at": updated_at,
        "ip": ip,
    }


def test_merge_rules(hass: HomeAssistant) -> None:
    store = KeyStore(hass)
    store.devices = {
        "aa": DeviceKeys(
            hwid="aa",
            api_key="k",
            api_secret=SECRET,
            updated_at="2026-10-14T20:00:00+02:00",
        ),
        "bb": DeviceKeys(
            hwid="bb",
            api_key="k",
            api_secret=SECRET,
            updated_at="2026-10-14T20:00:00+02:00",
            ip="192.0.2.2",
        ),
        "cc": DeviceKeys(hwid="cc"),
    }
    counts = store.merge(
        {
            "devices": {
                # Same instant written with another offset: not newer
                "aa": _record("aa", "2026-10-14T18:00:00+00:00"),
                # Newer: replaces, keeps the known address
                "BB": _record("BB", "2026-10-14T19:00:00+00:00"),
                # Stored without keys: replaced
                "cc": _record("cc"),
                "dd": _record("dd"),
                "ee": _record("ee", secret="short"),
                "ff": "not a record",
            }
        }
    )
    assert counts == (1, 2, 3)
    assert store.devices["bb"].ip == "192.0.2.2"
    assert store.devices["cc"].has_keys
    assert "dd" in store.devices and "ee" not in store.devices
    with pytest.raises(ValueError):
        store.merge({"no": "devices"})
    with pytest.raises(ValueError):
        store.merge([1, 2])


def _poseidon(hass: HomeAssistant) -> Poseidon:
    entry = MockConfigEntry(
        domain="redsea",
        data={
            "poseidon": True,
            "port": 1884,
            "host": "192.0.2.1",
            "cloud_account": "c",
        },
    )
    return Poseidon(hass, entry)


async def test_export_and_import(hass: HomeAssistant, tmp_path: Path) -> None:
    hass.config.config_dir = str(tmp_path)
    poseidon = _poseidon(hass)
    poseidon.keystore.devices = {
        "aa": DeviceKeys(hwid="aa", api_key="k", api_secret=SECRET)
    }
    path = await poseidon.async_export()
    assert path.parent == tmp_path / "redsea" / "poseidon"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["devices"]["aa"]["api_secret"] == SECRET

    other = _poseidon(hass)
    added = []
    other.async_set_switch_adder(added.append)
    assert await other.async_import(path) == (1, 0, 0)
    assert other.keystore.get("aa") is not None
    # Nothing new the second time
    assert await other.async_import(path) == (0, 0, 1)
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        await other.async_import(bad)
    with pytest.raises(OSError):
        await other.async_import(tmp_path / "missing.json")


async def test_import_upload(
    hass: HomeAssistant, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    from custom_components.redsea.poseidon import manager

    sent = tmp_path / "upload.json"
    sent.write_text(json.dumps({"devices": {"aa": _record("aa")}}), encoding="utf-8")
    used: list[str] = []

    @contextmanager
    def _uploaded(_hass: HomeAssistant, file_id: str):  # type: ignore[no-untyped-def]
        used.append(file_id)
        if file_id == "gone":
            raise ValueError("File does not exist")
        yield sent

    monkeypatch.setattr(manager, "process_uploaded_file", _uploaded)
    poseidon = _poseidon(hass)
    assert await poseidon.async_import_upload("id-1") == (1, 0, 0)
    assert used == ["id-1"]
    with pytest.raises(FileNotFoundError):
        await poseidon.async_import_upload("gone")
    sent.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        await poseidon.async_import_upload("id-2")


def test_export_url(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import timedelta

    from custom_components.redsea.poseidon import const, manager

    calls: list[tuple[str, timedelta]] = []

    def _sign(_hass: HomeAssistant, path: str, expiration: timedelta) -> str:
        calls.append((path, expiration))
        return f"{path}?authSig=x"

    monkeypatch.setattr(manager, "async_sign_path", _sign)
    poseidon = _poseidon(hass)
    assert poseidon.export_url() == f"{const.EXPORT_VIEW_URL}?authSig=x"
    assert calls == [(const.EXPORT_VIEW_URL, timedelta(minutes=5))]
    assert poseidon.export_filename().startswith("keystore-")
    assert poseidon.export_filename().endswith(".json")


async def test_keystore_view(hass: HomeAssistant) -> None:
    from types import SimpleNamespace

    from homeassistant.components.http.const import KEY_HASS_USER
    from homeassistant.helpers.http import KEY_HASS

    from custom_components.redsea.poseidon import const
    from custom_components.redsea.poseidon.http_view import PoseidonKeystoreView

    class _Request(dict):
        def __init__(self, user: object) -> None:
            super().__init__({KEY_HASS_USER: user} if user is not None else {})
            self.app = {KEY_HASS: hass}

    view = PoseidonKeystoreView()
    admin = SimpleNamespace(is_admin=True)
    assert view.requires_auth and view.url == const.EXPORT_VIEW_URL
    assert (await view.get(_Request(None))).status == 403  # type: ignore[arg-type]
    user = SimpleNamespace(is_admin=False)
    assert (await view.get(_Request(user))).status == 403  # type: ignore[arg-type]
    assert (await view.get(_Request(admin))).status == 404  # type: ignore[arg-type]
    poseidon = _poseidon(hass)
    poseidon.keystore.devices = {
        "aa": DeviceKeys(hwid="aa", api_key="k", api_secret=SECRET)
    }
    hass.data[const.DATA_POSEIDON] = poseidon
    try:
        response = await view.get(_Request(admin))  # type: ignore[arg-type]
    finally:
        hass.data.pop(const.DATA_POSEIDON)
    assert response.status == 200
    assert response.headers["Content-Disposition"].startswith(
        'attachment; filename="keystore-'
    )
    assert response.headers["Cache-Control"] == "no-store"
    assert json.loads(response.body)["devices"]["aa"]["api_secret"] == SECRET  # type: ignore[arg-type]
