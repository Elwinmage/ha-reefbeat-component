[← Retour à la page principale](README.fr.md)

# Mode Poseidon

<p align="center">
<img src="../img/poseidon/poseidon.png" alt="Poseidon" width="240">
</p>

Le mode Poseidon place un relais entre vos appareils ReefBeat et le broker MQTT
de Red Sea, dans Home Assistant. Un appareil en mode Poseidon se connecte à
Home Assistant au lieu de `mqtt.reef-beat.com`, et Home Assistant transmet son
trafic à Red Sea sans le modifier : l'app ReefBeat continue de fonctionner.

> [!WARNING]
> Le mode Poseidon est expérimental. Pour l'instant il relaie et observe le
> trafic : l'intégration lit toujours les appareils en les interrogeant.

## Ajouter Poseidon

*Paramètres > Appareils et services > Red Sea > Ajouter une entrée > Mode Poseidon*

- **Port d'écoute** : le premier port libre à partir de 1884 est proposé (1883
  et 8883, les ports MQTT habituels, sont sautés). Il est revérifié à la
  validation et à chaque démarrage du relais : si un autre service l'a pris,
  une alerte de réparation le signale et les appareils ne sont pas touchés.
- **Adresse de Home Assistant** : l'adresse IPv4 par laquelle les appareils
  joignent Home Assistant.
- **Compte cloud** : le compte cloud ReefBeat qui sert à récupérer les clefs
  des appareils. Un compte cloud est obligatoire.

## Ajouter des appareils

*Poseidon > Configurer > Ajouter des appareils*

Chaque appareil de l'intégration est listé avec son statut :

| Statut | Signification |
|---|---|
| Cochable | Ses clefs sont connues : il passe tout de suite en mode Poseidon |
| Cochable, 🔑 | Ses clefs doivent d'abord être récupérées (voir ci-dessous) |
| Déjà en mode Poseidon | Rien à faire |
| Sans identifiants cloud | Rattaché à un aquarium local : pas de mode Poseidon possible |
| Absent du compte cloud | Ses clefs ne peuvent pas être récupérées avec ce compte |
| Injoignable | Ne répond pas |

> [!CAUTION]
> **La récupération des clefs est destructive.** Un appareil ne donne pas ses
> clefs : pour les obtenir, il est supprimé du cloud ReefBeat puis recréé.
> - il est détaché de son aquarium, et l'app peut demander de le réappairer ;
> - les programmes, préréglages et l'historique gardés pour lui dans le cloud
>   peuvent être perdus ;
> - sa configuration est sauvegardée avant et comparée après : les ReefRun et
>   ReefWave retrouvent la leur automatiquement, pour les autres appareils ce
>   qui a changé est listé dans une notification (la configuration sauvegardée
>   reste dans `/config/redsea/poseidon/snapshots/`).
>
> La récupération se fait une fois par appareil : Home Assistant garde les
> clefs, même si Poseidon est supprimé.

## Le switch Poseidon

Chaque appareil dont les clefs sont connues a un switch **Mode Poseidon** sur
sa page :

- **activé** : l'appareil parle à Red Sea à travers Home Assistant ;
- **désactivé** : l'appareil parle directement à Red Sea (mode normal).

Son état est lu sur l'appareil lui-même. Ses attributs :

| Attribut | Signification |
|---|---|
| `connection_state` | État de connexion indiqué par l'appareil |
| `last_up` / `last_down` | Dernier trafic appareil → Red Sea / Red Sea → appareil |
| `silent` | En mode Poseidon, mais rien n'est passé par le relais pendant le délai des réglages |

Un appareil silencieux lève aussi une alerte de réparation, qui disparaît
d'elle-même quand son trafic reprend. Un appareil silencieux n'est jamais remis
en mode normal automatiquement.

## Ce qui se passe quand

| Événement | Appareils |
|---|---|
| Redémarrage de Home Assistant, rechargement de Poseidon | Laissés tels quels : ils se reconnectent quand le relais revient |
| Poseidon désactivé ou supprimé | Tous remis en mode normal |
| Un appareil ne peut pas être remis en mode normal | Nommé dans une notification |

On ne passe en mode Poseidon que sur votre décision. Toute bascule automatique
ramène au mode normal.

## Stratégies

Ce que fait Home Assistant d'un appareil en mode Poseidon. Chaque appareil a un
select **Stratégie Poseidon** à côté de son switch ; les réglages donnent la
valeur par défaut.

| Stratégie | Relevé | États poussés | Fichier |
|---|---|---|---|
| *Espion* | inchangé | enregistrés, comparés au relevé suivant | `spy.jsonl` |
| *Shadow* | inchangé | fusionnés dans les données de l'appareil, comparés au relevé suivant | `shadow.jsonl` |
| *Poseidon* | toutes les N minutes | utilisés ; l'appareil est relu à chaque état tant que sa famille ne sait pas être fusionnée | — |

> [!NOTE]
> Aucune famille d'appareils ne sait encore être fusionnée : la fusion s'écrit à
> partir des fichiers espion. D'ici là, *Shadow* ne fait que comparer, et
> *Poseidon* relit l'appareil chaque fois qu'il pousse un état.

### Espion

`/config/redsea/poseidon/logs/spy.jsonl` (rotation à 10 Mo, 5 fichiers gardés)
contient, avec la même horloge :

| `kind` | Enregistrement |
|---|---|
| `publish`, `control` | une trame entre l'appareil et Red Sea, dans les deux sens, déchiffrée |
| `http` | une requête HTTP envoyée par Home Assistant à l'appareil : méthode, endpoint, statut (0 = pas de réponse), durée, données ; `origin` vaut `integration` ou `poseidon` (ses lectures de `/cloud` toutes les 60 s) |
| `compare` | un état poussé face au relevé suivant, chaque valeur `same`, `differs` ou `unknown` |
| `mark` | la stratégie ou la pause a changé |

Un appareil en mode espion a aussi un switch **Pause du relevé** : plus aucune
requête ne lui est envoyée, lectures de `/cloud` de Poseidon comprises, donc
ce qu'il pousse alors, il le pousse de lui-même. La pause ne survit pas à un
redémarrage.

Relevé conseillé, par appareil (horloges des hôtes Home Assistant
synchronisées, même fuseau horaire) :

1. 30 minutes sans aucun relevé : tout autre Home Assistant qui lit l'appareil
   arrêté, la pause activée ;
2. 30 minutes avec le relevé seul (pause désactivée) ;
3. des actions à heures notées : depuis l'app ReefBeat, depuis Home Assistant,
   sur l'appareil lui-même ;
4. si un autre Home Assistant relève l'appareil, ses requêtes s'ajoutent avec
   l'action `logger.set_level`, `custom_components.redsea.reefbeat.api: debug`.

## Réglages

*Poseidon > Configurer > Réglages de Poseidon*

- **Stratégie par défaut** : celle des appareils en mode Poseidon qui n'en ont
  pas une à eux (voir [Stratégies](#stratégies)). *Espion* par défaut.
- **Intervalle du relevé en stratégie Poseidon**, en minutes (10 par défaut).
- **Mode debug** : chaque trame qui traverse le relais est écrite déchiffrée
  dans `/config/redsea/poseidon/logs/poseidon.jsonl` (rotation à 10 Mo, 5
  fichiers gardés). Les données sont en clair dans ce fichier.
- **Délai avant qu'un appareil soit silencieux**, en minutes (10 par défaut).
- **Clef du watchdog** : 16 caractères, proposée tant qu'aucune n'est définie.
  Un watchdog sur une autre machine (autonome, ou dans
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup))
  demande au relais s'il est vivant, et remet les appareils en mode normal
  quand il ne l'est pas. Recopiez cette clef dans sa configuration ; laissez-la
  vide pour ne répondre à aucun watchdog.

## Exporter et importer les clefs

*Poseidon > Configurer > Exporter les clefs* donne un lien de téléchargement de
toutes les clefs connues, valable 5 minutes. Le fichier est généré au clic,
jamais écrit dans `/config` ; il est au format de la CLI (`keystore.json`) et
contient les clefs en clair : gardez-le en lieu sûr. L'action
`redsea.poseidon_export`, pour les automatisations, écrit le même fichier dans
`/config/redsea/poseidon/keystore-<date>.json`, lisible par son seul
propriétaire.

*Poseidon > Configurer > Importer des clefs* demande un tel fichier et l'envoie
depuis votre navigateur. Un appareil n'est remplacé que par un enregistrement
plus récent, les appareils sans clefs sont ignorés, et les appareils importés
ont tout de suite leur switch.

## Script de secours

*Poseidon > Configurer > Script de secours* donne un lien de téléchargement
(5 minutes) vers `poseidon_rescue.py` : un script qui remet les appareils sur
le broker Red Sea sans Home Assistant, pour quand il ne peut plus le faire
(arrêté, relais en panne, intégration supprimée). Il tourne sur n'importe quel
ordinateur du réseau des appareils avec Python 3.8 ou plus, rien d'autre à
installer :

```bash
python3 poseidon_rescue.py --dry-run   # ce qui serait fait, rien n'est changé
python3 poseidon_rescue.py             # les appareils sur le relais, après confirmation
```

| Option | Usage |
|---|---|
| `--ip HWID=IP` | un appareil a changé d'adresse depuis le téléchargement |
| `--scan CIDR` | où chercher les appareils qui ont changé d'adresse (répétable) |
| `--no-scan` | ne jamais les chercher |
| `--only HWID` | un seul appareil (hwid ou nom, répétable) |
| `--all` | tous les appareils, quel que soit leur broker actuel |
| `--keystore keystore.json` | un export du keystore au lieu des appareils intégrés |
| `--yes` | sans confirmation |

Rien n'est écrit dans un appareil avant qu'il ait prouvé être le bon : son
`hwid`, lu dans `/device-info`, doit correspondre. Un appareil qui ne répond
plus à son adresse, ou dont l'adresse est désormais celle d'un autre, est
cherché sur le réseau : le /24 de chaque adresse connue et de l'ordinateur qui
lance le script, ou les sous-réseaux `--scan`.

Chaque appareil reçoit la même séquence que depuis Home Assistant (désactiver,
écrire le broker et les clefs, réactiver), puis `/cloud` est relu pour vérifier.
Le script contient les clefs en clair : gardez-le en lieu sûr, et
retéléchargez-le après avoir ajouté des appareils.
