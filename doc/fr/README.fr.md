[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/commits/main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

<!-- [![Clones GitHub](https://img.shields.io/badge/dynamic/json?color=success&label=uniques-clones&query=uniques&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge) -->

# Présentation
***Gestion locale des appareils HomeAssitant RedSea Reefbeat (hors cloud) : ReefATO+, ReefDose, ReefLed, ReefMat, ReefRun et ReefWave***

> [!TIP]
> ***Pour modifier la programmation avancée de ReefDose, ReefLed, ReefRun et ReefWave, vous devez utiliser la [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) (en cours de développement)***

> [!TIP]
> La liste des futures implémentations est disponible [ici](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> La liste des bugs est disponible [ici](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***Si vous avez besoin d'autres capteurs ou actionneurs, n'hésitez pas à me contacter [ici](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Si vos appareils ne sont pas sur le même sous-réseau que votre Home Assistant, veuillez [lire ceci](README.fr.md#mon-appareil-nest-pas-d%C3%A9tect%C3%A9).

> [!CAUTION]
> ⚠️ Ceci n'est pas un dépôt RedSea officiel. À utiliser à vos risques et périls.⚠️

# Compatibilité

✅ Testé ☑️ Doit fonctionner (Si vous en possédez un, pouvez-vous confirmer son fonctionnement [ici](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))❌ No Supported Yet 
<table>
<th>
<td colspan="2"><b>Modèle</b></td>
<td colspan="2"><b>État</b></td>
<td><b>Problèmes</b> <br/>📆(Planifié) <br/> 🐛(Bogues)</td>
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
    <td colspan="2">RSSENSE<br />Vous en avez un, contactez-moi <a href="https://github.com/Elwinmage/ha-reefbeat-component/discussions/8">ici</a> pour que je l'ajoute.</td><td>❌</td>
    <td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROL.png"/></td>
    <td>
      <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
      <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
    </td>

  </tr>  
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
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
<td rowspan="6"> <a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
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
<td><a href="#reefrun">ReefRun et DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>☑️</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSWAVE45</td><td>✅</td>
</tr>
</table>

(*) Utilisateurs de ReefWave, veuillez lire ceci : [ceci](README.fr.md#reefwave)

# Résumé
- [Installation via hacs](README.fr.md#installation-via-hacs)
- [Fonctions communes](README.fr.md#fonctions-communes)
- [ReefATO+](README.fr.md#reefato)
- [ReefControl](README.fr.md#reefcontrol)
- [ReefDose](README.fr.md#reefdose)
- [ReefLED](README.fr.md#reefled)
- [LED virtuelle](README.fr.md#led-virtuelle)
- [ReefMat](README.fr.md#reefmat)
- [ReefRun](README.fr.md#reefrun)
- [ReefWave](README.fr.md#reefwave)
- [API Cloud](README.fr.md#api-cloud)
- [FAQ](README.fr.md#faq)

# Installation via HACS

## Installation directe

Cliquez ici pour accéder directement au dépôt dans HACS et cliquez sur « Télécharger » : [![Ouvrez votre instance Home Assistant et ouvrez un dépôt dans la communauté Home Assistant Boutique.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Pour la carte compagnon ha-reef-card offrant des fonctionnalités avancées et ergonomiques, cliquez ici pour accéder directement au dépôt dans HACS et cliquez sur « Télécharger » : [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Rechercher dans HACS
Ou recherchez « redsea » ou « reefbeat » dans HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Image">
</p>

# Fonctions communes

## Ajouter un appareil
Lors de l'ajout d'un nouvel appareil, quatre options s'offrent à vous :

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Image">
</p>

### Ajout de l'API Cloud
***Obligatoire pour garder les Reefwave synchronisées avec l'application mobile ReefBeat*** (Lire [ceci](README.fr.md#reefwave)). <br />
***Obligatoire pour être notifié d'une nouvelle vesion de microgiciels*** (Lire [ceci](README.fr.md#mise-%C3%A0-jour-du-microgiciel)).
- Informations utilisateur
- Aquariums
- Bibliothèque Waves
- Bibliothèque LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Image">
</p>

### Détection automatique sur réseau privé
Si vous n'êtes pas sur le même réseau, lisez [ceci](README.fr.md#mon-appareil-n'est-pas-détecté) et utilisez le mode ["Manuel"](README.fr.md#mode-manuel)
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Image">
</p>

### Mode manuel
Vous pouvez saisir l'adresse IP ou l'adresse réseau de votre appareil pour une détection automatique.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Image">
</p>

### Définition de l'intervalle d'analyse pour l'appareil

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Image">
</p>

## Mise à jour en direct

> [!NOTE]
> Il est possible de choisir d'activer ou non le mode Live_update_config. Dans ce mode (ancien mode par défaut), les données de configuration sont récupérées en continu avec les données normales. Pour RSDOSE ou RSLED, ces requêtes http volumineuses peuvent prendre beaucoup de temps (7 à 9 secondes). Il arrive que l'appareil ne réponde pas à la requête ; j'ai donc dû coder une fonction de nouvelle tentative. Lorsque Live_update_config est désactivé, les données de configuration ne sont récupérées qu'au démarrage et sur demande via le bouton « Récupérer la configuration ». Ce nouveau mode est activé par défaut. Vous pouvez le modifier dans la configuration de l'appareil. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Image">
</p>

## Mise à jour du Microgiciel
Vous pouvez être notifié et mettre à jour votre appareil lorsqu'une nouvelle version du firmware. Vous devez disposer d'un composant actif ["cloud api"](README.fr.md#ajout-de-lapi-cloud) avec vos identifiants et l'interrupteur « Utiliser l'API cloud » doit être activé. 
> [!TIP]
> L'« API cloud » est uniquement nécessaire pour obtenir le numéro de version de la nouvelle version et le comparer à la version installée. Pour mettre à jour votre firmware, l'API cloud n'est pas indispensable.
> Si vous n'utilisez pas l'« API cloud » (option désactivée ou composant API cloud non installé), vous ne serez pas averti lorsqu'une nouvelle version sera disponible, mais vous pourrez toujours utiliser le bouton caché « Forcer la mise à jour du firmware ». Si une nouvelle version est disponible, elle sera installée.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Image">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Image">
</p> 


# ReefATO :
- Activation/désactivation du remplissage automatique
- Remplissage manuel
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Image">
</p>

# ReefControl:
Non supporté pour l'instant. Si vous en avez un, contactez-moi [ici](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8) pour que je l'ajoute.

# ReefDose :
- Modification de la dose quotidienne
- Dose manuelle
- Ajout et suppression de suppléments
- Modification et contrôle du volume du récipient. Le réglage du volume du récipient est automatiquement activé ou désactivé en fonction du volume sélectionné.
- Activation/désactivation de la programmation par pompe
- Configuration des alertes de stock
- Délai de dosage entre les compléments
- Amorçage (Veuillez lire [ceci](README.fr.md#calibration-et-amor%C3%A7age))
- Calibration (Veuillez lire [ceci](README.fr.md#calibration-et-amor%C3%A7age))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Image">
</p>

### Têtes
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Image">
</p>

#### Calibration et amorçage

> [!CAUTION]
> Vous devez suivre précisement l'ordre suivant (L'utilisation de [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) est plus sécuritaire).<br /><br />
> <ins>Calibration</ins>:
>  1. Positionnez l'éprouvette et pressez "Start Calibration"
>  2. Indiquez la valeur mesure à l'aide du champ "Dose of Calibration"
>  3. Pressez "Set Calibration Value"
>  4. Videz l'éprouvette et pressez "Test new Calibration". Si la valeur obtenue est différente de 4mL, revenez à l'étape 1.
>  5. Pressez "Stop and Save Graduation"
> 
> <ins>For priming</ins>:
>  1. (a) Pressez "Start Priming"
>  2. (b) Lorsque le liquide coule pressez "Stop Priming"
>  3. (1) Positionnez l'éprouvette et pressez "Start Calibration"
>  4. (2) Indiquez la valeur mesure à l'aide du champ "Dose of Calibration"
>  5. (3) Pressez "Set Calibration Value"
>  6. (4) Videz l'éprouvette et pressez "Test new Calibration". Si la valeur obtenue est différente de 4mL, revenez à l'étape 1.
>  7. (5) Pressez "Stop and Save Graduation"
>        
> ⚠️ Un amorçage doit forcément être suivi d'une calibration (étapes 1 à 5)!⚠️

<p align="center"> 
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Image">
</p>

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

# LED virtuelle
- Regroupez et gérez les LED avec un périphérique virtuel (créez un périphérique virtuel depuis le panneau d'intégration, puis utilisez le bouton de configuration pour lier les LED).
- Vous ne pouvez utiliser les Kelvin et l'intensité pour contrôler vos LED que si vous avez une G2 ou un mix de G1 et G2.
- Vous pouvez utiliser à la fois les Kelvin/Intensité et Blanc&Bleu si vous n'avez que des G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

# ReefMat :
- Interrupteur d'avance automatique (activer/désactiver)
- Avance programmée
- Valeur d'avance personnalisée : permet de sélectionner la valeur d'avance du roulis
- Avance manuelle
- Modifier le roulis.
>[!TIP]
> Pour un nouveau rouleau complet, veuillez régler le « diamètre du rouleau » sur minimum (4,0 cm). La taille sera ajustée en fonction de votre version RSMAT. Pour un rouleau déjà utilisé, saisissez la valeur en cm.
- Deux paramètres cachés : modèle et position, si vous devez reconfigurer votre RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Image">
</p>

# ReefRun :
- Réglage de la vitesse de la pompe
- Gestion du sur-écrémage
- Gestion de la détection de godet plein
- Modification possible du modèle d'écrémeur

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Image">
</p>

### Pompes
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Image">
</p>

# ReefWave :
> [!IMPORTANT]
> Les appareils ReefWave sont différents des autres appareils ReefBeat. Ce sont les seuls appareils esclaves du cloud ReefBeat.<br/>
> Lorsque vous lancez l'application mobile ReefBeat, l'état de tous les appareils est interrogé et les données de l'application ReefBeat sont récupérées à partir de l'état de l'appareil.<br/>
> Pour ReefWave, c'est l'inverse : il n'y a pas de point de contrôle local (comme vous pouvez le constater dans l'application ReefBeat, vous ne pouvez pas ajouter un ReefWave à un aquarium déconnecté).<br/>
> <center ><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Les vagues sont stockées dans la bibliothèque utilisateur du cloud. Lorsque vous modifiez la valeur d'une vague, celle-ci est modifiée dans la bibliothèque cloud et appliquée à la nouvelle programmation.<br/>
> Il n'y a donc pas de mode local ? Pas si simple. Il existe une API locale cachée pour contrôler ReefWave, mais l'application ReefBeat ne détecte pas les modifications. Ainsi, l'appareil et HomeAssistant d'un côté, et l'application mobile ReefBeat de l'autre, seront désynchronisés. L'appareil et HomeAssistant seront toujours synchronisés.<br/>
> Maintenant que vous savez, faites votre choix !

> [!NOTE]
> Les vagues ReefWave ont de nombreux paramètres liés, et la plage de certains paramètres dépend d'autres paramètres. Je n'ai pas pu tester toutes les combinaisons possibles. Si vous trouvez un bug, vous pouvez créer un ticket [ici](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modes ReefWave
Comme expliqué précédemment, les appareils ReefWave sont les seuls à pouvoir être désynchronisés de l'application ReefBeat si vous utilisez l'API locale.
Trois modes sont disponibles : Cloud, Local et Hybride.
Vous pouvez modifier les paramètres de mode « Connexion au Cloud » et « Utiliser l'API Cloud » comme décrit dans le tableau ci-dessous.

<table>
<tr>
<td>Nom du mode</td>
<td>Commutateur Connexion au Cloud</td>
<td>Commutateur Utiliser l'API Cloud</td>
<td>Comportement</td>
<td>ReefBeat et HA sont synchronisés</td>
</tr>
<tr>
<td>Cloud (par défaut)</td>
<td>✅</td>
<td>✅</td>
<td>Les données sont récupérées via l'API locale. <br />Les commandes marche/arrêt sont également envoyées via l'API locale. <br />Les commandes sont envoyées via l'API cloud.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Les données sont récupérées via l'API locale. <br />Les commandes sont envoyées via l'API locale. <br />L'appareil est affiché comme « éteint » dans l'application ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybride</td>
<td>✅</td>
<td>❌</td>
<td>Les données sont récupérées via l'API locale. <br />Les commandes sont envoyées via l'API locale.<br />L'application mobile ReefBeat ne représente pas les valeurs des bonnes vagues si elles ont été modifiées via HA.<br/>Home Assistant les représente toujours.<br/>Vous pouvez modifier les valeurs depuis l'application ReefBeat et Home Assistant.</td>
<td>❌</td>
</tr>
</table>

Pour les modes Cloud et Hybride, vous devez lier votre compte cloud ReefBeat.
Créez d'abord une ["API cloud"](README.fr.md#ajout-de-lapi-cloud) avec vos identifiants, et c'est tout !
Le capteur « Lié au compte » sera mis à jour avec le nom de votre compte ReefBeat une fois la connexion établie.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Modification des valeurs actuelles
Pour charger les valeurs des vagues actuelles dans les champs d'aperçu, utilisez le bouton « Définir l'aperçu à partir de la vague actuelle ».
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
Pour modifier les valeurs des vagues actuelles, définissez les valeurs d'aperçu et utilisez le bouton « Enregistrer l'aperçu ».

Le fonctionnement est identique à celui de l'application mobile ReefBeat. Toutes les vagues ayant le même identifiant dans le planning actuel seront mises à jour.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

# API Cloud
L'API Cloud permet d'obtenir les informations utilisateur, la bibliothèque de vagues, de suppléments et de LEDs, d'être notifié en cas de [nouvelle version d'un microgiciel](README.fr.md#mise-%C3%A0-jour-du-microgiciel) et d'envoyer des commandes à ReefWave lorsque le mode « [Cloud ou Hybride](README.fr.md#reefwave) » est sélectionné.
Les paramètres des vagues et des LEDs sont triés par aquarium.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Image">
</p>

>[!TIP]
> Il est possible de désactiver la récupération de la liste des suppléments via l'interface de configuration du périphérique API Cloud.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Image">
***
# FAQ

## Mon appareil n'est pas détecté
- Essayez de relancer la détection automatique avec le bouton « Ajouter une entrée ». Il arrive que les appareils ne répondent pas car ils sont occupés.
- Si vos appareils Redsea ne sont pas sur le même sous-réseau que votre Home Assistant, la détection automatique échouera d'abord et vous proposera de saisir l'adresse IP de votre appareil ou l'adresse du sous-réseau où se trouvent vos appareils. Pour la détection de sous-réseau, veuillez utiliser le format IP/MASK, comme dans cet exemple : 192.168.14.0/255.255.255.0.
- Vous pouvez également utiliser le mode [manuel](README.fr.md#mode-manuel).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Image">
</p>

## Certaines données sont correctement actualisées, d'autres non.
Les données sont divisées en trois parties : données, configuration et informations sur l'appareil.
- Les données sont régulièrement mises à jour.
- Les données de configuration sont mises à jour uniquement au démarrage et lorsque vous appuyez sur le bouton « fecth-config ».
- Les informations sur l'appareil sont mises à jour uniquement au démarrage.

Pour garantir la mise à jour régulière des données de configuration, veuillez activer la [mise à jour de la configuration en direct ](README.fr.md#mise-%C3%A0-jour-en-direct).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square


