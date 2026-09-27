[← Zurück zur Hauptseite](README.de.md)

# ReefControl:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_devices.png" alt="Image">
</p>

Der ReefControl-Hub (RSCONTROLPRO / RSCONTROLLITE) liest die ReefSense-Sonden an seinen Erweiterungsboxen, steuert seine 12V-DC-Ports (2 beim Pro, 1 beim Lite) und, sobald gekoppelt, die Steckdosen eines [ReefControl-Power](reefcontrol-power.de.md#reefcontrol-power).

- **ReefSense-Sonden** — pH, ORP, Salinität (EC), Temperatur, ATO (Wasserstand) und Leck: Wert und Stufe (erwünscht / akzeptabel / Gefahr), Status, Name, UID, Datum der letzten Installation und der letzten Kalibrierung sowie die eingebaute Temperatur der pH-, EC- und ATO-Sonden. Jede Sonden-Entität trägt die Attribute `probe_uid`, `probe_type` und `probe_index`, die Messsensoren zusätzlich ein Attribut `ranges` (`[acceptable_low, desired_low, desired_high, acceptable_high]`).
- **Salinitätssonden** — Sensoren für Leitfähigkeit, Salinität (ppt) und spezifisches Gewicht sowie ein Select für die Anzeigeeinheit.
- **Lecksonden** — trocken/nass, **Herkunft des Wassers** (trocken / Aquariumwasser / Osmosewasser) und die gemessene Leitfähigkeit, gelesen sobald die Sonde nass wird.
- **Einstellungen pro Sonde** — erwünschter und akzeptabler Bereich (Hauptmesswert und eingebaute Temperatur), Schalter für Aktiviert / Summer / Benachrichtigungen / Wartung und eine Schaltfläche „Jetzt auslesen“, die einen frischen Messwert holt, ohne auf die nächste Abfrage zu warten.
- **Sondenkalibrierung** — siehe [unten](#sondenkalibrierung).
- **Summer** — Gefahren- und Lecksummer (Aktivierung, Frequenz, Tastverhältnis), Entprellung der Gefahr, Schalter des Leckdetektors; Zustand aktiv / quittiert des Summers und seine Ursache.
- **12V-Ports** — bearbeitbarer Name, Ein/Aus-Schalter, Zustand, Modus, Typ, Verbrauch und eine Schaltfläche „Port deinstallieren“. Der Sensor `port_N_mode` trägt die gesamte Portkonfiguration, seinen Zeitplan und seine Sondenregel als Attribute, damit eine Karte den Port bearbeiten kann (siehe [Port- und Steckdosenmodi](#port--und-steckdosenmodi)).
- **Kopplung mit ReefControl-Power** — gekoppeltes Power Center, sein Zustand und seine Verbindung, Schaltflächen „Power Center koppeln“ / „Power Center entkoppeln“ und eine Schaltfläche „Steckdose abmelden“ pro Steckdose des Power Centers, die der Hub über eine Sonde steuert.
- **Sonden hinzufügen, ersetzen oder entfernen** über das Optionsmenü der Integration (siehe [unten](#sondenverwaltung-hinzufügen--ersetzen--entfernen)).
- Schreibvorgänge werden sofort angezeigt (optimistische Aktualisierung) und anschließend durch erneutes Auslesen des Geräts bestätigt.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_diag.png" alt="Image">
</p>

> [!TIP]
> Die [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) zeichnet den Hub, seine Sonden, seine Ports und das gekoppelte Power Center und führt Kalibrierungen und Portmodi mit wenigen Klicks durch.

## Sondenverwaltung (hinzufügen / ersetzen / entfernen)
BLE-Sonden (pH, ORP, EC, ATO, Leck, Temperatur) werden über das Menü **Optionen** der Integration verwaltet, wie in der Red Sea App:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_probe_management.png" alt="Image">
</p>

- **Sonde hinzufügen**: Sonde in den Kopplungsmodus versetzen, Typ wählen und zum Suchen bestätigen. Die Sonde wird so eingerichtet wie von der App: Eine Lecksonde zum Beispiel heißt `Leak <uid>`, mit eingeschaltetem Summer, Leckdetektor und Benachrichtigungen.
- **Sonde ersetzen**: die zu ersetzende Sonde wählen, eine neue Sonde desselben Typs in den Kopplungsmodus versetzen und bestätigen. Die neue Sonde übernimmt Verlauf und Statistiken der alten.
- **Sonde entfernen**: eine oder mehrere Sonden auswählen und bestätigen — dies löscht die Entitäten der Sonde und ihren Verlauf endgültig.

> [!NOTE]
> Eine erneut installierte Sonde verliert ihre Einstellungen auf dem Hub (eine ORP-Sonde kehrt zu ihren Werksbereichen zurück). Die Integration liest die Sondenkonfiguration neu, sobald eine Sonde erscheint oder neu installiert wird, ob aus Home Assistant oder aus der ReefBeat-App.

## Sondenkalibrierung
Jeder Sondentyp wird so kalibriert wie in der ReefBeat-App.

| Sonde | Vorgehen | Entität / Dienst |
| ----- | -------- | ---------------- |
| ORP | Sonde in die Kalibrierlösung tauchen, dann die Zahl auf den Wert der Lösung setzen | `{probe} kalibrieren (Wert der Lösung)` |
| Temperatur | Die Zahl auf die tatsächliche Temperatur des Wassers setzen, in dem die Sonde steckt | `{probe} kalibrieren (tatsächliche Temperatur)` |
| Eingebaute Temperatur (pH, EC, ATO) | Ebenso, für den in die Sonde eingebauten Temperatursensor | `Temperatur von {probe} kalibrieren (tatsächliche Temperatur)` |
| pH | Zwei Punkte: pH 7, dann pH 10 (Salzwasser) oder pH 4 (Süßwasser) | `redsea.probe_calibration` |
| Salinität (EC) | Ein Punkt, mit dem Wert der Lösung in mS/cm | `redsea.probe_calibration` |

Die **Referenzwert-Zahlen** (ORP und Temperaturen) zeigen den aktuellen Messwert. Wird eine davon auf die Referenz gesetzt, liest sie die Sonde erneut und verschiebt deren Offset um `Referenz - Messwert`, sodass die Sonde danach die Referenz anzeigt.

Die **pH- und EC-Kalibrierungen** laufen in mehreren Schritten über den Dienst `redsea.probe_calibration`, ein Schritt pro Aufruf: `enter`, dann `point` für jeden Kalibrierpunkt, `status` abgefragt, bis der Hub Erfolg oder Fehlschlag meldet (er liefert dabei `calibration_status`, `time_left` und `stability_progress`), und schließlich `exit`. Die [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) erledigt die ganze Abfolge für Sie.

```yaml
action: redsea.probe_calibration
data:
  device_id: <config entry of the hub>
  probe_type: ph
  probe_uid: "0x00B39"
  action: point
  point: MID
  solution_value: 7.0
  solution_rated_temp: 25
```

Das Datum der letzten Kalibrierung stammt vom Hub: Eine in der ReefBeat-App kalibrierte pH- oder EC-Sonde oder eine geprüfte ORP-Sonde markiert ihre Wartungsaufgabe zu diesem Datum als erledigt.

## Temperatur-Fusion mehrerer Sonden
Sobald zwei oder mehr Temperaturquellen vorhanden sind (die dedizierte Temperatursonde plus die in den EC-/pH-/ATO-Sonden eingebettete Temperatur), berechnet ReefControl eine robuste **fusionierte Temperatur** aus den Einzelwerten:

- **Fusionierte Temperatur** (`sensor`): ein einzelner Wert, aggregiert mit der gewählten Methode — Median (Standard), Mittelwert, Minimum oder Maximum. Konfigurierbar über die Select-Entität **Temperatur-Fusionsmethode**.
- **Temperaturkohärenz** (`binary_sensor`) und **Temperaturspanne** (`sensor`, Diagnose): zeigen, ob die Quellen innerhalb der **Schwelle Temperaturkohärenz** (konfigurierbar, Standard 0,5 °C) übereinstimmen und wie stark sie ggf. abweichen.
- **Temperatur-Anomaliequelle** (`sensor`, Diagnose): `OK`, wenn alle Quellen übereinstimmen, der Name der Sonde(n), die im Verdacht stehen zu driften oder falsch zu messen, oder `Unbekannt`, wenn die Abweichung keiner einzelnen Sonde zugeordnet werden kann. Die Attribute des Sensors listen jede Quelle mit Wert, 1‑Stunden-Änderung und Status auf.
- Ein **Wartungsschalter pro temperaturfähiger Sonde**: bei Aktivierung wird diese Sonde vorübergehend aus der Fusions-/Kohärenz-/Anomalieberechnung ausgeschlossen, sodass Reinigung oder Kalibrierung nie einen Fehlalarm auslöst.
- Eine **Kalibrierung auf die tatsächliche Temperatur** (`number`) pro temperaturfähiger Sonde (siehe [Sondenkalibrierung](#sondenkalibrierung)).

Diese Entitäten erscheinen erst, wenn mindestens zwei Temperaturquellen erkannt wurden.

## Port- und Steckdosenmodi
Ein 12V-Port des Hubs läuft, wie eine Steckdose des Power Centers, in einem von vier Modi: **off**, **on**, **schedule** (Zeitplan) oder **sensor** (von einer Sonde gesteuert). Ein noch nicht installierter Port ist im Modus `setup` und lehnt jeden Schreibvorgang ab, bis er installiert ist.

Diese Einstellungen werden nicht als einzelne Entitäten bereitgestellt — bei mehreren Ports und Steckdosen und einem Satz Schwellwerte pro Sondentyp wären das Dutzende selten genutzter Entitäten. Konfigurieren Sie sie über die [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), die dieselben Aufrufe wie die ReefBeat-App in einem Schritt über den Dienst `redsea.request` ausführt (siehe die Dienste der Integration in den Entwicklerwerkzeugen von Home Assistant).

Der Sensor `port_N_mode` trägt dennoch alles, was eine Automatisierung braucht, um die aktive Konfiguration zu lesen: `config` (der vollständige Porteintrag, einschließlich `power_on_percent`), `schedule` (vom Hub gelesen, solange der Port im Zeitplanmodus ist) und `sensor_config` (die Sondenregel), mit `sensor_source: control`.

> [!NOTE]
> Ein Port, der eine ATO-Pumpe über eine ATO-Sonde steuert, bleibt vom Typ `other`: Der Assistent des ATO-Kits der ReefBeat-App verknüpft beide. Der Hub stellt die ATO-Befehle des RSATO+ (manuelles Befüllen, automatisches Befüllen, Restvolumen…) nicht bereit.

## Wartungsaufgaben
| Aufgabe | Sonden | Standard | Bereich |
| ------- | ------ | -------- | ------- |
| Sonde reinigen | Alle | 30 Tage | 2 – 8 Wochen |
| Sonde kalibrieren | pH | 3 Monate | 2 – 4 Monate |
| Sonde kalibrieren | Salinität (EC) | 2 Monate | 1 – 3 Monate |
| Sonde prüfen | ORP | 6 Monate | 5 – 7 Monate |
| Sonde ersetzen | pH, ORP | 12 Monate | 9 – 18 Monate |

Die Aufgaben werden **pro Sonde** verfolgt, nach den offiziellen Empfehlungen von Red Sea. Temperatur- und Lecksonden erhalten keine Kalibriererinnerung, und die 4-polige EC-Zelle wird nie nach Zeitplan ersetzt. Siehe den Abschnitt [Wartung](maintenance.de.md#wartung).

---

[← Zurück zur Hauptseite](README.de.md)
