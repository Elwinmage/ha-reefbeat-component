[← Voltar à página principal](README.pt.md)

# ReefDose:
- Editar a dose diária
- Dose manual
- Adicionar e remover suplementos
- Editar e controlar o volume do recipiente. As definições do volume do recipiente são ativadas ou desativadas automaticamente conforme o interruptor de controlo de volume.
- Ativar/desativar programação por bomba
- Configuração de alertas de stock
- Atraso de dosagem entre suplementos
- Cebagem (Por favor leia [isto](#calibração-e-cebagem))
- Calibração (Por favor leia [isto](#calibração-e-cebagem))

<p align="center">
<img src="../img/rsdose_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="../img/rsdose_main_conf.png" alt="Image">
<img src="../img/rsdose_main_diag.png" alt="Image">
</p>

### Cabeças
<p align="center">
<img src="../img/rsdose_ctrl.png" alt="Image">
<img src="../img/rsdose_sensors.png" alt="Image">
<img src="../img/rsdose_diag.png" alt="Image">
</p>

#### Calibração e cebagem

> [!CAUTION]
> Deve seguir rigorosamente a seguinte ordem (Using the [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) is safer).<br /><br />
> <ins>Calibration</ins>:
>  1. Coloque o recipiente graduado e prima "Iniciar calibração"
>  2. Introduza o valor medido no campo "Dose de calibração"
>  3. Press "Set Calibration Value"
>  4. Esvazie o recipiente graduado e prima "Testar nova calibração". Se o valor obtido não for 4 mL, volte ao passo 1.
>  5. Press "Stop and Save Graduation"
>
> <ins>For priming</ins>:
>  1. (a) Press "Start Priming"
>  2. (b) Quando o líquido sair, prima "Parar preparação"
>  3. (1) Coloque o recipiente graduado e prima "Iniciar calibração"
>  4. (2) Introduza o valor medido no campo "Dose de calibração"
>  5. (3) Press "Set Calibration Value"
>  6. (4) Esvazie o recipiente graduado e prima "Testar nova calibração". Se o valor obtido não for 4 mL, volte ao passo 1.
>  7. (5) Press "Stop and Save Graduation"
>
> ⚠️ A preparação deve ser sempre seguida de uma calibração (passos 1 a 5)!⚠️

<p align="center">
  <img src="../img/calibration.png" alt="Image">
</p>

### Tarefas de manutenção
| Tarefa | Nível | Por omissão | Intervalo |
| ------ | ----- | ----------- | --------- |
| Calibrar as cabeças de doseamento | Aparelho | 90 dias | 80 – 120 dias |
| Substituir cabeças e tubos | Por cabeça | 15 meses | 11 – 19 meses |

A substituição é seguida **por cabeça**: trocar a cabeça 2 não reinicia a
contagem das outras três. Ver a secção [Manutenção](maintenance.pt.md#manutenção).

---

[← Voltar à página principal](README.pt.md)
