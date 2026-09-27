[← Zurück zur Hauptseite](README.de.md)

# ReefRun:
- Pumpengeschwindigkeit einstellen
- Überschäumen verwalten
- Erkennung eines vollen Auffangbehälters verwalten
- Skimmer-Modell änderbar

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Image">
</p>

### Hauptgerät
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Image">
</p>

### Pumpen
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Image">
</p>

### Wartungsaufgaben
Die Aufgaben hängen am Untergerät Pumpe und richten sich nach deren Typ.

| Aufgabe | Pumpe | Standard | Spanne |
| ------- | ----- | -------- | ------ |
| Motor und Rotor reinigen | Rückförderung | 4,5 Monate | 2 – 7 Monate |
| Ansaugsieb reinigen | Rückförderung | 6 Wochen | 3 – 9 Wochen |
| Venturi und Luftschlauch reinigen | Abschäumer | 5 Wochen | 3 – 7 Wochen |
| Rotor des Abschäumers reinigen | Abschäumer | 4,5 Monate | 2 – 7 Monate |
| Sonde für vollen Becher kalibrieren | Abschäumer | 4 Wochen | 2 – 6 Wochen |
| Sonde für Überschäumen kalibrieren | Abschäumer | 4 Wochen | 2 – 6 Wochen |

Die beiden Kalibrieraufgaben überwacht auch das Alarm-Blueprint, das das vom
Gerät gemeldete Datum der letzten Kalibrierung mit dem hier gesetzten Intervall
vergleicht. Siehe den Abschnitt [Wartung](maintenance.de.md#wartung).

### Werkzeug zum Ausbau des Rotors

Die obige Aufgabe *Rotor des Abschäumers reinigen* erfordert das Aufschrauben
des Pumpenkörpers, der nass so gut wie keinen Griff bietet. Ein 3D-druckbares
Werkzeug dafür, mit Video zur Anwendung, gibt es hier:
[Red Sea DC Skimmer Rotorwerkzeug](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

---

[← Zurück zur Hauptseite](README.de.md)
