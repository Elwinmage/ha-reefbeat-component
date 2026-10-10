# Red Sea (Dispositivi ReefBeat) 🐠
> Parte dell'[**Ecosistema Progetto ReefTech**](https://elwinmage.github.io/reeftank/)
<p align="center">
  <img src="../../icon.png"  width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
![Installations](https://img.shields.io/badge/dynamic/json?label=Active%20Installs&query=estimated&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-reefbeat-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)

[![Ruff Status](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](../../badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Lingue Supportate: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)
Per aiutarci con la traduzione, segui questa [guida](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Panoramica
***Gestione Locale di Dispositivi HomeAssistant RedSea Reefbeat (senza cloud): ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave***

<!-- generated:demo-videos:start -->

## 🎬 Video dimostrativi

<table>
<tr>
<td><a href="https://www.youtube.com/watch?v=Qee5LH0T9wQ"><img src="https://img.youtube.com/vi/Qee5LH0T9wQ/0.jpg" alt="Demo ReefDose" width="300"/></a><br/><em>Demo ReefDose</em></td>
<td><a href="https://www.youtube.com/watch?v=yyNyUSitb1E"><img src="https://img.youtube.com/vi/yyNyUSitb1E/0.jpg" alt="Demo ReefMat" width="300"/></a><br/><em>Demo ReefMat</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=Xxv38OPqiGI"><img src="https://img.youtube.com/vi/Xxv38OPqiGI/0.jpg" alt="Demo ReefRun" width="300"/></a><br/><em>Demo ReefRun</em></td>
<td><a href="https://www.youtube.com/watch?v=2R0DHp2eqT4"><img src="https://img.youtube.com/vi/2R0DHp2eqT4/0.jpg" alt="Demo ReefATO+" width="300"/></a><br/><em>Demo ReefATO+</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=voFobfc7Slk"><img src="https://img.youtube.com/vi/voFobfc7Slk/0.jpg" alt="Demo ReefControl & ReefControl-Power" width="300"/></a><br/><em>Demo ReefControl & ReefControl-Power</em></td>
<td><a href="https://www.youtube.com/watch?v=pA49z8QjTN4"><img src="https://img.youtube.com/vi/pA49z8QjTN4/0.jpg" alt="Demo ReefLed" width="300"/></a><br/><em>Demo ReefLed</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=sYVeE0zV3eo"><img src="https://img.youtube.com/vi/sYVeE0zV3eo/0.jpg" alt="Demo ReefWave" width="300"/></a><br/><em>Demo ReefWave</em></td>
</tr>
</table>

<!-- generated:demo-videos:end -->

<!-- ecosystem:start -->

## Progetti correlati

I progetti ReefTech si incastrano tra loro: le integrazioni portano la tua attrezzatura in Home Assistant, la scheda la mostra e la pilota, e il backup la mantiene in funzione durante un blackout. Ognuno funziona anche da solo.

<table>
  <tr>
    <th width="100px"></th>
    <th>Progetto</th>
    <th>Ruolo</th>
    <th>Funziona con</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td>🐠<br /><b>ha-reefbeat-component</b><br /><i>(questo repository)</i></td>
    <td>Dispositivi Red Sea ReefBeat, pilotati in locale senza cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave.<br />blueprint di allerta per modalità anomale, calibrazioni e batteria scarica. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td>🌊<br /><a href="https://github.com/Elwinmage/ha-aquamedic-component"><b>ha-aquamedic-component</b></a></td>
    <td>Pompe Aqua Medic tramite l'API cloud Gizwits: pompe di movimento EcoDrift e SmartDrift, pompe DC Runner di risalita e dello schiumatoio.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td>🐙<br /><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Tracciamento di pulizia e usura per l'attrezzatura che Home Assistant non può interrogare: pompe di movimento, pompe di risalita, schiumatoi, reattori, tutto ciò che curi a mano.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td>🪸<br /><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Vista grafica interattiva di ogni dispositivo sulla tua dashboard, e unico modo per modificare le programmazioni avanzate. Legge le tre integrazioni tramite il contratto <code>reef_role</code> comune, senza configurazione lato scheda. Disegna anche i flussi di energia di reefbeatEnergyBackup. La sua scheda acquario dà vita alla vostra vasca con ha-reeftank-component.</td>
    <td>tutte e tre le integrazioni, e ha-reeftank-component per l'acquario</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reeftank-component/main/icon.png" width="64" alt="ha-reeftank-component" /></td>
    <td>🐟<br /><a href="https://github.com/Elwinmage/ha-reeftank-component"><b>ha-reeftank-component</b></a></td>
    <td>Un'immagine viva della vostra vasca sulla plancia: la vostra foto, illuminata dalle vostre vere lampade, con pesci e coralli animati, e sopra i vostri dispositivi ed entità. Conserva gli acquari e la loro fauna, registra le alimentazioni.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reeftank-catalog/main/icon.png" width="64" alt="reeftank-catalog" /></td>
    <td>🐡<br /><a href="https://github.com/Elwinmage/reeftank-catalog"><b>reeftank-catalog</b></a></td>
    <td>Pesci, coralli e texture della scheda acquario, scaricati e tenuti aggiornati da ha-reeftank-component.</td>
    <td>ha-reeftank-component</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-blueprints/main/icon.png" width="64" alt="ha-reef-blueprints" /></td>
    <td>🐬<br /><a href="https://github.com/Elwinmage/ha-reef-blueprints"><b>ha-reef-blueprints</b></a></td>
    <td>Blueprint di notifica comuni a tutto l'ecosistema: manutenzioni scadute trovate tramite il contratto <code>reef_role</code>, e dispositivi diventati irraggiungibili. Otto lingue.</td>
    <td>tutte e tre le integrazioni</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td>⚡<br /><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Backup a batteria in caso di blackout. Un pacco 24V LiFePO₄ gestito da un Raspberry Pi, con degrado progressivo della velocità delle pompe in base allo stato di carica.</td>
    <td>da solo, o insieme a ha-reefbeat-component e ha-reef-card</td>
  </tr>
</table>

Sono tutti documentati insieme sulla [pagina del progetto ReefTech](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

# Compatibilità

✅ Testato ☑️ Deve Funzionare (Se ne hai uno, puoi confermarne il funzionamento [qui](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))
<table>
<th>
<td colspan="2"><b>Modello</b></td>
<td colspan="2"><b>Stato</b></td>
<td><b><a href="https://github.com/Elwinmage/reefbeatEnergyBackup">EnergyBackup</a></b></td>
<td><b>Problemi</b> <br/>📆(Previsti) <br/> 🐛(Bug)</td>
</th>
<tr>
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefato.it.md#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="../img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefcontrol.it.md#reefcontrol">ReefControl</a></td>
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
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefcontrol-power.it.md#reefcontrol-power">ReefControl-Power</a></td>
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
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefdose.it.md#reefdose">ReefDose</a></td>
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
<td rowspan="6"> <a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefled.it.md#reefled">ReefLed</a></td>
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
<td rowspan="3"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefmat.it.md#reefmat">ReefMat</a></td>
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
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefrun.it.md#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="../img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefwave.it.md#reefwave">ReefWave (*)</a></td>
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

(*) Utenti ReefWave, leggete [questo](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefwave.it.md#reefwave)

# Sommario
- [Installazione tramite HACS](#installazione-tramite-hacs)
- [Funzioni comuni](#funzioni-comuni)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefato.it.md#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefcontrol.it.md#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefcontrol-power.it.md#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefdose.it.md#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefled.it.md#reefled)
- [LED Virtuale](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/virtual-led.it.md#led-virtuale)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefmat.it.md#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefrun.it.md#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefwave.it.md#reefwave)
- [Manutenzione](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/maintenance.it.md#manutenzione)
- [API Cloud](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/cloud-api.it.md#api-cloud)
- [FAQ](#faq)

# Installazione tramite HACS

## Installazione diretta

Clicca qui per andare direttamente al repository in HACS e premi "Scarica": [![Apri la tua istanza di Home Assistant e apri un repository nell'Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Per la card companion ha-reef-card, che offre funzioni avanzate ed ergonomiche, clicca qui per andare direttamente al repository in HACS e premi "Scarica": [![Apri la tua istanza di Home Assistant e apri un repository nell'Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Trovare in HACS
Oppure cerca "redsea" o "reefbeat" in HACS.

<p align="center">
<img src="../img/hacs_search.png" alt="Image">
</p>

# Funzioni comuni

# Icone
Questa integrazione fornisce icone personalizzate accessibili tramite "redsea:nome-icona":

<img src="../img/redsea-icons.png"/>

## Aggiungere un dispositivo
Quando aggiungi un nuovo dispositivo hai 4 possibilità:

<p align="center">
<img src="../img/add_devices_main.png" alt="Image">
</p>

### Aggiungere l'API Cloud
***Obbligatoria per ReefWave se vuoi mantenerlo sincronizzato con l'app mobile ReefBeat*** (Leggi [questo](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/reefwave.it.md#reefwave)). <br />
***Obbligatoria per essere avvisato di una nuova versione del firmware*** (Leggi [questo](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#firmware-update)).
- Ottenere le informazioni utente
- Ottenere gli acquari
- Ottenere la libreria delle onde
- Ottenere la libreria LED

<p align="center">
<img src="../img/add_devices_cloud_api.png" alt="Image">
</p>

### Rilevamento automatico sulla rete privata
Se non sei sulla stessa rete, leggi [questo](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#my-device-is-not-detected) e usa la ["Modalità Manuale"](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#manual-mode).
<p align="center">
<img src="../img/auto_detect.png" alt="Image">
</p>

### Modalità Manuale
Puoi inserire l'indirizzo IP del dispositivo o l'indirizzo di rete per il rilevamento automatico.

<p align="center">
<img src="../img/add_devices_manual.png" alt="Image">
</p>

## Configurazione del dispositivo

Clicca con il tasto destro su un dispositivo (o apri le sue opzioni dalla pagina dell'integrazione) per accedere alla configurazione. La prima schermata permette di cambiare il modo in cui l'integrazione dialoga con l'apparecchio.

<p align="center">
<img src="../img/configure_device_1.png" alt="Image">
</p>

### Impostare l'intervallo di scansione del dispositivo

Imposta ogni quanti secondi l'integrazione interroga l'apparecchio per ottenere nuovi dati.

<p align="center">
<img src="../img/configure_device_2.png" alt="Image">
</p>

### Cambiare rete WiFi

Puoi spostare un apparecchio su un'altra rete WiFi direttamente da Home Assistant, senza tornare all'app ReefBeat.

Dal menu di configurazione del dispositivo scegli **Cambia rete WiFi**. L'integrazione chiede all'apparecchio di cercare le reti vicine e le mostra in un menu a tendina, ordinate per potenza del segnale. La rete a cui l'apparecchio è attualmente connesso è preselezionata: se devi solo aggiornare la password puoi lasciare la selezione invariata.

<p align="center">
<img src="../img/device_cfg.png" alt="Image">
</p>

Scegli la rete di destinazione, inserisci la password e conferma. L'integrazione invia le nuove credenziali all'apparecchio, lo riavvia e poi lo cerca di nuovo sulla rete per aggiornarne l'indirizzo IP.

<p align="center">
<img src="../img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> Dopo un cambio di WiFi l'apparecchio può finire su una subnet diversa (per esempio passando da `192.168.0.x` a `10.0.0.x`). L'integrazione esamina tutte le subnet a cui Home Assistant è direttamente collegato. Se l'apparecchio finisce su una subnet raggiungibile solo attraverso un router, la riscoperta fallirà e ti verrà chiesto di inserire manualmente la subnet di destinazione (per esempio `10.0.0.0/24`).

## Aggiornamento Configurazione Live

> [!NOTE]
> È possibile scegliere se abilitare o meno live_update_config. In questa modalità (vecchio predefinito), i dati di configurazione vengono recuperati continuamente insieme ai dati normali. Per RSDOSE o RSLED queste richieste HTTP di grandi dimensioni possono richiedere molto tempo (7–9 secondi). A volte l'apparecchio non risponde alla richiesta, per questo è stata implementata una funzione di ritentativo. Quando live_update_config è disabilitato, i dati di configurazione vengono recuperati solo all'avvio e quando richiesto tramite il pulsante "Recupera Configurazione". Questa nuova modalità è attiva per impostazione predefinita. Puoi cambiarla nella configurazione del dispositivo. <p align="center">
<img src="../img/configure_device_live_update_config.png" alt="Image">
<img src="../img/fetch_config_button.png" alt="Image">
</p>

> [!NOTE]
> Ogni dispositivo espone anche un pulsante «Aggiorna dati». Forza una lettura immediata delle sorgenti interrogate periodicamente, senza attendere il successivo intervallo di scansione, e funziona qualunque sia l'impostazione Live_update_config — a differenza di «Recupera configurazione», che aggiorna solo le sorgenti di configurazione.

## Aggiornamento del firmware
Puoi essere avvisato e aggiornare il tuo apparecchio quando è disponibile una nuova versione del firmware. Devi avere un dispositivo ["API Cloud"](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#add-cloud-api) attivo con le tue credenziali e l'interruttore "Usa API Cloud" deve essere abilitato.
> [!TIP]
> L'"API Cloud" serve solo a ottenere il numero di versione della nuova release e a confrontarlo con la versione installata. Per aggiornare il firmware l'API Cloud non è strettamente necessaria.
> Se non usi l'"API Cloud" (interruttore disabilitato o nessun dispositivo API Cloud installato) non verrai avvisato della disponibilità di una nuova versione, ma potrai comunque usare il pulsante nascosto "Forza Aggiornamento Firmware". Se una nuova versione è disponibile, verrà installata.
<p align="center">
  <img src="../img/firmware_update_1.png" alt="Image">
  <img src="../img/firmware_update_2.png" alt="Image">
</p>

# FAQ

## Il mio dispositivo non viene rilevato
- Prova a riavviare il rilevamento automatico con il pulsante "Aggiungi voce". A volte i dispositivi non rispondono perché sono occupati.
- Se i tuoi dispositivi Red Sea non si trovano sulla stessa subnet di Home Assistant, il rilevamento automatico inizialmente fallirà e poi ti offrirà l'opzione di inserire l'indirizzo IP del tuo dispositivo o l'indirizzo della subnet in cui si trovano i tuoi dispositivi. Per il rilevamento della subnet, utilizza il formato IP/MASK, ad esempio: 192.168.14.0/255.255.255.0.
- Puoi anche utilizzare [Modalità Manuale](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#manual-mode).

<p align="center">
<img src="../img/subnetwork.png" alt="Image">
</p>

## Alcuni dati vengono aggiornati correttamente, altri no
I dati sono divisi in tre parti: data, configurazione e device-info.
- I dati vengono aggiornati regolarmente.
- I dati di configurazione vengono aggiornati solo all'avvio e quando premi il pulsante "Recupera Configurazione".
- I dati device-info vengono aggiornati solo all'avvio.

Per assicurarti che i dati di configurazione vengono aggiornati regolarmente, abilita [Aggiornamento Configurazione Live](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#live-update).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
