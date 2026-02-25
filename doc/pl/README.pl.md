[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/commits/main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

<!-- [![Clones GitHub](https://img.shields.io/badge/dynamic/json?color=success&label=uniques-clones&query=uniques&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge) -->

# Opis
***Lokalne zarządzanie urządzeniami HomeAssistant RedSea Reefbeat (bez chmury): ReefATO+, ReefDose, ReefLed, ReefMat, ReefRun i ReefWave***

> [!TIP]
> ***Aby edytować zaawansowane harmonogramy dla ReefDose, ReefLed, ReefRun i ReefWave, musisz użyć [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) (w trakcie rozwoju)***

> [!TIP]
> Lista przyszłych implementacji jest dostępna [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> Lista błędów jest dostępna [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***Jeśli potrzebujesz innych czujników lub elementów wykonawczych, skontaktuj się ze mną [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Jeśli twoje urządzenia nie są w tej samej podsieci co Home Assistant, przeczytaj [to](README.pl.md#moje-urządzenie-nie-zostało-wykryte).

> [!CAUTION]
> ⚠️ To nie jest oficjalne repozytorium RedSea. Używaj na własne ryzyko.⚠️

# Zgodność

✅ Przetestowano ☑️ Powinno działać (Jeśli masz takie urządzenie, czy możesz potwierdzić działanie [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))❌ Jeszcze nie obsługiwane
<table>
<th>
<td colspan="2"><b>Model</b></td>
<td colspan="2"><b>Status</b></td>
<td><b>Problemy</b> <br/>📆(Planowane) <br/> 🐛(Błędy)</td>
</th>
<tr>
<td><a href="#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td><a href="#reefcontrol">ReefControl</a></td>
<td colspan="2">RSSENSE<br />Jeśli masz takie urządzenie, skontaktuj się ze mną <a href="https://github.com/Elwinmage/ha-reefbeat-component/discussions/8">tutaj</a>, abym mógł dodać jego obsługę.</td><td>❌</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROL.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE2.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"><a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
<td rowspan="6">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,RSLED90,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td>RSLED90</td><td>✅</td></tr>
<tr><td>RSLED160</td><td>✅ </td></tr>
<tr>
<td rowspan="3">G2</td>
<td>RSLED60</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g2.png"/></td>
</tr>
<tr><td>RSLED115</td><td>✅ </td></tr>
<tr><td>RSLED170</td><td>☑️</td></tr>
<tr>
<td rowspan="3"><a href="#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSMAT.png"/></td>
<td rowspan="3">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td colspan="2">RSMAT500</td><td>✅</td></tr>
<tr><td colspan="2">RSMAT1200</td><td>✅ </td></tr>
<tr>
<td><a href="#reefrun">ReefRun i DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td><td>☑️</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td colspan="2">RSWAVE45</td><td>✅</td></tr>
</table>

(*) Użytkownicy ReefWave, przeczytaj [to](README.pl.md#reefwave)

# Spis treści
- [Instalacja przez HACS](README.pl.md#instalacja-przez-hacs)
- [Wspólne funkcje](README.pl.md#wspólne-funkcje)
- [ReefATO+](README.pl.md#reefato)
- [ReefControl](README.pl.md#reefcontrol)
- [ReefDose](README.pl.md#reefdose)
- [ReefLED](README.pl.md#reefled)
- [Wirtualna dioda LED](README.pl.md#wirtualna-dioda-led)
- [ReefMat](README.pl.md#reefmat)
- [ReefRun](README.pl.md#reefrun)
- [ReefWave](README.pl.md#reefwave)
- [Cloud API](README.pl.md#cloud-api)
- [FAQ](README.pl.md#faq)

# Instalacja przez HACS

## Bezpośrednia instalacja

Kliknij tutaj, aby przejść bezpośrednio do repozytorium w HACS i kliknij „Pobierz": [![Otwórz swoją instancję Home Assistant i otwórz repozytorium w sklepie społeczności Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Aby skorzystać z karty towarzyszącej ha-reef-card oferującej zaawansowane i ergonomiczne funkcje, kliknij tutaj, aby przejść bezpośrednio do repozytorium w HACS i kliknij „Pobierz": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Wyszukaj w HACS
Lub wyszukaj „redsea" lub „reefbeat" w HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Obraz">
</p>

# Wspólne funkcje

## Dodawanie urządzenia
Przy dodawaniu nowego urządzenia masz cztery opcje:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Obraz">
</p>

### Dodawanie Cloud API
***Wymagane, aby ReefWave był zsynchronizowany z mobilną aplikacją ReefBeat*** (Przeczytaj [to](README.pl.md#reefwave)). <br />
***Wymagane, aby otrzymywać powiadomienia o nowych wersjach oprogramowania układowego*** (Przeczytaj [to](README.pl.md#aktualizacja-oprogramowania-układowego)).
- Informacje o użytkowniku
- Akwaria
- Biblioteka fal
- Biblioteka diod LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Obraz">
</p>

### Automatyczne wykrywanie w sieci prywatnej
Jeśli nie jesteś w tej samej sieci, przeczytaj [to](README.pl.md#moje-urządzenie-nie-zostało-wykryte) i użyj trybu [„Ręcznego"](README.pl.md#tryb-ręczny).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Obraz">
</p>

### Tryb ręczny
Możesz wprowadzić adres IP lub adres sieciowy urządzenia do automatycznego wykrywania.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Obraz">
</p>

### Ustawianie interwału skanowania urządzenia

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Obraz">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Obraz">
</p>

## Aktualizacja na żywo

> [!NOTE]
> Można wybrać, czy włączyć tryb Live_update_config. W tym trybie (stary domyślny) dane konfiguracyjne są pobierane ciągle wraz z normalnymi danymi. W przypadku RSDOSE lub RSLED te duże żądania HTTP mogą zajmować dużo czasu (7–9 sekund). Czasami urządzenie nie odpowiada na żądanie, dlatego zaimplementowano funkcję ponownych prób. Gdy Live_update_config jest wyłączony, dane konfiguracyjne są pobierane tylko przy uruchomieniu i na żądanie za pomocą przycisku „Pobierz konfigurację". Ten nowy tryb jest domyślnie aktywny. Można go zmienić w konfiguracji urządzenia. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Obraz">
</p>

## Aktualizacja oprogramowania układowego
Możesz otrzymywać powiadomienia i aktualizować urządzenie, gdy dostępna jest nowa wersja oprogramowania układowego. Musisz mieć aktywny komponent [„Cloud API"](README.pl.md#dodawanie-cloud-api) ze swoimi danymi logowania, a przełącznik „Użyj Cloud API" musi być włączony.
> [!TIP]
> „Cloud API" jest potrzebne tylko do pobrania numeru wersji nowej wersji i porównania go z zainstalowaną wersją. Do aktualizacji oprogramowania układowego Cloud API nie jest absolutnie konieczne.
> Jeśli nie używasz „Cloud API" (opcja wyłączona lub brak komponentu Cloud API), nie będziesz powiadamiany o nowych wersjach, ale nadal możesz użyć ukrytego przycisku „Wymuś aktualizację oprogramowania układowego". Jeśli dostępna jest nowa wersja, zostanie zainstalowana.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Obraz">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Obraz">
</p>

# ReefATO:
- Włącz/wyłącz automatyczne napełnianie
- Ręczne napełnianie
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Obraz">
</p>

# ReefControl:
Jeszcze nie obsługiwane. Jeśli masz takie urządzenie, skontaktuj się ze mną [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8), abym mógł dodać jego obsługę.

# ReefDose:
- Modyfikacja dziennej dawki
- Ręczne dozowanie
- Dodawanie i usuwanie suplementów
- Modyfikacja i kontrola objętości pojemnika. Ustawienie objętości pojemnika jest automatycznie włączane lub wyłączane w zależności od wybranej objętości.
- Włączanie/wyłączanie harmonogramu na pompę
- Konfiguracja alertów stanu zapasów
- Opóźnienie dozowania między suplementami
- Napełnianie przewodów (Przeczytaj [to](README.pl.md#kalibracja-i-napełnianie-przewodów))
- Kalibracja (Przeczytaj [to](README.pl.md#kalibracja-i-napełnianie-przewodów))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Obraz">
</p>

### Główne
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Obraz">
</p>

### Głowice
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Obraz">
</p>

#### Kalibracja i napełnianie przewodów

> [!CAUTION]
> Musisz dokładnie przestrzegać następującej kolejności (Korzystanie z [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) jest bezpieczniejsze).<br /><br />
> <ins>Kalibracja</ins>:
>  1. Ustaw cylinder miarowy i naciśnij „Start Calibration"
>  2. Podaj zmierzoną wartość w polu „Dose of Calibration"
>  3. Naciśnij „Set Calibration Value"
>  4. Opróżnij cylinder miarowy i naciśnij „Test new Calibration". Jeśli uzyskana wartość różni się od 4 mL, wróć do kroku 1.
>  5. Naciśnij „Stop and Save Graduation"
>
> <ins>Napełnianie przewodów</ins>:
>  1. (a) Naciśnij „Start Priming"
>  2. (b) Gdy ciecz zacznie płynąć, naciśnij „Stop Priming"
>  3. (1) Ustaw cylinder miarowy i naciśnij „Start Calibration"
>  4. (2) Podaj zmierzoną wartość w polu „Dose of Calibration"
>  5. (3) Naciśnij „Set Calibration Value"
>  6. (4) Opróżnij cylinder miarowy i naciśnij „Test new Calibration". Jeśli uzyskana wartość różni się od 4 mL, wróć do kroku 1.
>  7. (5) Naciśnij „Stop and Save Graduation"
>
> ⚠️ Po napełnianiu przewodów konieczna jest kalibracja (kroki 1 do 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Obraz">
</p>

# ReefLED:
- Pobieranie i ustawianie wartości białego, niebieskiego i księżyca (tylko dla G1: RSLED50, RSLED90, RSLED160)
- Pobieranie i ustawianie temperatury barwowej, intensywności i księżyca (wszystkie diody LED)
- Zarządzanie aklimatyzacją. Ustawienia aklimatyzacji są automatycznie włączane lub wyłączane zgodnie z przełącznikiem aklimatyzacji.
- Zarządzanie fazami księżyca. Ustawienia faz księżyca są automatycznie włączane lub wyłączane zgodnie ze zmianą fazy księżyca.
- Ustawianie ręcznego trybu kolorów z czasem lub bez.
- Wyświetlanie parametrów wentylatora i temperatury.
- Wyświetlanie nazwy i wartości programów (z obsługą chmury). Tylko dla diod G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Obraz">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Obraz">
</p>

***

Obsługa temperatury barwowej dla diod G1 uwzględnia specyfikę każdego z trzech modeli.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Obraz">
</p>

***
## WAŻNE dla lamp G1 i G2

### LAMPY G2

#### Intensywność
Ponieważ ten typ diody LED zapewnia stałą intensywność w całym zakresie kolorów, twoje diody LED nie wykorzystują pełnej pojemności w środku widma. Przy 8 000 K kanał biały jest na 100%, a kanał niebieski na 0% (odwrotnie przy 23 000 K). Przy 14 000 K i intensywności 100% dla lamp G2, moc kanałów białego i niebieskiego wynosi około 85%.
Oto krzywa strat dla G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Obraz">
</p>

#### Temperatura barwowa
Interfejs lamp G2 nie obsługuje pełnego zakresu temperatur. Od 8 000 K do 10 000 K wartości są zwiększane co 200 K, a od 10 000 K do 23 000 K co 500 K. To zachowanie jest uwzględnione: jeśli wybierzesz nieprawidłową wartość (np. 8 300 K), zostanie automatycznie wybrana prawidłowa wartość (8 200 K w naszym przykładzie). Dlatego czasami można zauważyć małą korektę suwaka przy wyborze koloru na lampie G2: kursor ustawia się na dozwolonej wartości.

### LAMPY G1

Diody G1 używają sterowania kanałami białym i niebieskim, co pozwala na pełną moc w całym zakresie, ale bez kompensacji nie zapewnia stałej intensywności.
Dlatego zaimplementowano kompensację intensywności.
Ta kompensacja gwarantuje tę samą wartość [PAR](https://pl.wikipedia.org/wiki/Promieniowanie_fotosyntetycznie_czynne) (intensywność światła) niezależnie od wybranej temperatury barwowej (w zakresie 12 000 do 23 000 K).
> [!NOTE]
> Ponieważ RedSea nie publikuje wartości PAR poniżej 12 000 K, kompensacja działa tylko w zakresie 12 000 do 23 000 K. Jeśli masz diodę G1 i miernik PAR, możesz [skontaktować się ze mną](https://github.com/Elwinmage/ha-reefbeat-component/discussions/), aby dodać kompensację dla pełnego zakresu (9 000 do 23 000 K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Obraz">
</p>

Innymi słowy, bez kompensacji intensywność x% przy 9 000 K nie zapewnia tej samej wartości PAR co przy 23 000 K lub 15 000 K.

Oto krzywe mocy:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Obraz">
</p>

Jeśli chcesz w pełni wykorzystać moc swojej diody LED, wyłącz kompensację intensywności (domyślnie).

Jeśli włączysz kompensację intensywności, intensywność światła będzie stała dla wszystkich wartości temperatury, ale w środku zakresu nie będziesz używać pełnej pojemności diod LED (jak w modelach G2).

Pamiętaj też, że przy włączonym trybie kompensacji współczynnik intensywności może przekroczyć 100% dla G1, jeśli ręcznie dotkniesz kanałów biały/niebieski. Możesz w ten sposób wykorzystać pełną moc swoich diod LED!

***

# Wirtualna dioda LED
- Grupuj i zarządzaj diodami LED za pomocą wirtualnego urządzenia (utwórz wirtualne urządzenie z panelu integracji, a następnie użyj przycisku konfiguracji, aby połączyć diody LED).
- Możesz używać tylko Kelvina i intensywności do sterowania diodami LED, jeśli masz G2 lub mieszankę G1 i G2.
- Możesz używać zarówno Kelvin/Intensywność, jak i Biały i Niebieski, jeśli masz tylko G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Obraz">
</p>

# ReefMat:
- Przełącznik automatycznego posuwu (włącz/wyłącz)
- Zaplanowany posuw
- Niestandardowa wartość posuwu: pozwala wybrać wartość posuwu rolki
- Ręczny posuw
- Zmiana rolki.
>[!TIP]
> W przypadku nowej pełnej rolki ustaw „średnicę rolki" na minimum (4,0 cm). Rozmiar zostanie dostosowany do wersji RSMAT. W przypadku już używanej rolki wprowadź wartość w cm.
- Dwa ukryte parametry: model i pozycja, jeśli musisz ponownie skonfigurować RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Obraz">
</p>

# ReefRun:
- Ustawianie prędkości pompy
- Zarządzanie nadmiernym spienieniem
- Zarządzanie wykrywaniem pełnego kubka zbiorczego
- Możliwość zmiany modelu skimmera

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Obraz">
</p>

### Główne
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Obraz">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Obraz">
</p>

### Pompy
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Obraz">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Obraz">
</p>

# ReefWave:
> [!IMPORTANT]
> Urządzenia ReefWave różnią się od innych urządzeń ReefBeat. Są jedynymi urządzeniami zależnymi od chmury ReefBeat.<br/>
> Po uruchomieniu mobilnej aplikacji ReefBeat, stan wszystkich urządzeń jest odpytywany, a dane aplikacji ReefBeat są pobierane ze stanu urządzenia.<br/>
> W przypadku ReefWave jest odwrotnie: nie ma lokalnego punktu sterowania (jak widać w aplikacji ReefBeat, nie można dodać ReefWave do odłączonego akwarium).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Obraz"></center><br />
> Fale są przechowywane w bibliotece użytkownika chmury. Po zmianie wartości fali jest ona zmieniana w bibliotece chmury i stosowana do nowego harmonogramu.<br/>
> Czy nie ma więc trybu lokalnego? Nie tak prosto. Istnieje ukryte lokalne API do sterowania ReefWave, ale aplikacja ReefBeat nie wykryje zmian. W związku z tym urządzenie i HomeAssistant z jednej strony oraz mobilna aplikacja ReefBeat z drugiej strony będą niezynchronizowane. Urządzenie i HomeAssistant zawsze będą zsynchronizowane.<br/>
> Teraz, gdy już wiesz, dokonaj wyboru!

> [!NOTE]
> Fale ReefWave mają wiele powiązanych parametrów, a zakres niektórych parametrów zależy od innych parametrów. Nie mogłem przetestować wszystkich możliwych kombinacji. Jeśli znajdziesz błąd, możesz utworzyć zgłoszenie [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Tryby ReefWave
Jak wyjaśniono wcześniej, urządzenia ReefWave są jedynymi urządzeniami, które mogą być niezynchronizowane z aplikacją ReefBeat podczas korzystania z lokalnego API.
Dostępne są trzy tryby: Cloud, Lokalny i Hybrydowy.
Możesz zmienić ustawienia trybu „Połącz z chmurą" i „Użyj Cloud API" zgodnie z opisem w poniższej tabeli.

<table>
<tr>
<td>Nazwa trybu</td>
<td>Przełącznik Połącz z chmurą</td>
<td>Przełącznik Użyj Cloud API</td>
<td>Zachowanie</td>
<td>ReefBeat i HA są zsynchronizowane</td>
</tr>
<tr>
<td>Cloud (domyślny)</td>
<td>✅</td>
<td>✅</td>
<td>Dane są pobierane przez lokalne API. <br />Polecenia włączania/wyłączania są również wysyłane przez lokalne API. <br />Polecenia są wysyłane przez Cloud API.</td>
<td>✅</td>
</tr>
<tr>
<td>Lokalny</td>
<td>❌</td>
<td>❌</td>
<td>Dane są pobierane przez lokalne API. <br />Polecenia są wysyłane przez lokalne API. <br />Urządzenie jest wyświetlane jako „wyłączone" w aplikacji ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrydowy</td>
<td>✅</td>
<td>❌</td>
<td>Dane są pobierane przez lokalne API. <br />Polecenia są wysyłane przez lokalne API.<br />Mobilna aplikacja ReefBeat nie wyświetla prawidłowych wartości fal, jeśli zostały zmienione przez HA.<br/>Home Assistant zawsze wyświetla prawidłowe wartości.<br/>Możesz zmieniać wartości z aplikacji ReefBeat i Home Assistant.</td>
<td>❌</td>
</tr>
</table>

W trybach Cloud i Hybrydowym musisz połączyć swoje konto ReefBeat Cloud.
Najpierw utwórz [„Cloud API"](README.pl.md#dodawanie-cloud-api) ze swoimi danymi logowania i to wszystko!
Czujnik „Połączono z kontem" zostanie zaktualizowany o nazwę twojego konta ReefBeat po nawiązaniu połączenia.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Obraz">
</p>

## Modyfikacja bieżących wartości
Aby załadować bieżące wartości fal do pól podglądu, użyj przycisku „Ustaw podgląd z bieżącej fali".
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Obraz">
</p>
Aby zmodyfikować bieżące wartości fal, ustaw wartości podglądu i użyj przycisku „Zapisz podgląd".

Działanie jest identyczne jak w mobilnej aplikacji ReefBeat. Wszystkie fale z tym samym identyfikatorem w bieżącym harmonogramie zostaną zaktualizowane.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Obraz">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Obraz">
</p>

# Cloud API
Cloud API umożliwia:
- Uruchamianie lub zatrzymywanie skrótów: awaryjne, konserwacja i karmienie,
- Pobieranie informacji o użytkowniku,
- Pobieranie biblioteki fal,
- Pobieranie biblioteki suplementów,
- Pobieranie biblioteki programów LED,
- Otrzymywanie powiadomień o [nowych wersjach oprogramowania układowego](README.pl.md#aktualizacja-oprogramowania-układowego),
- Wysyłanie poleceń do ReefWave po wybraniu trybu „[Cloud lub Hybrydowy](README.pl.md#reefwave)".

Skróty, parametry fal i diod LED są posortowane według akwarium.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Obraz">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Obraz">
</p>

>[!TIP]
> Możliwe jest wyłączenie pobierania listy suplementów w interfejsie konfiguracji urządzenia Cloud API.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Obraz">
***
# FAQ

## Moje urządzenie nie zostało wykryte
- Spróbuj ponownie uruchomić automatyczne wykrywanie za pomocą przycisku „Dodaj wpis". Czasami urządzenia nie odpowiadają, ponieważ są zajęte.
- Jeśli twoje urządzenia RedSea nie są w tej samej podsieci co Home Assistant, automatyczne wykrywanie najpierw się nie powiedzie i zaproponuje wprowadzenie adresu IP urządzenia lub adresu podsieci, w której znajdują się urządzenia. Do wykrywania podsieci użyj formatu IP/MASKA, jak w tym przykładzie: 192.168.14.0/255.255.255.0.
- Możesz również użyć [trybu ręcznego](README.pl.md#tryb-ręczny).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Obraz">
</p>

## Niektóre dane są poprawnie aktualizowane, inne nie.
Dane są podzielone na trzy części: dane, konfiguracja i informacje o urządzeniu.
- Dane są regularnie aktualizowane.
- Dane konfiguracyjne są aktualizowane tylko przy uruchomieniu i po naciśnięciu przycisku „fetch-config".
- Informacje o urządzeniu są aktualizowane tylko przy uruchomieniu.

Aby zapewnić regularne aktualizacje danych konfiguracyjnych, włącz [aktualizację konfiguracji na żywo](README.pl.md#aktualizacja-na-żywo).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
