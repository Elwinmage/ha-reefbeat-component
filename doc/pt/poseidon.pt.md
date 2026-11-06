[← Voltar à página principal](README.pt.md)

# Modo Poseidon

<p align="center">
<img src="../img/poseidon/poseidon.png" alt="Poseidon" width="240">
</p>

O modo Poseidon coloca um relé entre os seus dispositivos ReefBeat e o broker
MQTT da Red Sea, dentro do Home Assistant. Um dispositivo em modo Poseidon
liga-se ao Home Assistant em vez de `mqtt.reef-beat.com`, e o Home Assistant
transmite o seu tráfego à Red Sea sem o alterar: a app ReefBeat continua a
funcionar como antes.

> [!WARNING]
> O modo Poseidon é experimental. Com a estratégia *Espião*, a predefinida, apenas
> retransmite e observa o tráfego: a integração continua a consultar os
> dispositivos. As estratégias *Shadow* e *Poseidon* usam o que os dispositivos
> enviam (veja [Estratégias](#estratégias)).

## Adicionar o Poseidon

*Definições > Dispositivos e serviços > Red Sea > Adicionar entrada > Modo Poseidon*

- **Porta de escuta**: é proposta a primeira porta livre a partir de 1884
  (1883 e 8883, as portas MQTT habituais, são ignoradas). É verificada de novo
  ao validar e a cada arranque do relé: se outro serviço a ocupar, um aviso de
  reparação indica-o e os dispositivos não são tocados.
- **Endereço do Home Assistant**: o endereço IPv4 pelo qual os dispositivos
  chegam ao Home Assistant.
- **Conta cloud**: a conta cloud ReefBeat usada para obter as chaves dos
  dispositivos. É necessária uma conta cloud.

## Adicionar dispositivos

*Poseidon > Configurar > Adicionar dispositivos*

Cada dispositivo da integração é listado com o seu estado:

| Estado | Significado |
|---|---|
| Selecionável | As suas chaves são conhecidas: passa logo para o modo Poseidon |
| Selecionável, 🔑 | As suas chaves têm de ser obtidas primeiro (ver abaixo) |
| Já em modo Poseidon | Nada a fazer |
| Sem credenciais cloud | Ligado a um aquário local: sem modo Poseidon possível |
| Ausente da conta cloud | As suas chaves não podem ser obtidas com esta conta |
| Inacessível | Não responde |

> [!CAUTION]
> **Obter as chaves é destrutivo.** Um dispositivo não entrega as suas chaves:
> para as obter, é eliminado da cloud ReefBeat e criado de novo.
> - fica desligado do seu aquário, e a app pode pedir para o emparelhar de
>   novo;
> - os programas, predefinições e histórico guardados na cloud para ele podem
>   perder-se;
> - a sua configuração é guardada antes e comparada depois: ReefRun e ReefWave
>   recuperam a sua automaticamente; para os outros dispositivos, o que mudou é
>   listado numa notificação (a configuração guardada fica em
>   `/config/redsea/poseidon/snapshots/`);
> - uma ReefWave depende da cloud, que lhe envia o programa em cada ligação: antes
>   da eliminação são guardadas também as ondas personalizadas do seu aquário (com
>   as intensidades de cada bomba) e o seu programa; a obtenção para, sem eliminar
>   nada, se não puderem ser lidas. Depois, as ondas que a cloud perdeu são recriadas
>   (ou recuperam as definições da bomba), o programa é enviado para a cloud e a
>   cloud envia-o às bombas; a bomba só é escrita diretamente se não o tiver recebido.
>
> A obtenção faz-se uma vez por dispositivo: o Home Assistant guarda as
> chaves, mesmo que o Poseidon seja removido.

## O interruptor Poseidon

Cada dispositivo com chaves conhecidas tem um interruptor **Modo Poseidon** na
sua página:

- **ligado**: o dispositivo fala com a Red Sea através do Home Assistant;
- **desligado**: o dispositivo fala diretamente com a Red Sea (modo normal).

O seu estado é lido no próprio dispositivo. Os seus atributos:

| Atributo | Significado |
|---|---|
| `connection_state` | Estado da ligação indicado pelo dispositivo |
| `last_up` / `last_down` | Último tráfego dispositivo → Red Sea / Red Sea → dispositivo |
| `silent` | Em modo Poseidon, mas nada passou pelo relé durante o prazo das definições |

Um dispositivo silencioso também gera um aviso de reparação, que desaparece
sozinho quando o seu tráfego retoma. Um dispositivo silencioso nunca é reposto
em modo normal automaticamente.

## O que acontece e quando

| Evento | Dispositivos |
|---|---|
| Reinício do Home Assistant, recarga do Poseidon | Ficam como estão: voltam a ligar-se quando o relé regressa |
| Poseidon desativado ou removido | Todos repostos em modo normal |
| Um dispositivo não pode ser reposto em modo normal | Indicado numa notificação |
| O relé cai, um [watchdog](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog) vigia | Todos de volta ao modo normal, depois de confirmado que a Red Sea está acessível; sem watchdog, use o [script de emergência](#script-de-emergência) |
| Um dispositivo aponta para o relé mas nunca se liga a ele (manteve a sessão com a Red Sea) | Forçado a voltar a ligar-se após 2 minutos: apontado de novo à Red Sea e depois ao relé, duas vezes no máximo |

Só se entra em modo Poseidon por decisão sua. Toda a mudança automática repõe
o modo normal.

## Estratégias

O que o Home Assistant faz com um dispositivo em modo Poseidon. Cada
dispositivo tem um seletor **Estratégia Poseidon** ao lado do seu interruptor;
as definições dão o valor por omissão.

| Estratégia | Consulta | Estados enviados | Ficheiro |
|---|---|---|---|
| *Espião* | sem alterações | registados, comparados com a consulta seguinte | `spy.jsonl` |
| *Shadow* | sem alterações | juntados aos dados do dispositivo, comparados com a consulta seguinte | `shadow.jsonl` |
| *Poseidon* | a cada N minutos | usados; o dispositivo é lido de novo a cada estado enquanto a sua família não puder ser juntada | — |

> [!IMPORTANT]
> **Proprietários de ReefATO+, preciso da vossa ajuda.** Não tenho nenhum ReefATO+,
> por isso o modo Poseidon nunca funcionou num: ainda não se sabe o que envia, e
> nada é fundido. Ponha primeiro o seu na estratégia *Espião* e depois, para
> completar o seu suporte:
> - envie-me o seu registo espião (`/config/redsea/poseidon/logs/spy.jsonl`) numa
>   [issue do GitHub](https://github.com/Elwinmage/ha-reefbeat-component/issues),
>   depois de o ler: está decifrado e contém os identificadores dos seus
>   dispositivos;
> - e/ou abra as reparações que o Poseidon levantar pelas suas
>   [mensagens inesperadas](#mensagens-inesperadas): cada uma preenche a issue do GitHub.
>
> Nunca envie o ficheiro das chaves. O aviso sobre a obtenção das chaves aplica-se
> ao ReefATO+ como a qualquer dispositivo.

Famílias fundidas até agora, a partir das sessões espião:

| Família | Fundido |
|---|---|
| ReefControl Power | estados, telemetria (sonda de temperatura incluída); os estados das tomadas são calculados a partir dos seus programas, como faz a app ReefBeat |
| ReefDose | estados, telemetria; um `dosing-log` (fim de uma dose) volta a lê-la, pela sua fila de dosagem, tal como a meia-noite (00:01, hora do Home Assistant), quando a fila do novo dia substitui a do dia que termina |
| ReefMat | estados, telemetria, `rolling-log` (fim de um avanço) |
| ReefLED | telemetria |
| ReefWave | estados (modo: uma alimentação desliga-a e volta a auto, definições), telemetria (modo, sinal wifi); um programa escrito na app (`schedule`, enviado sem os seus intervalos) volta a lê-la. A sua onda atual é deduzida do programa e do relógio: nada envia a mudança de onda no início de um intervalo (só a telemetria a indica, em menos de um minuto) |
| ReefRun | estados, telemetria (estado, intensidade, temperatura das bombas: copo cheio, bomba em falta...); o fim de uma calibração e uma `notification` (uma bomba a religar) voltam a lê-la |
| ReefControl | telemetria e eventos `probe` (leituras das sondas), estados (modo, ligação com um ReefControl Power, modo de fuga), modo e estado das portas (uma porta desligada consome 0; o consumo de uma porta ligada vem pela consulta); uma sonda ou porta instalada ou configurada volta a lê-lo |

Para as outras famílias, *Shadow* só compara, e *Poseidon* volta a ler o dispositivo
sempre que ele envia um estado. *Poseidon* também o volta a ler quando um estado
indica algo que o seu fundidor não sabe escrever (uma definição desconhecida, um
programa de ReefDose, enviado sem os seus intervalos). Essa leitura inclui as fontes
de configuração: o que a app muda são sobretudo definições, que a consulta nunca volta
a ler. Cada comando de escrita da app aceite pelo dispositivo também o volta a ler:
nem toda a definição é enviada (o offset de uma sonda de temperatura não é).

Um ReefControl Power sem tomada controlada por um sensor (com ou sem sonda de
temperatura), uma ReefDose (a sua fila de dosagem é lida depois de cada dose e à
meia-noite) e uma ReefWave (o seu programa é relido quando muda) enviam tudo o que
muda: com *Poseidon*, só são consultados a cada *Intervalo da leitura de segurança*.

### Espião

`/config/redsea/poseidon/logs/spy.jsonl` (rotação aos 10 MB, 5 ficheiros
guardados) contém, com o mesmo relógio:

| `kind` | Registo |
|---|---|
| `publish`, `control` | uma trama entre o dispositivo e a Red Sea, nos dois sentidos, decifrada |
| `http` | um pedido HTTP enviado pelo Home Assistant ao dispositivo: método, endpoint, estado (0 = sem resposta), duração, dados; `origin` é `integration` ou `poseidon` (as suas leituras de `/cloud` a cada 60 s) |
| `compare` | um estado enviado face à consulta seguinte, cada valor `same`, `differs` ou `unknown` |
| `mark` | a estratégia ou a pausa mudou |

Um dispositivo em modo espião tem também um interruptor **Pausa da consulta**:
deixa de receber qualquer pedido, incluindo as leituras de `/cloud` do
Poseidon; o que envia então, envia-o por si. A pausa não sobrevive a um
reinício.

Captura aconselhada, por dispositivo (relógios dos hosts Home Assistant
sincronizados, mesmo fuso horário):

1. 30 minutos sem qualquer consulta: qualquer outro Home Assistant que leia o
   dispositivo parado, a pausa ativa;
2. 30 minutos só com a consulta (pausa desativada);
3. ações a horas anotadas: a partir da app ReefBeat, do Home Assistant, no
   próprio dispositivo;
4. se outro Home Assistant consultar o dispositivo, os seus pedidos juntam-se
   com a ação `logger.set_level`, `custom_components.redsea.reefbeat.api:
   debug`.

## Definições

*Poseidon > Configurar > Definições do Poseidon*

- **Estratégia por omissão**: a de cada dispositivo em modo Poseidon sem estratégia
  própria (veja [Estratégias](#estratégias)). *Espião* por omissão.
- **Intervalo de consulta da estratégia Poseidon**, em minutos (10 por omissão).
- **Modo debug**: cada trama que atravessa o relé é escrita decifrada em
  `/config/redsea/poseidon/logs/poseidon.jsonl` (rotação a 10 MB, 5 ficheiros
  guardados). Os dados ficam em claro nesse ficheiro.
- **Prazo até um dispositivo ficar silencioso**, em minutos (10 por omissão).
- **Intervalo da leitura de segurança**, em minutos (60 por omissão): a consulta de
  um dispositivo cujas mensagens enviadas cobrem tudo o que muda, e a frequência com
  que se lê o `/cloud` de um dispositivo que comunica pelo relé.
- **Assinalar mensagens inesperadas** (ligado por omissão): veja
  [Mensagens inesperadas](#mensagens-inesperadas).
- **Procurar relatos existentes no GitHub** (ligado por omissão): só é enviada a
  assinatura de uma mensagem inesperada.
- **Reter os restauros da nuvem na ligação** (ligado por omissão): veja
  [Proteção na ligação](#proteção-na-ligação).
- **Chave do watchdog**: 16 caracteres, proposta enquanto nenhuma estiver definida. O
  relé responde a um pedido cifrado «estás vivo?» feito com esta chave:
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup#-poseidon-mode-watchdog),
  ou o seu `poseidon_watchdog.py` sozinho noutra máquina, vigia o relé e devolve os
  dispositivos ao modo normal quando ele cai. Copie esta chave para a sua
  configuração; deixe-a vazia para não responder a nenhum watchdog.

## Mensagens inesperadas

Cada mensagem que atravessa o relé é comparada com o que se conhece da família do
dispositivo: um pacote ou topic MQTT desconhecido, um comando da cloud para um
endpoint desconhecido, um estado ou uma telemetria com um campo novo, em falta ou de
outro tipo. A primeira ocorrência vai para
`/config/redsea/poseidon/logs/anomalies.jsonl`, anonimizada (identificadores, nomes,
endereços de rede e chaves removidos); um comando desconhecido espera 5 segundos pelo
que o dispositivo responde e envia, e é escrito com isso.

Cada uma tem uma assinatura, a mesma para todos os utilizadores. As issues do
repositório são pesquisadas com ela, e uma reparação diz o que fazer: relatar (uma
issue do GitHub pré-preenchida, enviada só por si), seguir o relato aberto, atualizar
para a versão que o trata ou ler o relato fechado. Um novo campo de telemetria só
levanta uma reparação quando a pesquisa não encontrou nenhum relato.

## Proteção na ligação

Em cada ligação de um dispositivo, a cloud Red Sea envia-lhe a sua própria cópia das
definições do dispositivo. Quando essa cópia está desatualizada, o dispositivo perde
as atuais: uma ReefWave perdeu assim todo o seu programa. Durante os primeiros 30
segundos de cada ligação pelo relé, os restauros conhecidos da cloud (grupo e programa
de uma ReefWave, cabeça de alimentação de uma ReefDose) são por isso retidos.

Qualquer outro comando passa e é registado (`guard_passed` no ficheiro espião): um
dispositivo que reinicia enquanto a app é usada (um ReefControl que falha ao instalar
uma sonda) recebe os comandos do utilizador.

## Eventos

### `redsea_dose`

Emitido quando uma ReefDose em modo Poseidon (qualquer estratégia) termina uma dose,
programada ou manual, a partir do seu `dosing-log`. Uma dose enviada duas vezes
(depois de uma religação) é emitida uma vez.

| Campo | Conteúdo |
|---|---|
| `device_id` | o dispositivo no Home Assistant |
| `name` | o seu nome |
| `head` | número da cabeça |
| `supplement`, `brand` | tal como indicados pelo dispositivo |
| `dose_type` | `scheduled` ou `manual` |
| `volume` | volume dosado, em mL |
| `started_at` | início da dose, a partir da fila de dosagem consultada antes (hora local do dispositivo); para uma dose que não estava nela (a da meia-noite, manual pela app), estimado a partir do caudal da cabeça; `null` enquanto menos de 3 doses da cabeça tiverem duração medida |
| `ended_at` | fim da dose (hora local do dispositivo) |
| `duration_s` | `ended_at` − `started_at`, `null` sem início |
| `start_estimated` | `true` quando `started_at` (e `duration_s`) são estimados: volume ÷ caudal da cabeça (as suas últimas 20 doses de duração medida) |

Nada é enviado quando uma dose começa: o seu início é a hora que a fila de dosagem
lhe deu. A dose da meia-noite não está em nenhuma fila (a do dia que termina está
então vazia, a do novo dia começa depois): o seu início é estimado.

### `redsea_notification`

Emitido quando um dispositivo em modo Poseidon (qualquer estratégia) envia um alarme,
aquele que a app ReefBeat mostra como notificação. Traz o que o dispositivo indicou:

| Campo | Conteúdo |
|---|---|
| `device_id` | o dispositivo no Home Assistant |
| `name` | o seu nome |
| `device_type` | a sua família: `reef-run`, `reef-control`, `reef-dosing`... |
| `type` | o alarme, tal como o dispositivo o designa |
| `sub_type` | tal como indicado pelo dispositivo (`sub-type`) |
| outros campos | sobre o que é o alarme: `pump` ou `pump_name` (ReefRun), `probe` (ReefControl, o seu nome), `supplement` (ReefDose) |

Vistos até agora:

| Família | `type` |
|---|---|
| ReefRun | `full_cup_warning` (`pump`), `no_pump` (`pump_name`) |
| ReefControl | `sensor_danger_range`, `temperature_danger_range`, `aquarium_water_leak` (`probe`) |
| ReefDose | `stock_level_empty` (`supplement`) |

```yaml
automation:
  - alias: Skimmer cup full
    triggers:
      - trigger: event
        event_type: redsea_notification
        event_data:
          type: full_cup_warning
    actions:
      - action: notify.notify
        data:
          message: "{{ trigger.event.data.name }}: the skimmer cup is full"
```

### Histórico das doses

Cada dose é também guardada, por cabeça, durante 30 dias (5000 doses no máximo),
mesmo depois de reiniciar:

- cada cabeça de uma ReefDose recebe um sensor **Última dose** (no dispositivo da
  cabeça), disponível apenas enquanto o doseador estiver em modo Poseidon: o seu
  estado é o fim da última dose, os seus atributos o volume, tipo, início, duração e
  suplemento; o recorder guarda-os como para qualquer sensor;
- a ação `redsea.get_doses` devolve as doses, da mais recente para a mais antiga:
  `device_id` (o doseador, uma das suas cabeças ou a sua entrada de configuração) e,
  opcionalmente, `head`, `days`, `limit`;
- o ha-reef-card mostra-as na janela de configuração de uma cabeça (**Histórico das
  doses**).

```yaml
automation:
  - alias: Log the doses
    triggers:
      - trigger: event
        event_type: redsea_dose
    actions:
      - action: logbook.log
        data:
          name: "{{ trigger.event.data.name }}"
          message: >-
            head {{ trigger.event.data.head }}
            ({{ trigger.event.data.supplement }}):
            {{ trigger.event.data.volume }} mL,
            {{ trigger.event.data.dose_type }},
            {{ trigger.event.data.started_at }} → {{ trigger.event.data.ended_at }}
```

## Mensagens da app ReefBeat

Os sensores **Última mensagem** e **Última mensagem de alerta** (e o histórico de
mensagens) vêm das respostas dos dispositivos aos envios do Home Assistant, que ficam
em HTTP em todos os modos. Os comandos da app ReefBeat (ou da cloud) chegam a um
dispositivo por MQTT: em modo Poseidon (qualquer estratégia), a resposta do
dispositivo a cada comando de escrita (`command-response`, mesmo `uuid`) alimenta os
mesmos sensores, como faria uma resposta HTTP:

- uma `message` (`settings updated successfully`, `head settings successfully
  saved`...) torna-se a última mensagem;
- um `alert` (`NoMoreDoseAlert`...), `"success": false` ou um estado de erro torna-se
  o último alerta.

As leituras da app (`GET`) não trazem mensagem: ficam de fora. O atributo `origin` de
ambos os sensores, e de cada entrada do histórico (a ação `redsea.get_messages`), diz
de onde veio: `ha` (um envio do Home Assistant) ou `reefbeat` (um comando da app ou da
cloud). O ha-reef-card mostra-o depois da data.

## Exportar e importar as chaves

*Poseidon > Configurar > Exportar as chaves* dá uma ligação de descarga de
todas as chaves conhecidas, válida 5 minutos. O ficheiro é gerado ao clicar e
nunca é escrito em `/config`; está no formato da CLI (`keystore.json`) e contém
as chaves em claro: guarde-o em segurança. A ação `redsea.poseidon_export`,
para automações, escreve o mesmo ficheiro em
`/config/redsea/poseidon/keystore-<data>.json`, legível apenas pelo seu dono.

*Poseidon > Configurar > Importar chaves* pede um ficheiro assim e envia-o a
partir do seu navegador. Um dispositivo só é substituído por um registo mais
recente, os dispositivos sem chaves são ignorados, e os dispositivos importados
recebem logo o seu interruptor.

## Script de emergência

*Poseidon > Configurar > Script de emergência* dá uma ligação de descarga
(5 minutos) para `poseidon_rescue.py`: um script que repõe os dispositivos no
broker da Red Sea sem o Home Assistant, para quando este já não o pode fazer
(parado, relé avariado, integração removida). Corre em qualquer computador da
rede dos dispositivos com Python 3.8 ou superior, nada mais a instalar:

```bash
python3 poseidon_rescue.py --dry-run   # o que seria feito, nada é alterado
python3 poseidon_rescue.py             # os dispositivos no relé, após confirmação
```

| Opção | Utilização |
|---|---|
| `--ip HWID=IP` | um dispositivo mudou de endereço desde a descarga |
| `--scan CIDR` | onde procurar os dispositivos que mudaram de endereço (repetível) |
| `--no-scan` | nunca os procurar |
| `--only HWID` | um só dispositivo (hwid ou nome, repetível) |
| `--all` | todos os dispositivos, seja qual for o broker atual |
| `--keystore keystore.json` | uma exportação do keystore em vez dos dispositivos incluídos |
| `--yes` | sem confirmação |

Nada é escrito num dispositivo antes de este provar ser o certo: o seu `hwid`,
lido em `/device-info`, tem de corresponder. Um dispositivo que já não responde
no seu endereço, ou cujo endereço é agora o de outro, é procurado na rede: o
/24 de cada endereço conhecido e do computador que corre o script, ou as
sub-redes `--scan`.

Cada dispositivo recebe a mesma sequência que a partir do Home Assistant
(desativar, escrever o broker e as chaves, ativar), e depois `/cloud` é lido de
novo para verificar. O script contém as chaves em claro: guarde-o em
segurança, e descarregue-o de novo depois de adicionar dispositivos.
