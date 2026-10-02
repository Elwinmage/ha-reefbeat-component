[← Back to the main page](../../README.md)

# ReefControl:
<p align="center">
<img src="../img/rscontrol_devices.png" alt="Image">
</p>

The ReefControl hub (RSCONTROLPRO / RSCONTROLLITE) reads the ReefSense probes plugged into its extension boxes, drives its 12V DC ports (2 on the Pro, 1 on the Lite) and, once paired, the sockets of a [ReefControl-Power](reefcontrol-power.md#reefcontrol-power).

- **ReefSense probes** — pH, ORP, salinity (EC), temperature, ATO (water level) and leak: value and level (desired / acceptable / danger), status, name, uid, last installation and last calibration dates, and the embedded temperature of the pH, EC and ATO probes. Every probe entity carries `probe_uid`, `probe_type` and `probe_index` attributes, and the measurement sensors a `ranges` attribute (`[acceptable_low, desired_low, desired_high, acceptable_high]`).
- **Salinity probes** — conductivity, salinity (ppt) and specific gravity sensors, plus a display-unit select.
- **Leak probes** — wet/dry state, **origin of the water** (dry / aquarium water / RO/DI water) and the conductivity measured, read as soon as the probe turns wet.
- **Per-probe settings** — desired and acceptable ranges (main reading and embedded temperature), enabled / buzzer / notifications / maintenance switches, and a "Read now" button that fetches a fresh reading without waiting for the next poll.
- **Probe calibration** — see [below](#probe-calibration).
- **Buzzer** — danger buzzer and leak buzzer (enable, frequency, duty cycle), danger debounce, leak detector switch; buzzer active / dismissed state and its cause.
- **12V ports** — editable name, on/off switch, state, mode, type, consumption and an "Uninstall port" button. The `port_N_mode` sensor carries the whole port configuration, its schedule and its probe rule as attributes, so a card can edit the port (see [Port and socket modes](#port-and-socket-modes)).
- **ReefControl-Power pairing** — paired power center, its state and link, "Pair power center" / "Unpair power center" buttons, and one "Unsubscribe socket" button per power-center socket the hub drives from a probe.
- **Add, replace or remove probes** from the integration's options menu (see [below](#probe-management-add--replace--remove)).
- Writes are shown at once (optimistic update), then confirmed by reading the device back.

<p align="center">
<img src="../img/rscontrol_sensors.png" alt="Image">
<img src="../img/rscontrol_ctrl.png" alt="Image">
<img src="../img/rscontrol_conf.png" alt="Image">
<img src="../img/rscontrol_diag.png" alt="Image">
</p>

> [!TIP]
> The [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) draws the hub, its probes, its ports and the paired power center, and drives the calibrations and the port modes in a few clicks.

## Probe management (add / replace / remove)
BLE probes (pH, ORP, EC, ATO, leak, temperature) are managed from the integration's **Options** menu, mirroring the Red Sea app:

<p align="center">
<img src="../img/rscontrol_probe_management.png" alt="Image">
</p>

- **Add a probe**: put the probe in pairing mode, pick its type, then confirm to scan. The probe is set up the way the app does it: a leak probe, for example, is named `Leak <uid>` with its buzzer, leak detector and notifications on.
- **Replace a probe**: pick the probe to replace, put a new probe of the same type in pairing mode, then confirm. The new probe inherits the old one's entity history/statistics.
- **Remove a probe**: select one or more probes, then confirm — this permanently deletes the probe's entities and their history.

> [!NOTE]
> Reinstalling a probe resets its settings on the hub (an ORP probe goes back to its factory ranges). The integration reads the probe configuration again whenever a probe appears or is reinstalled, from Home Assistant or from the ReefBeat app.

## Probe calibration
Each probe type is calibrated the way the ReefBeat app does it.

| Probe | How | Entity / service |
| ----- | --- | ---------------- |
| ORP | Dip the probe in the calibration solution, then set the number to the solution's value | `Calibrate {probe} (solution value)` |
| Temperature | Set the number to the real temperature of the water the probe is in | `Calibrate {probe} (real temperature)` |
| Embedded temperature (pH, EC, ATO) | Same, for the temperature sensor built into the probe | `Calibrate {probe} temperature (real temperature)` |
| pH | Two points: pH 7, then pH 10 (salt water) or pH 4 (fresh water) | `redsea.probe_calibration` |
| Salinity (EC) | One point, with the value of the solution in mS/cm | `redsea.probe_calibration` |

The **reference-value numbers** (ORP and temperatures) show the current reading. Setting one to the reference reads the probe again and moves its offset by `reference - reading`, so the probe then reads the reference.

The **pH and EC calibrations** are multi-step and go through the `redsea.probe_calibration` service, one step per call: `enter`, then `point` for each calibration point, `status` polled until the hub reports success or failure (it returns `calibration_status`, `time_left` and `stability_progress` meanwhile), and finally `exit`. The [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) runs this whole sequence for you.

```yaml
action: redsea.probe_calibration
data:
  device_id: <config entry of the hub>
  probe_type: ph
  probe_uid: "0x00B39"
  action: point
  point: MID
  solution_value: 7.0
  solution_rated_temp: 25
```

The date of the last calibration comes from the hub: a pH or EC probe calibrated from the ReefBeat app, or an ORP probe validated, marks its maintenance task as done at that date.

## Multi-probe temperature fusion
When two or more temperature sources are present (the dedicated temperature probe plus the temperature embedded in the EC/pH/ATO probes), ReefControl computes a robust **fused temperature** on top of the individual readings:

- **Fused temperature** (`sensor`): a single value aggregated with the selected method — Median (default), Mean, Minimum or Maximum. Configurable via the **Temperature fusion method** select entity.
- **Temperature coherence** (`binary_sensor`) and **Temperature spread** (`sensor`, diagnostic): whether the sources agree within the **Temperature coherence threshold** (configurable, default 0.5 °C), and by how much they disagree.
- **Temperature anomaly source** (`sensor`, diagnostic): `ok` when every source agrees, the name of the probe(s) suspected of drifting or reading incorrectly, or `unknown` when the disagreement cannot be attributed to a single probe. The sensor's attributes list every source with its value, 1‑hour change and status.
- A **maintenance switch per temperature-capable probe**: turning it on temporarily excludes that probe from the fusion/coherence/anomaly calculation, so cleaning or recalibrating a probe never triggers a false alarm.
- A **calibration against the real temperature** (`number`) per temperature-capable probe (see [Probe calibration](#probe-calibration)).

These entities only appear once at least two temperature sources are detected.

## Port and socket modes
A 12V port of the hub, like a socket of the power center, runs in one of four modes: **off**, **on**, **schedule** or **sensor** (driven by a probe). A port not installed yet is in `setup` mode and refuses every write until it is installed.

These settings are not exposed as individual entities — with several ports and sockets and one set of thresholds per probe type, that would mean dozens of rarely-used entities. Configure them from [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), which issues the same calls as the ReefBeat app in one action via the `redsea.request` service (see the integration's Services in Home Assistant's Developer Tools).

The `port_N_mode` sensor still carries everything an automation needs to read the active configuration: `config` (the whole port entry, `power_on_percent` included), `schedule` (read back from the hub while the port is in schedule mode) and `sensor_config` (the probe rule), with `sensor_source: control`.

> [!NOTE]
> A port driving an ATO pump from an ATO probe stays of type `other`: the ReefBeat app's ATO kit wizard is what links them. The hub does not expose the RSATO+ ATO controls (manual fill, auto-fill, volume left…).

## Maintenance tasks
| Task | Probes | Default | Range |
| ---- | ------ | ------- | ----- |
| Clean probe | Every probe | 30 days | 2 – 8 weeks |
| Calibrate probe | pH | 3 months | 2 – 4 months |
| Calibrate probe | Salinity (EC) | 2 months | 1 – 3 months |
| Validate probe | ORP | 6 months | 5 – 7 months |
| Replace probe | pH, ORP | 12 months | 9 – 18 months |

Tasks are tracked **per probe**, following Red Sea's official recommendations. Temperature and leak probes get no calibration reminder, and the 4-pole EC cell is never replaced on a schedule. See the [Maintenance](maintenance.md#maintenance) section.

---

[← Back to the main page](../../README.md)
