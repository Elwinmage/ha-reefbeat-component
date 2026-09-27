[← Zurück zur Hauptseite](README.de.md)

# ReefLED:

- Weiß- und Blaukanal abrufen und einstellen (only for G1: RSLED50, RSLED90, RSLED160)
- Farbtemperatur, Intensität und Mond abrufen und einstellen (all LEDs)
- Akklimatisierung verwalten. Acclimation settings are automatically enabled or disabled according to the acclimation switch.
- Mondphasen verwalten. Moon phase settings are automatically enabled or disabled according to the moon phase switch.
- Manuellen Farbmodus mit oder ohne Dauer einstellen.
- Lüfter- und Temperaturwerte abrufen.
- Name und Wert für Programme abrufen (with cloud support). Only for G1 LEDs.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Image">
</p>

***

Die Unterstützung der Farbtemperatur für G1-LEDs berücksichtigt die Besonderheiten jedes der drei Modelle.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## WICHTIG für G1- und G2-Leuchten

### G2-LEUCHTEN

#### Intensität
Da G2-LEDs über den gesamten Farbbereich eine konstante Intensität gewährleisten, nutzen Ihre LEDs in der Mitte des Spektrums nicht ihre volle Leistung. Bei 8.000K steht der Weißkanal auf 100 % und der Blaukanal auf 0 % (umgekehrt bei 23.000K). Bei 14.000K und 100 % Intensität liegt die Leistung des Weiß- und des Blaukanals bei G2-Leuchten bei etwa 85 %.
Hier ist die Verlustkurve der G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
</p>

#### Farbtemperatur
Die G2-Oberfläche unterstützt nicht den gesamten Temperaturbereich. Von 8.000K bis 10.000K werden die Werte in 200K-Schritten erhöht, von 10.000K bis 23.000K in 500K-Schritten. Dies wird automatisch gehandhabt: Wählen Sie einen ungültigen Wert (z. B. 8.300K), wird automatisch ein gültiger Wert gewählt (in diesem Beispiel 8.200K). Deshalb springt der Regler bei der Farbwahl an einer G2-Leuchte manchmal leicht: Er stellt sich auf einen zulässigen Wert.

### G1-LEUCHTEN

G1-LEDs werden über den Weiß- und den Blaukanal gesteuert, was die volle Leistung über den gesamten Bereich erlaubt, ohne Kompensation aber keine konstante Intensität.
Deshalb wurde die Intensitätskompensation eingeführt.
Diese Kompensation sorgt dafür, dass Sie unabhängig von der gewählten Farbtemperatur (im Bereich 12.000 bis 23.000K) dasselbe [PAR](https://en.wikipedia.org/wiki/Photosynthetically_active_radiation) (Lichtintensität) erhalten.
> [!NOTE]
> Da Red Sea keine PAR-Werte unter 12.000K veröffentlicht, ist die Kompensation nur im Bereich 12.000 bis 23.000K verfügbar. Wenn Sie eine G1-LED und ein PAR-Messgerät besitzen, können Sie [mich kontaktieren](https://github.com/Elwinmage/ha-reefbeat-component/discussions/), um die Kompensation auf den gesamten Bereich (9.000 bis 23.000K) zu erweitern.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

Anders gesagt: Ohne Kompensation liefert eine Intensität von x % bei 9.000K nicht dasselbe PAR wie bei 23.000K oder 15.000K.

Hier sind die Leistungskurven:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

Wenn Sie die volle Leistung Ihrer LED nutzen möchten, deaktivieren Sie die Intensitätskompensation (Standard).

Wenn Sie die Intensitätskompensation aktivieren, ist die Lichtintensität über alle Farbtemperaturen konstant, in der Mitte des Bereichs nutzen Sie jedoch nicht die volle Leistung Ihrer LEDs (wie bei den G2-Modellen).

Beachten Sie auch, dass bei aktivierter Kompensation der Intensitätsfaktor bei G1-Leuchten 100 % überschreiten kann, wenn Sie die Weiß-/Blaukanäle manuell einstellen. So können Sie die volle Leistung Ihrer LEDs ausschöpfen!

***

### Wartungsaufgaben
| Aufgabe | Standard | Spanne |
| ------- | -------- | ------ |
| Linsen reinigen | 3 Wochen | 1 – 5 Wochen |
| Lüfter und Gitter entstauben | 6 Monate | 5 – 7 Monate |

Diese beiden Aufgaben entstehen für alle ReefLED-Generationen, auch für die
virtuelle LED. Siehe den Abschnitt [Wartung](maintenance.de.md#wartung).

---

[← Zurück zur Hauptseite](README.de.md)
