[← Volver a la página principal](README.es.md)

# Modo Poseidon

<p align="center">
<img src="../img/poseidon/poseidon.png" alt="Poseidon" width="240">
</p>

El modo Poseidon coloca un relé entre sus dispositivos ReefBeat y el broker
MQTT de Red Sea, dentro de Home Assistant. Un dispositivo en modo Poseidon se
conecta a Home Assistant en lugar de `mqtt.reef-beat.com`, y Home Assistant
transmite su tráfico a Red Sea sin modificarlo: la app ReefBeat sigue
funcionando como antes.

> [!WARNING]
> El modo Poseidon es experimental. Con la estrategia *Espía*, la predeterminada,
> solo retransmite y observa el tráfico: la integración sigue consultando los
> dispositivos. Las estrategias *Shadow* y *Poseidon* usan lo que envían los
> dispositivos (vea [Estrategias](#estrategias)).

## Añadir Poseidon

*Ajustes > Dispositivos y servicios > Red Sea > Añadir entrada > Modo Poseidon*

- **Puerto de escucha**: se propone el primer puerto libre a partir de 1884
  (1883 y 8883, los puertos MQTT habituales, se omiten). Se comprueba de nuevo
  al validar y en cada arranque del relé: si otro servicio lo ocupa, un aviso
  de reparación lo indica y los dispositivos no se tocan.
- **Dirección de Home Assistant**: la dirección IPv4 por la que los
  dispositivos llegan a Home Assistant.
- **Cuenta cloud**: la cuenta cloud ReefBeat usada para obtener las claves de
  los dispositivos. Se necesita una cuenta cloud.

## Añadir dispositivos

*Poseidon > Configurar > Añadir dispositivos*

Cada dispositivo de la integración aparece con su estado:

| Estado | Significado |
|---|---|
| Seleccionable | Sus claves se conocen: pasa enseguida a modo Poseidon |
| Seleccionable, 🔑 | Primero hay que obtener sus claves (ver abajo) |
| Ya en modo Poseidon | Nada que hacer |
| Sin credenciales cloud | Vinculado a un acuario local: no admite el modo Poseidon |
| No está en la cuenta cloud | Sus claves no se pueden obtener con esta cuenta |
| Inaccesible | No responde |

> [!CAUTION]
> **Obtener las claves es destructivo.** Un dispositivo no entrega sus claves:
> para obtenerlas, se elimina de la nube ReefBeat y se vuelve a crear.
> - se desvincula de su acuario, y la app puede pedir emparejarlo de nuevo;
> - los programas, preajustes e historial guardados en la nube para él pueden
>   perderse;
> - su configuración se guarda antes y se compara después: ReefRun y ReefWave
>   recuperan la suya automáticamente; para los demás dispositivos, lo que
>   cambió se lista en una notificación (la configuración guardada queda en
>   `/config/redsea/poseidon/snapshots/`);
> - una ReefWave depende de la nube, que le envía su programa en cada conexión:
>   antes de eliminarla se guardan también las olas personalizadas de su acuario
>   (con las intensidades de cada bomba) y su programa; la obtención se detiene,
>   sin eliminar nada, si no se pueden leer. Después, las olas que la nube perdió
>   se crean de nuevo (o recuperan los ajustes de la bomba), el programa se envía
>   a la nube y la nube lo envía a las bombas; la bomba solo se escribe
>   directamente si no lo recibió.
>
> La obtención se hace una vez por dispositivo: Home Assistant conserva las
> claves, incluso si se elimina Poseidon.

## El interruptor Poseidon

Cada dispositivo con claves conocidas tiene un interruptor **Modo Poseidon** en
su página:

- **encendido**: el dispositivo habla con Red Sea a través de Home Assistant;
- **apagado**: el dispositivo habla directamente con Red Sea (modo normal).

Su estado se lee en el propio dispositivo. Sus atributos:

| Atributo | Significado |
|---|---|
| `connection_state` | Estado de conexión indicado por el dispositivo |
| `last_up` / `last_down` | Último tráfico dispositivo → Red Sea / Red Sea → dispositivo |
| `silent` | En modo Poseidon, pero nada pasó por el relé durante el plazo de los ajustes |

Un dispositivo silencioso también genera un aviso de reparación, que
desaparece solo cuando su tráfico se reanuda. Un dispositivo silencioso nunca
se devuelve al modo normal automáticamente.

## Qué pasa y cuándo

| Evento | Dispositivos |
|---|---|
| Reinicio de Home Assistant, recarga de Poseidon | Se quedan como están: se reconectan cuando vuelve el relé |
| Poseidon desactivado o eliminado | Todos vuelven al modo normal |
| Un dispositivo no puede volver al modo normal | Se nombra en una notificación |
| El relé cae, un [watchdog](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog) vigila | Todos vuelven al modo normal, una vez confirmado que Red Sea es accesible; sin watchdog, use el [script de rescate](#script-de-rescate) |
| Un dispositivo apunta al relé pero nunca se conecta a él (conservó su sesión con Red Sea) | Se le obliga a reconectarse tras 2 minutos: apuntado de nuevo a Red Sea y luego al relé, dos veces como máximo |

Solo se entra en modo Poseidon por decisión suya. Todo cambio automático
devuelve al modo normal.

## Estrategias

Lo que hace Home Assistant con un dispositivo en modo Poseidon. Cada
dispositivo tiene un selector **Estrategia Poseidon** junto a su interruptor;
los ajustes dan el valor por defecto.

| Estrategia | Consulta | Estados enviados | Archivo |
|---|---|---|---|
| *Espía* | sin cambios | registrados, comparados con la consulta siguiente | `spy.jsonl` |
| *Shadow* | sin cambios | fusionados en los datos del dispositivo, comparados con la consulta siguiente | `shadow.jsonl` |
| *Poseidon* | cada N minutos | usados; el dispositivo se vuelve a leer en cada estado mientras su familia no se pueda fusionar | — |

> [!IMPORTANT]
> **Propietarios de ReefATO+, necesito su ayuda.** No tengo ningún ReefATO+, así
> que el modo Poseidon nunca ha funcionado en uno: aún no se sabe qué envía y nada
> de ello se fusiona. Ponga primero el suyo en la estrategia *Espía* y, para
> completar su soporte:
> - envíeme su registro espía (`/config/redsea/poseidon/logs/spy.jsonl`) en una
>   [issue de GitHub](https://github.com/Elwinmage/ha-reefbeat-component/issues),
>   tras leerlo: está descifrado y contiene los identificadores de sus
>   dispositivos;
> - y/o abra las reparaciones que Poseidon genere por sus
>   [mensajes inesperados](#mensajes-inesperados): cada una rellena la issue de GitHub.
>
> Nunca envíe el archivo de las claves. La advertencia sobre la obtención de las
> claves se aplica al ReefATO+ como a cualquier dispositivo.

Familias fusionadas hasta ahora, a partir de las sesiones espía:

| Familia | Fusionado |
|---|---|
| ReefControl Power | estados, telemetría (sonda de temperatura incluida); los estados de las tomas se calculan a partir de sus programas, como hace la app ReefBeat |
| ReefDose | estados, telemetría; un `dosing-log` (fin de una dosis) la vuelve a leer, por su cola de dosificación, y también la medianoche (00:01, hora de Home Assistant), cuando la cola del nuevo día sustituye a la del día que termina |
| ReefMat | estados, telemetría, `rolling-log` (fin de un avance) |
| ReefLED | telemetría |
| ReefWave | estados (modo: una alimentación la apaga y vuelve a auto, ajustes), telemetría (modo, señal wifi); un programa escrito en la app (`schedule`, enviado sin sus intervalos) la vuelve a leer. Su ola actual se deduce de su programa y del reloj: nada envía el cambio de ola al inicio de un intervalo (solo su telemetría lo indica, en menos de un minuto) |
| ReefRun | estados, telemetría (estado, intensidad, temperatura de sus bombas: copa llena, bomba ausente...); el fin de una calibración y una `notification` (una bomba por reconectar) la vuelven a leer |
| ReefControl | telemetría y eventos `probe` (lecturas de sondas), estados (modo, enlace con un ReefControl Power, modo de fuga), modo y estado de sus puertos (un puerto apagado consume 0; el consumo de un puerto encendido llega por la consulta); una sonda o un puerto instalado o configurado lo vuelve a leer |

Para las demás familias, *Shadow* solo compara, y *Poseidon* vuelve a leer el
dispositivo cada vez que envía un estado. *Poseidon* también lo vuelve a leer
cuando un estado indica algo que su fusionador no puede escribir (un ajuste que no
conoce, un programa de ReefDose, enviado sin sus intervalos). Esa lectura incluye
las fuentes de configuración: lo que cambia la app son sobre todo ajustes, que la
consulta nunca vuelve a leer. Cada comando de escritura de la app que el
dispositivo acepta también lo vuelve a leer: no todo ajuste se envía (el offset de
una sonda de temperatura no).

Un ReefControl Power sin toma controlada por un sensor (con o sin sonda de
temperatura), una ReefDose (su cola de dosificación se lee tras cada dosis y a
medianoche) y una ReefWave (su programa se vuelve a leer cuando cambia) envían todo
lo que cambia: con *Poseidon*, solo se consultan cada *Intervalo de sondeo de
seguridad*.

### Espía

`/config/redsea/poseidon/logs/spy.jsonl` (rotación a 10 MB, se guardan 5
archivos) contiene, con el mismo reloj:

| `kind` | Registro |
|---|---|
| `publish`, `control` | una trama entre el dispositivo y Red Sea, en ambos sentidos, descifrada |
| `http` | una petición HTTP enviada por Home Assistant al dispositivo: método, endpoint, estado (0 = sin respuesta), duración, datos; `origin` es `integration` o `poseidon` (sus lecturas de `/cloud` cada 60 s) |
| `compare` | un estado enviado frente a la consulta siguiente, cada valor `same`, `differs` o `unknown` |
| `mark` | la estrategia o la pausa cambió |

Un dispositivo en modo espía tiene también un interruptor **Pausa de la
consulta**: ya no se le envía ninguna petición, ni siquiera las lecturas de
`/cloud` de Poseidon; lo que envía entonces, lo envía por sí mismo. La pausa no
sobrevive a un reinicio.

Captura aconsejada, por dispositivo (relojes de los hosts Home Assistant
sincronizados, misma zona horaria):

1. 30 minutos sin ninguna consulta: cualquier otro Home Assistant que lea el
   dispositivo detenido, la pausa activada;
2. 30 minutos solo con la consulta (pausa desactivada);
3. acciones a horas anotadas: desde la app ReefBeat, desde Home Assistant, en
   el propio dispositivo;
4. si otro Home Assistant consulta el dispositivo, sus peticiones se añaden
   con la acción `logger.set_level`,
   `custom_components.redsea.reefbeat.api: debug`.

## Ajustes

*Poseidon > Configurar > Ajustes de Poseidon*

- **Estrategia por defecto**: la de cada dispositivo en modo Poseidon que no tiene
  estrategia propia (vea [Estrategias](#estrategias)). *Espía* por defecto.
- **Intervalo de consulta de la estrategia Poseidon**, en minutos (10 por defecto).
- **Modo debug**: cada trama que cruza el relé se escribe descifrada en
  `/config/redsea/poseidon/logs/poseidon.jsonl` (rotación a 10 MB, se guardan 5
  archivos). Los datos están en claro en ese archivo.
- **Plazo antes de que un dispositivo esté silencioso**, en minutos (10 por
  defecto).
- **Intervalo de sondeo de seguridad**, en minutos (60 por defecto): la consulta de
  un dispositivo cuyos mensajes enviados cubren todo lo que cambia, y la frecuencia
  con que se lee el `/cloud` de un dispositivo que intercambia a través del relé.
- **Señalar mensajes inesperados** (activado por defecto): vea
  [Mensajes inesperados](#mensajes-inesperados).
- **Buscar informes existentes en GitHub** (activado por defecto): solo se envía la
  firma de un mensaje inesperado.
- **Retener las restauraciones de la nube al conectar** (activado por defecto):
  vea [Protección al conectar](#protección-al-conectar).
- **Clave del watchdog**: 16 caracteres, propuesta mientras no haya ninguna. El relé
  responde a una petición cifrada «¿sigues vivo?» hecha con esta clave:
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog),
  o su `poseidon_watchdog.py` solo en otra máquina, vigila el relé y devuelve los
  dispositivos al modo normal cuando cae. Copie esta clave en su configuración;
  déjela vacía para no responder a ningún watchdog.

## Mensajes inesperados

Cada mensaje que cruza el relé se compara con lo que se conoce de la familia de su
dispositivo: un paquete o topic MQTT desconocido, un comando de la nube a un
endpoint desconocido, un estado o una telemetría con un campo nuevo, ausente o de
otro tipo. La primera aparición va a `/config/redsea/poseidon/logs/anomalies.jsonl`,
anonimizada (identificadores, nombres, direcciones de red y claves eliminados); un
comando desconocido espera 5 segundos a lo que el dispositivo responde y envía, y
se escribe con ello.

Cada uno tiene una firma, la misma para todos los usuarios. Se buscan en las issues
del repositorio, y una reparación indica qué hacer: notificarlo (una issue de GitHub
prerrellenada, enviada solo por usted), seguir el informe abierto, actualizar a la
versión que lo gestiona o leer el informe cerrado. Un campo nuevo de telemetría solo
genera una reparación cuando la búsqueda no encontró ningún informe.

## Protección al conectar

En cada conexión de un dispositivo, la nube Red Sea le envía su propia copia de los
ajustes del dispositivo. Cuando esa copia está desactualizada, el dispositivo pierde
los actuales: una ReefWave perdió así todo su programa. Durante los primeros 30
segundos de cada conexión a través del relé se retienen por ello las restauraciones
conocidas de la nube (grupo y programa de una ReefWave, cabezal de alimentación de
una ReefDose).

Cualquier otro comando pasa y se registra (`guard_passed` en el archivo espía): un
dispositivo que se reinicia mientras se usa la app (un ReefControl que falla al
instalar una sonda) recibe los comandos del usuario.

## Eventos

### `redsea_dose`

Se emite cuando una ReefDose en modo Poseidon (cualquier estrategia) termina una
dosis, programada o manual, según su `dosing-log`. Una dosis enviada dos veces (tras
una reconexión) se emite una vez.

| Campo | Contenido |
|---|---|
| `device_id` | el dispositivo en Home Assistant |
| `name` | su nombre |
| `head` | número de cabezal |
| `supplement`, `brand` | tal como los indica el dispositivo |
| `dose_type` | `scheduled` o `manual` |
| `volume` | volumen dosificado, en mL |
| `started_at` | inicio de la dosis, según la cola de dosificación consultada antes (hora local del dispositivo); para una dosis que no estaba en ella (la de medianoche, manual desde la app), estimado a partir del caudal del cabezal; `null` mientras menos de 3 dosis del cabezal tengan una duración medida |
| `ended_at` | fin de la dosis (hora local del dispositivo) |
| `duration_s` | `ended_at` − `started_at`, `null` sin inicio |
| `start_estimated` | `true` cuando `started_at` (y `duration_s`) son estimados: volumen ÷ caudal del cabezal (sus últimas 20 dosis de duración medida) |

No se envía nada cuando empieza una dosis: su inicio es la hora que le dio la cola de
dosificación. La dosis de medianoche no está en ninguna cola (la del día que termina
está vacía entonces, la del nuevo día empieza después): su inicio se estima.

### `redsea_notification`

Se emite cuando un dispositivo en modo Poseidon (cualquier estrategia) envía una
alarma, la que la app ReefBeat muestra como notificación. Lleva lo que indicó el
dispositivo:

| Campo | Contenido |
|---|---|
| `device_id` | el dispositivo en Home Assistant |
| `name` | su nombre |
| `device_type` | su familia: `reef-run`, `reef-control`, `reef-dosing`... |
| `type` | la alarma, tal como la nombra el dispositivo |
| `sub_type` | tal como lo indica el dispositivo (`sub-type`) |
| otros campos | de qué trata la alarma: `pump` o `pump_name` (ReefRun), `probe` (ReefControl, su nombre), `supplement` (ReefDose) |

Vistos hasta ahora:

| Familia | `type` |
|---|---|
| ReefRun | `full_cup_warning` (`pump`), `no_pump` (`pump_name`) |
| ReefControl | `sensor_danger_range`, `temperature_danger_range`, `aquarium_water_leak` (`probe`) |
| ReefDose | `stock_level_empty` (`supplement`) |

```yaml
automation:
  - alias: Skimmer cup full
    triggers:
      - trigger: event
        event_type: redsea_notification
        event_data:
          type: full_cup_warning
    actions:
      - action: notify.notify
        data:
          message: "{{ trigger.event.data.name }}: the skimmer cup is full"
```

### Historial de las dosis

Cada dosis también se guarda, por cabezal, durante 30 días (5000 dosis como máximo),
incluso tras reiniciar:

- cada cabezal de una ReefDose recibe un sensor **Última dosis** (en el dispositivo
  del cabezal), disponible solo mientras el dosificador está en modo Poseidon: su
  estado es el fin de la última dosis, sus atributos el volumen, tipo, inicio,
  duración y suplemento; el recorder los guarda como cualquier sensor;
- la acción `redsea.get_doses` devuelve las dosis, de la más reciente a la más
  antigua: `device_id` (el dosificador, uno de sus cabezales o su entrada de
  configuración), y opcionalmente `head`, `days`, `limit`;
- la ha-reef-card las muestra en el diálogo de configuración de un cabezal
  (**Historial de dosis**).

```yaml
automation:
  - alias: Log the doses
    triggers:
      - trigger: event
        event_type: redsea_dose
    actions:
      - action: logbook.log
        data:
          name: "{{ trigger.event.data.name }}"
          message: >-
            head {{ trigger.event.data.head }}
            ({{ trigger.event.data.supplement }}):
            {{ trigger.event.data.volume }} mL,
            {{ trigger.event.data.dose_type }},
            {{ trigger.event.data.started_at }} → {{ trigger.event.data.ended_at }}
```

## Mensajes de la app ReefBeat

Los sensores **Último mensaje** y **Último mensaje de alerta** (y el historial de
mensajes) vienen de las respuestas de los dispositivos a los envíos de Home
Assistant, que siguen en HTTP en todos los modos. Los comandos de la app ReefBeat (o
de la nube) llegan a un dispositivo por MQTT: en modo Poseidon (cualquier
estrategia), la respuesta del dispositivo a cada comando de escritura
(`command-response`, mismo `uuid`) alimenta los mismos sensores, como lo haría una
respuesta HTTP:

- un `message` (`settings updated successfully`, `head settings successfully
  saved`...) pasa a ser el último mensaje;
- una `alert` (`NoMoreDoseAlert`...), `"success": false` o un estado de error pasa a
  ser la última alerta.

Las lecturas de la app (`GET`) no llevan mensaje: se dejan fuera. El atributo
`origin` de ambos sensores, y de cada entrada del historial (la acción
`redsea.get_messages`), indica de dónde vino: `ha` (un envío de Home Assistant) o
`reefbeat` (un comando de la app o de la nube). La ha-reef-card lo muestra tras la
fecha.

## Exportar e importar las claves

*Poseidon > Configurar > Exportar las claves* da un enlace de descarga de
todas las claves conocidas, válido 5 minutos. El archivo se genera al hacer
clic y nunca se escribe en `/config`; está en el formato de la CLI
(`keystore.json`) y contiene las claves en claro: guárdelo en un lugar seguro.
La acción `redsea.poseidon_export`, para automatizaciones, escribe el mismo
archivo en `/config/redsea/poseidon/keystore-<fecha>.json`, legible solo por
su propietario.

*Poseidon > Configurar > Importar claves* pide un archivo así y lo envía desde
su navegador. Un dispositivo solo se reemplaza por un registro más reciente,
los dispositivos sin claves se omiten, y los dispositivos importados reciben su
interruptor enseguida.

## Script de rescate

*Poseidon > Configurar > Script de rescate* da un enlace de descarga
(5 minutos) a `poseidon_rescue.py`: un script que devuelve los dispositivos al
broker de Red Sea sin Home Assistant, para cuando este ya no puede hacerlo
(detenido, relé averiado, integración eliminada). Funciona en cualquier
ordenador de la red de los dispositivos con Python 3.8 o superior, nada más que
instalar:

```bash
python3 poseidon_rescue.py --dry-run   # lo que se haría, sin cambiar nada
python3 poseidon_rescue.py             # los dispositivos en el relé, tras confirmar
```

| Opción | Uso |
|---|---|
| `--ip HWID=IP` | un dispositivo cambió de dirección desde la descarga |
| `--scan CIDR` | dónde buscar los dispositivos que cambiaron de dirección (repetible) |
| `--no-scan` | no buscarlos nunca |
| `--only HWID` | un solo dispositivo (hwid o nombre, repetible) |
| `--all` | todos los dispositivos, sea cual sea su broker actual |
| `--keystore keystore.json` | una exportación del keystore en lugar de los dispositivos integrados |
| `--yes` | sin confirmación |

No se escribe nada en un dispositivo antes de que demuestre ser el correcto: su
`hwid`, leído en `/device-info`, debe coincidir. Un dispositivo que ya no
responde en su dirección, o cuya dirección es ahora la de otro, se busca en la
red: el /24 de cada dirección conocida y del ordenador que ejecuta el script,
o las subredes `--scan`.

Cada dispositivo recibe la misma secuencia que desde Home Assistant
(desactivar, escribir el broker y las claves, activar), y luego se vuelve a
leer `/cloud` para comprobarlo. El script contiene las claves en claro:
guárdelo en un lugar seguro, y vuelva a descargarlo tras añadir dispositivos.
