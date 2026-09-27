[← Zurück zur Hauptseite](README.de.md)

# Wartung

Über die Steuerung der Hardware hinaus verfolgt die Integration die
**wiederkehrenden Wartungsaufgaben** deiner Ausrüstung: das Venturi eines
Abschäumers reinigen, die Schläuche einer Dosierpumpe wechseln, die Aktivkohle
des ReefMat tauschen … Home Assistant erinnert sich daran, nicht mehr du.

Aufgaben hängen am betreffenden Gerät und am **Untergerät**, wenn das genauer
ist: einem ReefDose-Kopf, einer ReefRun-Pumpe. Ein ReefRun zeigt die Aufgaben
der Rückförderpumpe an Pumpe 1 und die des Abschäumers an Pumpe 2, nie
umgekehrt: die Liste folgt dem vom Gerät gemeldeten Pumpentyp.

## Die drei Entitäten einer Aufgabe

Jede Aufgabe erzeugt drei Entitäten, alle in den Kategorien *Konfiguration* und
*Diagnose*, damit dein Haupt-Dashboard übersichtlich bleibt:

| Entität | Rolle |
| ------- | ----- |
| `button.<Gerät>_<Aufgabe>` | **Aufgabe erledigt.** Ein Druck speichert das heutige Datum als letzte Ausführung und startet den Countdown neu. |
| `number.<Gerät>_<Aufgabe>_interval_<Einheit>` | **Intervall.** Wie oft die Aufgabe zu wiederholen ist, je nach Aufgabe in Tagen, Wochen oder Monaten. |
| `switch.<Gerät>_<Aufgabe>_notify` | **Benachrichtigungen.** Schaltet die Überfälligkeitsmeldung genau dieser Aufgabe stumm, ohne ihre Frist zu ändern. |

Der Button ist die Entität, die den Zustand trägt. Alles Abgeleitete steht in
Attributen, sodass eine einzige Entität für ein Dashboard oder eine
Automatisierung genügt:

| Attribut | Bedeutung |
| -------- | --------- |
| `last_reset` | ISO-8601-Datum des letzten Drucks, oder `null`, wenn nie ausgeführt |
| `interval_days` | Aktuelles Intervall, immer in Tagen normalisiert |
| `days_left` | Verbleibende Tage, negativ nach Ablauf der Frist |
| `overdue` | `true`, sobald `days_left` negativ ist |
| `reef_role` | `maint_<Aufgabenschlüssel>`, die stabile Markierung zum Auffinden der Aufgaben |

> [!TIP]
> `reef_role` macht das Ganze erweiterbar: Karte und Alarm-Blueprint finden die
> Aufgaben, indem sie nach diesem Attribut suchen. Eine in einer künftigen
> Version der Integration ergänzte Aufgabe erscheint in beiden ohne jede
> Aktualisierung auf deren Seite.

## Intervalle

Die Standardintervalle folgen den Empfehlungen von Red Sea und nehmen den Median
der veröffentlichten Spanne. Jede Aufgabe definiert zusätzlich ein Minimum und
ein Maximum, die von der `number`-Entität erzwungen werden: du kannst ein
Intervall an die Belastung deines Beckens anpassen, aber keinen absurden Wert
setzen.

Intervalle werden in der für die Aufgabe sinnvollen Einheit angezeigt (Wochen
für ein Venturi, Monate für einen Rotor) und intern in Tagen gespeichert, sodass
ein Einheitenwechsel nie Genauigkeit verliert.

## Persistenz

Daten und Intervalle speichert Home Assistant in
`.storage/redsea_maintenance_<entry_id>`, eine Datei je Konfigurationseintrag.
Sie überstehen Neustarts, Neuladen der Integration und Geräte-Reboots und werden
**nie an die Red-Sea-Cloud gesendet**. Wird der Konfigurationseintrag entfernt,
verschwindet auch die Datei.

## Die Wartungsansicht von ha-reef-card

Die Begleitkarte [ha-reef-card](https://github.com/Elwinmage/ha-reef-card)
sammelt alle Aufgaben der Anlage in einer eigenen Ansicht, als wäre die Wartung
ein eigenes Gerät: ein Fortschrittsbalken je Aufgabe, nach Restzeit eingefärbt,
sortierbar nach Gerät oder Fälligkeit, mit einem Button zum Abhaken, einer
Glocke zum Stummschalten und einem eingebetteten Schieberegler zum Ändern des
Intervalls.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/maintenance_task.png" alt="Wartungsaufgaben in ha-reef-card">
</p>

## Benachrichtigungen: das Alarm-Blueprint

Die Integration benachrichtigt bewusst nicht selbst: wen, wann und wie
informiert wird, entscheidest du. Diese Rolle übernimmt das mitgelieferte
Blueprint **ReefBeat watch**, das auch ungewöhnliche Modi, überfällige
Kalibrierungen, schwache Batterien und nicht erreichbare Geräte abdeckt.

### Installation

Klicke auf die Schaltfläche unten und bestätige den Import in Home Assistant:

[![Öffne deine Home-Assistant-Instanz und zeige den Blueprint-Importdialog.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-reefbeat-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fredsea_alerts.en.yaml)

Es gibt auch eine französische Fassung,
[`redsea_alerts.fr.yaml`](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/blueprints/automation/redsea_alerts.fr.yaml).
Alternativ kopierst du die Datei nach
`config/blueprints/automation/redsea_alerts/` und lädst die Automatisierungen
neu.

Erstelle anschließend eine Automatisierung aus dem Blueprint:
*Einstellungen → Automatisierungen & Szenen → Automatisierung erstellen →
Blueprint verwenden → ReefBeat watch (redsea)*.

### Konfiguration

Nur das erste Feld ist Pflicht:

| Abschnitt | Rolle |
| --------- | ----- |
| **Benachrichtigungsziele** | Die zu benachrichtigenden Mobilgeräte, ausgewählt im Geräteauswahlfeld. Der Dienst `notify.mobile_app_*` wird automatisch ermittelt. Ein Android-Benachrichtigungskanal lässt sich angeben (Standard `ReefBeat`). |
| **Wartung überfällig** | Meldet, wenn eine Aufgabe ihre Frist überschreitet. Die Option *Benachrichtigungsschalter je Aufgabe beachten* (standardmäßig aktiv) lässt die Automatisierung den `switch.*_notify`-Entitäten folgen: eine in der Karte stummgeschaltete Aufgabe schweigt damit auch in der Automatisierung. |
| **Ungewöhnlicher Modus** | Meldet, wenn ein Gerät seinen erwarteten Modus verlässt. `off_grace_minutes` (Standard 5) verhindert Fehlalarme während eines Fütterungszyklus oder eines kurzen manuellen Eingriffs. |
| **Kalibrierung überfällig** | ReefDose-Köpfe und Kalibrierungen der ReefRun-Abschäumer. |
| **Verzögerung der Sondenkalibrierung (RSRUN)** | Sonden für vollen Becher und Überschäumen der ReefRun-Abschäumer. |
| **Alarmmeldung des Geräts** | Leitet die von den Geräten selbst gesendeten Alarmmeldungen weiter. |
| **Schwache Batterie** / **Gerät nicht erreichbar** | Ohne Überraschungen. |

Jeder Abschnitt lässt sich einzeln abschalten und hat eine eigene
**Ausschlussliste**: ein Gerät im Test überflutet dich nicht mit Meldungen,
während die übrigen weiter überwacht werden. Die Automatisierung läuft im
5-Minuten-Takt und berücksichtigt im nächsten Zyklus Geräte, die der Integration
hinzugefügt oder aus ihr entfernt wurden — ohne dass du etwas ändern musst.

> [!NOTE]
> Das Blueprint überwacht **alle** Geräte der Integration und deren Untergeräte.
> Beim Hinzufügen eines neuen ReefBeat-Geräts ist nichts zu deklarieren.

---

[← Zurück zur Hauptseite](README.de.md)
