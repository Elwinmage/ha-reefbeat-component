# v2.0.0

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

