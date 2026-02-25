[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/commits/main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/badges/coverage.svg)]()
[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

<!-- [![Clones GitHub](https://img.shields.io/badge/dynamic/json?color=success&label=uniques-clones&query=uniques&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge) -->
# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)
To help us translate, follow this [guide](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Overview
***HomeAssistant RedSea Reefbeat devices Local Management (no cloud): ReefATO+, ReefDose, ReefLed, ReefMat, ReefRun and ReefWave***

> [!TIP]
> ***To edit advanced schedules for ReefDose, ReefLed, ReefRun and ReefWave, you need to use the [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) (currently under development)***

> [!TIP]
> The list of future implementations can be found [here](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> The list of bugs can be found [here](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***If you need other sensors or actuators, feel free to contact me [here](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> If your devices are not on the same subnet as your Home Assistant, please [read this](https://github.com/Elwinmage/ha-reefbeat-component/#my-device-is-not-detected).

> [!CAUTION]
> ⚠️ This is not an official RedSea repository. Use at your own risk.⚠️

# Compatibility

✅ Tested ☑️ Must Work (If you have one, can you confirm it's working [here](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8)) ❌ Not Supported Yet
<table>
<th>
<td colspan="2"><b>Model</b></td>
<td colspan="2"><b>Status</b></td>
<td><b>Issues</b> <br/>📆(Planned) <br/> 🐛(Bugs)</td>
</th>
<tr>
<td><a href="#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td><a href="#reefcontrol">ReefControl</a></td>
<td colspan="2">RSSENSE<br />If you have one, contact me <a href="https://github.com/Elwinmage/ha-reefbeat-component/discussions/8">here</a> and I will add its support.</td><td>❌</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROL.png"/></td>
<td>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE2.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"> <a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
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
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g2.png"/></td>
</tr>
<tr>
<td>RSLED115</td><td>✅ </td>
</tr>
<tr>
<td>RSLED170</td><td>☑️</td>
</tr>
<tr>
<td rowspan="3"><a href="#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSMAT.png"/></td>
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
<td><a href="#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>☑️</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSWAVE45</td><td>✅</td>
</tr>
</table>

(*) ReefWave users, please read [this](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)

# Summary
- [Installation via HACS](https://github.com/Elwinmage/ha-reefbeat-component/#installation-via-hacs)
- [Common functions](https://github.com/Elwinmage/ha-reefbeat-component/#common-functions)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/#reefcontrol)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/#reefled)
- [Virtual LED](https://github.com/Elwinmage/ha-reefbeat-component/#virtual-led)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)
- [Cloud API](https://github.com/Elwinmage/ha-reefbeat-component/#cloud-api)
- [FAQ](https://github.com/Elwinmage/ha-reefbeat-component/#faq)

# Installation via HACS

## Direct installation

Just click here to directly go to the repository in HACS and click "Download": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

For the companion card ha-reef-card offering advanced and ergonomic features, click here to directly go to the repository in HACS and click "Download": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Find in HACS
Or search for "redsea" or "reefbeat" in HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Image">
</p>

# Common functions

# Icons
This integration provides custom icons accessible via "redsea:icon-name":

<img src="doc/img/icons_feeding_maintenance.png"/>
<img src="doc/img/icons_devices.png"/>

## Add device
When adding a new device you have 4 choices:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Image">
</p>

### Add Cloud API
***Mandatory for ReefWave if you want to keep it synchronized with the ReefBeat Mobile App*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)). <br />
***Mandatory to be notified of a new firmware version*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update)).
- Get user information
- Get aquariums
- Get Waves library
- Get LED library

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Image">
</p>

### Auto detect on private network
If not on the same network, read [this](#my-device-is-not-detected) and use ["Manual Mode"](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Image">
</p>

### Manual Mode
You can enter your device IP address or the network address for auto-detection.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Image">
</p>

### Set scan interval for device

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Image">
</p>

## Live update

> [!NOTE]
> It is possible to choose whether to enable live_update_config or not. In this mode (old default), configuration data is continuously retrieved along with normal data. For RSDOSE or RSLED, these large HTTP requests can take a long time (7–9 seconds). Sometimes the device does not respond to the request, so a retry function has been implemented. When live_update_config is disabled, configuration data is only retrieved at startup and when requested via the "Fetch Configuration" button. This new mode is activated by default. You can change it in the device configuration. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Image">
</p>

## Firmware Update
You can be notified and update your device when a new firmware version is available. You must have an active ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) device with your credentials and the "Use Cloud API" switch must be enabled.
> [!TIP]
> The "Cloud API" is only needed to get the version number of the new release and compare it to the installed version. To update your firmware, the Cloud API is not strictly required.
> If you do not use the "Cloud API" (switch disabled or no Cloud API device installed), you will not be alerted when a new version is available, but you can still use the hidden "Force Firmware Update" button. If a new version is available, it will be installed.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Image">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Image">
</p>


# ReefATO:
- Auto-fill enable/disable
- Manual fill
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Image">
</p>

# ReefControl:
Not supported yet. If you have one, contact me [here](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8) and I will add its support.

# ReefDose:
- Edit daily dose
- Manual dose
- Add and remove supplements
- Edit and control container volume. Container volume settings are automatically enabled or disabled according to the volume control switch.
- Enable/disable schedule per pump
- Stock alert configuration
- Dosing delay between supplements
- Priming (Please read [this](https://github.com/Elwinmage/ha-reefbeat-component/#calibration-and-priming))
- Calibration (Please read [this](https://github.com/Elwinmage/ha-reefbeat-component/#calibration-and-priming))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Image">
</p>

### Main
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Image">
</p>

### Heads
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Image">
</p>

#### Calibration and Priming

> [!CAUTION]
> You must strictly follow the order below (Using the [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) is safer).<br /><br />
> <ins>Calibration</ins>:
>  1. Place the graduated container and press "Start Calibration"
>  2. Enter the measured value using the "Dose of Calibration" field
>  3. Press "Set Calibration Value"
>  4. Empty the graduated container and press "Test new Calibration". If the value obtained is not 4 mL, go back to step 1.
>  5. Press "Stop and Save Graduation"
>
> <ins>For priming</ins>:
>  1. (a) Press "Start Priming"
>  2. (b) When the liquid flows out, press "Stop Priming"
>  3. (1) Place the graduated container and press "Start Calibration"
>  4. (2) Enter the measured value using the "Dose of Calibration" field
>  5. (3) Press "Set Calibration Value"
>  6. (4) Empty the graduated container and press "Test new Calibration". If the value obtained is not 4 mL, go back to step 1.
>  7. (5) Press "Stop and Save Graduation"
>
> ⚠️ Priming must always be followed by a calibration (steps 1 to 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Image">
</p>

# ReefLED:

- Get and Set White and Blue channels (only for G1: RSLED50, RSLED90, RSLED160)
- Get and Set Color Temperature, Intensity and Moon (all LEDs)
- Manage acclimation. Acclimation settings are automatically enabled or disabled according to the acclimation switch.
- Manage moon phase. Moon phase settings are automatically enabled or disabled according to the moon phase switch.
- Set Manual Color Mode with or without duration.
- Get Fan and Temperature values.
- Get name and value for programs (with cloud support). Only for G1 LEDs.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Image">
</p>

***

Color Temperature support for G1 LEDs takes into account the specificities of each of the three models.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## IMPORTANT for G1 and G2 LIGHTS

### G2 LIGHTS

#### Intensity
Because G2 LEDs ensure constant intensity across the entire color range, your LEDs do not utilize their full capacity in the middle of the spectrum. At 8,000K, the white channel is at 100% and the blue channel at 0% (the opposite at 23,000K). At 14,000K with 100% intensity for G2 lights, the power of the white and blue channels is approximately 85%.
Here is the loss curve for the G2s.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
</p>

#### Color Temperature
The G2 interface does not support the entire temperature range. From 8,000K to 10,000K, values are incremented in 200K steps, and from 10,000K to 23,000K in 500K steps. This behavior is handled automatically: if you choose an invalid value (e.g. 8,300K), a valid value will be automatically selected (8,200K in this example). This is why you may sometimes observe a slight cursor adjustment when selecting the color on a G2 light — the cursor repositions itself to an allowed value.

### G1 LIGHTS

G1 LEDs use white and blue channel control, which allows full power across the entire range, but not constant intensity without compensation.
That is why intensity compensation has been implemented.
This compensation ensures you get the same [PAR](https://en.wikipedia.org/wiki/Photosynthetically_active_radiation) (light intensity) regardless of your color temperature choice (in the range 12,000 to 23,000K).
> [!NOTE]
> Because Red Sea does not publish PAR values below 12,000K, compensation is only available in the 12,000 to 23,000K range. If you have a G1 LED and a PAR meter, you can [contact me](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) to add compensation for the full range (9,000 to 23,000K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

In other words, without compensation, an intensity of x% at 9,000K does not provide the same PAR as at 23,000K or 15,000K.

Here are the power curves:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

If you want to use the full power of your LED, disable intensity compensation (default).

If you enable intensity compensation, the light intensity will be constant across all color temperature values, but in the middle of the range you will not use the full capacity of your LEDs (as with G2 models).

Also note that if compensation is enabled, the intensity factor can exceed 100% for G1 lights if you manually adjust the White/Blue channels. This allows you to harness the full power of your LEDs!

***

# Virtual LED
- Group and manage LEDs with a virtual device (create a virtual device from the integration panel, then use the configure button to link the LEDs).
- You can only use Kelvin and intensity to control your LEDs if you have G2 or a mix of G1 and G2.
- You can use both Kelvin/Intensity and White & Blue if you have only G1 lights.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

# ReefMat:
- Auto advance switch (enable/disable)
- Schedule advance
- Custom advance value: lets you select the value of the roll advance
- Manual advance
- Change the roll.
>[!TIP]
> For a new full roll, please set "roll diameter" to the minimum (4.0 cm). The size will be adjusted according to your RSMAT version. For a partially used roll, enter the value in cm.
- Two hidden parameters: model and position, if you need to reconfigure your RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Image">
</p>

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

# ReefWave:
> [!IMPORTANT]
> ReefWave devices are different from other ReefBeat devices. They are the only devices that are slaves to the ReefBeat cloud.<br/>
> When you launch the ReefBeat mobile app, the status of all devices is queried and data from the ReefBeat app is retrieved from device state.<br/>
> For ReefWave, it is the opposite: there is no local control point (as you can see in the ReefBeat app, you cannot add a ReefWave to a disconnected aquarium).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
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
First create a ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) device with your credentials, and that's it!
The "Linked to account" sensor will be updated with the name of your ReefBeat account once the connection is established.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Changing current values
To load current wave values into the preview fields, use the "Set Preview From Current Wave" button.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
To change the current wave values, set the preview values and use the "Save Preview" button.

The behavior is the same as the ReefBeat mobile app. All waves with the same ID in the current schedule will be updated.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

# Cloud API
The Cloud API allows you to:
- Launch or stop shortcuts: emergency, maintenance and feeding,
- Get user information,
- Retrieve the waves library,
- Retrieve the supplements library,
- Retrieve the LED programs library,
- Be notified of a [new firmware version](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update),
- Send commands to ReefWave when "[Cloud or Hybrid](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)" mode is selected.

Shortcuts, wave parameters and LED parameters are sorted by aquarium.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Image">
</p>

>[!TIP]
> You can disable fetching the supplements list in the Cloud API device configuration.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Image">
***
# FAQ

## My device is not detected
- Try relaunching the auto-detection with the "Add entry" button. Sometimes devices do not respond because they are busy.
- If your Red Sea devices are not on the same subnet as your Home Assistant, auto-detection will first fail and then offer you the option to enter the IP address of your device or the address of the subnet where your devices are located. For subnet detection, please use the format IP/MASK, for example: 192.168.14.0/255.255.255.0.
- You can also use [Manual Mode](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Image">
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
