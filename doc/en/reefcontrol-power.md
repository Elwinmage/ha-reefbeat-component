[← Back to the main page](../../README.md)

# ReefControl-Power

The RSPOWER (Power Center) is a standalone device with its own IP address, exposed separately in Home Assistant.

<p align="center">
<img src="../img/rspower_devices.png" alt="Image">
</p>

- 6 or 8 controllable sockets depending on the model (RSPOWER6 / RSPOWER8)
- **Per socket**: editable name, on/off switch, state, mode, previous mode, consumption, and a "Delete socket" button that resets the socket to its factory state (mode `setup`, factory name)
- **Device**: total consumption, battery level, mode, model region and number of sockets
- **Local temperature probe** (optional): add / remove buttons, "Fetch temperature" button, calibration against the real temperature, desired and acceptable temperature ranges, name, notifications and logging switches — all available once a probe is installed. The temperature sensor carries `ranges` and `level` attributes, as the hub probes do.
- **ReefControl pairing**: paired hub, its type and status, link and internet state, and an "Unpair control hub" button
- Writes are shown at once (optimistic update), then confirmed by reading the device back

<p align="center">
<img src="../img/rspower_ctrl.png" alt="Image">
<img src="../img/rspower_conf.png" alt="Image">
<img src="../img/rspower_diag.png" alt="Image">
</p>

> [!NOTE]
> The local temperature probe and the ReefControl hub exclude each other: "Add temperature probe" is only available with neither, "Remove temperature probe" with a local probe, and "Unpair control hub" with a paired hub. The buttons stay visible but unavailable when they do not apply.

## Pairing with a ReefControl
Pairing is always started from the hub, with its **Pair power center** button: the hub pairs with the power center it finds on the network. Unpairing works from either side. When both devices are set up in Home Assistant, the change shows on both at once — for a pairing, only when a single free power center makes it certain which one.

Once paired, the hub's probes can drive the sockets. The power center only stores which probe type a socket follows; the probe itself and the thresholds live on the hub. Two services let a card or an automation read that side:

- `redsea.get_control_probes` — the probes of a hub (identity and current values), by its hardware id
- `redsea.get_control_subscriptions` — the rules the hub applies to the sockets of its power center, by its hardware id

Deleting a socket on the power center only clears its half of a probe rule: the hub's **Unsubscribe socket N** button clears the other half.

## Socket mode and sensor-driven sockets
A socket's mode (off / on / schedule / sensor) and its schedule/sensor-threshold settings (e.g. "turn this socket on when the local temperature drops below 24 °C") are configured from [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), as for the [hub ports](reefcontrol.md#port-and-socket-modes).

Each socket exposes a `sensor.socket_N_mode` entity for automations: its state is the socket's current mode, and its attributes carry the current `schedule` and (when in sensor mode) `sensor_config`, tagged by `sensor_source`: `local` for the power center's own probe, `control` for a rule held by the paired hub.

A socket driven by a schedule or a probe can be switched off by hand: its mode then reads `off` while the **previous mode** sensor keeps the automatic mode it will return to.

The device automatically leaves its initial "setup" state as soon as the first socket is configured, mirroring the ReefBeat app — no manual action needed.

---

[← Back to the main page](../../README.md)
