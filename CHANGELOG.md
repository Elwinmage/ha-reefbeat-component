# v2.3.0

## NEW DEVICES

Adds read-only support for the new ReefControl family:

 - **RSPOWER6 / RSPOWER8** — ReefControl Power smart center (6 or 8 AC sockets).
   Exposes per-socket name, mode, state and consumption, plus battery level,
   temperature and pairing status to the ReefControl hub.
 - **RSCONTROLPRO / RSCONTROLLITE** — ReefControl hub for ReefSense probes.
   Exposes per-port (12V DC) name, mode, state, type and consumption, plus
   cable-connected, leak-detector, buzzer status and pairing status to the
   ReefControl Power center. Pro has 2 ports, Lite has 1.

Write endpoints (per-socket on/off, mode change, probe calibration) are **not
yet reverse-engineered** — only monitoring is available at this stage. Sniffs
of real device traffic are welcome to unlock write support in a later release.

## MODIFICATIONS

### CONST
 - New `HW_POWER_IDS`, `HW_CONTROL_IDS`, `HW_POWER_SOCKET_COUNT`,
   `HW_CONTROL_PORT_COUNT`, `POWER_SCAN_INTERVAL`, `CONTROL_SCAN_INTERVAL`.
 - `HW_DEVICES_IDS` extended so LAN auto-detection picks up the new models.

### API
 - New `ReefPowerAPI` and `ReefControlAPI` classes (both register
   `/configuration` as a config source).

### COORDINATORS
 - New `ReefPowerCoordinator` (with `socket_count` derived from hw_model)
   and `ReefControlCoordinator` (with `port_count`: 1 for Lite, 2 for Pro).
 - `get_model_type()` maps to `reef-power` / `reef-control` for firmware URL
   resolution against the cloud.

### PLATFORMS
 - `sensor.py`: new `POWER_SENSORS` and `CONTROL_SENSORS` static descriptions,
   plus dynamic per-socket / per-port sensors.
 - `binary_sensor.py`: new `POWER_SENSORS` and `CONTROL_SENSORS` for internet,
   pairing, cable, buzzer, leak-detector and per-socket enabled flags.

### TRANSLATIONS
 - New keys in `en.json` and `fr.json` for the new sensors and binary sensors.

# v2.0.1

CLOUD: Correct #63 - Cant log to redsea account

# v2.0.0

> [!CAUTION]
>  CLOUD, RSDOSE and RSRUN users: you have do delete and recreate your devices.

## GENERAL

### Compatibility with the new ha-reef-card
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/refs/heads/main/doc/img/rsdose/rsdose4_ex1.png" />

Follow this link to install it:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

### Big code refactoring thanks to @roblandry
Because the device id creation changed to be compliant with HA standards, RSDOSE and RSRUN users will see double sub-device with half empty. Remove your device and recreate it.

### New icons for your HomeAssistant

<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/doc/img/icons_feeding_maintenance.png"/>
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/doc/img/icons_devices.png"/>

## MODIFICATIONS

### ALL
 - Use strandard HA translations method for all devices and entities.
 - Add check_translation utility
 - Add de, es, it ,pl and pt languge support.

### CLOUD
- Add schortcut support.
- Correct scan_interval.

### RSATO
- Remove ato_mode.

### RSDOSE
- Correct supplement is_name_editable for specific supplement
- Add support of supplement display_name modification
- Add size for supplements

### RSLED
- Remove death code.

### RSMAT
- Correct #60. Since firmware update schedule time is in seconds and not more in minutes.

### RSWAVE
- Correct load preview.

### Icons
 - Add personnal icons for redsea domain.

