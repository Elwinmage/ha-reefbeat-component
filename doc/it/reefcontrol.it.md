[← Torna alla pagina principale](README.it.md)

# ReefControl:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_devices.png" alt="Image">
</p>

L'hub ReefControl (RSCONTROLPRO / RSCONTROLLITE) legge le sonde ReefSense collegate ai suoi box di estensione, gestisce le sue porte 12V DC (2 sul Pro, 1 sul Lite) e, una volta accoppiato, le prese di un [ReefControl-Power](reefcontrol-power.it.md#reefcontrol-power).

- **Sonde ReefSense** — pH, ORP, salinità (EC), temperatura, ATO (livello dell'acqua) e perdita: valore e livello (desiderato / accettabile / pericolo), stato, nome, uid, date dell'ultima installazione e dell'ultima calibrazione, e la temperatura integrata delle sonde pH, EC e ATO. Ogni entità di sonda porta gli attributi `probe_uid`, `probe_type` e `probe_index`, e i sensori di misura un attributo `ranges` (`[acceptable_low, desired_low, desired_high, acceptable_high]`).
- **Sonde di salinità** — sensori di conducibilità, salinità (ppt) e densità, più un select dell'unità di visualizzazione.
- **Sonde di perdita** — stato asciutto/bagnato, **origine dell'acqua** (asciutto / acqua dell'acquario / acqua osmotica) e la conducibilità misurata, letti non appena la sonda si bagna.
- **Impostazioni per sonda** — intervalli desiderato e accettabile (misura principale e temperatura integrata), interruttori attivata / buzzer / notifiche / manutenzione, e un pulsante «Leggi ora» che recupera una misura aggiornata senza attendere la prossima interrogazione.
- **Calibrazione delle sonde** — vedi [più avanti](#calibrazione-delle-sonde).
- **Buzzer** — buzzer di pericolo e buzzer di perdita (attivazione, frequenza, duty cycle), antirimbalzo del pericolo, interruttore del rilevatore di perdite; stato attivo / tacitato del buzzer e sua causa.
- **Porte 12V** — nome modificabile, interruttore acceso/spento, stato, modalità, tipo, consumo e un pulsante «Disinstalla porta». Il sensore `port_N_mode` porta come attributi l'intera configurazione della porta, il suo programma e la sua regola di sonda, così che una card possa modificare la porta (vedi [Modalità delle porte e delle prese](#modalità-delle-porte-e-delle-prese)).
- **Accoppiamento con ReefControl-Power** — Power Center accoppiato, il suo stato e il suo collegamento, pulsanti «Accoppia Power Center» / «Disaccoppia Power Center», e un pulsante «Annulla iscrizione presa» per ogni presa del Power Center che l'hub gestisce da una sonda.
- **Aggiunta, sostituzione o rimozione delle sonde** dal menu delle opzioni dell'integrazione (vedi [più avanti](#gestione-delle-sonde-aggiungi--sostituisci--rimuovi)).
- Le scritture vengono mostrate subito (aggiornamento ottimistico), poi confermate rileggendo il dispositivo.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_diag.png" alt="Image">
</p>

> [!TIP]
> La [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) disegna l'hub, le sue sonde, le sue porte e il Power Center accoppiato, e gestisce le calibrazioni e le modalità delle porte in pochi clic.

## Gestione delle sonde (aggiungi / sostituisci / rimuovi)
Le sonde BLE (pH, ORP, EC, ATO, perdita, temperatura) si gestiscono dal menu **Opzioni** dell'integrazione, come nell'app Red Sea:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_probe_management.png" alt="Image">
</p>

- **Aggiungere una sonda**: mettete la sonda in modalità di accoppiamento, sceglietene il tipo e confermate per avviare la ricerca. La sonda viene configurata come fa l'app: una sonda di perdita, ad esempio, si chiama `Leak <uid>` con buzzer, rilevatore di perdite e notifiche attivi.
- **Sostituire una sonda**: scegliete la sonda da sostituire, mettete una nuova sonda dello stesso tipo in modalità di accoppiamento e confermate. La nuova sonda eredita la cronologia e le statistiche della precedente.
- **Rimuovere una sonda**: selezionate una o più sonde e confermate — questo elimina definitivamente le entità della sonda e la loro cronologia.

> [!NOTE]
> Reinstallare una sonda ne azzera le impostazioni sull'hub (una sonda ORP torna ai suoi intervalli di fabbrica). L'integrazione rilegge la configurazione delle sonde ogni volta che una sonda compare o viene reinstallata, sia da Home Assistant che dall'app ReefBeat.

## Calibrazione delle sonde
Ogni tipo di sonda si calibra come nell'app ReefBeat.

| Sonda | Come | Entità / servizio |
| ----- | ---- | ----------------- |
| ORP | Immergete la sonda nella soluzione di calibrazione, poi impostate il numero sul valore della soluzione | `Calibrare {probe} (valore della soluzione)` |
| Temperatura | Impostate il numero sulla temperatura reale dell'acqua in cui si trova la sonda | `Calibrare {probe} (temperatura reale)` |
| Temperatura integrata (pH, EC, ATO) | Allo stesso modo, per il sensore di temperatura integrato nella sonda | `Calibrare la temperatura di {probe} (temperatura reale)` |
| pH | Due punti: pH 7, poi pH 10 (acqua salata) o pH 4 (acqua dolce) | `redsea.probe_calibration` |
| Salinità (EC) | Un punto, con il valore della soluzione in mS/cm | `redsea.probe_calibration` |

I **numeri a valore di riferimento** (ORP e temperature) mostrano la misura attuale. Impostarne uno sul riferimento rilegge la sonda e ne sposta l'offset di `riferimento - misura`, così che la sonda legga poi il riferimento.

Le **calibrazioni pH ed EC** richiedono più passaggi e passano dal servizio `redsea.probe_calibration`, un passaggio per chiamata: `enter`, poi `point` per ogni punto di calibrazione, `status` interrogato finché l'hub non segnala il successo o il fallimento (nel frattempo restituisce `calibration_status`, `time_left` e `stability_progress`), e infine `exit`. La [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) esegue l'intera sequenza per voi.

```yaml
action: redsea.probe_calibration
data:
  device_id: <config entry of the hub>
  probe_type: ph
  probe_uid: "0x00B39"
  action: point
  point: MID
  solution_value: 7.0
  solution_rated_temp: 25
```

La data dell'ultima calibrazione viene dall'hub: una sonda pH o EC calibrata dall'app ReefBeat, o una sonda ORP verificata, segna la sua attività di manutenzione come svolta in quella data.

## Fusione della temperatura multi-sonda
Non appena sono presenti due o più fonti di temperatura (la sonda di temperatura dedicata più la temperatura incorporata nelle sonde EC/pH/ATO), ReefControl calcola una **temperatura combinata** robusta a partire dalle letture individuali:

- **Temperatura combinata** (`sensor`): un unico valore aggregato con il metodo scelto — Mediana (predefinito), Media, Minimo o Massimo. Configurabile tramite l'entità select **Metodo di fusione temperatura**.
- **Coerenza temperatura** (`binary_sensor`) e **Scarto di temperatura** (`sensor`, diagnostica): indicano se le fonti concordano entro la **Soglia di coerenza temperatura** (configurabile, 0,5 °C predefinita), e l'entità di un eventuale disaccordo.
- **Origine anomalia temperatura** (`sensor`, diagnostica): `OK` quando tutte le fonti concordano, il nome della/e sonda/e sospettata/e di deriva o lettura errata, oppure `Sconosciuta` quando il disaccordo non può essere attribuito a una sonda precisa. Gli attributi del sensore elencano ogni fonte con valore, variazione in 1 ora e stato.
- Un **interruttore di manutenzione per ogni sonda compatibile con la temperatura**: attivandolo, quella sonda viene temporaneamente esclusa dal calcolo di fusione/coerenza/anomalia, così pulizia o taratura non generano mai un falso allarme.
- Una **calibrazione sulla temperatura reale** (`number`) per ogni sonda compatibile con la temperatura (vedi [Calibrazione delle sonde](#calibrazione-delle-sonde)).

Queste entità compaiono solo quando vengono rilevate almeno due fonti di temperatura.

## Modalità delle porte e delle prese
Una porta 12V dell'hub, come una presa del Power Center, funziona in una di quattro modalità: **off**, **on**, **schedule** (programma) o **sensor** (pilotata da una sonda). Una porta non ancora installata è in modalità `setup` e rifiuta qualsiasi scrittura finché non viene installata.

Queste impostazioni non sono esposte come entità singole — con più porte e prese e un insieme di soglie per tipo di sonda, sarebbero decine di entità usate di rado. Configuratele dalla [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), che esegue le stesse chiamate dell'app ReefBeat in un'unica azione tramite il servizio `redsea.request` (vedi i Servizi dell'integrazione negli Strumenti per sviluppatori di Home Assistant).

Il sensore `port_N_mode` porta comunque ciò che serve a un'automazione per leggere la configurazione attiva: `config` (l'intera voce della porta, `power_on_percent` compreso), `schedule` (riletto dall'hub finché la porta è in modalità programma) e `sensor_config` (la regola di sonda), con `sensor_source: control`.

## Modulo ATO (kit ATO Red Sea)
Il kit ATO Red Sea — una pompa su una porta 12V e una sonda ATO — si installa come fa la procedura guidata dell'app, dal menu **Opzioni** dell'integrazione:

1. **Aggiungi una sonda** di tipo `ato` (si chiama `ATO Temp. <uid>`, dalla sua temperatura, come nell'app).
2. **Installa il modulo ATO**: scegli la porta 12V libera, la sonda ATO, il volume del serbatoio (L), la lunghezza e l'altezza del tubo (cm, dalla pompa alla vasca; l'altezza è quanto sale sopra la pompa), il rabbocco automatico e il monitoraggio del serbatoio.

La porta diventa di tipo `ato` e riceve le entità del modulo: stato (`OK` o il guasto segnalato: pompa assente, pompa bloccata, serbatoio vuoto, tempo di rabbocco superato, perdita, guasto della porta), guasto e pompa (sensori binari), volume di oggi / residuo (mL), causa dell'ultimo rabbocco, interruttori per rabbocco automatico, monitoraggio serbatoio, notifiche e registro temperatura, numeri per il volume residuo del serbatoio, lunghezza/altezza del tubo (cm) e portata (da 0,2 a 4 L/min, 0 = predefinita), e pulsanti per riprendere (solo in caso di guasto), rabboccare manualmente e fermare.

Disinstallare la porta (da Home Assistant, dalla card o dall'app ReefBeat) rimuove il modulo e subito le sue entità. Un modulo installato dall'app ReefBeat compare dopo un ricaricamento automatico.

## Attività di manutenzione
| Attività | Sonde | Predefinito | Intervallo |
| -------- | ----- | ----------- | ---------- |
| Pulire la sonda | Tutte | 30 giorni | 2 – 8 settimane |
| Calibrare la sonda | pH | 3 mesi | 2 – 4 mesi |
| Calibrare la sonda | Salinità (EC) | 2 mesi | 1 – 3 mesi |
| Verificare la sonda | ORP | 6 mesi | 5 – 7 mesi |
| Sostituire la sonda | pH, ORP | 12 mesi | 9 – 18 mesi |

Le attività sono seguite **per sonda**, secondo le raccomandazioni ufficiali di Red Sea. Le sonde di temperatura e di perdita non hanno promemoria di calibrazione, e la cella EC a 4 poli non viene mai sostituita secondo un calendario. Vedi la sezione [Manutenzione](maintenance.it.md#manutenzione).

---

[← Torna alla pagina principale](README.it.md)
