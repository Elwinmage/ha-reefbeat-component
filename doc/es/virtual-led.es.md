[← Volver a la página principal](README.es.md)

# LED virtual
Un LED virtual es un **grupo** de ReefLED, como los LED «agrupados» de la
aplicación ReefBeat: sus lámparas se controlan como una sola.

- Cree un dispositivo virtual desde el panel de la integración y use después
  el botón de configuración: elija los LED (dos como mínimo, un LED solo
  pertenece a un grupo) y luego su orden. Un nuevo LED virtual empieza con
  las lámparas que la aplicación ReefBeat ya agrupa, en el orden de la
  aplicación.
- Solo puede usar Kelvin e intensidad para controlar sus LED si tiene G2 o una mezcla de G1 y G2.
- Puede usar tanto Kelvin/Intensidad como Blanco y Azul si solo tiene luces G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

## Lo que comparte el grupo
Un valor compartido ajustado en el LED virtual, o en una de sus lámparas, se
aplica a todas las lámparas del grupo: canales manuales, kelvin /
intensidad, modo, temporizador, programas, aclimatación, fase lunar y el
[programa meteorológico](reefled.es.md#programa-meteorológico). Lo que pertenece a una lámpara se queda
en la lámpara: nombre, Wi-Fi, nube, firmware, identificación, reinicio…

Como en la aplicación, una escritura de grupo se rechaza cuando una de las
lámparas no está cargada, no responde, o está en un modo que el grupo no
puede controlar (apagada, o retenida por un acceso directo): no se envía
nada, así las lámparas siguen sincronizadas, y el error nombra las lámparas
afectadas. Una lámpara puesta fuera de servicio en la aplicación se deja
fuera de las escrituras, las comprobaciones y el amanecer escalonado. El
blanco / azul no se puede ajustar en un grupo que contenga una G2: use
kelvin / intensidad.

## Amanecer escalonado
Como en la aplicación, las lámparas de un grupo pueden empezar su día una
tras otra:

| Entidad | Función |
| ------- | ------- |
| `switch` Amanecer escalonado | Escalona el amanecer de las lámparas del grupo |
| `number` Retraso del amanecer escalonado | Minutos entre dos lámparas, de 1 a 15 (10 por defecto) |

Cada lámpara empieza su día `retraso × posición` minutos más tarde (la
primera lámpara del grupo no se retrasa). El valor se escribe en el
Desfase del amanecer de cada lámpara, de nuevo en cuanto cambian las
lámparas del grupo o su orden; una lámpara que sale del grupo vuelve a 0.

## Las lámparas del grupo
El `sensor` LED vinculados, en el LED virtual y en cada lámpara de
un grupo, da el número de lámparas y, en su atributo `leds`, su lista en el
orden del grupo: `hwid`, `name`, `model`, `g2`, `offset` (desfase del
amanecer en minutos, vacío para una lámpara sin `/offset`) y `entry_id`.
ha-reef-card lo usa para listar las lámparas.

## Sincronización con la aplicación ReefBeat
Con una cuenta en la nube de ReefBeat ([API Cloud](README.es.md#añadir-la-api-cloud)), un grupo
cuyas lámparas son de un solo modelo, de un solo acuario y de una sola
cuenta es el mismo grupo en la aplicación: el grupo, su orden y su amanecer
escalonado se escriben en la nube, o se toman de la aplicación, según el
lado que haya cambiado desde la última sincronización.

Un grupo de la aplicación que ningún LED virtual controla (al menos dos
lámparas cargadas en Home Assistant) se propone como nuevo LED virtual entre
los dispositivos «Descubiertos», con sus lámparas en el orden de la
aplicación; «Ignorar» lo mantiene ignorado.

Cuando la decisión le corresponde, se señala una reparación (Ajustes >
Sistema > Reparaciones):

| Reparación | Qué hacer |
| ---------- | --------- |
| Sin cuenta cloud de ReefBeat | La aplicación podría contener el grupo, pero ninguna cuenta en la nube lista sus lámparas: añada la cuenta (la reparación desaparece sola), o mantenga el grupo solo en Home Assistant |
| LED agrupados en la aplicación ReefBeat | El grupo contiene varios modelos, que la aplicación no puede agrupar, y algunas lámparas siguen agrupadas en la aplicación: desagrúpelas allí; el grupo vive entonces solo en Home Assistant |
| Modificado en Home Assistant y en la aplicación ReefBeat | Ambos lados han cambiado desde la última sincronización: elija el grupo que se conserva |

---

[← Volver a la página principal](README.es.md)
