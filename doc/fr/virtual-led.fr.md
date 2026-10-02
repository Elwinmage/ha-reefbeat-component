[← Retour à la page principale](README.fr.md)

# LED virtuelle
Une LED virtuelle est un **groupe** de ReefLED, comme les LED « groupées »
de l'application ReefBeat : ses rampes se pilotent comme une seule.

- Créez un périphérique virtuel depuis le panneau d'intégration, puis
  utilisez le bouton de configuration : choisissez les LED (deux au moins,
  une LED n'appartient qu'à un seul groupe), puis leur ordre. Une nouvelle
  LED virtuelle démarre avec les rampes déjà groupées dans l'application
  ReefBeat, dans l'ordre de l'application.
- Vous ne pouvez utiliser les Kelvin et l'intensité pour contrôler vos LED que si vous avez une G2 ou un mix de G1 et G2.
- Vous pouvez utiliser à la fois les Kelvin/Intensité et Blanc&Bleu si vous n'avez que des G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

## Ce que partage le groupe
Une valeur partagée réglée sur la LED virtuelle, ou sur l'une de ses rampes,
est appliquée à toutes les rampes du groupe : canaux manuels, kelvin /
intensité, mode, minuteur, programmations, acclimatation, phase lunaire et
[programme météo](reefled.fr.md#programme-météo). Ce qui appartient à une rampe reste sur la
rampe : nom, Wi-Fi, cloud, firmware, identification, réinitialisation…

Comme dans l'application, une écriture de groupe est refusée quand l'une des
rampes n'est pas chargée, ne répond pas, ou est dans un mode que le groupe
ne peut pas piloter (éteinte, ou tenue par un raccourci) : rien n'est
envoyé, les rampes restent donc synchronisées, et l'erreur nomme les rampes
en cause. Une rampe mise hors service dans l'application est laissée de côté
pour les écritures, les vérifications et le lever décalé. Le blanc / bleu ne
peut pas être réglé sur un groupe contenant une G2 : utilisez kelvin /
intensité.

## Lever de soleil décalé
Comme dans l'application, les rampes d'un groupe peuvent commencer leur
journée l'une après l'autre :

| Entité | Rôle |
| ------ | ---- |
| `switch` Lever de soleil décalé | Décale le lever de soleil des rampes du groupe |
| `number` Délai du lever de soleil décalé | Minutes entre deux rampes, de 1 à 15 (10 par défaut) |

Chaque rampe commence sa journée `délai × position` minutes plus tard (la
première rampe du groupe n'est pas retardée). La valeur est écrite dans le
Décalage du lever de soleil de chaque rampe, à nouveau dès que les rampes du
groupe ou leur ordre changent ; une rampe qui quitte le groupe revient à 0.

## Les rampes du groupe
Le `sensor` LED liées, sur la LED virtuelle et sur chaque
rampe d'un groupe, donne le nombre de rampes et, dans son attribut `leds`,
leur liste dans l'ordre du groupe : `hwid`, `name`, `model`, `g2`, `offset`
(décalage du lever en minutes, vide pour une rampe sans `/offset`) et
`entry_id`. ha-reef-card s'en sert pour lister les rampes.

## Synchronisation avec l'application ReefBeat
Avec un compte cloud ReefBeat ([API Cloud](README.fr.md#ajout-de-lapi-cloud)), un groupe dont les
rampes sont d'un seul modèle, dans un seul aquarium et sur un seul compte
est le même groupe dans l'application : le groupe, son ordre et son lever
décalé sont écrits dans le cloud, ou repris de l'application, selon le côté
qui a changé depuis la dernière synchronisation.

Un groupe de l'application qu'aucune LED virtuelle ne pilote (deux rampes au
moins chargées dans Home Assistant) est proposé comme nouvelle LED virtuelle
dans les appareils « Découverts », avec ses rampes dans l'ordre de
l'application ; « Ignorer » le laisse ignoré.

Quand une décision vous revient, une réparation est signalée (Paramètres >
Système > Réparations) :

| Réparation | Que faire |
| ---------- | --------- |
| Aucun compte cloud ReefBeat | L'application pourrait porter le groupe mais aucun compte cloud ne liste ses rampes : ajoutez le compte (la réparation disparaît d'elle-même), ou gardez le groupe dans Home Assistant uniquement |
| LED groupées dans l'application ReefBeat | Le groupe contient plusieurs modèles, que l'application ne sait pas grouper, et des rampes sont encore groupées dans l'application : dégroupez-les là-bas ; le groupe vit alors dans Home Assistant uniquement |
| Modifié dans Home Assistant et dans l'application ReefBeat | Les deux côtés ont changé depuis la dernière synchronisation : choisissez le groupe à garder |

---

[← Retour à la page principale](README.fr.md)
