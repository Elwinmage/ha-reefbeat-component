[← Retour à la page principale](README.fr.md)

# ReefWave :
> [!IMPORTANT]
> Les appareils ReefWave sont différents des autres appareils ReefBeat. Ce sont les seuls appareils esclaves du cloud ReefBeat.<br/>
> Lorsque vous lancez l'application mobile ReefBeat, l'état de tous les appareils est interrogé et les données de l'application ReefBeat sont récupérées à partir de l'état de l'appareil.<br/>
> Pour ReefWave, c'est l'inverse : il n'y a pas de point de contrôle local (comme vous pouvez le constater dans l'application ReefBeat, vous ne pouvez pas ajouter un ReefWave à un aquarium déconnecté).<br/>
> <center ><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Les vagues sont stockées dans la bibliothèque utilisateur du cloud. Lorsque vous modifiez la valeur d'une vague, celle-ci est modifiée dans la bibliothèque cloud et appliquée à la nouvelle programmation.<br/>
> Il n'y a donc pas de mode local ? Pas si simple. Il existe une API locale cachée pour contrôler ReefWave, mais l'application ReefBeat ne détecte pas les modifications. Ainsi, l'appareil et HomeAssistant d'un côté, et l'application mobile ReefBeat de l'autre, seront désynchronisés. L'appareil et HomeAssistant seront toujours synchronisés.<br/>
> Maintenant que vous savez, faites votre choix !

> [!NOTE]
> Les vagues ReefWave ont de nombreux paramètres liés, et la plage de certains paramètres dépend d'autres paramètres. Je n'ai pas pu tester toutes les combinaisons possibles. Si vous trouvez un bug, vous pouvez créer un ticket [ici](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modes ReefWave
Comme expliqué précédemment, les appareils ReefWave sont les seuls à pouvoir être désynchronisés de l'application ReefBeat si vous utilisez l'API locale.
Trois modes sont disponibles : Cloud, Local et Hybride.
Vous pouvez modifier les paramètres de mode « Connexion au Cloud » et « Utiliser l'API Cloud » comme décrit dans le tableau ci-dessous.

<table>
<tr>
<td>Nom du mode</td>
<td>Commutateur Connexion au Cloud</td>
<td>Commutateur Utiliser l'API Cloud</td>
<td>Comportement</td>
<td>ReefBeat et HA sont synchronisés</td>
</tr>
<tr>
<td>Cloud (par défaut)</td>
<td>✅</td>
<td>✅</td>
<td>Les données sont récupérées via l'API locale. <br />Les commandes marche/arrêt sont également envoyées via l'API locale. <br />Les commandes sont envoyées via l'API cloud.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Les données sont récupérées via l'API locale. <br />Les commandes sont envoyées via l'API locale. <br />L'appareil est affiché comme « éteint » dans l'application ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybride</td>
<td>✅</td>
<td>❌</td>
<td>Les données sont récupérées via l'API locale. <br />Les commandes sont envoyées via l'API locale.<br />L'application mobile ReefBeat ne représente pas les valeurs des bonnes vagues si elles ont été modifiées via HA.<br/>Home Assistant les représente toujours.<br/>Vous pouvez modifier les valeurs depuis l'application ReefBeat et Home Assistant.</td>
<td>❌</td>
</tr>
</table>

Pour les modes Cloud et Hybride, vous devez lier votre compte cloud ReefBeat.
Créez d'abord une ["API cloud"](README.fr.md#ajout-de-lapi-cloud) avec vos identifiants, et c'est tout !
Le capteur « Lié au compte » sera mis à jour avec le nom de votre compte ReefBeat une fois la connexion établie.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Modification des valeurs actuelles
Pour charger les valeurs des vagues actuelles dans les champs d'aperçu, utilisez le bouton « Définir l'aperçu à partir de la vague actuelle ».
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
Pour modifier les valeurs des vagues actuelles, définissez les valeurs d'aperçu et utilisez le bouton « Enregistrer l'aperçu ».

Le fonctionnement est identique à celui de l'application mobile ReefBeat. Toutes les vagues ayant le même identifiant dans le planning actuel seront mises à jour.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

### Tâches de maintenance
| Tâche | Défaut | Plage |
| ----- | ------ | ----- |
| Nettoyer les cages de rotor | 2 mois | 1 – 3 mois |

Voir la section [Maintenance](maintenance.fr.md#maintenance).

---

[← Retour à la page principale](README.fr.md)
