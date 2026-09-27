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

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Image">
</p>

### Principale
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Image">
</p>

### Teste
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Image">
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
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Image">
</p>

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
