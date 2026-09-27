[← Back to the main page](../../README.md)

# ReefRun:
- Set pump speed
- Manage overskimming
- Manage full cup detection
- Can change skimmer model

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Image">
</p>

### Main
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Image">
</p>

### Pumps
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Image">
</p>

### Maintenance tasks
Tasks are attached to the pump sub-device and depend on its type.

| Task | Pump | Default | Range |
| ---- | ---- | ------- | ----- |
| Clean motor and rotor | Return | 4.5 months | 2 – 7 months |
| Clean intake strainer | Return | 6 weeks | 3 – 9 weeks |
| Clean venturi & air tube | Skimmer | 5 weeks | 3 – 7 weeks |
| Clean skimmer pump rotor | Skimmer | 4.5 months | 2 – 7 months |
| Calibrate fullcup sensor | Skimmer | 4 weeks | 2 – 6 weeks |
| Calibrate overskimming sensor | Skimmer | 4 weeks | 2 – 6 weeks |

The two calibration tasks are also watched by the alert blueprint, which
compares the last calibration date reported by the device with the interval you
set here. See the
[Maintenance](maintenance.md#maintenance) section.

### Impeller removal tool

The *Clean skimmer pump rotor* task above means unscrewing the pump body, which
offers almost nothing to grip once wet. A 3D-printable tool for that job, with a
video showing how it is used, is available here:
[Red Sea DC Skimmer impeller tool](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

---

[← Back to the main page](../../README.md)
