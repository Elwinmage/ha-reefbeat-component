[← Powrót do strony głównej](README.pl.md)

# ReefWave:
> [!IMPORTANT]
> Urządzenia ReefWave różnią się od pozostałych urządzeń ReefBeat. Są jedynymi urządzeniami podporządkowanymi chmurze ReefBeat.<br/>
> Po uruchomieniu aplikacji ReefBeat odpytywany jest stan wszystkich urządzeń, a dane aplikacji są pobierane ze stanu urządzenia.<br/>
> W przypadku ReefWave jest odwrotnie: nie ma lokalnego punktu sterowania (jak widać w aplikacji ReefBeat, nie można dodać ReefWave do akwarium odłączonego od sieci).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Fale są przechowywane w bibliotece użytkownika w chmurze. Gdy zmieniasz wartość fali, zmienia się ona w bibliotece w chmurze i jest stosowana w nowym harmonogramie.<br/>
> Czyli nie ma trybu lokalnego? To nie takie proste. Istnieje ukryte lokalne API do sterowania ReefWave, ale aplikacja ReefBeat nie wykryje zmian. W efekcie urządzenie i Home Assistant z jednej strony oraz aplikacja ReefBeat z drugiej przestaną być zsynchronizowane. Urządzenie i Home Assistant zawsze będą zsynchronizowane.<br/>
> Teraz już wiesz — wybieraj!

> [!NOTE]
> Fale ReefWave mają wiele powiązanych parametrów, a zakres niektórych zależy od innych. Nie byłem w stanie przetestować wszystkich możliwych kombinacji. Jeśli znajdziesz błąd, możesz zgłosić go [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Tryby ReefWave
Jak wyjaśniono powyżej, urządzenia ReefWave są jedynymi, które mogą utracić synchronizację z aplikacją ReefBeat, jeśli używasz lokalnego API.
Dostępne są trzy tryby: Cloud, Lokalny i Hybrydowy.
Możesz zmienić tryb, ustawiając przełączniki „Połącz z chmurą" i „Używaj API Cloud" zgodnie z opisem w poniższej tabeli.

<table>
<tr>
<td>Nazwa trybu</td>
<td>Przełącznik Połącz z chmurą</td>
<td>Przełącznik Używaj API Cloud</td>
<td>Zachowanie</td>
<td>ReefBeat i HA są zsynchronizowane</td>
</tr>
<tr>
<td>Cloud (domyślnie)</td>
<td>✅</td>
<td>✅</td>
<td>Dane są pobierane przez lokalne API. <br />Polecenia włączenia/wyłączenia są również wysyłane przez lokalne API. <br />Polecenia fal są wysyłane przez API chmury.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Dane są pobierane przez lokalne API. <br />Polecenia są wysyłane przez lokalne API. <br />Urządzenie jest widoczne w aplikacji ReefBeat jako „wyłączone".</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>Dane są pobierane przez lokalne API. <br />Polecenia są wysyłane przez lokalne API.<br />Aplikacja ReefBeat nie pokazuje właściwych wartości fal, jeśli zmieniono je w HA.<br/>Home Assistant zawsze pokazuje właściwe wartości.<br/>Wartości można zmieniać zarówno w aplikacji ReefBeat, jak i w Home Assistant.</td>
<td>❌</td>
</tr>
</table>

W trybach Chmura i Hybrydowym musisz połączyć swoje konto w chmurze ReefBeat.
Najpierw utwórz urządzenie [„Cloud API"](../../README.md#add-cloud-api) ze swoimi danymi logowania — i gotowe!
Czujnik „Połączono z kontem" pokaże nazwę Twojego konta ReefBeat po nawiązaniu połączenia.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Zmiana bieżących wartości
Aby wczytać aktualne wartości fali do pól podglądu, użyj przycisku „Podgląd z bieżącego".
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
Aby zmienić aktualne wartości fali, ustaw wartości podglądu i użyj przycisku „Zapisz podgląd".

Działa to tak samo jak w aplikacji ReefBeat. Wszystkie fale o tym samym ID w bieżącym harmonogramie zostaną zaktualizowane.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

## Grupy
Tak jak w aplikacji ReefBeat, wszystkie zgrupowane ReefWave akwarium tworzą
jedną grupę (tylko z kontem w chmurze).

| Encja | Rola |
| ----- | ---- |
| `switch` Zgrupowana z akwarium | Grupuje pompę z pozostałymi ReefWave jej akwarium albo ją rozgrupowuje; dołączająca pompa trafia na koniec. Niedostępne bez konta w chmurze |
| `sensor` Połączone ReefWave | Liczba pomp w grupie, ich lista w atrybucie `waves` (`hwid`, `name`, `model`, `entry_id`, `available`) |

Program jest zapisywany na każdej pompie grupy: te same przedziały, każda
pompa z własnymi intensywnościami. Tak jak w aplikacji, zapis jest
odrzucany, gdy pompa grupy nie jest załadowana albo nie odpowiada: nic nie
jest wysyłane, więc grupa pozostaje zsynchronizowana. Po zmianie grupy
odświeżane są wszystkie załadowane ReefWave.

## Program dnia
`sensor` Typ fali niesie cały program dnia w atrybucie
`schedule`: listę jego przedziałów, z których każdy zaczyna się w `st`
(minuta dnia) i trwa do następnego, z `wave_uid`, `name`, `type`,
`direction`, `frt`, `rrt`, `fti`, `rti`, `sn`, `pd` i `sync`. ha-reef-card
rysuje z niego dzień.

## Usługi
Te usługi obsługują bibliotekę fal i program dnia, tak jak robi to aplikacja
ReefBeat; używają ich edytory ha-reef-card. `device_id` to wpis
konfiguracji ReefWave.

| Usługa | Rola |
| ------ | ---- |
| `redsea.wave_library` | Fale akwarium pompy, z intensywnościami tej pompy, pompami używającymi każdej fali i grupą pompy. Bez konta w chmurze: fale jej własnego programu |
| `redsea.wave_library_save` | Tworzy falę albo aktualizuje istniejącą (`uid`). Kształt jest wspólny, intensywności należą do pompy; programy używające zaktualizowanej fali są zapisywane ponownie. Fale Red Sea i zajęte nazwy są odrzucane |
| `redsea.wave_library_delete` | Usuwa jedną z Twoich fal; odrzucane dla fali Red Sea albo fali używanej przez program |
| `redsea.wave_program_save` | Zapisuje program dnia (`slots`: `st`, `wave_uid`, `direction`; pierwszy zaczyna się w 0) na każdej pompie grupy; bez konta w chmurze na samej pompie |
| `redsea.wave_preview` | Uruchamia falę na pompie na 1 do 10 min, potem powrót do jej programu |
| `redsea.wave_preview_stop` | Zatrzymuje podgląd |
| `redsea.wave_pump_set` | Kierunek i intensywności tej pompy w bieżącej fali (także fali Red Sea); pozostałe pompy grupy pozostają bez zmian |
| `redsea.wave_group_set` | Grupuje albo rozgrupowuje pompę (`grouped`), tak jak przełącznik |
| `redsea.wave_group_order` | Kolejność pomp w grupie (`hwids`, każda pompa wymieniona raz) |

Biblioteka wymaga konta w chmurze ReefBeat: bez niego `wave_library_save` i
`wave_library_delete` są odrzucane. Wszystkie odmowy to przetłumaczone błędy
Home Assistant.

## Ikony
Piktogramy typów fal z aplikacji są dostępne jako `redsea:wave-uniform`,
`redsea:wave-random`, `redsea:wave-regular`, `redsea:wave-step`,
`redsea:wave-surface` i `redsea:wave-none`.

### Zadania konserwacyjne
| Zadanie | Domyślnie | Zakres |
| ------- | --------- | ------ |
| Czyszczenie koszy wirnika | 2 miesiące | 1 – 3 miesiące |

Zobacz sekcję [Konserwacja](maintenance.pl.md#konserwacja).

---

[← Powrót do strony głównej](README.pl.md)
