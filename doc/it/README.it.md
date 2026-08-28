# Red Sea (Dispositivi ReefBeat) 🐠
> Parte dell'[**Ecosistema Progetto ReefTech**](https://elwinmage.github.io/reeftank/)
<p align="center">
  <img src="icon.png"  width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
![Installations](https://img.shields.io/badge/dynamic/json?label=Active%20Installs&query=estimated&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-reefbeat-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)

[![Ruff Status](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Lingue Supportate: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)
Per aiutarci con la traduzione, segui questa [guida](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Panoramica
***Gestione Locale di Dispositivi HomeAssistant RedSea Reefbeat (senza cloud): ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave***

<!-- ecosystem:start -->

## Progetti correlati

I progetti ReefTech si incastrano tra loro: le integrazioni portano la tua attrezzatura in Home Assistant, la scheda la mostra e la pilota, e il backup la mantiene in funzione durante un blackout. Ognuno funziona anche da solo.

| | Progetto | Ruolo | Funziona con |
| --- | --- | --- | --- |
| <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="100" alt="ha-reefbeat-component" /> | **ha-reefbeat-component**<br />*(questo repository)* | Dispositivi Red Sea ReefBeat, pilotati in locale senza cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave.<br />Include **ReefBeat watch**, un blueprint di allerta per manutenzioni scadute, modalità anomale, batteria scarica e dispositivi irraggiungibili. [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml) | ha-reef-card |
| <img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="100" alt="ha-aquamedic-component" /> | [**ha-aquamedic-component**](https://github.com/Elwinmage/ha-aquamedic-component) | Pompe Aqua Medic tramite l'API cloud Gizwits: pompe di movimento EcoDrift e SmartDrift, pompe DC Runner di risalita e dello schiumatoio. | ha-reef-card |
| <img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="100" alt="ha-reef-maintenance-component" /> | [**ha-reef-maintenance-component**](https://github.com/Elwinmage/ha-reef-maintenance-component) | Tracciamento di pulizia e usura per l'attrezzatura che Home Assistant non può interrogare: pompe di movimento, pompe di risalita, schiumatoi, reattori, tutto ciò che curi a mano. | ha-reef-card |
| <img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="100" alt="ha-reef-card" /> | [**ha-reef-card**](https://github.com/Elwinmage/ha-reef-card) | Vista grafica interattiva di ogni dispositivo sulla tua dashboard, e unico modo per modificare le programmazioni avanzate. Legge le tre integrazioni tramite il contratto `reef_role` comune, senza configurazione lato scheda. | tutte e tre le integrazioni |
| <img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="100" alt="reefbeatEnergyBackup" /> | [**reefbeatEnergyBackup**](https://github.com/Elwinmage/reefbeatEnergyBackup) | Backup a batteria in caso di blackout. Un pacco 24V LiFePO₄ gestito da un Raspberry Pi, con degrado progressivo della velocità delle pompe in base allo stato di carica. | da solo, o insieme a ha-reefbeat-component |

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
<td><a href="#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefcontrol">ReefControl</a></td>
<td colspan="2">RSCONTROLPRO</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROLPRO.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSCONTROLLITE</td><td>☑️</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROLLITE.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="#reefcontrol-power">ReefControl-Power</a></td>
<td colspan="2">RSPOWER6</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSPOWER6.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSPOWER8</td><td>☑️</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSPOWER8.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE2.png"/></td>
<td align="center" rowspan="2">–</td>
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
<td rowspan="6"> <a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
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
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g2.png"/></td>
</tr>
<tr>
<td>RSLED115</td><td>✅ </td>
</tr>
<tr>
<td>RSLED170</td><td>☑️</td>
</tr>
<tr>
<td rowspan="3"><a href="#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSMAT.png"/></td>
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
<td><a href="#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>✅</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
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

(*) Utenti ReefWave, leggete [questo](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)

# Sommario
- [Installazione tramite HACS](https://github.com/Elwinmage/ha-reefbeat-component/#installation-via-hacs)
- [Funzioni comuni](https://github.com/Elwinmage/ha-reefbeat-component/#common-functions)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/#reefled)
- [LED Virtuale](https://github.com/Elwinmage/ha-reefbeat-component/#virtual-led)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)
- [Manutenzione](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance)
- [API Cloud](https://github.com/Elwinmage/ha-reefbeat-component/#cloud-api)
- [FAQ](https://github.com/Elwinmage/ha-reefbeat-component/#faq)

# Installazione tramite HACS

## Installazione diretta

Clicca qui per andare direttamente al repository in HACS e premi "Scarica": [![Apri la tua istanza di Home Assistant e apri un repository nell'Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Per la card companion ha-reef-card, che offre funzioni avanzate ed ergonomiche, clicca qui per andare direttamente al repository in HACS e premi "Scarica": [![Apri la tua istanza di Home Assistant e apri un repository nell'Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Trovare in HACS
Oppure cerca "redsea" o "reefbeat" in HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Image">
</p>

# Funzioni comuni

# Icone
Questa integrazione fornisce icone personalizzate accessibili tramite "redsea:nome-icona":

<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/redsea-icons.png"/>

## Aggiungere un dispositivo
Quando aggiungi un nuovo dispositivo hai 4 possibilità:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Image">
</p>

### Aggiungere l'API Cloud
***Obbligatoria per ReefWave se vuoi mantenerlo sincronizzato con l'app mobile ReefBeat*** (Leggi [questo](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)). <br />
***Obbligatoria per essere avvisato di una nuova versione del firmware*** (Leggi [questo](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update)).
- Ottenere le informazioni utente
- Ottenere gli acquari
- Ottenere la libreria delle onde
- Ottenere la libreria LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Image">
</p>

### Rilevamento automatico sulla rete privata
Se non sei sulla stessa rete, leggi [questo](#my-device-is-not-detected) e usa la ["Modalità Manuale"](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Image">
</p>

### Modalità Manuale
Puoi inserire l'indirizzo IP del dispositivo o l'indirizzo di rete per il rilevamento automatico.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Image">
</p>

## Configurazione del dispositivo

Clicca con il tasto destro su un dispositivo (o apri le sue opzioni dalla pagina dell'integrazione) per accedere alla configurazione. La prima schermata permette di cambiare il modo in cui l'integrazione dialoga con l'apparecchio.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Image">
</p>

### Impostare l'intervallo di scansione del dispositivo

Imposta ogni quanti secondi l'integrazione interroga l'apparecchio per ottenere nuovi dati.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Image">
</p>

### Cambiare rete WiFi

Puoi spostare un apparecchio su un'altra rete WiFi direttamente da Home Assistant, senza tornare all'app ReefBeat.

Dal menu di configurazione del dispositivo scegli **Cambia rete WiFi**. L'integrazione chiede all'apparecchio di cercare le reti vicine e le mostra in un menu a tendina, ordinate per potenza del segnale. La rete a cui l'apparecchio è attualmente connesso è preselezionata: se devi solo aggiornare la password puoi lasciare la selezione invariata.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/device_cfg.png" alt="Image">
</p>

Scegli la rete di destinazione, inserisci la password e conferma. L'integrazione invia le nuove credenziali all'apparecchio, lo riavvia e poi lo cerca di nuovo sulla rete per aggiornarne l'indirizzo IP.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> Dopo un cambio di WiFi l'apparecchio può finire su una subnet diversa (per esempio passando da `192.168.0.x` a `10.0.0.x`). L'integrazione esamina tutte le subnet a cui Home Assistant è direttamente collegato. Se l'apparecchio finisce su una subnet raggiungibile solo attraverso un router, la riscoperta fallirà e ti verrà chiesto di inserire manualmente la subnet di destinazione (per esempio `10.0.0.0/24`).

## Aggiornamento Configurazione Live

> [!NOTE]
> È possibile scegliere se abilitare o meno live_update_config. In questa modalità (vecchio predefinito), i dati di configurazione vengono recuperati continuamente insieme ai dati normali. Per RSDOSE o RSLED queste richieste HTTP di grandi dimensioni possono richiedere molto tempo (7–9 secondi). A volte l'apparecchio non risponde alla richiesta, per questo è stata implementata una funzione di ritentativo. Quando live_update_config è disabilitato, i dati di configurazione vengono recuperati solo all'avvio e quando richiesto tramite il pulsante "Recupera Configurazione". Questa nuova modalità è attiva per impostazione predefinita. Puoi cambiarla nella configurazione del dispositivo. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Image">
</p>

> [!NOTE]
> Ogni dispositivo espone anche un pulsante «Aggiorna dati». Forza una lettura immediata delle sorgenti interrogate periodicamente, senza attendere il successivo intervallo di scansione, e funziona qualunque sia l'impostazione Live_update_config — a differenza di «Recupera configurazione», che aggiorna solo le sorgenti di configurazione.

## Aggiornamento del firmware
Puoi essere avvisato e aggiornare il tuo apparecchio quando è disponibile una nuova versione del firmware. Devi avere un dispositivo ["API Cloud"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) attivo con le tue credenziali e l'interruttore "Usa API Cloud" deve essere abilitato.
> [!TIP]
> L'"API Cloud" serve solo a ottenere il numero di versione della nuova release e a confrontarlo con la versione installata. Per aggiornare il firmware l'API Cloud non è strettamente necessaria.
> Se non usi l'"API Cloud" (interruttore disabilitato o nessun dispositivo API Cloud installato) non verrai avvisato della disponibilità di una nuova versione, ma potrai comunque usare il pulsante nascosto "Forza Aggiornamento Firmware". Se una nuova versione è disponibile, verrà installata.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Image">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Image">
</p>

# ReefATO:
- Abilitare/disabilitare il riempimento automatico
- Riempimento manuale
- Abilitare/disabilitare il buzzer di allarme perdita
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Image">
</p>

### Attività di manutenzione
| Attività | Predefinito | Intervallo |
| -------- | ----------- | ---------- |
| Pulire la sonda EC | 6 settimane | 3 – 9 settimane |
| Pulire la pompa di risalita | 4,5 mesi | 2 – 7 mesi |

Vedi la sezione [Manutenzione](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance).

# ReefControl:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_devices.png" alt="Image">
</p>

- Leggere tutte le sonde ReefSense collegate (pH, ORP, salinità, temperatura, ATO, perdite) con valore e livello di qualità
- Stato del cicalino e del rilevatore di perdite
- Accensione/spegnimento della porta 12V DC (RSCONTROL)
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_diag.png" alt="Image">
</p>

## ReefControl-Power

L'RSPOWER (Power Center) è un apparecchio autonomo con un proprio indirizzo IP, esposto separatamente in Home Assistant.

- Stato, modalità, consumo e accensione/spegnimento per ogni presa
- 6 o 8 prese controllabili a seconda del modello (RSPOWER6 / RSPOWER8)
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_devices.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_diag.png" alt="Image">
</p>

# ReefDose:
- Modificare la dose giornaliera
- Dose manuale
- Aggiungere e rimuovere supplementi
- Modificare e controllare il volume del contenitore. Le impostazioni del volume vengono abilitate o disabilitate automaticamente in base all'interruttore di controllo del volume.
- Abilitare/disabilitare la programmazione per ogni pompa
- Configurazione dell'avviso di scorta
- Ritardo di dosaggio tra i supplementi
- Adescamento (Leggi [questo](https://github.com/Elwinmage/ha-reefbeat-component/#calibration-and-priming))
- Calibrazione (Leggi [questo](https://github.com/Elwinmage/ha-reefbeat-component/#calibration-and-priming))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Image">
</p>

### Principale
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Image">
</p>

### Teste
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Image">
</p>

#### Calibrazione e adescamento

> [!CAUTION]
> Devi seguire rigorosamente l'ordine indicato sotto (usare la [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) è più sicuro).<br /><br />
> <ins>Calibrazione</ins>:
>  1. Posiziona il contenitore graduato e premi "Avvia Calibrazione"
>  2. Inserisci il valore misurato nel campo "Dose di Calibrazione"
>  3. Premi "Imposta Valore di Calibrazione"
>  4. Svuota il contenitore graduato e premi "Prova la nuova Calibrazione". Se il valore ottenuto non è 4 mL, torna al passo 1.
>  5. Premi "Ferma e Salva Graduazione"
>
> <ins>Per l'adescamento</ins>:
>  1. (a) Premi "Avvia Adescamento"
>  2. (b) Quando il liquido esce, premi "Ferma Adescamento"
>  3. (1) Posiziona il contenitore graduato e premi "Avvia Calibrazione"
>  4. (2) Inserisci il valore misurato nel campo "Dose di Calibrazione"
>  5. (3) Premi "Imposta Valore di Calibrazione"
>  6. (4) Svuota il contenitore graduato e premi "Prova la nuova Calibrazione". Se il valore ottenuto non è 4 mL, torna al passo 1.
>  7. (5) Premi "Ferma e Salva Graduazione"
>
> ⚠️ L'adescamento deve sempre essere seguito da una calibrazione (passi da 1 a 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Image">
</p>

### Attività di manutenzione
| Attività | Livello | Predefinito | Intervallo |
| -------- | ------- | ----------- | ---------- |
| Calibrare le teste di dosaggio | Apparecchio | 90 giorni | 80 – 120 giorni |
| Sostituire teste e tubi | Per testa | 15 mesi | 11 – 19 mesi |

L'attività di sostituzione è tracciata **per testa**, quindi sostituire la testa 2
non azzera il conto alla rovescia delle altre tre. Vedi la sezione
[Manutenzione](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance).

# ReefLED:

- Leggere e impostare i canali Bianco e Blu (solo per G1: RSLED50, RSLED90, RSLED160)
- Leggere e impostare temperatura colore, intensità e luna (tutti i LED)
- Gestire l'acclimatazione. Le impostazioni di acclimatazione vengono abilitate o disabilitate automaticamente in base all'interruttore di acclimatazione.
- Gestire la fase lunare. Le impostazioni della fase lunare vengono abilitate o disabilitate automaticamente in base al relativo interruttore.
- Impostare la modalità colore manuale, con o senza durata.
- Leggere i valori di ventola e temperatura.
- Leggere nome e valore dei programmi (con supporto cloud). Solo per i LED G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Image">
</p>

***

Il supporto della temperatura colore per i LED G1 tiene conto delle specificità di ciascuno dei tre modelli.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## IMPORTANTE per i LED G1 e G2

### LED G2

#### Intensità
Poiché i LED G2 garantiscono un'intensità costante su tutta la gamma di colori, i tuoi LED non sfruttano la piena capacità al centro dello spettro. A 8.000K il canale bianco è al 100% e il canale blu allo 0% (il contrario a 23.000K). A 14.000K con intensità 100% sui G2, la potenza dei canali bianco e blu è di circa l'85%.
Ecco la curva di perdita dei G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
</p>

#### Temperatura colore
L'interfaccia dei G2 non supporta l'intera gamma di temperature. Da 8.000K a 10.000K i valori aumentano a passi di 200K, e da 10.000K a 23.000K a passi di 500K. Questo comportamento è gestito automaticamente: se scegli un valore non valido (ad esempio 8.300K), verrà selezionato automaticamente un valore valido (8.200K in questo esempio). Per questo a volte puoi osservare un piccolo aggiustamento del cursore quando scegli il colore su un G2: il cursore si riposiziona su un valore consentito.

### LED G1

I LED G1 usano il controllo dei canali bianco e blu, che permette la piena potenza su tutta la gamma, ma non un'intensità costante senza compensazione.
Per questo è stata implementata la compensazione dell'intensità.
Questa compensazione assicura lo stesso [PAR](https://it.wikipedia.org/wiki/Radiazione_fotosinteticamente_attiva) (intensità luminosa) qualunque sia la temperatura colore scelta (nella gamma da 12.000 a 23.000K).
> [!NOTE]
> Poiché Red Sea non pubblica i valori PAR sotto i 12.000K, la compensazione è disponibile solo nella gamma da 12.000 a 23.000K. Se hai un LED G1 e un PAR-metro, puoi [contattarmi](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) per aggiungere la compensazione sull'intera gamma (da 9.000 a 23.000K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

In altre parole, senza compensazione un'intensità del x% a 9.000K non fornisce lo stesso PAR che a 23.000K o 15.000K.

Ecco le curve di potenza:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

Se vuoi sfruttare tutta la potenza del tuo LED, disabilita la compensazione dell'intensità (predefinito).

Se abiliti la compensazione dell'intensità, l'intensità luminosa sarà costante su tutti i valori di temperatura colore, ma al centro della gamma non userai la piena capacità dei tuoi LED (come sui modelli G2).

Nota inoltre che, con la compensazione abilitata, il fattore di intensità può superare il 100% sui G1 se regoli manualmente i canali Bianco/Blu. Questo ti permette di sfruttare tutta la potenza dei tuoi LED!

***

### Attività di manutenzione
| Attività | Predefinito | Intervallo |
| -------- | ----------- | ---------- |
| Pulire le lenti | 3 settimane | 1 – 5 settimane |
| Spolverare ventola e griglie | 6 mesi | 5 – 7 mesi |

Le stesse due attività vengono create per ogni generazione di ReefLED, incluso il
[LED virtuale](https://github.com/Elwinmage/ha-reefbeat-component/#virtual-led).
Vedi la sezione [Manutenzione](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance).

# LED Virtuale
- Raggruppa e gestisci i LED con un dispositivo virtuale (crea un dispositivo virtuale dal pannello dell'integrazione, poi usa il pulsante di configurazione per collegare i LED).
- Puoi usare solo Kelvin e intensità per controllare i tuoi LED se hai dei G2 o un misto di G1 e G2.
- Puoi usare sia Kelvin/Intensità sia Bianco e Blu se hai solo LED G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

# ReefMat:
- Interruttore di avanzamento automatico (abilita/disabilita)
- Avanzamento programmato
- Valore di avanzamento personalizzato: permette di scegliere l'entità dell'avanzamento del rotolo
- Avanzamento manuale
- Cambiare il rotolo.
>[!TIP]
> Per un rotolo nuovo completo, imposta il "diametro del rotolo" al minimo (4,0 cm). La dimensione verrà adattata in base alla tua versione di RSMAT. Per un rotolo parzialmente usato, inserisci il valore in cm.
- Due parametri nascosti: modello e posizione, se hai bisogno di riconfigurare il tuo RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Image">
</p>

### Attività di manutenzione
| Attività | Predefinito | Intervallo |
| -------- | ----------- | ---------- |
| Sostituire il carbone attivo | 25 giorni | 2 – 5 settimane |

Vedi la sezione [Manutenzione](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance).

# ReefRun:
- Impostare la velocità delle pompe
- Gestire la sovra-schiumazione
- Gestire il rilevamento di bicchiere pieno
- Possibilità di cambiare il modello di schiumatoio

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Image">
</p>

### Principale
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Image">
</p>

### Pompe
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Image">
</p>

### Attività di manutenzione
Le attività sono associate al sottodispositivo pompa e dipendono dal suo tipo.

| Attività | Pompa | Predefinito | Intervallo |
| -------- | ----- | ----------- | ---------- |
| Pulire motore e rotore | Risalita | 4,5 mesi | 2 – 7 mesi |
| Pulire il filtro di aspirazione | Risalita | 6 settimane | 3 – 9 settimane |
| Pulire venturi e tubo dell'aria | Schiumatoio | 5 settimane | 3 – 7 settimane |
| Pulire il rotore dello schiumatoio | Schiumatoio | 4,5 mesi | 2 – 7 mesi |
| Calibrare la sonda di bicchiere pieno | Schiumatoio | 4 settimane | 2 – 6 settimane |
| Calibrare la sonda di sovra-schiumazione | Schiumatoio | 4 settimane | 2 – 6 settimane |

Le due attività di calibrazione sono sorvegliate anche dal blueprint degli
avvisi, che confronta la data dell'ultima calibrazione comunicata
dall'apparecchio con l'intervallo impostato qui. Vedi la sezione
[Manutenzione](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance).

### Chiave per smontare il rotore

L'attività *Pulire il rotore dello schiumatoio* qui sopra impone di svitare il
corpo pompa, che bagnato non offre quasi alcuna presa. Una chiave stampabile in
3D per questa operazione, con un video che ne mostra l'uso, è disponibile qui:
[Chiave per rotore di DC Skimmer Red Sea](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

# ReefWave

> [!IMPORTANT]
> I dispositivi ReefWave sono diversi dagli altri dispositivi ReefBeat. Sono gli unici dispositivi che sono slave del cloud ReefBeat.<br/>
> Quando avvii l'app mobile ReefBeat, lo stato di tutti i dispositivi viene interrogato e i dati dall'app ReefBeat vengono recuperati dallo stato del dispositivo.<br/>
> Per ReefWave è il contrario: non c'è un punto di controllo locale (come puoi vedere nell'app ReefBeat, non puoi aggiungere un ReefWave a un acquario disconnesso).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Le onde sono archiviate nella libreria utente del cloud. Quando cambi il valore di un'onda, viene modificato nella libreria cloud e applicato al nuovo orario.<br/>
> Quindi non c'è una modalità locale? Non proprio così semplice. Esiste un'API locale nascosta per controllare ReefWave, ma l'app ReefBeat non rileverà i cambiamenti. Di conseguenza, il dispositivo e Home Assistant da un lato, e l'app mobile ReefBeat dall'altro, saranno fuori sincronia. Il dispositivo e Home Assistant saranno sempre sincronizzati.<br/>
> Ora che lo sai, fai la tua scelta!

> [!NOTE]
> Le onde ReefWave hanno molti parametri collegati e l'intervallo di alcuni parametri dipende da altri parametri. Non sono stato in grado di testare tutte le possibili combinazioni. Se trovi un bug, puoi creare una segnalazione [qui](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modalità ReefWave
Come spiegato sopra, i dispositivi ReefWave sono gli unici dispositivi che possono diventare non sincronizzati con l'app ReefBeat se utilizzi l'API locale.
Sono disponibili tre modalità: Cloud, Local e Hybrid.
Puoi cambiare la modalità impostando gli interruttori "Connetti al Cloud" e "Usa API Cloud" come descritto nella tabella sottostante.

<table>
<tr>
<td>Nome Modalità</td>
<td>Interruttore Connetti al Cloud</td>
<td>Interruttore Usa API Cloud</td>
<td>Comportamento</td>
<td>ReefBeat e HA sono sincronizzati</td>
</tr>
<tr>
<td>Cloud (Predefinito)</td>
<td>✅</td>
<td>✅</td>
<td>I dati vengono recuperati tramite l'API locale. <br />I comandi on/off vengono inviati anche tramite l'API locale. <br />I comandi delle onde vengono inviati tramite l'API cloud.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>I dati vengono recuperati tramite l'API locale. <br />I comandi vengono inviati tramite l'API locale. <br />Il dispositivo viene mostrato come "spento" nell'app ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>I dati vengono recuperati tramite l'API locale. <br />I comandi vengono inviati tramite l'API locale.<br />L'app mobile ReefBeat non visualizza i valori delle onde corretti se sono stati modificati tramite HA.<br/>Home Assistant visualizza sempre i valori corretti.<br/>Puoi cambiare i valori sia dall'app ReefBeat che da Home Assistant.</td>
<td>❌</td>
</tr>
</table>

Per le modalità Cloud e Hybrid è necessario collegare il tuo account cloud ReefBeat.
Per prima cosa crea un dispositivo ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) con le tue credenziali, e il gioco è fatto!
Il sensore "Collegato all'account" verrà aggiornato con il nome del tuo account ReefBeat una volta stabilita la connessione.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Modifica dei valori correnti
Per caricare i valori dell'onda corrente nei campi di anteprima, utilizza il pulsante "Imposta Anteprima dall'Onda Corrente".
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
Per modificare i valori dell'onda corrente, imposta i valori di anteprima e utilizza il pulsante "Salva Anteprima".

Il comportamento è lo stesso dell'app mobile ReefBeat. Tutte le onde con lo stesso ID nell'orario corrente verranno aggiornate.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

### Attività di manutenzione
| Attività | Predefinito | Intervallo |
| -------- | ----------- | ---------- |
| Pulire le gabbie del rotore | 2 mesi | 1 – 3 mesi |

Vedi la sezione [Manutenzione](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance).

# Manutenzione

Oltre a pilotare l'hardware, l'integrazione tiene traccia delle **attività di
manutenzione ricorrenti** della tua attrezzatura: pulire il venturi di uno
schiumatoio, sostituire i tubi di una pompa dosatrice, cambiare il carbone
attivo del ReefMat… A ricordarsene è Home Assistant, non più tu.

Le attività sono associate al dispositivo interessato e al **sottodispositivo**
quando è più preciso: una testa di ReefDose, una pompa di ReefRun. Un ReefRun
espone le attività della pompa di risalita sulla pompa 1 e quelle dello
schiumatoio sulla pompa 2, mai il contrario: l'elenco segue il tipo di pompa
comunicato dall'apparecchio.

## Le tre entità di un'attività

Ogni attività crea tre entità, tutte nelle categorie *Configurazione* e
*Diagnostica* per non affollare la dashboard principale:

| Entità | Ruolo |
| ------ | ----- |
| `button.<dispositivo>_<attività>` | **Attività eseguita.** La pressione registra la data odierna come ultima esecuzione e fa ripartire il conto alla rovescia. |
| `number.<dispositivo>_<attività>_interval_<unità>` | **Intervallo.** Ogni quanto ripetere l'attività, in giorni, settimane o mesi a seconda del caso. |
| `switch.<dispositivo>_<attività>_notify` | **Notifiche.** Silenzia l'avviso di ritardo di quella sola attività, senza toccarne la scadenza. |

Il pulsante è l'entità che porta lo stato. Tutto ciò che ne deriva è esposto
come attributi, così una sola entità basta per costruire una dashboard o
un'automazione:

| Attributo | Significato |
| --------- | ----------- |
| `last_reset` | Data ISO-8601 dell'ultima pressione, o `null` se mai eseguita |
| `interval_days` | Intervallo corrente, sempre normalizzato in giorni |
| `days_left` | Giorni rimanenti, negativo una volta scaduta |
| `overdue` | `true` non appena `days_left` diventa negativo |
| `reef_role` | `maint_<chiave_attività>`, il marcatore stabile usato per scoprire le attività |

> [!TIP]
> È `reef_role` a rendere il tutto estensibile: la card e il blueprint degli
> avvisi scoprono le attività cercando questo attributo. Un'attività aggiunta in
> una versione futura dell'integrazione compare in entrambi senza alcun
> aggiornamento da parte loro.

## Intervalli

Gli intervalli predefiniti seguono le indicazioni di Red Sea, prendendo la
mediana dell'intervallo pubblicato. Ogni attività definisce anche un minimo e un
massimo, imposti dall'entità `number`: puoi adattare un intervallo al carico
della tua vasca, ma non impostare un valore assurdo.

Gli intervalli sono mostrati nell'unità che ha senso per l'attività (settimane
per un venturi, mesi per un rotore) e memorizzati internamente in giorni, quindi
cambiare unità non perde mai precisione.

## Persistenza

Date e intervalli sono salvati da Home Assistant in
`.storage/redsea_maintenance_<entry_id>`, un file per voce di configurazione.
Sopravvivono a riavvii, ricaricamenti dell'integrazione e riavvii degli
apparecchi, e **non vengono mai inviati al cloud Red Sea**. Rimuovendo la voce di
configurazione si rimuove anche il file.

## La vista manutenzione di ha-reef-card

La card companion [ha-reef-card](https://github.com/Elwinmage/ha-reef-card)
raccoglie tutte le attività dell'impianto in una vista dedicata, come se la
manutenzione fosse un dispositivo a sé: una barra di avanzamento per attività,
colorata in base al tempo rimanente, ordinabile per apparecchio o per scadenza,
con un pulsante per segnare l'attività come eseguita, una campanella per
silenziarla e un cursore in linea per cambiarne l'intervallo.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/maintenance_task.png" alt="Attività di manutenzione in ha-reef-card">
</p>

## Notifiche: il blueprint degli avvisi

L'integrazione non notifica da sola, ed è voluto: chi avvisare, quando e come
spetta a te. Se ne occupa il blueprint **ReefBeat watch** fornito con il
repository, che copre anche le modalità anomale, le calibrazioni scadute, le
batterie scariche e gli apparecchi irraggiungibili.

### Installazione

Clicca il pulsante qui sotto e conferma l'importazione in Home Assistant:

[![Apri la tua istanza di Home Assistant e mostra la finestra di importazione del blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-reefbeat-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fredsea_alerts.en.yaml)

È disponibile anche una versione francese,
[`redsea_alerts.fr.yaml`](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/blueprints/automation/redsea_alerts.fr.yaml).
In alternativa copia il file in
`config/blueprints/automation/redsea_alerts/` e ricarica le automazioni.

Crea poi un'automazione a partire dal blueprint:
*Impostazioni → Automazioni e scene → Crea automazione → Usa un blueprint →
ReefBeat watch (redsea)*.

### Configurazione

Solo il primo campo è obbligatorio:

| Sezione | Ruolo |
| ------- | ----- |
| **Destinatari delle notifiche** | I telefoni da avvisare, scelti nel selettore di dispositivi. Il servizio `notify.mobile_app_*` viene risolto automaticamente. Si può indicare un canale di notifica Android (`ReefBeat` di default). |
| **Manutenzione scaduta** | Avvisa quando un'attività supera la scadenza. L'opzione *Rispetta gli interruttori di notifica per attività* (attiva di default) fa obbedire l'automazione alle entità `switch.*_notify`: silenziare un'attività nella card silenzia anche l'automazione. |
| **Modalità anomala** | Avvisa quando un apparecchio esce dalla modalità attesa. `off_grace_minutes` (5 di default) evita falsi allarmi durante un ciclo di alimentazione o un breve intervento manuale. |
| **Calibrazione scaduta** | Teste di ReefDose e calibrazioni degli schiumatoi ReefRun. |
| **Ritardo di calibrazione delle sonde (RSRUN)** | Sonde di bicchiere pieno e di sovra-schiumazione degli schiumatoi ReefRun. |
| **Messaggio di avviso dell'apparecchio** | Inoltra i messaggi di avviso emessi dagli apparecchi stessi. |
| **Batteria scarica** / **Apparecchio irraggiungibile** | Senza sorprese. |

Ogni sezione si disattiva in modo indipendente e ha una propria **lista di
esclusione**: un apparecchio in prova non ti sommerge di avvisi mentre gli altri
restano sorvegliati. L'automazione gira su un ciclo di 5 minuti e tiene conto
degli apparecchi aggiunti o rimossi dall'integrazione al ciclo successivo, senza
modificare nulla.

> [!NOTE]
> Il blueprint sorveglia **tutti** i dispositivi dell'integrazione e i loro
> sottodispositivi. Non c'è nulla da dichiarare quando aggiungi un nuovo
> apparecchio ReefBeat.

# API Cloud
L'API Cloud ti consente di:
- Avviare o interrompere scorciatoie: emergenza, manutenzione e alimentazione,
- Ottenere informazioni sull'utente,
- Recuperare la libreria delle onde,
- Recuperare la libreria dei supplementi,
- Recuperare la libreria dei programmi LED,
- Ricevere notifiche di un [nuovo firmware version](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update),
- Inviare comandi a ReefWave quando la modalità "[Cloud o Hybrid](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)" è selezionata.

Le scorciatoie, i parametri delle onde e i parametri LED sono ordinati per acquario.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Image">
</p>

>[!TIP]
> Puoi disabilitare il recupero dell'elenco dei supplementi nella configurazione del dispositivo Cloud API.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Image">

***

# FAQ

## Il mio dispositivo non viene rilevato
- Prova a riavviare il rilevamento automatico con il pulsante "Aggiungi voce". A volte i dispositivi non rispondono perché sono occupati.
- Se i tuoi dispositivi Red Sea non si trovano sulla stessa subnet di Home Assistant, il rilevamento automatico inizialmente fallirà e poi ti offrirà l'opzione di inserire l'indirizzo IP del tuo dispositivo o l'indirizzo della subnet in cui si trovano i tuoi dispositivi. Per il rilevamento della subnet, utilizza il formato IP/MASK, ad esempio: 192.168.14.0/255.255.255.0.
- Puoi anche utilizzare [Modalità Manuale](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Image">
</p>

## Alcuni dati vengono aggiornati correttamente, altri no
I dati sono divisi in tre parti: data, configurazione e device-info.
- I dati vengono aggiornati regolarmente.
- I dati di configurazione vengono aggiornati solo all'avvio e quando premi il pulsante "Recupera Configurazione".
- I dati device-info vengono aggiornati solo all'avvio.

Per assicurarti che i dati di configurazione vengono aggiornati regolarmente, abilita [Aggiornamento Configurazione Live](#live-update).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
