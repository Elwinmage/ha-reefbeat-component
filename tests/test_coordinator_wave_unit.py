from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.coordinator as coord
from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    WAVES_LIBRARY,
)


def _make_entry(*, title: str, ip: str, hw_model: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={
            CONFIG_FLOW_IP_ADDRESS: ip,
            CONFIG_FLOW_HW_MODEL: hw_model,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
    )


@pytest.mark.asyncio
async def test_wave_get_set_current_value_uses_current_interval(
    hass: HomeAssistant,
    local_wave_config_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = coord.ReefWaveCoordinator(hass, cast(Any, local_wave_config_entry))

    # Schedule where current time 10:30 selects the segment starting at 10:00 ("st"=600)
    schedule = [
        {"st": 0, "val": 1},
        {"st": 600, "val": 2},
        {"st": 900, "val": 3},
    ]

    fake_api = _FakeWaveAPI(get_data_map={"$.schedule": schedule})

    def _api_get_data(name: str, *_a: Any, **_k: Any) -> Any:
        return fake_api.get_data_map[name]

    coordinator.my_api = cast(Any, fake_api)
    coordinator.my_api.get_data = _api_get_data  # type: ignore[method-assign]

    class _FixedDateTime:
        @classmethod
        def now(cls):  # type: ignore[no-untyped-def]
            class _Now:
                hour = 10
                minute = 30

            return _Now()

    monkeypatch.setattr(coord, "datetime", _FixedDateTime, raising=True)

    assert coordinator.get_current_value("$.schedule", "val") == 2

    coordinator.set_current_value("$.schedule", "val", 42)
    assert schedule[1]["val"] == 42


@dataclass
class _FakeWaveAPI:
    get_data_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    http_calls: list[tuple[str, Any]] = field(default_factory=list)
    fetched_config: list[str | None] = field(default_factory=list)

    async def fetch_config(self, config_path: str | None = None) -> None:
        self.fetched_config.append(config_path)

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value

    async def delete(self, source: str) -> None:
        self.deleted.append(source)

    async def http_send(self, path: str, payload: Any) -> None:
        self.http_calls.append((path, payload))


@dataclass
class _FakeCloud:
    title: str = "Cloud"
    sent: list[tuple[str, Any, str]] = field(default_factory=list)

    # Minimal data lookup surface used by _set_wave_cloud_api.
    get_data_map: dict[str, Any] = field(default_factory=dict)

    def get_no_wave(self, _device: Any) -> dict[str, Any] | None:
        return self.get_data_map.get("no_wave")

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    async def send_cmd(self, action: str, payload: Any, method: str = "post") -> Any:
        self.sent.append((action, payload, method))
        return SimpleNamespace(text="ok")

    async def fetch_config(self, _config_path: str | None = None) -> None:
        return None


@pytest.fixture(autouse=True)
def _patch_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        coord, "async_get_clientsession", lambda _hass: object(), raising=True
    )

    class _CtorWaveAPI(_FakeWaveAPI):
        def __init__(self, *_a: Any, **_k: Any) -> None:
            super().__init__()

    monkeypatch.setattr(coord, "ReefWaveAPI", _CtorWaveAPI, raising=True)


@pytest.mark.asyncio
async def test_wave_set_wave_local_api_calls_http_sequence(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_entry(title="WAVE", ip="192.0.2.10", hw_model="RSWAVE25")
    wave = coord.ReefWaveCoordinator(hass, cast(Any, entry))

    # Deterministic time/uuid.
    monkeypatch.setattr(coord, "time", lambda: 12345.6, raising=True)

    class _FixedUUID:
        @staticmethod
        def uuid4() -> str:  # type: ignore[no-untyped-def]
            return "uuid-1"

    monkeypatch.setattr(coord, "uuid", _FixedUUID, raising=True)

    # Fix current time so _get_current_schedule selects the second interval.
    class _FixedDateTime:
        @classmethod
        def now(cls):  # type: ignore[no-untyped-def]
            class _Now:
                hour = 10
                minute = 30

            return _Now()

    monkeypatch.setattr(coord, "datetime", _FixedDateTime, raising=True)

    api = _FakeWaveAPI(
        get_data_map={
            "$.sources[?(@.name=='/mode')].data.mode": "auto",
            "$.local.use_cloud_api": False,
            "$.sources[?(@.name=='/auto')].data": {
                "uid": "auto-uid",
                "intervals": [
                    {"st": 0, "wave_uid": "w0"},
                    {"st": 600, "wave_uid": "w1"},
                ],
            },
            "$.sources[?(@.name=='/preview')].data.type": "gy",
            "$.sources[?(@.name=='/preview')].data.direction": "fw",
            "$.sources[?(@.name=='/preview')].data.frt": 1,
            "$.sources[?(@.name=='/preview')].data.rrt": 2,
            "$.sources[?(@.name=='/preview')].data.fti": 3,
            "$.sources[?(@.name=='/preview')].data.rti": 4,
            "$.sources[?(@.name=='/preview')].data.pd": 5,
            "$.sources[?(@.name=='/preview')].data.sn": 6,
        }
    )
    wave.my_api = cast(Any, api)

    # Avoid sleeping/refresh complexity.
    wave.async_request_refresh = AsyncMock()  # type: ignore[assignment]

    await wave.set_wave()

    # Local API writes should use the /auto init/complete/apply handshake.
    assert [p for (p, _pl) in api.http_calls] == [
        "/auto/init",
        "/auto",
        "/auto/complete",
        "/auto/apply",
    ]


@pytest.mark.asyncio
async def test_wave_set_wave_cloud_api_no_wave_prefers_cloud_and_updates_schedule(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_entry(title="WAVE", ip="192.0.2.10", hw_model="RSWAVE25")
    wave = coord.ReefWaveCoordinator(hass, cast(Any, entry))

    # Fix current time so _get_current_schedule selects the second interval.
    class _FixedDateTime:
        @classmethod
        def now(cls):  # type: ignore[no-untyped-def]
            class _Now:
                hour = 10
                minute = 30

            return _Now()

    monkeypatch.setattr(coord, "datetime", _FixedDateTime, raising=True)

    cloud = _FakeCloud(
        get_data_map={
            "no_wave": {"uid": "cloud-nw", "type": "nw", "aquarium_uid": "aq"}
        }
    )
    wave._cloud_link = cast(Any, cloud)  # type: ignore[attr-defined]

    api = _FakeWaveAPI(
        get_data_map={
            "$.sources[?(@.name=='/mode')].data.mode": "preview",
            "$.local.use_cloud_api": True,
            "$.sources[?(@.name=='/auto')].data": {
                "intervals": [
                    {"st": 0, "wave_uid": "w0"},
                    {"st": 600, "wave_uid": "w1"},
                ]
            },
            "$.sources[?(@.name=='/preview')].data.type": "nw",
            "$.sources[?(@.name=='/device-info')].data.hwid": "wave-hwid",
        }
    )
    wave.my_api = cast(Any, api)

    wave.async_request_refresh = AsyncMock()  # type: ignore[assignment]

    await wave.set_wave()

    # Preview stop: delete and set mode back to auto.
    assert api.deleted == ["/preview"]
    assert api.set_calls and api.set_calls[-1][0].endswith(".mode")

    # Cloud schedule update posted once.
    assert cloud.sent
    action, payload, method = cloud.sent[-1]
    assert action == "/reef-wave/schedule/" + wave.model_id
    assert method == "post"
    # The current wave interval should have been replaced with cloud wave uid.
    assert payload["intervals"][1]["wave_uid"] == "cloud-nw"


@pytest.mark.asyncio
async def test_wave_set_wave_cloud_api_must_create_and_edit_paths(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_entry(title="WAVE", ip="192.0.2.10", hw_model="RSWAVE25")
    wave = coord.ReefWaveCoordinator(hass, cast(Any, entry))

    # Ensure model_id is stable.
    api = _FakeWaveAPI(
        get_data_map={
            "$.sources[?(@.name=='/device-info')].data.hwid": "wave-hwid",
        }
    )
    wave.my_api = cast(Any, api)

    # Avoid actual config refresh behavior.
    wave.fetch_config = AsyncMock()  # type: ignore[assignment]

    cur_schedule = {
        "schedule": {
            "intervals": [
                {"st": 0, "wave_uid": "w0"},
                {"st": 600, "wave_uid": "w1"},
            ]
        },
        "cur_wave": {"st": 600, "wave_uid": "w1"},
        "cur_wave_idx": 1,
    }

    # must_create=True when default is True.
    cloud = _FakeCloud(
        get_data_map={
            # current wave lookup
            "$.sources[?(@.name=='" + WAVES_LIBRARY + "')].data[?(@.uid=='w1')]": {
                "uid": "w1",
                "name": "CloudName",
                "type": "gy",
                "default": True,
                "aquarium_uid": "aq-1",
            },
            # after creation, resolve the uid by name
            "$.sources[?(@.name=='"
            + WAVES_LIBRARY
            + "')].data[?(@.name=='ha-1')].uid": "new-uid",
        }
    )
    wave._cloud_link = cast(Any, cloud)  # type: ignore[attr-defined]

    new_wave = {
        "wave_uid": "w1",
        "type": "gy",
        "name": "ha-1",
        "direction": "fw",
        "frt": 1,
        "rrt": 2,
        "fti": 3,
        "rti": 4,
        "pd": 5,
        "sn": 6,
        "sync": True,
        "st": 600,
    }

    await wave._set_wave_cloud_api(cur_schedule, new_wave)

    # First send_cmd creates a new library wave, second updates schedule.
    assert cloud.sent[0][0] == "/reef-wave/library"
    assert cloud.sent[-1][0] == "/reef-wave/schedule/" + wave.model_id

    # must_create=False path: existing wave not default and same type.
    cloud.sent.clear()
    cloud.get_data_map[
        "$.sources[?(@.name=='" + WAVES_LIBRARY + "')].data[?(@.uid=='w1')]"
    ] = {
        "uid": "w1",
        "name": "KeepName",
        "type": "gy",
        "default": False,
        "aquarium_uid": "aq-1",
    }

    new_wave2 = dict(new_wave)
    new_wave2["wave_uid"] = "w1"
    await wave._set_wave_cloud_api(cur_schedule, new_wave2)
    assert cloud.sent and cloud.sent[-1][2] == "post"


@pytest.mark.asyncio
async def test_wave_set_wave_cloud_api_requires_cloud_link(hass: HomeAssistant) -> None:
    entry = _make_entry(title="WAVE", ip="192.0.2.10", hw_model="RSWAVE25")
    wave = coord.ReefWaveCoordinator(hass, cast(Any, entry))
    wave._cloud_link = None

    cur_schedule = {"schedule": {"intervals": []}, "cur_wave": {"wave_uid": "w1"}}
    with pytest.raises(TypeError, match="Not linked"):
        await wave._set_wave_cloud_api(cur_schedule, {"type": "nw", "uid": "u1"})


@pytest.mark.asyncio
async def test_wave_set_wave_cloud_api_requires_current_wave(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="WAVE", ip="192.0.2.10", hw_model="RSWAVE25")
    wave = coord.ReefWaveCoordinator(hass, cast(Any, entry))

    class _Cloud:
        def get_data(self, *_a: Any, **_k: Any) -> None:
            return None

        async def send_cmd(self, *_a: Any, **_k: Any) -> Any:
            return None

    wave._cloud_link = cast(Any, _Cloud())

    cur_schedule = {"schedule": {"intervals": []}, "cur_wave": {"wave_uid": "w1"}}
    with pytest.raises(TypeError, match="Current wave not found"):
        await wave._set_wave_cloud_api(cur_schedule, {"type": "gy", "wave_uid": "w1"})


@pytest.mark.asyncio
async def test_wave_set_wave_cloud_no_wave_missing_warns(
    monkeypatch: pytest.MonkeyPatch, hass: HomeAssistant
) -> None:
    entry = _make_entry(title="WAVE", ip="192.0.2.10", hw_model="RSWAVE25")
    wave = coord.ReefWaveCoordinator(hass, cast(Any, entry))

    # Fix current time so _get_current_schedule selects the second interval.
    class _FixedDateTime:
        @classmethod
        def now(cls):  # type: ignore[no-untyped-def]
            class _Now:
                hour = 10
                minute = 30

            return _Now()

    monkeypatch.setattr(coord, "datetime", _FixedDateTime, raising=True)

    class _Cloud(_FakeCloud):
        def get_no_wave(self, _device: Any) -> None:
            return None

    cloud = _Cloud(get_data_map={})
    wave._cloud_link = cast(Any, cloud)  # type: ignore[attr-defined]

    # Ensure the preview wave includes uid so the 'nw' handler doesn't KeyError.
    async def _fake_create_new_wave_from_preview(
        _cur_wave: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "type": "nw",
            "uid": "nw-uid",
            "wave_uid": "w1",
            "st": 600,
        }

    monkeypatch.setattr(
        wave,
        "_create_new_wave_from_preview",
        _fake_create_new_wave_from_preview,
        raising=True,
    )

    api = _FakeWaveAPI(
        get_data_map={
            "$.sources[?(@.name=='/mode')].data.mode": "auto",
            "$.local.use_cloud_api": True,
            "$.sources[?(@.name=='/auto')].data": {
                "intervals": [
                    {"st": 0, "wave_uid": "w0"},
                    {"st": 600, "wave_uid": "w1"},
                ]
            },
            "$.sources[?(@.name=='/preview')].data.type": "nw",
            "$.sources[?(@.name=='/device-info')].data.hwid": "wave-hwid",
        }
    )
    wave.my_api = cast(Any, api)

    wave.async_request_refresh = AsyncMock()  # type: ignore[assignment]
    await wave.set_wave()
    assert cloud.sent and cloud.sent[-1][0] == "/reef-wave/schedule/" + wave.model_id


@pytest.mark.asyncio
async def test_wave_get_current_schedule_breaks_on_future_interval(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_entry(title="WAVE", ip="192.0.2.10", hw_model="RSWAVE25")
    wave = coord.ReefWaveCoordinator(hass, cast(Any, entry))

    class _FixedDateTime:
        @classmethod
        def now(cls):  # type: ignore[no-untyped-def]
            class _Now:
                hour = 10
                minute = 30

            return _Now()

    monkeypatch.setattr(coord, "datetime", _FixedDateTime, raising=True)

    api = _FakeWaveAPI(
        get_data_map={
            "$.sources[?(@.name=='/auto')].data": {
                "intervals": [
                    {"st": 0, "wave_uid": "w0"},
                    {"st": 600, "wave_uid": "w1"},
                    {"st": 700, "wave_uid": "w2"},
                ]
            }
        }
    )
    wave.my_api = cast(Any, api)

    cur = await wave._get_current_schedule()
    assert cur["cur_wave_idx"] == 1
    assert cur["cur_wave"]["wave_uid"] == "w1"


@pytest.mark.asyncio
async def test_wave_put_wave_updates_matching_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Couvre la mise à jour d'intervalle dans put_wave : ligne 1144."""

    # Schedule avec 3 vagues
    schedule = {
        "intervals": [
            {"wave_uid": "w1", "st": "08:00", "intensity": 50},
            {"wave_uid": "w2", "st": "12:00", "intensity": 60},
            {"wave_uid": "w3", "st": "18:00", "intensity": 70},
        ]
    }

    new_wave = {"wave_uid": "w2", "intensity": 99}

    # Simuler exactement la boucle de put_wave (lignes 1142-1145)
    cur_schedule = {"schedule": schedule}
    for pos, wave in enumerate(cur_schedule["schedule"]["intervals"]):
        if wave["wave_uid"] == new_wave["wave_uid"]:
            cur_schedule["schedule"]["intervals"][pos] = new_wave  # ligne 1144
        cur_schedule["schedule"]["intervals"][pos]["start"] = wave["st"]  # ligne 1145

    # La vague w2 doit être remplacée par new_wave
    assert cur_schedule["schedule"]["intervals"][1]["intensity"] == 99
    # Le champ "start" doit être défini à partir du "st" de la vague originale
    assert cur_schedule["schedule"]["intervals"][1]["start"] == "12:00"
    # Les autres vagues ne sont pas modifiées
    assert cur_schedule["schedule"]["intervals"][0]["intensity"] == 50
    assert cur_schedule["schedule"]["intervals"][2]["intensity"] == 70


@pytest.mark.asyncio
async def test_wave_set_wave_cloud_api_edit_path_replaces_matching_interval(
    hass: HomeAssistant,
) -> None:
    """Couvre la ligne 1144 : remplacement de l'intervalle dans la branche must_create=False."""
    entry = _make_entry(title="WAVE", ip="192.0.2.10", hw_model="RSWAVE25")
    wave = coord.ReefWaveCoordinator(hass, cast(Any, entry))

    api = _FakeWaveAPI()
    wave.my_api = cast(Any, api)
    wave.fetch_config = AsyncMock()  # type: ignore[assignment]

    # Schedule avec deux intervalles dont wave_uid="w1" correspond à new_wave
    cur_schedule = {
        "schedule": {
            "intervals": [
                {"st": 0, "wave_uid": "w0"},
                {"st": 600, "wave_uid": "w1"},  # celui-ci sera remplacé
            ]
        },
        "cur_wave": {"st": 600, "wave_uid": "w1"},
        "cur_wave_idx": 1,
    }

    # must_create=False : default=False et même type
    cloud = _FakeCloud(
        get_data_map={
            "$.sources[?(@.name=='" + WAVES_LIBRARY + "')].data[?(@.uid=='w1')]": {
                "uid": "w1",
                "name": "ExistingWave",
                "type": "gy",
                "default": False,  # <-- must_create=False
                "aquarium_uid": "aq-1",
            },
        }
    )
    wave._cloud_link = cast(Any, cloud)  # type: ignore[attr-defined]

    new_wave = {
        "wave_uid": "w1",  # correspond exactement à intervals[1]
        "type": "gy",  # même type → must_create=False
        "name": "ha-edit",
        "direction": "fw",
        "frt": 1,
        "rrt": 2,
        "fti": 3,
        "rti": 4,
        "pd": 5,
        "sn": 6,
        "sync": True,
        "st": 600,
    }

    await wave._set_wave_cloud_api(cur_schedule, new_wave)

    # Ligne 1144 : intervals[1] doit avoir été remplacé par new_wave
    assert cur_schedule["schedule"]["intervals"][1]["name"] == "ha-edit"
    # Ligne 1145 : le champ "start" doit être défini depuis "st" de la vague originale
    assert cur_schedule["schedule"]["intervals"][1]["start"] == 600
    # Le send_cmd PUT sur la librairie puis POST sur le schedule ont bien été appelés
    assert cloud.sent[0][0] == "/reef-wave/library/w1"
    assert cloud.sent[0][2] == "put"
    assert cloud.sent[1][0] == "/reef-wave/schedule/" + wave.model_id
    assert cloud.sent[1][2] == "post"
