[← Zurück zur Hauptseite](README.de.md)

# ReefWave:
> [!IMPORTANT]
> ReefWave-Geräte unterscheiden sich von den anderen ReefBeat-Geräten. Sie sind die einzigen Geräte, die der ReefBeat-Cloud untergeordnet sind.<br/>
> Wenn Sie die ReefBeat-App starten, wird der Status aller Geräte abgefragt und die Daten der App werden aus dem Gerätezustand gelesen.<br/>
> Bei ReefWave ist es umgekehrt: Es gibt keinen lokalen Steuerungspunkt (wie Sie in der ReefBeat-App sehen, kann man einem getrennten Aquarium keine ReefWave hinzufügen).<br/>
> <center><img width="20%" src="../img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Die Wellen werden in der Benutzerbibliothek in der Cloud gespeichert. Wenn Sie einen Wert einer Welle ändern, wird er in der Cloud-Bibliothek geändert und auf den neuen Zeitplan angewendet.<br/>
> Gibt es also keinen lokalen Modus? So einfach ist es nicht. Es gibt eine versteckte lokale API zur Steuerung der ReefWave, aber die ReefBeat-App erkennt die Änderungen nicht. Dadurch sind das Gerät und Home Assistant auf der einen Seite und die ReefBeat-App auf der anderen nicht mehr synchron. Gerät und Home Assistant sind dagegen immer synchron.<br/>
> Jetzt wissen Sie Bescheid, treffen Sie Ihre Wahl!

> [!NOTE]
> ReefWave-Wellen haben viele voneinander abhängige Parameter, und der Bereich einiger Parameter hängt von anderen ab. Ich konnte nicht alle möglichen Kombinationen testen. Wenn Sie einen Fehler finden, können Sie [hier](https://github.com/Elwinmage/ha-reefbeat-component/issues) ein Issue erstellen.

## ReefWave-Modi
Wie oben erklärt, sind ReefWave-Geräte die einzigen, die bei Nutzung der lokalen API mit der ReefBeat-App asynchron werden können.
Es stehen drei Modi zur Verfügung: Cloud, Lokal und Hybrid.
Sie können den Modus durch Einstellen der Schalter „Mit Cloud verbinden" und „Cloud-API verwenden" ändern, wie in der folgenden Tabelle beschrieben.

<table>
<tr>
<td>Modusname</td>
<td>Schalter Mit Cloud verbinden</td>
<td>Schalter Cloud-API verwenden</td>
<td>Verhalten</td>
<td>ReefBeat und HA sind synchronisiert</td>
</tr>
<tr>
<td>Cloud (Standard)</td>
<td>✅</td>
<td>✅</td>
<td>Die Daten werden über die lokale API abgerufen. <br />Ein-/Aus-Befehle werden ebenfalls über die lokale API gesendet. <br />Wellenbefehle werden über die Cloud-API gesendet.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Die Daten werden über die lokale API abgerufen. <br />Befehle werden über die lokale API gesendet. <br />Das Gerät wird in der ReefBeat-App als „aus" angezeigt.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>Die Daten werden über die lokale API abgerufen. <br />Befehle werden über die lokale API gesendet.<br />Die ReefBeat-App zeigt nicht die richtigen Wellenwerte an, wenn sie über HA geändert wurden.<br/>Home Assistant zeigt immer die richtigen Werte an.<br/>Sie können die Werte sowohl in der ReefBeat-App als auch in Home Assistant ändern.</td>
<td>❌</td>
</tr>
</table>

Für den Cloud- und den Hybridmodus müssen Sie Ihr ReefBeat-Cloud-Konto verknüpfen.
Legen Sie zuerst ein [„Cloud API"](../../README.md#add-cloud-api)-Gerät mit Ihren Zugangsdaten an, und das war es schon!
Der Sensor „Verknüpft mit Konto" zeigt den Namen Ihres ReefBeat-Kontos an, sobald die Verbindung hergestellt ist.
<p align="center">
<img src="../img/rswave_linked.png" alt="Image">
</p>

## Aktuelle Werte ändern
Um die aktuellen Wellenwerte in die Vorschaufelder zu laden, verwenden Sie die Schaltfläche „Vorschau aus aktuell setzen".
<p align="center">
<img src="../img/rswave_set_preview.png" alt="Image">
</p>
Um die aktuellen Wellenwerte zu ändern, setzen Sie die Vorschauwerte und verwenden Sie die Schaltfläche „Vorschau speichern".

Das Verhalten entspricht dem der ReefBeat-App. Alle Wellen mit derselben ID im aktuellen Zeitplan werden aktualisiert.
<p align="center">
<img src="../img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="../img/rswave_conf.png" alt="Image">
<img src="../img/rswave_sensors.png" alt="Image">
<img src="../img/rswave_diag.png" alt="Image">
</p>

## Gruppen
Wie in der ReefBeat-App bilden alle gruppierten ReefWaves eines Aquariums
eine Gruppe (nur mit einem Cloud-Konto).

| Entität | Rolle |
| ------- | ----- |
| `switch` Mit dem Aquarium gruppiert | Gruppiert die Pumpe mit den anderen ReefWaves ihres Aquariums oder hebt die Gruppierung auf; eine neu hinzukommende Pumpe steht an letzter Stelle. Ohne Cloud-Konto nicht verfügbar |
| `sensor` Verknüpfte ReefWaves | Anzahl der Pumpen der Gruppe, ihre Liste im Attribut `waves` (`hwid`, `name`, `model`, `entry_id`, `available`) |

Ein Programm wird auf jede Pumpe der Gruppe geschrieben: gleiche
Zeitfenster, jede Pumpe mit ihren eigenen Intensitäten. Wie in der App wird
ein Schreibvorgang abgelehnt, wenn eine Pumpe der Gruppe nicht geladen ist
oder nicht antwortet: Es wird nichts gesendet, die Gruppe bleibt also
synchron. Nach einer Gruppenänderung werden alle geladenen ReefWaves
aktualisiert.

## Tagesprogramm
Der `sensor` Wellentyp trägt das gesamte Tagesprogramm im
Attribut `schedule`: die Liste seiner Intervalle, jedes beginnt bei `st`
(Minute des Tages) und läuft bis zum nächsten, mit `wave_uid`, `name`,
`type`, `direction`, `frt`, `rrt`, `fti`, `rti`, `sn`, `pd` und `sync`.
ha-reef-card zeichnet daraus den Tag.

## Dienste
Diese Dienste steuern die Wellenbibliothek und das Tagesprogramm, wie es die
ReefBeat-App tut; die Editoren von ha-reef-card verwenden sie. `device_id`
ist der Konfigurationseintrag der ReefWave.

| Dienst | Rolle |
| ------ | ----- |
| `redsea.wave_library` | Wellen des Aquariums der Pumpe, mit den Intensitäten dieser Pumpe, den Pumpen, die jede Welle verwenden, und der Gruppe der Pumpe. Ohne Cloud-Konto: die Wellen ihres eigenen Programms |
| `redsea.wave_library_save` | Erstellt eine Welle oder aktualisiert eine (`uid`). Die Form wird geteilt, die Intensitäten sind die der Pumpe; die Programme, die eine aktualisierte Welle verwenden, werden neu geschrieben. Red-Sea-Wellen und bereits vergebene Namen werden abgelehnt |
| `redsea.wave_library_delete` | Löscht eine Ihrer Wellen; abgelehnt für eine Red-Sea-Welle oder eine von einem Programm verwendete Welle |
| `redsea.wave_program_save` | Schreibt das Tagesprogramm (`slots`: `st`, `wave_uid`, `direction`; das erste beginnt bei 0) auf jede Pumpe der Gruppe; ohne Cloud-Konto auf die Pumpe selbst |
| `redsea.wave_preview` | Lässt eine Welle 1 bis 10 min auf der Pumpe laufen, danach zurück zu ihrem Programm |
| `redsea.wave_preview_stop` | Beendet die Vorschau |
| `redsea.wave_pump_set` | Richtung und Intensitäten dieser Pumpe in der aktuellen Welle (auch einer Red-Sea-Welle); die anderen Pumpen der Gruppe bleiben unverändert |
| `redsea.wave_group_set` | Gruppiert eine Pumpe oder hebt die Gruppierung auf (`grouped`), wie der Schalter |
| `redsea.wave_group_order` | Reihenfolge der Pumpen der Gruppe (`hwids`, jede Pumpe einmal genannt) |

Die Bibliothek benötigt ein ReefBeat-Cloud-Konto: Ohne Konto werden
`wave_library_save` und `wave_library_delete` abgelehnt. Alle Ablehnungen
sind übersetzte Home-Assistant-Fehler.

## Symbole
Die Wellentyp-Piktogramme der App stehen als `redsea:wave-uniform`,
`redsea:wave-random`, `redsea:wave-regular`, `redsea:wave-step`,
`redsea:wave-surface` und `redsea:wave-none` zur Verfügung.

### Wartungsaufgaben
| Aufgabe | Standard | Spanne |
| ------- | -------- | ------ |
| Rotorkäfige reinigen | 2 Monate | 1 – 3 Monate |

Siehe den Abschnitt [Wartung](maintenance.de.md#wartung).

---

[← Zurück zur Hauptseite](README.de.md)
