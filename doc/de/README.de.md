# Red Sea (ReefBeat-Geräte) 🐠
> Teil des **[ReefTech Project Ökosystems](https://elwinmage.github.io/reeftank/de.html)**
<p align="center">
  <img src="../../icon.png" width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
![Installations](https://img.shields.io/badge/dynamic/json?label=Aktive%20Installationen&query=estimated&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-reefbeat-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![Ruff Status](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](../../badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)

Um bei der Übersetzung zu helfen, folgen Sie dieser [Anleitung](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Übersicht
***Lokale Verwaltung von HomeAssistant RedSea Reefbeat-Geräten (ohne Cloud): ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun und ReefWave***

<!-- generated:demo-videos:start -->

## 🎬 Demo-Videos

<table>
<tr>
<td><a href="https://www.youtube.com/watch?v=Qee5LH0T9wQ"><img src="https://img.youtube.com/vi/Qee5LH0T9wQ/0.jpg" alt="ReefDose-Demo" width="300"/></a><br/><em>ReefDose-Demo</em></td>
<td><a href="https://www.youtube.com/watch?v=yyNyUSitb1E"><img src="https://img.youtube.com/vi/yyNyUSitb1E/0.jpg" alt="ReefMat-Demo" width="300"/></a><br/><em>ReefMat-Demo</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=Xxv38OPqiGI"><img src="https://img.youtube.com/vi/Xxv38OPqiGI/0.jpg" alt="ReefRun-Demo" width="300"/></a><br/><em>ReefRun-Demo</em></td>
<td><a href="https://www.youtube.com/watch?v=2R0DHp2eqT4"><img src="https://img.youtube.com/vi/2R0DHp2eqT4/0.jpg" alt="ReefATO+-Demo" width="300"/></a><br/><em>ReefATO+-Demo</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=voFobfc7Slk"><img src="https://img.youtube.com/vi/voFobfc7Slk/0.jpg" alt="ReefControl- & ReefControl-Power-Demo" width="300"/></a><br/><em>ReefControl- & ReefControl-Power-Demo</em></td>
<td><a href="https://www.youtube.com/watch?v=pA49z8QjTN4"><img src="https://img.youtube.com/vi/pA49z8QjTN4/0.jpg" alt="ReefLed-Demo" width="300"/></a><br/><em>ReefLed-Demo</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=sYVeE0zV3eo"><img src="https://img.youtube.com/vi/sYVeE0zV3eo/0.jpg" alt="ReefWave-Demo" width="300"/></a><br/><em>ReefWave-Demo</em></td>
</tr>
</table>

<!-- generated:demo-videos:end -->

<!-- ecosystem:start -->

## Verwandte Projekte

Die ReefTech-Projekte greifen ineinander: die Integrationen bringen Ihre Geräte in Home Assistant, die Karte zeigt und steuert sie, und das Backup hält sie bei einem Stromausfall am Laufen. Jedes funktioniert auch für sich allein.

<table>
  <tr>
    <th width="100px"></th>
    <th>Projekt</th>
    <th>Funktion</th>
    <th>Arbeitet mit</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td>🐠<br /><b>ha-reefbeat-component</b><br /><i>(dieses Repository)</i></td>
    <td>Red Sea ReefBeat-Geräte, lokal gesteuert ohne Cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun und ReefWave.<br />Alarm-Blueprint für abweichende Modi, Kalibrierungen und niedrigen Akkustand. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td>🌊<br /><a href="https://github.com/Elwinmage/ha-aquamedic-component"><b>ha-aquamedic-component</b></a></td>
    <td>Aqua Medic-Pumpen über die Gizwits-Cloud-API: EcoDrift- und SmartDrift-Strömungspumpen, DC Runner Rückförder- und Abschäumerpumpen.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td>🐙<br /><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Reinigungs- und Verschleißverfolgung für Geräte, die Home Assistant nicht erreicht: Strömungspumpen, Rückförderpumpen, Abschäumer, Reaktoren, alles was von Hand gewartet wird.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td>🪸<br /><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Interaktive grafische Ansicht jedes Geräts auf Ihrem Dashboard und der einzige Weg, erweiterte Zeitpläne zu bearbeiten. Liest die drei Integrationen über den gemeinsamen <code>reef_role</code>-Vertrag, ohne Konfiguration auf Kartenseite. Zeichnet außerdem die Energieflüsse von reefbeatEnergyBackup. Ihre Aquariumkarte erweckt Ihr Becken mit ha-reeftank-component zum Leben.</td>
    <td>alle drei Integrationen und ha-reeftank-component für das Aquarium</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reeftank-component/main/icon.png" width="64" alt="ha-reeftank-component" /></td>
    <td>🐟<br /><a href="https://github.com/Elwinmage/ha-reeftank-component"><b>ha-reeftank-component</b></a></td>
    <td>Ein lebendiges Bild Ihres Beckens auf dem Dashboard: Ihr Foto, beleuchtet von Ihren echten Lampen, mit animierten Fischen und Korallen und Ihren Geräten und Entitäten darauf. Speichert die Aquarien und ihren Besatz, protokolliert die Fütterungen.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reeftank-catalog/main/icon.png" width="64" alt="reeftank-catalog" /></td>
    <td>🐡<br /><a href="https://github.com/Elwinmage/reeftank-catalog"><b>reeftank-catalog</b></a></td>
    <td>Fische, Korallen und Texturen der Aquariumkarte, von ha-reeftank-component heruntergeladen und aktuell gehalten.</td>
    <td>ha-reeftank-component</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-blueprints/main/icon.png" width="64" alt="ha-reef-blueprints" /></td>
    <td>🐬<br /><a href="https://github.com/Elwinmage/ha-reef-blueprints"><b>ha-reef-blueprints</b></a></td>
    <td>Benachrichtigungs-Blueprints für das gesamte Ökosystem: überfällige Wartungen, über den <code>reef_role</code>-Vertrag gefunden, und nicht mehr erreichbare Geräte. Acht Sprachen.</td>
    <td>alle drei Integrationen</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td>⚡<br /><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Batterie-Backup bei Stromausfall. Ein 24V LiFePO₄-Pack, gesteuert von einem Raspberry Pi, mit schrittweiser Reduzierung der Pumpendrehzahl je nach Ladezustand.</td>
    <td>eigenständig oder zusammen mit ha-reefbeat-component und ha-reef-card</td>
  </tr>
</table>

Alle zusammen sind auf der [ReefTech-Projektseite](https://elwinmage.github.io/reeftank/) dokumentiert.

<!-- ecosystem:end -->

# Kompatibilität

✅ Getestet ☑️ Sollte funktionieren (Wenn Sie eines haben, können Sie das Funktionieren [hier] bestätigen(https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))
<table>
<th>
<td colspan="2"><b>Model</b></td>
<td colspan="2"><b>Status</b></td>
<td><b><a href="https://github.com/Elwinmage/reefbeatEnergyBackup">EnergyBackup</a></b></td>
<td><b>Issues</b> <br/>📆(Planned) <br/> 🐛(Bugs)</td>
</th>
<tr>
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefato.de.md#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="../img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefcontrol.de.md#reefcontrol">ReefControl</a></td>
<td colspan="2">RSCONTROLPRO</td><td>✅</td>
<td width="200px"><img src="../img/RSCONTROLPRO.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSCONTROLLITE</td><td>☑️</td>
<td width="200px"><img src="../img/RSCONTROLLITE.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefcontrol-power.de.md#reefcontrol-power">ReefControl-Power</a></td>
<td colspan="2">RSPOWER6</td><td>✅</td>
<td width="200px"><img src="../img/RSPOWER6.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSPOWER8</td><td>☑️</td>
<td width="200px"><img src="../img/RSPOWER8.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefdose.de.md#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
<td width="200px"><img src="../img/RSDOSE2.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="../img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"> <a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefled.de.md#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="../img/rsled_g1.png"/></td>
<td align="center" rowspan="6">–</td>
<td rowspan="6">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,RSLED90,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td>RSLED90</td>
<td>✅</td>
</tr>
<tr>
<td>RSLED160</td><td>✅ </td>
</tr>
<tr>
<td rowspan="3">G2</td>
<td>RSLED60</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="../img/rsled_g2.png"/></td>
</tr>
<tr>
<td>RSLED115</td><td>✅ </td>
</tr>
<tr>
<td>RSLED170</td><td>☑️</td>
</tr>
<tr>
<td rowspan="3"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefmat.de.md#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="../img/RSMAT.png"/></td>
<td align="center" rowspan="3">–</td>
<td rowspan="3">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSMAT500</td><td>✅</td>
</tr>
<tr>
<td colspan="2">RSMAT1200</td><td>✅ </td>
</tr>
<tr>
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefrun.de.md#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="../img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefwave.de.md#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>✅</td>
<td width="200px" rowspan="2"><img src="../img/RSWAVE.png"/></td>
<td align="center" rowspan="2">✅</td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSWAVE45</td><td>✅</td>
</tr>
</table>

(*) ReefWave-Benutzer, bitte lesen Sie [dies](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefwave.de.md#reefwave)

# Zusammenfassung
- [Installation via HACS](#installation-via-hacs)
- [Gemeinsame Funktionen](#gemeinsame-funktionen)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefato.de.md#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefcontrol.de.md#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefcontrol-power.de.md#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefdose.de.md#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefled.de.md#reefled)
- [Virtuelle LED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/virtual-led.de.md#virtuelle-led)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefmat.de.md#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefrun.de.md#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefwave.de.md#reefwave)
- [Wartung](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/maintenance.de.md#wartung)
- [Cloud API](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/cloud-api.de.md#cloud-api)
- [FAQ](#faq)

# Installation via HACS

## Direkte Installation

Klicken Sie hier, um direkt zum Repository in HACS zu gelangen und auf „Herunterladen" zu klicken: [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Für die Begleit-Karte ha-reef-card mit erweiterten Funktionen klicken Sie hier, um zum Repository in HACS zu gelangen und auf „Herunterladen" zu klicken: [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## In HACS suchen
Oder suchen Sie in HACS nach „redsea" oder „reefbeat".

<p align="center">
<img src="../img/hacs_search.png" alt="Image">
</p>

# Gemeinsame Funktionen

# Symbole
Diese Integration stellt benutzerdefinierte Symbole bereit, zugänglich über "redsea:icon-name":

<img src="../img/redsea-icons.png"/>

## Gerät hinzufügen
Beim Hinzufügen eines neuen Geräts haben Sie 4 Optionen:

<p align="center">
<img src="../img/add_devices_main.png" alt="Image">
</p>

### Cloud-API hinzufügen
***Für ReefWave erforderlich, wenn Sie es mit der ReefBeat Mobile App synchronisiert halten möchten*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/reefwave.de.md#reefwave)). <br />
***Erforderlich, um über neue Firmware-Versionen benachrichtigt zu werden*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#firmware-update)).
- Benutzerinformationen abrufen
- Aquarien abrufen
- Waves-Bibliothek abrufen
- LED-Bibliothek abrufen

<p align="center">
<img src="../img/add_devices_cloud_api.png" alt="Image">
</p>

### Automatische Erkennung im privaten Netzwerk
Wenn Sie sich nicht im gleichen Netzwerk befinden, lesen Sie [dies](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#my-device-is-not-detected) und verwenden Sie den [„Manuellen Modus"](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#manual-mode).
<p align="center">
<img src="../img/auto_detect.png" alt="Image">
</p>

### Manueller Modus
Sie können die IP-Adresse Ihres Geräts oder die Netzwerkadresse für die automatische Erkennung eingeben.

<p align="center">
<img src="../img/add_devices_manual.png" alt="Image">
</p>

## Gerätekonfiguration

Klicken Sie mit der rechten Maustaste auf ein Gerät (oder öffnen Sie seine Optionen über die Integrationsseite), um zu seiner Konfiguration zu gelangen. Der erste Bildschirm legt fest, wie die Integration mit dem Gerät kommuniziert.

<p align="center">
<img src="../img/configure_device_1.png" alt="Image">
</p>

### Scan-Intervall für das Gerät festlegen

Legen Sie fest, wie oft (in Sekunden) die Integration das Gerät nach neuen Daten abfragt.

<p align="center">
<img src="../img/configure_device_2.png" alt="Image">
</p>

### WLAN-Netzwerk ändern

Sie können ein Gerät direkt aus Home Assistant in ein anderes WLAN-Netzwerk verschieben, ohne zur ReefBeat-App zurückzukehren.

Wählen Sie im Gerätekonfigurationsmenü **WLAN-Netzwerk ändern**. Die Integration fordert das Gerät auf, nach Netzwerken in der Nähe zu suchen, und zeigt sie in einer Dropdown-Liste an, sortiert nach Signalstärke. Das Netzwerk, mit dem das Gerät aktuell verbunden ist, ist vorausgewählt. Wenn Sie also nur das Passwort aktualisieren möchten, können Sie die Auswahl unverändert lassen.

<p align="center">
<img src="../img/device_cfg.png" alt="Image">
</p>

Wählen Sie das Zielnetzwerk, geben Sie dessen Passwort ein und bestätigen Sie. Die Integration sendet die neuen Zugangsdaten an das Gerät, startet es neu und sucht es anschließend automatisch im Netzwerk, um seine IP-Adresse zu aktualisieren.

<p align="center">
<img src="../img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> Nach einem WLAN-Wechsel kann das Gerät einem anderen Subnetz beitreten (zum Beispiel von `192.168.0.x` zu `10.0.0.x`). Die Integration durchsucht jedes Subnetz, mit dem Home Assistant direkt verbunden ist. Wenn das Gerät in einem Subnetz landet, das Home Assistant nur über einen Router erreichen kann, schlägt die Wiedererkennung fehl und Sie werden aufgefordert, das Zielsubnetz manuell einzugeben (zum Beispiel `10.0.0.0/24`).

## Live-Aktualisierung

> [!NOTE]
> Sie können wählen, ob live_update_config aktiviert wird oder nicht. In diesem Modus (früherer Standard) werden die Konfigurationsdaten laufend zusammen mit den normalen Daten abgerufen. Bei RSDOSE oder RSLED können diese großen HTTP-Anfragen lange dauern (7–9 Sekunden). Manchmal antwortet das Gerät nicht auf die Anfrage, daher wurde eine Wiederholungsfunktion eingebaut. Ist live_update_config deaktiviert, werden die Konfigurationsdaten nur beim Start und auf Anforderung über die Schaltfläche „Konfiguration abrufen" geladen. Dieser neue Modus ist standardmäßig aktiv. Sie können ihn in der Gerätekonfiguration ändern. <p align="center">
<img src="../img/configure_device_live_update_config.png" alt="Image">
<img src="../img/fetch_config_button.png" alt="Image">
</p>

> [!NOTE]
> Jedes Gerät bietet außerdem eine Schaltfläche „Daten abrufen". Sie erzwingt ein sofortiges Lesen der regelmäßig abgefragten Quellen, ohne auf das nächste Scan-Intervall zu warten, und funktioniert unabhängig von der Einstellung Live_update_config — anders als „Konfiguration abrufen", das nur die Konfigurationsquellen aktualisiert.

## Firmware-Aktualisierung
Sie können benachrichtigt werden und Ihr Gerät aktualisieren, wenn eine neue Firmware-Version verfügbar ist. Dazu benötigen Sie ein aktives [„Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#add-cloud-api)-Gerät mit Ihren Zugangsdaten, und der Schalter „Cloud-API verwenden" muss aktiviert sein.
> [!TIP]
> Die „Cloud API" wird nur benötigt, um die Versionsnummer der neuen Version abzurufen und mit der installierten zu vergleichen. Für die Aktualisierung der Firmware selbst ist die Cloud API nicht zwingend erforderlich.
> Wenn Sie die „Cloud API" nicht verwenden (Schalter deaktiviert oder kein Cloud-API-Gerät installiert), werden Sie nicht über eine neue Version benachrichtigt, können aber weiterhin die versteckte Schaltfläche „Firmware-Update erzwingen" verwenden. Ist eine neue Version verfügbar, wird sie installiert.
<p align="center">
  <img src="../img/firmware_update_1.png" alt="Image">
  <img src="../img/firmware_update_2.png" alt="Image">
</p>

# FAQ

## Mein Gerät wird nicht erkannt
- Versuchen Sie, die automatische Erkennung mit der Schaltfläche „Eintrag hinzufügen" neu zu starten. Sometimes devices do not respond because they are busy.
- Befinden sich Ihre Red Sea-Geräte nicht im selben Subnetz wie Home Assistant, schlägt die automatische Erkennung zunächst fehl und bietet Ihnen dann an, die IP-Adresse Ihres Geräts oder die Adresse des Subnetzes Ihrer Geräte einzugeben. Verwenden Sie für die Subnetzerkennung das Format IP/MASKE, zum Beispiel: 192.168.14.0/255.255.255.0.
- You can also use [Manual Mode](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#manual-mode).

<p align="center">
<img src="../img/subnetwork.png" alt="Image">
</p>

## Einige Daten werden korrekt aktualisiert, andere nicht.
Die Daten sind in drei Teile unterteilt: Daten, Konfiguration und Geräteinformationen.
- Daten werden regelmäßig aktualisiert.
- Konfigurationsdaten werden nur beim Start und beim Drücken der Schaltfläche „Konfiguration abrufen" aktualisiert.
- Geräteinformationen werden nur beim Starten aktualisiert.

Um sicherzustellen, dass Konfigurationsdaten regelmäßig aktualisiert werden, aktivieren Sie bitte [Live-Konfigurationsaktualisierung](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#live-update).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
