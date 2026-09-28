[← Voltar à página principal](README.pt.md)

# ReefControl:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_devices.png" alt="Image">
</p>

O hub ReefControl (RSCONTROLPRO / RSCONTROLLITE) lê as sondas ReefSense ligadas às suas caixas de extensão, controla as suas portas 12V DC (2 no Pro, 1 no Lite) e, depois de emparelhado, as tomadas de um [ReefControl-Power](reefcontrol-power.pt.md#reefcontrol-power).

- **Sondas ReefSense** — pH, ORP, salinidade (EC), temperatura, ATO (nível de água) e fuga: valor e nível (desejado / aceitável / perigo), estado, nome, uid, datas da última instalação e da última calibração, e a temperatura integrada das sondas de pH, EC e ATO. Cada entidade de sonda tem os atributos `probe_uid`, `probe_type` e `probe_index`, e os sensores de medida um atributo `ranges` (`[acceptable_low, desired_low, desired_high, acceptable_high]`).
- **Sondas de salinidade** — sensores de condutividade, salinidade (ppt) e densidade, mais um select da unidade de apresentação.
- **Sondas de fuga** — estado seco/molhado, **origem da água** (seco / água do aquário / água osmotizada) e a condutividade medida, lidos assim que a sonda deteta água.
- **Definições por sonda** — intervalos desejado e aceitável (leitura principal e temperatura integrada), interruptores ativada / buzzer / notificações / manutenção, e um botão «Ler agora» que obtém uma leitura nova sem esperar pela próxima consulta.
- **Calibração das sondas** — ver [mais abaixo](#calibração-das-sondas).
- **Buzzer** — buzzer de perigo e buzzer de fuga (ativação, frequência, ciclo de trabalho), anti-ressalto do perigo, interruptor do detetor de fugas; estado ativo / silenciado do buzzer e a sua causa.
- **Portas 12V** — nome editável, interruptor ligar/desligar, estado, modo, tipo, consumo e um botão «Desinstalar porta». O sensor `port_N_mode` tem como atributos toda a configuração da porta, o seu programa e a sua regra de sonda, para que um cartão possa editar a porta (ver [Modos das portas e das tomadas](#modos-das-portas-e-das-tomadas)).
- **Emparelhamento com ReefControl-Power** — Power Center emparelhado, o seu estado e ligação, botões «Emparelhar Power Center» / «Desemparelhar Power Center», e um botão «Cancelar subscrição tomada» por cada tomada do Power Center que o hub controla a partir de uma sonda.
- **Adicionar, substituir ou remover sondas** a partir do menu de opções da integração (ver [mais abaixo](#gestão-de-sondas-adicionar--substituir--remover)).
- As escritas aparecem de imediato (atualização otimista) e são depois confirmadas por uma nova leitura do aparelho.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_diag.png" alt="Image">
</p>

> [!TIP]
> O [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) desenha o hub, as suas sondas, as suas portas e o Power Center emparelhado, e trata das calibrações e dos modos das portas em poucos cliques.

## Gestão de sondas (adicionar / substituir / remover)
As sondas BLE (pH, ORP, EC, ATO, fuga, temperatura) são geridas a partir do menu **Opções** da integração, tal como na aplicação Red Sea:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_probe_management.png" alt="Image">
</p>

- **Adicionar uma sonda**: coloque a sonda em modo de emparelhamento, escolha o seu tipo e confirme para a procurar. A sonda é configurada como faz a aplicação: uma sonda de fuga, por exemplo, recebe o nome `Leak <uid>`, com buzzer, detetor de fugas e notificações ativados.
- **Substituir uma sonda**: escolha a sonda a substituir, coloque uma sonda nova do mesmo tipo em modo de emparelhamento e confirme. A nova sonda herda o histórico e as estatísticas da anterior.
- **Remover uma sonda**: selecione uma ou mais sondas e confirme — isto apaga definitivamente as entidades da sonda e o seu histórico.

> [!NOTE]
> Reinstalar uma sonda repõe as suas definições no hub (uma sonda ORP volta aos intervalos de fábrica). A integração volta a ler a configuração das sondas sempre que uma sonda aparece ou é reinstalada, seja a partir do Home Assistant ou da aplicação ReefBeat.

## Calibração das sondas
Cada tipo de sonda é calibrado como na aplicação ReefBeat.

| Sonda | Como | Entidade / serviço |
| ----- | ---- | ------------------ |
| ORP | Mergulhe a sonda na solução de calibração e defina o número com o valor da solução | `Calibrar {probe} (valor da solução)` |
| Temperatura | Defina o número com a temperatura real da água onde está a sonda | `Calibrar {probe} (temperatura real)` |
| Temperatura integrada (pH, EC, ATO) | Igual, para o sensor de temperatura integrado na sonda | `Calibrar a temperatura de {probe} (temperatura real)` |
| pH | Dois pontos: pH 7, depois pH 10 (água salgada) ou pH 4 (água doce) | `redsea.probe_calibration` |
| Salinidade (EC) | Um ponto, com o valor da solução em mS/cm | `redsea.probe_calibration` |

Os **números de valor de referência** (ORP e temperaturas) mostram a leitura atual. Definir um deles com a referência volta a ler a sonda e desloca o seu offset em `referência - leitura`, para que a sonda passe a ler a referência.

As **calibrações de pH e EC** têm vários passos e usam o serviço `redsea.probe_calibration`, um passo por chamada: `enter`, depois `point` para cada ponto de calibração, `status` consultado até o hub indicar sucesso ou falha (entretanto devolve `calibration_status`, `time_left` e `stability_progress`) e por fim `exit`. O [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) executa toda a sequência por si.

```yaml
action: redsea.probe_calibration
data:
  device_id: <config entry of the hub>
  probe_type: ph
  probe_uid: "0x00B39"
  action: point
  point: MID
  solution_value: 7.0
  solution_rated_temp: 25
```

A data da última calibração vem do hub: uma sonda de pH ou EC calibrada na aplicação ReefBeat, ou uma sonda ORP verificada, marca a sua tarefa de manutenção como feita nessa data.

## Fusão de temperatura multi-sonda
Assim que existem duas ou mais fontes de temperatura (a sonda de temperatura dedicada mais a temperatura embutida nas sondas EC/pH/ATO), o ReefControl calcula uma **temperatura fundida** robusta a partir das leituras individuais:

- **Temperatura fundida** (`sensor`): um único valor agregado com o método escolhido — Mediana (predefinição), Média, Mínimo ou Máximo. Configurável através da entidade select **Método de fusão de temperatura**.
- **Coerência de temperatura** (`binary_sensor`) e **Amplitude de temperatura** (`sensor`, diagnóstico): indicam se as fontes concordam dentro do **Limiar de coerência de temperatura** (configurável, 0,5 °C por predefinição), e em que medida diferem.
- **Origem de anomalia de temperatura** (`sensor`, diagnóstico): `OK` quando todas as fontes concordam, o nome da(s) sonda(s) suspeita(s) de deriva ou leitura incorreta, ou `Desconhecida` quando a discrepância não pode ser atribuída a uma sonda concreta. Os atributos do sensor detalham cada fonte com o seu valor, variação numa hora e estado.
- Um **interruptor de manutenção por sonda com capacidade de temperatura**: ativá-lo exclui temporariamente essa sonda do cálculo de fusão/coerência/anomalia, para que a sua limpeza ou calibração nunca desencadeie um falso alarme.
- Uma **calibração com a temperatura real** (`number`) por sonda com capacidade de temperatura (ver [Calibração das sondas](#calibração-das-sondas)).

Estas entidades só aparecem quando são detetadas pelo menos duas fontes de temperatura.

## Modos das portas e das tomadas
Uma porta 12V do hub, tal como uma tomada do Power Center, funciona num de quatro modos: **off**, **on**, **schedule** (programa) ou **sensor** (controlada por uma sonda). Uma porta ainda não instalada está no modo `setup` e recusa qualquer escrita até ser instalada.

Estas definições não são expostas como entidades individuais — com várias portas e tomadas e um conjunto de limiares por tipo de sonda, seriam dezenas de entidades pouco usadas. Configure-as a partir do [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), que faz as mesmas chamadas que a aplicação ReefBeat numa única ação através do serviço `redsea.request` (ver os Serviços da integração nas Ferramentas de programador do Home Assistant).

O sensor `port_N_mode` tem ainda tudo o que uma automação precisa para ler a configuração ativa: `config` (a entrada completa da porta, incluindo `power_on_percent`), `schedule` (lido do hub enquanto a porta está em modo programa) e `sensor_config` (a regra de sonda), com `sensor_source: control`.

## Módulo ATO (kit ATO Red Sea)
O kit ATO Red Sea — uma bomba numa porta de 12V e uma sonda ATO — instala-se como o assistente da aplicação, a partir do menu **Opções** da integração:

1. **Adicionar uma sonda** do tipo `ato` (chama-se `ATO Temp. <uid>`, pela sua temperatura, como na aplicação).
2. **Instalar o módulo ATO**: escolha a porta de 12V livre, a sonda ATO, o volume do reservatório (L), o comprimento e a altura do tubo (cm, da bomba ao aquário; a altura é quanto sobe acima da bomba), o enchimento automático e a monitorização do reservatório.

A porta passa a ser do tipo `ato` e recebe as entidades do módulo: estado (`OK` ou a falha indicada: bomba ausente, bomba bloqueada, reservatório vazio, tempo de enchimento excedido, fuga, falha da porta), falha e bomba (sensores binários), volume de hoje / restante (mL), causa do último enchimento, interruptores de enchimento automático, monitorização do reservatório, notificações e registo de temperatura, números para o volume restante do reservatório, comprimento/altura do tubo (cm) e caudal (0,2 a 4 L/min, 0 = predefinido), e botões para retomar (apenas com uma falha), encher manualmente e parar.

Desinstalar a porta remove o módulo; recarregue a integração para eliminar as suas entidades.

## Tarefas de manutenção
| Tarefa | Sondas | Predefinição | Intervalo |
| ------ | ------ | ------------ | --------- |
| Limpar a sonda | Todas | 30 dias | 2 – 8 semanas |
| Calibrar a sonda | pH | 3 meses | 2 – 4 meses |
| Calibrar a sonda | Salinidade (EC) | 2 meses | 1 – 3 meses |
| Verificar a sonda | ORP | 6 meses | 5 – 7 meses |
| Substituir a sonda | pH, ORP | 12 meses | 9 – 18 meses |

As tarefas são acompanhadas **por sonda**, segundo as recomendações oficiais da Red Sea. As sondas de temperatura e de fuga não têm lembrete de calibração, e a célula EC de 4 polos nunca é substituída segundo um calendário. Ver a secção [Manutenção](maintenance.pt.md#manutenção).

---

[← Voltar à página principal](README.pt.md)
