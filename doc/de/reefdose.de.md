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
- [Dosierregelung](#dosierregelung): assistierte Dosierung und Salzlösung
- [Verlauf der Dosierungen](poseidon.de.md#verlauf-der-dosierungen), im Poseidon-Modus

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

### Dosierregelung

Jeder Kopf hat eine Auswahl **Dosierregelung**: *Aus*, *Assistierte Dosierung* oder *Salzlösung (Salinität)*. Die [ha-reef-card](https://github.com/Elwinmage/ha-reef-card/blob/main/doc/de/reefdose.de.md#dosierregelung) fasst ihre Entitäten im Konfigurationsdialog des Kopfes zusammen.

Das Wasservolumen stammt aus **Wasservolumen des Beckens**, wenn Sie es einstellen; sonst aus dem [ReefTank](https://github.com/Elwinmage/ha-reeftank-component)-Aquarium des Dosierers; sonst aus seinem ReefBeat-Cloud-Aquarium. Der Sensor **Verwendetes Wasservolumen** zeigt, welcher Wert gilt.

#### Assistierte Dosierung

Sie legen ein Ziel fest (zum Beispiel KH 8,4 dKH) und speichern Ihre Testergebnisse. Aus den Ergebnissen und den dazwischen tatsächlich dosierten Mengen (das `/daily-log` des Dosierers) schätzt die Integration den Verbrauch des Beckens und **schlägt** eine Tagesdosis **vor**. Nichts erreicht den Dosierer, bevor Sie es übernehmen.

1. Wählen Sie den **Geregelten Parameter** (KH, Calcium, Magnesium, Kalium, Nitrat, Phosphat, Jod oder Eisen) und stellen Sie das **Regelziel** ein.
2. Prüfen Sie die **Wirkstärke des Zusatzes**: wie stark 1 mL den Parameter in 100 L anhebt, wie auf der Flasche angegeben. Sie ist für die Zusätze vorausgefüllt, deren Etikett sie nennt.
3. Tragen Sie nach jedem Test den Wert unter **Testergebnis** ein und drücken Sie **Testergebnis speichern**, oder rufen Sie `redsea.record_measurement` auf (nützlich für einen datierten Test: `measured_at`).
4. Zeigt **Regelstatus** *Neue Dosis vorgeschlagen*, prüfen Sie **Vorgeschlagene Tagesdosis** und drücken Sie **Vorgeschlagene Dosis übernehmen** oder **Vorgeschlagene Dosis verwerfen**.

Der Vorschlag entspricht dem Verbrauch des Beckens plus einer Korrektur: die Abweichung vom Ziel, verteilt auf die Tage des **Korrekturzeitraums**, nichts innerhalb der **Regeltoleranz**. Er weicht höchstens um die **Max. Dosisänderung** (Standard 20 %) von der aktuellen Dosis ab, und eine Änderung unter 5 % wird nicht vorgeschlagen. Ein Test, der zu weit vom Erwarteten abweicht, ergibt *Neuer Test empfohlen* statt eines Vorschlags.

> [!NOTE]
> Bei gebündelten Köpfen (Red Sea Complete Reef Care) kann nur Kopf 1 geregelt werden, assistiert auf Calcium: Der Dosierer leitet die anderen Köpfe daraus ab.

#### Salzlösung

Der Kopf enthält eine Salzlösung, in Wasser gelöstes Salz: den Zusatz **DIY - Brine**, den einzigen, der auf die Salinität geregelt wird. Home Assistant liest alle 10 Minuten einen Salinitätssensor (eine EC-Sonde des ReefControl oder einen beliebigen Sensor, Auswahl **Salinitätssensor**) und sendet kleine manuelle Dosen, um dessen 24-Stunden-Mittel auf dem Ziel zu halten (Standard 35 ppt). Bewusst manuelle Dosen statt des Programms des Kopfes: Ist Home Assistant aus, wird nichts dosiert, und die Salinität sinkt nur langsam.

| Einstellung | Standard | Zweck |
| ----------- | -------- | ----- |
| Regelziel | 35 ppt | Zu haltende Salinität |
| Konzentration der Salzlösung | 200 g/L | Ihre Mischung |
| Max. Salinitätsanstieg | 0,5 ppt/Tag | Schnellste erlaubte Korrektur |
| Salzlösungsdosen pro Tag | 12 | Aufteilung der Tagesmenge |
| Toleranz der Refraktometerprüfung | 1 ppt | Zulässige Abweichung zwischen Prüfung und Sonde |

**Geplante Salzlösung pro Tag** nennt die geplante Menge. Speichern Sie jeden Monat eine Refraktometermessung als Testergebnis `salinity`: Außerhalb der Toleranz pausiert die Regelung, bis die Sonde neu kalibriert ist. Ohne Prüfung seit 45 Tagen halbiert sich der erlaubte Anstieg pro Tag.

**Regelalarm** schaltet sich ein, und ein Ereignis `redsea_dose_regulation_alarm` wird ausgelöst, wenn die Salinität zu hoch ist (Salzlösung kann sie nicht senken), wenn sie nicht zum Ziel zurückgeführt werden kann, wenn der Sensor ausfällt und wenn eine Neukalibrierung nötig ist.

### Wartungsaufgaben
| Aufgabe | Ebene | Standard | Spanne |
| ------- | ----- | -------- | ------ |
| Dosierköpfe kalibrieren | Gerät | 90 Tage | 80 – 120 Tage |
| Köpfe und Schläuche tauschen | Je Kopf | 15 Monate | 11 – 19 Monate |

Der Tausch wird **je Kopf** verfolgt: Kopf 2 zu wechseln setzt den Countdown der
anderen drei nicht zurück. Siehe den Abschnitt [Wartung](maintenance.de.md#wartung).

---

[← Zurück zur Hauptseite](README.de.md)
