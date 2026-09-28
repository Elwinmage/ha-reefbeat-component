[← Retour à la page principale](README.fr.md)

# ReefControl:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_devices.png" alt="Image">
</p>

Le hub ReefControl (RSCONTROLPRO / RSCONTROLLITE) lit les sondes ReefSense branchées sur ses boîtiers d'extension, pilote ses ports 12V DC (2 sur le Pro, 1 sur le Lite) et, une fois appairé, les prises d'un [ReefControl-Power](reefcontrol-power.fr.md#reefcontrol-power).

- **Sondes ReefSense** — pH, ORP, salinité (EC), température, ATO (niveau d'eau) et fuite : valeur et niveau (souhaité / acceptable / danger), statut, nom, uid, dates de dernière installation et de dernier étalonnage, et température intégrée des sondes pH, EC et ATO. Chaque entité de sonde porte les attributs `probe_uid`, `probe_type` et `probe_index`, et les capteurs de mesure un attribut `ranges` (`[acceptable_low, desired_low, desired_high, acceptable_high]`).
- **Sondes de salinité** — capteurs de conductivité, de salinité (ppt) et de densité, plus un select d'unité d'affichage.
- **Sondes de fuite** — état sec/mouillé, **origine de l'eau** (sec / eau de l'aquarium / eau osmosée) et conductivité mesurée, lues dès que la sonde détecte de l'eau.
- **Réglages par sonde** — plages souhaitée et acceptable (mesure principale et température intégrée), switches activée / buzzer / notifications / maintenance, et un bouton « Lire maintenant » qui récupère une mesure fraîche sans attendre la prochaine interrogation.
- **Étalonnage des sondes** — voir [plus bas](#étalonnage-des-sondes).
- **Buzzer** — buzzer de danger et buzzer de fuite (activation, fréquence, rapport cyclique), anti-rebond du danger, switch du détecteur de fuite ; état actif / acquitté du buzzer et sa cause.
- **Ports 12V** — nom modifiable, switch marche/arrêt, état, mode, type, consommation et un bouton « Désinstaller le port ». Le capteur `port_N_mode` porte en attributs toute la configuration du port, son programme et sa règle de sonde, pour qu'une carte puisse modifier le port (voir [Modes des ports et des prises](#modes-des-ports-et-des-prises)).
- **Appairage ReefControl-Power** — Power Center appairé, son état et sa liaison, boutons « Apparier le Power Center » / « Désapparier le Power Center », et un bouton « Désabonner prise » par prise du Power Center pilotée par une sonde du hub.
- **Ajout, remplacement ou suppression de sondes** depuis le menu d'options de l'intégration (voir [plus bas](#gestion-des-sondes-ajout--remplacement--suppression)).
- Les écritures s'affichent immédiatement (mise à jour optimiste), puis sont confirmées par une relecture de l'appareil.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_diag.png" alt="Image">
</p>

> [!TIP]
> La [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) dessine le hub, ses sondes, ses ports et le Power Center appairé, et pilote les étalonnages et les modes des ports en quelques clics.

## Gestion des sondes (ajout / remplacement / suppression)
Les sondes BLE (pH, ORP, EC, ATO, fuite, température) se gèrent depuis le menu **Options** de l'intégration, à l'image de l'application Red Sea :

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_probe_management.png" alt="Image">
</p>

- **Ajouter une sonde** : mettez la sonde en appairage, choisissez son type, puis confirmez pour lancer la détection. La sonde est configurée comme le fait l'application : une sonde de fuite, par exemple, est nommée `Leak <uid>` avec son buzzer, son détecteur de fuite et ses notifications activés.
- **Remplacer une sonde** : choisissez la sonde à remplacer, mettez une nouvelle sonde du même type en appairage, puis confirmez. La nouvelle sonde hérite de l'historique/des statistiques de l'ancienne.
- **Supprimer une sonde** : sélectionnez une ou plusieurs sondes, puis confirmez — cela supprime définitivement les entités de la sonde et leur historique.

> [!NOTE]
> Réinstaller une sonde réinitialise ses réglages sur le hub (une sonde ORP revient à ses plages d'usine). L'intégration relit la configuration des sondes dès qu'une sonde apparaît ou est réinstallée, depuis Home Assistant comme depuis l'application ReefBeat.

## Étalonnage des sondes
Chaque type de sonde s'étalonne comme dans l'application ReefBeat.

| Sonde | Comment | Entité / service |
| ----- | ------- | ---------------- |
| ORP | Plongez la sonde dans la solution d'étalonnage, puis réglez le nombre sur la valeur de la solution | `Étalonner {probe} (valeur de la solution)` |
| Température | Réglez le nombre sur la température réelle de l'eau où se trouve la sonde | `Étalonner {probe} (température réelle)` |
| Température intégrée (pH, EC, ATO) | Idem, pour le capteur de température intégré à la sonde | `Étalonner la température de {probe} (température réelle)` |
| pH | Deux points : pH 7, puis pH 10 (eau de mer) ou pH 4 (eau douce) | `redsea.probe_calibration` |
| Salinité (EC) | Un point, avec la valeur de la solution en mS/cm | `redsea.probe_calibration` |

Les **nombres à valeur de référence** (ORP et températures) affichent la mesure actuelle. Les régler sur la référence relit la sonde et décale son offset de `référence - mesure`, pour que la sonde lise ensuite la référence.

Les **étalonnages pH et EC** se font en plusieurs étapes et passent par le service `redsea.probe_calibration`, une étape par appel : `enter`, puis `point` pour chaque point d'étalonnage, `status` interrogé jusqu'à ce que le hub annonce la réussite ou l'échec (il renvoie entre-temps `calibration_status`, `time_left` et `stability_progress`), et enfin `exit`. La [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) enchaîne toute la séquence pour vous.

```yaml
action: redsea.probe_calibration
data:
  device_id: <config entry of the hub>
  probe_type: ph
  probe_uid: "0x00B39"
  action: point
  point: MID
  solution_value: 7.0
  solution_rated_temp: 25
```

La date du dernier étalonnage vient du hub : une sonde pH ou EC étalonnée depuis l'application ReefBeat, ou une sonde ORP vérifiée, marque sa tâche de maintenance comme faite à cette date.

## Fusion de température multi-sondes
Dès que deux sources de température ou plus sont présentes (la sonde de température dédiée et la température intégrée aux sondes EC/pH/ATO), ReefControl calcule une **température fusionnée** robuste à partir des mesures individuelles :

- **Température fusionnée** (`sensor`) : une valeur unique agrégée selon la méthode choisie — Médiane (par défaut), Moyenne, Minimum ou Maximum. Configurable via l'entité select **Méthode de fusion de température**.
- **Cohérence des températures** (`binary_sensor`) et **Écart de température** (`sensor`, diagnostic) : indiquent si les sources concordent dans la limite du **Seuil de cohérence de température** (configurable, 0,5 °C par défaut), et l'ampleur de l'écart le cas échéant.
- **Source d'anomalie de température** (`sensor`, diagnostic) : `OK` quand toutes les sources concordent, le nom de la ou des sondes suspectées de dériver ou de mal lire, ou `Inconnue` quand le désaccord ne peut être attribué à une sonde précise. Les attributs du capteur détaillent chaque source (valeur, variation sur 1 heure, statut).
- Un **switch de maintenance par sonde compatible température** : l'activer exclut temporairement cette sonde du calcul de fusion/cohérence/anomalie, pour que son nettoyage ou son étalonnage ne déclenche jamais de fausse alerte.
- Un **étalonnage sur la température réelle** (`number`) par sonde compatible température (voir [Étalonnage des sondes](#étalonnage-des-sondes)).

Ces entités n'apparaissent que lorsqu'au moins deux sources de température sont détectées.

## Modes des ports et des prises
Un port 12V du hub, comme une prise du Power Center, fonctionne dans l'un de quatre modes : **off**, **on**, **schedule** (programme) ou **sensor** (piloté par une sonde). Un port pas encore installé est en mode `setup` et refuse toute écriture tant qu'il n'est pas installé.

Ces réglages ne sont pas exposés en entités individuelles — avec plusieurs ports et prises et un jeu de seuils par type de sonde, cela ferait des dizaines d'entités rarement utilisées. Configurez-les depuis [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), qui enchaîne les mêmes appels que l'application ReefBeat en une seule action via le service `redsea.request` (voir les Services de l'intégration dans les Outils de développement de Home Assistant).

Le capteur `port_N_mode` porte tout de même ce dont une automatisation a besoin pour lire la configuration active : `config` (l'entrée complète du port, `power_on_percent` compris), `schedule` (relu sur le hub tant que le port est en mode programme) et `sensor_config` (la règle de sonde), avec `sensor_source: control`.

## Module osmolateur (kit ATO Red Sea)
Le kit ATO Red Sea — une pompe sur un port 12V et une sonde ATO — s'installe comme le fait l'assistant de l'application, depuis le menu **Options** de l'intégration :

1. **Ajouter une sonde** de type `ato` (elle est nommée `ATO Temp. <uid>`, d'après sa température, comme dans l'application).
2. **Installer le module osmolateur** : choisissez le port 12V libre, la sonde ATO, le volume du réservoir (L), la longueur et la hauteur du tuyau (cm, de la pompe au bac, la hauteur étant celle dont il monte au-dessus de la pompe), le remplissage automatique et le suivi du réservoir.

Le port devient alors de type `ato` et reçoit les entités du module :

| Entité | Type | Rôle |
| ------ | ---- | ---- |
| `Port N état osmolateur` | capteur | `OK`, ou le défaut signalé par le port : pompe absente, pompe bloquée, réservoir vide, délai de remplissage dépassé, fuite, défaut du port |
| `Port N défaut osmolateur` | capteur binaire | actif tant qu'un défaut arrête le module |
| `Port N pompe osmolateur` | capteur binaire | la pompe remplit (l'état du port la suit) |
| `Port N volume osmolateur du jour` / `restant` | capteur | mL |
| `Port N cause du dernier remplissage` | capteur | manuel, capteur de niveau… (diagnostic) |
| `Port N remplissage automatique`, `suivi du réservoir`, `notifications`, `journal de température` | interrupteur | `PUT /ato/configuration` |
| `Port N volume restant du réservoir` | nombre | le volume restant, à saisir après avoir rempli le réservoir (`POST /ato/update-volume`) |
| `Port N longueur` / `hauteur du tuyau osmolateur` | nombre | cm |
| `Port N débit osmolateur` | nombre | débit forcé de la pompe, de 0,2 à 4 L/min comme dans l'application ; 0 revient au débit par défaut |
| `Port N reprise osmolateur` | bouton | efface un défaut (disponible seulement s'il y en a un) |
| `Port N remplissage manuel` / `arrêt osmolateur` | bouton | d'après l'API de l'application, pas encore capturés |

Désinstaller le port (`Désinstaller le port N`, la carte ou l'application ReefBeat) retire le module et supprime aussitôt ses entités. Un module installé depuis l'application ReefBeat apparaît après un rechargement automatique.

## Tâches de maintenance
| Tâche | Sondes | Par défaut | Plage |
| ----- | ------ | ---------- | ----- |
| Nettoyer la sonde | Toutes | 30 jours | 2 – 8 semaines |
| Étalonner la sonde | pH | 3 mois | 2 – 4 mois |
| Étalonner la sonde | Salinité (EC) | 2 mois | 1 – 3 mois |
| Vérifier la sonde | ORP | 6 mois | 5 – 7 mois |
| Remplacer la sonde | pH, ORP | 12 mois | 9 – 18 mois |

Les tâches sont suivies **par sonde**, selon les recommandations officielles de Red Sea. Les sondes de température et de fuite n'ont pas de rappel d'étalonnage, et la cellule EC à 4 pôles n'est jamais remplacée selon un calendrier. Voir la section [Maintenance](maintenance.fr.md#maintenance).

---

[← Retour à la page principale](README.fr.md)
