[← Retour à la page principale](README.fr.md)

# ReefDose :
- Modification de la dose quotidienne
- Dose manuelle
- Ajout et suppression de suppléments
- Modification et contrôle du volume du récipient. Le réglage du volume du récipient est automatiquement activé ou désactivé en fonction du volume sélectionné.
- Activation/désactivation de la programmation par pompe
- Configuration des alertes de stock
- Délai de dosage entre les compléments
- Amorçage (Veuillez lire [ceci](#calibration-et-amorçage))
- Calibration (Veuillez lire [ceci](#calibration-et-amorçage))
- [Régulation du dosage](#régulation-du-dosage) : dosage assisté et saumure
- [Historique des doses](poseidon.fr.md#historique-des-doses), en mode Poseidon

<p align="center">
<img src="../img/rsdose_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="../img/rsdose_main_conf.png" alt="Image">
<img src="../img/rsdose_main_diag.png" alt="Image">
</p>

### Têtes
<p align="center">
<img src="../img/rsdose_ctrl.png" alt="Image">
<img src="../img/rsdose_sensors.png" alt="Image">
<img src="../img/rsdose_diag.png" alt="Image">
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
  <img src="../img/calibration.png" alt="Image">
</p>

### Régulation du dosage

Chaque tête a un select **Régulation du dosage** : *Désactivée*, *Dosage assisté* ou *Saumure (salinité)*. La [ha-reef-card](https://github.com/Elwinmage/ha-reef-card/blob/main/doc/fr/reefdose.fr.md#régulation-du-dosage) regroupe ses entités dans la fenêtre de configuration de la tête.

Le volume d'eau vient de **Volume d'eau du bac** quand vous le renseignez ; sinon de l'aquarium [ReefTank](https://github.com/Elwinmage/ha-reeftank-component) du doseur ; sinon de son aquarium cloud ReefBeat. Le capteur **Volume d'eau utilisé** indique lequel s'applique.

#### Dosage assisté

Vous fixez une cible (par exemple KH 8,4 dKH) et enregistrez vos résultats de test. D'après ces résultats et les volumes réellement dosés entre deux tests (le `/daily-log` du doseur), l'intégration estime ce que consomme le bac et **propose** une dose journalière. Rien n'est envoyé au doseur tant que vous ne l'appliquez pas.

1. Choisissez le **Paramètre régulé** (KH, calcium, magnésium, potassium, nitrate, phosphate, iode ou fer) et réglez la **Cible de régulation**.
2. Vérifiez la **Puissance du supplément** : ce que 1 mL fait monter le paramètre dans 100 L, comme indiqué sur le flacon. Elle est préremplie pour les suppléments dont l'étiquette la donne.
3. Après chaque test, saisissez la valeur dans **Résultat de test** et appuyez sur **Enregistrer le résultat de test**, ou appelez `redsea.record_measurement` (utile pour un test daté : `measured_at`).
4. Quand **État de la régulation** indique *Nouvelle dose proposée*, regardez **Dose journalière proposée** et appuyez sur **Appliquer la dose proposée** ou **Ignorer la dose proposée**.

La proposition correspond à ce que consomme le bac, plus une correction : l'écart à la cible réparti sur les jours de l'**Étalement de la correction**, rien à l'intérieur de la **Tolérance de régulation**. Elle s'écarte au plus de la **Variation max de dose** (20 % par défaut) de la dose actuelle, et un changement de moins de 5 % n'est pas proposé. Un test trop éloigné de ce qui était attendu donne *Nouveau test conseillé* au lieu d'une proposition.

> [!NOTE]
> Avec des têtes groupées (Red Sea Complete Reef Care), seule la tête 1 peut être régulée, en dosage assisté sur le calcium : le doseur en déduit les autres têtes.

#### Saumure

La tête contient une saumure, du sel dissous dans de l'eau : le supplément **DIY - Brine**, le seul régulé sur la salinité. Home Assistant lit un capteur de salinité (une sonde EC de ReefControl ou n'importe quel capteur, select **Capteur de salinité**) toutes les 10 minutes et envoie de petites doses manuelles pour garder sa moyenne sur 24 heures à la cible (35 ppt par défaut). Il utilise exprès des doses manuelles plutôt que le programme de la tête : quand Home Assistant est arrêté, rien n'est dosé, et la salinité ne fait que baisser lentement.

| Réglage | Défaut | Rôle |
| ------- | ------ | ---- |
| Cible de régulation | 35 ppt | Salinité à tenir |
| Concentration de la saumure | 200 g/L | Ce que vous avez préparé |
| Hausse max de salinité | 0,5 ppt/jour | Correction la plus rapide autorisée |
| Doses de saumure par jour | 12 | Répartition du volume quotidien |
| Tolérance du contrôle réfractomètre | 1 ppt | Écart accepté entre le contrôle et la sonde |

**Saumure prévue par jour** donne le volume prévu. Enregistrez chaque mois une lecture au réfractomètre comme résultat de test `salinity` : hors tolérance, la régulation se met en pause jusqu'à ce que la sonde soit recalibrée. Sans contrôle pendant 45 jours, la hausse autorisée par jour est divisée par deux.

**Alarme de régulation** s'active, et un événement `redsea_dose_regulation_alarm` est émis, quand la salinité est trop haute (la saumure ne peut pas la faire baisser), quand elle ne peut pas être ramenée à la cible, quand le capteur est perdu et quand une recalibration est nécessaire.

### Tâches de maintenance
| Tâche | Niveau | Défaut | Plage |
| ----- | ------ | ------ | ----- |
| Calibrer les têtes de dosage | Appareil | 90 jours | 80 – 120 jours |
| Remplacer têtes et tuyaux | Par tête | 15 mois | 11 – 19 mois |

Le remplacement est suivi **par tête** : changer la tête 2 ne remet pas à zéro
le compte à rebours des trois autres. Voir la section
[Maintenance](maintenance.fr.md#maintenance).

---

[← Retour à la page principale](README.fr.md)
