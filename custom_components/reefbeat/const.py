from homeassistant.const import Platform

DOMAIN = "reefled"

DEVICE_MANUFACTURER="Red Sea"

CONF_FLOW_PLATFORM = "platform"

PLATFORMS: list[Platform] = [Platform.LIGHT,Platform.SENSOR,Platform.BINARY_SENSOR,Platform.SWITCH]

CONFIG_FLOW_IP_ADDRESS="ip_address"

SCAN_INTERVAL=120 #in seconds
DO_NOT_REFRESH_TIME=2 #in seconds

FAN_INTERNAL_NAME='fan'
TEMPERATURE_INTERNAL_NAME="temperature"
WHITE_INTERNAL_NAME="white"
BLUE_INTERNAL_NAME="blue"
MOON_INTERNAL_NAME="moon"
STATUS_INTERNAL_NAME="status"
IP_INTERNAL_NAME="ip"


MODEL_NAME="hw_model"
MODEL_ID="hwid"
HW_VERSION="hw_revision"
SW_VERSION="version"


DAILY_PROG_INTERNAL_NAME="daily_prog"

VIRTUAL_LED="virtual"
VIRTUAL_LED_INIT_DELAY=5 #wait 5s to be sure real LED have been configured
LINKED_LED="linked"

CONVERSION_COEF=100/255

