[← Volver a la página principal](README.es.md)

# ReefWave:
> [!IMPORTANT]
> Los dispositivos ReefWave son diferentes de los demás dispositivos ReefBeat. Son los únicos que dependen de la nube ReefBeat.<br/>
> Cuando abre la aplicación ReefBeat, se consulta el estado de todos los dispositivos y los datos de la aplicación se obtienen del estado del dispositivo.<br/>
> Con ReefWave es al revés: no hay punto de control local (como puede ver en la aplicación ReefBeat, no se puede añadir un ReefWave a un acuario desconectado).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Las olas se guardan en la biblioteca del usuario en la nube. Cuando cambia un valor de una ola, se cambia en la biblioteca de la nube y se aplica al nuevo programa.<br/>
> ¿Entonces no hay modo local? No es tan sencillo. Existe una API local oculta para controlar el ReefWave, pero la aplicación ReefBeat no detectará los cambios. Como resultado, el dispositivo y Home Assistant por un lado, y la aplicación ReefBeat por otro, quedarán desincronizados. El dispositivo y Home Assistant siempre estarán sincronizados.<br/>
> Ahora que lo sabe, ¡elija!

> [!NOTE]
> Las olas de ReefWave tienen muchos parámetros relacionados, y el rango de algunos depende de otros. No he podido probar todas las combinaciones posibles. Si encuentra un error, puede crear una incidencia [aquí](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modos ReefWave
Como se ha explicado, los dispositivos ReefWave son los únicos que pueden desincronizarse de la aplicación ReefBeat si usa la API local.
Hay tres modos disponibles: Cloud, Local e Híbrido.
Puede cambiar el modo configurando los interruptores "Conectar a la Nube" y "Usar la API Cloud" como se describe en la tabla a continuación.

<table>
<tr>
<td>Nombre del modo</td>
<td>Interruptor Conexión a la Nube</td>
<td>Interruptor Usar API Cloud</td>
<td>Comportamiento</td>
<td>ReefBeat y HA están sincronizados</td>
</tr>
<tr>
<td>Cloud (predeterminado)</td>
<td>✅</td>
<td>✅</td>
<td>Los datos se obtienen mediante la API local. <br />Las órdenes de encendido/apagado también se envían mediante la API local. <br />Las órdenes de olas se envían mediante la API en la nube.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Los datos se obtienen mediante la API local. <br />Las órdenes se envían mediante la API local. <br />El dispositivo aparece como "apagado" en la aplicación ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>Los datos se obtienen mediante la API local. <br />Las órdenes se envían mediante la API local.<br />La aplicación ReefBeat no muestra los valores correctos de las olas si se han cambiado desde HA.<br/>Home Assistant siempre muestra los valores correctos.<br/>Puede cambiar los valores tanto desde la aplicación ReefBeat como desde Home Assistant.</td>
<td>❌</td>
</tr>
</table>

Para los modos Nube e Híbrido debe vincular su cuenta de la nube ReefBeat.
Primero cree un dispositivo ["Cloud API"](../../README.md#add-cloud-api) con sus credenciales, ¡y listo!
El sensor "Vinculado a la cuenta" mostrará el nombre de su cuenta ReefBeat una vez establecida la conexión.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Modificar los valores actuales
Para cargar los valores actuales de la ola en los campos de vista previa, use el botón "Vista previa desde actual".
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
Para cambiar los valores actuales de la ola, ajuste los valores de vista previa y use el botón "Guardar vista previa".

El comportamiento es el mismo que en la aplicación ReefBeat. Se actualizarán todas las olas con el mismo ID en el programa actual.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

## Grupos
Como en la aplicación ReefBeat, todas las ReefWave agrupadas de un acuario
forman un solo grupo (solo con una cuenta en la nube).

| Entidad | Función |
| ------- | ------- |
| `switch` Agrupada con el acuario | Agrupa la bomba con las demás ReefWave de su acuario, o la desagrupa; una bomba que se une queda la última. No disponible sin cuenta en la nube |
| `sensor` ReefWave vinculadas | Número de bombas del grupo, su lista en el atributo `waves` (`hwid`, `name`, `model`, `entry_id`, `available`) |

Un programa se escribe en todas las bombas del grupo: mismos tramos, cada
bomba con sus propias intensidades. Como en la aplicación, una escritura se
rechaza cuando una bomba del grupo no está cargada o no responde: no se
envía nada, así el grupo sigue sincronizado. Todas las ReefWave cargadas se
actualizan tras un cambio de grupo.

## Programa del día
El `sensor` Tipo de ola lleva todo el programa del día en su
atributo `schedule`: la lista de sus intervalos, cada uno empieza en `st`
(minuto del día) y dura hasta el siguiente, con `wave_uid`, `name`, `type`,
`direction`, `frt`, `rrt`, `fti`, `rti`, `sn`, `pd` y `sync`. ha-reef-card
dibuja el día a partir de él.

## Servicios
Estos servicios manejan la biblioteca de olas y el programa del día, como lo
hace la aplicación ReefBeat; los editores de ha-reef-card los usan.
`device_id` es la entrada de configuración de la ReefWave.

| Servicio | Función |
| -------- | ------- |
| `redsea.wave_library` | Olas del acuario de la bomba, con las intensidades de esta bomba, las bombas que usan cada ola y el grupo de la bomba. Sin cuenta en la nube: las olas de su propio programa |
| `redsea.wave_library_save` | Crea una ola, o actualiza una (`uid`). La forma se comparte, las intensidades son las de la bomba; los programas que usan una ola actualizada se vuelven a escribir. Se rechazan las olas Red Sea y los nombres ya usados |
| `redsea.wave_library_delete` | Elimina una de sus olas; se rechaza para una ola Red Sea, o una ola usada por un programa |
| `redsea.wave_program_save` | Escribe el programa del día (`slots`: `st`, `wave_uid`, `direction`; el primero empieza en 0) en todas las bombas del grupo; en la propia bomba sin cuenta en la nube |
| `redsea.wave_preview` | Ejecuta una ola en la bomba de 1 a 10 min, y luego vuelve a su programa |
| `redsea.wave_preview_stop` | Detiene la vista previa |
| `redsea.wave_pump_set` | Dirección e intensidades de esta bomba en la ola actual (incluso una Red Sea); las demás bombas del grupo no se tocan |
| `redsea.wave_group_set` | Agrupa o desagrupa una bomba (`grouped`), como el interruptor |
| `redsea.wave_group_order` | Orden de las bombas del grupo (`hwids`, cada bomba citada una vez) |

La biblioteca necesita una cuenta en la nube de ReefBeat: sin ella,
`wave_library_save` y `wave_library_delete` se rechazan. Todos los rechazos
son errores traducidos de Home Assistant.

## Iconos
Los pictogramas de tipo de ola de la aplicación están disponibles como
`redsea:wave-uniform`, `redsea:wave-random`, `redsea:wave-regular`,
`redsea:wave-step`, `redsea:wave-surface` y `redsea:wave-none`.

### Tareas de mantenimiento
| Tarea | Por defecto | Rango |
| ----- | ----------- | ----- |
| Limpiar las jaulas del rotor | 2 meses | 1 – 3 meses |

Consulta la sección [Mantenimiento](maintenance.es.md#mantenimiento).

---

[← Volver a la página principal](README.es.md)
