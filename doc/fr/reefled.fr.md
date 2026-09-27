[← Retour à la page principale](README.fr.md)

# ReefLED :

- Récupération et définition des valeurs de blanc, de bleu et de lune (uniquement pour G1 : RSLED50, RSLED90, RSLED160)
- Récupération et définition de la température de couleur, de l'intensité et de la lune (toutes les LED)
- Gestion de l'acclimatation. Les paramètres d'acclimatation sont automatiquement activés ou désactivés en fonction du commutateur d'acclimatation.
- Gestion des phases lunaires. Les paramètres des phases lunaires sont automatiquement activés ou désactivés selon le changement de phase lunaire.
- Réglage manuel du mode couleur avec ou sans durée.
- Affichage des paramètres du ventilateur et de la température.
- Affichage du nom et de la valeur des programmes (avec prise en charge des nuages). Uniquement pour les LED G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Image">

</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Image">
</p>

***

La prise en charge de la température de couleur pour les LED G1 tient compte des spécificités de chacun des trois modèles.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## IMPORTANTS pour les lampes G1 et G2

### LAMPES G2

#### Intensité
Ce type de LED garantissant une intensité constante sur toute la gamme de couleurs, vos LED n'exploitent pas pleinement leur capacité au milieu du spectre. À 8 000K, le canal blanc est à 100 % et le canal bleu à 0 % (l'inverse à 23 000K). À 14 000K et avec une intensité de 100 % pour les lampes G2, la puissance des canaux blanc et bleu est d'environ 85 %.
Voici la courbe de perte des G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
</p>

#### Températrue de Couleur
L'interface des lamptes G2 ne supporte par l'intégralité de la plage de température. De 8 000K à 10 000K, les valeurs s'incrémentent par pas de 200K et de 10 000K à 23 000K en pas de 500K. Ce comportement est pris en compte: si vous choisissez une valeur incorrecte (8 300K par exemple), une valeur valide sera automatiquement sélectionnée (8 200K dans notre exemple). C'est pourquoi vous pouvez parfois observer un petit mouvement de réajustement du curseur lors de la sélection de la couleur sur une lampe G2: le cursor se repositionne sur une valeur autorisée.

### LAMPES G1

Les LED G1 utilisent le contrôle des canaux blanc et bleu, ce qui permet une pleine puissance sur toute la plage, mais pas une intensité constante sans compensation.
C'est pourquoi j'ai mis en place une compensation d'intensité.
Cette compenstation vous assure d'avoir le même [PAR](https://fr.wikipedia.org/wiki/Rayonnement_photosynth%C3%A9tiquement_actif) (intensité lumineuse) quelque soit le choix de votre couleur (dans la plage 12 000 à 23 000K].
> [!NOTE]
> Comem RedSea ne publie pas les valeurs de PAR en dessous de 12 000K, la compensation ne fonctionne que dans la plage 12 000 à 23 000K. Si vous avez une LED G1 et un PARmètre, vous pouvez me [contacter](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) afin que j'ajoute la compensation sur la plage complète (9 000 à 23 000K).
>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

En d'autres termes, sans compensattion, une intensité de x % à 9 000 K ne fourni pas la même valeur de PAR qu'à 23 000 K ou 15 000 K.

Voici les courbes de puissance:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

Si vous souhaitez exploiter pleinement la puissance de votre LED, désactivez la compensation d'intensité (par défaut).

Si vous activez la compensation d'intensité, l'intensité lumineuse sera constante sur toutes les valeurs de température, mais en milieu de plage, vous n'utiliserez pas la pleine capacité de vos LED (comme sur les modèles G2).

N'oubliez pas non plus que, si vous activez le mode compensation, le facteur d'intensité peut dépasser les 100% pour les G1 si vous touchez manuellement aux canaux mode Blanc/Bleu. Vous pouvez ainsi exploiter toute la puissance de vos LED !

***

### Tâches de maintenance
| Tâche | Défaut | Plage |
| ----- | ------ | ----- |
| Nettoyer les lentilles | 3 semaines | 1 – 5 semaines |
| Dépoussiérer ventilateur et grilles | 6 mois | 5 – 7 mois |

Ces deux tâches sont créées pour toutes les générations de ReefLED, y compris la
LED virtuelle. Voir la section [Maintenance](maintenance.fr.md#maintenance).

---

[← Retour à la page principale](README.fr.md)
