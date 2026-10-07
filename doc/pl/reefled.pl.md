[← Powrót do strony głównej](README.pl.md)

# ReefLED:

- Odczyt i ustawienie kanałów Białego i Niebieskiego (only for G1: RSLED50, RSLED90, RSLED160)
- Odczyt i ustawienie Temperatury barwowej, Intensywności i Księżyca (all LEDs)
- Zarządzaj aklimatyzacją. Acclimation settings are automatically enabled or disabled according to the acclimation switch.
- Zarządzaj fazami księżyca. Moon phase settings are automatically enabled or disabled according to the moon phase switch.
- Ustaw ręczny tryb koloru z czasem lub bez.
- Odczyt wartości wentylatora i temperatury.
- Odczyt nazwy i wartości programów (with cloud support). Only for G1 LEDs.

<p align="center">
<img src="../img/rsled_G1_ctrl.png" alt="Image">
<img src="../img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="../img/rsled_G1_sensors.png" alt="Image">
<img src="../img/rsled_conf.png" alt="Image">
</p>

***

Obsługa temperatury barwowej lamp LED G1 uwzględnia specyfikę każdego z trzech modeli.
<p align="center">
<img src="../img/leds_specs.png" alt="Image">
</p>

***
## WAŻNE dla lamp G1 i G2

### LAMPY G2

#### Intensywność
Ponieważ lampy LED G2 zapewniają stałą intensywność w całym zakresie barw, w środku widma nie wykorzystują pełnej mocy. Przy 8 000K kanał biały pracuje na 100 %, a niebieski na 0 % (odwrotnie przy 23 000K). Przy 14 000K i intensywności 100 % moc kanałów białego i niebieskiego w lampach G2 wynosi około 85 %.
Oto krzywa strat dla G2.
<p align="center">
<img src="../img/intensity_factor.png" alt="Image">
</p>

#### Temperatura barwowa
Interfejs G2 nie obsługuje całego zakresu temperatur. Od 8 000K do 10 000K wartości zmieniają się co 200K, a od 10 000K do 23 000K co 500K. Jest to obsługiwane automatycznie: jeśli wybierzesz nieprawidłową wartość (np. 8 300K), zostanie automatycznie wybrana prawidłowa (w tym przykładzie 8 200K). Dlatego przy wyborze barwy lampy G2 suwak czasem lekko się przesuwa — ustawia się na dozwolonej wartości.

### LAMPY G1

Lampy LED G1 są sterowane kanałami białym i niebieskim, co pozwala na pełną moc w całym zakresie, ale bez kompensacji nie daje stałej intensywności.
Dlatego wprowadzono kompensację intensywności.
Ta kompensacja zapewnia to samo [PAR](https://en.wikipedia.org/wiki/Photosynthetically_active_radiation) (natężenie światła) niezależnie od wybranej temperatury barwowej (w zakresie 12 000 do 23 000K).
> [!NOTE]
> Ponieważ Red Sea nie publikuje wartości PAR poniżej 12 000K, kompensacja jest dostępna tylko w zakresie 12 000 do 23 000K. Jeśli masz lampę G1 i miernik PAR, możesz [skontaktować się ze mną](https://github.com/Elwinmage/ha-reefbeat-component/discussions/), aby dodać kompensację w pełnym zakresie (9 000 do 23 000K).

<p align="center">
<img src="../img/intensity_compensation.png" alt="Image">
</p>

Innymi słowy, bez kompensacji intensywność x % przy 9 000K nie daje tego samego PAR co przy 23 000K lub 15 000K.

Oto krzywe mocy:
<p align="center">
<img src="../img/PAR_curves.png" alt="Image">
</p>

Jeśli chcesz wykorzystać pełną moc lampy, wyłącz kompensację intensywności (domyślnie).

Jeśli włączysz kompensację intensywności, natężenie światła będzie stałe dla wszystkich temperatur barwowych, ale w środku zakresu nie wykorzystasz pełnej mocy lamp (jak w modelach G2).

Pamiętaj też, że przy włączonej kompensacji współczynnik intensywności może przekroczyć 100 % w lampach G1, jeśli ręcznie ustawisz kanały biały/niebieski. Pozwala to wykorzystać pełną moc lamp!

***

### Program pogodowy
Lampa może podążać za pogodą wybranego miejsca: w **trybie pogody GPS** jej
tydzień jest budowany z pogody najbliższych siedmiu dni (prognoza) albo
siedmiu dni, które właśnie minęły (pogoda zmierzona), z serwisu
[Open-Meteo](https://open-meteo.com) (bezpłatny, bez klucza). Niczego nie
trzeba zatwierdzać: włączenie trybu odkłada własne programy lampy na bok i
od razu wysyła tydzień pogodowy; pogoda jest potem pobierana ponownie co
kilka dni (od 3 do 15, do wyboru; sprawdzane raz dziennie, o 00:10) oraz po
każdej zmianie ustawienia (30 s po ostatniej zmianie). Wyłączenie trybu
zapisuje z powrotem własne programy lampy.

| Encja | Rola |
| ----- | ---- |
| `switch` Tryb pogody GPS | Pogoda GPS albo standardowe programy lampy |
| `select` Okres pogody | Następny tydzień (prognoza) albo miniony tydzień (zmierzony) |
| `number` Odświeżanie pogody (dni) | Dni między dwoma pobraniami pogody, od 3 do 15 |
| `text` Lokalizacja pogody | `lat, lon`, URI `geo:` albo link z Google Maps / OpenStreetMap / Apple Maps; puste dla domu Home Assistant |
| `select` Dzień pogodowy w akwarium | Czas miejsca, zakotwiczony na wschodzie, na zachodzie, albo rozciągnięty między nimi |
| `time` Wschód pogody / Zachód pogody | Godziny akwarium używane przez te zakotwiczenia |
| `number` Minimalna intensywność pogody / Maksymalna intensywność pogody | Ograniczenia intensywności |
| `switch` Chmury pogodowe | Ustawia chmury lampy na pochmurne godziny |
| `sensor` Program pogodowy | Wynik ostatniego pobrania (stan, miejsce oraz dla każdego dnia słońce, nasłonecznienie, zachmurzenie i najwyższa intensywność); `writing` (`{done, total}` dni) podczas wysyłania tygodnia do lampy |

Jak powstaje dzień:
- **Godziny** — od wschodu do zachodu słońca w danym miejscu, według zegara
  miejsca (rafa na Fidżi wschodzi o 06:00 także na lampie), albo
  zakotwiczone na akwarium: *wschód* (dzień miejsca zaczyna się o wybranej
  godzinie), *zachód* (kończy się o wybranej godzinie) albo *oba* (dzień
  miejsca jest rozciągnięty między obiema godzinami).
- **Intensywność** — podąża za faktycznie otrzymanym słońcem (godzinowe
  promieniowanie słoneczne, 1000 W/m² to pełne słońce), między minimum a
  maksimum; do 8 punktów dziennie.
- **Kolor** — ten ze standardowego programu lampy w tym samym momencie jej
  dnia: balans białego/niebieskiego na G1, temperatura barwowa na G2.
  Zamiast tego możesz wybrać własne kolory, dla każdego dnia tygodnia
  (ustawienie `colors`: `{dzień: [{at, k}]}`, `at` od wschodu, 0, do
  zachodu, 1, `k` to temperatura barwowa od 8 000 do 23 000 K); G1
  przelicza je tabelą swojego modelu. To ustawienie nie ma encji: ustawia
  się je w edytorze programów ha-reef-card albo usługą
  `redsea.led_weather_save`.
- **Chmury** — w godzinach z zachmurzeniem co najmniej 40 %: Low, Medium
  albo High zależnie od średniego zachmurzenia; usuwane w pogodny dzień.
- **Księżyc** — zachowuje swoje miejsce po zachodzie słońca.

Program nazywa się na lampie *Weather*. Żądania zapisywane do lampy są
rozłożone w czasie (co 2 s): ReefLED odpowiada późno albo wcale na polecenie
wysłane zbyt wcześnie; zapis tygodnia trwa więc chwilę.

Lampy grupy ([Wirtualna LED](virtual-led.pl.md#wirtualna-led)) współdzielą jeden program
pogodowy: włączony lub ustawiony na dowolnej z nich, jest włączony i
ustawiony dla wszystkich. Każda lampa dostaje własny tydzień pogodowy, w
swoim formacie, a codzienne sprawdzenie wykonuje raz grupa.

| Usługa | Rola |
| ------ | ---- |
| `redsea.led_weather_apply` | Pobiera pogodę ponownie i od razu wysyła tydzień (tylko w trybie pogody), na przykład z automatyzacji |
| `redsea.led_weather_preview` | Tydzień, jaki dałyby podane ustawienia, oraz własny tydzień lampy: nic nie jest zapisywane |
| `redsea.led_weather_save` | Zapisuje naraz ustawienia i tryb (`enabled`), a potem zapisuje tydzień (w tle albo, z `wait`, przed odpowiedzią) |

***

### Przesunięcie wschodu słońca
Każda ReefLED odpowiadająca na `/offset` (sprawdzane przy starcie) dostaje
`number` Przesunięcie wschodu słońca (minuty): lampa odtwarza cały swój
program z takim opóźnieniem. W grupie ustawia je dla każdej lampy
[przesunięty wschód słońca](virtual-led.pl.md#wirtualna-led) wirtualnej LED.

***

### Biblioteka w chmurze
Z kontem w chmurze ReefBeat ([Cloud API](README.pl.md#dodaj-cloud-api)) programy świetlne z
biblioteki aplikacji ReefBeat można odczytywać i zapisywać, tak jak robi to
edytor programów ha-reef-card. Programy G1 są przechowywane dla akwarium,
programy G2 dla konta; programów Red Sea nie można zmieniać ani usuwać.

| Usługa | Rola |
| ------ | ---- |
| `redsea.led_library` | Lista programów, których lampa może użyć (`linked: false` bez konta w chmurze) |
| `redsea.led_library_save` | Dodaje program (`name`, `program`, `clouds`) albo aktualizuje jeden z Twoich (`uid`) |
| `redsea.led_library_delete` | Usuwa jeden z Twoich programów (`uid`) |
| `redsea.led_convert` | Przelicza punkty G1 między białym/niebieskim a kelwinami/intensywnością, tabelą modelu i z kompensacją intensywności |

***

### Zadania konserwacyjne
| Zadanie | Domyślnie | Zakres |
| ------- | --------- | ------ |
| Czyszczenie soczewek | 3 tygodnie | 1 – 5 tygodni |
| Odkurzanie wentylatora i kratek | 6 miesięcy | 5 – 7 miesięcy |

Te dwa zadania powstają dla wszystkich generacji ReefLED, łącznie z wirtualnym
LED-em. Zobacz sekcję [Konserwacja](maintenance.pl.md#konserwacja).

---

[← Powrót do strony głównej](README.pl.md)
