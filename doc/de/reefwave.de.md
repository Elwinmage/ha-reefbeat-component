[← Zurück zur Hauptseite](README.de.md)

# ReefWave:
> [!IMPORTANT]
> ReefWave-Geräte unterscheiden sich von den anderen ReefBeat-Geräten. Sie sind die einzigen Geräte, die der ReefBeat-Cloud untergeordnet sind.<br/>
> Wenn Sie die ReefBeat-App starten, wird der Status aller Geräte abgefragt und die Daten der App werden aus dem Gerätezustand gelesen.<br/>
> Bei ReefWave ist es umgekehrt: Es gibt keinen lokalen Steuerungspunkt (wie Sie in der ReefBeat-App sehen, kann man einem getrennten Aquarium keine ReefWave hinzufügen).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
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
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Aktuelle Werte ändern
Um die aktuellen Wellenwerte in die Vorschaufelder zu laden, verwenden Sie die Schaltfläche „Vorschau aus aktuell setzen".
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
Um die aktuellen Wellenwerte zu ändern, setzen Sie die Vorschauwerte und verwenden Sie die Schaltfläche „Vorschau speichern".

Das Verhalten entspricht dem der ReefBeat-App. Alle Wellen mit derselben ID im aktuellen Zeitplan werden aktualisiert.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

### Wartungsaufgaben
| Aufgabe | Standard | Spanne |
| ------- | -------- | ------ |
| Rotorkäfige reinigen | 2 Monate | 1 – 3 Monate |

Siehe den Abschnitt [Wartung](maintenance.de.md#wartung).

---

[← Zurück zur Hauptseite](README.de.md)
