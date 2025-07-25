[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default) 
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/commits/master)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=uniques-clones&query=uniques&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component) 
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Overview
RedSea: Reefled, ReefMat, ReefDose, ReefRun and ReefATO+ Local Management (no cloud)

***If someone have reefwave I ll try to integrate them too.***

***If you need other sensors or actuators let me know.***

This is not an official RedSea repository

Use at your own risk

# Installation via hacs 

## Direct installation

Just click here to directly go to the repository in HACS and click "Download": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)                         

## Find in HACS
Or search for "redsea" or "reefbeat" in hacs 

<p align="center">                                                                                                                                                                              
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/hacs_search.png" alt="Image">                                                                                       
</p> 


## Old way, manual installation in hacs
1) open HACS
2) go to custom repositories and add:
    https://github.com/Elwinmage/ha-reefbeat-component

# Hardware
## ReefLed:
  - Test with the RESLED 160  but may work with 50, 60, 90, 115 and 170 versions.

## ReefMat:
  - Test with ReefMat 1200 must work with all other versions

## ReefDose:
  - Test with ReefDose4 but may work with ReefdDose2

## ReefATO+:
  - Tested

## ReefRun:
  - Partially tested
  
# What works
## All devices:
 - Auto detect on private network (if on same network)
 - Set scan interval for device

<p align="center">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/auto_detect.png" alt="Image">
</p> 
<p align="center"> 
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/configure_device_1.png" alt="Image">
</p> 
<p align="center">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/configure_device_2.png" alt="Image">
</p> 
 
 - It is possible to choose whether to enable live_update_config or not. In this mode (old default), configuration data is continuously retrieved along with normal data. For RSDOSE or RSLED, these large http requests can take a long time (7-9 seconds). Sometimes the device does not respond to the request, so I had to coded a retry function. When live_update_config is disabled, configuration data is only retrieved at startup and when requested via the "fetch configuration" button. This new mode is activated by default. You can change it in the device configuration.
<p align="center">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/configure_device_live_update_config.png" alt="Image">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/fetch_config_button.png" alt="Image">
</p> 


 
## LED:
  - Get and Set White, Blue and Moon values (only for G1: RSLED50,RSLED90,RSLED160)
  - Get and Set Color Temperature, Intensity and Moon (all LEDS)
  - Manage acclimation. Acclimation settings are automaticaly enabled or disabled according to acclimation switch.
  - Manage moonphase. Moonphase settings are automaticaly enabled or disabled according to moonphase switch.
  - Set Manual Color Mode with or without duration
  - Get Fan and Temperature
  - Get name and value for progams (with clouds support) Only for G1 LEDS.

***

The support of Color Temperature for G1 LEDS take into account the specificity of each of the three models.
<p align="center">                                                                                                                                                                             
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## IMPORTANT THING

<b>The Kelvin/intensity interface of G2 lamps does not allow for full LED power.</b>

### G2 LIGHTS

Because this method ensures constant intensity across the entire color range, your LEDs do not utilize their full capacity in the middle. At 8.000K, the white channel is at 100% and the blue channel at 0% (the opposite at 23.000K). At 14.000K and with 100% intensity for G2 lights, the power of the white and blue channels is approximately 85%.
Here is the loss curve for the G2s.
<p align="center">                                                                                                                                                                             
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/intensity_factor.png" alt="Image">
</p>

### G1 LIGHTS

G1 LEDS use white and blue channel control, which allows for full power across the entire range, but not constant intensity without compensation.
That's why I implent intensity compensation. Because I only have RESL160, you can enable this option only for this kind of LEDS. 

If you want this option for RSLED50 or RSLED90 let me known but be aware that you have to make some measures.

<p align="center">                                                                                                                                                                             
<img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/intensity_compensation.png" alt="Image">
</p>

If you want to use the full power of your LED then disable intensity compensation (default).

In other words, an intensity of x% for 9.000K is not the same than at 23.000K or 15,000K.

Here is the power curve for the RSLED160 (0 is for full blue to  full white 200).
<p align="center">                                                                                                                                                                             
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsled160_power_curve.png" alt="Image">
</p>

If you enable intentisty compensation, the intensity of your light will be constant accross all kelvin values but in the middle of the range you will not use the full capacity of your LED (like G2 models). For RSL160, that's more than a 50% loss.

Also, don't be surprised to see the intensity factor exceed 100% for the G1s in White/Blue mode if you enable compensation. This is because you can harness the full power of your LEDs!


***

<p align="center">                                                                                                                                                                             
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsled_G1_ctrl.png" alt="Image">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsled_G1_sensors.png" alt="Image">
</p>
<p align="center">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsled_diag.png" alt="Image">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsled_g2_ctrl.png" alt="Image">
 </p> 

## Virtual Led :
- Group and manage LED with a virtual device (Create a vitual device from the integration panel, then use the configure button to link the leds).
- You can only use Kelvin and intensity to control your leds if you have G2 or a mix of G1 and G2.
- You can use both Kelvin/Intensity and White&Blue  if you have only G1


<p align="center">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/virtual_led_config_1.png" alt="Image">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/virtual_led_config_2.png" alt="Image">
</p> 
      
## ReefMat:
  - Auto advance switch (enable/disable)
  - Schedule advance
  - Custom advance value: let you select the value of roll advance
  - Manual Advance
  - Change the roll. <b>For a new full roll please set "roll diameter" to min (4.0cm). It will adjust the size according to your RSMAT version. For a started roll enter the value in cm.</b>
  - Two hidden parameters: model and position if you need to reconfigure your RSMAT
<p align="center">                                                                                                                                                                               
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsmat_ctr.png" alt="Image">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsmat_sensors.png" alt="Image">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsmat_diag.png" alt="Image">
</p>

## ReefDose:
  - Edit daily dose
  - Manual dose
  - Change and control container volume. Container Volume settigns is automaticaly enabled or disabled according to  volume controleur switch.
  - Enable/disable schedule per pump
<p align="center"> 
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsdose_ctrl.png" alt="Image">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsdose_sensors.png" alt="Image">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsdose_diag.png" alt="Image">
</p> 

## ReefATO+:
  - Auto_fill enable/disable
  - Manual fill
<p align="center">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsato.png" alt="Image">                                                                                       
</p> 

## ReefRun:
- <b>First try to set pump speed (without device it's not so simple :-) ). I use the first slot for scheduling speed pump (according to youtube they are 10). Using this probably break your scheulde if you have one.
If your pump speed is always the same I think it could do the job. If someone with a reefrun can contact me, we could propose a better support.</b>

<p align="center">
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsrun_1.png" alt="Image">
</p>
<p align="center">                                                                                                                                                                              
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsrun_2.png" alt="Image">
</p>
<p align="center">                                                                                                                                                                              
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsrun_3.png" alt="Image">
</p>


# What next?
## LED:
  - Set programs
  - Random  program creation
  - Daily program generation according to meteo of a specific place according to geographic coordinates

## ReefDose:
  - Implement scheduling edition
  
***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
