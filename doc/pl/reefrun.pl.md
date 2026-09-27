[← Powrót do strony głównej](README.pl.md)

# ReefRun:
- Ustaw prędkość pompy
- Zarządzaj nadmiernym pienowaniem
- Zarządzaj wykrywaniem pełnego kubka
- Możliwość zmiany modelu skimmera

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Image">
</p>

### Główny
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Image">
</p>

### Pompy
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Image">
</p>

### Zadania konserwacyjne
Zadania są przypisane do podurządzenia pompy i zależą od jej typu.

| Zadanie | Pompa | Domyślnie | Zakres |
| ------- | ----- | --------- | ------ |
| Czyszczenie silnika i wirnika | Powrotna | 4,5 miesiąca | 2 – 7 miesięcy |
| Czyszczenie filtra wlotowego | Powrotna | 6 tygodni | 3 – 9 tygodni |
| Czyszczenie venturi i wężyka powietrza | Odpieniacz | 5 tygodni | 3 – 7 tygodni |
| Czyszczenie wirnika odpieniacza | Odpieniacz | 4,5 miesiąca | 2 – 7 miesięcy |
| Kalibracja sondy pełnego kubka | Odpieniacz | 4 tygodnie | 2 – 6 tygodni |
| Kalibracja sondy nadmiernego odpieniania | Odpieniacz | 4 tygodnie | 2 – 6 tygodni |

Oba zadania kalibracyjne nadzoruje również blueprint alertów, porównując datę
ostatniej kalibracji zgłoszoną przez urządzenie z interwałem ustawionym tutaj. Zobacz sekcję [Konserwacja](maintenance.pl.md#konserwacja).

### Klucz do demontażu wirnika

Powyższe zadanie *Czyszczenie wirnika odpieniacza* wymaga odkręcenia korpusu
pompy, który mokry praktycznie nie daje się chwycić. Klucz do wydruku 3D do tego
zadania, wraz z filmem pokazującym użycie, jest dostępny tutaj:
[Klucz do wirnika DC Skimmer Red Sea](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

---

[← Powrót do strony głównej](README.pl.md)
