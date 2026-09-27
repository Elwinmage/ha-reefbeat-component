[← Retour à la page principale](README.fr.md)

# Maintenance

Au-delà du pilotage du matériel, l'intégration assure le suivi des **tâches de
maintenance récurrentes** de vos équipements : nettoyer le venturi d'un
écumeur, remplacer les tuyaux d'une pompe doseuse, changer le charbon actif du
ReefMat… C'est Home Assistant qui s'en souvient, plus vous.

Les tâches sont rattachées à l'appareil concerné, et au **sous-appareil**
lorsque c'est plus précis : une tête de ReefDose, une pompe de ReefRun. Un
ReefRun expose les tâches de la pompe de remontée sur la pompe 1 et celles de
l'écumeur sur la pompe 2, jamais l'inverse : la liste suit le type de pompe
remonté par l'appareil.

## Les trois entités d'une tâche

Chaque tâche crée trois entités, toutes rangées dans les catégories
*Configuration* et *Diagnostic* pour ne pas encombrer votre tableau de bord :

| Entité | Rôle |
| ------ | ---- |
| `button.<appareil>_<tâche>` | **Tâche réalisée.** L'appui enregistre la date du jour comme dernière réalisation et relance le compte à rebours. |
| `number.<appareil>_<tâche>_interval_<unité>` | **Intervalle.** Périodicité de la tâche, en jours, semaines ou mois selon le cas. |
| `switch.<appareil>_<tâche>_notify` | **Notifications.** Coupe l'alerte de retard de cette seule tâche, sans toucher à son échéance. |

Le bouton est l'entité qui porte l'état. Tout ce qui en découle est exposé en
attributs, ce qui suffit à construire un tableau de bord ou une automatisation :

| Attribut | Signification |
| -------- | ------------- |
| `last_reset` | Date ISO-8601 du dernier appui, ou `null` si jamais réalisée |
| `interval_days` | Intervalle courant, toujours normalisé en jours |
| `days_left` | Jours restants, négatif une fois l'échéance dépassée |
| `overdue` | `true` dès que `days_left` est négatif |
| `reef_role` | `maint_<clé_de_tâche>`, le marqueur stable servant à découvrir les tâches |

> [!TIP]
> C'est `reef_role` qui rend l'ensemble extensible : la carte et le blueprint
> d'alertes découvrent les tâches en cherchant cet attribut. Une tâche ajoutée
> dans une future version de l'intégration apparaît dans les deux sans aucune
> mise à jour de leur côté.

## Intervalles

Les intervalles par défaut reprennent les préconisations de Red Sea, en prenant
la médiane de la fourchette publiée. Chaque tâche définit aussi un minimum et un
maximum, imposés par l'entité `number` : vous pouvez adapter un intervalle à la
charge de votre bac, mais pas saisir une valeur aberrante.

Les intervalles sont affichés dans l'unité qui a du sens pour la tâche (semaines
pour un venturi, mois pour un rotor) et stockés en jours en interne, si bien
qu'un changement d'unité ne perd jamais de précision.

## Persistance

Dates et intervalles sont stockés par Home Assistant dans
`.storage/redsea_maintenance_<entry_id>`, un fichier par entrée de
configuration. Ils survivent aux redémarrages, aux rechargements de
l'intégration et aux reboots des appareils, et ne sont **jamais envoyés au cloud
Red Sea**. Supprimer l'entrée de configuration supprime le fichier avec elle.

## La vue maintenance de ha-reef-card

La carte compagnon [ha-reef-card](https://github.com/Elwinmage/ha-reef-card)
rassemble toutes les tâches de l'installation dans une vue dédiée, comme si la
maintenance était un appareil à part entière : une barre de progression par
tâche, colorée selon le temps restant, triable par équipement ou par échéance,
avec un bouton pour marquer la tâche comme faite, une cloche pour la mettre en
sourdine et un curseur en ligne pour changer son intervalle.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/maintenance_task.png" alt="Tâches de maintenance dans ha-reef-card">
</p>

## Notifications : le blueprint d'alertes

L'intégration ne notifie pas d'elle-même, et c'est volontaire : qui prévenir,
quand et comment vous regarde. Ce rôle revient au blueprint **ReefBeat watch**
livré avec le dépôt, qui couvre aussi les modes anormaux, les calibrations en
retard, les batteries faibles et les appareils injoignables.

### Installation

Cliquez sur le bouton ci-dessous et confirmez l'import dans Home Assistant :

[![Ouvrir votre instance Home Assistant et afficher la boîte de dialogue d'import de blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-reefbeat-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fredsea_alerts.fr.yaml)

Une version anglaise est disponible sous
[`redsea_alerts.en.yaml`](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/blueprints/automation/redsea_alerts.en.yaml).
Vous pouvez aussi copier le fichier dans
`config/blueprints/automation/redsea_alerts/` puis recharger les automatisations.

Créez ensuite une automatisation à partir du blueprint :
*Paramètres → Automatisations et scènes → Créer une automatisation →
Utiliser un blueprint → ReefBeat watch (redsea)*.

### Configuration

Seul le premier champ est obligatoire :

| Section | Rôle |
| ------- | ---- |
| **Cibles de notification** | Les appareils mobiles à prévenir, choisis dans le sélecteur d'appareils. Le service `notify.mobile_app_*` est résolu pour vous. Un canal de notification Android peut être précisé (`ReefBeat` par défaut). |
| **Maintenance en retard** | Alerte dès qu'une tâche dépasse son échéance. L'option *Respecter les interrupteurs de notification par tâche* (activée par défaut) fait obéir l'automatisation aux entités `switch.*_notify` : mettre une tâche en sourdine dans la carte fait donc aussi taire l'automatisation. |
| **Mode anormal** | Alerte quand un appareil quitte son mode attendu. `off_grace_minutes` (5 par défaut) évite les fausses alertes pendant un cycle de nourrissage ou une courte intervention manuelle. |
| **Calibration en retard** | Têtes de ReefDose et calibrations d'écumeur ReefRun. |
| **Délai de calibration des sondes (RSRUN)** | Sondes de coupelle pleine et de sur-écumage des écumeurs ReefRun. |
| **Message d'alerte de l'appareil** | Relaie les messages d'alerte émis par les appareils eux-mêmes. |
| **Batterie faible** / **Appareil injoignable** | Sans surprise. |

Chaque section se désactive indépendamment et dispose de sa propre **liste
d'exclusion** : un appareil en cours de test ne vous inonde pas d'alertes
pendant que les autres restent surveillés. L'automatisation tourne sur un cycle
de 5 minutes et prend en compte les appareils ajoutés ou retirés de
l'intégration au cycle suivant, sans rien modifier.

> [!NOTE]
> Le blueprint surveille **tous** les appareils de l'intégration et leurs
> sous-appareils. Il n'y a rien à déclarer quand vous ajoutez un nouvel appareil
> ReefBeat.

---

[← Retour à la page principale](README.fr.md)
