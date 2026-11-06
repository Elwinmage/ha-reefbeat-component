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
> Tryb Poseidon jest eksperymentalny. Z domyślną strategią *Szpieg* tylko
> przekazuje i obserwuje ruch: integracja nadal odpytuje urządzenia. Strategie
> *Shadow* i *Poseidon* wykorzystują to, co wysyłają urządzenia (zobacz
> [Strategie](#strategie)).

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
> - jego konfiguracja jest zapisywana przed i porównywana po: ReefRun i ReefWave
>   odzyskują swoją automatycznie, a dla pozostałych urządzeń zmiany są wymieniane
>   w powiadomieniu (zapisana konfiguracja zostaje w
>   `/config/redsea/poseidon/snapshots/`);
> - ReefWave zależy od chmury, która przy każdym połączeniu wysyła jej program:
>   przed usunięciem zapisywane są też własne fale jej akwarium (z intensywnościami
>   każdej pompy) oraz jej program; pobieranie zatrzymuje się, niczego nie usuwając,
>   jeśli nie można ich odczytać. Potem fale utracone przez chmurę są tworzone
>   ponownie (lub odzyskują ustawienia pompy), program jest wysyłany do chmury, a
>   chmura przekazuje go pompom; pompa jest zapisywana bezpośrednio tylko wtedy, gdy
>   go nie otrzymała.
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
| Przekaźnik przestaje działać, a [watchdog](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog) go nadzoruje | Wszystkie wracają do trybu normalnego po potwierdzeniu dostępności Red Sea; bez watchdoga użyj [skryptu ratunkowego](#skrypt-ratunkowy) |
| Urządzenie wskazuje na przekaźnik, ale nigdy się z nim nie łączy (zachowało sesję z Red Sea) | Po 2 minutach zmuszane do ponownego połączenia: przełączane na Red Sea, potem znów na przekaźnik, najwyżej dwa razy |

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

> [!IMPORTANT]
> **Właściciele ReefATO+, potrzebuję Waszej pomocy.** Nie mam ReefATO+, więc tryb
> Poseidon nigdy na nim nie działał: nie wiadomo jeszcze, co wysyła, i nic z tego nie
> jest scalane. Ustaw najpierw swoje urządzenie na strategię *Szpieg*, a potem, aby
> dokończyć jego obsługę:
> - wyślij mi jego log szpiega (`/config/redsea/poseidon/logs/spy.jsonl`) w
>   [zgłoszeniu GitHub](https://github.com/Elwinmage/ha-reefbeat-component/issues),
>   po przeczytaniu: jest odszyfrowany i zawiera identyfikatory Twoich urządzeń;
> - i/lub otwórz naprawy zgłaszane przez Poseidona dla jego
>   [nieoczekiwanych wiadomości](#nieoczekiwane-wiadomości): każda wstępnie wypełnia zgłoszenie
>   GitHub.
>
> Nigdy nie wysyłaj pliku kluczy. Ostrzeżenie o pobieraniu kluczy dotyczy ReefATO+
> tak samo jak każdego urządzenia.

Rodziny scalane do tej pory, na podstawie sesji szpiegowskich:

| Rodzina | Scalane |
|---|---|
| ReefControl Power | stany, telemetria (w tym sonda temperatury); stany gniazd są wyliczane z ich harmonogramów, jak robi to aplikacja ReefBeat |
| ReefDose | stany, telemetria; `dosing-log` (koniec dawki) odczytuje ją ponownie ze względu na kolejkę dozowania, podobnie północ (00:01, czas Home Assistant), gdy kolejka nowego dnia zastępuje kolejkę kończącego się dnia |
| ReefMat | stany, telemetria, `rolling-log` (koniec przesuwu) |
| ReefLED | telemetria |
| ReefWave | stany (tryb: karmienie wyłącza ją i przywraca auto, ustawienia), telemetria (tryb, sygnał wifi); program zapisany w aplikacji (`schedule`, wysyłany bez przedziałów) odczytuje ją ponownie. Jej bieżąca fala wynika z programu i zegara: zmiany fali na początku przedziału nic nie wysyła (pokazuje ją tylko telemetria, w ciągu minuty) |
| ReefRun | stany, telemetria (stan, intensywność, temperatura pomp: pełny kubek, brak pompy...); koniec kalibracji i `notification` (pompa do ponownego podłączenia) odczytują ją ponownie |
| ReefControl | telemetria i zdarzenia `probe` (odczyty sond), stany (tryb, połączenie z ReefControl Power, tryb wycieku), tryb i stan portów (wyłączony port zużywa 0; zużycie włączonego portu przychodzi z odpytywaniem); zainstalowana lub skonfigurowana sonda albo port odczytuje go ponownie |

Dla pozostałych rodzin *Shadow* tylko porównuje, a *Poseidon* odczytuje urządzenie
ponownie za każdym razem, gdy wyśle stan. *Poseidon* odczytuje je też ponownie, gdy
stan zawiera coś, czego jego scalacz nie umie zapisać (nieznane ustawienie, harmonogram
ReefDose wysyłany bez przedziałów). Taki odczyt obejmuje źródła konfiguracji: to, co
zmienia aplikacja, to głównie ustawienia, których odpytywanie nigdy nie czyta ponownie.
Każde polecenie zapisu aplikacji zaakceptowane przez urządzenie także je odczytuje: nie
każde ustawienie jest wysyłane (offset sondy temperatury nie).

ReefControl Power bez gniazda sterowanego czujnikiem (z sondą temperatury lub bez),
ReefDose (jej kolejka dozowania jest odczytywana po każdej dawce i o północy) i
ReefWave (jej program jest odczytywany ponownie, gdy się zmienia) wysyłają wszystko, co
się zmienia: z *Poseidon* są odpytywane tylko co *Interwał odczytu bezpieczeństwa*.

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

- **Domyślna strategia**: strategia każdego urządzenia w trybie Poseidon, które nie
  ma własnej (zobacz [Strategie](#strategie)). Domyślnie *Szpieg*.
- **Interwał odpytywania strategii Poseidon**, w minutach (domyślnie 10).
- **Tryb debug**: każda ramka przechodząca przez przekaźnik jest zapisywana
  odszyfrowana w `/config/redsea/poseidon/logs/poseidon.jsonl` (rotacja przy 10 MB, 5
  plików). Dane są w tym pliku jawne.
- **Czas, po którym urządzenie jest ciche**, w minutach (domyślnie 10).
- **Interwał odczytu bezpieczeństwa**, w minutach (domyślnie 60): odpytywanie
  urządzenia, którego wysyłane wiadomości obejmują wszystko, co się zmienia, oraz
  częstotliwość odczytu `/cloud` urządzenia komunikującego się przez przekaźnik.
- **Zgłaszaj nieoczekiwane wiadomości** (domyślnie włączone): zobacz
  [Nieoczekiwane wiadomości](#nieoczekiwane-wiadomości).
- **Szukaj istniejących zgłoszeń na GitHubie** (domyślnie włączone): wysyłana jest
  tylko sygnatura nieoczekiwanej wiadomości.
- **Wstrzymuj przywracanie z chmury przy połączeniu** (domyślnie włączone): zobacz
  [Ochrona przy połączeniu](#ochrona-przy-połączeniu).
- **Klucz watchdoga**: 16 znaków, proponowany, dopóki żaden nie jest ustawiony.
  Przekaźnik odpowiada na zaszyfrowane tym kluczem zapytanie „czy żyjesz”:
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog)
  lub sam jego `poseidon_watchdog.py` na innej maszynie nadzoruje przekaźnik i
  przełącza urządzenia z powrotem do trybu normalnego, gdy ten przestaje działać.
  Skopiuj ten klucz do jego konfiguracji; zostaw pusty, aby nie odpowiadać żadnemu
  watchdogowi.

## Nieoczekiwane wiadomości

Każda wiadomość przechodząca przez przekaźnik jest porównywana z tym, co wiadomo o
rodzinie urządzenia: nieznany pakiet lub topic MQTT, polecenie chmury do nieznanego
endpointu, stan lub telemetria z polem nowym, brakującym lub innego typu. Pierwsze
wystąpienie trafia do `/config/redsea/poseidon/logs/anomalies.jsonl`, zanonimizowane
(bez identyfikatorów, nazw, adresów sieciowych i kluczy); nieznane polecenie czeka 5
sekund na odpowiedź urządzenia i to, co wyśle, i jest zapisywane razem z nimi.

Każda ma sygnaturę, taką samą dla wszystkich użytkowników. Zgłoszenia repozytorium są
przeszukiwane według niej, a naprawa mówi, co zrobić: zgłosić (wstępnie wypełnione
zgłoszenie GitHub, wysyłane tylko przez Ciebie), śledzić otwarte zgłoszenie,
zaktualizować do wersji, która to obsługuje, lub przeczytać zamknięte zgłoszenie. Nowe
pole telemetrii tworzy naprawę tylko wtedy, gdy wyszukiwanie nie znalazło zgłoszenia.

## Ochrona przy połączeniu

Przy każdym połączeniu urządzenia chmura Red Sea wysyła mu własną kopię jego ustawień.
Gdy ta kopia jest nieaktualna, urządzenie traci bieżące ustawienia: ReefWave straciła
w ten sposób cały harmonogram. Dlatego przez pierwsze 30 sekund każdego połączenia
przez przekaźnik znane przywracania z chmury (grupa i harmonogram ReefWave, głowica
karmienia ReefDose) są wstrzymywane.

Każde inne polecenie przechodzi i jest zapisywane w logach (`guard_passed` w pliku
szpiega): urządzenie, które restartuje się podczas korzystania z aplikacji (ReefControl
zawieszający się przy instalacji sondy), otrzymuje polecenia użytkownika.

## Zdarzenia

### `redsea_dose`

Wysyłane, gdy ReefDose w trybie Poseidon (dowolna strategia) kończy dawkę, zaplanowaną
lub ręczną, na podstawie swojego `dosing-log`. Dawka wysłana dwa razy (po ponownym
połączeniu) jest zgłaszana raz.

| Pole | Zawartość |
|---|---|
| `device_id` | urządzenie w Home Assistant |
| `name` | jego nazwa |
| `head` | numer głowicy |
| `supplement`, `brand` | tak, jak podaje je urządzenie |
| `dose_type` | `scheduled` lub `manual` |
| `volume` | dozowana objętość w mL |
| `started_at` | początek dawki, z odczytanej wcześniej kolejki dozowania (czas lokalny urządzenia); dla dawki spoza kolejki (tej o północy, ręcznej z aplikacji) szacowany na podstawie przepływu głowicy; `null`, dopóki mniej niż 3 dawki głowicy mają zmierzony czas trwania |
| `ended_at` | koniec dawki (czas lokalny urządzenia) |
| `duration_s` | `ended_at` − `started_at`, `null` bez początku |
| `start_estimated` | `true`, gdy `started_at` (i `duration_s`) są szacowane: objętość ÷ przepływ głowicy (jej ostatnie 20 dawek o zmierzonym czasie) |

Na początku dawki nic nie jest wysyłane: jej początek to czas podany przez kolejkę
dozowania. Dawki o północy nie ma w żadnej kolejce (kolejka kończącego się dnia jest
wtedy pusta, kolejka nowego dnia zaczyna się po niej): jej początek jest szacowany.

### `redsea_notification`

Wysyłane, gdy urządzenie w trybie Poseidon (dowolna strategia) wysyła alarm, ten, który
aplikacja ReefBeat pokazuje jako powiadomienie. Zawiera to, co podało urządzenie:

| Pole | Zawartość |
|---|---|
| `device_id` | urządzenie w Home Assistant |
| `name` | jego nazwa |
| `device_type` | jego rodzina: `reef-run`, `reef-control`, `reef-dosing`... |
| `type` | alarm, tak jak nazywa go urządzenie |
| `sub_type` | tak, jak podaje urządzenie (`sub-type`) |
| inne pola | czego dotyczy alarm: `pump` lub `pump_name` (ReefRun), `probe` (ReefControl, jej nazwa), `supplement` (ReefDose) |

Dotąd zaobserwowane:

| Rodzina | `type` |
|---|---|
| ReefRun | `full_cup_warning` (`pump`), `no_pump` (`pump_name`) |
| ReefControl | `sensor_danger_range`, `temperature_danger_range`, `aquarium_water_leak` (`probe`) |
| ReefDose | `stock_level_empty` (`supplement`) |

```yaml
automation:
  - alias: Skimmer cup full
    triggers:
      - trigger: event
        event_type: redsea_notification
        event_data:
          type: full_cup_warning
    actions:
      - action: notify.notify
        data:
          message: "{{ trigger.event.data.name }}: the skimmer cup is full"
```

### Historia dawek

Każda dawka jest też przechowywana, dla każdej głowicy, przez 30 dni (najwyżej 5000
dawek), także po restartach:

- każda głowica ReefDose otrzymuje sensor **Ostatnia dawka** (na urządzeniu głowicy),
  dostępny tylko wtedy, gdy dozownik jest w trybie Poseidon: jego stan to koniec
  ostatniej dawki, a atrybuty to objętość, typ, początek, czas trwania i suplement;
  recorder przechowuje je jak dla każdego sensora;
- akcja `redsea.get_doses` zwraca dawki, od najnowszych: `device_id` (dozownik, jedna z
  jego głowic lub jego wpis konfiguracji) oraz opcjonalnie `head`, `days`, `limit`;
- ha-reef-card pokazuje je w oknie konfiguracji głowicy (**Historia dawek**).

```yaml
automation:
  - alias: Log the doses
    triggers:
      - trigger: event
        event_type: redsea_dose
    actions:
      - action: logbook.log
        data:
          name: "{{ trigger.event.data.name }}"
          message: >-
            head {{ trigger.event.data.head }}
            ({{ trigger.event.data.supplement }}):
            {{ trigger.event.data.volume }} mL,
            {{ trigger.event.data.dose_type }},
            {{ trigger.event.data.started_at }} → {{ trigger.event.data.ended_at }}
```

## Wiadomości aplikacji ReefBeat

Sensory **Ostatni komunikat** i **Ostatni komunikat alertu** (oraz historia komunikatów)
pochodzą z odpowiedzi urządzeń na polecenia Home Assistant, które w każdym trybie
pozostają HTTP. Polecenia aplikacji ReefBeat (lub chmury) docierają do urządzenia przez
MQTT: w trybie Poseidon (dowolna strategia) odpowiedź urządzenia na każde polecenie
zapisu (`command-response`, ten sam `uuid`) zasila te same sensory, jak zrobiłaby to
odpowiedź HTTP:

- `message` (`settings updated successfully`, `head settings successfully saved`...)
  staje się ostatnim komunikatem;
- `alert` (`NoMoreDoseAlert`...), `"success": false` lub status błędu staje się
  ostatnim alertem.

Odczyty aplikacji (`GET`) nie niosą komunikatu: są pomijane. Atrybut `origin` obu
sensorów i każdego wpisu historii (akcja `redsea.get_messages`) mówi, skąd pochodzi:
`ha` (polecenie Home Assistant) lub `reefbeat` (polecenie aplikacji lub chmury).
ha-reef-card pokazuje go po dacie.

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
