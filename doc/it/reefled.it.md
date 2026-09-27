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
[LED virtuale](virtual-led.it.md#led-virtuale).
Vedi la sezione [Manutenzione](maintenance.it.md#manutenzione).

---

[← Torna alla pagina principale](README.it.md)
