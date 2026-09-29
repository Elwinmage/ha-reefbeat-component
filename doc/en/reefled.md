[← Back to the main page](../../README.md)

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

### Weather program
The lamp can follow the weather of a place: in **GPS weather mode** its week
is built from the weather of the next seven days (forecast) or of the seven
days that have just passed (measured weather), from
[Open-Meteo](https://open-meteo.com) (free, no key). There is nothing to
validate: turning the mode on keeps the lamp's own programs aside and sends
the weather week at once; the weather is then fetched again every few days
(3 to 15, your choice) and whenever a setting changes (30 s after the last
change). Turning the mode off writes the lamp's own programs back.

| Entity | Role |
| ------ | ---- |
| `switch` GPS weather mode | GPS weather, or the lamp's standard programs |
| `select` Weather period | Next week (forecast) or last week (measured) |
| `number` Weather refresh (days) | Days between two weather fetches, 3 to 15 |
| `text` Weather location | `lat, lon`, a `geo:` URI or a Google Maps / OpenStreetMap / Apple Maps link; empty for the Home Assistant home |
| `select` Weather day on the tank | Place's clock, anchored on the sunrise, on the sunset, or stretched between both |
| `time` Weather sunrise / sunset | Tank times used by the anchors |
| `number` Weather minimum / maximum intensity | Guard rails of the intensity |
| `switch` Weather clouds | Set the lamp's clouds on the cloudy hours |
| `sensor` Weather program | Result of the last fetch (status, place, and each day's sun, sunshine, cloud cover and top intensity) |

How a day is built:
- **Times** — from the place's sunrise to its sunset, on the place's clock
  (a reef in Fiji rises at 06:00 on the lamp too), or anchored on the tank:
  *sunrise* (the place's day starts at the chosen time), *sunset* (it ends
  at the chosen time), or *both* (the place's day is stretched between the
  two times).
- **Intensity** — follows the sun actually received (hourly shortwave
  radiation, 1000 W/m² being full sun), between the minimum and the maximum;
  up to 8 points a day.
- **Colour** — the one of the lamp's standard program at the same moment of
  its day: its white/blue balance on a G1, its colour temperature on a G2.
- **Clouds** — on the hours with at least 40 % cloud cover: Low, Medium or
  High from their mean cover; removed on a clear day.
- **Moon** — keeps its place after the sunset.

The program is named *Weather* on the lamp. A virtual LED writes each of its
lamps, in its own format. In weather mode, the `redsea.led_weather_apply`
service fetches the weather again at once (from an automation, say).

***

### Maintenance tasks
| Task | Default | Range |
| ---- | ------- | ----- |
| Clean lens | 3 weeks | 1 – 5 weeks |
| Dust the fan and grilles | 6 months | 5 – 7 months |

The same two tasks are created for every ReefLED generation, including the
[virtual LED](virtual-led.md#virtual-led).
See the [Maintenance](maintenance.md#maintenance) section.

---

[← Back to the main page](../../README.md)
