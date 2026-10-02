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

### Programme météo
La rampe peut suivre la météo d'un lieu : en **mode météo GPS**, sa semaine
est construite à partir de la météo des sept jours à venir (prévisions) ou
des sept jours passés (météo mesurée), fournie par
[Open-Meteo](https://open-meteo.com) (gratuit, sans clé). Rien à valider :
activer le mode met de côté les programmations de la rampe et envoie tout de
suite la semaine météo ; la météo est ensuite récupérée à nouveau tous les
quelques jours (de 3 à 15, à votre choix ; vérifié une fois par jour, à
00:10) et à chaque changement de réglage (30 s après le dernier). Désactiver
le mode réécrit les programmations de la rampe.

| Entité | Rôle |
| ------ | ---- |
| `switch` Mode météo GPS | Météo GPS, ou programmations standard de la rampe |
| `select` Période météo | Semaine à venir (prévisions) ou passée (mesurée) |
| `number` Fréquence de la météo (jours) | Jours entre deux récupérations, de 3 à 15 |
| `text` Lieu météo | `lat, lon`, une URI `geo:` ou un lien Google Maps / OpenStreetMap / Apple Plans ; vide pour le domicile de Home Assistant |
| `select` Journée météo sur le bac | Heure du lieu, calée sur le lever, sur le coucher, ou étirée entre les deux |
| `time` Lever météo / Coucher météo | Heures du bac utilisées par ces calages |
| `number` Intensité minimale météo / Intensité maximale météo | Garde-fous de l'intensité |
| `switch` Nuages météo | Règle les nuages de la rampe sur les heures nuageuses |
| `sensor` Programme météo | Résultat de la dernière récupération (état, lieu, et pour chaque jour soleil, ensoleillement, couverture nuageuse et intensité maximale) ; `writing` (`{done, total}` jours) pendant l'envoi d'une semaine à la rampe |

Construction d'une journée :
- **Horaires** — du lever au coucher du lieu, à l'heure du lieu (un récif
  des Fidji se lève aussi à 6h00 sur la rampe), ou calés sur le bac :
  *lever* (la journée du lieu commence à l'heure choisie), *coucher* (elle
  finit à l'heure choisie), ou *les deux* (la journée du lieu est étirée
  entre les deux heures).
- **Intensité** — suit le soleil réellement reçu (rayonnement solaire
  horaire, 1000 W/m² valant plein soleil), entre le minimum et le maximum ;
  jusqu'à 8 points par jour.
- **Couleur** — celle de la programmation standard de la rampe au même
  moment de sa journée : son équilibre blanc/bleu sur une G1, sa
  température de couleur sur une G2. Vous pouvez choisir vos propres
  couleurs à la place, par jour de la semaine (réglage `colors` :
  `{jour: [{at, k}]}`, `at` allant du lever, 0, au coucher, 1, `k` la
  température de couleur de 8 000 à 23 000 K) ; une G1 les convertit avec la
  table de son modèle. Ce réglage n'a pas d'entité : il se fait depuis
  l'éditeur de programmation de ha-reef-card, ou avec
  `redsea.led_weather_save`.
- **Nuages** — sur les heures couvertes à 40 % au moins : Low, Medium ou
  High selon leur couverture moyenne ; supprimés un jour dégagé.
- **Lune** — garde sa place après le coucher.

La programmation s'appelle *Weather* sur la rampe. Les requêtes écrites
dans une rampe sont espacées (de 2 s) : une ReefLED répond tard, voire pas
du tout, à une commande envoyée trop tôt ; l'écriture d'une semaine prend
donc un peu de temps.

Les rampes d'un groupe ([LED virtuelle](virtual-led.fr.md#led-virtuelle)) partagent un seul
programme météo : activé ou réglé sur l'une d'elles, il l'est pour toutes.
Chaque rampe reçoit sa propre semaine météo, dans son format, et la
vérification quotidienne est faite une seule fois, par le groupe.

| Service | Rôle |
| ------- | ---- |
| `redsea.led_weather_apply` | Récupère à nouveau la météo et envoie la semaine tout de suite (mode météo uniquement), depuis une automatisation par exemple |
| `redsea.led_weather_preview` | La semaine que feraient des réglages, et celle de la rampe : rien n'est écrit |
| `redsea.led_weather_save` | Enregistre d'un coup des réglages et le mode (`enabled`), puis écrit la semaine (en arrière-plan, ou avant de répondre avec `wait`) |

***

### Décalage du lever de soleil
Chaque ReefLED répondant à `/offset` (testé au démarrage) reçoit un `number`
Décalage du lever de soleil (minutes) : la rampe joue toute sa
programmation avec ce retard. Dans un groupe, le
[lever de soleil décalé](virtual-led.fr.md#led-virtuelle) de la LED virtuelle le règle pour
chaque rampe.

***

### Bibliothèque cloud
Avec un compte cloud ReefBeat ([API Cloud](README.fr.md#ajout-de-lapi-cloud)), les programmations
de la bibliothèque de l'application ReefBeat peuvent être lues et écrites,
comme le fait l'éditeur de programmation de ha-reef-card. Les
programmations G1 sont conservées par aquarium, les G2 par compte ; celles
de Red Sea ne peuvent être ni modifiées ni supprimées.

| Service | Rôle |
| ------- | ---- |
| `redsea.led_library` | Liste les programmations utilisables par la rampe (`linked: false` sans compte cloud) |
| `redsea.led_library_save` | Ajoute une programmation (`name`, `program`, `clouds`), ou met à jour l'une des vôtres (`uid`) |
| `redsea.led_library_delete` | Supprime l'une de vos programmations (`uid`) |
| `redsea.led_convert` | Convertit des points G1 entre blanc/bleu et kelvin/intensité, avec la table du modèle et la compensation d'intensité |

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
