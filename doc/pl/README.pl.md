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
[![Coverage](../../badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)

Aby pomóc w tłumaczeniu, postępuj zgodnie z tym [przewodnikiem](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Przegląd
***Lokalne zarządzanie urządzeniami HomeAssistant RedSea Reefbeat (bez chmury): ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun i ReefWave***

<!-- generated:demo-videos:start -->

## 🎬 Filmy demonstracyjne

<table>
<tr>
<td><a href="https://www.youtube.com/watch?v=Qee5LH0T9wQ"><img src="https://img.youtube.com/vi/Qee5LH0T9wQ/0.jpg" alt="Demo ReefDose" width="300"/></a><br/><em>Demo ReefDose</em></td>
<td><a href="https://www.youtube.com/watch?v=yyNyUSitb1E"><img src="https://img.youtube.com/vi/yyNyUSitb1E/0.jpg" alt="Demo ReefMat" width="300"/></a><br/><em>Demo ReefMat</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=Xxv38OPqiGI"><img src="https://img.youtube.com/vi/Xxv38OPqiGI/0.jpg" alt="Demo ReefRun" width="300"/></a><br/><em>Demo ReefRun</em></td>
<td><a href="https://www.youtube.com/watch?v=2R0DHp2eqT4"><img src="https://img.youtube.com/vi/2R0DHp2eqT4/0.jpg" alt="Demo ReefATO+" width="300"/></a><br/><em>Demo ReefATO+</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=voFobfc7Slk"><img src="https://img.youtube.com/vi/voFobfc7Slk/0.jpg" alt="Demo ReefControl & ReefControl-Power" width="300"/></a><br/><em>Demo ReefControl & ReefControl-Power</em></td>
<td><a href="https://www.youtube.com/watch?v=pA49z8QjTN4"><img src="https://img.youtube.com/vi/pA49z8QjTN4/0.jpg" alt="Demo ReefLed" width="300"/></a><br/><em>Demo ReefLed</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=sYVeE0zV3eo"><img src="https://img.youtube.com/vi/sYVeE0zV3eo/0.jpg" alt="Demo ReefWave" width="300"/></a><br/><em>Demo ReefWave</em></td>
</tr>
</table>

<!-- generated:demo-videos:end -->

<!-- ecosystem:start -->

## Powiązane projekty

Projekty ReefTech uzupełniają się: integracje wprowadzają sprzęt do Home Assistant, karta go wyświetla i steruje nim, a zasilanie awaryjne utrzymuje go w ruchu podczas przerwy w zasilaniu. Każdy działa również samodzielnie.

<table>
  <tr>
    <th width="100px"></th>
    <th>Projekt</th>
    <th>Rola</th>
    <th>Współpracuje z</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td>🐠<br /><b>ha-reefbeat-component</b><br /><i>(to repozytorium)</i></td>
    <td>Urządzenia Red Sea ReefBeat, sterowane lokalnie bez chmury: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun i ReefWave.<br />blueprint alertów dla nietypowych trybów, kalibracji i niskiego poziomu baterii. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td>🌊<br /><a href="https://github.com/Elwinmage/ha-aquamedic-component"><b>ha-aquamedic-component</b></a></td>
    <td>Pompy Aqua Medic przez chmurowe API Gizwits: pompy cyrkulacyjne EcoDrift i SmartDrift, pompy DC Runner obiegowe i do odpieniacza.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td>🐙<br /><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Śledzenie czyszczenia i zużycia sprzętu, do którego Home Assistant nie ma dostępu: pompy cyrkulacyjne, pompy obiegowe, odpieniacze, reaktory, wszystko co obsługujesz ręcznie.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td>🪸<br /><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Interaktywny widok graficzny każdego urządzenia na pulpicie i jedyny sposób edycji zaawansowanych harmonogramów. Odczytuje trzy integracje przez wspólny kontrakt <code>reef_role</code>, bez konfiguracji po stronie karty. Rysuje też przepływy energii z reefbeatEnergyBackup.</td>
    <td>wszystkie trzy integracje</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-blueprints/main/icon.png" width="64" alt="ha-reef-blueprints" /></td>
    <td>🐬<br /><a href="https://github.com/Elwinmage/ha-reef-blueprints"><b>ha-reef-blueprints</b></a></td>
    <td>Blueprinty powiadomień wspólne dla całego ekosystemu: zaległe konserwacje znajdowane przez kontrakt <code>reef_role</code> oraz urządzenia, które przestały odpowiadać. Osiem języków.</td>
    <td>wszystkie trzy integracje</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td>⚡<br /><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Zasilanie awaryjne na wypadek przerw w zasilaniu. Pakiet 24V LiFePO₄ sterowany przez Raspberry Pi, ze stopniowym obniżaniem prędkości pomp zależnie od stanu naładowania.</td>
    <td>samodzielnie lub razem z ha-reefbeat-component i ha-reef-card</td>
  </tr>
</table>

Wszystkie są udokumentowane razem na [stronie projektu ReefTech](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

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
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefato.pl.md#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="../img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefcontrol.pl.md#reefcontrol">ReefControl</a></td>
<td colspan="2">RSCONTROLPRO</td><td>✅</td>
<td width="200px"><img src="../img/RSCONTROLPRO.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSCONTROLLITE</td><td>☑️</td>
<td width="200px"><img src="../img/RSCONTROLLITE.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefcontrol-power.pl.md#reefcontrol-power">ReefControl-Power</a></td>
<td colspan="2">RSPOWER6</td><td>✅</td>
<td width="200px"><img src="../img/RSPOWER6.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSPOWER8</td><td>☑️</td>
<td width="200px"><img src="../img/RSPOWER8.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefdose.pl.md#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
<td width="200px"><img src="../img/RSDOSE2.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="../img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"> <a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefled.pl.md#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="../img/rsled_g1.png"/></td>
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
<td rowspan="3" width="200px"><img src="../img/rsled_g2.png"/></td>
</tr>
<tr>
<td>RSLED115</td><td>✅ </td>
</tr>
<tr>
<td>RSLED170</td><td>☑️</td>
</tr>
<tr>
<td rowspan="3"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefmat.pl.md#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="../img/RSMAT.png"/></td>
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
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefrun.pl.md#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="../img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefwave.pl.md#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>✅</td>
<td width="200px" rowspan="2"><img src="../img/RSWAVE.png"/></td>
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

(*) Użytkownicy ReefWave, proszę przeczytajcie [to](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefwave.pl.md#reefwave)

# Spis treści
- [Instalacja przez HACS](#instalacja-przez-hacs)
- [Wspólne funkcje](#wspólne-funkcje)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefato.pl.md#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefcontrol.pl.md#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefcontrol-power.pl.md#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefdose.pl.md#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefled.pl.md#reefled)
- [Wirtualna LED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/virtual-led.pl.md#wirtualna-led)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefmat.pl.md#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefrun.pl.md#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefwave.pl.md#reefwave)
- [Konserwacja](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/maintenance.pl.md#konserwacja)
- [Cloud API](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/cloud-api.pl.md#api-cloud)
- [FAQ](#faq)

# Instalacja przez HACS

## Bezpośrednia instalacja

Kliknij tutaj, aby przejść bezpośrednio do repozytorium w HACS i kliknij „Pobierz": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Dla karty towarzyszącej ha-reef-card z zaawansowanymi funkcjami, kliknij tutaj, aby przejść do repozytorium w HACS i kliknij „Pobierz": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Szukaj w HACS
Lub wyszukaj «redsea» lub «reefbeat» w HACS.

<p align="center">
<img src="../img/hacs_search.png" alt="Image">
</p>

# Wspólne funkcje

# Ikony
Ta integracja udostępnia niestandardowe ikony dostępne przez "redsea:icon-name":

<img src="../img/redsea-icons.png"/>

## Dodaj urządzenie
Przy dodawaniu nowego urządzenia masz 4 opcje:

<p align="center">
<img src="../img/add_devices_main.png" alt="Image">
</p>

### Dodaj Cloud API
***Wymagane dla ReefWave, jeśli chcesz zachować synchronizację z aplikacją mobilną ReefBeat*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/reefwave.pl.md#reefwave)). <br />
***Wymagane do otrzymywania powiadomień o nowych wersjach firmware*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#firmware-update)).
- Pobierz informacje o użytkowniku
- Pobierz akwaria
- Pobierz bibliotekę Waves
- Pobierz bibliotekę LED

<p align="center">
<img src="../img/add_devices_cloud_api.png" alt="Image">
</p>

### Automatyczne wykrywanie w sieci prywatnej
Jeśli nie jesteś w tej samej sieci, przeczytaj [to](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#my-device-is-not-detected) i użyj [„Trybu ręcznego"](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#manual-mode).
<p align="center">
<img src="../img/auto_detect.png" alt="Image">
</p>

### Tryb ręczny
Możesz wpisać adres IP urządzenia lub adres sieci do automatycznego wykrywania.

<p align="center">
<img src="../img/add_devices_manual.png" alt="Image">
</p>

## Konfiguracja urządzenia

Kliknij urządzenie prawym przyciskiem myszy (lub otwórz jego opcje na stronie integracji), aby przejść do jego konfiguracji. Pierwszy ekran pozwala zmienić sposób, w jaki integracja komunikuje się z urządzeniem.

<p align="center">
<img src="../img/configure_device_1.png" alt="Image">
</p>

### Ustaw interwał skanowania urządzenia

Ustaw, jak często (w sekundach) integracja odpytuje urządzenie o nowe dane.

<p align="center">
<img src="../img/configure_device_2.png" alt="Image">
</p>

### Zmiana sieci WiFi

Możesz przenieść urządzenie do innej sieci WiFi bezpośrednio z Home Assistant, bez wracania do aplikacji ReefBeat.

W menu konfiguracji urządzenia wybierz **Zmiana sieci WiFi**. Integracja prosi urządzenie o wyszukanie pobliskich sieci i wyświetla je na liście rozwijanej, posortowane według siły sygnału. Sieć, z którą urządzenie jest obecnie połączone, jest wstępnie zaznaczona, więc jeśli chcesz tylko zaktualizować hasło, możesz pozostawić zaznaczenie bez zmian.

<p align="center">
<img src="../img/device_cfg.png" alt="Image">
</p>

Wybierz sieć docelową, wpisz jej hasło i zatwierdź. Integracja wysyła nowe dane logowania do urządzenia, uruchamia je ponownie, a następnie automatycznie wyszukuje je w sieci, aby zaktualizować jego adres IP.

<p align="center">
<img src="../img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> Po zmianie sieci WiFi urządzenie może dołączyć do innej podsieci (na przykład przejść z `192.168.0.x` na `10.0.0.x`). Integracja skanuje każdą podsieć, z którą Home Assistant jest bezpośrednio połączony. Jeśli urządzenie trafi do podsieci, do której Home Assistant ma dostęp tylko przez router, ponowne wykrycie nie powiedzie się i zostaniesz poproszony o ręczne wpisanie docelowej podsieci (na przykład `10.0.0.0/24`).

## Aktualizacja na żywo

> [!NOTE]
> Można wybrać, czy włączyć live_update_config. W tym trybie (dawniej domyślnym) dane konfiguracyjne są pobierane stale razem ze zwykłymi danymi. W przypadku RSDOSE lub RSLED te duże zapytania HTTP mogą trwać długo (7–9 sekund). Czasem urządzenie nie odpowiada na zapytanie, dlatego zaimplementowano ponawianie. Gdy live_update_config jest wyłączone, dane konfiguracyjne są pobierane tylko przy starcie i na żądanie przyciskiem „Pobierz konfigurację". Ten nowy tryb jest domyślnie włączony. Można go zmienić w konfiguracji urządzenia. <p align="center">
<img src="../img/configure_device_live_update_config.png" alt="Image">
<img src="../img/fetch_config_button.png" alt="Image">
</p>

> [!NOTE]
> Każde urządzenie udostępnia również przycisk „Pobierz dane". Wymusza natychmiastowy odczyt regularnie odpytywanych źródeł, bez czekania na kolejny cykl skanowania, i działa niezależnie od ustawienia Live_update_config — w przeciwieństwie do „Pobierz konfigurację", które odświeża tylko źródła konfiguracji.

## Aktualizacja Firmware
Możesz otrzymywać powiadomienia i aktualizować urządzenie, gdy dostępna jest nowa wersja oprogramowania. Musisz mieć aktywne urządzenie [„Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#add-cloud-api) ze swoimi danymi logowania, a przełącznik „Użyj API chmury" musi być włączony.
> [!TIP]
> „Cloud API" jest potrzebne tylko do pobrania numeru nowej wersji i porównania go z zainstalowaną. Do samej aktualizacji firmware Cloud API nie jest konieczne.
> Jeśli nie używasz „Cloud API" (przełącznik wyłączony lub brak urządzenia Cloud API), nie dostaniesz powiadomienia o nowej wersji, ale nadal możesz użyć ukrytego przycisku „Wymuś aktualizację firmware". Jeśli nowa wersja jest dostępna, zostanie zainstalowana.
<p align="center">
  <img src="../img/firmware_update_1.png" alt="Image">
  <img src="../img/firmware_update_2.png" alt="Image">
</p>

# FAQ

## Moje urządzenie nie jest wykrywane
- Spróbuj ponownie uruchomić automatyczne wykrywanie za pomocą przycisku „Dodaj wpis". Sometimes devices do not respond because they are busy.
- Jeśli urządzenia Red Sea nie są w tej samej podsieci co Home Assistant, automatyczne wykrywanie najpierw się nie powiedzie, a następnie zaproponuje wpisanie adresu IP urządzenia lub adresu podsieci, w której znajdują się urządzenia. Do wykrywania w podsieci użyj formatu IP/MASKA, na przykład: 192.168.14.0/255.255.255.0.
- You can also use [Manual Mode](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#manual-mode).

<p align="center">
<img src="../img/subnetwork.png" alt="Image">
</p>

## Niektóre dane są aktualizowane poprawnie, inne nie.
Dane są podzielone na trzy części: dane, konfiguracja i informacje o urządzeniu.
- Dane są regularnie aktualizowane.
- Dane konfiguracyjne są aktualizowane tylko przy uruchomieniu i po naciśnięciu przycisku „Pobierz konfigurację".
- Dane informacyjne urządzenia są aktualizowane tylko przy uruchomieniu.

Aby zapewnić regularne aktualizowanie danych konfiguracyjnych, włącz [Aktualizację konfiguracji na żywo](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#live-update).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
