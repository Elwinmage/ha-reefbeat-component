[← Powrót do strony głównej](README.pl.md)

# ReefDose:
- Edytuj dzienną dawkę
- Ręczne dozowanie
- Dodawaj i usuwaj suplementy
- Edytuj i kontroluj objętość pojemnika. Ustawienia objętości pojemnika są automatycznie włączane lub wyłączane zależnie od przełącznika kontroli objętości.
- Włącz/wyłącz harmonogram dla każdej pompy
- Konfiguracja alertów zapasów
- Opóźnienie dozowania między suplementami
- Napełnianie (Proszę przeczytać [to](#kalibracja-i-napełnianie))
- Kalibracja (Proszę przeczytać [to](#kalibracja-i-napełnianie))

<p align="center">
<img src="../img/rsdose_devices.png" alt="Image">
</p>

### Główny
<p align="center">
<img src="../img/rsdose_main_conf.png" alt="Image">
<img src="../img/rsdose_main_diag.png" alt="Image">
</p>

### Głowice
<p align="center">
<img src="../img/rsdose_ctrl.png" alt="Image">
<img src="../img/rsdose_sensors.png" alt="Image">
<img src="../img/rsdose_diag.png" alt="Image">
</p>

#### Kalibracja i napełnianie

> [!CAUTION]
> Musisz ściśle przestrzegać poniższej kolejności (Using the [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) is safer).<br /><br />
> <ins>Calibration</ins>:
>  1. Ustaw pojemnik z podziałką i naciśnij „Rozpocznij kalibrację"
>  2. Wpisz zmierzoną wartość w polu „Dawka kalibracyjna"
>  3. Press "Set Calibration Value"
>  4. Opróżnij pojemnik z podziałką i naciśnij „Testuj nową kalibrację". Jeśli uzyskana wartość nie wynosi 4 mL, wróć do kroku 1.
>  5. Press "Stop and Save Graduation"
>
> <ins>For priming</ins>:
>  1. (a) Press "Start Priming"
>  2. (b) Gdy płyn zacznie wypływać, naciśnij „Zatrzymaj napełnianie przewodów"
>  3. (1) Ustaw pojemnik z podziałką i naciśnij „Rozpocznij kalibrację"
>  4. (2) Wpisz zmierzoną wartość w polu „Dawka kalibracyjna"
>  5. (3) Press "Set Calibration Value"
>  6. (4) Opróżnij pojemnik z podziałką i naciśnij „Testuj nową kalibrację". Jeśli uzyskana wartość nie wynosi 4 mL, wróć do kroku 1.
>  7. (5) Press "Stop and Save Graduation"
>
> ⚠️ Po napełnieniu przewodów zawsze należy wykonać kalibrację (kroki 1 do 5)!⚠️

<p align="center">
  <img src="../img/calibration.png" alt="Image">
</p>

### Zadania konserwacyjne
| Zadanie | Poziom | Domyślnie | Zakres |
| ------- | ------ | --------- | ------ |
| Kalibracja głowic dozujących | Urządzenie | 90 dni | 80 – 120 dni |
| Wymiana głowic i wężyków | Na głowicę | 15 miesięcy | 11 – 19 miesięcy |

Wymiana śledzona jest **osobno dla każdej głowicy**: wymiana głowicy 2 nie
zeruje odliczania pozostałych trzech. Zobacz sekcję [Konserwacja](maintenance.pl.md#konserwacja).

---

[← Powrót do strony głównej](README.pl.md)
