[← Torna alla pagina principale](README.it.md)

# ReefLED:

- Leggere e impostare i canali Bianco e Blu (solo per G1: RSLED50, RSLED90, RSLED160)
- Leggere e impostare temperatura colore, intensità e luna (tutti i LED)
- Gestire l'acclimatazione. Le impostazioni di acclimatazione vengono abilitate o disabilitate automaticamente in base all'interruttore di acclimatazione.
- Gestire la fase lunare. Le impostazioni della fase lunare vengono abilitate o disabilitate automaticamente in base al relativo interruttore.
- Impostare la modalità colore manuale, con o senza durata.
- Leggere i valori di ventola e temperatura.
- Leggere nome e valore dei programmi (con supporto cloud). Solo per i LED G1.

<p align="center">
<img src="../img/rsled_G1_ctrl.png" alt="Image">
<img src="../img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="../img/rsled_G1_sensors.png" alt="Image">
<img src="../img/rsled_conf.png" alt="Image">
</p>

***

Il supporto della temperatura colore per i LED G1 tiene conto delle specificità di ciascuno dei tre modelli.
<p align="center">
<img src="../img/leds_specs.png" alt="Image">
</p>

***
## IMPORTANTE per i LED G1 e G2

### LED G2

#### Intensità
Poiché i LED G2 garantiscono un'intensità costante su tutta la gamma di colori, i tuoi LED non sfruttano la piena capacità al centro dello spettro. A 8.000K il canale bianco è al 100% e il canale blu allo 0% (il contrario a 23.000K). A 14.000K con intensità 100% sui G2, la potenza dei canali bianco e blu è di circa l'85%.
Ecco la curva di perdita dei G2.
<p align="center">
<img src="../img/intensity_factor.png" alt="Image">
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
<img src="../img/intensity_compensation.png" alt="Image">
</p>

In altre parole, senza compensazione un'intensità del x% a 9.000K non fornisce lo stesso PAR che a 23.000K o 15.000K.

Ecco le curve di potenza:
<p align="center">
<img src="../img/PAR_curves.png" alt="Image">
</p>

Se vuoi sfruttare tutta la potenza del tuo LED, disabilita la compensazione dell'intensità (predefinito).

Se abiliti la compensazione dell'intensità, l'intensità luminosa sarà costante su tutti i valori di temperatura colore, ma al centro della gamma non userai la piena capacità dei tuoi LED (come sui modelli G2).

Nota inoltre che, con la compensazione abilitata, il fattore di intensità può superare il 100% sui G1 se regoli manualmente i canali Bianco/Blu. Questo ti permette di sfruttare tutta la potenza dei tuoi LED!

***

### Programma meteo
La lampada può seguire il meteo di un luogo: in **modalità meteo GPS** la
sua settimana viene costruita dal meteo dei prossimi sette giorni
(previsioni) o dei sette giorni appena trascorsi (meteo misurato), fornito
da [Open-Meteo](https://open-meteo.com) (gratuito, senza chiave). Non c'è
nulla da confermare: attivando la modalità, i programmi propri della lampada
vengono messi da parte e la settimana meteo viene inviata subito; il meteo
viene poi riletto ogni pochi giorni (da 3 a 15, a scelta; controllato una
volta al giorno, alle 00:10) e a ogni modifica di un'impostazione (30 s dopo
l'ultima). Disattivando la modalità, i programmi propri della lampada
vengono riscritti.

| Entità | Ruolo |
| ------ | ----- |
| `switch` Modalità meteo GPS | Meteo GPS, oppure i programmi standard della lampada |
| `select` Periodo meteo | Settimana prossima (previsioni) o scorsa (misurata) |
| `number` Aggiornamento meteo (giorni) | Giorni tra due letture del meteo, da 3 a 15 |
| `text` Luogo meteo | `lat, lon`, un URI `geo:` o un link di Google Maps / OpenStreetMap / Apple Mappe; vuoto per la casa di Home Assistant |
| `select` Giornata meteo sull'acquario | Ora del luogo, ancorata all'alba, al tramonto, oppure distesa tra i due |
| `time` Alba meteo / Tramonto meteo | Orari dell'acquario usati da questi ancoraggi |
| `number` Intensità minima meteo / Intensità massima meteo | Limiti dell'intensità |
| `switch` Nuvole meteo | Imposta le nuvole della lampada nelle ore nuvolose |
| `sensor` Programma meteo | Risultato dell'ultima lettura (stato, luogo e, per ogni giorno, sole, soleggiamento, copertura nuvolosa e intensità massima); `writing` (`{done, total}` giorni) mentre una settimana viene inviata alla lampada |

Come viene costruita una giornata:
- **Orari** — dall'alba al tramonto del luogo, all'ora del luogo (una
  barriera delle Figi sorge alle 06:00 anche sulla lampada), oppure ancorati
  all'acquario: *alba* (la giornata del luogo inizia all'ora scelta),
  *tramonto* (finisce all'ora scelta) o *entrambi* (la giornata del luogo è
  distesa tra i due orari).
- **Intensità** — segue il sole effettivamente ricevuto (radiazione solare
  oraria, 1000 W/m² valgono pieno sole), tra il minimo e il massimo; fino a
  8 punti al giorno.
- **Colore** — quello del programma standard della lampada nello stesso
  momento della sua giornata: il suo equilibrio bianco/blu su una G1, la sua
  temperatura colore su una G2. Al suo posto puoi scegliere i tuoi colori,
  per giorno della settimana (impostazione `colors`:
  `{giorno: [{at, k}]}`, `at` dall'alba, 0, al tramonto, 1, `k` la
  temperatura colore da 8.000 a 23.000 K); una G1 li converte con la tabella
  del suo modello. Questa impostazione non ha un'entità: si imposta
  dall'editor dei programmi di ha-reef-card, oppure con
  `redsea.led_weather_save`.
- **Nuvole** — nelle ore con almeno il 40 % di copertura: Low, Medium o High
  secondo la copertura media; rimosse in una giornata serena.
- **Luna** — mantiene il suo posto dopo il tramonto.

Il programma si chiama *Weather* sulla lampada. Le richieste scritte su una
lampada sono distanziate (di 2 s): una ReefLED risponde in ritardo, o non
risponde affatto, a un comando inviato troppo presto; scrivere una settimana
richiede quindi un po' di tempo.

Le lampade di un gruppo ([LED virtuale](virtual-led.it.md#led-virtuale)) condividono un unico
programma meteo: attivato o impostato su una qualsiasi di esse, lo è per
tutte. Ogni lampada riceve la propria settimana meteo, nel proprio formato,
e il controllo quotidiano viene fatto una sola volta, dal gruppo.

| Servizio | Ruolo |
| -------- | ----- |
| `redsea.led_weather_apply` | Rilegge il meteo e invia subito la settimana (solo in modalità meteo), ad esempio da un'automazione |
| `redsea.led_weather_preview` | La settimana che darebbero certe impostazioni, e quella propria della lampada: non viene scritto nulla |
| `redsea.led_weather_save` | Salva in una volta le impostazioni e la modalità (`enabled`), poi scrive la settimana (in background, oppure prima di rispondere con `wait`) |

***

### Sfasamento dell'alba
Ogni ReefLED che risponde a `/offset` (verificato all'avvio) riceve un
`number` Sfasamento dell'alba (minuti): la lampada esegue tutto il
suo programma con quel ritardo. In un gruppo, l'
[alba sfalsata](virtual-led.it.md#led-virtuale) del LED virtuale lo imposta per ogni lampada.

***

### Libreria cloud
Con un account cloud ReefBeat ([API Cloud](README.it.md#aggiungere-lapi-cloud)), i programmi luce
della libreria dell'app ReefBeat possono essere letti e scritti, come fa
l'editor dei programmi di ha-reef-card. I programmi G1 sono conservati per
acquario, quelli G2 per account; quelli di Red Sea non possono essere né
modificati né eliminati.

| Servizio | Ruolo |
| -------- | ----- |
| `redsea.led_library` | Elenca i programmi che la lampada può usare (`linked: false` senza account cloud) |
| `redsea.led_library_save` | Aggiunge un programma (`name`, `program`, `clouds`), oppure ne aggiorna uno dei tuoi (`uid`) |
| `redsea.led_library_delete` | Elimina uno dei tuoi programmi (`uid`) |
| `redsea.led_convert` | Converte punti G1 tra bianco/blu e kelvin/intensità, con la tabella del modello e la compensazione dell'intensità |

***

### Attività di manutenzione
| Attività | Predefinito | Intervallo |
| -------- | ----------- | ---------- |
| Pulire le lenti | 3 settimane | 1 – 5 settimane |
| Spolverare ventola e griglie | 6 mesi | 5 – 7 mesi |

Le stesse due attività vengono create per ogni generazione di ReefLED, incluso il
[LED virtuale](virtual-led.it.md#led-virtuale).
Vedi la sezione [Manutenzione](maintenance.it.md#manutenzione).

---

[← Torna alla pagina principale](README.it.md)
