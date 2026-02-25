[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/commits/main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

<!-- [![Clones GitHub](https://img.shields.io/badge/dynamic/json?color=success&label=uniques-clones&query=uniques&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge) -->

# Übersicht
***Lokale Verwaltung von HomeAssistant RedSea Reefbeat-Geräten (ohne Cloud): ReefATO+, ReefDose, ReefLed, ReefMat, ReefRun und ReefWave***

> [!TIP]
> ***Um die erweiterte Programmierung von ReefDose, ReefLed, ReefRun und ReefWave zu bearbeiten, musst du die [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) verwenden (in Entwicklung)***

> [!TIP]
> Die Liste der zukünftigen Implementierungen ist [hier](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement) verfügbar<br />
> Die Liste der Fehler ist [hier](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug) verfügbar<br />

***Wenn du andere Sensoren oder Aktoren benötigst, kontaktiere mich gerne [hier](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Wenn deine Geräte nicht im selben Subnetz wie dein Home Assistant sind, lies bitte [dies](README.de.md#mein-gerät-wird-nicht-erkannt).

> [!CAUTION]
> ⚠️ Dies ist kein offizielles RedSea-Repository. Nutzung auf eigene Gefahr.⚠️

# Kompatibilität

✅ Getestet ☑️ Sollte funktionieren (Wenn du eines hast, kannst du die Funktion [hier](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8) bestätigen)❌ Noch nicht unterstützt
<table>
<th>
<td colspan="2"><b>Modell</b></td>
<td colspan="2"><b>Status</b></td>
<td><b>Probleme</b> <br/>📆(Geplant) <br/> 🐛(Fehler)</td>
</th>
<tr>
<td><a href="#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td><a href="#reefcontrol">ReefControl</a></td>
<td colspan="2">RSSENSE<br />Wenn du eines hast, kontaktiere mich <a href="https://github.com/Elwinmage/ha-reefbeat-component/discussions/8">hier</a>, damit ich es hinzufügen kann.</td><td>❌</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROL.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE2.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"><a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
<td rowspan="6">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,RSLED90,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td>RSLED90</td><td>✅</td></tr>
<tr><td>RSLED160</td><td>✅ </td></tr>
<tr>
<td rowspan="3">G2</td>
<td>RSLED60</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g2.png"/></td>
</tr>
<tr><td>RSLED115</td><td>✅ </td></tr>
<tr><td>RSLED170</td><td>☑️</td></tr>
<tr>
<td rowspan="3"><a href="#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSMAT.png"/></td>
<td rowspan="3">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td colspan="2">RSMAT500</td><td>✅</td></tr>
<tr><td colspan="2">RSMAT1200</td><td>✅ </td></tr>
<tr>
<td><a href="#reefrun">ReefRun und DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td><td>☑️</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td colspan="2">RSWAVE45</td><td>✅</td></tr>
</table>

(*) ReefWave-Nutzer, bitte lies [dies](README.de.md#reefwave)

# Inhaltsverzeichnis
- [Installation über HACS](README.de.md#installation-über-hacs)
- [Gemeinsame Funktionen](README.de.md#gemeinsame-funktionen)
- [ReefATO+](README.de.md#reefato)
- [ReefControl](README.de.md#reefcontrol)
- [ReefDose](README.de.md#reefdose)
- [ReefLED](README.de.md#reefled)
- [Virtuelles LED](README.de.md#virtuelles-led)
- [ReefMat](README.de.md#reefmat)
- [ReefRun](README.de.md#reefrun)
- [ReefWave](README.de.md#reefwave)
- [Cloud API](README.de.md#cloud-api)
- [FAQ](README.de.md#faq)

# Installation über HACS

## Direkte Installation

Klicke hier, um direkt zum Repository in HACS zu gelangen und klicke auf „Herunterladen": [![Öffne deine Home Assistant-Instanz und öffne ein Repository im Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Für die Begleitkarte ha-reef-card mit erweiterten und ergonomischen Funktionen, klicke hier, um direkt zum Repository in HACS zu gelangen und klicke auf „Herunterladen": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## In HACS suchen
Oder suche nach „redsea" oder „reefbeat" in HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Bild">
</p>

# Gemeinsame Funktionen

## Gerät hinzufügen
Beim Hinzufügen eines neuen Geräts hast du vier Optionen:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Bild">
</p>

### Cloud API hinzufügen
***Erforderlich, um ReefWave mit der mobilen ReefBeat-App synchronisiert zu halten*** (Lies [dies](README.de.md#reefwave)). <br />
***Erforderlich, um über neue Firmware-Versionen benachrichtigt zu werden*** (Lies [dies](README.de.md#firmware-update)).
- Benutzerinformationen
- Aquarien
- Waves-Bibliothek
- LED-Bibliothek

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Bild">
</p>

### Automatische Erkennung im privaten Netzwerk
Wenn du nicht im selben Netzwerk bist, lies [dies](README.de.md#mein-gerät-wird-nicht-erkannt) und verwende den [„Manuellen Modus"](README.de.md#manueller-modus).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Bild">
</p>

### Manueller Modus
Du kannst die IP-Adresse oder die Netzwerkadresse deines Geräts für die automatische Erkennung eingeben.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Bild">
</p>

### Scan-Intervall für das Gerät festlegen

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Bild">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Bild">
</p>

## Live-Aktualisierung

> [!NOTE]
> Es ist möglich zu wählen, ob der Live_update_config-Modus aktiviert werden soll oder nicht. In diesem Modus (alter Standard) werden Konfigurationsdaten kontinuierlich zusammen mit den normalen Daten abgerufen. Bei RSDOSE oder RSLED können diese umfangreichen HTTP-Anfragen sehr lange dauern (7–9 Sekunden). Manchmal antwortet das Gerät nicht auf die Anfrage, weshalb eine Wiederholungsfunktion implementiert wurde. Wenn Live_update_config deaktiviert ist, werden Konfigurationsdaten nur beim Start und auf Anfrage über die Schaltfläche „Konfiguration abrufen" abgerufen. Dieser neue Modus ist standardmäßig aktiviert. Du kannst ihn in der Gerätekonfiguration ändern. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Bild">
</p>

## Firmware-Update
Du kannst benachrichtigt werden und dein Gerät aktualisieren, wenn eine neue Firmware-Version verfügbar ist. Du musst eine aktive [„Cloud API"](README.de.md#cloud-api-hinzufügen) mit deinen Zugangsdaten haben und der Schalter „Cloud API verwenden" muss aktiviert sein.
> [!TIP]
> Die „Cloud API" wird nur benötigt, um die Versionsnummer der neuen Version abzurufen und mit der installierten Version zu vergleichen. Für das Firmware-Update ist die Cloud API nicht zwingend erforderlich.
> Wenn du die „Cloud API" nicht verwendest (Option deaktiviert oder kein Cloud API-Komponente installiert), wirst du nicht benachrichtigt, wenn eine neue Version verfügbar ist, aber du kannst weiterhin die versteckte Schaltfläche „Firmware-Update erzwingen" verwenden. Wenn eine neue Version verfügbar ist, wird sie installiert.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Bild">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Bild">
</p>

# ReefATO:
- Automatische Befüllung aktivieren/deaktivieren
- Manuelle Befüllung
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Bild">
</p>

# ReefControl:
Noch nicht unterstützt. Wenn du eines hast, kontaktiere mich [hier](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8), damit ich es hinzufügen kann.

# ReefDose:
- Tagesdosis ändern
- Manuelle Dosierung
- Nahrungsergänzungsmittel hinzufügen und entfernen
- Behältervolumen ändern und steuern. Die Behältervolumen-Einstellung wird automatisch aktiviert oder deaktiviert, je nach ausgewähltem Volumen.
- Zeitplan pro Pumpe aktivieren/deaktivieren
- Bestandsalarm-Konfiguration
- Dosierungsverzögerung zwischen Nahrungsergänzungsmitteln
- Befüllung (Bitte lies [dies](README.de.md#kalibrierung-und-befüllung))
- Kalibrierung (Bitte lies [dies](README.de.md#kalibrierung-und-befüllung))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Bild">
</p>

### Hauptgerät
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Bild">
</p>

### Köpfe
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Bild">
</p>

#### Kalibrierung und Befüllung

> [!CAUTION]
> Du musst genau die folgende Reihenfolge einhalten (Die Verwendung der [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) ist sicherer).<br /><br />
> <ins>Kalibrierung</ins>:
>  1. Messzylinder positionieren und „Start Calibration" drücken
>  2. Den gemessenen Wert im Feld „Dose of Calibration" eingeben
>  3. „Set Calibration Value" drücken
>  4. Messzylinder leeren und „Test new Calibration" drücken. Wenn der erhaltene Wert nicht 4 mL beträgt, zurück zu Schritt 1.
>  5. „Stop and Save Graduation" drücken
>
> <ins>Befüllung</ins>:
>  1. (a) „Start Priming" drücken
>  2. (b) Wenn die Flüssigkeit fließt, „Stop Priming" drücken
>  3. (1) Messzylinder positionieren und „Start Calibration" drücken
>  4. (2) Den gemessenen Wert im Feld „Dose of Calibration" eingeben
>  5. (3) „Set Calibration Value" drücken
>  6. (4) Messzylinder leeren und „Test new Calibration" drücken. Wenn der erhaltene Wert nicht 4 mL beträgt, zurück zu Schritt 1.
>  7. (5) „Stop and Save Graduation" drücken
>
> ⚠️ Auf eine Befüllung muss zwingend eine Kalibrierung folgen (Schritte 1 bis 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Bild">
</p>

# ReefLED:
- Weiß-, Blau- und Mondwerte abrufen und festlegen (nur für G1: RSLED50, RSLED90, RSLED160)
- Farbtemperatur, Intensität und Mond abrufen und festlegen (alle LEDs)
- Akklimatisierung verwalten. Akklimatisierungseinstellungen werden automatisch aktiviert oder deaktiviert, je nach Akklimatisierungsschalter.
- Mondphasen verwalten. Mondphaseneinstellungen werden automatisch aktiviert oder deaktiviert, je nach Mondphasenwechsel.
- Manuellen Farbmodus mit oder ohne Dauer festlegen.
- Lüfter- und Temperaturwerte anzeigen.
- Name und Wert der Programme anzeigen (mit Cloud-Unterstützung). Nur für G1-LEDs.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Bild">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Bild">
</p>

***

Die Unterstützung der Farbtemperatur für G1-LEDs berücksichtigt die Besonderheiten jedes der drei Modelle.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Bild">
</p>

***
## WICHTIG für G1- und G2-Leuchten

### G2-LEUCHTEN

#### Intensität
Da dieser LED-Typ eine konstante Intensität über das gesamte Farbspektrum gewährleistet, nutzen deine LEDs in der Mitte des Spektrums nicht ihre volle Kapazität. Bei 8 000 K ist der weiße Kanal bei 100 % und der blaue Kanal bei 0 % (umgekehrt bei 23 000 K). Bei 14 000 K und 100 % Intensität für G2-Leuchten beträgt die Leistung der weißen und blauen Kanäle ca. 85 %.
Hier ist die Verlustkurve der G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Bild">
</p>

#### Farbtemperatur
Die Schnittstelle der G2-Leuchten unterstützt nicht den gesamten Temperaturbereich. Von 8 000 K bis 10 000 K werden die Werte in 200-K-Schritten erhöht und von 10 000 K bis 23 000 K in 500-K-Schritten. Dieses Verhalten wird berücksichtigt: Wenn du einen ungültigen Wert wählst (z. B. 8 300 K), wird automatisch ein gültiger Wert ausgewählt (in unserem Beispiel 8 200 K). Deshalb kann es manchmal vorkommen, dass du eine kleine Neujustierung des Schiebereglers beim Auswählen der Farbe an einer G2-Leuchte beobachtest: Der Cursor positioniert sich auf einem zulässigen Wert.

### G1-LEUCHTEN

G1-LEDs verwenden die Steuerung der weiß-blauen Kanäle, was volle Leistung im gesamten Bereich ermöglicht, aber ohne Kompensation keine konstante Intensität.
Deshalb wurde eine Intensitätskompensation implementiert.
Diese Kompensation stellt sicher, dass du denselben [PAR](https://de.wikipedia.org/wiki/Photosynthetisch_aktive_Strahlung)-Wert (Lichtintensität) unabhängig von deiner gewählten Farbtemperatur erhältst (im Bereich 12 000 bis 23 000 K).
> [!NOTE]
> Da RedSea keine PAR-Werte unter 12 000 K veröffentlicht, funktioniert die Kompensation nur im Bereich 12 000 bis 23 000 K. Wenn du eine G1-LED und ein PAR-Messgerät hast, kannst du mich [kontaktieren](https://github.com/Elwinmage/ha-reefbeat-component/discussions/), um die Kompensation für den vollständigen Bereich (9 000 bis 23 000 K) hinzuzufügen.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Bild">
</p>

Mit anderen Worten: Ohne Kompensation liefert eine Intensität von x % bei 9 000 K nicht denselben PAR-Wert wie bei 23 000 K oder 15 000 K.

Hier sind die Leistungskurven:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Bild">
</p>

Wenn du die volle Leistung deiner LED nutzen möchtest, deaktiviere die Intensitätskompensation (Standard).

Wenn du die Intensitätskompensation aktivierst, ist die Lichtintensität über alle Temperaturwerte konstant, aber in der Mitte des Bereichs wirst du nicht die volle Kapazität deiner LEDs nutzen (wie bei G2-Modellen).

Vergiss auch nicht, dass bei aktiviertem Kompensationsmodus der Intensitätsfaktor für G1 100 % überschreiten kann, wenn du die Weiß-/Blaukanäle manuell anpasst. So kannst du die volle Leistung deiner LEDs nutzen!

***

# Virtuelles LED
- LEDs mit einem virtuellen Gerät gruppieren und verwalten (erstelle ein virtuelles Gerät im Integrations-Panel und verwende dann die Konfigurationsschaltfläche, um die LEDs zu verknüpfen).
- Du kannst Kelvin und Intensität zur Steuerung deiner LEDs nur verwenden, wenn du G2 oder eine Mischung aus G1 und G2 hast.
- Du kannst sowohl Kelvin/Intensität als auch Weiß & Blau verwenden, wenn du nur G1 hast.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Bild">
</p>

# ReefMat:
- Automatischer Vorschubschalter (aktivieren/deaktivieren)
- Geplanter Vorschub
- Benutzerdefinierter Vorschubwert: ermöglicht die Auswahl des Rollenvorschubwerts
- Manueller Vorschub
- Rolle wechseln.
>[!TIP]
> Für eine neue volle Rolle bitte den „Rollendurchmesser" auf das Minimum (4,0 cm) einstellen. Die Größe wird entsprechend deiner RSMAT-Version angepasst. Für eine bereits verwendete Rolle den Wert in cm eingeben.
- Zwei versteckte Parameter: Modell und Position, wenn du deinen RSMAT neu konfigurieren musst
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Bild">
</p>

# ReefRun:
- Pumpengeschwindigkeit einstellen
- Überschäumung verwalten
- Erkennung eines vollen Auffangbehälters verwalten
- Skimmer-Modell ändern möglich

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Bild">
</p>

### Hauptgerät
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Bild">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Bild">
</p>

### Pumpen
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Bild">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Bild">
</p>

# ReefWave:
> [!IMPORTANT]
> ReefWave-Geräte unterscheiden sich von anderen ReefBeat-Geräten. Sie sind die einzigen Geräte, die von der ReefBeat-Cloud abhängig sind.<br/>
> Wenn du die mobile ReefBeat-App startest, wird der Status aller Geräte abgefragt und die Daten der ReefBeat-App werden aus dem Gerätestatus abgerufen.<br/>
> Bei ReefWave ist es umgekehrt: Es gibt keinen lokalen Kontrollpunkt (wie du in der ReefBeat-App sehen kannst, kannst du ein ReefWave nicht zu einem getrennten Aquarium hinzufügen).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Bild"></center><br />
> Wellen werden in der Cloud-Benutzerbibliothek gespeichert. Wenn du den Wert einer Welle änderst, wird dieser in der Cloud-Bibliothek geändert und auf die neue Programmierung angewendet.<br/>
> Gibt es also keinen lokalen Modus? Nicht ganz. Es gibt eine versteckte lokale API zur Steuerung von ReefWave, aber die ReefBeat-App erkennt die Änderungen nicht. Somit werden das Gerät und HomeAssistant auf der einen Seite und die mobile ReefBeat-App auf der anderen Seite nicht synchronisiert. Das Gerät und HomeAssistant werden immer synchronisiert sein.<br/>
> Jetzt, wo du es weißt, triff deine Wahl!

> [!NOTE]
> ReefWave-Wellen haben viele verknüpfte Parameter, und der Bereich einiger Parameter hängt von anderen Parametern ab. Ich konnte nicht alle möglichen Kombinationen testen. Wenn du einen Fehler findest, kannst du ein Ticket [hier](https://github.com/Elwinmage/ha-reefbeat-component/issues) erstellen.

## ReefWave-Modi
Wie bereits erklärt, sind ReefWave-Geräte die einzigen Geräte, die mit der ReefBeat-App nicht synchronisiert sein können, wenn du die lokale API verwendest.
Drei Modi sind verfügbar: Cloud, Lokal und Hybrid.
Du kannst die Moduseinstellungen „Verbindung zur Cloud" und „Cloud API verwenden" wie in der folgenden Tabelle beschrieben ändern.

<table>
<tr>
<td>Modusname</td>
<td>Schalter Verbindung zur Cloud</td>
<td>Schalter Cloud API verwenden</td>
<td>Verhalten</td>
<td>ReefBeat und HA sind synchronisiert</td>
</tr>
<tr>
<td>Cloud (Standard)</td>
<td>✅</td>
<td>✅</td>
<td>Daten werden über die lokale API abgerufen. <br />Ein-/Ausschaltbefehle werden ebenfalls über die lokale API gesendet. <br />Befehle werden über die Cloud API gesendet.</td>
<td>✅</td>
</tr>
<tr>
<td>Lokal</td>
<td>❌</td>
<td>❌</td>
<td>Daten werden über die lokale API abgerufen. <br />Befehle werden über die lokale API gesendet. <br />Das Gerät wird in der ReefBeat-App als „ausgeschaltet" angezeigt.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>Daten werden über die lokale API abgerufen. <br />Befehle werden über die lokale API gesendet.<br />Die mobile ReefBeat-App zeigt nicht die richtigen Wellenwerte an, wenn sie über HA geändert wurden.<br/>Home Assistant zeigt sie immer korrekt an.<br/>Du kannst Werte über die ReefBeat-App und Home Assistant ändern.</td>
<td>❌</td>
</tr>
</table>

Für die Modi Cloud und Hybrid musst du dein ReefBeat-Cloud-Konto verknüpfen.
Erstelle zunächst eine [„Cloud API"](README.de.md#cloud-api-hinzufügen) mit deinen Zugangsdaten, und das war's!
Der Sensor „Verknüpft mit Konto" wird mit dem Namen deines ReefBeat-Kontos aktualisiert, sobald die Verbindung hergestellt ist.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Bild">
</p>

## Aktuelle Werte ändern
Um die aktuellen Wellenwerte in die Vorschaufelder zu laden, verwende die Schaltfläche „Vorschau aus aktueller Welle festlegen".
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Bild">
</p>
Um die aktuellen Wellenwerte zu ändern, setze die Vorschauwerte und verwende die Schaltfläche „Vorschau speichern".

Das Verhalten ist identisch mit der mobilen ReefBeat-App. Alle Wellen mit derselben ID im aktuellen Zeitplan werden aktualisiert.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Bild">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Bild">
</p>

# Cloud API
Die Cloud API ermöglicht:
- Verknüpfungen starten oder stoppen: Notfall, Wartung und Fütterung,
- Benutzerinformationen abrufen,
- Die Waves-Bibliothek abrufen,
- Die Nahrungsergänzungsmittel-Bibliothek abrufen,
- Die LED-Programmbibliothek abrufen,
- Über [neue Firmware-Versionen](README.de.md#firmware-update) benachrichtigt werden,
- Befehle an ReefWave senden, wenn der Modus „[Cloud oder Hybrid](README.de.md#reefwave)" ausgewählt ist.

Verknüpfungen, Wellen- und LED-Parameter sind nach Aquarium sortiert.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Bild">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Bild">
</p>

>[!TIP]
> Es ist möglich, das Abrufen der Nahrungsergänzungsmittelliste über die Konfigurationsoberfläche des Cloud API-Geräts zu deaktivieren.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Bild">
***
# FAQ

## Mein Gerät wird nicht erkannt
- Versuche, die automatische Erkennung mit der Schaltfläche „Eintrag hinzufügen" neu zu starten. Manchmal antworten Geräte nicht, weil sie beschäftigt sind.
- Wenn deine RedSea-Geräte nicht im selben Subnetz wie dein Home Assistant sind, schlägt die automatische Erkennung zunächst fehl und bietet dir an, die IP-Adresse deines Geräts oder die Subnetz-Adresse einzugeben, wo sich deine Geräte befinden. Für die Subnetz-Erkennung verwende bitte das Format IP/MASKE, wie in diesem Beispiel: 192.168.14.0/255.255.255.0.
- Du kannst auch den [manuellen Modus](README.de.md#manueller-modus) verwenden.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Bild">
</p>

## Einige Daten werden korrekt aktualisiert, andere nicht.
Die Daten sind in drei Teile unterteilt: Daten, Konfiguration und Geräteinformationen.
- Daten werden regelmäßig aktualisiert.
- Konfigurationsdaten werden nur beim Start und wenn du die Schaltfläche „fetch-config" drückst, aktualisiert.
- Geräteinformationen werden nur beim Start aktualisiert.

Um sicherzustellen, dass Konfigurationsdaten regelmäßig aktualisiert werden, aktiviere bitte die [Live-Konfigurationsaktualisierung](README.de.md#live-aktualisierung).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
