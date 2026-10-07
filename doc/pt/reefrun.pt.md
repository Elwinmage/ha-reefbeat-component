[← Voltar à página principal](README.pt.md)

# ReefRun:
- Ajustar a velocidade da bomba
- Gerir o sobredesnatamento
- Gerir a deteção de copo cheio
- Possibilidade de alterar o modelo de skimmer

<p align="center">
<img src="../img/rsrun_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="../img/rsrun_main_sensors.png" alt="Image">
<img src="../img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="../img/rsrun_main_conf.png" alt="Image">
<img src="../img/rsrun_main_diag.png" alt="Image">
</p>

### Bombas
<p align="center"><img src="../img/rsrun_ctrl.png" alt="Image">
<img src="../img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="../img/rsrun_sensors.png" alt="Image">
<img src="../img/rsrun_diag.png" alt="Image">
</p>

### Tarefas de manutenção
As tarefas são associadas ao subaparelho bomba e dependem do seu tipo.

| Tarefa | Bomba | Por omissão | Intervalo |
| ------ | ----- | ----------- | --------- |
| Limpar motor e rotor | Retorno | 4,5 meses | 2 – 7 meses |
| Limpar o filtro de aspiração | Retorno | 6 semanas | 3 – 9 semanas |
| Limpar venturi e tubo de ar | Escumador | 5 semanas | 3 – 7 semanas |
| Limpar o rotor do escumador | Escumador | 4,5 meses | 2 – 7 meses |
| Calibrar a sonda de copo cheio | Escumador | 4 semanas | 2 – 6 semanas |
| Calibrar a sonda de sobre-escumação | Escumador | 4 semanas | 2 – 6 semanas |

As duas tarefas de calibração são também vigiadas pelo blueprint de alertas, que
compara a data da última calibração comunicada pelo aparelho com o intervalo
definido aqui. Ver a secção [Manutenção](maintenance.pt.md#manutenção).

### Chave para desmontar o rotor

A tarefa *Limpar o rotor do escumador* acima obriga a desenroscar o
corpo da bomba, que molhado quase não oferece pega. Uma chave imprimível em 3D
para essa operação, com um vídeo de utilização, está disponível aqui:
[Chave para rotor de DC Skimmer Red Sea](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

---

[← Voltar à página principal](README.pt.md)
