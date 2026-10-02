[← Back to the main page](../../README.md)

# Virtual LED
A virtual LED is a **group** of ReefLEDs, as the "grouped" LEDs of the
ReefBeat app: its lamps are driven as one.

- Create a virtual device from the integration panel, then use the configure
  button: choose the LEDs (two at least, a LED belongs to one group at most),
  then their order. A new virtual LED starts with the lamps the ReefBeat app
  already groups, in the app's order.
- You can only use Kelvin and intensity to control your LEDs if you have G2 or a mix of G1 and G2.
- You can use both Kelvin/Intensity and White & Blue if you have only G1 lights.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

## What the group shares
A shared value set on the virtual LED, or on one of its lamps, is applied to
every lamp of the group: manual channels, kelvin / intensity, mode, timer,
programs, acclimation, moon phase and the
[weather program](reefled.md#weather-program). What belongs to a lamp stays on the lamp: name,
Wi-Fi, cloud, firmware, identify, reset…

As the app does, a group write is refused when one of the lamps is not
loaded, does not answer, or is in a mode the group cannot drive (off, or held
by a shortcut): nothing is sent, so the lamps stay in sync, and the error
names the lamps. A lamp set out of service in the app is left out of the
writes, the checks and the staggered sunrise. White / blue cannot be set on
a group holding a G2 lamp: use kelvin / intensity.

## Staggered sunrise
As in the app, the lamps of a group can start their day one after the other:

| Entity | Role |
| ------ | ---- |
| `switch` Staggered sunrise | Stagger the sunrise of the group |
| `number` Staggered sunrise delay | Minutes between two lamps, 1 to 15 (10 by default) |

Each lamp starts its day `delay × position` minutes later (the first lamp of
the group is not delayed). The value is written to the
Sunrise offset of each lamp, again whenever the lamps of the
group or their order change; a lamp leaving the group goes back to 0.

## The lamps of the group
The `sensor` Linked LEDs, on the virtual LED and on each lamp of
a group, gives the number of lamps and, in its `leds` attribute, their list
in the group order: `hwid`, `name`, `model`, `g2`, `offset` (sunrise offset in
minutes, empty for a lamp without `/offset`) and `entry_id`. ha-reef-card
uses it to list the lamps.

## Synchronisation with the ReefBeat app
With a ReefBeat cloud account ([Cloud API](../../README.md#add-cloud-api)), a
group whose lamps are of one model, in one aquarium and on one account is
the same group in the app: the group, its order and its staggered sunrise
are written to the cloud, or taken from the app, whichever changed since
they were last in sync.

A group of the app that no virtual LED drives (two lamps at least loaded in
Home Assistant) is proposed as a new virtual LED in the "Discovered" devices,
with its lamps in the app's order; "Ignore" keeps it ignored.

When something needs your decision, a repair is raised (Settings > System >
Repairs):

| Repair | What to do |
| ------ | ---------- |
| No ReefBeat cloud account | The app could hold the group but no cloud account lists its lamps: add the account (the repair goes away by itself), or keep the group in Home Assistant only |
| LEDs grouped in the ReefBeat app | The group holds several models, which the app cannot group, and some lamps are still grouped in the app: ungroup them there; the group then lives in Home Assistant only |
| Changed in Home Assistant and in the ReefBeat app | Both sides changed since the last sync: choose the group to keep |

---

[← Back to the main page](../../README.md)
