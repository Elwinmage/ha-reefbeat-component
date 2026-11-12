[← Back to the main page](../../README.md)

# ReefDose:
- Edit daily dose
- Manual dose
- Add and remove supplements
- Edit and control container volume. Container volume settings are automatically enabled or disabled according to the volume control switch.
- Enable/disable schedule per pump
- Stock alert configuration
- Dosing delay between supplements
- Priming (Please read [this](#calibration-and-priming))
- Calibration (Please read [this](#calibration-and-priming))
- [Dose regulation](#dose-regulation): assisted dosing and brine
- [History of the doses](poseidon.md#history-of-the-doses), in Poseidon mode

<p align="center">
<img src="../img/rsdose_devices.png" alt="Image">
</p>

### Main
<p align="center">
<img src="../img/rsdose_main_conf.png" alt="Image">
<img src="../img/rsdose_main_diag.png" alt="Image">
</p>

### Heads
<p align="center">
<img src="../img/rsdose_ctrl.png" alt="Image">
<img src="../img/rsdose_sensors.png" alt="Image">
<img src="../img/rsdose_diag.png" alt="Image">
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
  <img src="../img/calibration.png" alt="Image">
</p>

### Dose regulation

Each head has a **Dose regulation** select: *Off*, *Assisted dosing* or *Brine
(salinity)*. The [ha-reef-card](https://github.com/Elwinmage/ha-reef-card/blob/main/doc/en/reefdose.md#dose-regulation)
gathers its entities in the configuration dialog of the head.

The water volume is taken from **Tank water volume** when you set it; else from
the [ReefTank](https://github.com/Elwinmage/ha-reeftank-component) aquarium of
the doser; else from its ReefBeat cloud aquarium. The **Water volume used**
sensor tells which one applies.

#### Assisted dosing

You set a target (for example KH 8.4 dKH) and record your test results. From the
results and the volumes really dosed in between (the `/daily-log` of the doser),
the integration estimates what the tank consumes and **proposes** a daily dose.
Nothing reaches the doser until you apply it.

1. Choose the **Regulated parameter** (KH, calcium, magnesium, potassium,
   nitrate, phosphate, iodine or iron) and set the **Regulation target**.
2. Check **Supplement potency**: how much 1 mL raises the parameter in 100 L, as
   printed on the bottle. It is filled in for the supplements whose label gives
   it.
3. After each test, enter the value in **Test result** and press **Record test
   result**, or call `redsea.record_measurement` (useful with a dated test:
   `measured_at`).
4. When **Regulation status** reads *New dose proposed*, look at **Proposed daily
   dose** and press **Apply proposed dose** or **Dismiss proposed dose**.

The proposal is what the tank consumes plus a correction: the gap to the target
spread over **Correction spread** days, nothing inside **Regulation tolerance**.
It moves at most **Max dose change** (20 % by default) from the current dose, and
a change under 5 % is not proposed. A test too far from what was expected gives
*Retest suggested* instead of a proposal.

**Test kits**: instead of typing the result, pick the kit in **Test kit** and
type the syringe reading in **Reagent reading** (mL): the result is computed
into **Test result**. Red Sea Pro (KH, Ca, Mg) and Colombo (KH) are read as the
reagent used, Salifert (KH, Ca, Mg) as what is left in the 1 mL syringe.

**History**: `redsea.update_measurement` corrects a result (its `value`, its
date with `new_measured_at`) and `redsea.delete_measurement` removes one, both
identified by their `measured_at` as listed in the `measurements` attribute of
**Last test result**. The proposal is recomputed.

A supplement no test drives (Red Sea NO3:PO4-X, which lowers nitrate and
phosphate, or a food) offers no assisted mode, and its **Supplement potency**
is unavailable.

> [!NOTE]
> With bundled heads (Red Sea Complete Reef Care), only head 1 can be regulated,
> in assisted mode on the calcium: the doser derives the other heads from it.

#### Brine

The head holds a brine: salt dissolved in water, the **DIY - Brine** supplement,
the only one regulated on the salinity. Home Assistant reads a salinity sensor
(a ReefControl EC probe or any sensor, **Salinity sensor** select) every 10
minutes and sends small manual doses to keep its 24-hour average on target (35
ppt by default). It uses manual doses rather than the schedule of the head on
purpose: when Home Assistant is down nothing is dosed, and the salinity only
drifts down slowly.

| Setting | Default | Use |
| ------- | ------- | --- |
| Regulation target | 35 ppt | Salinity to hold |
| Brine concentration | 200 g/L | What you mixed |
| Max salinity rise | 0.5 ppt/day | Fastest correction allowed |
| Brine doses per day | 12 | How the daily volume is split |
| Refractometer check tolerance | 1 ppt | Gap accepted between the check and the probe |

**Brine planned per day** gives the volume planned. Record a refractometer
reading each month as a `salinity` test result: out of tolerance, the regulation
pauses until the probe is calibrated again. Without a check for 45 days, the rise
allowed per day is halved.

**Regulation alarm** turns on, and a `redsea_dose_regulation_alarm` event is
fired, when the salinity is too high (brine cannot lower it), when it cannot be
brought back to target, when the sensor is lost, and when a recalibration is
required.

### Maintenance tasks
| Task | Level | Default | Range |
| ---- | ----- | ------- | ----- |
| Calibrate dosing heads | Device | 90 days | 80 – 120 days |
| Replace dosing heads & tubes | Per head | 15 months | 11 – 19 months |

The replacement task is tracked **per head**, so replacing head 2 does not reset
the countdown of the other three. See the
[Maintenance](maintenance.md#maintenance) section.

---

[← Back to the main page](../../README.md)
