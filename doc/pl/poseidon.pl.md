[← Powrót do strony głównej](README.pl.md)

# Tryb Poseidon

<p align="center">
<img src="../img/poseidon/poseidon.png" alt="Poseidon" width="240">
</p>

Tryb Poseidon umieszcza w Home Assistant przekaźnik między twoimi urządzeniami
ReefBeat a brokerem MQTT Red Sea. Urządzenie w trybie Poseidon łączy się z
Home Assistant zamiast z `mqtt.reef-beat.com`, a Home Assistant przekazuje jego
ruch do Red Sea bez zmian: aplikacja ReefBeat działa jak dotąd.

> [!WARNING]
> Tryb Poseidon jest eksperymentalny. Na razie tylko przekazuje i obserwuje
> ruch: integracja nadal odpytuje urządzenia.

## Dodawanie Poseidon

*Ustawienia > Urządzenia i usługi > Red Sea > Dodaj wpis > Tryb Poseidon*

- **Port nasłuchu**: proponowany jest pierwszy wolny port od 1884 (1883 i
  8883, zwykłe porty MQTT, są pomijane). Jest sprawdzany ponownie przy
  zatwierdzeniu i przy każdym uruchomieniu przekaźnika: jeśli zajęła go inna
  usługa, informuje o tym zgłoszenie naprawy, a urządzenia pozostają
  nietknięte.
- **Adres Home Assistant**: adres IPv4, pod którym urządzenia łączą się z Home
  Assistant.
- **Konto w chmurze**: konto ReefBeat używane do pobrania kluczy urządzeń.
  Konto w chmurze jest wymagane.

## Dodawanie urządzeń

*Poseidon > Konfiguruj > Dodaj urządzenia*

Każde urządzenie integracji jest wymienione ze swoim statusem:

| Status | Znaczenie |
|---|---|
| Do zaznaczenia | Jego klucze są znane: od razu przechodzi w tryb Poseidon |
| Do zaznaczenia, 🔑 | Najpierw trzeba pobrać jego klucze (patrz niżej) |
| Już w trybie Poseidon | Nic do zrobienia |
| Bez danych chmury | Powiązane z lokalnym akwarium: tryb Poseidon niedostępny |
| Brak w koncie chmury | Jego kluczy nie można pobrać tym kontem |
| Niedostępne | Nie odpowiada |

> [!CAUTION]
> **Pobranie kluczy jest destrukcyjne.** Urządzenie nie udostępnia swoich
> kluczy: aby je uzyskać, jest usuwane z chmury ReefBeat i tworzone ponownie.
> - zostaje odłączone od swojego akwarium, a aplikacja może poprosić o ponowne
>   sparowanie;
> - harmonogramy, ustawienia i historia przechowywane dla niego w chmurze mogą
>   zostać utracone;
> - jego konfiguracja jest zapisywana przed i porównywana po: ReefRun i
>   ReefWave odzyskują swoją automatycznie, dla pozostałych urządzeń zmiany są
>   wymienione w powiadomieniu (zapisana konfiguracja zostaje w
>   `/config/redsea/poseidon/snapshots/`).
>
> Pobranie odbywa się raz na urządzenie: Home Assistant przechowuje klucze,
> nawet jeśli Poseidon zostanie usunięty.

## Przełącznik Poseidon

Każde urządzenie ze znanymi kluczami ma na swojej stronie przełącznik **Tryb
Poseidon**:

- **włączony**: urządzenie komunikuje się z Red Sea przez Home Assistant;
- **wyłączony**: urządzenie komunikuje się z Red Sea bezpośrednio (tryb
  normalny).

Jego stan jest odczytywany z samego urządzenia. Jego atrybuty:

| Atrybut | Znaczenie |
|---|---|
| `connection_state` | Stan połączenia zgłaszany przez urządzenie |
| `last_up` / `last_down` | Ostatni ruch urządzenie → Red Sea / Red Sea → urządzenie |
| `silent` | W trybie Poseidon, ale przez czas z ustawień nic nie przeszło przez przekaźnik |

Ciche urządzenie wywołuje też zgłoszenie naprawy, które znika samo, gdy ruch
wznowi się. Ciche urządzenie nigdy nie jest automatycznie przełączane z
powrotem.

## Co się dzieje i kiedy

| Zdarzenie | Urządzenia |
|---|---|
| Restart Home Assistant, przeładowanie Poseidon | Pozostają bez zmian: łączą się ponownie, gdy przekaźnik wróci |
| Poseidon wyłączony lub usunięty | Wszystkie wracają do trybu normalnego |
| Urządzenia nie da się przełączyć z powrotem | Wymienione w powiadomieniu |

W tryb Poseidon przechodzi się tylko z twojej decyzji. Każde automatyczne
przełączenie prowadzi z powrotem do trybu normalnego.

## Strategie

Co Home Assistant robi z urządzeniem w trybie Poseidon. Każde urządzenie ma
obok przełącznika wybór **Strategia Poseidon**; ustawienia podają wartość
domyślną.

| Strategia | Odpytywanie | Wysłane stany | Plik |
|---|---|---|---|
| *Szpieg* | bez zmian | zapisywane, porównywane z następnym odpytaniem | `spy.jsonl` |
| *Shadow* | bez zmian | scalane z danymi urządzenia, porównywane z następnym odpytaniem | `shadow.jsonl` |
| *Poseidon* | co N minut | używane; urządzenie jest odczytywane ponownie przy każdym stanie, dopóki jego rodziny nie da się scalić | — |

> [!NOTE]
> Żadnej rodziny urządzeń nie da się jeszcze scalić: scalanie powstaje na
> podstawie plików szpiega. Do tego czasu *Shadow* tylko porównuje, a
> *Poseidon* odczytuje urządzenie ponownie za każdym razem, gdy wyśle stan.

### Szpieg

`/config/redsea/poseidon/logs/spy.jsonl` (rotacja przy 10 MB, 5 plików)
zawiera, z tym samym zegarem:

| `kind` | Wpis |
|---|---|
| `publish`, `control` | ramka między urządzeniem a Red Sea, w obu kierunkach, odszyfrowana |
| `http` | żądanie HTTP wysłane przez Home Assistant do urządzenia: metoda, endpoint, status (0 = brak odpowiedzi), czas, dane; `origin` to `integration` lub `poseidon` (jego odczyty `/cloud` co 60 s) |
| `compare` | wysłany stan wobec następnego odpytania, każda wartość `same`, `differs` lub `unknown` |
| `mark` | zmieniła się strategia lub pauza |

Urządzenie w trybie szpiega ma też przełącznik **Pauza odpytywania**: nie
dostaje żadnego żądania, łącznie z odczytami `/cloud` przez Poseidon; co wtedy
wysyła, wysyła samo z siebie. Pauza nie przetrwa restartu.

Zalecany zapis, dla każdego urządzenia (zegary hostów Home Assistant
zsynchronizowane, ta sama strefa czasowa):

1. 30 minut bez żadnego odpytywania: każdy inny Home Assistant czytający
   urządzenie zatrzymany, pauza włączona;
2. 30 minut tylko z odpytywaniem (pauza wyłączona);
3. działania o zapisanych godzinach: z aplikacji ReefBeat, z Home Assistant, na
   samym urządzeniu;
4. jeśli inny Home Assistant odpytuje urządzenie, jego żądania można dodać
   akcją `logger.set_level`, `custom_components.redsea.reefbeat.api: debug`.

## Ustawienia

*Poseidon > Konfiguruj > Ustawienia Poseidon*

- **Domyślna strategia**: strategia urządzeń w trybie Poseidon, które nie
  mają własnej (patrz [Strategie](#strategie)). Domyślnie *Szpieg*.
- **Interwał odpytywania strategii Poseidon**, w minutach (domyślnie 10).
- **Tryb debug**: każda ramka przechodząca przez przekaźnik jest zapisywana
  odszyfrowana do `/config/redsea/poseidon/logs/poseidon.jsonl` (rotacja przy
  10 MB, 5 plików). Dane są w tym pliku jawne.
- **Czas, po którym urządzenie jest ciche**, w minutach (domyślnie 10).
- **Klucz watchdoga**: 16 znaków, proponowany, dopóki żaden nie jest ustawiony.
  Watchdog na innym komputerze (samodzielny lub w
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup))
  pyta przekaźnik, czy działa, i przełącza urządzenia do trybu normalnego, gdy
  nie działa. Skopiuj ten klucz do jego konfiguracji; zostaw pusty, aby nie
  odpowiadać żadnemu watchdogowi.

## Eksport i import kluczy

*Poseidon > Konfiguruj > Eksportuj klucze* daje link do pobrania wszystkich
znanych kluczy, ważny 5 minut. Plik jest generowany po kliknięciu i nigdy nie
jest zapisywany w `/config`; ma format CLI (`keystore.json`) i zawiera klucze
jawnie: przechowuj go bezpiecznie. Akcja `redsea.poseidon_export`, dla
automatyzacji, zapisuje ten sam plik do
`/config/redsea/poseidon/keystore-<data>.json`, czytelnego tylko dla
właściciela.

*Poseidon > Konfiguruj > Importuj klucze* prosi o taki plik i wysyła go z twojej
przeglądarki. Urządzenie jest zastępowane tylko nowszym wpisem, urządzenia bez
kluczy są pomijane, a zaimportowane urządzenia od razu dostają swój
przełącznik.

## Skrypt ratunkowy

*Poseidon > Konfiguruj > Skrypt ratunkowy* daje link do pobrania (5 minut)
pliku `poseidon_rescue.py`: skryptu, który przełącza urządzenia z powrotem na
broker Red Sea bez Home Assistant, gdy ten już tego nie może (zatrzymany,
przekaźnik uszkodzony, integracja usunięta). Działa na dowolnym komputerze w
sieci urządzeń z Pythonem 3.8 lub nowszym, nic więcej do instalowania:

```bash
python3 poseidon_rescue.py --dry-run   # co zostałoby zrobione, bez zmian
python3 poseidon_rescue.py             # urządzenia na przekaźniku, po potwierdzeniu
```

| Opcja | Zastosowanie |
|---|---|
| `--ip HWID=IP` | urządzenie zmieniło adres od pobrania |
| `--scan CIDR` | gdzie szukać urządzeń, które zmieniły adres (można powtarzać) |
| `--no-scan` | nigdy ich nie szukać |
| `--only HWID` | jedno urządzenie (hwid lub nazwa, można powtarzać) |
| `--all` | wszystkie urządzenia, niezależnie od obecnego brokera |
| `--keystore keystore.json` | eksport keystore zamiast wbudowanych urządzeń |
| `--yes` | bez potwierdzenia |

Nic nie jest zapisywane do urządzenia, zanim nie udowodni, że to właściwe:
jego `hwid` odczytany z `/device-info` musi się zgadzać. Urządzenie, które nie
odpowiada już pod swoim adresem lub którego adres należy teraz do innego, jest
szukane w sieci: w /24 każdego znanego adresu i komputera uruchamiającego
skrypt albo w podsieciach `--scan`.

Każde urządzenie dostaje tę samą sekwencję co z Home Assistant (wyłączenie,
zapis brokera i kluczy, włączenie), po czym `/cloud` jest odczytywany ponownie
dla sprawdzenia. Skrypt zawiera klucze jawnie: przechowuj go bezpiecznie i
pobierz ponownie po dodaniu urządzeń.
