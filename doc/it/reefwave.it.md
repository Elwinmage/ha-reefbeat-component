[← Torna alla pagina principale](README.it.md)

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
Per prima cosa crea un dispositivo ["Cloud API"](../../README.md#add-cloud-api) con le tue credenziali, e il gioco è fatto!
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

Vedi la sezione [Manutenzione](maintenance.it.md#manutenzione).

---

[← Torna alla pagina principale](README.it.md)
