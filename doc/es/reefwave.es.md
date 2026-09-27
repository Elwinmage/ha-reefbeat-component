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

### Tareas de mantenimiento
| Tarea | Por defecto | Rango |
| ----- | ----------- | ----- |
| Limpiar las jaulas del rotor | 2 meses | 1 – 3 meses |

Consulta la sección [Mantenimiento](maintenance.es.md#mantenimiento).

---

[← Volver a la página principal](README.es.md)
