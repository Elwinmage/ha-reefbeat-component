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
> El modo Poseidon es experimental. Por ahora solo retransmite y observa el
> tráfico: la integración sigue consultando los dispositivos.

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
>   `/config/redsea/poseidon/snapshots/`).
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

> [!NOTE]
> Ninguna familia de dispositivos se puede fusionar aún: la fusión se escribe a
> partir de los archivos espía. Hasta entonces, *Shadow* solo compara, y
> *Poseidon* vuelve a leer el dispositivo cada vez que envía un estado.

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

- **Estrategia por defecto**: la de los dispositivos en modo Poseidon que no
  tienen una propia (ver [Estrategias](#estrategias)). *Espía* por defecto.
- **Intervalo de consulta de la estrategia Poseidon**, en minutos (10 por
  defecto).
- **Modo debug**: cada trama que cruza el relé se escribe descifrada en
  `/config/redsea/poseidon/logs/poseidon.jsonl` (rotación a 10 MB, se guardan
  5 archivos). Los datos están en claro en ese archivo.
- **Plazo antes de que un dispositivo esté silencioso**, en minutos (10 por
  defecto).
- **Clave del watchdog**: 16 caracteres, propuesta mientras no haya ninguna.
  Un watchdog en otra máquina (autónomo, o en
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup))
  pregunta al relé si está vivo, y devuelve los dispositivos al modo normal
  cuando no lo está. Copie esta clave en su configuración; déjela vacía para no
  responder a ningún watchdog.

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
