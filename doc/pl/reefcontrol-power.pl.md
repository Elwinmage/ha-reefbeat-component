[← Powrót do strony głównej](README.pl.md)

# ReefControl-Power

RSPOWER (Power Center) to samodzielne urządzenie z własnym adresem IP, udostępniane w Home Assistant osobno.

<p align="center">
<img src="../img/rspower_devices.png" alt="Image">
</p>

- 6 lub 8 sterowanych gniazd w zależności od modelu (RSPOWER6 / RSPOWER8)
- **Dla każdego gniazda**: edytowalna nazwa, przełącznik wł./wył., stan, tryb, poprzedni tryb, zużycie oraz przycisk „Usuń gniazdko”, który przywraca gniazdo do stanu fabrycznego (tryb `setup`, nazwa fabryczna)
- **Urządzenie**: całkowite zużycie, poziom baterii, tryb, region modelu i liczba gniazd
- **Lokalna sonda temperatury** (opcjonalna): przyciski dodawania / usuwania, przycisk „Pobierz temperaturę”, kalibracja względem rzeczywistej temperatury, pożądany i akceptowalny zakres temperatury, nazwa, przełączniki powiadomień i rejestrowania — wszystko dostępne po zainstalowaniu sondy. Czujnik temperatury ma atrybuty `ranges` i `level`, tak jak sondy huba.
- **Parowanie z ReefControl**: sparowany hub, jego typ i status, stan połączenia i internetu oraz przycisk „Rozłącz hub sterujący”
- Zapisy są pokazywane natychmiast (aktualizacja optymistyczna), a następnie potwierdzane ponownym odczytem urządzenia

<p align="center">
<img src="../img/rspower_ctrl.png" alt="Image">
<img src="../img/rspower_conf.png" alt="Image">
<img src="../img/rspower_diag.png" alt="Image">
</p>

> [!NOTE]
> Lokalna sonda temperatury i hub ReefControl wykluczają się: „Dodaj sondę temperatury” jest dostępne tylko bez żadnego z nich, „Usuń sondę temperatury” przy lokalnej sondzie, a „Rozłącz hub sterujący” przy sparowanym hubie. Przyciski, które nie mają zastosowania, pozostają widoczne, ale niedostępne.

## Parowanie z ReefControl
Parowanie zawsze rozpoczyna się z huba, jego przyciskiem **Sparuj Power Center**: hub paruje się z Power Center, który znajdzie w sieci. Rozłączenie działa z obu stron. Gdy oba urządzenia są skonfigurowane w Home Assistant, zmiana pojawia się na obu jednocześnie — w przypadku parowania tylko wtedy, gdy jeden wolny Power Center nie pozostawia wątpliwości, o który chodzi.

Po sparowaniu sondy huba mogą sterować gniazdami. Power Center przechowuje tylko typ sondy, za którą podąża gniazdo; sama sonda i progi są zapisane w hubie. Dwie usługi pozwalają karcie lub automatyzacji odczytać tę stronę:

- `redsea.get_control_probes` — sondy huba (tożsamość i bieżące wartości), według jego identyfikatora sprzętowego
- `redsea.get_control_subscriptions` — reguły, które hub stosuje do gniazd swojego Power Center, według jego identyfikatora sprzętowego

Usunięcie gniazda w Power Center usuwa tylko jego połowę reguły sondy: przycisk **Wypisz gniazdko N** huba usuwa drugą połowę.

## Tryb gniazda i gniazda sterowane czujnikiem
Tryb gniazda (off / on / schedule / sensor) i jego ustawienia harmonogramu lub progu czujnika (np. „włącz to gniazdo, gdy lokalna temperatura spadnie poniżej 24 °C”) konfiguruje się z [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), tak jak [porty huba](reefcontrol.pl.md#tryby-portów-i-gniazd).

Każde gniazdo udostępnia encję `sensor.socket_N_mode` dla automatyzacji: jej stan to bieżący tryb gniazda, a atrybuty zawierają bieżący `schedule` oraz (w trybie sensor) `sensor_config`, oznaczony przez `sensor_source`: `local` dla własnej sondy Power Center, `control` dla reguły sparowanego huba.

Gniazdo sterowane harmonogramem lub sondą można ręcznie wyłączyć: jego tryb pokazuje wtedy `off`, a czujnik **poprzedni tryb** zachowuje tryb automatyczny, do którego gniazdo wróci.

Urządzenie automatycznie opuszcza początkowy stan „setup”, gdy tylko zostanie skonfigurowane pierwsze gniazdo, tak jak w aplikacji ReefBeat — nie jest potrzebna żadna ręczna czynność.

## Zadania konserwacyjne
| Zadanie | Domyślnie | Zakres |
| ------- | --------- | ------ |
| Kontrola wzrokowa | 1 miesiąc | 1 – 3 miesiące |
| Usunąć kurz i osady soli | 3 miesiące | 2 – 4 miesiące |

Red Sea nie publikuje harmonogramu konserwacji Power Center: te dwa zadania wynikają z ogólnej praktyki akwarystyki rafowej dla urządzeń sieciowych w pobliżu słonej wody. Przed odkurzaniem lub usuwaniem osadów soli odłącz Power Center od zasilania i użyj suchej ściereczki. Zobacz sekcję [Konserwacja](maintenance.pl.md#konserwacja).

---

[← Powrót do strony głównej](README.pl.md)
