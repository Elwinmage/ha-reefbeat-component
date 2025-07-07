from homeassistant.const import Platform

PLATFORMS: list[Platform] = [Platform.LIGHT,Platform.SENSOR,Platform.BINARY_SENSOR,Platform.SWITCH,Platform.NUMBER,Platform.BUTTON]

DOMAIN = "redsea"

DEVICE_MANUFACTURER="Red Sea"
CONF_FLOW_PLATFORM = "platform"
MODEL_NAME="hw_model"
MODEL_ID="hwid"
HW_VERSION="hw_revision"
SW_VERSION="version"

CONFIG_FLOW_IP_ADDRESS="ip_address"
CONFIG_FLOW_HW_MODEL="hw_model"
CONFIG_FLOW_SCAN_INTERVAL="scan_interval"

SCAN_INTERVAL=120 #in seconds
DO_NOT_REFRESH_TIME=2 #in seconds

DEFAULT_TIMEOUT=5

################################################################################

HW_LED_IDS=['RSLED160','RSLED90','RSLED50','RSLED115','RSLED60','RSLED175']
HW_DOSE_IDS=['RSDOSE4','RSDOSE2']
HW_MAT_IDS=['RSMAT','RSMAT500']
HW_ATO_IDS=['RSATO+']
HW_RUN_IDS=['RSRUN']
HW_WAVE_IDS=['RSWAVE45','RSWAVE25']

HW_DEVICES_IDS=HW_LED_IDS+HW_DOSE_IDS+HW_MAT_IDS+HW_RUN_IDS+HW_WAVE_IDS+HW_ATO_IDS

################################################################################
# LED
LED_SCAN_INTERVAL=120 #in seconds

LED_WHITE_INTERNAL_NAME="$.sources[?(@.name=='/manual')].data.white"
LED_BLUE_INTERNAL_NAME ="$.sources[?(@.name=='/manual')].data.blue"
LED_MOON_INTERNAL_NAME ="$.sources[?(@.name=='/manual')].data.moon"

DAILY_PROG_INTERNAL_NAME="$.local.daily_prog"

VIRTUAL_LED="virtual_led"
VIRTUAL_LED_MAX_WAITING_TIME=10
LINKED_LED="linked"

LED_CONVERSION_COEF=100/255

################################################################################
# MAT
MAT_SCAN_INTERVAL=300 #in seconds
# MAT SWITCHES
MAT_AUTO_ADVANCE_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.auto_advance"
# MAT NUMBERS
MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.custom_advance_value"

########################################
#DOSE__INTERNAL_NAME
DOSE_SCAN_INTERVAL= 120 # in seconds
#
#DOSE_MANUAL_DOSEE_INTERNAL_NAME="$.local.head.<head_nb>.manual_dose"

################################################################################
# ATO
ATO_SCAN_INTERVAL=10 #in seconds
#MAT SWITCHES
ATO_AUTO_FILL_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.auto_fill"

################################################################################
# RUN
RUN_SCAN_INTERVAL=5 #in seconds


