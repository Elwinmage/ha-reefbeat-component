[← Back to the main page](../../README.md)

# Poseidon mode

<p align="center">
<img src="../img/poseidon/poseidon.png" alt="Poseidon" width="240">
</p>

Poseidon mode puts a relay between your ReefBeat devices and the Red Sea MQTT
broker, inside Home Assistant. A device in Poseidon mode connects to Home
Assistant instead of `mqtt.reef-beat.com`, and Home Assistant passes its
traffic on to Red Sea unchanged: the ReefBeat app keeps working as before.

> [!WARNING]
> Poseidon mode is experimental. For now it only relays and observes the
> traffic: the integration still reads the devices by polling them.

## Adding Poseidon

*Settings > Devices & services > Red Sea > Add entry > Poseidon mode*

- **Listening port**: the first free port from 1884 is proposed (1883 and 8883,
  the usual MQTT ports, are skipped). It is checked again when you submit, and
  every time the relay starts: if another service took it, a repair issue says
  so and the devices are left alone.
- **Address of Home Assistant**: the IPv4 address the devices use to reach Home
  Assistant.
- **Cloud account**: the ReefBeat cloud account used to get the keys of the
  devices. A cloud account is required.

## Adding devices

*Poseidon > Configure > Add devices*

Every device of the integration is listed with its status:

| Status | Meaning |
|---|---|
| Can be checked | Its keys are known: it switches to Poseidon mode at once |
| Can be checked, 🔑 | Its keys must be captured first (see below) |
| Already in Poseidon mode | Nothing to do |
| No cloud credentials | Bound to a local-only aquarium: cannot use Poseidon mode |
| Not in the cloud account | Its keys cannot be captured with this account |
| Unreachable | Does not answer |

> [!CAUTION]
> **Capturing the keys is destructive.** A device does not give its keys: to
> get them, it is deleted from the ReefBeat cloud and created again.
> - it is unbound from its aquarium, and the app may need it paired again;
> - schedules, presets and history kept in the cloud for it can be lost;
> - its configuration is saved before and compared after: ReefRun and
>   ReefWave get theirs back automatically, for the other devices what changed
>   is listed in a notification (the saved configuration stays in
>   `/config/redsea/poseidon/snapshots/`).
>
> A capture is done once per device: Home Assistant keeps the keys, even when
> Poseidon is removed.

## The Poseidon switch

Each device with known keys gets a **Poseidon mode** switch on its page:

- **on**: the device talks to Red Sea through Home Assistant;
- **off**: the device talks to Red Sea directly (normal mode).

Its state is read from the device itself. Its attributes:

| Attribute | Meaning |
|---|---|
| `connection_state` | Connection state reported by the device |
| `last_up` / `last_down` | Last traffic device → Red Sea / Red Sea → device |
| `silent` | In Poseidon mode, but nothing went through the relay for the delay of the settings |

A silent device also raises a repair issue, which goes away by itself when its
traffic resumes. A silent device is never switched back automatically.

## What happens when

| Event | Devices |
|---|---|
| Home Assistant restarts, Poseidon reloads | Left as they are: they reconnect when the relay is back |
| Poseidon disabled or removed | All switched back to normal mode |
| A device cannot be switched back | Named in a notification |
| A device is pointed at the relay but never connects to it (it kept its session with Red Sea) | Made to reconnect after 2 minutes: pointed back at Red Sea, then at the relay again, twice at most |

Poseidon mode is only ever entered by you. Every automatic switch goes back to
normal mode.

## Strategies

What Home Assistant does with a device in Poseidon mode. Each device has a
**Poseidon strategy** select next to its switch; the settings give the default.

| Strategy | Polling | Pushed states | File |
|---|---|---|---|
| *Spy* | unchanged | recorded, compared with the next poll | `spy.jsonl` |
| *Shadow* | unchanged | merged into the device's data, compared with the next poll | `shadow.jsonl` |
| *Poseidon* | every N minutes | used; the device is read again on each state while its family cannot be merged | — |

Families merged so far, from the spy runs:

| Family | Merged |
|---|---|
| ReefControl Power | states, telemetry; the socket states are computed from their schedules, as the ReefBeat app does |
| ReefDose | states, telemetry; a `dosing-log` (end of a dose) reads it again, for its dosing queue |
| ReefMat | states, telemetry, `rolling-log` (end of an advance) |
| ReefLED | telemetry |

For the other families, *Shadow* only compares, and *Poseidon* reads the device
again every time it pushes a state. *Poseidon* also reads it again when a state
tells something its merger cannot write (a setting it does not know, a ReefDose
schedule, pushed without its intervals). Such a read includes the config
sources: what the app changes is mostly settings, which the polling never reads
again.

A ReefControl Power without temperature probe nor socket driven by a sensor has
everything that changes pushed: with *Poseidon*, it is only polled every
*Safety polling interval*.

### Spy

`/config/redsea/poseidon/logs/spy.jsonl` (rotated at 10 MB, 5 files kept)
holds, with the same clock:

| `kind` | Record |
|---|---|
| `publish`, `control` | a frame between the device and Red Sea, both ways, decrypted |
| `http` | an HTTP request Home Assistant sent to the device: method, endpoint, status (0 = no answer), duration, payload; `origin` is `integration` or `poseidon` (its `/cloud` reads every 60 s) |
| `compare` | a pushed state against the next poll, each value `same`, `differs` or `unknown` |
| `mark` | the strategy or the pause changed |

A device in spy mode also gets a **Polling pause** switch: no request at all is
sent to it, Poseidon's `/cloud` reads included, so whatever it pushes then it
pushes on its own. The pause is not kept across a restart.

Suggested capture, per device (clocks of the Home Assistant hosts in sync, same
time zone):

1. 30 minutes with no polling at all: any other Home Assistant reading the
   device stopped, the pause on;
2. 30 minutes with the polling only (pause off);
3. actions at noted times: from the ReefBeat app, from Home Assistant, on the
   device itself;
4. if another Home Assistant polls the device, its requests can be added with
   the `logger.set_level` action, `custom_components.redsea.reefbeat.api:
   debug`.

## Settings

*Poseidon > Configure > Poseidon settings*

- **Default strategy**: the one of every device in Poseidon mode that has no
  strategy of its own (see [Strategies](#strategies)). *Spy* by default.
- **Polling interval of the Poseidon strategy**, in minutes (10 by default).
- **Debug mode**: every frame crossing the relay is written decrypted to
  `/config/redsea/poseidon/logs/poseidon.jsonl` (rotated at 10 MB, 5 files
  kept). The payloads are in clear in that file.
- **Delay before a device is silent**, in minutes (10 by default).
- **Safety polling interval**, in minutes (60 by default): the polling of a
  device whose pushed messages cover everything that changes, and how often the
  `/cloud` of a device exchanging through the relay is read.
- **Report unexpected messages** (on by default): see
  [Unexpected messages](#unexpected-messages).
- **Look for existing reports on GitHub** (on by default): only the signature
  of an unexpected message is sent.
- **Hold back the cloud's write commands at connection** (on by default): see
  [Guard at connection](#guard-at-connection).
- **Watchdog key**: 16 characters, proposed when none is set. A watchdog on
  another machine (standalone, or in
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup))
  asks the relay whether it is alive, and switches the devices back to normal
  mode when it is not. Copy this key into its configuration; leave it empty to
  answer no watchdog.

## Unexpected messages

Every message crossing the relay is checked against what is known of its device
family: an MQTT packet or topic nothing knows, a command of the cloud to an
unknown endpoint, a state or a telemetry with a new field, a missing one or
another type. The first occurrence goes to
`/config/redsea/poseidon/logs/anomalies.jsonl`, anonymised (ids, names,
network addresses, keys removed); an unknown command waits 5 seconds for what
the device answers and pushes, written with it.

Each one has a signature, the same for every user. The repository issues are
searched for it, and a repair issue tells what to do: report it (a GitHub issue
prefilled, sent only by you), follow the open report, update to the version
that handles it, or read the closed report. A new telemetry field only raises a
repair issue when the search found no report.

## Guard at connection

At every connection of a device, the Red Sea cloud sends it its own copy of the
device settings. When that copy is out of date, the device loses its current
ones: a ReefWave lost its whole schedule that way. For the first 30 seconds of
each connection through the relay, the write commands of the cloud are
therefore held back (its reads still pass).

The known restores (a ReefDose food head, a ReefWave group and schedule) are
held back silently. Any other write command held back raises a repair issue
listing it: if you changed something in the ReefBeat app at that very moment,
do it again.

## Events

### `redsea_dose`

Fired when a ReefDose in Poseidon mode (any strategy) ends a dose, scheduled or
manual, from its `dosing-log`. A dose pushed twice (after a reconnection) is
fired once.

| Field | Content |
|---|---|
| `device_id` | the device in Home Assistant |
| `name` | its name |
| `head` | head number |
| `supplement`, `brand` | as the device tells them |
| `dose_type` | `scheduled` or `manual` |
| `volume` | dosed volume, in mL |
| `started_at` | start of the dose, from the dosing queue polled before it (device local time); `null` for a dose that was not in it (manual from the app) |
| `ended_at` | end of the dose (device local time) |
| `duration_s` | `ended_at` − `started_at`, `null` without start |

Nothing is pushed when a dose starts: its start is the time the dosing queue
gave it.

### History of the doses

Every dose is also kept, per head, for 30 days (5000 doses at most), across
restarts:

- each head of a ReefDose gets a **Last dose** sensor (on the head device),
  available only while the doser is in Poseidon mode: its state is the end
  of the last dose, its attributes the volume, type, start, duration and
  supplement; the recorder keeps them as any sensor;
- the `redsea.get_doses` action returns the doses, newest first: `device_id`
  (the doser, one of its heads, or its config entry), and optionally `head`,
  `days`, `limit`;
- the ha-reef-card shows them in the configuration dialog of a head
  (**Dose history**).

```yaml
automation:
  - alias: Log the doses
    triggers:
      - trigger: event
        event_type: redsea_dose
    actions:
      - action: logbook.log
        data:
          name: "{{ trigger.event.data.name }}"
          message: >-
            head {{ trigger.event.data.head }}
            ({{ trigger.event.data.supplement }}):
            {{ trigger.event.data.volume }} mL,
            {{ trigger.event.data.dose_type }},
            {{ trigger.event.data.started_at }} → {{ trigger.event.data.ended_at }}
```

## Exporting and importing the keys

*Poseidon > Configure > Export the keys* gives a download link for every known
key, valid 5 minutes. The file is generated when you click, never written in
`/config`; it is in the format of the CLI (`keystore.json`) and holds the keys
in clear: keep it safe. The `redsea.poseidon_export` action, for automations,
writes the same file to `/config/redsea/poseidon/keystore-<date>.json`,
readable by its owner only.

*Poseidon > Configure > Import keys* asks for such a file and sends it from your
browser. A device is only replaced by a more recent record, devices without
keys are skipped, and the imported devices get their switch at once.

## Rescue script

*Poseidon > Configure > Rescue script* gives a download link (5 minutes) to
`poseidon_rescue.py`: a script that switches the devices back to the Red Sea
broker without Home Assistant, for when it cannot do it any more (down, relay
broken, integration removed). It runs on any computer on the devices' network
with Python 3.8 or later, nothing else to install:

```bash
python3 poseidon_rescue.py --dry-run   # what would be done, nothing changed
python3 poseidon_rescue.py             # devices on the relay, after a confirmation
```

| Option | Use |
|---|---|
| `--ip HWID=IP` | a device moved since the download |
| `--scan CIDR` | where to look for moved devices (repeatable) |
| `--no-scan` | never look for them |
| `--only HWID` | one device (hwid or name, repeatable) |
| `--all` | every device, whatever broker it points at |
| `--keystore keystore.json` | a keystore export instead of the embedded devices |
| `--yes` | no confirmation |

Nothing is written into a device before it proves to be the right one: its
`hwid`, read in `/device-info`, must match. A device that no longer answers at
its address, or whose address is now another device's, is looked for on the
network: the /24 of every known address and of the computer running the
script, or the `--scan` subnets.

Each device gets the same sequence as Home Assistant (disable, write the broker
and keys, enable), then `/cloud` is read again to check it. The script embeds
the keys in clear: keep it safe, and download it again after adding devices.
