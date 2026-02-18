[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/commits/main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

<!-- [![Clones GitHub](https://img.shields.io/badge/dynamic/json?color=success&label=uniques-clones&query=uniques&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge) -->

# Presentazione
***Gestione locale dei dispositivi HomeAssistant RedSea Reefbeat (senza cloud): ReefATO+, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave***

> [!TIP]
> ***Per modificare la programmazione avanzata di ReefDose, ReefLed, ReefRun e ReefWave, è necessario utilizzare la [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) (in fase di sviluppo)***

> [!TIP]
> L'elenco delle future implementazioni è disponibile [qui](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> L'elenco dei bug è disponibile [qui](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***Se hai bisogno di altri sensori o attuatori, non esitare a contattarmi [qui](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Se i tuoi dispositivi non sono nella stessa sottorete di Home Assistant, leggi [questo](README.it.md#il-mio-dispositivo-non-viene-rilevato).

> [!CAUTION]
> ⚠️ Questo non è un repository ufficiale RedSea. Utilizzare a proprio rischio.⚠️

# Compatibilità

✅ Testato ☑️ Dovrebbe funzionare (Se ne hai uno, puoi confermare che funziona [qui](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))❌ Non ancora supportato
<table>
<th>
<td colspan="2"><b>Modello</b></td>
<td colspan="2"><b>Stato</b></td>
<td><b>Problemi</b> <br/>📆(Pianificato) <br/> 🐛(Bug)</td>
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
<td colspan="2">RSSENSE<br />Se ne hai uno, contattami <a href="https://github.com/Elwinmage/ha-reefbeat-component/discussions/8">qui</a> per aggiungerne il supporto.</td><td>❌</td>
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
<td><a href="#reefrun">ReefRun e DC Skimmer</a></td>
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

(*) Utenti ReefWave, leggete [questo](README.it.md#reefwave)

# Indice
- [Installazione tramite HACS](README.it.md#installazione-tramite-hacs)
- [Funzioni comuni](README.it.md#funzioni-comuni)
- [ReefATO+](README.it.md#reefato)
- [ReefControl](README.it.md#reefcontrol)
- [ReefDose](README.it.md#reefdose)
- [ReefLED](README.it.md#reefled)
- [LED virtuale](README.it.md#led-virtuale)
- [ReefMat](README.it.md#reefmat)
- [ReefRun](README.it.md#reefrun)
- [ReefWave](README.it.md#reefwave)
- [API Cloud](README.it.md#api-cloud)
- [FAQ](README.it.md#faq)

# Installazione tramite HACS

## Installazione diretta

Clicca qui per accedere direttamente al repository in HACS e clicca su «Scarica»: [![Apri la tua istanza Home Assistant e apri un repository nel Community Store di Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Per la scheda companion ha-reef-card che offre funzionalità avanzate ed ergonomiche, clicca qui per accedere direttamente al repository in HACS e clicca su «Scarica»: [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Cerca in HACS
Oppure cerca «redsea» o «reefbeat» in HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Immagine">
</p>

# Funzioni comuni

## Aggiungere un dispositivo
Quando si aggiunge un nuovo dispositivo, hai quattro opzioni:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Immagine">
</p>

### Aggiungere l'API Cloud
***Obbligatorio per mantenere i ReefWave sincronizzati con l'applicazione mobile ReefBeat*** (Leggi [questo](README.it.md#reefwave)). <br />
***Obbligatorio per essere notificato delle nuove versioni del firmware*** (Leggi [questo](README.it.md#aggiornamento-firmware)).
- Informazioni utente
- Acquari
- Libreria Wave
- Libreria LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Immagine">
</p>

### Rilevamento automatico sulla rete privata
Se non sei sulla stessa rete, leggi [questo](README.it.md#il-mio-dispositivo-non-viene-rilevato) e usa la modalità [«Manuale»](README.it.md#modalità-manuale).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Immagine">
</p>

### Modalità manuale
Puoi inserire l'indirizzo IP o l'indirizzo di rete del tuo dispositivo per il rilevamento automatico.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Immagine">
</p>

### Impostare l'intervallo di scansione del dispositivo

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Immagine">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Immagine">
</p>

## Aggiornamento in tempo reale

> [!NOTE]
> È possibile scegliere se attivare o meno la modalità Live_update_config. In questa modalità (vecchia impostazione predefinita), i dati di configurazione vengono recuperati continuamente insieme ai dati normali. Per RSDOSE o RSLED, queste richieste HTTP voluminose possono richiedere molto tempo (7-9 secondi). A volte il dispositivo non risponde alla richiesta, quindi è stata implementata una funzione di ripetizione. Quando Live_update_config è disabilitato, i dati di configurazione vengono recuperati solo all'avvio e su richiesta tramite il pulsante «Recupera configurazione». Questa nuova modalità è attiva per impostazione predefinita. Puoi modificarla nella configurazione del dispositivo. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Immagine">
</p>

## Aggiornamento Firmware
Puoi ricevere notifiche e aggiornare il tuo dispositivo quando è disponibile una nuova versione del firmware. Devi avere un componente [«API Cloud»](README.it.md#aggiungere-lapi-cloud) attivo con le tue credenziali e l'interruttore «Usa API Cloud» deve essere abilitato.
> [!TIP]
> L'«API Cloud» è necessaria solo per ottenere il numero di versione della nuova versione e confrontarlo con la versione installata. Per aggiornare il firmware, l'API Cloud non è indispensabile.
> Se non usi l'«API Cloud» (opzione disabilitata o componente API Cloud non installato), non verrai avvisato quando è disponibile una nuova versione, ma puoi comunque utilizzare il pulsante nascosto «Forza aggiornamento firmware». Se è disponibile una nuova versione, verrà installata.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Immagine">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Immagine">
</p>

# ReefATO:
- Attivare/disattivare il riempimento automatico
- Riempimento manuale
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Immagine">
</p>

# ReefControl:
Non ancora supportato. Se ne hai uno, contattami [qui](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8) per aggiungerne il supporto.

# ReefDose:
- Modificare la dose giornaliera
- Dose manuale
- Aggiungere e rimuovere integratori
- Modificare e controllare il volume del contenitore. L'impostazione del volume del contenitore viene attivata o disattivata automaticamente in base al volume selezionato.
- Attivare/disattivare la programmazione per pompa
- Configurazione degli avvisi di scorta
- Ritardo di dosaggio tra gli integratori
- Preparazione (Leggi [questo](README.it.md#calibrazione-e-preparazione))
- Calibrazione (Leggi [questo](README.it.md#calibrazione-e-preparazione))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Immagine">
</p>

### Principale
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Immagine">
</p>

### Testine
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Immagine">
</p>

#### Calibrazione e preparazione

> [!CAUTION]
> Devi seguire esattamente il seguente ordine (L'uso di [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) è più sicuro).<br /><br />
> <ins>Calibrazione</ins>:
>  1. Posiziona il cilindro graduato e premi "Start Calibration"
>  2. Indica il valore misurato usando il campo "Dose of Calibration"
>  3. Premi "Set Calibration Value"
>  4. Svuota il cilindro graduato e premi "Test new Calibration". Se il valore ottenuto è diverso da 4 mL, torna al passo 1.
>  5. Premi "Stop and Save Graduation"
>
> <ins>Preparazione</ins>:
>  1. (a) Premi "Start Priming"
>  2. (b) Quando il liquido scorre, premi "Stop Priming"
>  3. (1) Posiziona il cilindro graduato e premi "Start Calibration"
>  4. (2) Indica il valore misurato usando il campo "Dose of Calibration"
>  5. (3) Premi "Set Calibration Value"
>  6. (4) Svuota il cilindro graduato e premi "Test new Calibration". Se il valore ottenuto è diverso da 4 mL, torna al passo 1.
>  7. (5) Premi "Stop and Save Graduation"
>
> ⚠️ La preparazione deve essere obbligatoriamente seguita da una calibrazione (passi da 1 a 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Immagine">
</p>

# ReefLED:
- Ottenere e impostare i valori di bianco, blu e luna (solo per G1: RSLED50, RSLED90, RSLED160)
- Ottenere e impostare la temperatura del colore, l'intensità e la luna (tutti i LED)
- Gestire l'acclimatazione. Le impostazioni di acclimatazione vengono attivate o disattivate automaticamente in base all'interruttore di acclimatazione.
- Gestire le fasi lunari. Le impostazioni delle fasi lunari vengono attivate o disattivate automaticamente in base al cambio di fase lunare.
- Impostare la modalità colore manuale con o senza durata.
- Visualizzare i parametri della ventola e della temperatura.
- Visualizzare il nome e il valore dei programmi (con supporto cloud). Solo per LED G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Immagine">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Immagine">
</p>

***

Il supporto della temperatura del colore per i LED G1 tiene conto delle specificità di ciascuno dei tre modelli.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Immagine">
</p>

***
## IMPORTANTE per le lampade G1 e G2

### LAMPADE G2

#### Intensità
Poiché questo tipo di LED garantisce un'intensità costante sull'intera gamma di colori, i tuoi LED non sfruttano appieno la loro capacità nel mezzo dello spettro. A 8 000 K, il canale bianco è al 100% e il canale blu allo 0% (il contrario a 23 000 K). A 14 000 K e con un'intensità del 100% per le lampade G2, la potenza dei canali bianco e blu è di circa l'85%.
Ecco la curva di perdita dei G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Immagine">
</p>

#### Temperatura del colore
L'interfaccia delle lampade G2 non supporta l'intera gamma di temperatura. Da 8 000 K a 10 000 K, i valori si incrementano in passi di 200 K e da 10 000 K a 23 000 K in passi di 500 K. Questo comportamento è previsto: se si sceglie un valore non valido (ad esempio 8 300 K), verrà selezionato automaticamente un valore valido (8 200 K nel nostro esempio). Ecco perché a volte si può osservare un piccolo riadattamento del cursore durante la selezione del colore su una lampada G2: il cursore si riposiziona su un valore consentito.

### LAMPADE G1

I LED G1 utilizzano il controllo dei canali bianco e blu, il che consente la piena potenza sull'intera gamma, ma senza un'intensità costante senza compensazione.
Per questo è stata implementata una compensazione dell'intensità.
Questa compensazione garantisce lo stesso valore di [PAR](https://it.wikipedia.org/wiki/Radiazione_fotosinteticamente_attiva) (intensità luminosa) indipendentemente dalla temperatura del colore scelta (nella gamma da 12 000 a 23 000 K).
> [!NOTE]
> Poiché RedSea non pubblica i valori PAR al di sotto di 12 000 K, la compensazione funziona solo nella gamma da 12 000 a 23 000 K. Se hai un LED G1 e un misuratore PAR, puoi [contattarmi](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) per aggiungere la compensazione per l'intera gamma (da 9 000 a 23 000 K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Immagine">
</p>

In altre parole, senza compensazione, un'intensità di x% a 9 000 K non fornisce lo stesso valore PAR che a 23 000 K o 15 000 K.

Ecco le curve di potenza:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Immagine">
</p>

Se vuoi sfruttare appieno la potenza del tuo LED, disabilita la compensazione dell'intensità (impostazione predefinita).

Se abiliti la compensazione dell'intensità, l'intensità luminosa sarà costante per tutti i valori di temperatura, ma nella parte centrale della gamma non utilizzerai la piena capacità dei tuoi LED (come nei modelli G2).

Ricorda anche che, se abiliti la modalità di compensazione, il fattore di intensità può superare il 100% per i G1 se tocchi manualmente i canali Bianco/Blu. Puoi così sfruttare tutta la potenza dei tuoi LED!

***

# LED virtuale
- Raggruppa e gestisci i LED con un dispositivo virtuale (crea un dispositivo virtuale dal pannello di integrazione, poi usa il pulsante di configurazione per collegare i LED).
- Puoi usare solo Kelvin e intensità per controllare i tuoi LED se hai G2 o una combinazione di G1 e G2.
- Puoi usare sia Kelvin/Intensità che Bianco e Blu se hai solo G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Immagine">
</p>

# ReefMat:
- Interruttore avanzamento automatico (attiva/disattiva)
- Avanzamento programmato
- Valore di avanzamento personalizzato: consente di selezionare il valore di avanzamento del rotolo
- Avanzamento manuale
- Cambiare il rotolo.
>[!TIP]
> Per un rotolo nuovo completo, imposta il «diametro del rotolo» al minimo (4,0 cm). La dimensione verrà adattata in base alla versione RSMAT. Per un rotolo già usato, inserisci il valore in cm.
- Due parametri nascosti: modello e posizione, se devi riconfigurare il tuo RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Immagine">
</p>

# ReefRun:
- Impostare la velocità della pompa
- Gestire la sovra-schiumatura
- Gestire il rilevamento della tazza piena
- Possibilità di cambiare il modello di schiumatoio

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Immagine">
</p>

### Principale
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Immagine">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Immagine">
</p>

### Pompe
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Immagine">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Immagine">
</p>

# ReefWave:
> [!IMPORTANT]
> I dispositivi ReefWave sono diversi dagli altri dispositivi ReefBeat. Sono gli unici dispositivi dipendenti dal cloud ReefBeat.<br/>
> Quando avvii l'applicazione mobile ReefBeat, lo stato di tutti i dispositivi viene interrogato e i dati dell'applicazione ReefBeat vengono recuperati dallo stato del dispositivo.<br/>
> Per ReefWave è il contrario: non esiste un punto di controllo locale (come puoi vedere nell'applicazione ReefBeat, non puoi aggiungere un ReefWave a un acquario disconnesso).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Immagine"></center><br />
> Le onde sono archiviate nella libreria utente del cloud. Quando modifichi il valore di un'onda, questa viene modificata nella libreria cloud e applicata alla nuova programmazione.<br/>
> Quindi non esiste la modalità locale? Non è così semplice. Esiste una API locale nascosta per controllare ReefWave, ma l'applicazione ReefBeat non rileva le modifiche. Pertanto il dispositivo e HomeAssistant da un lato, e l'applicazione mobile ReefBeat dall'altro, saranno desincronizzati. Il dispositivo e HomeAssistant saranno sempre sincronizzati.<br/>
> Ora che lo sai, fai la tua scelta!

> [!NOTE]
> Le onde ReefWave hanno molti parametri collegati, e l'intervallo di alcuni parametri dipende da altri parametri. Non ho potuto testare tutte le possibili combinazioni. Se trovi un bug, puoi creare un ticket [qui](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modalità ReefWave
Come spiegato in precedenza, i dispositivi ReefWave sono gli unici che possono essere desincronizzati dall'applicazione ReefBeat se si utilizza l'API locale.
Sono disponibili tre modalità: Cloud, Locale e Ibrida.
Puoi modificare le impostazioni di modalità «Connessione al cloud» e «Usa API Cloud» come descritto nella tabella seguente.

<table>
<tr>
<td>Nome modalità</td>
<td>Interruttore Connessione al cloud</td>
<td>Interruttore Usa API Cloud</td>
<td>Comportamento</td>
<td>ReefBeat e HA sono sincronizzati</td>
</tr>
<tr>
<td>Cloud (predefinita)</td>
<td>✅</td>
<td>✅</td>
<td>I dati vengono recuperati tramite l'API locale. <br />I comandi di accensione/spegnimento vengono anch'essi inviati tramite l'API locale. <br />I comandi vengono inviati tramite l'API Cloud.</td>
<td>✅</td>
</tr>
<tr>
<td>Locale</td>
<td>❌</td>
<td>❌</td>
<td>I dati vengono recuperati tramite l'API locale. <br />I comandi vengono inviati tramite l'API locale. <br />Il dispositivo viene mostrato come «spento» nell'applicazione ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Ibrida</td>
<td>✅</td>
<td>❌</td>
<td>I dati vengono recuperati tramite l'API locale. <br />I comandi vengono inviati tramite l'API locale.<br />L'applicazione mobile ReefBeat non mostra i valori corretti delle onde se sono stati modificati tramite HA.<br/>Home Assistant li mostra sempre correttamente.<br/>Puoi modificare i valori dall'applicazione ReefBeat e da Home Assistant.</td>
<td>❌</td>
</tr>
</table>

Per le modalità Cloud e Ibrida devi collegare il tuo account ReefBeat Cloud.
Prima crea una [«API Cloud»](README.it.md#aggiungere-lapi-cloud) con le tue credenziali, e il gioco è fatto!
Il sensore «Collegato all'account» verrà aggiornato con il nome del tuo account ReefBeat una volta stabilita la connessione.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Immagine">
</p>

## Modificare i valori attuali
Per caricare i valori delle onde attuali nei campi di anteprima, usa il pulsante «Imposta anteprima dall'onda attuale».
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Immagine">
</p>
Per modificare i valori delle onde attuali, imposta i valori di anteprima e usa il pulsante «Salva anteprima».

Il funzionamento è identico a quello dell'applicazione mobile ReefBeat. Tutte le onde con lo stesso identificatore nella programmazione attuale verranno aggiornate.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Immagine">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Immagine">
</p>

# API Cloud
L'API Cloud consente di:
- Avviare o fermare i collegamenti rapidi: emergenza, manutenzione e alimentazione,
- Ottenere informazioni sull'utente,
- Recuperare la libreria delle onde,
- Recuperare la libreria degli integratori,
- Recuperare la libreria dei programmi LED,
- Ricevere notifiche di [nuove versioni del firmware](README.it.md#aggiornamento-firmware),
- Inviare comandi a ReefWave quando è selezionata la modalità «[Cloud o Ibrida](README.it.md#reefwave)».

I collegamenti rapidi, i parametri delle onde e dei LED sono ordinati per acquario.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Immagine">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Immagine">
</p>

>[!TIP]
> È possibile disabilitare il recupero dell'elenco degli integratori tramite l'interfaccia di configurazione del dispositivo API Cloud.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Immagine">
***
# FAQ

## Il mio dispositivo non viene rilevato
- Prova a riavviare il rilevamento automatico con il pulsante «Aggiungi voce». A volte i dispositivi non rispondono perché sono occupati.
- Se i tuoi dispositivi RedSea non sono nella stessa sottorete di Home Assistant, il rilevamento automatico fallirà prima e ti proporrà di inserire l'indirizzo IP del tuo dispositivo o l'indirizzo della sottorete in cui si trovano i tuoi dispositivi. Per il rilevamento della sottorete, usa il formato IP/MASCHERA, come in questo esempio: 192.168.14.0/255.255.255.0.
- Puoi anche usare la [modalità manuale](README.it.md#modalità-manuale).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Immagine">
</p>

## Alcuni dati vengono aggiornati correttamente, altri no.
I dati sono divisi in tre parti: dati, configurazione e informazioni sul dispositivo.
- I dati vengono aggiornati regolarmente.
- I dati di configurazione vengono aggiornati solo all'avvio e quando si preme il pulsante «fetch-config».
- Le informazioni sul dispositivo vengono aggiornate solo all'avvio.

Per garantire l'aggiornamento regolare dei dati di configurazione, abilita l'[aggiornamento della configurazione in tempo reale](README.it.md#aggiornamento-in-tempo-reale).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
