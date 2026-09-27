[← Powrót do strony głównej](README.pl.md)

# Konserwacja

Poza sterowaniem sprzętem integracja śledzi **cykliczne zadania konserwacyjne**
twojego wyposażenia: czyszczenie venturi odpieniacza, wymianę wężyków pompy
dozującej, wymianę węgla aktywnego w ReefMat… To Home Assistant o tym pamięta,
a nie ty.

Zadania są przypisane do właściwego urządzenia, a jeśli to bardziej precyzyjne —
do **podurządzenia**: głowicy ReefDose, pompy ReefRun. ReefRun udostępnia
zadania pompy powrotnej na pompie 1, a zadania odpieniacza na pompie 2, nigdy
odwrotnie: lista wynika z typu pompy zgłaszanego przez urządzenie.

## Trzy encje jednego zadania

Każde zadanie tworzy trzy encje, wszystkie w kategoriach *Konfiguracja* i
*Diagnostyka*, aby nie zaśmiecać głównego pulpitu:

| Encja | Rola |
| ----- | ---- |
| `button.<urządzenie>_<zadanie>` | **Zadanie wykonane.** Naciśnięcie zapisuje bieżącą datę jako ostatnie wykonanie i restartuje odliczanie. |
| `number.<urządzenie>_<zadanie>_interval_<jednostka>` | **Interwał.** Jak często zadanie ma być powtarzane — w dniach, tygodniach lub miesiącach, zależnie od zadania. |
| `switch.<urządzenie>_<zadanie>_notify` | **Powiadomienia.** Wycisza alert o przekroczeniu terminu tego jednego zadania, nie zmieniając jego terminu. |

To przycisk przechowuje stan. Wszystko, co z niego wynika, jest udostępniane
jako atrybuty, więc jedna encja wystarczy do zbudowania pulpitu lub automatyzacji:

| Atrybut | Znaczenie |
| ------- | --------- |
| `last_reset` | Data ISO-8601 ostatniego naciśnięcia lub `null`, jeśli nigdy nie wykonano |
| `interval_days` | Bieżący interwał, zawsze znormalizowany w dniach |
| `days_left` | Pozostałe dni, ujemne po przekroczeniu terminu |
| `overdue` | `true`, gdy `days_left` jest ujemne |
| `reef_role` | `maint_<klucz_zadania>`, stabilny znacznik służący do wykrywania zadań |

> [!TIP]
> To `reef_role` czyni całość rozszerzalną: karta i blueprint alertów wykrywają
> zadania, szukając tego atrybutu. Zadanie dodane w przyszłej wersji integracji
> pojawi się w obu bez żadnej aktualizacji po ich stronie.

## Interwały

Domyślne interwały odpowiadają zaleceniom Red Sea, przyjmując medianę
publikowanego zakresu. Każde zadanie definiuje też minimum i maksimum,
wymuszane przez encję `number`: możesz dostosować interwał do obciążenia swojego
zbiornika, ale nie ustawisz absurdalnej wartości.

Interwały są pokazywane w jednostce sensownej dla zadania (tygodnie dla venturi,
miesiące dla wirnika), a wewnętrznie przechowywane w dniach, więc zmiana
jednostki nigdy nie traci precyzji.

## Trwałość danych

Daty i interwały zapisuje Home Assistant w
`.storage/redsea_maintenance_<entry_id>`, po jednym pliku na wpis konfiguracji.
Przetrwają restarty, przeładowania integracji i restarty urządzeń i **nigdy nie
są wysyłane do chmury Red Sea**. Usunięcie wpisu konfiguracji usuwa też plik.

## Widok konserwacji w ha-reef-card

Karta towarzysząca [ha-reef-card](https://github.com/Elwinmage/ha-reef-card)
zbiera wszystkie zadania instalacji w osobnym widoku, tak jakby konserwacja była
oddzielnym urządzeniem: pasek postępu na zadanie, kolorowany według pozostałego
czasu, sortowalny według sprzętu lub terminu, z przyciskiem oznaczenia zadania
jako wykonanego, dzwonkiem do wyciszenia i suwakiem do zmiany interwału.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/maintenance_task.png" alt="Zadania konserwacyjne w ha-reef-card">
</p>

## Powiadomienia: blueprint alertów

Integracja celowo nie powiadamia sama: kogo, kiedy i jak zawiadomić, to twoja
decyzja. Tym zajmuje się blueprint **ReefBeat watch** dołączony do repozytorium,
który obejmuje także nietypowe tryby, zaległe kalibracje, słabe baterie i
nieosiągalne urządzenia.

### Instalacja

Kliknij poniższy przycisk i potwierdź import w Home Assistant:

[![Otwórz swoją instancję Home Assistant i wyświetl okno importu blueprintu.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-reefbeat-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fredsea_alerts.en.yaml)

Dostępna jest też wersja francuska,
[`redsea_alerts.fr.yaml`](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/blueprints/automation/redsea_alerts.fr.yaml).
Alternatywnie skopiuj plik do
`config/blueprints/automation/redsea_alerts/` i przeładuj automatyzacje.

Następnie utwórz automatyzację na podstawie blueprintu:
*Ustawienia → Automatyzacje i sceny → Utwórz automatyzację → Użyj blueprintu →
ReefBeat watch (redsea)*.

### Konfiguracja

Obowiązkowe jest tylko pierwsze pole:

| Sekcja | Rola |
| ------ | ---- |
| **Cele powiadomień** | Telefony do powiadomienia, wybrane w selektorze urządzeń. Usługa `notify.mobile_app_*` jest ustalana automatycznie. Można podać kanał powiadomień Android (domyślnie `ReefBeat`). |
| **Zaległa konserwacja** | Ostrzega, gdy zadanie przekroczy termin. Opcja *Respektuj przełączniki powiadomień poszczególnych zadań* (domyślnie włączona) sprawia, że automatyzacja słucha encji `switch.*_notify`: wyciszenie zadania w karcie wycisza też automatyzację. |
| **Nietypowy tryb** | Ostrzega, gdy urządzenie opuści oczekiwany tryb. `off_grace_minutes` (domyślnie 5) zapobiega fałszywym alertom podczas karmienia lub krótkiej interwencji ręcznej. |
| **Zaległa kalibracja** | Głowice ReefDose i kalibracje odpieniaczy ReefRun. |
| **Opóźnienie kalibracji sond (RSRUN)** | Sondy pełnego kubka i nadmiernego odpieniania w odpieniaczach ReefRun. |
| **Komunikat alarmowy urządzenia** | Przekazuje komunikaty wysyłane przez same urządzenia. |
| **Niski poziom baterii** / **Urządzenie nieosiągalne** | Bez niespodzianek. |

Każdą sekcję można wyłączyć niezależnie i każda ma własną **listę wykluczeń**:
testowane urządzenie nie zasypie cię alertami, podczas gdy pozostałe są nadal
nadzorowane. Automatyzacja działa w cyklu 5-minutowym i uwzględnia urządzenia
dodane lub usunięte z integracji w kolejnym cyklu, bez żadnych zmian w
konfiguracji.

> [!NOTE]
> Blueprint nadzoruje **wszystkie** urządzenia integracji i ich podurządzenia.
> Dodając nowe urządzenie ReefBeat, nie trzeba niczego deklarować.

---

[← Powrót do strony głównej](README.pl.md)
