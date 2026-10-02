[← Retour à la page principale](README.fr.md)

# ReefRun :
- Réglage de la vitesse de la pompe
- Gestion du sur-écrémage
- Gestion de la détection de godet plein
- Modification possible du modèle d'écrémeur

<p align="center">
<img src="../img/rsrun_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="../img/rsrun_main_sensors.png" alt="Image">
<img src="../img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="../img/rsrun_main_conf.png" alt="Image">
<img src="../img/rsrun_main_diag.png" alt="Image">
</p>

### Pompes
<p align="center"><img src="../img/rsrun_ctrl.png" alt="Image">
<img src="../img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="../img/rsrun_sensors.png" alt="Image">
<img src="../img/rsrun_diag.png" alt="Image">
</p>

### Tâches de maintenance
Les tâches sont rattachées au sous-appareil pompe et dépendent de son type.

| Tâche | Pompe | Défaut | Plage |
| ----- | ----- | ------ | ----- |
| Nettoyer moteur et rotor | Remontée | 4,5 mois | 2 – 7 mois |
| Nettoyer la crépine d'aspiration | Remontée | 6 semaines | 3 – 9 semaines |
| Nettoyer venturi et tuyau d'air | Écumeur | 5 semaines | 3 – 7 semaines |
| Nettoyer le rotor de l'écumeur | Écumeur | 4,5 mois | 2 – 7 mois |
| Calibrer la sonde de coupelle pleine | Écumeur | 4 semaines | 2 – 6 semaines |
| Calibrer la sonde de sur-écumage | Écumeur | 4 semaines | 2 – 6 semaines |

Les deux tâches de calibration sont également surveillées par le blueprint
d'alertes, qui compare la date de dernière calibration remontée par l'appareil à
l'intervalle défini ici. Voir la section [Maintenance](maintenance.fr.md#maintenance).

### Clé de démontage du rotor

La tâche *Nettoyer le rotor de l'écumeur* ci-dessus impose de dévisser le corps
de pompe, qui n'offre pratiquement aucune prise une fois mouillé. Une clé
imprimable en 3D pour cette opération, avec une vidéo de mise en œuvre, est
disponible ici : [Clé pour rotor de DC Skimmer Red Sea](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

---

[← Retour à la page principale](README.fr.md)
