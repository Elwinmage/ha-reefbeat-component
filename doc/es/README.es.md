[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/commits/main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

<!-- [![Clones GitHub](https://img.shields.io/badge/dynamic/json?color=success&label=uniques-clones&query=uniques&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge) -->

# Presentación
***Gestión local de dispositivos HomeAssistant RedSea Reefbeat (sin nube): ReefATO+, ReefDose, ReefLed, ReefMat, ReefRun y ReefWave***

> [!TIP]
> ***Para editar la programación avanzada de ReefDose, ReefLed, ReefRun y ReefWave, debes usar la [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) (en desarrollo)***

> [!TIP]
> La lista de futuras implementaciones está disponible [aquí](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> La lista de errores está disponible [aquí](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***Si necesitas otros sensores o actuadores, no dudes en contactarme [aquí](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Si tus dispositivos no están en la misma subred que tu Home Assistant, por favor [lee esto](README.es.md#mi-dispositivo-no-se-detecta).

> [!CAUTION]
> ⚠️ Este no es un repositorio oficial de RedSea. Úsalo bajo tu propia responsabilidad.⚠️

# Compatibilidad

✅ Probado ☑️ Debería funcionar (Si tienes uno, ¿puedes confirmar que funciona [aquí](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))❌ Aún no compatible
<table>
<th>
<td colspan="2"><b>Modelo</b></td>
<td colspan="2"><b>Estado</b></td>
<td><b>Problemas</b> <br/>📆(Planificado) <br/> 🐛(Errores)</td>
</th>
<tr>
<td><a href="#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td><a href="#reefcontrol">ReefControl</a></td>
<td colspan="2">RSSENSE<br />Si tienes uno, contáctame <a href="https://github.com/Elwinmage/ha-reefbeat-component/discussions/8">aquí</a> para añadir su soporte.</td><td>❌</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROL.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE2.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"><a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
<td rowspan="6">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,RSLED90,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td>RSLED90</td><td>✅</td></tr>
<tr><td>RSLED160</td><td>✅ </td></tr>
<tr>
<td rowspan="3">G2</td>
<td>RSLED60</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g2.png"/></td>
</tr>
<tr><td>RSLED115</td><td>✅ </td></tr>
<tr><td>RSLED170</td><td>☑️</td></tr>
<tr>
<td rowspan="3"><a href="#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSMAT.png"/></td>
<td rowspan="3">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td colspan="2">RSMAT500</td><td>✅</td></tr>
<tr><td colspan="2">RSMAT1200</td><td>✅ </td></tr>
<tr>
<td><a href="#reefrun">ReefRun y DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td><td>☑️</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td colspan="2">RSWAVE45</td><td>✅</td></tr>
</table>

(*) Usuarios de ReefWave, por favor lee [esto](README.es.md#reefwave)

# Resumen
- [Instalación via HACS](README.es.md#instalación-via-hacs)
- [Funciones comunes](README.es.md#funciones-comunes)
- [ReefATO+](README.es.md#reefato)
- [ReefControl](README.es.md#reefcontrol)
- [ReefDose](README.es.md#reefdose)
- [ReefLED](README.es.md#reefled)
- [LED virtual](README.es.md#led-virtual)
- [ReefMat](README.es.md#reefmat)
- [ReefRun](README.es.md#reefrun)
- [ReefWave](README.es.md#reefwave)
- [API Cloud](README.es.md#api-cloud)
- [FAQ](README.es.md#faq)

# Instalación via HACS

## Instalación directa

Haz clic aquí para ir directamente al repositorio en HACS y haz clic en «Descargar»: [![Abre tu instancia de Home Assistant y abre un repositorio en la tienda de la comunidad Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Para la tarjeta compañera ha-reef-card que ofrece funciones avanzadas y ergonómicas, haz clic aquí para ir directamente al repositorio en HACS y haz clic en «Descargar»: [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Buscar en HACS
O busca «redsea» o «reefbeat» en HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Imagen">
</p>

# Funciones comunes

## Añadir un dispositivo
Al añadir un nuevo dispositivo, tienes cuatro opciones:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Imagen">
</p>

### Añadir la API Cloud
***Obligatorio para mantener los ReefWave sincronizados con la aplicación móvil ReefBeat*** (Leer [esto](README.es.md#reefwave)). <br />
***Obligatorio para recibir notificaciones de nuevas versiones de firmware*** (Leer [esto](README.es.md#actualización-de-firmware)).
- Información de usuario
- Acuarios
- Biblioteca de Waves
- Biblioteca de LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Imagen">
</p>

### Detección automática en red privada
Si no estás en la misma red, lee [esto](README.es.md#mi-dispositivo-no-se-detecta) y usa el modo [«Manual»](README.es.md#modo-manual).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Imagen">
</p>

### Modo manual
Puedes introducir la dirección IP o la dirección de red de tu dispositivo para la detección automática.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Imagen">
</p>

### Configurar el intervalo de análisis del dispositivo

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Imagen">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Imagen">
</p>

## Actualización en tiempo real

> [!NOTE]
> Es posible elegir si activar o no el modo Live_update_config. En este modo (antiguo modo predeterminado), los datos de configuración se recuperan continuamente junto con los datos normales. Para RSDOSE o RSLED, estas solicitudes HTTP voluminosas pueden tardar mucho tiempo (7-9 segundos). A veces el dispositivo no responde a la solicitud, por lo que se ha implementado una función de reintento. Cuando Live_update_config está desactivado, los datos de configuración solo se recuperan al inicio y cuando se solicitan mediante el botón «Obtener configuración». Este nuevo modo está activado por defecto. Puedes cambiarlo en la configuración del dispositivo. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Imagen">
</p>

## Actualización de Firmware
Puedes recibir notificaciones y actualizar tu dispositivo cuando haya una nueva versión de firmware disponible. Debes tener un componente [«API Cloud»](README.es.md#añadir-la-api-cloud) activo con tus credenciales y el interruptor «Usar la API Cloud» debe estar activado.
> [!TIP]
> La «API Cloud» solo es necesaria para obtener el número de versión de la nueva versión y compararlo con la versión instalada. Para actualizar el firmware, la API Cloud no es imprescindible.
> Si no usas la «API Cloud» (opción desactivada o componente API Cloud no instalado), no recibirás notificaciones cuando haya una nueva versión disponible, pero podrás usar el botón oculto «Forzar actualización de firmware». Si hay una nueva versión disponible, se instalará.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Imagen">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Imagen">
</p>

# ReefATO:
- Activar/desactivar el llenado automático
- Llenado manual
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Imagen">
</p>

# ReefControl:
Aún no compatible. Si tienes uno, contáctame [aquí](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8) para añadir su soporte.

# ReefDose:
- Modificar la dosis diaria
- Dosis manual
- Añadir y eliminar suplementos
- Modificar y controlar el volumen del recipiente. El ajuste del volumen del recipiente se activa o desactiva automáticamente según el volumen seleccionado.
- Activar/desactivar la programación por bomba
- Configuración de alertas de stock
- Retardo de dosificación entre suplementos
- Cebado (Por favor lee [esto](README.es.md#calibración-y-cebado))
- Calibración (Por favor lee [esto](README.es.md#calibración-y-cebado))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Imagen">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Imagen">
</p>

### Cabezales
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Imagen">
</p>

#### Calibración y cebado

> [!CAUTION]
> Debes seguir exactamente el orden siguiente (El uso de [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) es más seguro).<br /><br />
> <ins>Calibración</ins>:
>  1. Coloca la probeta y pulsa "Start Calibration"
>  2. Indica el valor medido usando el campo "Dose of Calibration"
>  3. Pulsa "Set Calibration Value"
>  4. Vacía la probeta y pulsa "Test new Calibration". Si el valor obtenido es diferente de 4 mL, vuelve al paso 1.
>  5. Pulsa "Stop and Save Graduation"
>
> <ins>Cebado</ins>:
>  1. (a) Pulsa "Start Priming"
>  2. (b) Cuando el líquido fluya, pulsa "Stop Priming"
>  3. (1) Coloca la probeta y pulsa "Start Calibration"
>  4. (2) Indica el valor medido usando el campo "Dose of Calibration"
>  5. (3) Pulsa "Set Calibration Value"
>  6. (4) Vacía la probeta y pulsa "Test new Calibration". Si el valor obtenido es diferente de 4 mL, vuelve al paso 1.
>  7. (5) Pulsa "Stop and Save Graduation"
>
> ⚠️ ¡El cebado debe ir seguido obligatoriamente de una calibración (pasos 1 a 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Imagen">
</p>

# ReefLED:
- Obtener y configurar los valores de blanco, azul y luna (solo para G1: RSLED50, RSLED90, RSLED160)
- Obtener y configurar la temperatura de color, la intensidad y la luna (todos los LED)
- Gestionar la aclimatación. Los parámetros de aclimatación se activan o desactivan automáticamente según el interruptor de aclimatación.
- Gestionar las fases lunares. Los parámetros de fase lunar se activan o desactivan automáticamente según el cambio de fase lunar.
- Configurar el modo de color manual con o sin duración.
- Mostrar los parámetros del ventilador y la temperatura.
- Mostrar el nombre y el valor de los programas (con soporte de nubes). Solo para LED G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Imagen">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Imagen">
</p>

***

El soporte de temperatura de color para los LED G1 tiene en cuenta las especificidades de cada uno de los tres modelos.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Imagen">
</p>

***
## IMPORTANTE para las lámparas G1 y G2

### LÁMPARAS G2

#### Intensidad
Este tipo de LED garantiza una intensidad constante en toda la gama de colores, por lo que tus LED no aprovechan su plena capacidad en el centro del espectro. A 8 000 K, el canal blanco está al 100 % y el canal azul al 0 % (lo contrario a 23 000 K). A 14 000 K y con una intensidad del 100 % para las lámparas G2, la potencia de los canales blanco y azul es de aproximadamente el 85 %.
Esta es la curva de pérdida de los G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Imagen">
</p>

#### Temperatura de color
La interfaz de las lámparas G2 no admite toda la gama de temperatura. De 8 000 K a 10 000 K, los valores se incrementan en pasos de 200 K y de 10 000 K a 23 000 K en pasos de 500 K. Este comportamiento está contemplado: si eliges un valor incorrecto (por ejemplo, 8 300 K), se seleccionará automáticamente un valor válido (8 200 K en nuestro ejemplo). Por eso a veces puedes observar un pequeño reajuste del cursor al seleccionar el color en una lámpara G2: el cursor se reposiciona en un valor permitido.

### LÁMPARAS G1

Los LED G1 usan el control de canales blanco y azul, lo que permite plena potencia en toda la gama, pero no una intensidad constante sin compensación.
Por eso se ha implementado una compensación de intensidad.
Esta compensación garantiza el mismo [PAR](https://es.wikipedia.org/wiki/Radiaci%C3%B3n_fotosint%C3%A9ticamente_activa) (intensidad lumínica) independientemente de la temperatura de color elegida (en el rango de 12 000 a 23 000 K).
> [!NOTE]
> Como RedSea no publica los valores de PAR por debajo de 12 000 K, la compensación solo funciona en el rango de 12 000 a 23 000 K. Si tienes un LED G1 y un medidor PAR, puedes [contactarme](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) para añadir la compensación en el rango completo (9 000 a 23 000 K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Imagen">
</p>

En otras palabras, sin compensación, una intensidad de x % a 9 000 K no proporciona el mismo valor de PAR que a 23 000 K o 15 000 K.

Estas son las curvas de potencia:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Imagen">
</p>

Si deseas aprovechar al máximo la potencia de tu LED, desactiva la compensación de intensidad (opción predeterminada).

Si activas la compensación de intensidad, la intensidad lumínica será constante en todos los valores de temperatura, pero en el centro del rango no usarás la plena capacidad de tus LED (como en los modelos G2).

Recuerda también que, si activas el modo de compensación, el factor de intensidad puede superar el 100 % para los G1 si tocas manualmente los canales Blanco/Azul. ¡Puedes así aprovechar toda la potencia de tus LED!

***

# LED virtual
- Agrupa y gestiona los LED con un dispositivo virtual (crea un dispositivo virtual desde el panel de integración, luego usa el botón de configuración para vincular los LED).
- Solo puedes usar Kelvin e intensidad para controlar tus LED si tienes G2 o una combinación de G1 y G2.
- Puedes usar tanto Kelvin/Intensidad como Blanco y Azul si solo tienes G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Imagen">
</p>

# ReefMat:
- Interruptor de avance automático (activar/desactivar)
- Avance programado
- Valor de avance personalizado: permite seleccionar el valor de avance del rollo
- Avance manual
- Cambiar el rollo.
>[!TIP]
> Para un rollo nuevo completo, ajusta el «diámetro del rollo» al mínimo (4,0 cm). El tamaño se ajustará según tu versión de RSMAT. Para un rollo ya usado, introduce el valor en cm.
- Dos parámetros ocultos: modelo y posición, si necesitas reconfigurar tu RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Imagen">
</p>

# ReefRun:
- Ajustar la velocidad de la bomba
- Gestionar el sobre-espumado
- Gestionar la detección de vaso lleno
- Posibilidad de cambiar el modelo de espumador

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Imagen">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Imagen">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Imagen">
</p>

### Bombas
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Imagen">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Imagen">
</p>

# ReefWave:
> [!IMPORTANT]
> Los dispositivos ReefWave son diferentes de los demás dispositivos ReefBeat. Son los únicos dispositivos esclavos de la nube ReefBeat.<br/>
> Cuando inicias la aplicación móvil ReefBeat, se consulta el estado de todos los dispositivos y los datos de la aplicación ReefBeat se recuperan del estado del dispositivo.<br/>
> Para ReefWave, es al revés: no hay punto de control local (como puedes ver en la aplicación ReefBeat, no puedes añadir un ReefWave a un acuario desconectado).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Imagen"></center><br />
> Las olas se almacenan en la biblioteca de usuarios de la nube. Cuando modificas el valor de una ola, se modifica en la biblioteca de la nube y se aplica a la nueva programación.<br/>
> ¿Entonces no hay modo local? No es tan sencillo. Existe una API local oculta para controlar ReefWave, pero la aplicación ReefBeat no detecta los cambios. Así, el dispositivo y HomeAssistant por un lado, y la aplicación móvil ReefBeat por el otro, quedarán desincronizados. El dispositivo y HomeAssistant siempre estarán sincronizados.<br/>
> ¡Ahora que lo sabes, haz tu elección!

> [!NOTE]
> Las olas de ReefWave tienen muchos parámetros vinculados, y el rango de algunos parámetros depende de otros parámetros. No he podido probar todas las combinaciones posibles. Si encuentras un error, puedes crear un ticket [aquí](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modos ReefWave
Como se explicó anteriormente, los dispositivos ReefWave son los únicos que pueden desincronizarse de la aplicación ReefBeat si usas la API local.
Hay tres modos disponibles: Cloud, Local e Híbrido.
Puedes cambiar los ajustes de modo «Conexión a la nube» y «Usar la API Cloud» como se describe en la tabla siguiente.

<table>
<tr>
<td>Nombre del modo</td>
<td>Interruptor Conexión a la nube</td>
<td>Interruptor Usar la API Cloud</td>
<td>Comportamiento</td>
<td>ReefBeat y HA están sincronizados</td>
</tr>
<tr>
<td>Cloud (predeterminado)</td>
<td>✅</td>
<td>✅</td>
<td>Los datos se recuperan mediante la API local. <br />Los comandos de encendido/apagado también se envían mediante la API local. <br />Los comandos se envían mediante la API Cloud.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Los datos se recuperan mediante la API local. <br />Los comandos se envían mediante la API local. <br />El dispositivo aparece como «apagado» en la aplicación ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Híbrido</td>
<td>✅</td>
<td>❌</td>
<td>Los datos se recuperan mediante la API local. <br />Los comandos se envían mediante la API local.<br />La aplicación móvil ReefBeat no muestra los valores correctos de las olas si se han modificado mediante HA.<br/>Home Assistant siempre los muestra correctamente.<br/>Puedes modificar los valores desde la aplicación ReefBeat y desde Home Assistant.</td>
<td>❌</td>
</tr>
</table>

Para los modos Cloud e Híbrido, debes vincular tu cuenta Cloud de ReefBeat.
Primero crea una [«API Cloud»](README.es.md#añadir-la-api-cloud) con tus credenciales, ¡y listo!
El sensor «Vinculado a la cuenta» se actualizará con el nombre de tu cuenta ReefBeat una vez establecida la conexión.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Imagen">
</p>

## Modificar los valores actuales
Para cargar los valores de las olas actuales en los campos de vista previa, usa el botón «Definir vista previa desde la ola actual».
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Imagen">
</p>
Para modificar los valores de las olas actuales, define los valores de vista previa y usa el botón «Guardar vista previa».

El funcionamiento es idéntico al de la aplicación móvil ReefBeat. Todas las olas con el mismo identificador en la programación actual se actualizarán.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Imagen">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Imagen">
</p>

# API Cloud
La API Cloud permite:
- Iniciar o detener accesos directos: emergencia, mantenimiento y alimentación,
- Obtener información del usuario,
- Recuperar la biblioteca de olas,
- Recuperar la biblioteca de suplementos,
- Recuperar la biblioteca de programas LED,
- Recibir notificaciones de [nuevas versiones de firmware](README.es.md#actualización-de-firmware),
- Enviar comandos a ReefWave cuando se selecciona el modo «[Cloud o Híbrido](README.es.md#reefwave)».

Los accesos directos, los parámetros de olas y de LED están ordenados por acuario.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Imagen">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Imagen">
</p>

>[!TIP]
> Es posible desactivar la recuperación de la lista de suplementos desde la interfaz de configuración del dispositivo API Cloud.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Imagen">
***
# FAQ

## Mi dispositivo no se detecta
- Intenta relanzar la detección automática con el botón «Añadir entrada». A veces los dispositivos no responden porque están ocupados.
- Si tus dispositivos RedSea no están en la misma subred que tu Home Assistant, la detección automática fallará primero y te propondrá introducir la dirección IP de tu dispositivo o la dirección de la subred donde se encuentran tus dispositivos. Para la detección de subred, usa el formato IP/MÁSCARA, como en este ejemplo: 192.168.14.0/255.255.255.0.
- También puedes usar el [modo manual](README.es.md#modo-manual).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Imagen">
</p>

## Algunos datos se actualizan correctamente, otros no.
Los datos se dividen en tres partes: datos, configuración e información del dispositivo.
- Los datos se actualizan regularmente.
- Los datos de configuración solo se actualizan al inicio y cuando pulsas el botón «fetch-config».
- La información del dispositivo solo se actualiza al inicio.

Para garantizar la actualización regular de los datos de configuración, activa la [actualización de configuración en tiempo real](README.es.md#actualización-en-tiempo-real).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
