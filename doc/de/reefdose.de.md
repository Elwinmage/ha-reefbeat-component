[← Zurück zur Hauptseite](README.de.md)

# ReefDose:
- Tagesdosis bearbeiten
- Manuelle Dosierung
- Supplemente hinzufügen und entfernen
- Behältervolumen bearbeiten und steuern. Die Einstellungen des Behältervolumens werden je nach Schalter der Volumenkontrolle automatisch aktiviert oder deaktiviert.
- Zeitplan pro Pumpe aktivieren/deaktivieren
- Konfiguration von Bestandsalarmen
- Dosierungsverzögerung zwischen Supplementen
- Befüllen (Bitte lesen Sie [dies](#kalibrierung-und-befüllen))
- Kalibrierung (Bitte lesen Sie [dies](#kalibrierung-und-befüllen))

<p align="center">
<img src="../img/rsdose_devices.png" alt="Image">
</p>

### Hauptgerät
<p align="center">
<img src="../img/rsdose_main_conf.png" alt="Image">
<img src="../img/rsdose_main_diag.png" alt="Image">
</p>

### Köpfe
<p align="center">
<img src="../img/rsdose_ctrl.png" alt="Image">
<img src="../img/rsdose_sensors.png" alt="Image">
<img src="../img/rsdose_diag.png" alt="Image">
</p>

#### Kalibrierung und Befüllen

> [!CAUTION]
> Sie müssen die folgende Reihenfolge genau einhalten (Using the [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) is safer).<br /><br />
> <ins>Calibration</ins>:
>  1. Stellen Sie den Messbecher auf und drücken Sie „Kalibrierung starten"
>  2. Geben Sie den gemessenen Wert im Feld „Kalibrierungsdosis" ein
>  3. Press "Set Calibration Value"
>  4. Leeren Sie den Messbecher und drücken Sie „Neue Kalibrierung testen". Beträgt der erhaltene Wert nicht 4 mL, kehren Sie zu Schritt 1 zurück.
>  5. Press "Stop and Save Graduation"
>
> <ins>For priming</ins>:
>  1. (a) Press "Start Priming"
>  2. (b) Sobald die Flüssigkeit austritt, drücken Sie „Befüllung stoppen"
>  3. (1) Stellen Sie den Messbecher auf und drücken Sie „Kalibrierung starten"
>  4. (2) Geben Sie den gemessenen Wert im Feld „Kalibrierungsdosis" ein
>  5. (3) Press "Set Calibration Value"
>  6. (4) Leeren Sie den Messbecher und drücken Sie „Neue Kalibrierung testen". Beträgt der erhaltene Wert nicht 4 mL, kehren Sie zu Schritt 1 zurück.
>  7. (5) Press "Stop and Save Graduation"
>
> ⚠️ Auf das Befüllen muss immer eine Kalibrierung folgen (Schritte 1 bis 5)!⚠️

<p align="center">
  <img src="../img/calibration.png" alt="Image">
</p>

### Wartungsaufgaben
| Aufgabe | Ebene | Standard | Spanne |
| ------- | ----- | -------- | ------ |
| Dosierköpfe kalibrieren | Gerät | 90 Tage | 80 – 120 Tage |
| Köpfe und Schläuche tauschen | Je Kopf | 15 Monate | 11 – 19 Monate |

Der Tausch wird **je Kopf** verfolgt: Kopf 2 zu wechseln setzt den Countdown der
anderen drei nicht zurück. Siehe den Abschnitt [Wartung](maintenance.de.md#wartung).

---

[← Zurück zur Hauptseite](README.de.md)
