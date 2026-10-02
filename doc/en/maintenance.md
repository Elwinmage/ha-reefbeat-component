[← Back to the main page](../../README.md)

# Maintenance

Beyond driving the hardware, the integration keeps track of the **recurring
maintenance tasks** of your equipment: cleaning a skimmer venturi, replacing
dosing tubes, changing the ReefMat activated carbon, and so on. Home Assistant
does the remembering, so you no longer have to.

Tasks are attached to the device they belong to, and to the **sub-device** when
that is more precise: a ReefDose head, a ReefRun pump. A ReefRun exposes the
return-pump tasks on pump 1 and the skimmer tasks on pump 2, never the other way
round: the task list follows the pump type reported by the device.

## The three entities of a task

Every task creates three entities, all under the *Configuration* and
*Diagnostic* categories so they stay out of your main dashboard:

| Entity | Role |
| ------ | ---- |
| `button.<device>_<task>` | **Task done.** Pressing it stamps the current date as the last time you performed the task, and restarts the countdown. |
| `number.<device>_<task>_interval_<unit>` | **Interval.** How often the task should be repeated, in days, weeks or months depending on the task. |
| `switch.<device>_<task>_notify` | **Notifications.** Mutes the overdue alert for this single task without touching its schedule. |

The button is the entity that carries the state. Everything derived is exposed
as attributes, so one entity is enough to build a dashboard or an automation:

| Attribute | Meaning |
| --------- | ------- |
| `last_reset` | ISO-8601 date of the last press, or `null` if never done |
| `interval_days` | Current interval, always normalized in days |
| `days_left` | Days remaining, negative once overdue |
| `overdue` | `true` once `days_left` is negative |
| `reef_role` | `maint_<task_key>`, the stable marker used to discover tasks |

> [!TIP]
> `reef_role` is what makes the whole thing extensible: the card and the alert
> blueprint discover tasks by scanning for this attribute. A task added to a
> future release of the integration appears in both without any update on their
> side.

## Intervals

Default intervals follow Red Sea's own recommendations, taking the median of
the published range. Each task also defines a minimum and a maximum, enforced by
the `number` entity: you can adapt an interval to your tank load, but not set an
absurd value.

Intervals are shown in the unit that makes sense for the task (weeks for a
venturi, months for a rotor) and stored in days internally, so switching units
never loses precision.

## Persistence

Dates and intervals are stored by Home Assistant in
`.storage/redsea_maintenance_<entry_id>`, one file per config entry. They
survive restarts, integration reloads and device reboots, and are **never sent
to the Red Sea cloud**. Removing the config entry removes the file with it.

## The maintenance view of ha-reef-card

The companion card [ha-reef-card](https://github.com/Elwinmage/ha-reef-card)
gathers every task of the installation into a dedicated view, as if maintenance
were a device of its own: one progress bar per task, colored by remaining time,
sortable by equipment or by due date, with a button to mark a task as done, a
bell to mute it and an inline slider to change its interval.

<p align="center">
<img src="../img/maintenance_task.png" alt="Maintenance tasks in ha-reef-card">
</p>

## Notifications: the alert blueprint

The integration does not notify by itself, on purpose: who to notify, when and
how is your call. That job is handled by the **ReefBeat watch** blueprint
shipped with the repository, which also covers abnormal modes, overdue
calibrations, low battery and unreachable devices.

### Installation

Click the button below and confirm the import in Home Assistant:

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-reefbeat-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fredsea_alerts.en.yaml)

A French version is available as
[`redsea_alerts.fr.yaml`](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/blueprints/automation/redsea_alerts.fr.yaml).
Alternatively, copy the file into
`config/blueprints/automation/redsea_alerts/` and reload the automations.

Then create an automation from the blueprint:
*Settings → Automations & scenes → Create automation → Use a blueprint →
ReefBeat watch (redsea)*.

### Configuration

Only the first field is mandatory:

| Section | What it does |
| ------- | ------------ |
| **Notification targets** | The mobile devices to notify, picked from the device selector. The `notify.mobile_app_*` service is resolved for you. An optional Android notification channel can be set (default `ReefBeat`). |
| **Maintenance overdue** | Alerts when a task passes its due date. *Respect the per-task notification switches* (on by default) makes the automation obey the `switch.*_notify` entities, so muting a task in the card also silences the automation. |
| **Abnormal mode** | Alerts when a device leaves its expected mode. `off_grace_minutes` (5 by default) avoids false alerts during a feeding cycle or a short manual intervention. |
| **Calibration overdue** | ReefDose heads and ReefRun skimmer calibrations. |
| **Sensor calibration delay (RSRUN)** | Full-cup and overskimming sensors of the ReefRun skimmers. |
| **Device alert message** | Relays the alert messages sent by the devices themselves. |
| **Low battery** / **Device unreachable** | Self-explanatory. |

Every section can be turned off independently and has its own **exclusion list**,
so a device under test does not spam you while the others stay monitored. The
automation runs on a 5-minute cycle and picks up devices added or removed from
the integration at the next cycle, without editing anything.

> [!NOTE]
> The blueprint monitors **all** devices of the integration and their
> sub-devices. There is nothing to declare when you add a new ReefBeat device.

---

[← Back to the main page](../../README.md)
