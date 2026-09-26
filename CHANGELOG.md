# UNRELEASED

## MODIFICATIONS

### RSPOWER
 - Calibration against a reference temperature (number
   `temperature_calibration`) replaces the `temperature_offset` number, as
   on the RSCONTROL probes (see there). `temperature_offset` is purged from
   the registry.
 - Optimistic updates for installing or removing the local temperature
   probe and unpairing the hub (see RSCONTROL).
 - `power_temperature` carries `ranges` (`[acceptable_low, desired_low,
   desired_high, acceptable_high]`, from `/temperature/config`) and `level`
   (from `/dashboard.temperature.level`), as the hub probes do, so a card
   draws its level the same way.

### RSCONTROL
 - Calibration of the embedded temperature of pH, EC and ATO probes
   (number `probe_temp_calibration`, °C), the same way: it goes through
   `/probe/offset?type=<ph|ec|ato>&uid=…`, captured on pH and EC (adds too,
   and moves `temp_value`). Its date is not the probe's calibration date.
 - Calibration against a reference value replaces the offset numbers:
   `probe_orp_calibration` (mV) and `probe_temperature_calibration` (°C) per
   probe show its reading; with the probe in a solution or water of known
   value, setting the number to that value reads the probe again and moves
   its offset by `reference - reading`, as the ReefBeat app's ORP validation
   does, so the probe then reads the reference. The `probe_offset` numbers
   are removed, and purged from the registry.
 - `/probe/config` is read again when a probe appears or its
   `last_installation_date` changes. Reinstalling a probe resets its settings
   on the hub (an ORP probe goes back to `[100, 200, 400, 480]`); installed
   from the ReefBeat app, the integration kept the old ranges while the hub
   judged the level against the new ones (a card's bar and dot disagreed).
 - ORP probes get the date of their last validation (sensor
   `probe_last_adjustment`), read from `GET /probe/offset?type=orp&uid=…`
   (`{"offset", "last_adjustment_date"}`).
 - `POST /probe/offset` *adds* the posted value to the current offset
   (captured on an ORP probe: 1 + 35 = 36, 36 + 20 = 56, 56 - 55 = 1) and
   the readings include it. Every offset write posts the correction only,
   reads the offset back, and posts the full offset if a hub replaced it
   instead (not captured yet for a temperature probe).
 - Calibration reminders are dated by the hub: a pH or EC probe calibrated
   from the ReefBeat app (`/dashboard.probes[].last_adjustment_date`) or an
   ORP probe validated (`/probe/offset` `last_adjustment_date`) marks its
   calibration task done at that date. The task only moves forward, so a
   later press of its button is kept.
 - Probe calibration reminders follow Red Sea's official intervals: pH every
   3 months (was monthly; its interval is now set in months, number
   `maint_control_probe_calibration_ph_interval_months` replaces
   `..._interval_weeks`), ORP every 6 months (was 2) and a new salinity (EC)
   calibration task every 2 months (button, interval and notification switch
   per EC probe). Temperature probes still get no calibration reminder.
   Only the defaults change: an interval already set by the user is kept,
   so a pH or ORP interval chosen under the old ranges should be set again.
 - Removed the per-port ATO entities, which could never work on the hub:
   buttons `ato_manual_pump`, `ato_stop`, `ato_resume`, number
   `ato_volume_left`, switch `ato_auto_fill`, binary sensors
   `port_check_sensor`, `port_is_advancing`, `port_is_pump_on`,
   `port_leak_sensor` and sensors `port_last_fill_date`,
   `port_last_pump_on_cause`, `port_today_volume`, `port_leak_status`. They
   were built for a port of type `ato` and read RSATO+ fields the hub's
   `/dashboard.ports` never carries, and wrote to `/ato/…` endpoints it does
   not have: a port driven by an ATO probe stays of type `other`. Their
   API helpers and translations are gone with them.
 - Leak probes tell where the water comes from. `/dashboard` only has the
   boolean `detected`; the origin is in the probe's own reading
   (`GET /probe?type=leak&uid=…` → `leak_status`: `dry`,
   `aquarium_water_leak` or `rodi_water_leak`, and `ec`, the conductivity it
   measured), as the ReefBeat app models it (ControlLeakStatus). Each leak
   probe gets a `probe_leak_status` sensor (dry / aquarium water / RO/DI
   water) and a `probe_leak_conductivity` diagnostic sensor. A probe is read
   on its own as soon as it turns wet, once per leak; its "read value"
   button reads it too.
 - Fix: reading a leak probe on demand ignored a wet answer: only `dry`,
   `wet`, `leak` and `detected` were understood, not the firmware's
   `aquarium_water_leak` / `rodi_water_leak`.
 - Fix: a leak probe added from Home Assistant stayed in `status: setup` —
   not shown by the app, reporting nothing. Its install now follows the
   app's sequence: `POST /probe/install`, `GET /probe/info`, `POST
   /ble/off`, then `PUT /leak/config` (buzzer, leak detector, notification
   on, emergency shutdown off) and `PUT /probe/config` with its name
   (`Leak <uid digits>`, as the app names it). Every probe type now reads
   `/probe/info` after its install, as the app does.
 - Optimistic updates: an accepted write is shown at once, before the
   settle delay and read-back that follow it; the read-back corrects it if
   the device did not apply it. Covers the 12V ports as the card writes them
   through `redsea.request` (mode, name and power in `/ports/config`, probe
   rule in `/ports/subscribe`, install, uninstall), the port uninstall
   button, and pairing / unpairing the power center — both ends at once when
   the power center is set up too (pairing only when a single free power
   center makes it certain which one).
 - A failed GET no longer dumps the whole cached device data into the debug
   log: only the URL, status and reason are logged.
 - Fix: leak probe sensors were removed at every start-up ("Removing orphaned
   probe entity …_leak"). Their unique_id lacked the probe type
   (`probe_{uid}_detected`), so the orphan purge did not recognise them as
   belonging to a current probe. They are now keyed
   `probe_leak_{uid}_detected`; an existing entry is migrated before the
   platforms load, so the entity_id and its history are kept.
 - Every ReefSense probe entity (sensors and the leak `binary_sensor`) now
   carries `probe_uid`, `probe_type` and `probe_index` state attributes. All
   probes of a type share the same translation keys, so these attributes are
   the only way for a card to group a hub's entities per probe;
   `probe_index` is the probe's position in `/dashboard.probes`.
 - The measurement sensors (main value and embedded temperature) also carry a
   `ranges` attribute, `[acceptable_low, desired_low, desired_high,
   acceptable_high]`, read from `/probe/config` (`temp.ranges` for the
   temperature).
 - Every per-port entity of the 12V ports (sensors and ATO binary sensors)
   carries a `port` attribute (0-based), for the same reason.
 - Every entity of a 12V port (switch, name, ATO buttons and numbers
   included) now carries the `port` attribute, not only the sensors: both
   ports share their translation keys, so it is what tells a card which port
   an entity drives. The keys themselves are unchanged.
 - The `port_N_mode` sensor carries what a card needs to edit the port, as
   `socket_N_mode` does on a power center: `config` (the whole
   `/ports/config` entry, `power_on_percent` included), `schedule` and
   `sensor_config` (the hub's probe rule for the port, from the `internal`
   part of `/subscription-info`, else the `sensor` field of the port entry
   when it names a probe — the app's own `{default_state, app_cache}` there
   is not a rule),
   with `sensor_source: control`.
 - A port's schedule is read back from `GET /port/<n>/schedule`, only while
   the port is in `schedule` mode (from `/dashboard` on polls, from
   `/ports/config` after a config refresh): an uninstalled port answers 503
   and a port on, off or probe-driven does not use it. The source is
   registered when the port switches to schedule, fetched at once, and
   dropped when it leaves that mode.
 - The probe settings (range bounds, EC unit, temperature offset, buzzer /
   notify / enabled / maintenance switches, "read now" button) carry
   `probe_uid` and `probe_type` too, so a card can open the settings of one
   probe. They carry no `probe_index`: these attributes are set once at
   setup, and only the measurement sensors track the live position.

### RSATO
 - New `buzzer_enabled` switch on the RSATO+: enables/disables the leak alarm
   buzzer. Reverse-engineered from the Red Sea Android app
   (`ATODevice$Keys$Configuration$Buzzer`), pushed as
   `{"buzzer": {"enabled": <bool>}}` on a PUT to `/configuration`. The key is
   omitted from the payload when the device has not reported it, since the
   firmware merges partial configurations.
 - The switch replaces the read-only `binary_sensor.buzzer_enabled`, which
   reported the same firmware setting from `/dashboard`. **Breaking**: that
   entity is gone; use the switch, which now reads from `/dashboard` too and
   so keeps following changes made in the Red Sea app.
 - Same treatment for the leak probe's arming flag: the read-only
   `binary_sensor.enabled` becomes a switch (`leak.sensor_enabled` on
   `/configuration`, read back from `/dashboard.leak_sensor.enabled`).
   **Breaking**: the binary_sensor is gone, the switch keeps its
   `enabled` translation key and label.

### BUTTONS
 - Every generic button now reads the device back after its action, as the
   dose, run and wave button entities already did. **Fixes** the ATO fill and
   stop-fill buttons leaving `is_pump_on` stale until the next scan interval.
 - New `optimistic` field on `ReefBeatButtonEntityDescription`: values written
   into the cache as soon as the command is accepted, so entities move on the
   press instead of on the read-back a couple of seconds later. Used by the
   ATO fill and stop-fill buttons for `is_pump_on`; the refresh that follows
   replaces the guess with what the device reports.

### ALL DEVICES
 - New `fetch_data` button on every device, next to `fetch_config`. It forces
   an immediate read of the polled "data" sources instead of waiting for the
   scan interval, where `fetch_config` only covers sources typed "config".
   Offered whatever `live_config_update` is set to, since data sources are
   polled either way.

### RSATO polling
 - `/configuration` is now a polled "data" source instead of an on-demand
   "config" one. It carries `auto_fill`, which the device does not report on
   `/dashboard`, so the switch used to stay stale until someone pressed
   `fetch_config`. Costs one extra GET per cycle on the LAN; `fetch_config`
   no longer covers this source, since that button only refreshes sources
   typed "config".

### SWITCH
 - New `push_source` field on `ReefBeatSwitchEntityDescription`, for a setting
   read at one endpoint and written at another. Defaults to the source named
   in `value_name`, so every existing switch is unchanged.

### CONST
 - New `ATO_BUZZER_ENABLED_INTERNAL_NAME`.

### TRANSLATIONS
 - New `entity.switch.buzzer_enabled` key in the 8 locales and `strings.json`;
   `entity.binary_sensor.buzzer_enabled` removed with its entity.

## FIXES

### RSCONTROL probes
 - The probe-scoped maintenance tasks were built by `button.py` and
   `switch.py` as a single device-level entity, without the `{probe}`
   translation placeholder their names require, which HA reported as a
   name/placeholder mismatch. They now fan out per ReefSense probe through
   `iter_maintenance_probes()`, as `number.py` already did.

### ENUM sensors
 - An ENUM sensor whose device reported a value outside its `options` raised
   `ValueError` on every state write, killing the entity and every other
   listener of the same coordinator. Seen on `port_N_last_pump_on_cause`,
   which an RSCONTROLPRO ATO port reports as `unknown` -- a reserved HA state
   that can never be an option. Unlisted values are now reported as unknown.

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

