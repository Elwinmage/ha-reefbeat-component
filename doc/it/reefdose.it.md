[← Torna alla pagina principale](README.it.md)

# ReefDose:
- Modificare la dose giornaliera
- Dose manuale
- Aggiungere e rimuovere supplementi
- Modificare e controllare il volume del contenitore. Le impostazioni del volume vengono abilitate o disabilitate automaticamente in base all'interruttore di controllo del volume.
- Abilitare/disabilitare la programmazione per ogni pompa
- Configurazione dell'avviso di scorta
- Ritardo di dosaggio tra i supplementi
- Adescamento (Leggi [questo](#calibrazione-e-adescamento))
- Calibrazione (Leggi [questo](#calibrazione-e-adescamento))
- [Regolazione del dosaggio](#regolazione-del-dosaggio): dosaggio assistito e salamoia
- [Cronologia delle dosi](poseidon.it.md#cronologia-delle-dosi), in modalità Poseidon

<p align="center">
<img src="../img/rsdose_devices.png" alt="Image">
</p>

### Principale
<p align="center">
<img src="../img/rsdose_main_conf.png" alt="Image">
<img src="../img/rsdose_main_diag.png" alt="Image">
</p>

### Teste
<p align="center">
<img src="../img/rsdose_ctrl.png" alt="Image">
<img src="../img/rsdose_sensors.png" alt="Image">
<img src="../img/rsdose_diag.png" alt="Image">
</p>

#### Calibrazione e adescamento

> [!CAUTION]
> Devi seguire rigorosamente l'ordine indicato sotto (usare la [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) è più sicuro).<br /><br />
> <ins>Calibrazione</ins>:
>  1. Posiziona il contenitore graduato e premi "Avvia Calibrazione"
>  2. Inserisci il valore misurato nel campo "Dose di Calibrazione"
>  3. Premi "Imposta Valore di Calibrazione"
>  4. Svuota il contenitore graduato e premi "Prova la nuova Calibrazione". Se il valore ottenuto non è 4 mL, torna al passo 1.
>  5. Premi "Ferma e Salva Graduazione"
>
> <ins>Per l'adescamento</ins>:
>  1. (a) Premi "Avvia Adescamento"
>  2. (b) Quando il liquido esce, premi "Ferma Adescamento"
>  3. (1) Posiziona il contenitore graduato e premi "Avvia Calibrazione"
>  4. (2) Inserisci il valore misurato nel campo "Dose di Calibrazione"
>  5. (3) Premi "Imposta Valore di Calibrazione"
>  6. (4) Svuota il contenitore graduato e premi "Prova la nuova Calibrazione". Se il valore ottenuto non è 4 mL, torna al passo 1.
>  7. (5) Premi "Ferma e Salva Graduazione"
>
> ⚠️ L'adescamento deve sempre essere seguito da una calibrazione (passi da 1 a 5)!⚠️

<p align="center">
  <img src="../img/calibration.png" alt="Image">
</p>

### Regolazione del dosaggio

Ogni testa ha un selettore **Regolazione del dosaggio**: *Disattivata*, *Dosaggio assistito* o *Salamoia (salinità)*. La [ha-reef-card](https://github.com/Elwinmage/ha-reef-card/blob/main/doc/it/reefdose.it.md#regolazione-del-dosaggio) raccoglie le sue entità nella finestra di configurazione della testa.

Il volume d'acqua viene da **Volume d'acqua della vasca** quando lo imposti; altrimenti dall'acquario [ReefTank](https://github.com/Elwinmage/ha-reeftank-component) del dosatore; altrimenti dal suo acquario cloud ReefBeat. Il sensore **Volume d'acqua usato** indica quale si applica.

#### Dosaggio assistito

Imposti un obiettivo (ad esempio KH 8,4 dKH) e registri i risultati dei tuoi test. Dai risultati e dai volumi realmente dosati tra un test e l'altro (il `/daily-log` del dosatore), l'integrazione stima ciò che la vasca consuma e **propone** una dose giornaliera. Nulla arriva al dosatore finché non la applichi.

1. Scegli il **Parametro regolato** (KH, calcio, magnesio, potassio, nitrato, fosfato, iodio o ferro) e imposta l'**Obiettivo di regolazione**.
2. Controlla la **Potenza dell'integratore**: quanto 1 mL alza il parametro in 100 L, come indicato sul flacone. È precompilata per gli integratori la cui etichetta la riporta.
3. Dopo ogni test, inserisci il valore in **Risultato del test** e premi **Registra risultato del test**, oppure chiama `redsea.record_measurement` (utile per un test datato: `measured_at`).
4. Quando **Stato della regolazione** indica *Nuova dose proposta*, guarda **Dose giornaliera proposta** e premi **Applica dose proposta** o **Ignora dose proposta**.

La proposta è ciò che la vasca consuma più una correzione: lo scarto dall'obiettivo distribuito sui giorni della **Distribuzione della correzione**, nulla entro la **Tolleranza di regolazione**. Si allontana al massimo della **Variazione max della dose** (20 % di default) dalla dose attuale, e un cambiamento sotto il 5 % non viene proposto. Un test troppo lontano dal previsto dà *Nuovo test consigliato* invece di una proposta.

> [!NOTE]
> Con teste raggruppate (Red Sea Complete Reef Care), solo la testa 1 può essere regolata, in dosaggio assistito sul calcio: il dosatore ne deriva le altre teste.

#### Salamoia

La testa contiene una salamoia, sale sciolto in acqua: l'integratore **DIY - Brine**, l'unico regolato sulla salinità. Home Assistant legge un sensore di salinità (una sonda EC di ReefControl o qualsiasi sensore, selettore **Sensore di salinità**) ogni 10 minuti e invia piccole dosi manuali per mantenere la sua media di 24 ore sull'obiettivo (35 ppt di default). Usa di proposito dosi manuali e non il programma della testa: quando Home Assistant è fermo non viene dosato nulla, e la salinità scende solo lentamente.

| Impostazione | Default | Uso |
| ------------ | ------- | --- |
| Obiettivo di regolazione | 35 ppt | Salinità da mantenere |
| Concentrazione della salamoia | 200 g/L | Ciò che hai preparato |
| Aumento max di salinità | 0,5 ppt/giorno | Correzione più rapida consentita |
| Dosi di salamoia al giorno | 12 | Ripartizione del volume giornaliero |
| Tolleranza del controllo con rifrattometro | 1 ppt | Scarto accettato tra il controllo e la sonda |

**Salamoia prevista al giorno** dà il volume previsto. Registra ogni mese una lettura al rifrattometro come risultato del test `salinity`: fuori tolleranza, la regolazione si mette in pausa finché la sonda non viene ricalibrata. Senza controllo per 45 giorni, l'aumento consentito al giorno si dimezza.

**Allarme di regolazione** si attiva, e viene emesso un evento `redsea_dose_regulation_alarm`, quando la salinità è troppo alta (la salamoia non può abbassarla), quando non può essere riportata all'obiettivo, quando il sensore è perso e quando serve una ricalibrazione.

### Attività di manutenzione
| Attività | Livello | Predefinito | Intervallo |
| -------- | ------- | ----------- | ---------- |
| Calibrare le teste di dosaggio | Apparecchio | 90 giorni | 80 – 120 giorni |
| Sostituire teste e tubi | Per testa | 15 mesi | 11 – 19 mesi |

L'attività di sostituzione è tracciata **per testa**, quindi sostituire la testa 2
non azzera il conto alla rovescia delle altre tre. Vedi la sezione
[Manutenzione](maintenance.it.md#manutenzione).

---

[← Torna alla pagina principale](README.it.md)
