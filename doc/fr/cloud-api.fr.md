[← Retour à la page principale](README.fr.md)

# API Cloud
L'API Cloud permet d'obtenir les informations utilisateur, la bibliothèque de vagues, de suppléments et de LEDs, d'être notifié en cas de [nouvelle version d'un microgiciel](README.fr.md#mise-à-jour-du-microgiciel) et d'envoyer des commandes à ReefWave lorsque le mode « [Cloud ou Hybride](reefwave.fr.md#reefwave) » est sélectionné.
Les paramètres des vagues et des LEDs sont triés par aquarium.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Image">
</p>

>[!TIP]
> Il est possible de désactiver la récupération de la liste des suppléments via l'interface de configuration du périphérique API Cloud.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Image">

>[!TIP]
> **Simulateur.** Pour utiliser le compte simulé d'un
> [reefbeat-devices-simulator](https://github.com/Elwinmage/reefbeat-devices-simulator)
> (ses rampes et leur bibliothèque de programmations, sans toucher à votre
> vrai compte), créez le fichier-drapeau local (git-ignoré, ne jamais le
> commiter) :
> ```bash
> cp custom_components/redsea/simulator_enabled.example custom_components/redsea/.simulator_enabled
> ```
> Redémarrez Home Assistant : le formulaire du compte demande alors aussi le
> **serveur cloud** (`cloud.reef-beat.com` par défaut). Donnez l'adresse du
> simulateur (son appareil `CLOUD`, par ex. `192.168.0.251`) ; tous les
> identifiants sont acceptés.
***

---

[← Retour à la page principale](README.fr.md)
