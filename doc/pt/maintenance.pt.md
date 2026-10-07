[← Voltar à página principal](README.pt.md)

# Manutenção

Para além de controlar o equipamento, a integração acompanha as **tarefas de
manutenção recorrentes** do seu material: limpar o venturi de um escumador,
substituir os tubos de uma bomba doseadora, trocar o carvão ativado do ReefMat…
É o Home Assistant que se lembra, já não o utilizador.

As tarefas são associadas ao aparelho correspondente e ao **subaparelho** quando
isso é mais preciso: uma cabeça de ReefDose, uma bomba de ReefRun. Um ReefRun
expõe as tarefas da bomba de retorno na bomba 1 e as do escumador na bomba 2,
nunca ao contrário: a lista segue o tipo de bomba comunicado pelo aparelho.

## As três entidades de uma tarefa

Cada tarefa cria três entidades, todas nas categorias *Configuração* e
*Diagnóstico* para não sobrecarregar o painel principal:

| Entidade | Função |
| -------- | ------ |
| `button.<aparelho>_<tarefa>` | **Tarefa realizada.** Premir regista a data atual como última realização e reinicia a contagem decrescente. |
| `number.<aparelho>_<tarefa>_interval_<unidade>` | **Intervalo.** Com que frequência a tarefa deve ser repetida, em dias, semanas ou meses conforme o caso. |
| `switch.<aparelho>_<tarefa>_notify` | **Notificações.** Silencia o alerta de atraso apenas dessa tarefa, sem alterar o seu prazo. |

O botão é a entidade que guarda o estado. Tudo o que dele deriva é exposto em
atributos, pelo que basta uma entidade para construir um painel ou uma
automação:

| Atributo | Significado |
| -------- | ----------- |
| `last_reset` | Data ISO-8601 da última pressão, ou `null` se nunca foi feita |
| `interval_days` | Intervalo atual, sempre normalizado em dias |
| `days_left` | Dias restantes, negativo depois de ultrapassado o prazo |
| `overdue` | `true` assim que `days_left` fica negativo |
| `reef_role` | `maint_<chave_da_tarefa>`, o marcador estável usado para descobrir as tarefas |

> [!TIP]
> É o `reef_role` que torna o conjunto extensível: o cartão e o blueprint de
> alertas descobrem as tarefas procurando este atributo. Uma tarefa adicionada
> numa versão futura da integração aparece em ambos sem qualquer atualização do
> lado deles.

## Intervalos

Os intervalos por omissão seguem as recomendações da Red Sea, usando a mediana
do intervalo publicado. Cada tarefa define também um mínimo e um máximo,
impostos pela entidade `number`: pode adaptar um intervalo à carga do seu
aquário, mas não definir um valor absurdo.

Os intervalos são apresentados na unidade que faz sentido para a tarefa (semanas
para um venturi, meses para um rotor) e guardados internamente em dias, pelo que
mudar de unidade nunca perde precisão.

## Persistência

Datas e intervalos são guardados pelo Home Assistant em
`.storage/redsea_maintenance_<entry_id>`, um ficheiro por entrada de
configuração. Sobrevivem a reinícios, recargas da integração e reinícios dos
aparelhos, e **nunca são enviados para a nuvem da Red Sea**. Remover a entrada
de configuração remove também o ficheiro.

## A vista de manutenção do ha-reef-card

O cartão companheiro [ha-reef-card](https://github.com/Elwinmage/ha-reef-card)
reúne todas as tarefas da instalação numa vista dedicada, como se a manutenção
fosse um aparelho por si só: uma barra de progresso por tarefa, colorida
conforme o tempo restante, ordenável por equipamento ou por prazo, com um botão
para marcar a tarefa como feita, um sino para a silenciar e um cursor em linha
para alterar o seu intervalo.

<p align="center">
<img src="../img/maintenance_task.png" alt="Tarefas de manutenção no ha-reef-card">
</p>

## Notificações: o blueprint de alertas

A integração não notifica por si própria, e isso é intencional: a quem avisar,
quando e como é decisão sua. Esse papel cabe ao blueprint **ReefBeat watch**
incluído no repositório, que cobre também os modos anómalos, as calibrações em
atraso, as baterias fracas e os aparelhos inacessíveis.

### Instalação

Clique no botão abaixo e confirme a importação no Home Assistant:

[![Abrir a sua instância do Home Assistant e mostrar a caixa de diálogo de importação de blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-reefbeat-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fredsea_alerts.en.yaml)

Existe também uma versão francesa,
[`redsea_alerts.fr.yaml`](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/blueprints/automation/redsea_alerts.fr.yaml).
Em alternativa, copie o ficheiro para
`config/blueprints/automation/redsea_alerts/` e recarregue as automações.

Depois crie uma automação a partir do blueprint:
*Definições → Automações e cenas → Criar automação → Usar um blueprint →
ReefBeat watch (redsea)*.

### Configuração

Apenas o primeiro campo é obrigatório:

| Secção | Função |
| ------ | ------ |
| **Destinos de notificação** | Os telemóveis a avisar, escolhidos no seletor de aparelhos. O serviço `notify.mobile_app_*` é resolvido automaticamente. Pode indicar-se um canal de notificação Android (`ReefBeat` por omissão). |
| **Manutenção em atraso** | Alerta quando uma tarefa ultrapassa o seu prazo. A opção *Respeitar os interruptores de notificação por tarefa* (ativa por omissão) faz a automação obedecer às entidades `switch.*_notify`: silenciar uma tarefa no cartão silencia também a automação. |
| **Modo anómalo** | Alerta quando um aparelho sai do modo esperado. `off_grace_minutes` (5 por omissão) evita falsos alertas durante um ciclo de alimentação ou uma intervenção manual curta. |
| **Calibração em atraso** | Cabeças de ReefDose e calibrações de escumador ReefRun. |
| **Atraso de calibração das sondas (RSRUN)** | Sondas de copo cheio e de sobre-escumação dos escumadores ReefRun. |
| **Mensagem de alerta do aparelho** | Retransmite as mensagens de alerta enviadas pelos próprios aparelhos. |
| **Bateria fraca** / **Aparelho inacessível** | Sem surpresas. |

Cada secção pode ser desativada de forma independente e tem a sua própria
**lista de exclusão**: um aparelho em testes não o inunda de alertas enquanto os
restantes continuam vigiados. A automação corre num ciclo de 5 minutos e tem em
conta os aparelhos adicionados ou removidos da integração no ciclo seguinte, sem
alterar nada.

> [!NOTE]
> O blueprint vigia **todos** os aparelhos da integração e os seus
> subaparelhos. Não há nada a declarar quando adiciona um novo aparelho
> ReefBeat.

---

[← Voltar à página principal](README.pt.md)
