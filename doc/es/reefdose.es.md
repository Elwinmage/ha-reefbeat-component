[← Volver a la página principal](README.es.md)

# ReefDose:
- Modificar la dosis diaria
- Dosis manual
- Añadir y eliminar suplementos
- Modificar y controlar el volumen del recipiente. Los ajustes del volumen del recipiente se activan o desactivan automáticamente según el interruptor de control de volumen.
- Activar/desactivar la programación por bomba
- Configuración de alertas de stock
- Retraso de dosificación entre suplementos
- Cebado (Por favor lea [esto](#calibración-y-cebado))
- Calibración (Por favor lea [esto](#calibración-y-cebado))
- [Regulación de dosificación](#regulación-de-dosificación): dosificación asistida y salmuera
- [Historial de las dosis](poseidon.es.md#historial-de-las-dosis), en modo Poseidon

<p align="center">
<img src="../img/rsdose_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="../img/rsdose_main_conf.png" alt="Image">
<img src="../img/rsdose_main_diag.png" alt="Image">
</p>

### Cabezas
<p align="center">
<img src="../img/rsdose_ctrl.png" alt="Image">
<img src="../img/rsdose_sensors.png" alt="Image">
<img src="../img/rsdose_diag.png" alt="Image">
</p>

#### Calibración y cebado

> [!CAUTION]
> Debe seguir estrictamente el siguiente orden (Using the [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) is safer).<br /><br />
> <ins>Calibration</ins>:
>  1. Coloque el recipiente graduado y pulse "Iniciar calibración"
>  2. Introduzca el valor medido en el campo "Dosis de calibración"
>  3. Press "Set Calibration Value"
>  4. Vacíe el recipiente graduado y pulse "Probar nueva calibración". Si el valor obtenido no es 4 mL, vuelva al paso 1.
>  5. Press "Stop and Save Graduation"
>
> <ins>For priming</ins>:
>  1. (a) Press "Start Priming"
>  2. (b) Cuando el líquido salga, pulse "Detener cebado"
>  3. (1) Coloque el recipiente graduado y pulse "Iniciar calibración"
>  4. (2) Introduzca el valor medido en el campo "Dosis de calibración"
>  5. (3) Press "Set Calibration Value"
>  6. (4) Vacíe el recipiente graduado y pulse "Probar nueva calibración". Si el valor obtenido no es 4 mL, vuelva al paso 1.
>  7. (5) Press "Stop and Save Graduation"
>
> ⚠️ ¡El cebado siempre debe ir seguido de una calibración (pasos 1 a 5)!⚠️

<p align="center">
  <img src="../img/calibration.png" alt="Image">
</p>

### Regulación de dosificación

Cada cabezal tiene un selector **Regulación de dosificación**: *Desactivada*, *Dosificación asistida* o *Salmuera (salinidad)*. La [ha-reef-card](https://github.com/Elwinmage/ha-reef-card/blob/main/doc/es/reefdose.es.md#regulación-de-dosificación) reúne sus entidades en el diálogo de configuración del cabezal.

El volumen de agua viene de **Volumen de agua del acuario** cuando lo define; si no, del acuario [ReefTank](https://github.com/Elwinmage/ha-reeftank-component) del dosificador; si no, de su acuario en la nube ReefBeat. El sensor **Volumen de agua usado** indica cuál se aplica.

#### Dosificación asistida

Usted fija un objetivo (por ejemplo KH 8,4 dKH) y registra sus resultados de test. A partir de los resultados y de los volúmenes realmente dosificados entre ellos (el `/daily-log` del dosificador), la integración estima lo que consume el acuario y **propone** una dosis diaria. Nada llega al dosificador hasta que usted lo aplica.

1. Elija el **Parámetro regulado** (KH, calcio, magnesio, potasio, nitrato, fosfato, yodo o hierro) y ajuste el **Objetivo de regulación**.
2. Compruebe la **Potencia del suplemento**: cuánto sube el parámetro 1 mL en 100 L, como indica el envase. Viene rellenada para los suplementos cuya etiqueta la da.
3. Tras cada test, escriba el valor en **Resultado de test** y pulse **Registrar resultado de test**, o llame a `redsea.record_measurement` (útil para un test con fecha: `measured_at`).
4. Cuando **Estado de la regulación** indique *Nueva dosis propuesta*, mire **Dosis diaria propuesta** y pulse **Aplicar dosis propuesta** o **Descartar dosis propuesta**.

La propuesta es lo que consume el acuario más una corrección: la diferencia con el objetivo repartida en los días del **Reparto de la corrección**, nada dentro de la **Tolerancia de regulación**. Se aleja como máximo el **Cambio máx. de dosis** (20 % por defecto) de la dosis actual, y un cambio inferior al 5 % no se propone. Un test demasiado alejado de lo esperado da *Se recomienda repetir el test* en lugar de una propuesta.

> [!NOTE]
> Con cabezales agrupados (Red Sea Complete Reef Care), solo se puede regular el cabezal 1, en dosificación asistida sobre el calcio: el dosificador deduce de él los demás cabezales.

#### Salmuera

El cabezal contiene una salmuera, sal disuelta en agua: el suplemento **DIY - Brine**, el único regulado según la salinidad. Home Assistant lee un sensor de salinidad (una sonda EC de ReefControl o cualquier sensor, selector **Sensor de salinidad**) cada 10 minutos y envía pequeñas dosis manuales para mantener su media de 24 horas en el objetivo (35 ppt por defecto). Usa dosis manuales a propósito, y no el programa del cabezal: cuando Home Assistant está parado no se dosifica nada, y la salinidad solo baja lentamente.

| Ajuste | Por defecto | Uso |
| ------ | ----------- | --- |
| Objetivo de regulación | 35 ppt | Salinidad a mantener |
| Concentración de la salmuera | 200 g/L | Lo que ha preparado |
| Subida máx. de salinidad | 0,5 ppt/día | Corrección más rápida permitida |
| Dosis de salmuera por día | 12 | Reparto del volumen diario |
| Tolerancia del control con refractómetro | 1 ppt | Diferencia aceptada entre el control y la sonda |

**Salmuera prevista por día** da el volumen previsto. Registre cada mes una lectura de refractómetro como resultado de test `salinity`: fuera de tolerancia, la regulación se pausa hasta que la sonda se calibre de nuevo. Sin control durante 45 días, la subida permitida por día se reduce a la mitad.

**Alarma de regulación** se activa, y se emite un evento `redsea_dose_regulation_alarm`, cuando la salinidad es demasiado alta (la salmuera no puede bajarla), cuando no puede devolverse al objetivo, cuando se pierde el sensor y cuando hace falta una recalibración.

### Tareas de mantenimiento
| Tarea | Nivel | Por defecto | Rango |
| ----- | ----- | ----------- | ----- |
| Calibrar los cabezales | Dispositivo | 90 días | 80 – 120 días |
| Sustituir cabezales y tubos | Por cabezal | 15 meses | 11 – 19 meses |

La sustitución se sigue **por cabezal**: cambiar el cabezal 2 no reinicia
la cuenta atrás de los otros tres. Consulta la sección [Mantenimiento](maintenance.es.md#mantenimiento).

---

[← Volver a la página principal](README.es.md)
