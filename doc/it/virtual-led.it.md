[← Torna alla pagina principale](README.it.md)

# LED Virtuale
Un LED virtuale è un **gruppo** di ReefLED, come i LED «raggruppati»
dell'app ReefBeat: le sue lampade si comandano come una sola.

- Crea un dispositivo virtuale dal pannello dell'integrazione, poi usa il
  pulsante di configurazione: scegli i LED (almeno due, un LED appartiene a
  un solo gruppo), poi il loro ordine. Un nuovo LED virtuale parte dalle
  lampade che l'app ReefBeat raggruppa già, nell'ordine dell'app.
- Puoi usare solo Kelvin e intensità per controllare i tuoi LED se hai dei G2 o un misto di G1 e G2.
- Puoi usare sia Kelvin/Intensità sia Bianco e Blu se hai solo LED G1.

<p align="center">
<img src="../img/virtual_led_config_1.png" alt="Image">
<img src="../img/virtual_led_config_2.png" alt="Image">
</p>

## Cosa condivide il gruppo
Un valore condiviso impostato sul LED virtuale, o su una delle sue lampade,
viene applicato a tutte le lampade del gruppo: canali manuali, kelvin /
intensità, modalità, timer, programmi, acclimatazione, fase lunare e il
[programma meteo](reefled.it.md#programma-meteo). Ciò che appartiene a una lampada resta sulla
lampada: nome, Wi-Fi, cloud, firmware, identificazione, reset…

Come nell'app, una scrittura di gruppo viene rifiutata quando una delle
lampade non è caricata, non risponde, o è in una modalità che il gruppo non
può comandare (spenta, o trattenuta da una scorciatoia): non viene inviato
nulla, così le lampade restano sincronizzate, e l'errore nomina le lampade
interessate. Una lampada messa fuori servizio nell'app viene esclusa dalle
scritture, dai controlli e dall'alba sfalsata. Il bianco / blu non può
essere impostato su un gruppo che contiene una G2: usa kelvin / intensità.

## Alba sfalsata
Come nell'app, le lampade di un gruppo possono iniziare la giornata una dopo
l'altra:

| Entità | Ruolo |
| ------ | ----- |
| `switch` Alba sfalsata | Sfalsa l'alba delle lampade del gruppo |
| `number` Ritardo dell'alba sfalsata | Minuti tra due lampade, da 1 a 15 (10 per impostazione predefinita) |

Ogni lampada inizia la giornata `ritardo × posizione` minuti più tardi (la
prima lampada del gruppo non viene ritardata). Il valore viene scritto nello
Sfasamento dell'alba di ogni lampada, di nuovo ogni volta che
cambiano le lampade del gruppo o il loro ordine; una lampada che lascia il
gruppo torna a 0.

## Le lampade del gruppo
Il `sensor` LED collegati, sul LED virtuale e su ogni lampada di
un gruppo, dà il numero di lampade e, nell'attributo `leds`, il loro elenco
nell'ordine del gruppo: `hwid`, `name`, `model`, `g2`, `offset` (sfasamento
dell'alba in minuti, vuoto per una lampada senza `/offset`) ed `entry_id`.
ha-reef-card lo usa per elencare le lampade.

## Sincronizzazione con l'app ReefBeat
Con un account cloud ReefBeat ([API Cloud](README.it.md#aggiungere-lapi-cloud)), un gruppo le cui
lampade sono di un solo modello, in un solo acquario e su un solo account è
lo stesso gruppo nell'app: il gruppo, il suo ordine e la sua alba sfalsata
vengono scritti nel cloud, oppure presi dall'app, a seconda del lato che è
cambiato dall'ultima sincronizzazione.

Un gruppo dell'app che nessun LED virtuale comanda (almeno due lampade
caricate in Home Assistant) viene proposto come nuovo LED virtuale tra i
dispositivi «Rilevati», con le sue lampade nell'ordine dell'app; «Ignora» lo
lascia ignorato.

Quando la decisione spetta a te, viene segnalata una riparazione
(Impostazioni > Sistema > Riparazioni):

| Riparazione | Cosa fare |
| ----------- | --------- |
| Nessun account cloud ReefBeat | L'app potrebbe contenere il gruppo, ma nessun account cloud elenca le sue lampade: aggiungi l'account (la riparazione scompare da sola), oppure tieni il gruppo solo in Home Assistant |
| LED raggruppati nell'app ReefBeat | Il gruppo contiene più modelli, che l'app non può raggruppare, e alcune lampade sono ancora raggruppate nell'app: separale lì; il gruppo vive allora solo in Home Assistant |
| Modificato in Home Assistant e nell'app ReefBeat | Entrambi i lati sono cambiati dall'ultima sincronizzazione: scegli il gruppo da tenere |

---

[← Torna alla pagina principale](README.it.md)
