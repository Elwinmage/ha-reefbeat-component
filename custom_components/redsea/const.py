"""Constants for the Red Sea ReefBeat integration.

This module contains:
- Integration identifiers and config keys
- Hardware model identifiers
- Default scan intervals / timeouts
- JSONPath strings used to read device data
- Static lookup tables used by platforms (LED conversions, wave types, etc.)
"""

from __future__ import annotations

from typing import Final, TypedDict

# -----------------------------------------------------------------------------
# Platforms
# -----------------------------------------------------------------------------

try:
    from homeassistant.const import Platform

    PLATFORMS: Final[list[Platform]] = [
        Platform.LIGHT,
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.SWITCH,
        Platform.NUMBER,
        Platform.BUTTON,
        Platform.SELECT,
        Platform.TIME,
        Platform.UPDATE,
        Platform.TEXT,
    ]
except Exception:  # pragma: no cover
    # Allow importing this module outside of Home Assistant.
    PLATFORMS = []  # type: ignore[assignment]

# -----------------------------------------------------------------------------
# Integration / config keys
# -----------------------------------------------------------------------------

DOMAIN: Final[str] = "redsea"

DEVICE_MANUFACTURER: Final[str] = "Red Sea"
CONF_FLOW_PLATFORM: Final[str] = "platform"
MODEL_NAME: Final[str] = "hw_model"
MODEL_ID: Final[str] = "hwid"
HW_VERSION: Final[str] = "hw_revision"
SW_VERSION: Final[str] = "version"

CLOUD_SERVER_ADDR: Final[str] = "cloud.reef-beat.com"

CONFIG_FLOW_IP_ADDRESS: Final[str] = "ip_address"

CONFIG_FLOW_ADD_TYPE: Final[str] = "add_type"
ADD_CLOUD_API: Final[str] = "cloud_api"
ADD_LOCAL_DETECT: Final[str] = "local_detect"
ADD_MANUAL_MODE: Final[str] = "manual_mode"
VIRTUAL_LED: Final[str] = "virtual_led"

ADD_TYPES: Final[tuple[str, ...]] = (
    ADD_CLOUD_API,
    ADD_LOCAL_DETECT,
    ADD_MANUAL_MODE,
    VIRTUAL_LED,
)

# CLOUD
CONFIG_FLOW_CLOUD_USERNAME: Final[str] = "username"
CONFIG_FLOW_CLOUD_PASSWORD: Final[str] = "password"
CLOUD_SCAN_INTERVAL: Final[int] = 600
CLOUD_DEVICE_TYPE: Final[str] = "Smartphone App"
CLOUD_AUTH_TIMEOUT: Final[int] = 2700  # seconds => 45m

CONFIG_FLOW_CLOUD_ACCOUNT: Final[str] = "cloud_account"
CONFIG_FLOW_HW_MODEL: Final[str] = "hw_model"
CONFIG_FLOW_SCAN_INTERVAL: Final[str] = "scan_interval"
CONFIG_FLOW_INTENSITY_COMPENSATION: Final[str] = "intensity_compensation"
CONFIG_FLOW_CONFIG_TYPE: Final[str] = "live_config_update"

SCAN_INTERVAL: Final[int] = 120  # seconds
DO_NOT_REFRESH_TIME: Final[int] = 2  # seconds

DEFAULT_TIMEOUT: Final[int] = 20

HTTP_MAX_RETRY: Final[int] = 5
HTTP_DELAY_BETWEEN_RETRY: Final[int] = 2

# -----------------------------------------------------------------------------
# Hardware model identifiers
# -----------------------------------------------------------------------------

HW_G1_LED_IDS: Final[tuple[str, ...]] = ("RSLED50", "RSLED90", "RSLED160")
HW_G2_LED_IDS: Final[tuple[str, ...]] = ("RSLED60", "RSLED115", "RSLED170")

HW_LED_IDS: Final[tuple[str, ...]] = HW_G1_LED_IDS + HW_G2_LED_IDS

HW_DOSE_IDS: Final[tuple[str, ...]] = ("RSDOSE2", "RSDOSE4")
HW_MAT_IDS: Final[tuple[str, ...]] = ("RSMAT",)
HW_MAT_MODEL: Final[tuple[str, ...]] = ("RSMAT250", "RSMAT500", "RSMAT1200")
HW_ATO_IDS: Final[tuple[str, ...]] = ("RSATO+",)
HW_RUN_IDS: Final[tuple[str, ...]] = ("RSRUN",)
HW_WAVE_IDS: Final[tuple[str, ...]] = ("RSWAVE25", "RSWAVE45")

HW_DEVICES_IDS: Final[tuple[str, ...]] = (
    HW_LED_IDS + HW_DOSE_IDS + HW_MAT_IDS + HW_RUN_IDS + HW_ATO_IDS + HW_WAVE_IDS
)

# -----------------------------------------------------------------------------
# Common JSONPath names
# -----------------------------------------------------------------------------

JsonPath = str

COMMON_ON_OFF_SWITCH: Final[JsonPath] = "$.sources[?(@.name=='/mode')].data.mode"
COMMON_CLOUD_CONNECTION: Final[JsonPath] = "$.sources[?(@.name=='/cloud')].data.enabled"
COMMON_MAINTENANCE_SWITCH: Final[JsonPath] = "$.sources[?(@.name=='/mode')].data.mode"

# -----------------------------------------------------------------------------
# REEFLED
# -----------------------------------------------------------------------------

LED_SCAN_INTERVAL: Final[int] = 120  # seconds

LED_WHITE_INTERNAL_NAME: Final[JsonPath] = "$.sources[?(@.name=='/manual')].data.white"
LED_BLUE_INTERNAL_NAME: Final[JsonPath] = "$.sources[?(@.name=='/manual')].data.blue"
LED_MOON_INTERNAL_NAME: Final[JsonPath] = "$.sources[?(@.name=='/manual')].data.moon"
LED_INTENSITY_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/manual')].data.intensity"
)
LED_KELVIN_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/manual')].data.kelvin"
)

LED_ACCLIMATION_ENABLED_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/acclimation')].data.enabled"
)
LED_MOONPHASE_ENABLED_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/moonphase')].data.enabled"
)

LED_MOON_DAY_INTERNAL_NAME: Final[JsonPath] = "$.local.moonphase.moon_day"
LED_ACCLIMATION_DURATION_INTERNAL_NAME: Final[JsonPath] = "$.local.acclimation.duration"
LED_ACCLIMATION_INTENSITY_INTERNAL_NAME: Final[JsonPath] = (
    "$.local.acclimation.start_intensity_factor"
)

LED_MANUAL_DURATION_INTERNAL_NAME: Final[JsonPath] = "$.local.manual_duration"

DAILY_PROG_INTERNAL_NAME: Final[JsonPath] = "$.local.daily_prog"

LED_CONVERSION_COEF: Final[float] = 100 / 255


class LedConv(TypedDict):
    name: str
    kelvin: list[int]
    white_blue: list[int]


LEDS_CONV: Final[list[LedConv]] = [
    {
        "name": "RSLED160",
        "kelvin": [9000, 12000, 15000, 20000, 23000],
        "white_blue": [200, 125, 100, 50, 10],
    },
    {
        "name": "RSLED90",
        "kelvin": [9000, 12000, 15000, 20000, 23000],
        "white_blue": [200, 134, 100, 50, 10],
    },
    {
        "name": "RSLED50",
        "kelvin": [9000, 12000, 15000, 20000, 23000],
        "white_blue": [200, 100, 50, 25, 5],
    },
    {"name": "RSLED60", "kelvin": [], "white_blue": []},
    {"name": "RSLED115", "kelvin": [], "white_blue": []},
    {"name": "RSLED170", "kelvin": [], "white_blue": []},
]


class LedIntensityComp(TypedDict):
    name: str
    intensity: list[int]
    white_blue: list[int]


LEDS_INTENSITY_COMPENSATION: Final[list[LedIntensityComp]] = [
    {
        "name": "RSLED160",
        "intensity": [10320, 14300, 17240, 20575, 23100, 22260, 20190, 18070, 13370],
        "white_blue": [200, 170, 150, 125, 100, 75, 50, 30, 0],
    }
]

LED_MODE_INTERNAL_NAME: Final[JsonPath] = "$.sources[?(@.name=='/mode')].data.mode"
LED_MODES: Final[tuple[str, ...]] = ("auto", "timer", "manual")

EVENT_KELVIN_LIGHT_UPDATED: Final[str] = "Kelvin_light_updated"
EVENT_WB_LIGHT_UPDATED: Final[str] = "Kelvin_wb_updated"

# -----------------------------------------------------------------------------
# Virtual LED
# -----------------------------------------------------------------------------

VIRTUAL_LED_MAX_WAITING_TIME: Final[int] = 15
LINKED_LED: Final[str] = "linked"
VIRTUAL_LED_SCAN_INTERVAL: Final[int] = 10  # seconds

# -----------------------------------------------------------------------------
# REEFMAT
# -----------------------------------------------------------------------------

MAT_SCAN_INTERVAL: Final[int] = 300  # seconds
MAT_MIN_ROLL_DIAMETER: Final[float] = 4.0
# NOTE: keeping original constant name for compatibility (typo is in original name).
MAT_MAX_ROLL_DIAMETERS: Final[dict[str, float]] = {
    "RSMAT1200": 11.1,
    "RSMAT500": 10.0,
    "RSMAT250": 10.6,
}
MAT_ROLL_THICKNESS: Final[float] = 0.0237

MAT_AUTO_ADVANCE_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/configuration')].data.auto_advance"
)
MAT_SCHEDULE_ADVANCE_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/configuration')].data.schedule_enable"
)

MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/configuration')].data.custom_advance_value"
)
MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME: Final[JsonPath] = (
    "$.local.started_roll_diameter"
)

MAT_MODEL_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/configuration')].data.model"
)
MAT_POSITION_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/configuration')].data.position"
)

# -----------------------------------------------------------------------------
# REEFDOSE
# -----------------------------------------------------------------------------

DOSE_SCAN_INTERVAL: Final[int] = 120  # seconds
# DOSE_MANUAL_DOSEE_INTERNAL_NAME="$.local.head.<head_nb>.manual_dose"

# -----------------------------------------------------------------------------
# REEFATO
# -----------------------------------------------------------------------------

ATO_SCAN_INTERVAL: Final[int] = 20  # seconds

ATO_AUTO_FILL_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/configuration')].data.auto_fill"
)
ATO_VOLUME_LEFT_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/dashboard')].data.volume_left"
)

# TODO: test ato modes
ATO_MODE_INTERNAL_NAME: Final[JsonPath] = "$.sources[?(@.name=='/dashboard')].data.mode"
ATO_MODES: Final[tuple[str, ...]] = ("auto", "empty", "error")

# -----------------------------------------------------------------------------
# REEFRUN
# -----------------------------------------------------------------------------

RUN_SCAN_INTERVAL: Final[int] = 60  # seconds

RETURN_MODELS: Final[tuple[str, ...]] = (
    "return-6",
    "return-7",
    "return-9",
    "return-4000",
    "return-6000",
    "return-8000",
    "return-12000",
)
SKIMMER_MODELS: Final[tuple[str, ...]] = ("rsk-300", "rsk-600", "rsk-900")

FULLCUP_ENABLED_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/pump/settings')].data.fullcup_enabled"
)
OVERSKIMMING_ENABLED_INTERNAL_NAME: Final[JsonPath] = (
    "$.sources[?(@.name=='/pump/settings')].data.overskimming.enabled"
)

# -----------------------------------------------------------------------------
# REEFWAVE
# -----------------------------------------------------------------------------

WAVE_SHORTCUT_OFF_DELAY: Final[JsonPath] = (
    "$.sources[?(@.name=='/device-settings')].data.shortcut_off_delay"
)

WAVE_TYPES: Final[list[dict[str, str]]] = [
    {"id": "nw", "en": "No Wave", "fr": "Pas de vague"},
    {"id": "ra", "en": "Random", "fr": "Aléatoire"},
    {"id": "re", "en": "Regular", "fr": "Régulier"},
    {"id": "st", "en": "Step", "fr": "Paliers"},
    {"id": "su", "en": "Surface", "fr": "Surface"},
    {"id": "un", "en": "Uniform", "fr": "Uniforme"},
]

WAVE_DIRECTIONS: Final[list[dict[str, str]]] = [
    {"id": "alt", "en": "Alternate", "fr": "Alternatif"},
    {"id": "fw", "en": "Forward", "fr": "Marche Avant"},
    {"id": "rw", "en": "Reward", "fr": "Marche Arrière"},
]

# -----------------------------------------------------------------------------
# Libraries / endpoints
# -----------------------------------------------------------------------------

LIGHTS_LIBRARY: Final[str] = "/reef-lights/library?include=all"
WAVES_LIBRARY: Final[str] = "/reef-wave/library"
SUPPLEMENTS_LIBRARY: Final[str] = "/reef-dosing/supplement"

WAVE_SCHEDULE_PATH: Final[JsonPath] = "$.sources[?(@.name=='/auto')].data.intervals"
WAVES_DATA_NAMES: Final[tuple[str, ...]] = (
    "type",
    "direction",
    "frt",
    "rrt",
    "fti",
    "rti",
    "sn",
    "pd",
)
