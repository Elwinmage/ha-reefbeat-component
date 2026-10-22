"""Constants of Poseidon mode (see README.md)."""

from __future__ import annotations

from typing import Final

# Config entry
POSEIDON_UNIQUE_ID: Final[str] = "poseidon"
POSEIDON_TITLE: Final[str] = "Poseidon"
CONF_POSEIDON: Final[str] = "poseidon"
CONF_PORT: Final[str] = "port"
CONF_HOST: Final[str] = "host"
CONF_CLOUD_ACCOUNT: Final[str] = "cloud_account"
# Add type of the integration's "add" menu
ADD_POSEIDON: Final[str] = "poseidon"

# Options flow
OPTIONS_MENU_ADD_DEVICES: Final[str] = "add_devices"
CONF_DEVICES: Final[str] = "devices"
CONF_CONFIRM: Final[str] = "confirm"

# Where hass.data keeps the running Poseidon (not hass.data[DOMAIN], whose
# values are all device coordinators)
DATA_POSEIDON: Final[str] = "redsea_poseidon"

# Red Sea broker
UPSTREAM_HOST: Final[str] = "mqtt.reef-beat.com"
UPSTREAM_PORT: Final[int] = 1883
NORMAL_MQTT_URL: Final[str] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"

# Listening port: the first free one from here is proposed. 1883 and 8883
# are the standard MQTT ports, usually taken by a local broker.
DEFAULT_PORT: Final[int] = 1884
PORT_SCAN_LAST: Final[int] = 1899
RESERVED_PORTS: Final[frozenset[int]] = frozenset({1883, 8883})

# Keystore (HA Store, kept when the entry is removed)
STORE_KEY: Final[str] = "redsea.poseidon"
STORE_VERSION: Final[int] = 1

# Files under the Home Assistant config directory
FILES_DIR: Final[str] = "redsea/poseidon"

# Relay
CONNECT_TIMEOUT_S: Final[float] = 10.0
UPSTREAM_TIMEOUT_S: Final[float] = 10.0
READ_CHUNK: Final[int] = 8192

# How often the /cloud of the managed devices is read again
CLOUD_REFRESH_S: Final[int] = 60
# Pause before reading /cloud again after a switch
SWITCH_SETTLE_S: Final[float] = 2.0

# Key capture
CLOUD_SETTLE_S: Final[float] = 1.0
DEVICE_SETTLE_S: Final[float] = 4.0
RESTORE_RETRIES: Final[int] = 3
RESTORE_INTERVAL_S: Final[float] = 5.0
STEP_WAIT_S: Final[float] = 2.0

# Signal sent when the state of the managed devices may have changed
SIGNAL_POSEIDON_UPDATE: Final[str] = "redsea_poseidon_update"

# Repair issue: the listening port is taken
ISSUE_PORT_IN_USE: Final[str] = "poseidon_port_in_use"

# Model prefix -> cloud device type (the namespaces the cloud API uses)
MODEL_TO_TYPE: Final[dict[str, str]] = {
    "RSWAVE": "reef-wave",
    "RSRUN": "reef-run",
    "RSLED": "reef-lights",
    "RSDOSE": "reef-dosing",
    "RSMAT": "reef-mat",
    "RSATO": "reef-ato",
    "RSSKIM": "reef-skimmer",
    "RSCONTROL": "reef-control",
    "RSPOWER": "reef-power",
}


def type_from_model(model: str) -> str:
    """Cloud device type of a model (RSWAVE45 -> reef-wave), "" if unknown."""
    upper = model.upper()
    for prefix, device_type in sorted(
        MODEL_TO_TYPE.items(), key=lambda kv: -len(kv[0])
    ):
        if upper.startswith(prefix):
            return device_type
    return ""


# Options of the Poseidon entry
OPTIONS_MENU_SETTINGS: Final[str] = "settings_poseidon"
CONF_DEBUG: Final[str] = "debug"
CONF_SILENT_MINUTES: Final[str] = "silent_minutes"
CONF_WATCHDOG_KEY: Final[str] = "watchdog_key"
DEFAULT_SILENT_MINUTES: Final[int] = 10

# Repair issue: a device in Poseidon mode exchanges nothing anymore
ISSUE_DEVICE_SILENT: Final[str] = "poseidon_device_silent"

# Keystore export / import (CLI format)
OPTIONS_MENU_EXPORT: Final[str] = "export_keystore"
OPTIONS_MENU_IMPORT: Final[str] = "import_keystore"
CONF_FILE: Final[str] = "file"
# Download of the keystore: generated on request, behind a signed link
EXPORT_VIEW_URL: Final[str] = "/api/redsea/poseidon/keystore"
EXPORT_VIEW_NAME: Final[str] = "api:redsea:poseidon_keystore"
EXPORT_LINK_MINUTES: Final[int] = 5
# Rescue script: switches devices back without Home Assistant, keys embedded
OPTIONS_MENU_RESCUE: Final[str] = "rescue_script"
RESCUE_VIEW_URL: Final[str] = "/api/redsea/poseidon/rescue"
RESCUE_VIEW_NAME: Final[str] = "api:redsea:poseidon_rescue"
RESCUE_FILE: Final[str] = "poseidon_rescue.py"
SERVICE_EXPORT: Final[str] = "poseidon_export"

# Strategy of a device in Poseidon mode (see strategy.py). A default in the
# options, and an override per device (the select next to its switch)
CONF_STRATEGY: Final[str] = "strategy"
CONF_DEVICE_STRATEGIES: Final[str] = "device_strategies"
CONF_REDUCED_MINUTES: Final[str] = "reduced_minutes"
STRATEGY_SPY: Final[str] = "spy"
STRATEGY_SHADOW: Final[str] = "shadow"
STRATEGY_POSEIDON: Final[str] = "poseidon"
STRATEGIES: Final[list[str]] = [STRATEGY_SPY, STRATEGY_SHADOW, STRATEGY_POSEIDON]
DEFAULT_STRATEGY: Final[str] = STRATEGY_SPY
# Values of earlier versions of the option
LEGACY_STRATEGIES: Final[dict[str, str]] = {
    "normal": STRATEGY_SPY,
    "reduced": STRATEGY_POSEIDON,
}
DEFAULT_REDUCED_MINUTES: Final[int] = 10
# Poseidon strategy: a pushed state triggers a refresh, at most this often
# per device
PUSH_REFRESH_MIN_S: Final[float] = 5.0
PUSH_REFRESH_WAIT_S: Final[int] = 1
SPY_FILE: Final[str] = "spy.jsonl"
SHADOW_FILE: Final[str] = "shadow.jsonl"
