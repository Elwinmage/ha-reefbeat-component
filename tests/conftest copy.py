"""Test fixtures for the Red Sea ReefBeat custom integration.

These tests are designed for `pytest-homeassistant-custom-component`.

They:
- Avoid real network by monkeypatching ReefBeatAPI.fetch_data (aiohttp)
- Feed deterministic payloads from captured cloud + local device dumps
- Exercise HA setup, device registry, and per-head device association
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest


# Ensure HA loads integrations from ./custom_components during tests
@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading this repo's custom_components in the HA test instance."""
    return


from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

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


ADD_CLOUD_API = _const("ADD_CLOUD_API", "cloud_api")
CLOUD_SERVER_ADDR = _const("CLOUD_SERVER_ADDR", "cloud.reef-beat.com")
CLOUD_DEVICE_TYPE = _const("CLOUD_DEVICE_TYPE", "Smartphone App")


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def reefbeat_cloud_dump(fixtures_dir: Path) -> dict[str, Any]:
    return json.loads((fixtures_dir / ".private/reefbeat_cloud_dump.json").read_text())


@pytest.fixture(scope="session")
def reefbeat_probe_by_type(fixtures_dir: Path) -> dict[str, Any]:
    return json.loads(
        (fixtures_dir / ".private/reefbeat_probe_by_type.json").read_text()
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
    reefbeat_cloud_dump: dict[str, Any],
    reefbeat_probe_by_type: dict[str, Any],
) -> None:
    """Patch the integration's API layer so tests never touch the network."""

    # Import here so test collection doesn't require HA to import the integration.
    from custom_components.redsea.reefbeat.api import ReefBeatAPI  # type: ignore
    from custom_components.redsea.reefbeat.cloud import ReefBeatCloudAPI  # type: ignore

    cloud_sources = _index_cloud_sources(reefbeat_cloud_dump)
    local_sources_by_ip = _index_local_sources(reefbeat_probe_by_type)

    async def _fake_http_get(self: ReefBeatAPI, session: Any, source: Any) -> bool:
        """Fake the low-level GET used by `fetch_*` and `get_initial_data`.

        This is the most reliable patch point because the integration uses
        `_call_url()` -> `_http_get()` for *all* cached sources.
        """
        endpoint = None
        try:
            endpoint = source.value.get("name")
        except Exception:
            endpoint = None

        if not isinstance(endpoint, str):
            return False

        # Cloud
        if getattr(self, "_secure", False):
            if endpoint in cloud_sources:
                source.value["data"] = cloud_sources[endpoint]
            else:
                source.value["data"] = {}
            return True

        # Local
        ip = getattr(self, "ip", None)
        if isinstance(ip, str) and ip in local_sources_by_ip:
            payloads = local_sources_by_ip[ip]
            source.value["data"] = payloads.get(endpoint, {})
            return True

        # Unknown device/ip
        source.value["data"] = {}
        return True

    async def _fake_cloud_connect(self: ReefBeatCloudAPI) -> None:
        """Avoid calling real cloud auth endpoints."""
        # Cloud API expects a token + headers; any non-empty value works for our tests.
        self._token = "test-token"
        self._header = {"Authorization": "Bearer test-token"}
        self._auth_date = time.time()

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
        },
        unique_id="test-cloud",
    )


@pytest.fixture
def local_dose_config_entry() -> MockConfigEntry:
    """Config entry for the captured ReefDose4 device."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="RSDOSE4-217211586",
        data={
            CONF_HOST: "10.0.30.94",
            CONFIG_FLOW_IP_ADDRESS: "10.0.30.94",
            CONFIG_FLOW_HW_MODEL: "RSDOSE4",
            # The integration reads this to decide which sources to fetch.
            "live_config_update": True,
        },
        unique_id="1c9dc262f20c",
    )


@pytest.fixture
def local_mat_config_entry() -> MockConfigEntry:
    """Config entry for the captured ReefMat 500 device."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="RSMAT-3632934213",
        data={
            CONF_HOST: "10.0.30.95",
            CONFIG_FLOW_IP_ADDRESS: "10.0.30.95",
            # NOTE: current integration uses HW_MAT_IDS=("RSMAT",) in the
            # coordinator factory. Using "RSMAT" keeps tests passing while
            # refactor work continues.
            CONFIG_FLOW_HW_MODEL: "RSMAT",
            # Preserve the real model as extra data for later assertions.
            "model": "RSMAT500",
            "live_config_update": True,
        },
        unique_id="345f452d8ad8",
    )


@pytest.fixture
def local_ato_config_entry() -> MockConfigEntry:
    """Config entry for the captured ReefATO+ device."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="RSATO+2487379135",
        data={
            CONF_HOST: "10.0.30.96",
            CONFIG_FLOW_IP_ADDRESS: "10.0.30.96",
            CONFIG_FLOW_HW_MODEL: "RSATO+",
            "live_config_update": True,
        },
        unique_id="8813bf644294",
    )
