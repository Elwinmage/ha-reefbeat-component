from homeassistant.const import Platform

PLATFORMS: list[Platform] = [Platform.LIGHT,Platform.SENSOR,Platform.BINARY_SENSOR,Platform.SWITCH,Platform.NUMBER,Platform.BUTTON,Platform.SELECT,Platform.TIME]

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

DEFAULT_TIMEOUT=20


HTTP_MAX_RETRY=5
HTTP_DELAY_BETWEEN_RETRY=2

################################################################################


HW_G1_LED_IDS=['RSLED50','RSLED90','RSLED160']
HW_G2_LED_IDS=['RSLED60','RSLED115','RSLED170']

HW_LED_IDS=HW_G1_LED_IDS+HW_G2_LED_IDS

HW_DOSE_IDS=['RSDOSE2','RSDOSE4']
HW_MAT_IDS=['RSMAT']
HW_MAT_MODEL=['RSMAT250','RSMAT500','RSMAT1200']
HW_ATO_IDS=['RSATO+']
HW_RUN_IDS=['RSRUN']
HW_WAVE_IDS=['RSWAVE25','RSWAVE45']

HW_DEVICES_IDS=HW_LED_IDS+HW_DOSE_IDS+HW_MAT_IDS+HW_RUN_IDS+HW_WAVE_IDS+HW_ATO_IDS

################################################################################
# LED
LED_SCAN_INTERVAL=120 #in seconds

LED_WHITE_INTERNAL_NAME="$.sources[?(@.name=='/manual')].data.white"
LED_BLUE_INTERNAL_NAME ="$.sources[?(@.name=='/manual')].data.blue"
LED_MOON_INTERNAL_NAME ="$.sources[?(@.name=='/manual')].data.moon"

LED_ACCLIMATION_ENABLED_INTERNAL_NAME="$.sources[?(@.name=='/acclimation')].data.enabled"
LED_MOONPHASE_ENABLED_INTERNAL_NAME="$.sources[?(@.name=='/moonphase')].data.enabled"

LED_MOON_DAY_INTERNAL_NAME="$.local.moonphase.moon_day"
LED_ACCLIMATION_DURATION_INTERNAL_NAME="$.local.acclimation.duration"
LED_ACCLIMATION_INTENSITY_INTERNAL_NAME="$.local.acclimation.start_intensity_factor"

LED_MANUAL_DURATION_INTERNAL_NAME="$.local.manual_duration"

DAILY_PROG_INTERNAL_NAME="$.local.daily_prog"

LED_CONVERSION_COEF=100/255

#VIRTUAL

VIRTUAL_LED="virtual_led"
VIRTUAL_LED_MAX_WAITING_TIME=10
LINKED_LED="linked"
VIRTUAL_LED_SCAN_INTERVAL=10 #in seconds


################################################################################
# MAT
MAT_SCAN_INTERVAL=300 #in seconds
MAT_MIN_ROLL_DIAMETER=4.0
MAT_MAX_ROLL_DIAMETERS={'RSMAT1200':11.1,'RSMAT500':10.0,'RSMAT250':10.6}
MAT_ROLL_THICKNESS=0.0237
# MAT SWITCHES
MAT_AUTO_ADVANCE_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.auto_advance"
MAT_SCHEDULE_ADVANCE_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.schedule_enable"
# MAT NUMBERS
MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.custom_advance_value"
MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME="$.local.started_roll_diameter"
# MAT SELECT
MAT_MODEL_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.model"
MAT_POSITION_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.position"

########################################
#DOSE__INTERNAL_NAME
DOSE_SCAN_INTERVAL= 120 # in seconds
#
#DOSE_MANUAL_DOSEE_INTERNAL_NAME="$.local.head.<head_nb>.manual_dose"

################################################################################
# ATO
ATO_SCAN_INTERVAL=20 #in seconds
#ATO SWITCHES
ATO_AUTO_FILL_INTERNAL_NAME="$.sources[?(@.name=='/configuration')].data.auto_fill"

################################################################################
# RUN
RUN_SCAN_INTERVAL=60 #in seconds


