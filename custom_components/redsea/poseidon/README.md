# Poseidon mode — architecture

Poseidon mode puts a **transparent MQTT relay** between ReefBeat devices and
the Red Sea broker, inside the `redsea` integration. Devices keep talking to
the Red Sea cloud (the official app keeps working), but every frame crosses
Home Assistant, where it can be logged and — later — injected into the
coordinators to replace local polling.

It is the integration of the standalone `reefbeat_god_mode.py` tool (formerly
"god mode"), whose protocol work and switch sequence are validated on real
hardware. User documentation: [doc/en/poseidon.md](../../../doc/en/poseidon.md).

## Status

| Step | Content | State |
|---|---|---|
| 1 | Entry, relay, keystore, key capture, switches, lifecycle | done (lot A) |
| 2 | Debug log, silent devices, encrypted `is_alive`, settings | done (lot B) |
| 3 | Keystore export / import (CLI format) | done (lot C) |
| 4 | Standalone watchdog, then reefbeatEnergyBackup | to do |
| 5 | Strategies per device: `spy`, `shadow`, `poseidon` | done; mergers of pushed states: per family, from the spy files |

## Modules

```
poseidon/
├── __init__.py       entry setup / unload / remove, port-in-use issue
├── const.py          constants, model -> cloud type
├── crypto.py         AES-128-CBC payloads (from the CLI)
├── mqtt.py           frame parser and the few encoders needed
├── ports.py          free port search, local address
├── device_http.py    raw local HTTP, /cloud switch sequence
├── keystore.py       Store-backed keystore (CLI schema)
├── capture.py        snapshots, key capture, diff, RSRUN/RSWAVE restore
├── relay.py          asyncio relay, traffic timestamps, local sessions
├── watchdog.py       is_alive, served by the relay
├── debug.py          decrypted JSONL logs, rotated, written off the loop
├── strategy.py       comparisons, mergers, polling control
├── manager.py        the running Poseidon (hass.data["redsea_poseidon"])
├── switch_entity.py  per device: mode switch, polling pause, strategy select
├── flow.py           config / options flow steps (mixins)
├── http_view.py      downloads behind a signed link (keystore, rescue script)
└── rescue_script.py  standalone switch back, stdlib only (the downloaded script)
```

The manager is kept out of `hass.data[DOMAIN]`, whose values the integration
iterates as device coordinators.

## Key facts relied upon

- A device's broker is the `url` of its local `/cloud`. Switching uses the
  validated sequence `POST /cloud/disable` → `POST /cloud {url, api_key,
  api_secret}` → `POST /cloud/enable`; the firmware needs all three fields.
  The enable is sent even after a refused write, never to leave a device cut
  off.
- `GET /cloud` shows `api_key` in clear but masks `api_secret`: only the
  destructive cloud `DELETE /device/{hwid}` + `POST /device` returns it.
- A device bound to a local-only aquarium has no `api_key`: no Poseidon mode.
- The relay is a byte-for-byte passthrough; the CONNECT (`<type>-<hwid>`,
  password = `api_key`) reaches Red Sea untouched.

## Entry and options

- One entry, `unique_id = "poseidon"`, data: `port`, `host` (address written
  in the devices' `/cloud.url`), `cloud_account` (entry id).
- The proposed port is the first free one from 1884 (1883 and 8883 skipped),
  checked again on submit and at every start; taken at start → repair issue
  `poseidon_port_in_use` and `ConfigEntryNotReady`, devices untouched.
- Options (applied live, the relay is not restarted): `debug`,
  `silent_minutes` (10), `watchdog_key` (16 characters, proposed when unset),
  `strategy` (default, `spy`), `reduced_minutes` (10), `device_strategies`
  (`{hwid: strategy}`, written by the strategy select).

## Devices

- Keystore in `.storage/redsea.poseidon`, kept when the entry is removed.
- "Add devices" lists every local device with its live status: keys known,
  keys needed (🔑, warning + confirmation), already in Poseidon mode, no cloud
  credentials, not in the cloud account, unreachable.
- Capture, one device at a time: pending snapshot written once under
  `/config/redsea/poseidon/snapshots/<hwid>/` → delete / create in the cloud →
  keys stored → keys pushed (Red Sea broker) → snapshot again, diff → RSRUN
  and RSWAVE restored automatically, other families reported in a
  notification. The pending snapshot is dropped only when nothing is left to
  check. Then the device is switched to Poseidon mode.

## Switch

- `unique_id = poseidon_<hwid>`, attached to the device's own registry entry
  through `device_entry` (identifiers are only unique within a config entry,
  so `device_info` would create a device of its own). Only created for a
  device already in the registry; new ones are added without a reload.
- `is_on` = `/cloud.url` is the relay (`/cloud` is a config source: Poseidon
  reads it again every 60 s). No RestoreEntity.
- Attributes: `connection_state`, `last_up`, `last_down`, `silent`.
- `silent`: in Poseidon mode and nothing through the relay for
  `silent_minutes` (counted from the relay start at the earliest); raises the
  repair issue `poseidon_device_silent_<hwid>`, cleared when traffic resumes.
  A silent device is never switched by Home Assistant.

## Lifecycle rules

1. Poseidon mode is only ever entered manually (switch, add devices).
2. Automatic switches only go towards normal mode.
3. Entry disabled (`disabled_by` set at unload) or removed → every device in
   Poseidon mode back to normal mode; failures named in a notification.
4. Reload or Home Assistant restart → devices untouched.

## Watchdog protocol (`is_alive`)

The watchdog connects to the relay port with the reserved login
`poseidon-watchdog`; the relay serves that session itself (CONNACK, SUBACK,
PINGRESP, PUBACK for QoS 1).

| Topic | Payload (encrypted with the watchdog key) |
|---|---|
| `poseidon/is_alive` | `{"id", "ts", "minutes"}` |
| `poseidon/is_alive/response` | `{"id", "ts", "ok", "devices"}` |

- `ok`: at least one device exchanged frames with Red Sea in both directions
  within `minutes`.
- `devices`: every device in Poseidon mode, with `name`, `type`, `ip`,
  `api_key`, `api_secret`, `mqtt_url` (where to switch it back), `last_up`,
  `last_down`: the watchdog replays the full switch sequence.
- The key never goes on the wire; a request that does not decrypt gets no
  answer; the response repeats the request id. No key set → no answer.

Watchdog algorithm (step 4): every N minutes `is_alive(10)`; on failure wait
10 minutes and retry; still failing and the Red Sea broker reachable from the
watchdog → every cached device back to normal mode, then notify.

## Keystore export / import

- Export (options menu): an abort whose description holds a link to
  `GET /api/redsea/poseidon/keystore` (`http_view.py`), signed with
  `async_sign_path` for the user of the flow request, valid 5 minutes. The
  view requires auth (the signature counts), answers administrators only, and
  builds the JSON on each request (`Content-Disposition: attachment`,
  `Cache-Control: no-store`): nothing is written to disk.
- `redsea.poseidon_export` action (automations): writes
  `/config/redsea/poseidon/keystore-<YYYYmmdd-HHMMSS>.json`, created `0600`,
  and returns the path.
- Import (options menu): a `FileSelector` (`.json`), so the file comes from the
  browser through `file_upload` (a manifest dependency), read with
  `process_uploaded_file`, which deletes it afterwards. Merged by hwid: devices
  without keys skipped, a stored device only replaced by a more recent
  `updated_at` (compared as datetimes), keeping its known IP. Switches of the
  imported devices are created at once.

## Rescue script

`rescue_script.py`, standard library only (Python 3.8+), switches devices
back to the Red Sea broker without Home Assistant: the `/cloud` sequence of
`device_http.py`, then `/cloud` read again to check. Downloaded from the
options menu (`GET /api/redsea/poseidon/rescue`, same signed link and admin
check as the keystore): the view replaces its `EMBEDDED = None` line with the
relay address and every device with keys (`ip`, `api_key`, `api_secret`, and
`mqtt_url` already resolved to the normal broker). Without embedded devices
it takes `--keystore` (CLI format, relay unknown: a device is switched back
when it is not on its normal broker). Default: devices on the relay, after a
confirmation; `--dry-run`, `--all`, `--only`, `--ip HWID=IP`, `--yes`.
Nothing is written before the device at the address answers its own `hwid` in
`/device-info` (addresses change, and another device's keys would cut it off);
a device not found there is looked for in the /24 of every known address and
of the computer (default route, no packet sent), or the `--scan` subnets: 64
parallel `/device-info` probes, 1.5 s each, 4096 addresses at most.

## Strategies

Applied to each device while it is in Poseidon mode: its own strategy
(`device_strategies`, the **Poseidon strategy** select next to its switch),
or the default (`strategy`; earlier values `normal` / `reduced` read as
`spy` / `poseidon`). Every device not in Poseidon mode gets its own polling
back, and so do all of them when Poseidon stops.

- `spy`: polling unchanged. To `logs/spy.jsonl`, same clock for all:
  - every frame of the device, both directions (CLI format, `publish` /
    `control`);
  - `http`: every request sent to the device's address by any API instance
    of the integration (`reefbeat/api.py` observers, `origin:
    integration`) and by Poseidon itself (`device_http.py`, `origin:
    poseidon`, payloads left out: they carry the keys);
  - `compare`: each decrypted `state` (`device/<type>/<hwid>/state`), kept
    until the next poll of the device (a coordinator listener), every leaf
    looked up in the polled sources: a pushed path matches a polled one it is
    a suffix of, the closest wins; verdict `same` / `differs` / `unknown`;
  - `mark`: strategy or pause changed.

  **Polling pause** switch (spy only, not restored): `update_interval =
  None`, and no `/cloud` read by Poseidon either. Given back with a refresh,
  the only way to schedule the next poll again.
- `shadow`: polling unchanged. A pushed `state` goes through
  `merge_state(type, ...)` (`MERGERS`, per cloud device type); when merged,
  the coordinator listeners are told, without counting as a poll. Its
  comparison with the next poll goes to `logs/shadow.jsonl` with `merged`: a
  merger is right when nothing `differs`.
- `poseidon`: `update_interval` set to `reduced_minutes` (10). A pushed
  `state` is merged; a family without a merger gets
  `async_request_refresh` instead (at most every 5 s per device).
  `telemetry` triggers nothing.

`MERGERS` is empty: mergers are written per family from the spy files.

Capture protocol, per device (clocks in sync): 30 min paused with every other
reader stopped (what the device pushes on its own), 30 min polling only, then
timed actions (app, Home Assistant, device). Another Home Assistant polling the
same device can add its requests with `logger.set_level`
(`custom_components.redsea.reefbeat.api: debug`).

## Debug log

`/config/redsea/poseidon/logs/poseidon.jsonl`: every frame of every device,
whatever its strategy. Like `spy.jsonl` and `shadow.jsonl`: rotated at 10 MB
(5 files), created on the first record, CLI `ProxyLogger` format (`kind`
publish/control), payloads decrypted with the device's key, written by a
logging `QueueListener` thread.

## Out of scope

- Mirror mode (devices without a cloud aquarium, relay as the broker).
- Per-device watchdog fallback.
- Passive observation of the Red Sea broker or app credentials: closed, see
  `reefbeat_etat_des_lieux.md`.
