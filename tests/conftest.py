"""Test fixtures for the Red Sea ReefBeat custom integration.

These tests are designed for `pytest-homeassistant-custom-component`.

They:
- Avoid real network by monkeypatching ReefBeatAPI.fetch_data (aiohttp)
- Feed deterministic payloads from captured cloud + local device dumps
- Exercise HA setup, device registry, and per-head device association
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_frontend_for_tests(hass):
    """Empêche les erreurs de frontend pendant les tests."""
    # On mocke add_extra_js_url pour qu'elle ne fasse rien
    with patch("homeassistant.components.frontend.add_extra_js_url"):
        # On s'assure que les clés existent pour éviter les KeyError
        # au cas où ton code ne ferait pas la vérification 'if "frontend" in...'
        hass.data["frontend_extra_module_url"] = set()
        yield


# Add the parent directory (project root) to sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# Ensure HA loads integrations from ./custom_components during tests
@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading this repo's custom_components in the HA test instance."""
    return


DOMAIN = "redsea"


def _const(name: str, default: str) -> str:
    """Read a constant from the integration if available.

    The integration is actively being refactored, so we try to avoid hard-coding
    storage keys in tests.
    """

    try:
        from custom_components.redsea import const as c  # type: ignore

        return str(getattr(c, name))
    except Exception:
        return default


CONFIG_FLOW_IP_ADDRESS = _const("CONFIG_FLOW_IP_ADDRESS", "ip_address")
CONFIG_FLOW_HW_MODEL = _const("CONFIG_FLOW_HW_MODEL", "hw_model")
CONFIG_FLOW_CLOUD_USERNAME = _const("CONFIG_FLOW_CLOUD_USERNAME", "username")
CONFIG_FLOW_CLOUD_PASSWORD = _const("CONFIG_FLOW_CLOUD_PASSWORD", "password")
CONFIG_FLOW_ADD_TYPE = _const("CONFIG_FLOW_ADD_TYPE", "add_type")
CONFIG_FLOW_CONFIG_TYPE = _const("CONFIG_FLOW_CONFIG_TYPE", "live_config_update")
CONFIG_FLOW_DISABLE_SUPPLEMENT = _const(
    "CONFIG_FLOW_DISABLE_SUPPLEMENT", "disable_supplements"
)


ADD_CLOUD_API = _const("ADD_CLOUD_API", "cloud_api")
CLOUD_SERVER_ADDR = _const("CLOUD_SERVER_ADDR", "cloud.reef-beat.com")
CLOUD_DEVICE_TYPE = _const("CLOUD_DEVICE_TYPE", "Smartphone App")


def _cloud_library_paths() -> tuple[str, str, str]:
    """Return the cloud library endpoint paths.

    Prefer integration constants when importable (keeps tests aligned with refactors).
    """

    try:
        from custom_components.redsea.const import (  # type: ignore
            LIGHTS_LIBRARY,
            SUPPLEMENTS_LIBRARY,
            WAVES_LIBRARY,
        )

        return (str(LIGHTS_LIBRARY), str(WAVES_LIBRARY), str(SUPPLEMENTS_LIBRARY))
    except Exception:
        return (
            "/reef-lights/library?include=all",
            "/reef-wave/library",
            "/reef-dosing/supplement",
        )


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def devices_dir(fixtures_dir: Path) -> Path:
    # tests/fixtures/devices contains captured endpoint payloads per device type.
    #
    # Historically this repo used a symlink to an external simulator checkout.
    # For portable tests (CI, tarballs, etc.) we keep real fixture files here.
    return fixtures_dir / "devices"


def _read_device_endpoint(devices_dir: Path, profile: str, endpoint: str) -> Any:
    """
    Load JSON (or text) for a simulated device endpoint.

    profile: "DOSE4", "ATO", "LED", "RUN", "WAVE"
    endpoint: "/device-info", "/dashboard", "/head/3/settings", "/description.xml", "/"
    """
    rel = endpoint.lstrip("/")  # "/device-info" -> "device-info"
    if rel == "":
        # root "/" maps to "<profile>/data"
        data_path = devices_dir / profile / "data"
    else:
        data_path = devices_dir / profile / rel / "data"

    if not data_path.exists():
        # endpoint not implemented in simulator dataset; mirror "not present"
        return {}

    raw = data_path.read_text(encoding="utf-8")

    # description.xml is not JSON
    if rel.endswith("description.xml"):
        return raw

    return json.loads(raw)


# Public alias for tests (keeps type checkers happy about private usage)
read_device_endpoint = _read_device_endpoint


def _read_device_info(devices_dir: Path, profile: str) -> dict[str, Any]:
    info = _read_device_endpoint(devices_dir, profile, "/device-info")
    return info if isinstance(info, dict) else {}


def _read_device_ip(devices_dir: Path, profile: str) -> str:
    """Return the device IP used for test routing.

    Prefer /wifi.ip when present; fall back to /.wifi_ip.
    """
    wifi = _read_device_endpoint(devices_dir, profile, "/wifi")
    if isinstance(wifi, dict) and isinstance(wifi.get("ip"), str):
        return str(wifi["ip"])

    root = _read_device_endpoint(devices_dir, profile, "/")
    if isinstance(root, dict) and isinstance(root.get("wifi_ip"), str):
        return str(root["wifi_ip"])

    return ""


def _profile_to_ip(devices_dir: Path) -> dict[str, str]:
    """Return a stable mapping of fixture profile -> device IP.

    Some fixtures use a placeholder like "__REEFBEAT_DEVICE_IP__". When that
    happens we assign a deterministic TEST-NET IP so each profile stays unique.
    """

    profiles = sorted(p.name for p in devices_dir.iterdir() if p.is_dir())
    out: dict[str, str] = {}

    base = 90
    for i, profile in enumerate(profiles):
        ip = _read_device_ip(devices_dir, profile)
        if not ip or ip.startswith("__"):
            ip = f"192.0.2.{base + i}"
        out[profile] = ip

    return out


def _build_ip_to_profile(devices_dir: Path) -> dict[str, str]:
    profile_to_ip = _profile_to_ip(devices_dir)
    return {ip: profile for profile, ip in profile_to_ip.items() if ip}


def _local_config_entry_from_profile(
    devices_dir: Path, profile: str
) -> MockConfigEntry:
    info = _read_device_info(devices_dir, profile)
    ip = _profile_to_ip(devices_dir).get(profile, "")

    name = info.get("name")
    hw_model = info.get("hw_model")
    hwid = info.get("hwid")

    title = str(name) if isinstance(name, str) else profile
    hw_model_str = str(hw_model) if isinstance(hw_model, str) else ""
    unique_id = str(hwid) if isinstance(hwid, str) else None

    data: dict[str, Any] = {
        CONFIG_FLOW_CONFIG_TYPE: True,
    }
    if ip:
        data[CONF_HOST] = ip
        data[CONFIG_FLOW_IP_ADDRESS] = ip
    if hw_model_str:
        data[CONFIG_FLOW_HW_MODEL] = hw_model_str

    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data=data,
        unique_id=unique_id,
    )


def _index_cloud_sources(cloud_dump: dict[str, Any]) -> dict[str, Any]:
    """Map endpoint -> payload from the captured cloud dump."""
    out: dict[str, Any] = {}
    for src in cloud_dump.get("sources", []):
        name = src.get("name")
        if isinstance(name, str):
            out[name] = src.get("data")
    return out


def _index_local_sources(probe_by_type: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map ip -> endpoint -> payload from the captured local probe dump."""
    out: dict[str, dict[str, Any]] = {}
    for _dev_type, block in probe_by_type.items():
        device = block.get("device") or {}
        ip = device.get("ip_address")
        if not isinstance(ip, str):
            continue
        hits_ok: dict[str, Any] = (block.get("hits") or {}).get("ok") or {}
        out[ip] = hits_ok
    return out


@pytest.fixture(autouse=True)
def patch_reefbeat_network(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    devices_dir: Path,
) -> None:
    from custom_components.redsea.reefbeat.api import ReefBeatAPI  # type: ignore
    from custom_components.redsea.reefbeat.cloud import ReefBeatCloudAPI  # type: ignore

    # Map host/ip -> simulator profile based on captured fixture payloads.
    ip_to_profile = _build_ip_to_profile(devices_dir)

    # Cloud payloads are served from sanitized fixtures under tests/fixtures/devices/CLOUD.
    lights_library, waves_library, supplements_library = _cloud_library_paths()
    cloud_sources: dict[str, Any] = {
        "/user": _read_device_endpoint(devices_dir, "CLOUD", "/user"),
        "/aquarium": _read_device_endpoint(devices_dir, "CLOUD", "/aquarium"),
        "/device": _read_device_endpoint(devices_dir, "CLOUD", "/device"),
        # Library endpoints may not be present in the sanitized dataset; default to empty.
        lights_library: [],
        waves_library: [],
        supplements_library: [],
    }

    async def _fake_http_get(self: ReefBeatAPI, session: Any, source: Any) -> bool:
        endpoint = None
        try:
            endpoint = source.value.get("name")
        except Exception:
            endpoint = None

        if not isinstance(endpoint, str):
            return False

        # Cloud API instances are created with secure=True
        if bool(getattr(self, "_secure", False)):
            source.value["data"] = cloud_sources.get(endpoint, {})
            return True

        # Your integration uses `self.ip` for locals
        ip = getattr(self, "ip", None)
        profile = ip_to_profile.get(ip) if isinstance(ip, str) else None
        if not profile:
            source.value["data"] = {}
            return True

        source.value["data"] = _read_device_endpoint(devices_dir, profile, endpoint)
        return True

    async def _fake_cloud_connect(self: ReefBeatCloudAPI) -> None:
        self._token = "test-token"
        self._header = {"Authorization": "Bearer test-token"}

    monkeypatch.setattr(ReefBeatAPI, "_http_get", _fake_http_get, raising=True)
    monkeypatch.setattr(ReefBeatCloudAPI, "connect", _fake_cloud_connect, raising=True)


@pytest.fixture
def cloud_config_entry() -> MockConfigEntry:
    """Config entry representing a ReefBeat cloud account."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="ReefBeat Cloud (tests)",
        data={
            # Cloud coordinator still expects ip/hw keys because it subclasses
            # the same base coordinator as local devices.
            CONFIG_FLOW_IP_ADDRESS: CLOUD_SERVER_ADDR,
            CONFIG_FLOW_HW_MODEL: CLOUD_DEVICE_TYPE,
            CONFIG_FLOW_CLOUD_USERNAME: "test@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "not-a-real-password",
            CONFIG_FLOW_CONFIG_TYPE: False,
            CONFIG_FLOW_DISABLE_SUPPLEMENT: True,
        },
        unique_id="test-cloud",
    )


@pytest.fixture
def local_dose_config_entry(devices_dir: Path) -> MockConfigEntry:
    return _local_config_entry_from_profile(devices_dir, "DOSE4")


@pytest.fixture
def local_dose2_config_entry(devices_dir: Path) -> MockConfigEntry:
    return _local_config_entry_from_profile(devices_dir, "DOSE2")


@pytest.fixture
def local_mat_config_entry(devices_dir: Path) -> MockConfigEntry:
    """Config entry for the captured ReefMat 500 device."""
    return _local_config_entry_from_profile(devices_dir, "MAT")


@pytest.fixture
def local_ato_config_entry(devices_dir: Path) -> MockConfigEntry:
    """Config entry for the captured ReefATO+ device."""
    return _local_config_entry_from_profile(devices_dir, "ATO")


@pytest.fixture
def local_run_config_entry(devices_dir: Path) -> MockConfigEntry:
    return _local_config_entry_from_profile(devices_dir, "RUN")


@pytest.fixture
def local_wave_config_entry(devices_dir: Path) -> MockConfigEntry:
    return _local_config_entry_from_profile(devices_dir, "WAVE")


@pytest.fixture
def local_led_config_entry(devices_dir: Path) -> MockConfigEntry:
    return _local_config_entry_from_profile(devices_dir, "LED")
