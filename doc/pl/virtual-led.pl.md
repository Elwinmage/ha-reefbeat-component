[← Powrót do strony głównej](README.pl.md)

# Wirtualna LED
Wirtualna LED to **grupa** lamp ReefLED, jak „zgrupowane" LED w aplikacji
ReefBeat: jej lampy są sterowane jak jedna.

- Utwórz wirtualne urządzenie w panelu integracji, a następnie użyj
  przycisku konfiguracji: wybierz LED (co najmniej dwie, LED należy do
  najwyżej jednej grupy), a potem ich kolejność. Nowa wirtualna LED zaczyna
  od lamp, które aplikacja ReefBeat już grupuje, w kolejności aplikacji.
- Możesz używać Kelvinów i intensywności do sterowania LED tylko jeśli masz G2 lub mieszankę G1 i G2.
- Możesz używać zarówno Kelvin/Intensywność jak i Biały i Niebieski jeśli masz tylko lampy G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

## Co współdzieli grupa
Wspólna wartość ustawiona na wirtualnej LED albo na jednej z jej lamp jest
stosowana do wszystkich lamp grupy: kanały ręczne, kelwiny / intensywność,
tryb, timer, programy, aklimatyzacja, faza księżyca oraz
[program pogodowy](reefled.pl.md#program-pogodowy). To, co należy do lampy, zostaje na lampie:
nazwa, Wi-Fi, chmura, firmware, identyfikacja, reset…

Tak jak w aplikacji, zapis do grupy jest odrzucany, gdy jedna z lamp nie
jest załadowana, nie odpowiada albo jest w trybie, którym grupa nie może
sterować (wyłączona albo wstrzymana przez skrót): nic nie jest wysyłane,
więc lampy pozostają zsynchronizowane, a błąd wymienia te lampy. Lampa
wyłączona z użytku w aplikacji jest pomijana przy zapisach, sprawdzeniach i
przesuniętym wschodzie słońca. Białego / niebieskiego nie można ustawić na
grupie zawierającej lampę G2: użyj kelwinów / intensywności.

## Przesunięty wschód słońca
Tak jak w aplikacji, lampy grupy mogą zaczynać dzień jedna po drugiej:

| Encja | Rola |
| ----- | ---- |
| `switch` Przesunięty wschód słońca | Przesuwa wschód słońca lamp grupy |
| `number` Opóźnienie przesuniętego wschodu słońca | Minuty między dwiema lampami, od 1 do 15 (domyślnie 10) |

Każda lampa zaczyna dzień o `opóźnienie × pozycja` minut później (pierwsza
lampa grupy nie jest opóźniana). Wartość jest zapisywana w
Przesunięcie wschodu słońca każdej lampy, ponownie za każdym razem, gdy
zmieniają się lampy grupy lub ich kolejność; lampa opuszczająca grupę wraca
do 0.

## Lampy grupy
`sensor` Połączone LED, na wirtualnej LED i na każdej lampie
grupy, podaje liczbę lamp, a w atrybucie `leds` ich listę w kolejności
grupy: `hwid`, `name`, `model`, `g2`, `offset` (przesunięcie wschodu w
minutach, puste dla lampy bez `/offset`) i `entry_id`. ha-reef-card używa
go do wyświetlenia listy lamp.

## Synchronizacja z aplikacją ReefBeat
Z kontem w chmurze ReefBeat ([Cloud API](README.pl.md#dodaj-cloud-api)) grupa, której lampy są
jednego modelu, w jednym akwarium i na jednym koncie, jest tą samą grupą w
aplikacji: grupa, jej kolejność i jej przesunięty wschód słońca są
zapisywane do chmury albo pobierane z aplikacji, zależnie od tego, która
strona zmieniła się od ostatniej synchronizacji.

Grupa z aplikacji, którą nie steruje żadna wirtualna LED (co najmniej dwie
lampy załadowane w Home Assistant), jest proponowana jako nowa wirtualna LED
wśród urządzeń „Wykrytych", z lampami w kolejności aplikacji; „Ignoruj"
pozostawia ją zignorowaną.

Gdy decyzja należy do Ciebie, zgłaszana jest naprawa (Ustawienia > System >
Naprawy):

| Naprawa | Co zrobić |
| ------- | --------- |
| Brak konta chmury ReefBeat | Aplikacja mogłaby obsługiwać grupę, ale żadne konto w chmurze nie zawiera jej lamp: dodaj konto (naprawa zniknie sama) albo zostaw grupę tylko w Home Assistant |
| LED-y zgrupowane w aplikacji ReefBeat | Grupa zawiera kilka modeli, których aplikacja nie potrafi zgrupować, a część lamp jest nadal zgrupowana w aplikacji: rozgrupuj je tam; grupa istnieje wtedy tylko w Home Assistant |
| Zmieniona w Home Assistant i w aplikacji ReefBeat | Obie strony zmieniły się od ostatniej synchronizacji: wybierz grupę, która ma zostać |

---

[← Powrót do strony głównej](README.pl.md)
