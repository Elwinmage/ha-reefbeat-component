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
> La modalità Poseidon è sperimentale. Per ora si limita a inoltrare e
> osservare il traffico: l'integrazione continua a interrogare i dispositivi.

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
>   ReefWave riottengono la loro automaticamente, per gli altri dispositivi le
>   modifiche sono elencate in una notifica (la configurazione salvata resta in
>   `/config/redsea/poseidon/snapshots/`).
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

> [!NOTE]
> Nessuna famiglia di dispositivi può ancora essere unita: l'unione si scrive a
> partire dai file spia. Fino ad allora, *Shadow* si limita a confrontare, e
> *Poseidon* rilegge il dispositivo ogni volta che invia uno stato.

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

- **Strategia predefinita**: quella dei dispositivi in modalità Poseidon che
  non ne hanno una propria (vedi [Strategie](#strategie)). *Spia* di default.
- **Intervallo di interrogazione della strategia Poseidon**, in minuti (10 di
  default).
- **Modalità debug**: ogni frame che attraversa il relè viene scritto
  decifrato in `/config/redsea/poseidon/logs/poseidon.jsonl` (rotazione a 10
  MB, 5 file conservati). I dati sono in chiaro in quel file.
- **Ritardo prima che un dispositivo sia silenzioso**, in minuti (10 di
  default).
- **Chiave del watchdog**: 16 caratteri, proposta finché non ne è impostata
  una. Un watchdog su un'altra macchina (autonomo, o in
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup))
  chiede al relè se è vivo, e riporta i dispositivi in modalità normale quando
  non lo è. Copia questa chiave nella sua configurazione; lasciala vuota per non
  rispondere a nessun watchdog.

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
