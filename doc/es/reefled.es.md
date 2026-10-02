[← Volver a la página principal](README.es.md)

# ReefLED:

- Obtener y establecer canales Blanco y Azul (only for G1: RSLED50, RSLED90, RSLED160)
- Obtener y establecer Temperatura de Color, Intensidad y Luna (all LEDs)
- Gestión de la aclimatación. Acclimation settings are automatically enabled or disabled according to the acclimation switch.
- Gestión de las fases lunares. Moon phase settings are automatically enabled or disabled according to the moon phase switch.
- Ajuste manual del modo de color con o sin duración.
- Obtener valores de ventilador y temperatura.
- Obtener nombre y valor de los programas (with cloud support). Only for G1 LEDs.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Image">
</p>

***

La compatibilidad con la temperatura de color de los LED G1 tiene en cuenta las particularidades de cada uno de los tres modelos.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## IMPORTANTE para las luces G1 y G2

### LUCES G2

#### Intensidad
Como los LED G2 garantizan una intensidad constante en todo el rango de colores, sus LED no aprovechan toda su capacidad en el centro del espectro. A 8.000K, el canal blanco está al 100 % y el azul al 0 % (al revés a 23.000K). A 14.000K con un 100 % de intensidad en las luces G2, la potencia de los canales blanco y azul es de aproximadamente un 85 %.
Esta es la curva de pérdida de los G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
</p>

#### Temperatura de Color
La interfaz G2 no admite todo el rango de temperaturas. De 8.000K a 10.000K, los valores avanzan en pasos de 200K, y de 10.000K a 23.000K en pasos de 500K. Esto se gestiona automáticamente: si elige un valor no válido (p. ej. 8.300K), se selecciona automáticamente un valor válido (8.200K en este ejemplo). Por eso a veces verá que el cursor se reajusta ligeramente al elegir el color en una luz G2: se recoloca en un valor permitido.

### LUCES G1

Los LED G1 se controlan mediante los canales blanco y azul, lo que permite la potencia máxima en todo el rango, pero no una intensidad constante sin compensación.
Por eso se ha implementado la compensación de intensidad.
Esta compensación garantiza el mismo [PAR](https://en.wikipedia.org/wiki/Photosynthetically_active_radiation) (intensidad luminosa) sea cual sea la temperatura de color elegida (en el rango de 12.000 a 23.000K).
> [!NOTE]
> Como Red Sea no publica valores de PAR por debajo de 12.000K, la compensación solo está disponible en el rango de 12.000 a 23.000K. Si tiene un LED G1 y un medidor de PAR, puede [contactarme](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) para añadir la compensación en todo el rango (9.000 a 23.000K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

Dicho de otro modo, sin compensación, una intensidad del x % a 9.000K no proporciona el mismo PAR que a 23.000K o a 15.000K.

Estas son las curvas de potencia:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

Si quiere usar toda la potencia de su LED, desactive la compensación de intensidad (por defecto).

Si activa la compensación de intensidad, la intensidad luminosa será constante en todas las temperaturas de color, pero en el centro del rango no usará toda la capacidad de sus LED (como con los modelos G2).

Tenga en cuenta también que, con la compensación activada, el factor de intensidad puede superar el 100 % en las luces G1 si ajusta a mano los canales blanco/azul. ¡Así puede aprovechar toda la potencia de sus LED!

***

### Programa meteorológico
La lámpara puede seguir el tiempo de un lugar: en **modo meteorológico GPS**,
su semana se construye a partir del tiempo de los próximos siete días
(previsión) o de los siete días pasados (tiempo medido), proporcionado por
[Open-Meteo](https://open-meteo.com) (gratuito, sin clave). No hay nada que
validar: al activar el modo se apartan los programas propios de la lámpara y
se envía de inmediato la semana meteorológica; después el tiempo se vuelve a
consultar cada pocos días (de 3 a 15, a su elección; se comprueba una vez al
día, a las 00:10) y cada vez que cambia un ajuste (30 s después del último
cambio). Al desactivar el modo se vuelven a escribir los programas propios
de la lámpara.

| Entidad | Función |
| ------- | ------- |
| `switch` Modo tiempo GPS | Tiempo GPS, o los programas estándar de la lámpara |
| `select` Periodo meteorológico | Semana próxima (previsión) o pasada (medida) |
| `number` Actualización del tiempo (días) | Días entre dos consultas del tiempo, de 3 a 15 |
| `text` Lugar meteorológico | `lat, lon`, una URI `geo:` o un enlace de Google Maps / OpenStreetMap / Apple Maps; vacío para el hogar de Home Assistant |
| `select` Día meteorológico en el acuario | Hora del lugar, anclada al amanecer, al atardecer, o estirada entre ambos |
| `time` Amanecer meteorológico / Atardecer meteorológico | Horas del acuario usadas por esos anclajes |
| `number` Intensidad mínima meteorológica / Intensidad máxima meteorológica | Límites de la intensidad |
| `switch` Nubes del tiempo | Ajusta las nubes de la lámpara en las horas nubladas |
| `sensor` Programa meteorológico | Resultado de la última consulta (estado, lugar y, para cada día, sol, horas de sol, nubosidad e intensidad máxima); `writing` (`{done, total}` días) mientras se envía una semana a la lámpara |

Cómo se construye un día:
- **Horarios** — del amanecer al atardecer del lugar, con la hora del lugar
  (un arrecife de Fiyi también amanece a las 06:00 en la lámpara), o
  anclados al acuario: *amanecer* (el día del lugar empieza a la hora
  elegida), *atardecer* (termina a la hora elegida) o *ambos* (el día del
  lugar se estira entre las dos horas).
- **Intensidad** — sigue el sol realmente recibido (radiación solar horaria,
  1000 W/m² equivalen a pleno sol), entre el mínimo y el máximo; hasta 8
  puntos por día.
- **Color** — el del programa estándar de la lámpara en el mismo momento de
  su día: su equilibrio blanco/azul en una G1, su temperatura de color en
  una G2. Puede elegir sus propios colores en su lugar, por día de la semana
  (ajuste `colors`: `{día: [{at, k}]}`, `at` del amanecer, 0, al atardecer,
  1, `k` la temperatura de color de 8.000 a 23.000 K); una G1 los convierte
  con la tabla de su modelo. Este ajuste no tiene entidad: se define desde
  el editor de programas de ha-reef-card, o con `redsea.led_weather_save`.
- **Nubes** — en las horas con al menos un 40 % de nubosidad: Low, Medium o
  High según su nubosidad media; se eliminan en un día despejado.
- **Luna** — conserva su lugar después del atardecer.

El programa se llama *Weather* en la lámpara. Las peticiones escritas en
una lámpara se espacian (2 s): una ReefLED responde tarde, o no responde, a
una orden enviada demasiado pronto; por eso escribir una semana lleva un
poco de tiempo.

Las lámparas de un grupo ([LED virtual](virtual-led.es.md#led-virtual)) comparten un único
programa meteorológico: activado o ajustado en cualquiera de ellas, lo está
para todas. Cada lámpara recibe su propia semana meteorológica, en su
formato, y la comprobación diaria se hace una sola vez, por el grupo.

| Servicio | Función |
| -------- | ------- |
| `redsea.led_weather_apply` | Vuelve a consultar el tiempo y envía la semana de inmediato (solo en modo meteorológico), desde una automatización por ejemplo |
| `redsea.led_weather_preview` | La semana que darían unos ajustes, y la propia de la lámpara: no se escribe nada |
| `redsea.led_weather_save` | Guarda de una vez los ajustes y el modo (`enabled`), y luego escribe la semana (en segundo plano, o antes de responder con `wait`) |

***

### Desfase del amanecer
Cada ReefLED que responde a `/offset` (comprobado al arrancar) recibe un
`number` Desfase del amanecer (minutos): la lámpara reproduce todo su
programa con ese retraso. En un grupo, el
[amanecer escalonado](virtual-led.es.md#led-virtual) del LED virtual lo ajusta para cada
lámpara.

***

### Biblioteca en la nube
Con una cuenta en la nube de ReefBeat ([API Cloud](README.es.md#añadir-la-api-cloud)), los
programas de luz de la biblioteca de la aplicación ReefBeat se pueden leer y
escribir, como hace el editor de programas de ha-reef-card. Los programas G1
se guardan por acuario, los G2 por cuenta; los de Red Sea no se pueden
modificar ni eliminar.

| Servicio | Función |
| -------- | ------- |
| `redsea.led_library` | Lista los programas que puede usar la lámpara (`linked: false` sin cuenta en la nube) |
| `redsea.led_library_save` | Añade un programa (`name`, `program`, `clouds`), o actualiza uno de los suyos (`uid`) |
| `redsea.led_library_delete` | Elimina uno de sus programas (`uid`) |
| `redsea.led_convert` | Convierte puntos G1 entre blanco/azul y kelvin/intensidad, con la tabla del modelo y la compensación de intensidad |

***

### Tareas de mantenimiento
| Tarea | Por defecto | Rango |
| ----- | ----------- | ----- |
| Limpiar las lentes | 3 semanas | 1 – 5 semanas |
| Quitar el polvo del ventilador y las rejillas | 6 meses | 5 – 7 meses |

Estas dos tareas se crean para todas las generaciones de ReefLED, incluida la
LED virtual. Consulta la sección [Mantenimiento](maintenance.es.md#mantenimiento).

---

[← Volver a la página principal](README.es.md)
