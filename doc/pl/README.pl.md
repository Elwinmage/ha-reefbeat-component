# Red Sea (urządzenia ReefBeat) 🐠
> Część **[Ekosystemu ReefTech Project](https://elwinmage.github.io/reeftank/pl.html)**
<p align="center">
  <img src="../../icon.png" width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
![Installations](https://img.shields.io/badge/dynamic/json?label=Aktywne%20instalacje&query=estimated&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-reefbeat-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![Ruff Status](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)

Aby pomóc w tłumaczeniu, postępuj zgodnie z tym [przewodnikiem](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Przegląd
***Lokalne zarządzanie urządzeniami HomeAssistant RedSea Reefbeat (bez chmury): ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun i ReefWave***

## Powiązane projekty

Ta integracja jest jednym z trzech uzupełniających się projektów dla akwarium rafowego Red Sea:

| Projekt | Rola |
| --- | --- |
| [**ha-reefbeat-component**](https://github.com/Elwinmage/ha-reefbeat-component) | Ta integracja. Lokalne sterowanie urządzeniami ReefBeat z Home Assistant, bez chmury: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun i ReefWave. |
| [**ReefBeat watch**](https://github.com/Elwinmage/ha-reefbeat-component/tree/main/blueprints/automation) | Blueprint alertów dostarczany z tą integracją. Powiadamia o zaległych konserwacjach i kalibracjach, nietypowych trybach, niskim poziomie baterii i niedostępnych urządzeniach, na wybranych przez Ciebie urządzeniach mobilnych. [![Otwórz swoją instancję Home Assistant i wyświetl okno importu blueprintu.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml) |
| [**ha-reef-card**](https://github.com/Elwinmage/ha-reef-card) | Towarzysząca karta Lovelace. Niezbędna do edycji zaawansowanych harmonogramów ReefDose, ReefLed, ReefRun i ReefWave; daje każdemu urządzeniu interaktywny widok graficzny. |
| [**reefbeatEnergyBackup**](https://github.com/Elwinmage/reefbeatEnergyBackup) | Zasilanie awaryjne z akumulatora. Pakiet 24V LiFePO₄ sterowany przez Raspberry Pi, ze stopniowym ograniczaniem prędkości pomp zależnie od stanu naładowania. Działa samodzielnie lub razem z tą integracją. |

Wszystkie trzy, a także inne projekty rafowe, są opisane razem na [stronie projektu](https://elwinmage.github.io/reeftank/).

> [!TIP]
> Lista przyszłych implementacji jest dostępna [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> Lista błędów jest dostępna [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***Jeśli potrzebujesz innych czujników lub urządzeń wykonawczych, skontaktuj się ze mną [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Jeśli Twoje urządzenia nie są w tej samej podsieci co Home Assistant, [przeczytaj to](https://github.com/Elwinmage/ha-reefbeat-component/#my-device-is-not-detected).

> [!CAUTION]
> ⚠️ To nie jest oficjalne repozytorium RedSea. Używasz na własne ryzyko.⚠️

# Zgodność

✅ Przetestowano ☑️ Powinno działać (Jeśli masz takie urządzenie, czy możesz potwierdzić jego działanie [tutaj](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))
<table>
<th>
<td colspan="2"><b>Model</b></td>
<td colspan="2"><b>Status</b></td>
<td><b><a href="https://github.com/Elwinmage/reefbeatEnergyBackup">EnergyBackup</a></b></td>
<td><b>Issues</b> <br/>📆(Planned) <br/> 🐛(Bugs)</td>
</th>
<tr>
<td><a href="#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefcontrol">ReefControl</a></td>
<td colspan="2">RSCONTROLPRO</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROLPRO.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSCONTROLLITE</td><td>☑️</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROLLITE.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="#reefcontrol-power">ReefControl-Power</a></td>
<td colspan="2">RSPOWER6</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSPOWER6.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSPOWER8</td><td>☑️</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSPOWER8.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE2.png"/></td>
<td align="center" rowspan="2">–</td>
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
<td rowspan="6"> <a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
<td align="center" rowspan="6">–</td>
<td rowspan="6">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,RSLED90,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td>RSLED90</td>
<td>✅</td>
</tr>
<tr>
<td>RSLED160</td><td>✅ </td>
</tr>
<tr>
<td rowspan="3">G2</td>
<td>RSLED60</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g2.png"/></td>
</tr>
<tr>
<td>RSLED115</td><td>✅ </td>
</tr>
<tr>
<td>RSLED170</td><td>☑️</td>
</tr>
<tr>
<td rowspan="3"><a href="#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSMAT.png"/></td>
<td align="center" rowspan="3">–</td>
<td rowspan="3">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSMAT500</td><td>✅</td>
</tr>
<tr>
<td colspan="2">RSMAT1200</td><td>✅ </td>
</tr>
<tr>
<td><a href="#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>✅</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
<td align="center" rowspan="2">✅</td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSWAVE45</td><td>✅</td>
</tr>
</table>

(*) Użytkownicy ReefWave, proszę przeczytajcie [to](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)

# Spis treści
- [Instalacja przez HACS](https://github.com/Elwinmage/ha-reefbeat-component/#installation-via-hacs)
- [Wspólne funkcje](https://github.com/Elwinmage/ha-reefbeat-component/#common-functions)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/#reefled)
- [Wirtualna LED](https://github.com/Elwinmage/ha-reefbeat-component/#virtual-led)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)
- [Konserwacja](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance)
- [Cloud API](https://github.com/Elwinmage/ha-reefbeat-component/#cloud-api)
- [FAQ](https://github.com/Elwinmage/ha-reefbeat-component/#faq)

# Instalacja przez HACS

## Bezpośrednia instalacja

Kliknij tutaj, aby przejść bezpośrednio do repozytorium w HACS i kliknij „Pobierz": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Dla karty towarzyszącej ha-reef-card z zaawansowanymi funkcjami, kliknij tutaj, aby przejść do repozytorium w HACS i kliknij „Pobierz": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Szukaj w HACS
Lub wyszukaj «redsea» lub «reefbeat» w HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Image">
</p>

# Wspólne funkcje

# Ikony
Ta integracja udostępnia niestandardowe ikony dostępne przez "redsea:icon-name":

<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/redsea-icons.png"/>

## Dodaj urządzenie
Przy dodawaniu nowego urządzenia masz 4 opcje:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Image">
</p>

### Dodaj Cloud API
***Wymagane dla ReefWave, jeśli chcesz zachować synchronizację z aplikacją mobilną ReefBeat*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)). <br />
***Wymagane do otrzymywania powiadomień o nowych wersjach firmware*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update)).
- Pobierz informacje o użytkowniku
- Pobierz akwaria
- Pobierz bibliotekę Waves
- Pobierz bibliotekę LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Image">
</p>

### Automatyczne wykrywanie w sieci prywatnej
Jeśli nie jesteś w tej samej sieci, przeczytaj [to](#my-device-is-not-detected) i użyj [„Trybu ręcznego"](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Image">
</p>

### Tryb ręczny
Możesz wpisać adres IP urządzenia lub adres sieci do automatycznego wykrywania.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Image">
</p>

## Konfiguracja urządzenia

Kliknij urządzenie prawym przyciskiem myszy (lub otwórz jego opcje na stronie integracji), aby przejść do jego konfiguracji. Pierwszy ekran pozwala zmienić sposób, w jaki integracja komunikuje się z urządzeniem.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Image">
</p>

### Ustaw interwał skanowania urządzenia

Ustaw, jak często (w sekundach) integracja odpytuje urządzenie o nowe dane.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Image">
</p>

### Zmiana sieci WiFi

Możesz przenieść urządzenie do innej sieci WiFi bezpośrednio z Home Assistant, bez wracania do aplikacji ReefBeat.

W menu konfiguracji urządzenia wybierz **Zmiana sieci WiFi**. Integracja prosi urządzenie o wyszukanie pobliskich sieci i wyświetla je na liście rozwijanej, posortowane według siły sygnału. Sieć, z którą urządzenie jest obecnie połączone, jest wstępnie zaznaczona, więc jeśli chcesz tylko zaktualizować hasło, możesz pozostawić zaznaczenie bez zmian.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/device_cfg.png" alt="Image">
</p>

Wybierz sieć docelową, wpisz jej hasło i zatwierdź. Integracja wysyła nowe dane logowania do urządzenia, uruchamia je ponownie, a następnie automatycznie wyszukuje je w sieci, aby zaktualizować jego adres IP.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> Po zmianie sieci WiFi urządzenie może dołączyć do innej podsieci (na przykład przejść z `192.168.0.x` na `10.0.0.x`). Integracja skanuje każdą podsieć, z którą Home Assistant jest bezpośrednio połączony. Jeśli urządzenie trafi do podsieci, do której Home Assistant ma dostęp tylko przez router, ponowne wykrycie nie powiedzie się i zostaniesz poproszony o ręczne wpisanie docelowej podsieci (na przykład `10.0.0.0/24`).

## Aktualizacja na żywo

> [!NOTE]
> It is possible to choose whether to enable live_update_config or not. In this mode (old default), configuration data is continuously retrieved along with normal data. For RSDOSE or RSLED, these large HTTP requests can take a long time (7–9 seconds). Sometimes the device does not respond to the request, so a retry function has been implemented. When live_update_config is disabled, configuration data is only retrieved at startup and when requested via the "Fetch Configuration" button. This new mode is activated by default. You can change it in the device configuration. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Image">
</p>

> [!NOTE]
> Każde urządzenie udostępnia również przycisk „Pobierz dane". Wymusza natychmiastowy odczyt regularnie odpytywanych źródeł, bez czekania na kolejny cykl skanowania, i działa niezależnie od ustawienia Live_update_config — w przeciwieństwie do „Pobierz konfigurację", które odświeża tylko źródła konfiguracji.

## Aktualizacja Firmware
Możesz otrzymywać powiadomienia i aktualizować urządzenie, gdy dostępna jest nowa wersja oprogramowania. You must have an active ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) device with your credentials and the "Use Cloud API" switch must be enabled.
> [!TIP]
> The "Cloud API" is only needed to get the version number of the new release and compare it to the installed version. To update your firmware, the Cloud API is not strictly required.
> If you do not use the "Cloud API" (switch disabled or no Cloud API device installed), you will not be alerted when a new version is available, but you can still use the hidden "Force Firmware Update" button. If a new version is available, it will be installed.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Image">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Image">
</p>

# ReefATO:
- Włącz/wyłącz automatyczne napełnianie
- Ręczne napełnianie
- Włącz/wyłącz buzzer alarmu wycieku
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Image">
</p>

### Zadania konserwacyjne
| Zadanie | Domyślnie | Zakres |
| ------- | --------- | ------ |
| Czyszczenie sondy EC | 6 tygodni | 3 – 9 tygodni |
| Czyszczenie pompy powrotnej | 4,5 miesiąca | 2 – 7 miesięcy |

Zobacz sekcję [Konserwacja](README.pl.md#konserwacja).

# ReefControl:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_devices.png" alt="Image">
</p>

- Odczyt wszystkich podłączonych sond ReefSense (pH, ORP, zasolenie, temperatura, ATO, wyciek) z wartością i poziomem jakości
- Stan brzęczyka i czujnika wycieku
- Włączanie/wyłączanie portów 12V DC (RSCONTROL)
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_diag.png" alt="Image">
</p>

## ReefControl-Power

RSPOWER (Power Center) to samodzielne urządzenie z własnym adresem IP, widoczne osobno w Home Assistant.

- Stan, tryb, zużycie oraz włączanie/wyłączanie każdego gniazda
- 6 lub 8 sterowalnych gniazd w zależności od modelu (RSPOWER6 / RSPOWER8)
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_devices.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_diag.png" alt="Image">
</p>

# ReefDose:
- Edytuj dzienną dawkę
- Ręczne dozowanie
- Dodawaj i usuwaj suplementy
- Edytuj i kontroluj objętość pojemnika. Container volume settings are automatically enabled or disabled according to the volume control switch.
- Włącz/wyłącz harmonogram dla każdej pompy
- Konfiguracja alertów zapasów
- Opóźnienie dozowania między suplementami
- Napełnianie (Proszę przeczytać [this](https://github.com/Elwinmage/ha-reefbeat-component/#calibration-and-priming))
- Kalibracja (Proszę przeczytać [this](https://github.com/Elwinmage/ha-reefbeat-component/#calibration-and-priming))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Image">
</p>

### Główny
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Image">
</p>

### Głowice
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Image">
</p>

#### Calibration and Priming

> [!CAUTION]
> Musisz ściśle przestrzegać poniższej kolejności (Using the [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) is safer).<br /><br />
> <ins>Calibration</ins>:
>  1. Place the graduated container and press "Start Calibration"
>  2. Enter the measured value using the "Dose of Calibration" field
>  3. Press "Set Calibration Value"
>  4. Empty the graduated container and press "Test new Calibration". If the value obtained is not 4 mL, go back to step 1.
>  5. Press "Stop and Save Graduation"
>
> <ins>For priming</ins>:
>  1. (a) Press "Start Priming"
>  2. (b) When the liquid flows out, press "Stop Priming"
>  3. (1) Place the graduated container and press "Start Calibration"
>  4. (2) Enter the measured value using the "Dose of Calibration" field
>  5. (3) Press "Set Calibration Value"
>  6. (4) Empty the graduated container and press "Test new Calibration". If the value obtained is not 4 mL, go back to step 1.
>  7. (5) Press "Stop and Save Graduation"
>
> ⚠️ Priming must always be followed by a calibration (steps 1 to 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Image">
</p>

### Zadania konserwacyjne
| Zadanie | Poziom | Domyślnie | Zakres |
| ------- | ------ | --------- | ------ |
| Kalibracja głowic dozujących | Urządzenie | 90 dni | 80 – 120 dni |
| Wymiana głowic i wężyków | Na głowicę | 15 miesięcy | 11 – 19 miesięcy |

Wymiana śledzona jest **osobno dla każdej głowicy**: wymiana głowicy 2 nie
zeruje odliczania pozostałych trzech. Zobacz sekcję [Konserwacja](README.pl.md#konserwacja).

# ReefLED:

- Odczyt i ustawienie kanałów Białego i Niebieskiego (only for G1: RSLED50, RSLED90, RSLED160)
- Odczyt i ustawienie Temperatury barwowej, Intensywności i Księżyca (all LEDs)
- Zarządzaj aklimatyzacją. Acclimation settings are automatically enabled or disabled according to the acclimation switch.
- Zarządzaj fazami księżyca. Moon phase settings are automatically enabled or disabled according to the moon phase switch.
- Ustaw ręczny tryb koloru z czasem lub bez.
- Odczyt wartości wentylatora i temperatury.
- Odczyt nazwy i wartości programów (with cloud support). Only for G1 LEDs.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Image">
</p>

***

Color Temperature support for G1 LEDs takes into account the specificities of each of the three models.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## WAŻNE dla lamp G1 i G2

### LAMPY G2

#### Intensywność
Because G2 LEDs ensure constant intensity across the entire color range, your LEDs do not utilize their full capacity in the middle of the spectrum. At 8,000K, the white channel is at 100% and the blue channel at 0% (the opposite at 23,000K). At 14,000K with 100% intensity for G2 lights, the power of the white and blue channels is approximately 85%.
Here is the loss curve for the G2s.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
</p>

#### Temperatura barwowa
The G2 interface does not support the entire temperature range. From 8,000K to 10,000K, values are incremented in 200K steps, and from 10,000K to 23,000K in 500K steps. This behavior is handled automatically: if you choose an invalid value (e.g. 8,300K), a valid value will be automatically selected (8,200K in this example). This is why you may sometimes observe a slight cursor adjustment when selecting the color on a G2 light — the cursor repositions itself to an allowed value.

### LAMPY G1

G1 LEDs use white and blue channel control, which allows full power across the entire range, but not constant intensity without compensation.
That is why intensity compensation has been implemented.
This compensation ensures you get the same [PAR](https://en.wikipedia.org/wiki/Photosynthetically_active_radiation) (light intensity) regardless of your color temperature choice (in the range 12,000 to 23,000K).
> [!NOTE]
> Because Red Sea does not publish PAR values below 12,000K, compensation is only available in the 12,000 to 23,000K range. If you have a G1 LED and a PAR meter, you can [contact me](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) to add compensation for the full range (9,000 to 23,000K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

In other words, without compensation, an intensity of x% at 9,000K does not provide the same PAR as at 23,000K or 15,000K.

Here are the power curves:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

If you want to use the full power of your LED, disable intensity compensation (default).

If you enable intensity compensation, the light intensity will be constant across all color temperature values, but in the middle of the range you will not use the full capacity of your LEDs (as with G2 models).

Also note that if compensation is enabled, the intensity factor can exceed 100% for G1 lights if you manually adjust the White/Blue channels. This allows you to harness the full power of your LEDs!

***

### Zadania konserwacyjne
| Zadanie | Domyślnie | Zakres |
| ------- | --------- | ------ |
| Czyszczenie soczewek | 3 tygodnie | 1 – 5 tygodni |
| Odkurzanie wentylatora i kratek | 6 miesięcy | 5 – 7 miesięcy |

Te dwa zadania powstają dla wszystkich generacji ReefLED, łącznie z wirtualnym
LED-em. Zobacz sekcję [Konserwacja](README.pl.md#konserwacja).

# Wirtualna LED
- Grupuj i zarządzaj LED za pomocą wirtualnego urządzenia (create a virtual device from the integration panel, then use the configure button to link the LEDs).
- Możesz używać Kelvinów i intensywności do sterowania LED tylko jeśli masz G2 lub mieszankę G1 i G2.
- Możesz używać zarówno Kelvin/Intensywność jak i Biały i Niebieski jeśli masz tylko lampy G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

# ReefMat:
- Przełącznik automatycznego posuwu (włącz/wyłącz)
- Zaplanowany posuw
- Niestandardowa wartość posuwu: pozwala wybrać wartość posuwu rolki
- Ręczny posuw
- Zmień rolkę.
>[!TIP]
> For a new full roll, please set "roll diameter" to the minimum (4.0 cm). The size will be adjusted according to your RSMAT version. For a partially used roll, enter the value in cm.
- Dwa ukryte parametry: model i pozycja, jeśli musisz ponownie skonfigurować RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Image">
</p>

### Zadania konserwacyjne
| Zadanie | Domyślnie | Zakres |
| ------- | --------- | ------ |
| Wymiana węgla aktywnego | 25 dni | 2 – 5 tygodni |

Zobacz sekcję [Konserwacja](README.pl.md#konserwacja).

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
ostatniej kalibracji zgłoszoną przez urządzenie z interwałem ustawionym tutaj. Zobacz sekcję [Konserwacja](README.pl.md#konserwacja).

### Klucz do demontażu wirnika

Powyższe zadanie *Czyszczenie wirnika odpieniacza* wymaga odkręcenia korpusu
pompy, który mokry praktycznie nie daje się chwycić. Klucz do wydruku 3D do tego
zadania, wraz z filmem pokazującym użycie, jest dostępny tutaj:
[Klucz do wirnika DC Skimmer Red Sea](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

# ReefWave:
> [!IMPORTANT]
> ReefWave devices are different from other ReefBeat devices. They are the only devices that are slaves to the ReefBeat cloud.<br/>
> When you launch the ReefBeat mobile app, the status of all devices is queried and data from the ReefBeat app is retrieved from device state.<br/>
> For ReefWave, it is the opposite: there is no local control point (as you can see in the ReefBeat app, you cannot add a ReefWave to a disconnected aquarium).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Waves are stored in the cloud user library. When you change a wave's value, it is changed in the cloud library and applied to the new schedule.<br/>
> So there is no local mode? Not so simple. There is a hidden local API to control ReefWave, but the ReefBeat app will not detect the changes. As a result, the device and Home Assistant on one side, and the ReefBeat mobile app on the other, will be out of sync. The device and Home Assistant will always be synchronized.<br/>
> Now that you know, make your choice!

> [!NOTE]
> ReefWave waves have many linked parameters, and the range of some parameters depends on other parameters. I was not able to test all possible combinations. If you find a bug, you can create an issue [here](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Tryby ReefWave
As explained above, ReefWave devices are the only devices that can become unsynchronized with the ReefBeat app if you use the local API.
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
<td>Data is fetched via the local API. <br />On/off commands are also sent via the local API. <br />Wave commands are sent via the cloud API.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Data is fetched via the local API. <br />Commands are sent via the local API. <br />Device is shown as "off" in the ReefBeat app.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>Data is fetched via the local API. <br />Commands are sent via the local API.<br />The ReefBeat mobile app does not display the correct wave values if they have been changed via HA.<br/>Home Assistant always displays the correct values.<br/>You can change values from both the ReefBeat app and Home Assistant.</td>
<td>❌</td>
</tr>
</table>

For Cloud and Hybrid modes you must link your ReefBeat cloud account.
First create a ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) device with your credentials, and that's it!
The "Linked to account" sensor will be updated with the name of your ReefBeat account once the connection is established.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Zmiana bieżących wartości
To load current wave values into the preview fields, use the "Set Preview From Current Wave" button.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
To change the current wave values, set the preview values and use the "Save Preview" button.

The behavior is the same as the ReefBeat mobile app. All waves with the same ID in the current schedule will be updated.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

### Zadania konserwacyjne
| Zadanie | Domyślnie | Zakres |
| ------- | --------- | ------ |
| Czyszczenie koszy wirnika | 2 miesiące | 1 – 3 miesiące |

Zobacz sekcję [Konserwacja](README.pl.md#konserwacja).

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

# API Cloud
API Cloud umożliwia:
- Uruchamianie lub zatrzymywanie skrótów: awaryjny, konserwacja i karmienie,
- Pobierz informacje o użytkowniku,
- Pobierz bibliotekę waves,
- Pobierz bibliotekę suplementów,
- Pobierz bibliotekę programów LED,
- Otrzymuj powiadomienia o [nowej wersji firmware](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update),
- Wysyłaj polecenia do ReefWave gdy tryb „[Cloud lub Hybrydowy](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)" mode is selected.

Skróty, parametry waves i LED są posortowane według akwarium.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Image">
</p>

>[!TIP]
> Możesz wyłączyć pobieranie listy suplementów w konfiguracji urządzenia API Cloud.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Image">
***
# FAQ

## Moje urządzenie nie jest wykrywane
- Spróbuj ponownie uruchomić automatyczne wykrywanie za pomocą przycisku „Dodaj wpis". Sometimes devices do not respond because they are busy.
- If your Red Sea devices are not on the same subnet as your Home Assistant, auto-detection will first fail and then offer you the option to enter the IP address of your device or the address of the subnet where your devices are located. For subnet detection, please use the format IP/MASK, for example: 192.168.14.0/255.255.255.0.
- You can also use [Manual Mode](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Image">
</p>

## Niektóre dane są aktualizowane poprawnie, inne nie.
Dane są podzielone na trzy części: dane, konfiguracja i informacje o urządzeniu.
- Dane są regularnie aktualizowane.
- Dane konfiguracyjne są aktualizowane tylko przy uruchomieniu i po naciśnięciu przycisku „Pobierz konfigurację".
- Dane informacyjne urządzenia są aktualizowane tylko przy uruchomieniu.

Aby zapewnić regularne aktualizowanie danych konfiguracyjnych, włącz [Aktualizację konfiguracji na żywo](#live-update).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
