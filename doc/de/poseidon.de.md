[← Zurück zur Hauptseite](README.de.md)

# Poseidon-Modus

<p align="center">
<img src="../img/poseidon/poseidon.png" alt="Poseidon" width="240">
</p>

Der Poseidon-Modus setzt in Home Assistant ein Relais zwischen Ihre
ReefBeat-Geräte und den MQTT-Broker von Red Sea. Ein Gerät im Poseidon-Modus
verbindet sich mit Home Assistant statt mit `mqtt.reef-beat.com`, und Home
Assistant gibt seinen Datenverkehr unverändert an Red Sea weiter: die
ReefBeat-App funktioniert weiter wie bisher.

> [!WARNING]
> Der Poseidon-Modus ist experimentell. Derzeit leitet er den Datenverkehr nur
> weiter und beobachtet ihn: die Integration fragt die Geräte weiterhin ab.

## Poseidon hinzufügen

*Einstellungen > Geräte & Dienste > Red Sea > Eintrag hinzufügen > Poseidon-Modus*

- **Lauschport**: der erste freie Port ab 1884 wird vorgeschlagen (1883 und
  8883, die üblichen MQTT-Ports, werden übersprungen). Er wird beim Absenden
  und bei jedem Start des Relais erneut geprüft: ist er von einem anderen
  Dienst belegt, meldet das ein Reparaturhinweis, und die Geräte bleiben
  unberührt.
- **Adresse von Home Assistant**: die IPv4-Adresse, über die die Geräte Home
  Assistant erreichen.
- **Cloud-Konto**: das ReefBeat-Cloud-Konto, mit dem die Schlüssel der Geräte
  geholt werden. Ein Cloud-Konto ist erforderlich.

## Geräte hinzufügen

*Poseidon > Konfigurieren > Geräte hinzufügen*

Jedes Gerät der Integration wird mit seinem Status aufgeführt:

| Status | Bedeutung |
|---|---|
| Auswählbar | Seine Schlüssel sind bekannt: es wechselt sofort in den Poseidon-Modus |
| Auswählbar, 🔑 | Seine Schlüssel müssen zuerst geholt werden (siehe unten) |
| Bereits im Poseidon-Modus | Nichts zu tun |
| Ohne Cloud-Zugangsdaten | An ein lokales Aquarium gebunden: kein Poseidon-Modus möglich |
| Nicht im Cloud-Konto | Seine Schlüssel können mit diesem Konto nicht geholt werden |
| Nicht erreichbar | Antwortet nicht |

> [!CAUTION]
> **Der Schlüsselabruf ist destruktiv.** Ein Gerät gibt seine Schlüssel nicht
> heraus: um sie zu erhalten, wird es aus der ReefBeat-Cloud gelöscht und neu
> angelegt.
> - es wird von seinem Aquarium gelöst, und die App muss es eventuell neu
>   koppeln;
> - in der Cloud gespeicherte Zeitpläne, Voreinstellungen und Verlauf können
>   verloren gehen;
> - seine Konfiguration wird vorher gesichert und danach verglichen: ReefRun
>   und ReefWave erhalten ihre automatisch zurück, bei den anderen Geräten wird
>   die Änderung in einer Benachrichtigung aufgelistet (die gesicherte
>   Konfiguration bleibt in `/config/redsea/poseidon/snapshots/`).
>
> Der Abruf erfolgt einmal pro Gerät: Home Assistant behält die Schlüssel,
> auch wenn Poseidon entfernt wird.

## Der Poseidon-Schalter

Jedes Gerät mit bekannten Schlüsseln erhält auf seiner Seite einen Schalter
**Poseidon-Modus**:

- **an**: das Gerät spricht über Home Assistant mit Red Sea;
- **aus**: das Gerät spricht direkt mit Red Sea (Normalmodus).

Sein Zustand wird vom Gerät selbst gelesen. Seine Attribute:

| Attribut | Bedeutung |
|---|---|
| `connection_state` | Vom Gerät gemeldeter Verbindungszustand |
| `last_up` / `last_down` | Letzter Verkehr Gerät → Red Sea / Red Sea → Gerät |
| `silent` | Im Poseidon-Modus, aber während der eingestellten Wartezeit ging nichts durch das Relais |

Ein stilles Gerät löst zusätzlich einen Reparaturhinweis aus, der von selbst
verschwindet, sobald sein Verkehr wieder läuft. Ein stilles Gerät wird nie
automatisch zurückgeschaltet.

## Was wann passiert

| Ereignis | Geräte |
|---|---|
| Neustart von Home Assistant, Neuladen von Poseidon | Bleiben, wie sie sind: sie verbinden sich neu, sobald das Relais zurück ist |
| Poseidon deaktiviert oder entfernt | Alle zurück in den Normalmodus |
| Ein Gerät kann nicht zurückgeschaltet werden | In einer Benachrichtigung genannt |

In den Poseidon-Modus wechselt ein Gerät nur auf Ihre Entscheidung. Jedes
automatische Umschalten führt zurück in den Normalmodus.

## Strategien

Was Home Assistant mit einem Gerät im Poseidon-Modus macht. Jedes Gerät hat
neben seinem Schalter eine Auswahl **Poseidon-Strategie**; die Einstellungen
geben den Standard vor.

| Strategie | Abfrage | Gesendete Zustände | Datei |
|---|---|---|---|
| *Spion* | unverändert | aufgezeichnet, mit der nächsten Abfrage verglichen | `spy.jsonl` |
| *Shadow* | unverändert | in die Gerätedaten übernommen, mit der nächsten Abfrage verglichen | `shadow.jsonl` |
| *Poseidon* | alle N Minuten | genutzt; das Gerät wird bei jedem Zustand neu gelesen, solange seine Familie nicht übernommen werden kann | — |

> [!NOTE]
> Noch kann keine Gerätefamilie übernommen werden: Die Übernahme wird aus den
> Spion-Dateien geschrieben. Bis dahin vergleicht *Shadow* nur, und *Poseidon*
> liest das Gerät bei jedem gesendeten Zustand neu.

### Spion

`/config/redsea/poseidon/logs/spy.jsonl` (Rotation bei 10 MB, 5 Dateien)
enthält, mit derselben Uhr:

| `kind` | Eintrag |
|---|---|
| `publish`, `control` | ein Frame zwischen Gerät und Red Sea, in beide Richtungen, entschlüsselt |
| `http` | eine HTTP-Anfrage von Home Assistant an das Gerät: Methode, Endpoint, Status (0 = keine Antwort), Dauer, Daten; `origin` ist `integration` oder `poseidon` (seine `/cloud`-Abfragen alle 60 s) |
| `compare` | ein gesendeter Zustand gegenüber der nächsten Abfrage, jeder Wert `same`, `differs` oder `unknown` |
| `mark` | Strategie oder Pause geändert |

Ein Gerät im Spion-Modus hat außerdem einen Schalter **Abfragepause**: Es
erhält keine Anfrage mehr, auch nicht die `/cloud`-Abfragen von Poseidon; was
es dann sendet, sendet es von sich aus. Die Pause übersteht keinen Neustart.

Empfohlene Aufzeichnung, je Gerät (Uhren der Home-Assistant-Hosts
synchronisiert, gleiche Zeitzone):

1. 30 Minuten ganz ohne Abfrage: jedes andere Home Assistant, das das Gerät
   liest, gestoppt, Pause an;
2. 30 Minuten nur mit Abfrage (Pause aus);
3. Aktionen zu notierten Zeiten: aus der ReefBeat-App, aus Home Assistant, am
   Gerät selbst;
4. fragt ein anderes Home Assistant das Gerät ab, lassen sich seine Anfragen
   mit der Aktion `logger.set_level`,
   `custom_components.redsea.reefbeat.api: debug` hinzufügen.

## Einstellungen

*Poseidon > Konfigurieren > Poseidon-Einstellungen*

- **Standardstrategie**: die jedes Geräts im Poseidon-Modus ohne eigene
  Strategie (siehe [Strategien](#strategien)). Standardmäßig *Spion*.
- **Abfrageintervall der Poseidon-Strategie**, in Minuten (standardmäßig 10).
- **Debug-Modus**: jedes Frame, das das Relais passiert, wird entschlüsselt
  nach `/config/redsea/poseidon/logs/poseidon.jsonl` geschrieben (Rotation bei
  10 MB, 5 Dateien). Die Daten stehen dort im Klartext.
- **Wartezeit, bis ein Gerät still ist**, in Minuten (standardmäßig 10).
- **Watchdog-Schlüssel**: 16 Zeichen, vorgeschlagen, solange keiner gesetzt
  ist. Ein Watchdog auf einem anderen Rechner (eigenständig oder in
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup))
  fragt das Relais, ob es lebt, und schaltet die Geräte in den Normalmodus
  zurück, wenn nicht. Übernehmen Sie diesen Schlüssel in seine Konfiguration;
  leer lassen, um keinem Watchdog zu antworten.

## Schlüssel exportieren und importieren

*Poseidon > Konfigurieren > Schlüssel exportieren* liefert einen
Download-Link für alle bekannten Schlüssel, 5 Minuten gültig. Die Datei wird
beim Klick erzeugt und nie in `/config` geschrieben; sie hat das Format der CLI
(`keystore.json`) und enthält die Schlüssel im Klartext: sicher aufbewahren.
Die Aktion `redsea.poseidon_export` schreibt für Automationen dieselbe Datei
nach `/config/redsea/poseidon/keystore-<Datum>.json`, nur für den Besitzer
lesbar.

*Poseidon > Konfigurieren > Schlüssel importieren* fragt nach einer solchen
Datei und sendet sie aus dem Browser. Ein Gerät wird nur durch einen neueren
Eintrag ersetzt, Geräte ohne Schlüssel werden übersprungen, und importierte
Geräte erhalten sofort ihren Schalter.

## Notfallskript

*Poseidon > Konfigurieren > Notfallskript* liefert einen Download-Link
(5 Minuten) zu `poseidon_rescue.py`: ein Skript, das die Geräte ohne Home
Assistant auf den Red-Sea-Broker zurückschaltet, wenn Home Assistant es nicht
mehr kann (gestoppt, Relais defekt, Integration entfernt). Es läuft auf jedem
Rechner im Netz der Geräte mit Python 3.8 oder neuer, sonst nichts zu
installieren:

```bash
python3 poseidon_rescue.py --dry-run   # was getan würde, nichts wird geändert
python3 poseidon_rescue.py             # Geräte am Relais, nach Bestätigung
```

| Option | Zweck |
|---|---|
| `--ip HWID=IP` | ein Gerät hat seit dem Download die Adresse gewechselt |
| `--scan CIDR` | wo Geräte mit neuer Adresse gesucht werden (wiederholbar) |
| `--no-scan` | nie suchen |
| `--only HWID` | ein Gerät (hwid oder Name, wiederholbar) |
| `--all` | alle Geräte, egal auf welchen Broker sie zeigen |
| `--keystore keystore.json` | ein Keystore-Export statt der eingebetteten Geräte |
| `--yes` | ohne Bestätigung |

In ein Gerät wird nichts geschrieben, bevor es sich als das richtige erwiesen
hat: seine `hwid` aus `/device-info` muss passen. Ein Gerät, das unter seiner
Adresse nicht mehr antwortet oder dessen Adresse jetzt einem anderen gehört,
wird im Netz gesucht: im /24 jeder bekannten Adresse und des Rechners, auf dem
das Skript läuft, oder in den `--scan`-Subnetzen.

Jedes Gerät erhält dieselbe Sequenz wie aus Home Assistant (deaktivieren,
Broker und Schlüssel schreiben, aktivieren), danach wird `/cloud` zur Kontrolle
neu gelesen. Das Skript enthält die Schlüssel im Klartext: sicher aufbewahren
und nach dem Hinzufügen von Geräten erneut herunterladen.
