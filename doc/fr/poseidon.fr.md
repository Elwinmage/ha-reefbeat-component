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
| Un appareil pointe vers le relais mais ne s'y connecte jamais (il a gardé sa session avec Red Sea) | Reconnecté au bout de 2 minutes : repointé vers Red Sea puis vers le relais, deux fois au plus |

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

Familles fusionnées à ce jour, d'après les relevés espion :

| Famille | Fusionné |
|---|---|
| ReefControl Power | états, télémétrie ; l'état des prises est calculé depuis leurs programmes, comme le fait l'app ReefBeat |
| ReefDose | états, télémétrie ; un `dosing-log` (fin d'une dose) le fait relire, pour sa file de dosage, de même que minuit (00:01, heure de Home Assistant), quand la file du nouveau jour remplace celle du jour qui finit |
| ReefMat | états, télémétrie, `rolling-log` (fin d'une avance) |
| ReefLED | télémétrie |

Pour les autres familles, *Shadow* ne fait que comparer, et *Poseidon* relit
l'appareil chaque fois qu'il pousse un état. *Poseidon* le relit aussi quand un
état dit quelque chose que son fusionneur ne sait pas écrire (un réglage
inconnu, un programme de ReefDose, poussé sans ses intervalles). Cette relecture
comprend les sources de configuration : ce que l'app modifie, ce sont surtout
des réglages, que le relevé ne relit jamais.

Un ReefControl Power sans sonde de température ni prise pilotée par un
capteur, et une ReefDose (sa file de dosage relue après chaque dose et à
minuit), ont tout ce qui change poussé : en stratégie *Poseidon*, ils ne sont
relevés que tous les *Intervalle du relevé de sécurité*.

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
- **Intervalle du relevé de sécurité**, en minutes (60 par défaut) : le relevé
  d'un appareil dont les messages poussés couvrent tout ce qui change, et la
  fréquence de lecture du `/cloud` d'un appareil qui échange via le relais.
- **Signaler les messages inattendus** (activé par défaut) : voir
  [Messages inattendus](#messages-inattendus).
- **Chercher les signalements existants sur GitHub** (activé par défaut) :
  seule la signature d'un message inattendu est envoyée.
- **Retenir les commandes d'écriture du cloud à la connexion** (activé par
  défaut) : voir [Garde à la connexion](#garde-à-la-connexion).
- **Clef du watchdog** : 16 caractères, proposée tant qu'aucune n'est définie.
  Un watchdog sur une autre machine (autonome, ou dans
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup))
  demande au relais s'il est vivant, et remet les appareils en mode normal
  quand il ne l'est pas. Recopiez cette clef dans sa configuration ; laissez-la
  vide pour ne répondre à aucun watchdog.

## Messages inattendus

Chaque message qui traverse le relais est comparé à ce que l'on connaît de la
famille de l'appareil : un paquet ou un topic MQTT inconnu, une commande du
cloud vers un endpoint inconnu, un état ou une télémétrie avec un champ
nouveau, manquant ou d'un autre type. La première occurrence est écrite dans
`/config/redsea/poseidon/logs/anomalies.jsonl`, anonymisée (identifiants, noms,
adresses réseau, clefs retirés) ; une commande inconnue attend 5 secondes ce
que l'appareil répond et pousse, écrit avec elle.

Chacun a une signature, la même pour tous les utilisateurs. Les issues du dépôt
sont cherchées par cette signature, et une réparation dit quoi faire : le
signaler (une issue GitHub pré-remplie, envoyée par vous seul), suivre le
signalement ouvert, passer à la version qui le prend en charge, ou lire le
signalement fermé. Un champ nouveau de télémétrie ne crée une réparation que si
la recherche n'a trouvé aucun signalement.

## Garde à la connexion

À chaque connexion d'un appareil, le cloud Red Sea lui renvoie sa propre copie
des réglages de l'appareil. Quand cette copie n'est pas à jour, l'appareil perd
ses réglages actuels : une ReefWave a perdu tout son programme ainsi. Pendant
les 30 premières secondes de chaque connexion via le relais, les commandes
d'écriture du cloud sont donc retenues (ses lectures passent).

Les restaurations connues (tête de nourrissage d'une ReefDose, groupe et
programme d'une ReefWave) sont retenues sans rien dire. Toute autre commande
d'écriture retenue crée une réparation qui la liste : si vous avez modifié
quelque chose dans l'app ReefBeat à ce moment précis, refaites-le.

## Événements

### `redsea_dose`

Émis quand une ReefDose en mode Poseidon (quelle que soit la stratégie) termine
une dose, programmée ou manuelle, d'après son `dosing-log`. Une dose poussée
deux fois (après une reconnexion) n'est émise qu'une fois.

| Champ | Contenu |
|---|---|
| `device_id` | l'appareil dans Home Assistant |
| `name` | son nom |
| `head` | numéro de la tête |
| `supplement`, `brand` | tels que l'appareil les donne |
| `dose_type` | `scheduled` ou `manual` |
| `volume` | volume dosé, en mL |
| `started_at` | début de la dose, d'après la file de dosage relevée avant elle (heure locale de l'appareil) ; pour une dose qui n'y était pas (celle de minuit, une manuelle depuis l'app), estimé d'après le débit de la tête ; `null` tant que moins de 3 doses de la tête ont une durée mesurée |
| `ended_at` | fin de la dose (heure locale de l'appareil) |
| `duration_s` | `ended_at` − `started_at`, `null` sans début |
| `start_estimated` | `true` quand `started_at` (et `duration_s`) sont estimés : volume ÷ débit de la tête (ses 20 dernières doses de durée mesurée) |

Rien n'est poussé quand une dose commence : son début est l'heure que lui
donnait la file de dosage. La dose de minuit n'est dans aucune file (celle du
jour qui finit est vide à ce moment, celle du nouveau jour commence après
elle) : son début est estimé.

### Historique des doses

Chaque dose est aussi gardée, par tête, 30 jours (5000 doses au plus), malgré
les redémarrages :

- chaque tête d'une ReefDose a un capteur **Dernière dose** (sur l'appareil
  de la tête), disponible seulement quand le doseur est en mode Poseidon : son
  état est la fin de la dernière dose, ses attributs le volume, le type, le
  début, la durée et le supplément ; l'enregistreur les garde comme pour tout
  capteur ;
- l'action `redsea.get_doses` renvoie les doses, les plus récentes d'abord :
  `device_id` (le doseur, une de ses têtes, ou son entrée de configuration),
  et en option `head`, `days`, `limit` ;
- la ha-reef-card les montre dans la boîte de dialogue de configuration
  d'une tête (**Historique des doses**).

```yaml
automation:
  - alias: Journal des doses
    triggers:
      - trigger: event
        event_type: redsea_dose
    actions:
      - action: logbook.log
        data:
          name: "{{ trigger.event.data.name }}"
          message: >-
            tête {{ trigger.event.data.head }}
            ({{ trigger.event.data.supplement }}) :
            {{ trigger.event.data.volume }} mL,
            {{ trigger.event.data.dose_type }},
            {{ trigger.event.data.started_at }} → {{ trigger.event.data.ended_at }}
```

## Messages de l'app ReefBeat

Les capteurs **Dernier message** et **Dernière alerte** (et l'historique des
messages) viennent des réponses des appareils aux envois de Home Assistant,
qui restent en HTTP dans tous les modes. Les commandes de l'app ReefBeat (ou
du cloud) arrivent à l'appareil par MQTT : en mode Poseidon (toute
stratégie), la réponse de l'appareil à chaque commande d'écriture
(`command-response`, même `uuid`) alimente les mêmes capteurs, comme le
ferait une réponse HTTP :

- un `message` (`settings updated successfully`, `head settings successfully
  saved`…) devient le dernier message ;
- une `alert` (`NoMoreDoseAlert`…), `"success": false` ou un statut d'erreur
  devient la dernière alerte.

Les lectures de l'app (`GET`) ne portent pas de message : elles sont
ignorées. L'attribut `origin` des deux capteurs, et de chaque entrée de
l'historique (action `redsea.get_messages`), dit d'où il vient : `ha` (un
envoi de Home Assistant) ou `reefbeat` (une commande de l'app ou du cloud).
La ha-reef-card l'affiche après la date.

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
