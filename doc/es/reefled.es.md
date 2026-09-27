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

### Tareas de mantenimiento
| Tarea | Por defecto | Rango |
| ----- | ----------- | ----- |
| Limpiar las lentes | 3 semanas | 1 – 5 semanas |
| Quitar el polvo del ventilador y las rejillas | 6 meses | 5 – 7 meses |

Estas dos tareas se crean para todas las generaciones de ReefLED, incluida la
LED virtual. Consulta la sección [Mantenimiento](maintenance.es.md#mantenimiento).

---

[← Volver a la página principal](README.es.md)
