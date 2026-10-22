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
> O modo Poseidon é experimental. Por agora apenas retransmite e observa o
> tráfego: a integração continua a consultar os dispositivos.

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
>   `/config/redsea/poseidon/snapshots/`).
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

> [!NOTE]
> Nenhuma família de dispositivos pode ainda ser juntada: a junção escreve-se a
> partir dos ficheiros espião. Até lá, *Shadow* apenas compara, e *Poseidon*
> lê de novo o dispositivo cada vez que envia um estado.

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

- **Estratégia por omissão**: a dos dispositivos em modo Poseidon que não têm
  uma própria (ver [Estratégias](#estratégias)). *Espião* por omissão.
- **Intervalo de consulta da estratégia Poseidon**, em minutos (10 por
  omissão).
- **Modo debug**: cada trama que atravessa o relé é escrita decifrada em
  `/config/redsea/poseidon/logs/poseidon.jsonl` (rotação aos 10 MB, 5
  ficheiros guardados). Os dados ficam em claro nesse ficheiro.
- **Prazo até um dispositivo ficar silencioso**, em minutos (10 por omissão).
- **Chave do watchdog**: 16 caracteres, proposta enquanto não houver nenhuma.
  Um watchdog noutra máquina (autónomo, ou no
  [reefbeatEnergyBackup](https://github.com/Elwinmage/reefbeatEnergyBackup))
  pergunta ao relé se está vivo, e repõe os dispositivos em modo normal quando
  não está. Copie esta chave para a sua configuração; deixe-a vazia para não
  responder a nenhum watchdog.

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
