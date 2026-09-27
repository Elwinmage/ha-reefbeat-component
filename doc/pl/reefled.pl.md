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
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Image">
</p>

***

Obsługa temperatury barwowej lamp LED G1 uwzględnia specyfikę każdego z trzech modeli.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## WAŻNE dla lamp G1 i G2

### LAMPY G2

#### Intensywność
Ponieważ lampy LED G2 zapewniają stałą intensywność w całym zakresie barw, w środku widma nie wykorzystują pełnej mocy. Przy 8 000K kanał biały pracuje na 100 %, a niebieski na 0 % (odwrotnie przy 23 000K). Przy 14 000K i intensywności 100 % moc kanałów białego i niebieskiego w lampach G2 wynosi około 85 %.
Oto krzywa strat dla G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
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
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

Innymi słowy, bez kompensacji intensywność x % przy 9 000K nie daje tego samego PAR co przy 23 000K lub 15 000K.

Oto krzywe mocy:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

Jeśli chcesz wykorzystać pełną moc lampy, wyłącz kompensację intensywności (domyślnie).

Jeśli włączysz kompensację intensywności, natężenie światła będzie stałe dla wszystkich temperatur barwowych, ale w środku zakresu nie wykorzystasz pełnej mocy lamp (jak w modelach G2).

Pamiętaj też, że przy włączonej kompensacji współczynnik intensywności może przekroczyć 100 % w lampach G1, jeśli ręcznie ustawisz kanały biały/niebieski. Pozwala to wykorzystać pełną moc lamp!

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
