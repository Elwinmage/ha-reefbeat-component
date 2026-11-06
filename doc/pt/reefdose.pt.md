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
- [Regulação da dosagem](#regulação-da-dosagem): dosagem assistida e salmoura
- [Histórico das doses](poseidon.pt.md#histórico-das-doses), em modo Poseidon

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

### Regulação da dosagem

Cada cabeça tem um seletor **Regulação da dosagem**: *Desligada*, *Dosagem assistida* ou *Salmoura (salinidade)*. O [ha-reef-card](https://github.com/Elwinmage/ha-reef-card/blob/main/doc/pt/reefdose.pt.md#regulação-da-dosagem) reúne as suas entidades na janela de configuração da cabeça.

O volume de água vem de **Volume de água do aquário** quando o define; senão, do aquário [ReefTank](https://github.com/Elwinmage/ha-reeftank-component) do doseador; senão, do seu aquário na cloud ReefBeat. O sensor **Volume de água usado** indica qual se aplica.

#### Dosagem assistida

Define um alvo (por exemplo KH 8,4 dKH) e regista os seus resultados de teste. A partir dos resultados e dos volumes realmente dosados entre eles (o `/daily-log` do doseador), a integração estima o que o aquário consome e **propõe** uma dose diária. Nada chega ao doseador até a aplicar.

1. Escolha o **Parâmetro regulado** (KH, cálcio, magnésio, potássio, nitrato, fosfato, iodo ou ferro) e defina o **Alvo de regulação**.
2. Verifique a **Potência do suplemento**: quanto 1 mL sobe o parâmetro em 100 L, como indicado no frasco. Vem preenchida para os suplementos cujo rótulo a indica.
3. Depois de cada teste, introduza o valor em **Resultado do teste** e prima **Registar resultado do teste**, ou chame `redsea.record_measurement` (útil para um teste datado: `measured_at`).
4. Quando **Estado da regulação** indicar *Nova dose proposta*, veja **Dose diária proposta** e prima **Aplicar dose proposta** ou **Ignorar dose proposta**.

A proposta é o que o aquário consome mais uma correção: a diferença para o alvo distribuída pelos dias da **Distribuição da correção**, nada dentro da **Tolerância de regulação**. Afasta-se no máximo a **Variação máx. da dose** (20 % por omissão) da dose atual, e uma alteração inferior a 5 % não é proposta. Um teste demasiado afastado do esperado dá *Novo teste recomendado* em vez de uma proposta.

> [!NOTE]
> Com cabeças agrupadas (Red Sea Complete Reef Care), só a cabeça 1 pode ser regulada, em dosagem assistida pelo cálcio: o doseador deduz dela as outras cabeças.

#### Salmoura

A cabeça contém uma salmoura, sal dissolvido em água: o suplemento **DIY - Brine**, o único regulado pela salinidade. O Home Assistant lê um sensor de salinidade (uma sonda EC do ReefControl ou qualquer sensor, seletor **Sensor de salinidade**) a cada 10 minutos e envia pequenas doses manuais para manter a sua média de 24 horas no alvo (35 ppt por omissão). Usa doses manuais de propósito, e não o programa da cabeça: quando o Home Assistant está parado nada é dosado, e a salinidade apenas desce lentamente.

| Definição | Por omissão | Uso |
| --------- | ----------- | --- |
| Alvo de regulação | 35 ppt | Salinidade a manter |
| Concentração da salmoura | 200 g/L | O que preparou |
| Subida máx. de salinidade | 0,5 ppt/dia | Correção mais rápida permitida |
| Doses de salmoura por dia | 12 | Repartição do volume diário |
| Tolerância do controlo com refratómetro | 1 ppt | Diferença aceite entre o controlo e a sonda |

**Salmoura prevista por dia** dá o volume previsto. Registe todos os meses uma leitura do refratómetro como resultado de teste `salinity`: fora da tolerância, a regulação fica em pausa até a sonda ser recalibrada. Sem controlo durante 45 dias, a subida permitida por dia é reduzida a metade.

**Alarme de regulação** liga-se, e é emitido um evento `redsea_dose_regulation_alarm`, quando a salinidade está demasiado alta (a salmoura não a pode baixar), quando não pode voltar ao alvo, quando o sensor se perde e quando é necessária uma recalibração.

### Tarefas de manutenção
| Tarefa | Nível | Por omissão | Intervalo |
| ------ | ----- | ----------- | --------- |
| Calibrar as cabeças de doseamento | Aparelho | 90 dias | 80 – 120 dias |
| Substituir cabeças e tubos | Por cabeça | 15 meses | 11 – 19 meses |

A substituição é seguida **por cabeça**: trocar a cabeça 2 não reinicia a
contagem das outras três. Ver a secção [Manutenção](maintenance.pt.md#manutenção).

---

[← Voltar à página principal](README.pt.md)
