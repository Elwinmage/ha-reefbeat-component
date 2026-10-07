[← Volver a la página principal](README.es.md)

# Mantenimiento

Más allá de controlar el hardware, la integración lleva el seguimiento de las
**tareas de mantenimiento recurrentes** de tus equipos: limpiar el venturi de un
skimmer, sustituir los tubos de una bomba dosificadora, cambiar el carbón activo
del ReefMat... Es Home Assistant quien lo recuerda, ya no tú.

Las tareas se asocian al dispositivo correspondiente y al **subdispositivo**
cuando es más preciso: un cabezal de ReefDose, una bomba de ReefRun. Un ReefRun
expone las tareas de la bomba de retorno en la bomba 1 y las del skimmer en la
bomba 2, nunca al revés: la lista sigue el tipo de bomba que informa el aparato.

## Las tres entidades de una tarea

Cada tarea crea tres entidades, todas en las categorías *Configuración* y
*Diagnóstico* para no saturar tu panel principal:

| Entidad | Función |
| ------- | ------- |
| `button.<dispositivo>_<tarea>` | **Tarea realizada.** Al pulsarlo se registra la fecha actual como última realización y se reinicia la cuenta atrás. |
| `number.<dispositivo>_<tarea>_interval_<unidad>` | **Intervalo.** Con qué frecuencia debe repetirse la tarea, en días, semanas o meses según el caso. |
| `switch.<dispositivo>_<tarea>_notify` | **Notificaciones.** Silencia la alerta de retraso de esa única tarea, sin tocar su vencimiento. |

El botón es la entidad que guarda el estado. Todo lo derivado se expone como
atributos, de modo que basta una entidad para construir un panel o una
automatización:

| Atributo | Significado |
| -------- | ----------- |
| `last_reset` | Fecha ISO-8601 de la última pulsación, o `null` si nunca se hizo |
| `interval_days` | Intervalo actual, siempre normalizado en días |
| `days_left` | Días restantes, negativo una vez vencida |
| `overdue` | `true` en cuanto `days_left` es negativo |
| `reef_role` | `maint_<clave_de_tarea>`, el marcador estable usado para descubrir las tareas |

> [!TIP]
> `reef_role` es lo que hace extensible todo el conjunto: la tarjeta y el
> blueprint de alertas descubren las tareas buscando este atributo. Una tarea
> añadida en una futura versión de la integración aparece en ambos sin ninguna
> actualización por su parte.

## Intervalos

Los intervalos por defecto siguen las recomendaciones de Red Sea, tomando la
mediana del rango publicado. Cada tarea define además un mínimo y un máximo, que
la entidad `number` impone: puedes adaptar un intervalo a la carga de tu acuario,
pero no fijar un valor absurdo.

Los intervalos se muestran en la unidad que tiene sentido para la tarea (semanas
para un venturi, meses para un rotor) y se almacenan internamente en días, así
que cambiar de unidad nunca pierde precisión.

## Persistencia

Fechas e intervalos los guarda Home Assistant en
`.storage/redsea_maintenance_<entry_id>`, un archivo por entrada de
configuración. Sobreviven a reinicios, recargas de la integración y reinicios de
los aparatos, y **nunca se envían a la nube de Red Sea**. Eliminar la entrada de
configuración elimina también el archivo.

## La vista de mantenimiento de ha-reef-card

La tarjeta complementaria [ha-reef-card](https://github.com/Elwinmage/ha-reef-card)
reúne todas las tareas de la instalación en una vista dedicada, como si el
mantenimiento fuera un dispositivo más: una barra de progreso por tarea,
coloreada según el tiempo restante, ordenable por equipo o por vencimiento, con
un botón para marcar la tarea como hecha, una campana para silenciarla y un
control deslizante en línea para cambiar su intervalo.

<p align="center">
<img src="../img/maintenance_task.png" alt="Tareas de mantenimiento en ha-reef-card">
</p>

## Notificaciones: el blueprint de alertas

La integración no notifica por sí misma, y es intencionado: a quién avisar,
cuándo y cómo es cosa tuya. De eso se encarga el blueprint **ReefBeat watch**
incluido en el repositorio, que cubre también los modos anómalos, las
calibraciones vencidas, las baterías bajas y los aparatos inalcanzables.

### Instalación

Pulsa el botón siguiente y confirma la importación en Home Assistant:

[![Abre tu instancia de Home Assistant y muestra el diálogo de importación de blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-reefbeat-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fredsea_alerts.en.yaml)

También hay una versión francesa,
[`redsea_alerts.fr.yaml`](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/blueprints/automation/redsea_alerts.fr.yaml).
Como alternativa, copia el archivo en
`config/blueprints/automation/redsea_alerts/` y recarga las automatizaciones.

Después crea una automatización a partir del blueprint:
*Ajustes → Automatizaciones y escenas → Crear automatización → Usar un
blueprint → ReefBeat watch (redsea)*.

### Configuración

Solo el primer campo es obligatorio:

| Sección | Función |
| ------- | ------- |
| **Destinos de notificación** | Los móviles a avisar, elegidos en el selector de dispositivos. El servicio `notify.mobile_app_*` se resuelve por ti. Se puede indicar un canal de notificación Android (`ReefBeat` por defecto). |
| **Mantenimiento vencido** | Avisa cuando una tarea supera su vencimiento. La opción *Respetar los interruptores de notificación por tarea* (activada por defecto) hace que la automatización obedezca a las entidades `switch.*_notify`: silenciar una tarea en la tarjeta silencia también la automatización. |
| **Modo anómalo** | Avisa cuando un aparato sale de su modo esperado. `off_grace_minutes` (5 por defecto) evita falsas alertas durante un ciclo de alimentación o una intervención manual breve. |
| **Calibración vencida** | Cabezales de ReefDose y calibraciones de skimmer ReefRun. |
| **Retraso de calibración de sondas (RSRUN)** | Sondas de copa llena y de sobre-espumado de los skimmers ReefRun. |
| **Mensaje de alerta del aparato** | Retransmite los mensajes de alerta emitidos por los propios aparatos. |
| **Batería baja** / **Aparato inalcanzable** | Sin sorpresas. |

Cada sección se desactiva de forma independiente y tiene su propia **lista de
exclusión**: un aparato en pruebas no te inunda de alertas mientras el resto
sigue vigilado. La automatización funciona con un ciclo de 5 minutos y tiene en
cuenta los aparatos añadidos o retirados de la integración en el ciclo
siguiente, sin tocar nada.

> [!NOTE]
> El blueprint vigila **todos** los dispositivos de la integración y sus
> subdispositivos. No hay nada que declarar cuando añades un nuevo aparato
> ReefBeat.

---

[← Volver a la página principal](README.es.md)
