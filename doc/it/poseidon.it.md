[← Torna alla pagina principale](README.it.md)

# Modalità Poseidon

<p align="center">
<img src="../img/poseidon/poseidon.png" alt="Poseidon" width="240">
</p>

La modalità Poseidon mette un relè tra i tuoi dispositivi ReefBeat e il broker
MQTT di Red Sea, dentro Home Assistant. Un dispositivo in modalità Poseidon si
collega a Home Assistant invece che a `mqtt.reef-beat.com`, e Home Assistant
inoltra il suo traffico a Red Sea senza modificarlo: l'app ReefBeat continua a
funzionare come prima.

> [!WARNING]
> La modalità Poseidon è sperimentale. Con la strategia *Spia*, predefinita, si
> limita a inoltrare e osservare il traffico: l'integrazione continua a interrogare
> i dispositivi. Le strategie *Shadow* e *Poseidon* usano ciò che i dispositivi
> inviano (vedi [Strategie](#strategie)).

## Aggiungere Poseidon

*Impostazioni > Dispositivi e servizi > Red Sea > Aggiungi voce > Modalità Poseidon*

- **Porta di ascolto**: viene proposta la prima porta libera a partire da 1884
  (1883 e 8883, le porte MQTT abituali, vengono saltate). Viene ricontrollata
  alla conferma e a ogni avvio del relè: se un altro servizio la occupa, un
  avviso di riparazione lo segnala e i dispositivi non vengono toccati.
- **Indirizzo di Home Assistant**: l'indirizzo IPv4 con cui i dispositivi
  raggiungono Home Assistant.
- **Account cloud**: l'account cloud ReefBeat usato per recuperare le chiavi
  dei dispositivi. Serve un account cloud.

## Aggiungere dispositivi

*Poseidon > Configura > Aggiungi dispositivi*

Ogni dispositivo dell'integrazione è elencato con il suo stato:

| Stato | Significato |
|---|---|
| Selezionabile | Le sue chiavi sono note: passa subito in modalità Poseidon |
| Selezionabile, 🔑 | Le sue chiavi vanno prima recuperate (vedi sotto) |
| Già in modalità Poseidon | Niente da fare |
| Senza credenziali cloud | Collegato a un acquario locale: niente modalità Poseidon |
| Non presente nell'account cloud | Le sue chiavi non si possono recuperare con questo account |
| Non raggiungibile | Non risponde |

> [!CAUTION]
> **Il recupero delle chiavi è distruttivo.** Un dispositivo non fornisce le
> sue chiavi: per ottenerle, viene eliminato dal cloud ReefBeat e ricreato.
> - viene scollegato dal suo acquario, e l'app potrebbe chiedere di
>   riassociarlo;
> - programmi, preset e cronologia salvati nel cloud per lui possono andare
>   persi;
> - la sua configurazione viene salvata prima e confrontata dopo: ReefRun e
>   ReefWave riottengono la propria automaticamente; per gli altri dispositivi, ciò
>   che è cambiato è elencato in una notifica (la configurazione salvata resta in
>   `/config/redsea/poseidon/snapshots/`);
> - una ReefWave dipende dal cloud, che le invia il programma a ogni connessione:
>   prima dell'eliminazione vengono salvate anche le onde personalizzate del suo
>   acquario (con le intensità di ogni pompa) e il suo programma; l'acquisizione si
>   ferma, senza eliminare nulla, se non si possono leggere. Dopo, le onde perse dal
>   cloud vengono ricreate (o riottengono le impostazioni della pompa), il programma
>   viene inviato al cloud e il cloud lo invia alle pompe; la pompa viene scritta
>   direttamente solo se non lo ha ricevuto.
>
> Il recupero si fa una volta per dispositivo: Home Assistant conserva le
> chiavi, anche se Poseidon viene rimosso.

## L'interruttore Poseidon

Ogni dispositivo con chiavi note ha un interruttore **Modalità Poseidon** nella
sua pagina:

- **acceso**: il dispositivo parla con Red Sea attraverso Home Assistant;
- **spento**: il dispositivo parla direttamente con Red Sea (modalità normale).

Il suo stato viene letto sul dispositivo stesso. I suoi attributi:

| Attributo | Significato |
|---|---|
| `connection_state` | Stato di connessione indicato dal dispositivo |
| `last_up` / `last_down` | Ultimo traffico dispositivo → Red Sea / Red Sea → dispositivo |
| `silent` | In modalità Poseidon, ma nulla è passato dal relè durante il ritardo delle impostazioni |

Un dispositivo silenzioso genera anche un avviso di riparazione, che scompare
da solo quando il suo traffico riprende. Un dispositivo silenzioso non viene
mai riportato in modalità normale automaticamente.

## Cosa succede e quando

| Evento | Dispositivi |
|---|---|
| Riavvio di Home Assistant, ricaricamento di Poseidon | Lasciati come sono: si ricollegano quando il relè torna |
| Poseidon disattivato o rimosso | Tutti riportati in modalità normale |
| Un dispositivo non può essere riportato in modalità normale | Indicato in una notifica |
| Il relè cade, un [watchdog](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog) sorveglia | Tutti riportati in modalità normale, una volta confermato che Red Sea è raggiungibile; senza watchdog, usa lo [script di emergenza](#script-di-emergenza) |
| Un dispositivo punta al relè ma non vi si connette mai (ha mantenuto la sessione con Red Sea) | Fatto riconnettere dopo 2 minuti: riportato su Red Sea, poi di nuovo sul relè, due volte al massimo |

Si entra in modalità Poseidon solo per tua decisione. Ogni passaggio automatico
riporta in modalità normale.

## Strategie

Cosa fa Home Assistant di un dispositivo in modalità Poseidon. Ogni
dispositivo ha un selettore **Strategia Poseidon** accanto al suo interruttore;
le impostazioni danno il valore predefinito.

| Strategia | Interrogazione | Stati inviati | File |
|---|---|---|---|
| *Spia* | invariata | registrati, confrontati con l'interrogazione successiva | `spy.jsonl` |
| *Shadow* | invariata | uniti ai dati del dispositivo, confrontati con l'interrogazione successiva | `shadow.jsonl` |
| *Poseidon* | ogni N minuti | usati; il dispositivo viene riletto a ogni stato finché la sua famiglia non può essere unita | — |

> [!IMPORTANT]
> **Proprietari di ReefATO+, ho bisogno del vostro aiuto.** Non possiedo un ReefATO+,
> quindi la modalità Poseidon non ha mai funzionato su di esso: ciò che invia non è
> ancora noto e nulla viene unito. Metti prima il tuo in strategia *Spia*, poi, per
> completarne il supporto:
> - inviami il suo log spia (`/config/redsea/poseidon/logs/spy.jsonl`) in una
>   [issue GitHub](https://github.com/Elwinmage/ha-reefbeat-component/issues), dopo
>   averlo riletto: è decifrato e contiene gli identificativi dei tuoi dispositivi;
> - e/o apri le riparazioni che Poseidon segnala per i suoi
>   [messaggi inattesi](#messaggi-inattesi): ognuna precompila la issue GitHub.
>
> Non inviare mai il file delle chiavi. L'avvertenza sull'acquisizione delle chiavi
> vale per il ReefATO+ come per qualsiasi dispositivo.

Famiglie unite finora, dalle sessioni spia:

| Famiglia | Unito |
|---|---|
| ReefControl Power | stati, telemetria (sonda di temperatura inclusa); gli stati delle prese sono calcolati dai loro programmi, come fa l'app ReefBeat |
| ReefDose | stati, telemetria; un `dosing-log` (fine di una dose) la rilegge, per la sua coda di dosaggio, e così la mezzanotte (00:01, ora di Home Assistant), quando la coda del nuovo giorno sostituisce quella del giorno che finisce |
| ReefMat | stati, telemetria, `rolling-log` (fine di un avanzamento) |
| ReefLED | telemetria |
| ReefWave | stati (modalità: un'alimentazione la spegne e la riporta su auto, impostazioni), telemetria (modalità, segnale wifi); un programma scritto nell'app (`schedule`, inviato senza i suoi intervalli) la rilegge. La sua onda attuale è dedotta dal programma e dall'orologio: nulla invia il cambio d'onda all'inizio di un intervallo (solo la telemetria lo indica, entro un minuto) |
| ReefRun | stati, telemetria (stato, intensità, temperatura delle pompe: bicchiere pieno, pompa mancante...); la fine di una calibrazione e una `notification` (una pompa da ricollegare) la rileggono |
| ReefControl | telemetria ed eventi `probe` (letture delle sonde), stati (modalità, collegamento con un ReefControl Power, modalità perdita), modalità e stato delle porte (una porta spenta consuma 0; il consumo di una porta accesa arriva con l'interrogazione); una sonda o una porta installata o configurata lo rilegge |

Per le altre famiglie, *Shadow* si limita a confrontare e *Poseidon* rilegge il
dispositivo ogni volta che invia uno stato. *Poseidon* lo rilegge anche quando uno
stato indica qualcosa che il suo merger non sa scrivere (un'impostazione sconosciuta,
un programma di ReefDose, inviato senza i suoi intervalli). Questa lettura include le
fonti di configurazione: ciò che l'app cambia sono soprattutto impostazioni, che
l'interrogazione non rilegge mai. Anche ogni comando di scrittura dell'app accettato
dal dispositivo lo rilegge: non ogni impostazione viene inviata (l'offset di una
sonda di temperatura no).

Un ReefControl Power senza presa pilotata da un sensore (con o senza sonda di
temperatura), una ReefDose (la sua coda di dosaggio viene letta dopo ogni dose e a
mezzanotte) e una ReefWave (il suo programma viene riletto quando cambia) inviano
tutto ciò che cambia: con *Poseidon* vengono interrogati solo ogni *Intervallo della
lettura di sicurezza*.

### Spia

`/config/redsea/poseidon/logs/spy.jsonl` (rotazione a 10 MB, 5 file
conservati) contiene, con lo stesso orologio:

| `kind` | Record |
|---|---|
| `publish`, `control` | un frame tra il dispositivo e Red Sea, nei due sensi, decifrato |
| `http` | una richiesta HTTP inviata da Home Assistant al dispositivo: metodo, endpoint, stato (0 = nessuna risposta), durata, dati; `origin` vale `integration` o `poseidon` (le sue letture di `/cloud` ogni 60 s) |
| `compare` | uno stato inviato rispetto all'interrogazione successiva, ogni valore `same`, `differs` o `unknown` |
| `mark` | la strategia o la pausa è cambiata |

Un dispositivo in modalità spia ha anche un interruttore **Pausa
dell'interrogazione**: non gli viene più inviata alcuna richiesta, letture di
`/cloud` di Poseidon comprese; ciò che invia allora, lo invia da sé. La pausa
non sopravvive a un riavvio.

Registrazione consigliata, per dispositivo (orologi degli host Home Assistant
sincronizzati, stesso fuso orario):

1. 30 minuti senza alcuna interrogazione: ogni altro Home Assistant che legge
   il dispositivo fermato, la pausa attiva;
2. 30 minuti con la sola interrogazione (pausa disattivata);
3. azioni a orari annotati: dall'app ReefBeat, da Home Assistant, sul
   dispositivo stesso;
4. se un altro Home Assistant interroga il dispositivo, le sue richieste si
   aggiungono con l'azione `logger.set_level`,
   `custom_components.redsea.reefbeat.api: debug`.

## Impostazioni

*Poseidon > Configura > Impostazioni di Poseidon*

- **Strategia predefinita**: quella di ogni dispositivo in modalità Poseidon senza
  strategia propria (vedi [Strategie](#strategie)). *Spia* di default.
- **Intervallo di interrogazione della strategia Poseidon**, in minuti (10 di
  default).
- **Modalità debug**: ogni frame che attraversa il relè viene scritto decifrato in
  `/config/redsea/poseidon/logs/poseidon.jsonl` (rotazione a 10 MB, 5 file
  conservati). I dati sono in chiaro in quel file.
- **Ritardo prima che un dispositivo sia silenzioso**, in minuti (10 di default).
- **Intervallo della lettura di sicurezza**, in minuti (60 di default):
  l'interrogazione di un dispositivo i cui messaggi inviati coprono tutto ciò che
  cambia, e la frequenza di lettura del `/cloud` di un dispositivo che scambia
  tramite il relè.
- **Segnalare i messaggi inattesi** (attivo di default): vedi
  [Messaggi inattesi](#messaggi-inattesi).
- **Cercare segnalazioni esistenti su GitHub** (attivo di default): viene inviata
  solo la firma di un messaggio inatteso.
- **Trattenere i ripristini del cloud alla connessione** (attivo di default): vedi
  [Protezione alla connessione](#protezione-alla-connessione).
- **Chiave del watchdog**: 16 caratteri, proposta finché non ne è impostata una. Il
  relè risponde a una richiesta cifrata «sei vivo?» fatta con questa chiave:
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog),
  o il suo `poseidon_watchdog.py` da solo su un'altra macchina, sorveglia il relè e
  riporta i dispositivi in modalità normale quando cade. Copia questa chiave nella
  sua configurazione; lasciala vuota per non rispondere a nessun watchdog.

## Messaggi inattesi

Ogni messaggio che attraversa il relè viene confrontato con ciò che si conosce della
famiglia del dispositivo: un pacchetto o topic MQTT sconosciuto, un comando del cloud
verso un endpoint sconosciuto, uno stato o una telemetria con un campo nuovo,
mancante o di altro tipo. La prima occorrenza finisce in
`/config/redsea/poseidon/logs/anomalies.jsonl`, anonimizzata (identificativi, nomi,
indirizzi di rete e chiavi rimossi); un comando sconosciuto attende 5 secondi ciò che
il dispositivo risponde e invia, e viene scritto insieme.

Ognuno ha una firma, la stessa per tutti gli utenti. Le issue del repository vengono
cercate con essa, e una riparazione dice cosa fare: segnalarlo (una issue GitHub
precompilata, inviata solo da te), seguire la segnalazione aperta, aggiornare alla
versione che lo gestisce o leggere la segnalazione chiusa. Un nuovo campo di
telemetria crea una riparazione solo se la ricerca non ha trovato segnalazioni.

## Protezione alla connessione

A ogni connessione di un dispositivo, il cloud Red Sea gli invia la propria copia
delle impostazioni del dispositivo. Quando questa copia è superata, il dispositivo
perde quelle attuali: una ReefWave ha perso così tutto il suo programma. Per i primi
30 secondi di ogni connessione tramite il relè, i ripristini noti del cloud (gruppo e
programma di una ReefWave, testa di alimentazione di una ReefDose) vengono quindi
trattenuti.

Ogni altro comando passa e viene registrato (`guard_passed` nel file spia): un
dispositivo che si riavvia mentre si usa l'app (un ReefControl che va in crash
durante l'installazione di una sonda) riceve i comandi dell'utente.

## Eventi

### `redsea_dose`

Emesso quando una ReefDose in modalità Poseidon (qualsiasi strategia) termina una
dose, programmata o manuale, dal suo `dosing-log`. Una dose inviata due volte (dopo
una riconnessione) viene emessa una volta.

| Campo | Contenuto |
|---|---|
| `device_id` | il dispositivo in Home Assistant |
| `name` | il suo nome |
| `head` | numero della testa |
| `supplement`, `brand` | come indicati dal dispositivo |
| `dose_type` | `scheduled` o `manual` |
| `volume` | volume dosato, in mL |
| `started_at` | inizio della dose, dalla coda di dosaggio letta prima (ora locale del dispositivo); per una dose che non vi era (quella di mezzanotte, manuale dall'app), stimato dalla portata della testa; `null` finché meno di 3 dosi della testa hanno una durata misurata |
| `ended_at` | fine della dose (ora locale del dispositivo) |
| `duration_s` | `ended_at` − `started_at`, `null` senza inizio |
| `start_estimated` | `true` quando `started_at` (e `duration_s`) sono stimati: volume ÷ portata della testa (le sue ultime 20 dosi di durata misurata) |

Non viene inviato nulla all'inizio di una dose: il suo inizio è l'ora che le ha dato
la coda di dosaggio. La dose di mezzanotte non è in nessuna coda (quella del giorno
che finisce è allora vuota, quella del nuovo giorno inizia dopo): il suo inizio è
stimato.

### `redsea_notification`

Emesso quando un dispositivo in modalità Poseidon (qualsiasi strategia) invia un
allarme, quello che l'app ReefBeat mostra come notifica. Riporta ciò che il
dispositivo ha indicato:

| Campo | Contenuto |
|---|---|
| `device_id` | il dispositivo in Home Assistant |
| `name` | il suo nome |
| `device_type` | la sua famiglia: `reef-run`, `reef-control`, `reef-dosing`... |
| `type` | l'allarme, come lo nomina il dispositivo |
| `sub_type` | come indicato dal dispositivo (`sub-type`) |
| altri campi | ciò che riguarda l'allarme: `pump` o `pump_name` (ReefRun), `probe` (ReefControl, il suo nome), `supplement` (ReefDose) |

Visti finora:

| Famiglia | `type` |
|---|---|
| ReefRun | `full_cup_warning` (`pump`), `no_pump` (`pump_name`) |
| ReefControl | `sensor_danger_range`, `temperature_danger_range`, `aquarium_water_leak` (`probe`) |
| ReefDose | `stock_level_empty` (`supplement`) |

```yaml
automation:
  - alias: Skimmer cup full
    triggers:
      - trigger: event
        event_type: redsea_notification
        event_data:
          type: full_cup_warning
    actions:
      - action: notify.notify
        data:
          message: "{{ trigger.event.data.name }}: the skimmer cup is full"
```

### Cronologia delle dosi

Ogni dose viene anche conservata, per testa, per 30 giorni (5000 dosi al massimo),
anche dopo i riavvii:

- ogni testa di una ReefDose riceve un sensore **Ultima dose** (sul dispositivo
  della testa), disponibile solo finché il dosatore è in modalità Poseidon: il suo
  stato è la fine dell'ultima dose, i suoi attributi volume, tipo, inizio, durata e
  integratore; il recorder li conserva come per ogni sensore;
- l'azione `redsea.get_doses` restituisce le dosi, dalla più recente: `device_id` (il
  dosatore, una delle sue teste o la sua voce di configurazione) e opzionalmente
  `head`, `days`, `limit`;
- la ha-reef-card le mostra nella finestra di configurazione di una testa
  (**Cronologia delle dosi**).

```yaml
automation:
  - alias: Log the doses
    triggers:
      - trigger: event
        event_type: redsea_dose
    actions:
      - action: logbook.log
        data:
          name: "{{ trigger.event.data.name }}"
          message: >-
            head {{ trigger.event.data.head }}
            ({{ trigger.event.data.supplement }}):
            {{ trigger.event.data.volume }} mL,
            {{ trigger.event.data.dose_type }},
            {{ trigger.event.data.started_at }} → {{ trigger.event.data.ended_at }}
```

## Messaggi dell'app ReefBeat

I sensori **Ultimo messaggio** e **Ultimo messaggio di avviso** (e la cronologia dei
messaggi) vengono dalle risposte dei dispositivi agli invii di Home Assistant, che
restano HTTP in ogni modalità. I comandi dell'app ReefBeat (o del cloud) raggiungono
un dispositivo via MQTT: in modalità Poseidon (qualsiasi strategia), la risposta del
dispositivo a ogni comando di scrittura (`command-response`, stesso `uuid`) alimenta
gli stessi sensori, come farebbe una risposta HTTP:

- un `message` (`settings updated successfully`, `head settings successfully
  saved`...) diventa l'ultimo messaggio;
- un `alert` (`NoMoreDoseAlert`...), `"success": false` o uno stato di errore diventa
  l'ultimo avviso.

Le letture dell'app (`GET`) non portano alcun messaggio: restano fuori. L'attributo
`origin` di entrambi i sensori, e di ogni voce della cronologia (l'azione
`redsea.get_messages`), dice da dove è venuto: `ha` (un invio di Home Assistant) o
`reefbeat` (un comando dell'app o del cloud). La ha-reef-card lo mostra dopo la data.

## Esportare e importare le chiavi

*Poseidon > Configura > Esporta le chiavi* fornisce un link di download di
tutte le chiavi note, valido 5 minuti. Il file viene generato al clic e mai
scritto in `/config`; è nel formato della CLI (`keystore.json`) e contiene le
chiavi in chiaro: conservalo al sicuro. L'azione `redsea.poseidon_export`, per
le automazioni, scrive lo stesso file in
`/config/redsea/poseidon/keystore-<data>.json`, leggibile solo dal
proprietario.

*Poseidon > Configura > Importa chiavi* chiede un file del genere e lo invia dal
tuo browser. Un dispositivo viene sostituito solo da un record più recente, i
dispositivi senza chiavi vengono ignorati, e i dispositivi importati ricevono
subito il loro interruttore.

## Script di emergenza

*Poseidon > Configura > Script di emergenza* fornisce un link di download
(5 minuti) a `poseidon_rescue.py`: uno script che riporta i dispositivi sul
broker Red Sea senza Home Assistant, per quando non può più farlo (fermo, relè
guasto, integrazione rimossa). Funziona su qualsiasi computer della rete dei
dispositivi con Python 3.8 o successivo, nient'altro da installare:

```bash
python3 poseidon_rescue.py --dry-run   # cosa verrebbe fatto, nulla cambia
python3 poseidon_rescue.py             # i dispositivi sul relè, dopo conferma
```

| Opzione | Uso |
|---|---|
| `--ip HWID=IP` | un dispositivo ha cambiato indirizzo dopo il download |
| `--scan CIDR` | dove cercare i dispositivi che hanno cambiato indirizzo (ripetibile) |
| `--no-scan` | non cercarli mai |
| `--only HWID` | un solo dispositivo (hwid o nome, ripetibile) |
| `--all` | tutti i dispositivi, qualunque sia il loro broker attuale |
| `--keystore keystore.json` | un'esportazione del keystore al posto dei dispositivi incorporati |
| `--yes` | senza conferma |

Nulla viene scritto in un dispositivo prima che abbia dimostrato di essere
quello giusto: il suo `hwid`, letto in `/device-info`, deve corrispondere. Un
dispositivo che non risponde più al suo indirizzo, o il cui indirizzo ora è di
un altro, viene cercato in rete: il /24 di ogni indirizzo noto e del computer
che esegue lo script, o le sottoreti `--scan`.

Ogni dispositivo riceve la stessa sequenza che da Home Assistant (disattivare,
scrivere broker e chiavi, attivare), poi `/cloud` viene riletto per verifica.
Lo script contiene le chiavi in chiaro: conservalo al sicuro, e riscaricalo
dopo aver aggiunto dispositivi.
