[← Back to the main page](../../README.md)

# Cloud API
The Cloud API allows you to:
- Launch or stop shortcuts: emergency, maintenance and feeding,
- Get user information,
- Retrieve the waves library,
- Retrieve the supplements library,
- Retrieve the LED programs library,
- Be notified of a [new firmware version](../../README.md#firmware-update),
- Send commands to ReefWave when "[Cloud or Hybrid](reefwave.md#reefwave)" mode is selected.

Shortcuts, wave parameters and LED parameters are sorted by aquarium.
<p align="center">
<img src="../img/cloud_api_devices.png" alt="Image">
<img src="../img/cloud_ctrl.png" alt="Image">
<img src="../img/cloud_api_supplements.png" alt="Image">
<img src="../img/cloud_api_sensors.png" alt="Image">
<img src="../img/cloud_api_led_and_waves.png" alt="Image">
<img src="../img/cloud_api_conf.png" alt="Image">
</p>

>[!TIP]
> You can disable fetching the supplements list in the Cloud API device configuration.
>    <img src="../img/cloud_config.png" alt="Image">

>[!TIP]
> **Simulator.** To use the simulated account of a
> [reefbeat-devices-simulator](https://github.com/Elwinmage/reefbeat-devices-simulator)
> (its lamps and their light programs library, without touching your real
> account), create the local flag file (git-ignored, never commit it):
> ```bash
> cp custom_components/redsea/simulator_enabled.example custom_components/redsea/.simulator_enabled
> ```
> Restart Home Assistant: the account form then also asks for the **cloud
> server** (`cloud.reef-beat.com` by default). Give the simulator's address
> (its `CLOUD` device, e.g. `192.168.0.251`); any credentials are accepted.
***

---

[← Back to the main page](../../README.md)
