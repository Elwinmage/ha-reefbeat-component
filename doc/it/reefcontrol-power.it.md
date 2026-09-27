[← Torna alla pagina principale](README.it.md)

# ReefControl-Power

L'RSPOWER (Power Center) è un dispositivo autonomo con un proprio indirizzo IP, esposto separatamente in Home Assistant.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_devices.png" alt="Image">
</p>

- 6 o 8 prese controllabili a seconda del modello (RSPOWER6 / RSPOWER8)
- **Per presa**: nome modificabile, interruttore acceso/spento, stato, modalità, modalità precedente, consumo e un pulsante «Elimina presa» che riporta la presa allo stato di fabbrica (modalità `setup`, nome di fabbrica)
- **Dispositivo**: consumo totale, livello della batteria, modalità, regione del modello e numero di prese
- **Sonda di temperatura locale** (opzionale): pulsanti di aggiunta / rimozione, pulsante «Recupera temperatura», calibrazione sulla temperatura reale, intervalli di temperatura desiderato e accettabile, nome, interruttori di notifiche e registrazione — tutti disponibili una volta installata la sonda. Il sensore di temperatura porta gli attributi `ranges` e `level`, come le sonde dell'hub.
- **Accoppiamento ReefControl**: hub accoppiato, suo tipo e stato, stato del collegamento e di internet, e un pulsante «Disaccoppia hub di controllo»
- Le scritture vengono mostrate subito (aggiornamento ottimistico), poi confermate rileggendo il dispositivo

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_diag.png" alt="Image">
</p>

> [!NOTE]
> La sonda di temperatura locale e l'hub ReefControl si escludono: «Aggiungi sonda temperatura» è disponibile solo senza nessuno dei due, «Rimuovi sonda temperatura» con una sonda locale e «Disaccoppia hub di controllo» con un hub accoppiato. I pulsanti restano visibili ma non disponibili quando non si applicano.

## Accoppiamento con un ReefControl
L'accoppiamento si avvia sempre dall'hub, con il suo pulsante **Accoppia Power Center**: l'hub si accoppia con il Power Center che trova sulla rete. Il disaccoppiamento funziona da entrambi i lati. Quando i due dispositivi sono configurati in Home Assistant, la modifica compare su entrambi contemporaneamente — per un accoppiamento, solo quando un unico Power Center libero rende certo quale sia.

Una volta accoppiato, le sonde dell'hub possono pilotare le prese. Il Power Center memorizza solo il tipo di sonda che una presa segue; la sonda stessa e le soglie risiedono sull'hub. Due servizi permettono a una card o a un'automazione di leggere quel lato:

- `redsea.get_control_probes` — le sonde di un hub (identità e valori attuali), tramite il suo identificativo hardware
- `redsea.get_control_subscriptions` — le regole che l'hub applica alle prese del suo Power Center, tramite il suo identificativo hardware

Eliminare una presa sul Power Center cancella solo la sua metà di una regola di sonda: il pulsante **Annulla iscrizione presa N** dell'hub cancella l'altra metà.

## Modalità delle prese e prese pilotate da sensore
La modalità di una presa (off / on / schedule / sensor) e le sue impostazioni di programma o di soglia del sensore (ad es. «accendere questa presa quando la temperatura locale scende sotto i 24 °C») si configurano dalla [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), come per le [porte dell'hub](reefcontrol.it.md#modalità-delle-porte-e-delle-prese).

Ogni presa espone un'entità `sensor.socket_N_mode` per le automazioni: il suo stato è la modalità attuale della presa, e i suoi attributi portano lo `schedule` attuale e (in modalità sensor) la `sensor_config`, contrassegnata da `sensor_source`: `local` per la sonda propria del Power Center, `control` per una regola dell'hub accoppiato.

Una presa pilotata da un programma o da una sonda può essere spenta a mano: la sua modalità indica allora `off`, mentre il sensore **modalità precedente** conserva la modalità automatica a cui tornerà.

Il dispositivo esce automaticamente dallo stato iniziale «setup» non appena viene configurata la prima presa, come fa l'app ReefBeat — nessuna azione manuale necessaria.

---

[← Torna alla pagina principale](README.it.md)
