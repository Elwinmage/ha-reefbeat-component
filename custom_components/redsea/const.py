try:
    from homeassistant.const import Platform
    PLATFORMS: list[Platform] = [Platform.LIGHT,Platform.SENSOR,Platform.BINARY_SENSOR,Platform.SWITCH,Platform.NUMBER,Platform.BUTTON,Platform.SELECT,Platform.TIME,Platform.UPDATE,Platform.TEXT]
except Exception:
    pass

DOMAIN = "redsea"

DEVICE_MANUFACTURER="Red Sea"
CONF_FLOW_PLATFORM = "platform"
MODEL_NAME="hw_model"
MODEL_ID="hwid"
HW_VERSION="hw_revision"
SW_VERSION="version"

CLOUD_SERVER_ADDR="cloud.reef-beat.com"

CONFIG_FLOW_IP_ADDRESS="ip_address"

CONFIG_FLOW_ADD_TYPE="add_type"
ADD_CLOUD_API="cloud_api"
ADD_LOCAL_DETECT="local_detect"
ADD_MANUAL_MODE="manual_mode"
VIRTUAL_LED="virtual_led"

ADD_TYPES=[ADD_CLOUD_API,ADD_LOCAL_DETECT,ADD_MANUAL_MODE,VIRTUAL_LED]



#CLOUD
CONFIG_FLOW_CLOUD_USERNAME="username"
CONFIG_FLOW_CLOUD_PASSWORD="password"
CLOUD_SCAN_INTERVAL=600
CLOUD_DEVICE_TYPE="Smartphone App"
CLOUD_AUTH_TIMEOUT=2700 # seconds => 45m

CONFIG_FLOW_CLOUD_ACCOUNT="cloud_account"
CONFIG_FLOW_HW_MODEL="hw_model"
CONFIG_FLOW_SCAN_INTERVAL="scan_interval"
CONFIG_FLOW_INTENSITY_COMPENSATION="intensity_compensation"
CONFIG_FLOW_CONFIG_TYPE="live_config_update"

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

HW_DEVICES_IDS=HW_LED_IDS+HW_DOSE_IDS+HW_MAT_IDS+HW_RUN_IDS+HW_ATO_IDS+HW_WAVE_IDS

################################################################################
# COMMON
COMMON_ON_OFF_SWITCH="$.sources[?(@.name=='/mode')].data.mode"
COMMON_CLOUD_CONNECTION="$.sources[?(@.name=='/cloud')].data.enabled"
COMMON_MAINTENANCE_SWITCH="$.sources[?(@.name=='/mode')].data.mode"

################################################################################
# LED
LED_SCAN_INTERVAL=120 #in seconds

LED_WHITE_INTERNAL_NAME="$.sources[?(@.name=='/manual')].data.white"
LED_BLUE_INTERNAL_NAME ="$.sources[?(@.name=='/manual')].data.blue"
LED_MOON_INTERNAL_NAME ="$.sources[?(@.name=='/manual')].data.moon"
LED_INTENSITY_INTERNAL_NAME="$.sources[?(@.name=='/manual')].data.intensity"
LED_KELVIN_INTERNAL_NAME="$.sources[?(@.name=='/manual')].data.kelvin"

LED_ACCLIMATION_ENABLED_INTERNAL_NAME="$.sources[?(@.name=='/acclimation')].data.enabled"
LED_MOONPHASE_ENABLED_INTERNAL_NAME="$.sources[?(@.name=='/moonphase')].data.enabled"

LED_MOON_DAY_INTERNAL_NAME="$.local.moonphase.moon_day"
LED_ACCLIMATION_DURATION_INTERNAL_NAME="$.local.acclimation.duration"
LED_ACCLIMATION_INTENSITY_INTERNAL_NAME="$.local.acclimation.start_intensity_factor"

LED_MANUAL_DURATION_INTERNAL_NAME="$.local.manual_duration"

DAILY_PROG_INTERNAL_NAME="$.local.daily_prog"

LED_CONVERSION_COEF=100/255

LEDS_CONV=[{'name':'RSLED160','kelvin': [9000,12000,15000,20000,23000], 'white_blue':[200,125,100,50,10]},
           {'name':'RSLED90', 'kelvin': [9000,12000,15000,20000,23000], 'white_blue':[200,134,100,50,10]},
           {'name':'RSLED50', 'kelvin': [9000,12000,15000,20000,23000], 'white_blue':[200,100,50,25,5]},
           {'name':'RSLED60','kelvin': [],'white_blue':[]},
           {'name':'RSLED115','kelvin': [],'white_blue':[]},
           {'name':'RSLED170','kelvin': [],'white_blue':[]},
           ]

LEDS_INTENSITY_COMPENSATION=[{'name':'RSLED160','intensity':[10320,14300,17240,20575,23100,22260,20190,18070,13370],'white_blue':[200,170,150,125,100,75,50,30,0]}
]


LED_MODE_INTERNAL_NAME="$.sources[?(@.name=='/mode')].data.mode"
LED_MODES=["auto","timer","manual"]

EVENT_KELVIN_LIGHT_UPDATED='Kelvin_light_updated'
EVENT_WB_LIGHT_UPDATED='Kelvin_wb_updated'

#VIRTUAL

VIRTUAL_LED_MAX_WAITING_TIME=15
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
ATO_VOLUME_LEFT_INTERNAL_NAME = "$.sources[?(@.name=='/dashboard')].data.volume_left"

################################################################################
# RUN
RUN_SCAN_INTERVAL=60 #in seconds
RETURN_MODELS=['return-6','return-7','return-9','return-4000','return-6000','return-8000','return-12000']
SKIMMER_MODELS=['rsk-300','rsk-600','rsk-900']
FULLCUP_ENABLED_INTERNAL_NAME="$.sources[?(@.name=='/pump/settings')].data.fullcup_enabled"
OVERSKIMMING_ENABLED_INTERNAL_NAME="$.sources[?(@.name=='/pump/settings')].data.overskimming.enabled"

################################################################################
# WAVE
WAVE_SHORTCUT_OFF_DELAY="$.sources[?(@.name=='/device-settings')].data.shortcut_off_delay"


WAVE_TYPES=[
    {"id":"nw",
     "en":"No Wave",
     "fr":"Pas de vague"
     },
    {"id":"ra",
     "en":"Random",
     "fr":"Aléatoire"
     },
    {"id":"re",
     "en":"Regular",
     "fr":"Régulier"
     },
    {"id":"st",
     "en":"Step",
     "fr":"Paliers"
     },
    {"id":"su",
     "en":"Surface",
     "fr":"Surface"
     },
    {"id":"un",
     "en":"Uniform",
     "fr":"Uniforme"
     },
    ]

WAVE_DIRECTIONS=[
    {"id":"alt",
     "en": "Alternate",
     "fr": "Alternatif"
     },
     {"id":"fw",
      "en": "Forward",
      "fr": "Marche Avant"
      },
     {"id":"rw",
      "en": "Reward",
      "fr": "Marche Arrière"
      }]

################################################################################
# LIBRARIES
LIGHTS_LIBRARY="/reef-lights/library?include=all"
WAVES_LIBRARY="/reef-wave/library"
SUPPLEMENTS_LIBRARY="/reef-dosing/supplement"
WAVE_SCHEDULE_PATH="$.sources[?(@.name=='/auto')].data.intervals"
WAVES_DATA_NAMES=['type','direction','frt','rrt','fti','rti','sn','pd']
