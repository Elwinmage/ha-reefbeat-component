[← Back to the main page](../../README.md)

# ReefWave:
> [!IMPORTANT]
> ReefWave devices are different from other ReefBeat devices. They are the only devices that are slaves to the ReefBeat cloud.<br/>
> When you launch the ReefBeat mobile app, the status of all devices is queried and data from the ReefBeat app is retrieved from device state.<br/>
> For ReefWave, it is the opposite: there is no local control point (as you can see in the ReefBeat app, you cannot add a ReefWave to a disconnected aquarium).<br/>
> <center><img width="20%" src="../img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Waves are stored in the cloud user library. When you change a wave's value, it is changed in the cloud library and applied to the new schedule.<br/>
> So there is no local mode? Not so simple. There is a hidden local API to control ReefWave, but the ReefBeat app will not detect the changes. As a result, the device and Home Assistant on one side, and the ReefBeat mobile app on the other, will be out of sync. The device and Home Assistant will always be synchronized.<br/>
> Now that you know, make your choice!

> [!NOTE]
> ReefWave waves have many linked parameters, and the range of some parameters depends on other parameters. I was not able to test all possible combinations. If you find a bug, you can create an issue [here](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## ReefWave Modes
As explained above, ReefWave devices are the only devices that can become unsynchronized with the ReefBeat app if you use the local API.
Three modes are available: Cloud, Local, and Hybrid.
You can change the mode by setting the "Connect To Cloud" and "Use Cloud API" switches as described in the table below.

<table>
<tr>
<td>Mode name</td>
<td>Connect To Cloud Switch</td>
<td>Use Cloud API Switch</td>
<td>Behavior</td>
<td>ReefBeat and HA are synchronized</td>
</tr>
<tr>
<td>Cloud (Default)</td>
<td>✅</td>
<td>✅</td>
<td>Data is fetched via the local API. <br />On/off commands are also sent via the local API. <br />Wave commands are sent via the cloud API.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Data is fetched via the local API. <br />Commands are sent via the local API. <br />Device is shown as "off" in the ReefBeat app.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>Data is fetched via the local API. <br />Commands are sent via the local API.<br />The ReefBeat mobile app does not display the correct wave values if they have been changed via HA.<br/>Home Assistant always displays the correct values.<br/>You can change values from both the ReefBeat app and Home Assistant.</td>
<td>❌</td>
</tr>
</table>

For Cloud and Hybrid modes you must link your ReefBeat cloud account.
First create a ["Cloud API"](../../README.md#add-cloud-api) device with your credentials, and that's it!
The "Linked to account" sensor will be updated with the name of your ReefBeat account once the connection is established.
<p align="center">
<img src="../img/rswave_linked.png" alt="Image">
</p>

## Changing current values
To load current wave values into the preview fields, use the "Set Preview From Current Wave" button.
<p align="center">
<img src="../img/rswave_set_preview.png" alt="Image">
</p>
To change the current wave values, set the preview values and use the "Save Preview" button.

The behavior is the same as the ReefBeat mobile app. All waves with the same ID in the current schedule will be updated.
<p align="center">
<img src="../img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="../img/rswave_conf.png" alt="Image">
<img src="../img/rswave_sensors.png" alt="Image">
<img src="../img/rswave_diag.png" alt="Image">
</p>

## Groups
As in the ReefBeat app, all the grouped ReefWaves of an aquarium form one
group (with a cloud account only).

| Entity | Role |
| ------ | ---- |
| `switch` Grouped with the aquarium | Group the pump with the other ReefWaves of its aquarium, or ungroup it; a pump joining goes last. Unavailable without a cloud account |
| `sensor` Linked ReefWaves | Number of pumps in the group, their list in the `waves` attribute (`hwid`, `name`, `model`, `entry_id`, `available`) |

A program is written to every pump of the group: same slots, each pump with
its own intensities. As the app does, a write is refused when a pump of the
group is not loaded or does not answer: nothing is sent, so the group stays
in sync. Every loaded ReefWave is refreshed after a change of group.

## Day program
The `sensor` Waves Type carries the whole day program in its
`schedule` attribute: the list of its intervals, each starting at `st`
(minute of the day) and running until the next one, with `wave_uid`, `name`,
`type`, `direction`, `frt`, `rrt`, `fti`, `rti`, `sn`, `pd` and `sync`.
ha-reef-card draws the day from it.

## Services
These services drive the wave library and the day program, as the ReefBeat
app does; ha-reef-card's editors use them. `device_id` is the config entry
of the ReefWave.

| Service | Role |
| ------- | ---- |
| `redsea.wave_library` | Waves of the pump's aquarium, with this pump's intensities, the pumps using each wave and the pump's group. Without a cloud account: the waves of its own program |
| `redsea.wave_library_save` | Create a wave, or update one (`uid`). The shape is shared, the intensities are the pump's; the programs using an updated wave are written again. Red Sea waves and names already taken are refused |
| `redsea.wave_library_delete` | Delete one of your waves; refused for a Red Sea wave, or a wave a program uses |
| `redsea.wave_program_save` | Write the day program (`slots`: `st`, `wave_uid`, `direction`; the first one starts at 0) to every pump of the group; to the pump itself without a cloud account |
| `redsea.wave_preview` | Run a wave on the pump for 1 to 10 min, then back to its program |
| `redsea.wave_preview_stop` | Stop the preview |
| `redsea.wave_pump_set` | This pump's direction and intensities in the current wave (even a Red Sea one); the other pumps of the group are left as they are |
| `redsea.wave_group_set` | Group or ungroup a pump (`grouped`), as the switch does |
| `redsea.wave_group_order` | Order of the pumps of the group (`hwids`, every pump listed once) |

The library needs a ReefBeat cloud account: without one, `wave_library_save`
and `wave_library_delete` are refused. All the refusals are translated Home
Assistant errors.

## Icons
The wave type pictograms of the app are available as `redsea:wave-uniform`,
`redsea:wave-random`, `redsea:wave-regular`, `redsea:wave-step`,
`redsea:wave-surface` and `redsea:wave-none`.

### Maintenance tasks
| Task | Default | Range |
| ---- | ------- | ----- |
| Clean rotor cages | 2 months | 1 – 3 months |

See the [Maintenance](maintenance.md#maintenance) section.

---

[← Back to the main page](../../README.md)
