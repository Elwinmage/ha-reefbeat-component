# Red Sea (ReefBeat devices) 🐠
> Part of the [**ReefTech Project Ecosystem**](https://elwinmage.github.io/reeftank/)
<p align="center">
  <img src="icon.png"  width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
![Installations](https://img.shields.io/badge/dynamic/json?label=Active%20Installs&query=estimated&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-reefbeat-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)

[![Ruff Status](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" width="5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" width="5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" width="5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" width="5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" width="5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" width="5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" width="5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)
To help us with translation, follow this [guide](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Overview
***HomeAssistant RedSea Reefbeat devices Local Management (no cloud): ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun and ReefWave***

<!-- ecosystem:start -->

## Related projects

The ReefTech projects fit together: the integrations bring your equipment into Home Assistant, the card displays and drives it, and the backup keeps it running through an outage. Each one also works on its own.

<table>
  <tr>
    <th width="100px"></th>
    <th>Project</th>
    <th>What it does</th>
    <th>Works with</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td>🐠<br /><b>ha-reefbeat-component</b><br /><i>(this repository)</i></td>
    <td>Red Sea ReefBeat devices, controlled locally with no cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun and ReefWave.<br />alert blueprint for abnormal modes, calibrations and low battery. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td>🌊<br /><a href="https://github.com/Elwinmage/ha-aquamedic-component"><b>ha-aquamedic-component</b></a></td>
    <td>Aqua Medic pumps through the Gizwits cloud API: EcoDrift and SmartDrift wavemakers, DC Runner return and skimmer pumps.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td>🐙<br /><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Cleaning and wear tracking for the equipment Home Assistant cannot talk to: flow pumps, return pumps, skimmers, media reactors, anything you service by hand.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td>🪸<br /><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Interactive graphical view of each device on your dashboard, and the only way to edit advanced schedules. Reads the three integrations above through the shared <code>reef_role</code> contract, with no card-side configuration.</td>
    <td>all three integrations</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-blueprints/main/icon.png" width="64" alt="ha-reef-blueprints" /></td>
    <td>🐬<br /><a href="https://github.com/Elwinmage/ha-reef-blueprints"><b>ha-reef-blueprints</b></a></td>
    <td>Notification blueprints shared by the whole ecosystem: overdue maintenance found through the <code>reef_role</code> contract, and devices that went unreachable. Eight languages.</td>
    <td>all three integrations</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td>⚡<br /><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Battery backup for power outages. A 24V LiFePO₄ pack driven by a Raspberry Pi, with pump speed degraded progressively according to the state of charge.</td>
    <td>standalone, or alongside ha-reefbeat-component</td>
  </tr>
</table>

All of them are documented together on the [ReefTech project page](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

> [!TIP]
> The list of future implementations can be found [here](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> The list of bugs can be found [here](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***If you need other sensors or actuators, feel free to contact me [here](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> If your devices are not on the same subnet as your Home Assistant, please [read this](https://github.com/Elwinmage/ha-reefbeat-component/#my-device-is-not-detected).

> [!CAUTION]
> ⚠️ This is not an official RedSea repository. Use at your own risk.⚠️

# Compatibility

> ✅ Supported &nbsp;|&nbsp; 🚧 In progress &nbsp;|&nbsp; 🧪 Untested (may work) &nbsp;|&nbsp; ❌ Not yet supported
>
> Own a device marked 🧪? Please confirm it works [here](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8).
<table>
<th>
<td colspan="2"><b>Model</b></td>
<td colspan="2"><b>Status</b></td>
<td><b><a href="https://github.com/Elwinmage/reefbeatEnergyBackup">EnergyBackup</a></b></td>
<td><b>Issues</b> <br/>📆(Planned) <br/> 🐛(Bugs)</td>
</th>
<tr>
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefato.md#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="doc/img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefcontrol.md#reefcontrol">ReefControl</a></td>
<td colspan="2">RSCONTROLPRO</td><td>✅</td>
<td width="200px"><img src="doc/img/RSCONTROLPRO.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSCONTROLLITE</td><td>🧪</td>
<td width="200px"><img src="doc/img/RSCONTROLLITE.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefcontrol-power.md#reefcontrol-power">ReefControl-Power</a></td>
<td colspan="2">RSPOWER6</td><td>✅</td>
<td width="200px"><img src="doc/img/RSPOWER6.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSPOWER8</td><td>🧪</td>
<td width="200px"><img src="doc/img/RSPOWER8.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefdose.md#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
<td width="200px"><img src="doc/img/RSDOSE2.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="doc/img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"> <a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefled.md#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="doc/img/rsled_g1.png"/></td>
<td align="center" rowspan="6">–</td>
<td rowspan="6">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,RSLED90,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td>RSLED90</td>
<td>✅</td>
</tr>
<tr>
<td>RSLED160</td><td>✅ </td>
</tr>
<tr>
<td rowspan="3">G2</td>
<td>RSLED60</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="doc/img/rsled_g2.png"/></td>
</tr>
<tr>
<td>RSLED115</td><td>✅ </td>
</tr>
<tr>
<td>RSLED170</td><td>🧪</td>
</tr>
<tr>
<td rowspan="3"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefmat.md#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="doc/img/RSMAT.png"/></td>
<td align="center" rowspan="3">–</td>
<td rowspan="3">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSMAT500</td><td>✅</td>
</tr>
<tr>
<td colspan="2">RSMAT1200</td><td>✅ </td>
</tr>
<tr>
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefrun.md#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="doc/img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefwave.md#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>✅</td>
<td width="200px" rowspan="2"><img src="doc/img/RSWAVE.png"/></td>
<td align="center" rowspan="2">✅</td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSWAVE45</td><td>✅</td>
</tr>
</table>

(*) ReefWave users, please read [this](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefwave.md#reefwave)

# Summary
- [Installation via HACS](https://github.com/Elwinmage/ha-reefbeat-component/#installation-via-hacs)
- [Common functions](https://github.com/Elwinmage/ha-reefbeat-component/#common-functions)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefato.md#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefcontrol.md#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefcontrol-power.md#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefdose.md#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefled.md#reefled)
- [Virtual LED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/virtual-led.md#virtual-led)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefmat.md#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefrun.md#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefwave.md#reefwave)
- [Maintenance](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/maintenance.md#maintenance)
- [Cloud API](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/cloud-api.md#cloud-api)
- [FAQ](https://github.com/Elwinmage/ha-reefbeat-component/#faq)

# Installation via HACS

## Direct installation

Just click here to directly go to the repository in HACS and click "Download": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

For the companion card ha-reef-card offering advanced and ergonomic features, click here to directly go to the repository in HACS and click "Download": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Find in HACS
Or search for "redsea" or "reefbeat" in HACS.

<p align="center">
<img src="doc/img/hacs_search.png" alt="Image">
</p>

# Common functions

# Icons
This integration provides custom icons accessible via "redsea:icon-name":

<img src="doc/img/redsea-icons.png"/>

## Add device
When adding a new device you have 4 choices:

<p align="center">
<img src="doc/img/add_devices_main.png" alt="Image">
</p>

### Add Cloud API
***Mandatory for ReefWave if you want to keep it synchronized with the ReefBeat Mobile App*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/en/reefwave.md#reefwave)). <br />
***Mandatory to be notified of a new firmware version*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update)).
- Get user information
- Get aquariums
- Get Waves library
- Get LED library

<p align="center">
<img src="doc/img/add_devices_cloud_api.png" alt="Image">
</p>

### Auto detect on private network
If not on the same network, read [this](#my-device-is-not-detected) and use ["Manual Mode"](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).
<p align="center">
<img src="doc/img/auto_detect.png" alt="Image">
</p>

### Manual Mode
You can enter your device IP address or the network address for auto-detection.

<p align="center">
<img src="doc/img/add_devices_manual.png" alt="Image">
</p>

## Device Config

Right-click a device (or open its options from the integration page) to reach its configuration. The first screen lets you change how the integration talks to the device.

<p align="center">
<img src="doc/img/configure_device_1.png" alt="Image">
</p>

### Set scan interval for device

Set how often (in seconds) the integration polls the device for new data.

<p align="center">
<img src="doc/img/configure_device_2.png" alt="Image">
</p>

### Change WiFi network

You can move a device to another WiFi network directly from Home Assistant, without going back to the ReefBeat app.

From the device configuration menu, choose **Change WiFi network**. The integration asks the device to scan for nearby networks and shows them in a drop-down, sorted by signal strength. The network the device is currently connected to is pre-selected, so if you only need to update the password you can leave the selection as-is.

<p align="center">
<img src="doc/img/device_cfg.png" alt="Image">
</p>

Pick the target network, enter its password, and submit. The integration sends the new credentials to the device, reboots it, and then automatically looks for it again on the network to update its IP address.

<p align="center">
<img src="doc/img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> After a WiFi change the device may join a different subnet (for example moving from `192.168.0.x` to `10.0.0.x`). The integration scans every subnet Home Assistant is directly connected to. If the device lands on a subnet that Home Assistant can only reach through a router, rediscovery will fail and you will be asked to enter the target subnet manually (for example `10.0.0.0/24`).

## Live update

> [!NOTE]
> It is possible to choose whether to enable live_update_config or not. In this mode (old default), configuration data is continuously retrieved along with normal data. For RSDOSE or RSLED, these large HTTP requests can take a long time (7–9 seconds). Sometimes the device does not respond to the request, so a retry function has been implemented. When live_update_config is disabled, configuration data is only retrieved at startup and when requested via the "Fetch Configuration" button. This new mode is activated by default. You can change it in the device configuration. <p align="center">
<img src="doc/img/configure_device_live_update_config.png" alt="Image">
<img src="doc/img/fetch_config_button.png" alt="Image">
</p>

> [!NOTE]
> Every device also exposes a "Fetch data" button. It forces an immediate read of the polled sources instead of waiting for the next scan interval, and works whatever the Live update config setting is — unlike "Fetch config", which only refreshes the configuration sources.

## Firmware Update
You can be notified and update your device when a new firmware version is available. You must have an active ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) device with your credentials and the "Use Cloud API" switch must be enabled.
> [!TIP]
> The "Cloud API" is only needed to get the version number of the new release and compare it to the installed version. To update your firmware, the Cloud API is not strictly required.
> If you do not use the "Cloud API" (switch disabled or no Cloud API device installed), you will not be alerted when a new version is available, but you can still use the hidden "Force Firmware Update" button. If a new version is available, it will be installed.
<p align="center">
  <img src="doc/img/firmware_update_1.png" alt="Image">
  <img src="doc/img/firmware_update_2.png" alt="Image">
</p>


# FAQ

## My device is not detected
- Try relaunching the auto-detection with the "Add entry" button. Sometimes devices do not respond because they are busy.
- If your Red Sea devices are not on the same subnet as your Home Assistant, auto-detection will first fail and then offer you the option to enter the IP address of your device or the address of the subnet where your devices are located. For subnet detection, please use the format IP/MASK, for example: 192.168.14.0/255.255.255.0.
- You can also use [Manual Mode](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).

<p align="center">
<img src="doc/img/subnetwork.png" alt="Image">
</p>

## Some data are updated correctly but others are not
Data is divided into three parts: data, configuration and device-info.
- Data is regularly updated.
- Configuration data is only updated at startup and when you press the "Fetch Config" button.
- Device-info data is only updated at boot.

To ensure that configuration data is updated regularly, please enable [Live Configuration Update](#live-update).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
[ruff-shield]: https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/ruff.yml/badge.svg
[ruff-link]: https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/ruff.yml
[pyright-shield]: https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/pyright.yml/badge.svg
[pyright-link]: https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/pyright.yml
[coverage-shield]: https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/badges/coverage.svg
[coverage-link]: https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component
