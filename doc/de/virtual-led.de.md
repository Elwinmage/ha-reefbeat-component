[← Zurück zur Hauptseite](README.de.md)

# Virtuelle LED
Eine virtuelle LED ist eine **Gruppe** von ReefLEDs, wie die „gruppierten"
LEDs der ReefBeat-App: Ihre Leuchten werden wie eine einzige gesteuert.

- Erstellen Sie ein virtuelles Gerät im Integrationsbereich und verwenden
  Sie dann die Schaltfläche „Konfigurieren": Wählen Sie die LEDs (mindestens
  zwei, eine LED gehört höchstens zu einer Gruppe) und dann ihre
  Reihenfolge. Eine neue virtuelle LED beginnt mit den Leuchten, die die
  ReefBeat-App bereits gruppiert, in der Reihenfolge der App.
- Sie können Kelvin und Intensität zur Steuerung nur verwenden, wenn Sie G2 oder eine Mischung aus G1 und G2 haben.
- Sie können sowohl Kelvin/Intensität als auch Weiß & Blau verwenden, wenn Sie nur G1-Leuchten haben.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

## Was die Gruppe teilt
Ein gemeinsamer Wert, der auf der virtuellen LED oder auf einer ihrer
Leuchten gesetzt wird, gilt für alle Leuchten der Gruppe: manuelle Kanäle,
Kelvin / Intensität, Modus, Timer, Programme, Akklimatisierung, Mondphase
und das [Wetterprogramm](reefled.de.md#wetterprogramm). Was zu einer Leuchte gehört, bleibt auf
der Leuchte: Name, WLAN, Cloud, Firmware, Identifizieren, Zurücksetzen…

Wie in der App wird ein Schreibvorgang der Gruppe abgelehnt, wenn eine der
Leuchten nicht geladen ist, nicht antwortet oder sich in einem Modus
befindet, den die Gruppe nicht steuern kann (aus, oder von einer Verknüpfung
gehalten): Es wird nichts gesendet, die Leuchten bleiben also synchron, und
der Fehler nennt die betroffenen Leuchten. Eine in der App außer Betrieb
gesetzte Leuchte wird bei Schreibvorgängen, Prüfungen und dem versetzten
Sonnenaufgang ausgelassen. Weiß / Blau kann auf einer Gruppe mit einer
G2-Leuchte nicht gesetzt werden: Verwenden Sie Kelvin / Intensität.

## Versetzter Sonnenaufgang
Wie in der App können die Leuchten einer Gruppe ihren Tag nacheinander
beginnen:

| Entität | Rolle |
| ------- | ----- |
| `switch` Versetzter Sonnenaufgang | Versetzt den Sonnenaufgang der Leuchten der Gruppe |
| `number` Verzögerung des versetzten Sonnenaufgangs | Minuten zwischen zwei Leuchten, 1 bis 15 (Standard 10) |

Jede Leuchte beginnt ihren Tag `Verzögerung × Position` Minuten später (die
erste Leuchte der Gruppe wird nicht verzögert). Der Wert wird in den
Sonnenaufgang-Versatz jeder Leuchte geschrieben, erneut sobald sich
die Leuchten der Gruppe oder ihre Reihenfolge ändern; eine Leuchte, die die
Gruppe verlässt, geht auf 0 zurück.

## Die Leuchten der Gruppe
Der `sensor` Verknüpfte LEDs, auf der virtuellen LED und auf jeder
Leuchte einer Gruppe, gibt die Anzahl der Leuchten und im Attribut `leds`
ihre Liste in der Reihenfolge der Gruppe an: `hwid`, `name`, `model`, `g2`,
`offset` (Sonnenaufgang-Versatz in Minuten, leer bei einer Leuchte ohne
`/offset`) und `entry_id`. ha-reef-card listet damit die Leuchten auf.

## Synchronisierung mit der ReefBeat-App
Mit einem ReefBeat-Cloud-Konto ([Cloud-API](README.de.md#cloud-api-hinzufügen)) ist eine Gruppe,
deren Leuchten von einem Modell, in einem Aquarium und in einem Konto sind,
dieselbe Gruppe in der App: Die Gruppe, ihre Reihenfolge und ihr versetzter
Sonnenaufgang werden in die Cloud geschrieben oder aus der App übernommen,
je nachdem, welche Seite sich seit der letzten Synchronisierung geändert
hat.

Eine Gruppe der App, die keine virtuelle LED steuert (mindestens zwei in
Home Assistant geladene Leuchten), wird unter den „Entdeckten" Geräten als
neue virtuelle LED vorgeschlagen, mit ihren Leuchten in der Reihenfolge der
App; „Ignorieren" lässt sie ignoriert.

Wenn eine Entscheidung bei Ihnen liegt, wird eine Reparatur gemeldet
(Einstellungen > System > Reparaturen):

| Reparatur | Was zu tun ist |
| --------- | -------------- |
| Kein ReefBeat-Cloud-Konto | Die App könnte die Gruppe führen, aber kein Cloud-Konto listet ihre Leuchten: Fügen Sie das Konto hinzu (die Reparatur verschwindet von selbst) oder behalten Sie die Gruppe nur in Home Assistant |
| LEDs in der ReefBeat-App gruppiert | Die Gruppe enthält mehrere Modelle, die die App nicht gruppieren kann, und einige Leuchten sind in der App noch gruppiert: Heben Sie dort die Gruppierung auf; die Gruppe lebt dann nur in Home Assistant |
| In Home Assistant und in der ReefBeat-App geändert | Beide Seiten haben sich seit der letzten Synchronisierung geändert: Wählen Sie die Gruppe, die bleiben soll |

---

[← Zurück zur Hauptseite](README.de.md)
