[← Retour à la page principale](README.fr.md)

# ReefControl-Power

Le RSPOWER (Power Center) est un appareil autonome avec sa propre adresse IP, exposé séparément dans Home Assistant.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_devices.png" alt="Image">
</p>

- 6 ou 8 prises contrôlables selon le modèle (RSPOWER6 / RSPOWER8)
- **Par prise** : nom modifiable, switch marche/arrêt, état, mode, mode précédent, consommation, et un bouton « Supprimer prise » qui remet la prise dans son état d'usine (mode `setup`, nom d'usine)
- **Appareil** : consommation totale, niveau de batterie, mode, région du modèle et nombre de prises
- **Sonde de température locale** (optionnelle) : boutons d'ajout / de suppression, bouton « Obtenir la température », étalonnage sur la température réelle, plages de température souhaitée et acceptable, nom, switches de notifications et de journalisation — tous disponibles une fois la sonde installée. Le capteur de température porte les attributs `ranges` et `level`, comme les sondes du hub.
- **Appairage ReefControl** : hub appairé, son type et son statut, état de la liaison et d'internet, et un bouton « Désapparier le hub de contrôle »
- Les écritures s'affichent immédiatement (mise à jour optimiste), puis sont confirmées par une relecture de l'appareil

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_diag.png" alt="Image">
</p>

> [!NOTE]
> La sonde de température locale et le hub ReefControl s'excluent : « Ajouter la sonde de température » n'est disponible qu'en l'absence des deux, « Supprimer la sonde de température » avec une sonde locale, et « Désapparier le hub de contrôle » avec un hub appairé. Les boutons restent visibles mais indisponibles quand ils ne s'appliquent pas.

## Appairage avec un ReefControl
L'appairage se lance toujours depuis le hub, avec son bouton **Apparier le Power Center** : le hub s'appaire au Power Center qu'il trouve sur le réseau. Le désappairage fonctionne des deux côtés. Quand les deux appareils sont configurés dans Home Assistant, le changement apparaît sur les deux à la fois — pour un appairage, seulement quand un unique Power Center libre ne laisse aucun doute.

Une fois appairé, les sondes du hub peuvent piloter les prises. Le Power Center ne retient que le type de sonde qu'une prise suit ; la sonde elle-même et les seuils sont stockés sur le hub. Deux services permettent à une carte ou à une automatisation de lire ce côté :

- `redsea.get_control_probes` — les sondes d'un hub (identité et valeurs actuelles), par son identifiant matériel
- `redsea.get_control_subscriptions` — les règles que le hub applique aux prises de son Power Center, par son identifiant matériel

Supprimer une prise sur le Power Center n'efface que sa moitié d'une règle de sonde : le bouton **Désabonner prise N** du hub efface l'autre moitié.

## Mode des prises et prises pilotées par capteur
Le mode d'une prise (off / on / schedule / sensor) et ses réglages de programme/seuil capteur (par ex. « allumer cette prise si la température locale descend sous 24 °C ») se configurent depuis [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), comme pour les [ports du hub](reefcontrol.fr.md#modes-des-ports-et-des-prises).

Chaque prise expose une entité `sensor.socket_N_mode` pour les automatisations : son état est le mode courant de la prise, et ses attributs portent le `schedule` actuel et (en mode sensor) le `sensor_config`, marqué par `sensor_source` : `local` pour la sonde propre au Power Center, `control` pour une règle portée par le hub appairé.

Une prise pilotée par un programme ou une sonde peut être forcée à l'arrêt à la main : son mode indique alors `off`, tandis que le capteur **mode précédent** garde le mode automatique vers lequel elle reviendra.

Le device quitte automatiquement son état initial « setup » dès que la première prise est configurée, comme le fait l'application ReefBeat — aucune action manuelle nécessaire.

---

[← Retour à la page principale](README.fr.md)
