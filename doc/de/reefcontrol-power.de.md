[← Zurück zur Hauptseite](README.de.md)

# ReefControl-Power

Das RSPOWER (Power Center) ist ein eigenständiges Gerät mit eigener IP-Adresse und wird in Home Assistant separat angezeigt.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_devices.png" alt="Image">
</p>

- 6 oder 8 steuerbare Steckdosen je nach Modell (RSPOWER6 / RSPOWER8)
- **Pro Steckdose**: bearbeitbarer Name, Ein/Aus-Schalter, Zustand, Modus, vorheriger Modus, Verbrauch und eine Schaltfläche „Steckdose löschen“, die die Steckdose in den Werkszustand zurücksetzt (Modus `setup`, Werksname)
- **Gerät**: Gesamtverbrauch, Batteriestand, Modus, Modellregion und Anzahl der Steckdosen
- **Lokale Temperatursonde** (optional): Schaltflächen zum Hinzufügen / Entfernen, Schaltfläche „Temperatur abrufen“, Kalibrierung auf die tatsächliche Temperatur, erwünschter und akzeptabler Temperaturbereich, Name, Schalter für Benachrichtigungen und Protokollierung — alle verfügbar, sobald eine Sonde installiert ist. Der Temperatursensor trägt die Attribute `ranges` und `level`, wie die Sonden des Hubs.
- **ReefControl-Kopplung**: gekoppelter Hub, sein Typ und Status, Verbindungs- und Internetzustand sowie eine Schaltfläche „Steuerungs-Hub entkoppeln“
- Schreibvorgänge werden sofort angezeigt (optimistische Aktualisierung) und anschließend durch erneutes Auslesen des Geräts bestätigt

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_diag.png" alt="Image">
</p>

> [!NOTE]
> Die lokale Temperatursonde und der ReefControl-Hub schließen sich gegenseitig aus: „Temperatursonde hinzufügen“ ist nur ohne beide verfügbar, „Temperatursonde entfernen“ mit einer lokalen Sonde und „Steuerungs-Hub entkoppeln“ mit einem gekoppelten Hub. Die Schaltflächen bleiben sichtbar, aber nicht verfügbar, wenn sie nicht zutreffen.

## Kopplung mit einem ReefControl
Die Kopplung wird immer vom Hub aus gestartet, mit seiner Schaltfläche **Power Center koppeln**: Der Hub koppelt sich mit dem Power Center, das er im Netzwerk findet. Entkoppeln funktioniert von beiden Seiten. Sind beide Geräte in Home Assistant eingerichtet, erscheint die Änderung auf beiden gleichzeitig — bei einer Kopplung nur, wenn ein einziges freies Power Center eindeutig festlegt, welches gemeint ist.

Nach der Kopplung können die Sonden des Hubs die Steckdosen steuern. Das Power Center speichert nur, welchem Sondentyp eine Steckdose folgt; die Sonde selbst und die Schwellwerte liegen auf dem Hub. Zwei Dienste erlauben einer Karte oder Automatisierung, diese Seite zu lesen:

- `redsea.get_control_probes` — die Sonden eines Hubs (Identität und aktuelle Werte), über seine Hardware-ID
- `redsea.get_control_subscriptions` — die Regeln, die der Hub auf die Steckdosen seines Power Centers anwendet, über seine Hardware-ID

Das Löschen einer Steckdose am Power Center entfernt nur ihre Hälfte einer Sondenregel: Die Schaltfläche **Steckdose N abmelden** des Hubs entfernt die andere Hälfte.

## Steckdosenmodus und sensorgesteuerte Steckdosen
Der Modus einer Steckdose (off / on / schedule / sensor) und ihre Zeitplan- bzw. Sensorschwellwert-Einstellungen (z. B. „diese Steckdose einschalten, wenn die lokale Temperatur unter 24 °C fällt“) werden über die [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) konfiguriert, wie bei den [Ports des Hubs](reefcontrol.de.md#port--und-steckdosenmodi).

Jede Steckdose stellt eine Entität `sensor.socket_N_mode` für Automatisierungen bereit: Ihr Zustand ist der aktuelle Modus der Steckdose, ihre Attribute tragen den aktuellen `schedule` und (im Sensormodus) die `sensor_config`, gekennzeichnet durch `sensor_source`: `local` für die eigene Sonde des Power Centers, `control` für eine Regel des gekoppelten Hubs.

Eine per Zeitplan oder Sonde gesteuerte Steckdose kann von Hand ausgeschaltet werden: Ihr Modus zeigt dann `off`, während der Sensor **vorheriger Modus** den automatischen Modus behält, zu dem sie zurückkehrt.

Das Gerät verlässt seinen anfänglichen „setup“-Zustand automatisch, sobald die erste Steckdose konfiguriert ist, wie in der ReefBeat-App — keine manuelle Aktion nötig.

---

[← Zurück zur Hauptseite](README.de.md)
