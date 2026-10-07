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
