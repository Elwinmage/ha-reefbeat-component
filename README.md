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

<p align="center">                                                                                                                                                                               <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/auto_detect.png" alt="Image">                                                                                 </p> 
<p align="center">                                                                                                                                                                               <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/configure_device_1.png" alt="Image">                                                                          </p> 
<p align="center">                                                                                                                                                                               <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/configure_device_2.png" alt="Image">                                                                          </p> 
   

## LED:
  - Get and Set White, Blue and Moon values (only for G1: RSLED50,RSLED90,RSLED160)
  - Get and Set Color Temperature, Intensity and Moon (all LEDS)
  - Manage acclimation. Acclimation settings are automaticaly enabled or disabled according to acclimation switch.
  - Manage moonphase. Moonphase settings are automaticaly enabled or disabled according to moonphase switch.
  - Set Manual Color Mode with or without duration
  - Get Fan and Temperature
  - Get name and value for progams (with clouds support) Only for G1 LEDS.
  
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
- You can only use Kelvin and intensity to control your leds.


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
<p align="center">                                                                                                                                                                               <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/rsato.png" alt="Image">                                                                                       
</p> 

## ReefRun:
- <b>First try to set pump speed (without device it's not so simple :-) ). I use the first slot for scheduling speed pump (according to youtube they are 10). Using this probably break your scheulde if you have one.
If your pump speed is always the same I hitnk it could do the job. If someone with a reefrun can contact me, we could propose a better support.</b>

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
  - Set programs (and implement the daily prog button that do nothing yet)
  - Random  program creation
  - Daily program generation according to meteo of a specific place according to geographic coordinates

## ReefDose:
  - Implement scheduling edition
  
# Home Assitant Card
An example to display your led program.

<p align="center">                                                                                                                                                                              
  <img src="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/img/program.png" alt="Image">                                                                                       
</p> 


You need to install decluttering, config-template-card and apexcharts-card from HACS.

Don't forget to edit the entity name (sensor.rsledXXXXXXXX_YYY) to set your own.

<code>
decluttering_templates:
  reefled-auto:
    default:
      - icon: mdi:calendar
    card:
      type: custom:config-template-card
      entities:
        - - - sensor
      card:
        type: custom:apexcharts-card
        header:
          show: true
          title: ${'[[day_name]] :\ '+states[ '[[sensor]]' ].state}
          show_states: false
          colorize_states: false
        graph_span: 28h
        span:
          start: day
        series:
          - entity: '[[sensor]]'
            show:
              legend_value: false
            name: clouds
            type: area
            color: rgb(100,100,100)
            yaxis_id: clouds
            curve: stepline
            data_generator: >
              const now = new Date();   now.setHours(0,0,0,0);   const data=[];
              data.push([now.getTime(),0]); var intensity=0;
              switch(entity.attributes.clouds.intensity){
                case "Low": 
                  intensity = 1;
                  break;
                case "Medium":
                  intensity = 2;
                  break;
                case "High":
                  intensity = 3;
                  break;
                default:
                  intensity = 0;
                  }
              data.push([now.getTime()+60000*(entity.attributes.clouds.from%1440),intensity]);
              data.push([now.getTime()+60000*(entity.attributes.clouds.to%1440),0]);
              return data;
          - entity: '[[sensor]]'
            show:
              legend_value: false
            name: white
            color: rgb(200,200,200)
            yaxis_id: power
            data_generator: >
              const now = new Date();  now.setHours(0,0,0,0); const data = [];
              data.push([now.getTime(),0]);
              data.push([now.getTime()+60000*(entity.attributes.data.white.rise%1440),0]);
              for (var point in entity.attributes.data.white.points){
                data.push([now.getTime()+60000*(entity.attributes.data.white.points[point].t+entity.attributes.data.white.rise%1440),entity.attributes.data.white.points[point].i]);
                }
              data.push([now.getTime()+60000*(entity.attributes.data.white.set%1440),0]);
              return data;
          - entity: '[[sensor]]'
            show:
              legend_value: false
            name: blue
            color: rgb(100,100,250)
            yaxis_id: power
            data_generator: >
              const now = new Date(); now.setHours(0,0,0,0); const data = [];
              data.push([now.getTime(),0]);
              data.push([now.getTime()+60000*(entity.attributes.data.blue.rise%1440),0]);
              for (var point in entity.attributes.data.blue.points){
                data.push([now.getTime()+60000*(entity.attributes.data.blue.points[point].t+entity.attributes.data.blue.rise%1440),entity.attributes.data.blue.points[point].i]);
                }
              data.push([now.getTime()+60000*(entity.attributes.data.blue.set%1440),0]);
              return data;
          - entity: '[[sensor]]'
            show:
              legend_value: false
            name: moon
            color: rgb(250,100,250)
            yaxis_id: power
            data_generator: >
              const now = new Date(); now.setHours(0,0,0,0); const data = [];
              data.push([now.getTime(),0]);
              data.push([now.getTime()+60000*(entity.attributes.data.moon.rise%1440),0]);
              for (var point in entity.attributes.data.moon.points){
                data.push([now.getTime()+60000*(entity.attributes.data.moon.points[point].t+entity.attributes.data.moon.rise%1440),entity.attributes.data.moon.points[point].i]);
                }
              data.push([now.getTime()+60000*(entity.attributes.data.moon.set%1440),0]);
              return data;
        yaxis:
          - id: clouds
            min: 0
            max: 3
            opposite: true
            apex_config:
              tickAmount: 3
              title:
                text: Cloud Cover Intensity
          - id: power
            min: 0
            max: 100
views:
  - title: Home
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Nouvelle section
          - type: entities
            entities:
              - entity: switch.rsledXXXXXXXX_daily_prog
                name: Programmation journalière
          - type: conditional
            conditions:
              - condition: state
                entity: switch.rsledXXXXXXXX_daily_prog
                state: 'on'
            card:
              type: custom:decluttering-card
              template: reefled-auto
              variables:
                - sensor: sensor.rsledXXXXXXXX_lundi
                - day_name: Tous les jours
          - type: conditional
            conditions:
              - condition: state
                entity: switch.rsledXXXXXXXX_daily_prog
                state_not: 'on'
            card:
              type: custom:layout-card
              layout_type: custom:masonry-layout
              cards:
                - type: custom:decluttering-card
                  template: reefled-auto
                  variables:
                    - sensor: sensor.rsledXXXXXXXX_monday
                    - day_name: Monday
                - type: custom:decluttering-card
                  template: reefled-auto
                  variables:
                    - sensor: sensor.rsledXXXXXXXX_thuesday
                    - day_name: Thuesday
                - type: custom:decluttering-card
                  template: reefled-auto
                  variables:
                    - sensor: sensor.rsledXXXXXXXX_wednesday
                    - day_name: Wednesday
                - type: custom:decluttering-card
                  template: reefled-auto
                  variables:
                    - sensor: sensor.rsledXXXXXXXX_thrusday
                    - day_name: Thursday
                - type: custom:decluttering-card
                  template: reefled-auto
                  variables:
                    - sensor: sensor.rsledXXXXXXXX_friday
                    - day_name: Friday
                - type: custom:decluttering-card
                  template: reefled-auto
                  variables:
                    - sensor: sensor.rsledXXXXXXXX_saturday
                    - day_name: Saturday
                - type: custom:decluttering-card
                  template: reefled-auto
                  variables:
                    - sensor: sensor.rsledXXXXXXXX_sunday
                    - day_name: Sunday
</code>

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
