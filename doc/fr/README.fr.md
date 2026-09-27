# Red Sea (appareils ReefBeat) 🐠
> Fait partie de l'**[Écosystème ReefTech Project](https://elwinmage.github.io/reeftank/fr.html)**
<p align="center">
  <img src="../../icon.png" width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
![Installations](https://img.shields.io/badge/dynamic/json?label=Installations%20actives&query=estimated&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-reefbeat-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![Ruff Status](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)

# Présentation
***Gestion locale des appareils HomeAssitant RedSea Reefbeat (hors cloud) : ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun et ReefWave***

<!-- ecosystem:start -->

## Projets liés

Les projets ReefTech s'articulent entre eux : les intégrations font entrer votre matériel dans Home Assistant, la carte l'affiche et le pilote, et le secours le maintient en marche pendant une coupure. Chacun fonctionne aussi seul.

<table>
  <tr>
    <th width="100px"></th>
    <th>Projet</th>
    <th>Rôle</th>
    <th>Fonctionne avec</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td>🐠<br /><b>ha-reefbeat-component</b><br /><i>(ce dépôt)</i></td>
    <td>Appareils Red Sea ReefBeat, pilotés en local sans cloud : ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun et ReefWave.<br />blueprint d'alertes pour les modes anormaux, les calibrations et les batteries faibles. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td>🌊<br /><a href="https://github.com/Elwinmage/ha-aquamedic-component"><b>ha-aquamedic-component</b></a></td>
    <td>Pompes Aqua Medic via l'API cloud Gizwits : brasseurs EcoDrift et SmartDrift, pompes DC Runner de remontée et d'écumeur.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td>🐙<br /><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Suivi du nettoyage et de l'usure du matériel que Home Assistant ne peut pas interroger : pompes de brassage, pompes de remontée, écumeurs, réacteurs, tout ce que vous entretenez à la main.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td>🪸<br /><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Vue graphique interactive de chaque appareil sur votre tableau de bord, et seul moyen d'éditer les programmes avancés. Lit les trois intégrations ci-dessus via le contrat <code>reef_role</code> commun, sans configuration côté carte.</td>
    <td>les trois intégrations</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-blueprints/main/icon.png" width="64" alt="ha-reef-blueprints" /></td>
    <td>🐬<br /><a href="https://github.com/Elwinmage/ha-reef-blueprints"><b>ha-reef-blueprints</b></a></td>
    <td>Blueprints de notification communs à tout l'écosystème : entretiens en retard trouvés via le contrat <code>reef_role</code>, et appareils devenus injoignables. Huit langues.</td>
    <td>les trois intégrations</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td>⚡<br /><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Secours sur batterie en cas de coupure. Pack 24V LiFePO₄ piloté par un Raspberry Pi, avec dégradation progressive de la vitesse des pompes selon l'état de charge.</td>
    <td>seul, ou avec ha-reefbeat-component</td>
  </tr>
</table>

L'ensemble est documenté sur la [page du projet ReefTech](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

# Compatibilité

✅ Testé ☑️ Doit fonctionner (Si vous en possédez un, pouvez-vous confirmer son fonctionnement [ici](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))
<table>
<th>
<td colspan="2"><b>Modèle</b></td>
<td colspan="2"><b>État</b></td>
<td><b><a href="https://github.com/Elwinmage/reefbeatEnergyBackup">EnergyBackup</a></b></td>
<td><b>Problèmes</b> <br/>📆(Planifié) <br/> 🐛(Bogues)</td>
</th>
<tr>
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefato.fr.md#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
    <tr>
    <td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefcontrol.fr.md#reefcontrol">ReefControl</a></td>
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
    <td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefcontrol-power.fr.md#reefcontrol-power">ReefControl-Power</a></td>
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
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefdose.fr.md#reefdose">ReefDose</a></td>
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
<td rowspan="6"> <a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefled.fr.md#reefled">ReefLed</a></td>
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
<td rowspan="3"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefmat.fr.md#reefmat">ReefMat</a></td>
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
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefrun.fr.md#reefrun">ReefRun et DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefwave.fr.md#reefwave">ReefWave (*)</a></td>
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

(*) Utilisateurs de ReefWave, veuillez lire ceci : [ceci](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefwave.fr.md#reefwave)

# Résumé
- [Installation via hacs](#installation-via-hacs)
- [Fonctions communes](#fonctions-communes)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefato.fr.md#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefcontrol.fr.md#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefcontrol-power.fr.md#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefdose.fr.md#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefled.fr.md#reefled)
- [LED virtuelle](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/virtual-led.fr.md#led-virtuelle)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefmat.fr.md#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefrun.fr.md#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefwave.fr.md#reefwave)
- [Maintenance](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/maintenance.fr.md#maintenance)
- [API Cloud](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/cloud-api.fr.md#api-cloud)
- [FAQ](#faq)

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

# Icônes
Cette intégration fournit des icônes personnelles accessbiles via "redsea:icon-name":

<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/redsea-icons.png"/>

## Ajouter un appareil
Lors de l'ajout d'un nouvel appareil, quatre options s'offrent à vous :

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Image">
</p>

### Ajout de l'API Cloud
***Obligatoire pour garder les Reefwave synchronisées avec l'application mobile ReefBeat*** (Lire [ceci](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/reefwave.fr.md#reefwave)). <br />
***Obligatoire pour être notifié d'une nouvelle vesion de microgiciels*** (Lire [ceci](#mise-à-jour-du-microgiciel)).
- Informations utilisateur
- Aquariums
- Bibliothèque Waves
- Bibliothèque LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Image">
</p>

### Détection automatique sur réseau privé
Si vous n'êtes pas sur le même réseau, lisez [ceci](#mon-appareil-nest-pas-détecté) et utilisez le mode ["Manuel"](#mode-manuel)
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Image">
</p>

### Mode manuel
Vous pouvez saisir l'adresse IP ou l'adresse réseau de votre appareil pour une détection automatique.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Image">
</p>

## Configuration de l'appareil

Faites un clic droit sur un appareil (ou ouvrez ses options depuis la page de l'intégration) pour accéder à sa configuration. Le premier écran permet de modifier la façon dont l'intégration communique avec l'appareil.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Image">
</p>

### Définition de l'intervalle d'analyse pour l'appareil

Définissez la fréquence (en secondes) à laquelle l'intégration interroge l'appareil pour récupérer de nouvelles données.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Image">
</p>

### Changer de réseau WiFi

Vous pouvez déplacer un appareil vers un autre réseau WiFi directement depuis Home Assistant, sans repasser par l'application ReefBeat.

Dans le menu de configuration de l'appareil, choisissez **Changer de réseau WiFi**. L'intégration demande à l'appareil de scanner les réseaux à proximité et les affiche dans une liste déroulante, triés par puissance de signal. Le réseau auquel l'appareil est actuellement connecté est pré-sélectionné : si vous devez seulement mettre à jour le mot de passe, vous pouvez laisser la sélection telle quelle.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/device_cfg.png" alt="Image">
</p>

Choisissez le réseau cible, saisissez son mot de passe et validez. L'intégration envoie les nouveaux identifiants à l'appareil, le redémarre, puis le recherche automatiquement sur le réseau pour mettre à jour son adresse IP.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> Après un changement de WiFi, l'appareil peut rejoindre un sous-réseau différent (par exemple passer de `192.168.0.x` à `10.0.0.x`). L'intégration scanne tous les sous-réseaux auxquels Home Assistant est directement connecté. Si l'appareil arrive sur un sous-réseau que Home Assistant ne peut atteindre qu'à travers un routeur, la redécouverte échoue et il vous sera demandé de saisir manuellement le sous-réseau cible (par exemple `10.0.0.0/24`).

## Mise à jour en direct

> [!NOTE]
> Il est possible de choisir d'activer ou non le mode Live_update_config. Dans ce mode (ancien mode par défaut), les données de configuration sont récupérées en continu avec les données normales. Pour RSDOSE ou RSLED, ces requêtes http volumineuses peuvent prendre beaucoup de temps (7 à 9 secondes). Il arrive que l'appareil ne réponde pas à la requête ; j'ai donc dû coder une fonction de nouvelle tentative. Lorsque Live_update_config est désactivé, les données de configuration ne sont récupérées qu'au démarrage et sur demande via le bouton « Récupérer la configuration ». Ce nouveau mode est activé par défaut. Vous pouvez le modifier dans la configuration de l'appareil. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Image">
</p>

> [!NOTE]
> Chaque appareil expose également un bouton « Rafraîchir les données ». Il force une lecture immédiate des sources interrogées régulièrement, sans attendre le prochain cycle de scan, et fonctionne quel que soit le réglage Live_update_config — contrairement à « Récupérer la configuration », qui ne rafraîchit que les sources de configuration.

## Mise à jour du Microgiciel
Vous pouvez être notifié et mettre à jour votre appareil lorsqu'une nouvelle version du firmware. Vous devez disposer d'un composant actif ["cloud api"](#ajout-de-lapi-cloud) avec vos identifiants et l'interrupteur « Utiliser l'API cloud » doit être activé.
> [!TIP]
> L'« API cloud » est uniquement nécessaire pour obtenir le numéro de version de la nouvelle version et le comparer à la version installée. Pour mettre à jour votre firmware, l'API cloud n'est pas indispensable.
> Si vous n'utilisez pas l'« API cloud » (option désactivée ou composant API cloud non installé), vous ne serez pas averti lorsqu'une nouvelle version sera disponible, mais vous pourrez toujours utiliser le bouton caché « Forcer la mise à jour du firmware ». Si une nouvelle version est disponible, elle sera installée.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Image">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Image">
</p>

# FAQ

## Mon appareil n'est pas détecté
- Essayez de relancer la détection automatique avec le bouton « Ajouter une entrée ». Il arrive que les appareils ne répondent pas car ils sont occupés.
- Si vos appareils Redsea ne sont pas sur le même sous-réseau que votre Home Assistant, la détection automatique échouera d'abord et vous proposera de saisir l'adresse IP de votre appareil ou l'adresse du sous-réseau où se trouvent vos appareils. Pour la détection de sous-réseau, veuillez utiliser le format IP/MASK, comme dans cet exemple : 192.168.14.0/255.255.255.0.
- Vous pouvez également utiliser le mode [manuel](#mode-manuel).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Image">
</p>

## Certaines données sont correctement actualisées, d'autres non.
Les données sont divisées en trois parties : données, configuration et informations sur l'appareil.
- Les données sont régulièrement mises à jour.
- Les données de configuration sont mises à jour uniquement au démarrage et lorsque vous appuyez sur le bouton « fecth-config ».
- Les informations sur l'appareil sont mises à jour uniquement au démarrage.

Pour garantir la mise à jour régulière des données de configuration, veuillez activer la [mise à jour de la configuration en direct ](#mise-à-jour-en-direct).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
