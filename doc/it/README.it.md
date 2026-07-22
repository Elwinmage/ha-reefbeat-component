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
***Gestione Locale di Dispositivi HomeAssistant RedSea Reefbeat (senza cloud): ReefATO+, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave***

> [!TIP]
> ***Per modificare gli orari avanzati di ReefDose, ReefLed, ReefRun e ReefWave, è necessario utilizzare [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) (attualmente in sviluppo)***

> [!TIP]
> L'elenco delle implementazioni future può essere trovato [qui](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> L'elenco dei bug può essere trovato [qui](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***Se hai bisogno di altri sensori o attuatori, sentiti libero di contattarmi [qui](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Se i tuoi dispositivi non si trovano sulla stessa subnet di Home Assistant, per favore [leggi questo](https://github.com/Elwinmage/ha-reefbeat-component/#my-device-is-not-detected).

> [!CAUTION]
> ⚠️ Questo non è un repository ufficiale RedSea. Usa a tuo rischio.⚠️

# Compatibilità

✅ Testato ☑️ Deve Funzionare (Se ne hai uno, puoi confermarne il funzionamento [qui](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8)) ❌ Non Supportato Ancora

Vedi il README inglese per la tabella completa di compatibilità.

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

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
