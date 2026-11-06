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
> Der Poseidon-Modus ist experimentell. Mit der Standardstrategie *Spion* leitet
> er den Datenverkehr nur weiter und beobachtet ihn: Die Integration fragt die
> Geräte weiter ab. Die Strategien *Shadow* und *Poseidon* nutzen, was die Geräte
> senden (siehe [Strategien](#strategien)).

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
> - seine Konfiguration wird davor gesichert und danach verglichen: ReefRun und
>   ReefWave erhalten ihre automatisch zurück, bei den anderen Geräten wird das
>   Geänderte in einer Benachrichtigung aufgeführt (die gesicherte Konfiguration
>   bleibt in `/config/redsea/poseidon/snapshots/`);
> - eine ReefWave hängt von der Cloud ab, die ihr bei jeder Verbindung ihr
>   Programm sendet: Vor dem Löschen werden auch die eigenen Wellen ihres
>   Aquariums (mit den Intensitäten jeder Pumpe) und ihr Programm gesichert; die
>   Erfassung bricht ab, ohne etwas zu löschen, wenn sie nicht lesbar sind. Danach
>   werden die von der Cloud verlorenen Wellen neu angelegt (oder erhalten die
>   Einstellungen der Pumpe zurück), das Programm wird in die Cloud gesendet, und
>   die Cloud gibt es an die Pumpen weiter; die Pumpe wird nur direkt beschrieben,
>   wenn sie es nicht erhalten hat.
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
| Das Relais fällt aus, ein [Watchdog](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog) überwacht es | Alle zurück in den Normalmodus, sobald Red Sea als erreichbar bestätigt ist; ohne Watchdog nutzen Sie das [Notfallskript](#notfallskript) |
| Ein Gerät zeigt auf das Relais, verbindet sich aber nie damit (es hat seine Sitzung mit Red Sea behalten) | Nach 2 Minuten zum Neuverbinden gebracht: zurück auf Red Sea, dann wieder auf das Relais, höchstens zweimal |

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

> [!IMPORTANT]
> **ReefATO+-Besitzer, ich brauche Ihre Hilfe.** Ich besitze keinen ReefATO+, der
> Poseidon-Modus lief also noch nie auf einem: Was er sendet, ist noch unbekannt,
> und nichts davon wird übernommen. Stellen Sie Ihren zuerst auf die Strategie
> *Spion*, und helfen Sie dann, seine Unterstützung zu vervollständigen:
> - senden Sie mir sein Spion-Log (`/config/redsea/poseidon/logs/spy.jsonl`) in
>   einem [GitHub-Issue](https://github.com/Elwinmage/ha-reefbeat-component/issues),
>   nachdem Sie es gelesen haben: Es ist entschlüsselt und enthält die Kennungen
>   Ihrer Geräte;
> - und/oder öffnen Sie die Reparaturhinweise, die Poseidon für seine
>   [unerwarteten Nachrichten](#unerwartete-nachrichten) meldet: Jeder füllt das GitHub-Issue vor.
>
> Senden Sie niemals die Schlüsseldatei. Die Warnung zur Schlüsselerfassung gilt
> für den ReefATO+ wie für jedes Gerät.

Bisher übernommene Familien, aus den Spion-Läufen:

| Familie | Übernommen |
|---|---|
| ReefControl Power | Zustände, Telemetrie (einschließlich Temperatursonde); die Steckdosenzustände werden wie in der ReefBeat-App aus ihren Programmen berechnet |
| ReefDose | Zustände, Telemetrie; ein `dosing-log` (Ende einer Dosis) liest das Gerät für seine Dosierwarteschlange neu, ebenso Mitternacht (00:01, Zeit von Home Assistant), wenn die Warteschlange des neuen Tages die des endenden ersetzt |
| ReefMat | Zustände, Telemetrie, `rolling-log` (Ende eines Vorschubs) |
| ReefLED | Telemetrie |
| ReefWave | Zustände (Modus: eine Fütterung schaltet sie aus und zurück auf Auto, Einstellungen), Telemetrie (Modus, WLAN-Signal); ein in der App geschriebenes Programm (`schedule`, ohne seine Intervalle gesendet) liest sie neu. Ihre aktuelle Welle wird aus Programm und Uhrzeit abgeleitet: Den Wellenwechsel zu Beginn eines Intervalls sendet nichts (nur ihre Telemetrie zeigt ihn, innerhalb einer Minute) |
| ReefRun | Zustände, Telemetrie (Zustand, Intensität, Temperatur ihrer Pumpen: voller Becher, fehlende Pumpe...); das Ende einer Kalibrierung und eine `notification` (eine wieder anzuschließende Pumpe) lesen sie neu |
| ReefControl | Telemetrie und `probe`-Ereignisse (Sondenwerte), Zustände (Modus, Verbindung mit einem ReefControl Power, Leckmodus), Modus und Zustand seiner Ports (ein ausgeschalteter Port verbraucht 0; der Verbrauch eines eingeschalteten Ports kommt per Abfrage); eine installierte oder eingerichtete Sonde oder ein solcher Port liest ihn neu |

Bei den anderen Familien vergleicht *Shadow* nur, und *Poseidon* liest das Gerät
bei jedem gesendeten Zustand neu. *Poseidon* liest es auch neu, wenn ein Zustand
etwas meldet, das sein Merger nicht schreiben kann (eine unbekannte Einstellung,
ein ReefDose-Programm, ohne seine Intervalle gesendet). Ein solches Lesen schließt
die Konfigurationsquellen ein: Was die App ändert, sind meist Einstellungen, die
die Abfrage nie neu liest. Auch jeder vom Gerät akzeptierte Schreibbefehl der App
liest es neu: Nicht jede Einstellung wird gesendet (der Offset einer
Temperatursonde nicht).

Ein ReefControl Power ohne sensorgesteuerte Steckdose (mit oder ohne
Temperatursonde), eine ReefDose (ihre Dosierwarteschlange wird nach jeder Dosis
und um Mitternacht gelesen) und eine ReefWave (ihr Programm wird bei Änderung neu
gelesen) senden alles, was sich ändert: Mit *Poseidon* werden sie nur im
*Sicherheits-Abfrageintervall* abgefragt.

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

- **Standardstrategie**: die jedes Geräts im Poseidon-Modus ohne eigene Strategie
  (siehe [Strategien](#strategien)). Standardmäßig *Spion*.
- **Abfrageintervall der Poseidon-Strategie**, in Minuten (Standard 10).
- **Debug-Modus**: Jedes Frame, das das Relais passiert, wird entschlüsselt nach
  `/config/redsea/poseidon/logs/poseidon.jsonl` geschrieben (Rotation bei 10 MB,
  5 Dateien). Die Daten stehen dort im Klartext.
- **Wartezeit, bis ein Gerät still ist**, in Minuten (Standard 10).
- **Sicherheits-Abfrageintervall**, in Minuten (Standard 60): die Abfrage eines
  Geräts, dessen gesendete Nachrichten alles abdecken, was sich ändert, und wie
  oft das `/cloud` eines über das Relais kommunizierenden Geräts gelesen wird.
- **Unerwartete Nachrichten melden** (standardmäßig an): siehe
  [Unerwartete Nachrichten](#unerwartete-nachrichten).
- **Vorhandene Meldungen auf GitHub suchen** (standardmäßig an): Nur die Signatur
  einer unerwarteten Nachricht wird gesendet.
- **Wiederherstellungen der Cloud beim Verbinden zurückhalten** (standardmäßig
  an): siehe [Schutz beim Verbinden](#schutz-beim-verbinden).
- **Watchdog-Schlüssel**: 16 Zeichen, vorgeschlagen, solange keiner gesetzt ist.
  Das Relais beantwortet eine verschlüsselte „Lebst du“-Anfrage mit diesem
  Schlüssel:
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog)
  oder sein `poseidon_watchdog.py` allein auf einem anderen Rechner überwacht das
  Relais und schaltet die Geräte in den Normalmodus zurück, wenn es ausfällt.
  Übernehmen Sie diesen Schlüssel in dessen Konfiguration; leer lassen, um keinem
  Watchdog zu antworten.

## Unerwartete Nachrichten

Jede Nachricht, die das Relais passiert, wird mit dem Bekannten ihrer Gerätefamilie
verglichen: ein unbekanntes MQTT-Paket oder Topic, ein Cloud-Befehl an einen
unbekannten Endpoint, ein Zustand oder eine Telemetrie mit neuem, fehlendem oder
anders typisiertem Feld. Das erste Auftreten landet anonymisiert (ohne Kennungen,
Namen, Netzwerkadressen, Schlüssel) in
`/config/redsea/poseidon/logs/anomalies.jsonl`; ein unbekannter Befehl wartet 5
Sekunden auf das, was das Gerät antwortet und sendet, und wird damit gespeichert.

Jede hat eine Signatur, für alle Nutzer dieselbe. Die Issues des Repositorys werden
danach durchsucht, und ein Reparaturhinweis sagt, was zu tun ist: melden (ein
vorausgefülltes GitHub-Issue, nur von Ihnen gesendet), der offenen Meldung folgen,
auf die Version aktualisieren, die es behandelt, oder die geschlossene Meldung
lesen. Ein neues Telemetriefeld erzeugt nur dann einen Reparaturhinweis, wenn die
Suche keine Meldung gefunden hat.

## Schutz beim Verbinden

Bei jeder Verbindung eines Geräts sendet ihm die Red-Sea-Cloud ihre eigene Kopie
der Geräteeinstellungen. Ist diese Kopie veraltet, verliert das Gerät seine
aktuellen Einstellungen: Eine ReefWave verlor so ihr gesamtes Programm. In den
ersten 30 Sekunden jeder Verbindung über das Relais werden die bekannten
Wiederherstellungen der Cloud (Gruppe und Programm einer ReefWave, Futterkopf
einer ReefDose) daher zurückgehalten.

Jeder andere Befehl geht durch und wird protokolliert (`guard_passed` in der
Spion-Datei): Ein Gerät, das während der App-Nutzung neu startet (ein ReefControl,
der beim Einbau einer Sonde abstürzt), erhält die Befehle des Nutzers.

## Ereignisse

### `redsea_dose`

Wird ausgelöst, wenn eine ReefDose im Poseidon-Modus (jede Strategie) eine Dosis
beendet, geplant oder manuell, aus ihrem `dosing-log`. Eine doppelt gesendete Dosis
(nach einer Neuverbindung) wird einmal ausgelöst.

| Feld | Inhalt |
|---|---|
| `device_id` | das Gerät in Home Assistant |
| `name` | sein Name |
| `head` | Kopfnummer |
| `supplement`, `brand` | wie vom Gerät gemeldet |
| `dose_type` | `scheduled` oder `manual` |
| `volume` | dosierte Menge in mL |
| `started_at` | Beginn der Dosis, aus der vorher abgefragten Dosierwarteschlange (Ortszeit des Geräts); bei einer Dosis, die nicht darin war (die um Mitternacht, manuell aus der App), aus dem Durchfluss des Kopfes geschätzt; `null`, solange weniger als 3 Dosen des Kopfes eine gemessene Dauer haben |
| `ended_at` | Ende der Dosis (Ortszeit des Geräts) |
| `duration_s` | `ended_at` − `started_at`, `null` ohne Beginn |
| `start_estimated` | `true`, wenn `started_at` (und `duration_s`) geschätzt sind: Menge ÷ Durchfluss des Kopfes (seine letzten 20 Dosen mit gemessener Dauer) |

Beim Start einer Dosis wird nichts gesendet: Ihr Beginn ist die Zeit, die die
Dosierwarteschlange ihr gab. Die Dosis um Mitternacht steht in keiner Warteschlange
(die des endenden Tages ist dann leer, die des neuen Tages beginnt danach): Ihr
Beginn wird geschätzt.

### `redsea_notification`

Wird ausgelöst, wenn ein Gerät im Poseidon-Modus (jede Strategie) einen Alarm
sendet, den die ReefBeat-App als Benachrichtigung zeigt. Es enthält, was das Gerät
meldet:

| Feld | Inhalt |
|---|---|
| `device_id` | das Gerät in Home Assistant |
| `name` | sein Name |
| `device_type` | seine Familie: `reef-run`, `reef-control`, `reef-dosing`... |
| `type` | der Alarm, wie vom Gerät benannt |
| `sub_type` | wie vom Gerät gemeldet (`sub-type`) |
| weitere Felder | worum es beim Alarm geht: `pump` oder `pump_name` (ReefRun), `probe` (ReefControl, ihr Name), `supplement` (ReefDose) |

Bisher gesehen:

| Familie | `type` |
|---|---|
| ReefRun | `full_cup_warning` (`pump`), `no_pump` (`pump_name`) |
| ReefControl | `sensor_danger_range`, `temperature_danger_range`, `aquarium_water_leak` (`probe`) |
| ReefDose | `stock_level_empty` (`supplement`) |

```yaml
automation:
  - alias: Skimmer cup full
    triggers:
      - trigger: event
        event_type: redsea_notification
        event_data:
          type: full_cup_warning
    actions:
      - action: notify.notify
        data:
          message: "{{ trigger.event.data.name }}: the skimmer cup is full"
```

### Verlauf der Dosierungen

Jede Dosis wird außerdem pro Kopf 30 Tage lang (höchstens 5000 Dosen) gespeichert,
auch über Neustarts hinweg:

- jeder Kopf einer ReefDose erhält einen Sensor **Letzte Dosierung** (auf dem
  Kopfgerät), nur verfügbar, solange der Dosierer im Poseidon-Modus ist: Sein
  Zustand ist das Ende der letzten Dosis, seine Attribute Menge, Art, Beginn, Dauer
  und Zusatz; der Recorder speichert sie wie bei jedem Sensor;
- die Aktion `redsea.get_doses` liefert die Dosen, neueste zuerst: `device_id` (der
  Dosierer, einer seiner Köpfe oder sein Konfigurationseintrag) und optional
  `head`, `days`, `limit`;
- die ha-reef-card zeigt sie im Konfigurationsdialog eines Kopfes
  (**Dosierverlauf**).

```yaml
automation:
  - alias: Log the doses
    triggers:
      - trigger: event
        event_type: redsea_dose
    actions:
      - action: logbook.log
        data:
          name: "{{ trigger.event.data.name }}"
          message: >-
            head {{ trigger.event.data.head }}
            ({{ trigger.event.data.supplement }}):
            {{ trigger.event.data.volume }} mL,
            {{ trigger.event.data.dose_type }},
            {{ trigger.event.data.started_at }} → {{ trigger.event.data.ended_at }}
```

## Nachrichten der ReefBeat-App

Die Sensoren **Letzte Meldung** und **Letzte Alarmmeldung** (und der
Meldungsverlauf) stammen aus den Antworten der Geräte auf die Befehle von Home
Assistant, die in jedem Modus über HTTP laufen. Die Befehle der ReefBeat-App (oder
der Cloud) erreichen ein Gerät über MQTT: Im Poseidon-Modus (jede Strategie) speist
die Antwort des Geräts auf jeden Schreibbefehl (`command-response`, gleiche `uuid`)
dieselben Sensoren, wie eine HTTP-Antwort es täte:

- eine `message` (`settings updated successfully`, `head settings successfully
  saved`...) wird zur letzten Meldung;
- ein `alert` (`NoMoreDoseAlert`...), `"success": false` oder ein Fehlerstatus wird
  zum letzten Alarm.

Die Lesevorgänge der App (`GET`) enthalten keine Meldung: Sie bleiben außen vor.
Das Attribut `origin` beider Sensoren und jedes Verlaufseintrags (die Aktion
`redsea.get_messages`) sagt, woher sie kam: `ha` (ein Befehl von Home Assistant)
oder `reefbeat` (ein Befehl der App oder der Cloud). Die ha-reef-card zeigt es nach
dem Datum an.

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
