[← Volver a la página principal](README.es.md)

# ReefRun:
- Ajustar la velocidad de la bomba
- Gestión del sobredesnatado
- Gestión de la detección de vaso lleno
- Posibilidad de cambiar el modelo de skimmer

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Image">
</p>

### Bombas
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Image">
</p>

### Tareas de mantenimiento
Las tareas se asocian al subdispositivo bomba y dependen de su tipo.

| Tarea | Bomba | Por defecto | Rango |
| ----- | ----- | ----------- | ----- |
| Limpiar motor y rotor | Retorno | 4,5 meses | 2 – 7 meses |
| Limpiar el filtro de aspiración | Retorno | 6 semanas | 3 – 9 semanas |
| Limpiar venturi y tubo de aire | Skimmer | 5 semanas | 3 – 7 semanas |
| Limpiar el rotor del skimmer | Skimmer | 4,5 meses | 2 – 7 meses |
| Calibrar la sonda de copa llena | Skimmer | 4 semanas | 2 – 6 semanas |
| Calibrar la sonda de sobre-espumado | Skimmer | 4 semanas | 2 – 6 semanas |

Las dos tareas de calibración también las vigila el blueprint de alertas, que
compara la fecha de última calibración informada por el aparato con el intervalo
definido aquí. Consulta la sección [Mantenimiento](maintenance.es.md#mantenimiento).

### Llave para desmontar el rotor

La tarea *Limpiar el rotor del skimmer* de arriba obliga a
desenroscar el cuerpo de la bomba, que mojado apenas ofrece agarre. Una llave
imprimible en 3D para esa tarea, con un vídeo de uso, está disponible aquí:
[Llave para rotor de DC Skimmer Red Sea](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

---

[← Volver a la página principal](README.es.md)
