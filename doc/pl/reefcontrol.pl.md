[← Powrót do strony głównej](README.pl.md)

# ReefControl:
<p align="center">
<img src="../img/rscontrol_devices.png" alt="Image">
</p>

Hub ReefControl (RSCONTROLPRO / RSCONTROLLITE) odczytuje sondy ReefSense podłączone do jego skrzynek rozszerzeń, steruje swoimi portami 12V DC (2 w Pro, 1 w Lite), a po sparowaniu także gniazdami [ReefControl-Power](reefcontrol-power.pl.md#reefcontrol-power).

- **Sondy ReefSense** — pH, ORP, zasolenie (EC), temperatura, ATO (poziom wody) i wyciek: wartość i poziom (pożądany / akceptowalny / niebezpieczny), status, nazwa, uid, daty ostatniej instalacji i ostatniej kalibracji oraz temperatura wbudowana w sondy pH, EC i ATO. Każda encja sondy ma atrybuty `probe_uid`, `probe_type` i `probe_index`, a czujniki pomiarowe dodatkowo atrybut `ranges` (`[acceptable_low, desired_low, desired_high, acceptable_high]`).
- **Sondy zasolenia** — czujniki przewodności, zasolenia (ppt) i gęstości właściwej oraz select jednostki wyświetlania.
- **Sondy wycieku** — stan suchy/mokry, **pochodzenie wody** (sucho / woda z akwarium / woda RO/DI) i zmierzona przewodność, odczytywane, gdy tylko sonda wykryje wodę.
- **Ustawienia sondy** — zakresy pożądany i akceptowalny (główny odczyt i temperatura wbudowana), przełączniki włączona / buzzer / powiadomienia / konserwacja oraz przycisk „Odczytaj teraz”, który pobiera świeży odczyt bez czekania na kolejne odpytanie.
- **Kalibracja sond** — zob. [niżej](#kalibracja-sond).
- **Buzzer** — buzzer zagrożenia i buzzer wycieku (włączenie, częstotliwość, wypełnienie), eliminacja drgań sygnału zagrożenia, przełącznik detektora wycieku; stan aktywny / wyciszony buzzera i jego przyczyna.
- **Porty 12V** — edytowalna nazwa, przełącznik wł./wył., stan, tryb, typ, zużycie i przycisk „Odinstaluj port”. Czujnik `port_N_mode` zawiera w atrybutach całą konfigurację portu, jego harmonogram i regułę sondy, aby karta mogła edytować port (zob. [Tryby portów i gniazd](#tryby-portów-i-gniazd)).
- **Parowanie z ReefControl-Power** — sparowany Power Center, jego stan i połączenie, przyciski „Sparuj Power Center” / „Rozłącz Power Center” oraz przycisk „Wypisz gniazdko” dla każdego gniazda Power Center sterowanego przez sondę huba.
- **Dodawanie, wymiana i usuwanie sond** z menu opcji integracji (zob. [niżej](#zarządzanie-sondami-dodawanie--wymiana--usuwanie)).
- Zapisy są pokazywane natychmiast (aktualizacja optymistyczna), a następnie potwierdzane ponownym odczytem urządzenia.

<p align="center">
<img src="../img/rscontrol_sensors.png" alt="Image">
<img src="../img/rscontrol_ctrl.png" alt="Image">
<img src="../img/rscontrol_conf.png" alt="Image">
<img src="../img/rscontrol_diag.png" alt="Image">
</p>

> [!TIP]
> [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) rysuje hub, jego sondy, porty i sparowany Power Center, a kalibracje i tryby portów obsługuje w kilku kliknięciach.

## Zarządzanie sondami (dodawanie / wymiana / usuwanie)
Sondami BLE (pH, ORP, EC, ATO, wyciek, temperatura) zarządza się z menu **Opcje** integracji, tak jak w aplikacji Red Sea:

<p align="center">
<img src="../img/rscontrol_probe_management.png" alt="Image">
</p>

- **Dodanie sondy**: przełącz sondę w tryb parowania, wybierz jej typ i potwierdź, aby rozpocząć wyszukiwanie. Sonda jest konfigurowana tak jak w aplikacji: sonda wycieku, na przykład, otrzymuje nazwę `Leak <uid>` z włączonym buzzerem, detektorem wycieku i powiadomieniami.
- **Wymiana sondy**: wybierz sondę do wymiany, przełącz nową sondę tego samego typu w tryb parowania i potwierdź. Nowa sonda przejmuje historię i statystyki poprzedniej.
- **Usunięcie sondy**: wybierz jedną lub kilka sond i potwierdź — spowoduje to trwałe usunięcie encji sondy i ich historii.

> [!NOTE]
> Ponowna instalacja sondy resetuje jej ustawienia w hubie (sonda ORP wraca do fabrycznych zakresów). Integracja ponownie odczytuje konfigurację sond, gdy tylko sonda się pojawi lub zostanie ponownie zainstalowana, czy to z Home Assistant, czy z aplikacji ReefBeat.

## Kalibracja sond
Każdy typ sondy kalibruje się tak jak w aplikacji ReefBeat.

| Sonda | Jak | Encja / usługa |
| ----- | --- | -------------- |
| ORP | Zanurz sondę w roztworze kalibracyjnym, a następnie ustaw liczbę na wartość roztworu | `Kalibruj {probe} (wartość roztworu)` |
| Temperatura | Ustaw liczbę na rzeczywistą temperaturę wody, w której jest sonda | `Kalibruj {probe} (rzeczywista temperatura)` |
| Temperatura wbudowana (pH, EC, ATO) | Tak samo, dla czujnika temperatury wbudowanego w sondę | `Kalibruj temperaturę {probe} (rzeczywista temperatura)` |
| pH | Dwa punkty: pH 7, potem pH 10 (woda morska) lub pH 4 (woda słodka) | `redsea.probe_calibration` |
| Zasolenie (EC) | Jeden punkt, z wartością roztworu w mS/cm | `redsea.probe_calibration` |

**Liczby wartości referencyjnej** (ORP i temperatury) pokazują bieżący odczyt. Ustawienie jednej z nich na wartość referencyjną ponownie odczytuje sondę i przesuwa jej offset o `wartość referencyjna - odczyt`, dzięki czemu sonda odczytuje potem wartość referencyjną.

**Kalibracje pH i EC** są wieloetapowe i przechodzą przez usługę `redsea.probe_calibration`, jeden krok na wywołanie: `enter`, następnie `point` dla każdego punktu kalibracji, `status` odpytywany, aż hub zgłosi sukces lub porażkę (w międzyczasie zwraca `calibration_status`, `time_left` i `stability_progress`), a na końcu `exit`. [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) wykonuje całą sekwencję za Ciebie.

```yaml
action: redsea.probe_calibration
data:
  device_id: <config entry of the hub>
  probe_type: ph
  probe_uid: "0x00B39"
  action: point
  point: MID
  solution_value: 7.0
  solution_rated_temp: 25
```

Data ostatniej kalibracji pochodzi z huba: sonda pH lub EC skalibrowana w aplikacji ReefBeat albo sprawdzona sonda ORP oznacza swoje zadanie konserwacyjne jako wykonane w tym dniu.

## Scalanie temperatury z wielu sond
Gdy dostępne są co najmniej dwa źródła temperatury (dedykowana sonda temperatury oraz temperatura wbudowana w sondy EC/pH/ATO), ReefControl oblicza solidną **scaloną temperaturę** na podstawie pojedynczych odczytów:

- **Temperatura scalona** (`sensor`): pojedyncza wartość zagregowana wybraną metodą — Mediana (domyślnie), Średnia, Minimum lub Maksimum. Konfigurowalna przez encję select **Metoda scalania temperatury**.
- **Spójność temperatury** (`binary_sensor`) oraz **Rozrzut temperatury** (`sensor`, diagnostyczny): pokazują, czy źródła są zgodne w granicach **Progu spójności temperatury** (konfigurowalny, domyślnie 0,5 °C), oraz jak bardzo się różnią.
- **Źródło anomalii temperatury** (`sensor`, diagnostyczny): `OK`, gdy wszystkie źródła są zgodne, nazwa sondy (sond) podejrzewanej o dryf lub błędny odczyt, albo `Nieznane`, gdy niezgodności nie można przypisać jednej sondzie. Atrybuty czujnika wymieniają każde źródło wraz z wartością, zmianą w ciągu 1 godziny i statusem.
- **Przełącznik konserwacji dla każdej sondy obsługującej temperaturę**: jego włączenie tymczasowo wyklucza daną sondę z obliczeń scalania/spójności/anomalii, dzięki czemu czyszczenie lub kalibracja nigdy nie wywołują fałszywego alarmu.
- **Kalibracja względem rzeczywistej temperatury** (`number`) dla każdej sondy obsługującej temperaturę (zob. [Kalibracja sond](#kalibracja-sond)).

Te encje pojawiają się dopiero, gdy wykryte zostaną co najmniej dwa źródła temperatury.

## Tryby portów i gniazd
Port 12V huba, tak jak gniazdo Power Center, działa w jednym z czterech trybów: **off**, **on**, **schedule** (harmonogram) lub **sensor** (sterowany sondą). Port jeszcze niezainstalowany jest w trybie `setup` i odrzuca każdy zapis, dopóki nie zostanie zainstalowany.

Te ustawienia nie są udostępniane jako osobne encje — przy kilku portach i gniazdach oraz zestawie progów dla każdego typu sondy byłyby to dziesiątki rzadko używanych encji. Konfiguruj je z [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), która wykonuje te same wywołania co aplikacja ReefBeat w jednym kroku przez usługę `redsea.request` (zob. Usługi integracji w Narzędziach deweloperskich Home Assistant).

Czujnik `port_N_mode` zawiera jednak wszystko, czego automatyzacja potrzebuje do odczytu aktywnej konfiguracji: `config` (cały wpis portu, łącznie z `power_on_percent`), `schedule` (odczytywany z huba, dopóki port jest w trybie harmonogramu) i `sensor_config` (reguła sondy), z `sensor_source: control`.

> [!NOTE]
> Port sterujący pompą ATO na podstawie sondy ATO pozostaje typu `other`: łączy je kreator zestawu ATO w aplikacji ReefBeat. Hub nie udostępnia poleceń ATO z RSATO+ (ręczne napełnianie, automatyczne napełnianie, pozostała objętość…).

## Zadania konserwacyjne
| Zadanie | Sondy | Domyślnie | Zakres |
| ------- | ----- | --------- | ------ |
| Wyczyść sondę | Wszystkie | 30 dni | 2 – 8 tygodni |
| Skalibruj sondę | pH | 3 miesiące | 2 – 4 miesiące |
| Skalibruj sondę | Zasolenie (EC) | 2 miesiące | 1 – 3 miesiące |
| Sprawdź sondę | ORP | 6 miesięcy | 5 – 7 miesięcy |
| Wymień sondę | pH, ORP | 12 miesięcy | 9 – 18 miesięcy |

Zadania są śledzone **dla każdej sondy osobno**, zgodnie z oficjalnymi zaleceniami Red Sea. Sondy temperatury i wycieku nie mają przypomnienia o kalibracji, a 4-biegunowa cela EC nigdy nie jest wymieniana według harmonogramu. Zob. sekcję [Konserwacja](maintenance.pl.md#konserwacja).

---

[← Powrót do strony głównej](README.pl.md)
