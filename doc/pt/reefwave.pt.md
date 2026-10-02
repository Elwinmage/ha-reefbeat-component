[← Voltar à página principal](README.pt.md)

# ReefWave:
> [!IMPORTANT]
> Os dispositivos ReefWave são diferentes dos outros dispositivos ReefBeat. São os únicos que dependem da nuvem ReefBeat.<br/>
> Quando abre a aplicação ReefBeat, o estado de todos os dispositivos é consultado e os dados da aplicação são obtidos a partir do estado do dispositivo.<br/>
> Com o ReefWave é o contrário: não há ponto de controlo local (como pode ver na aplicação ReefBeat, não é possível adicionar um ReefWave a um aquário desligado).<br/>
> <center><img width="20%" src="../img/reefbeat_rswave.jpg" alt="Image"></center><br />
> As ondas são guardadas na biblioteca do utilizador na nuvem. Quando altera um valor de uma onda, este é alterado na biblioteca da nuvem e aplicado ao novo agendamento.<br/>
> Então não há modo local? Não é tão simples. Existe uma API local oculta para controlar o ReefWave, mas a aplicação ReefBeat não deteta as alterações. Assim, o dispositivo e o Home Assistant por um lado, e a aplicação ReefBeat por outro, ficam dessincronizados. O dispositivo e o Home Assistant estarão sempre sincronizados.<br/>
> Agora que sabe, faça a sua escolha!

> [!NOTE]
> As ondas ReefWave têm muitos parâmetros interligados, e o intervalo de alguns depende de outros. Não consegui testar todas as combinações possíveis. Se encontrar um erro, pode abrir uma issue [aqui](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modos ReefWave
Como explicado acima, os dispositivos ReefWave são os únicos que podem ficar dessincronizados da aplicação ReefBeat se usar a API local.
Estão disponíveis três modos: Cloud, Local e Híbrido.
Pode alterar o modo configurando os interruptores "Ligar à Cloud" e "Usar API Cloud" conforme descrito na tabela abaixo.

<table>
<tr>
<td>Nome do modo</td>
<td>Interruptor Ligar à Cloud</td>
<td>Interruptor Usar API Cloud</td>
<td>Comportamento</td>
<td>ReefBeat e HA estão sincronizados</td>
</tr>
<tr>
<td>Cloud (predefinição)</td>
<td>✅</td>
<td>✅</td>
<td>Os dados são obtidos pela API local. <br />Os comandos de ligar/desligar também são enviados pela API local. <br />Os comandos de ondas são enviados pela API na nuvem.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Os dados são obtidos pela API local. <br />Os comandos são enviados pela API local. <br />O dispositivo aparece como "desligado" na aplicação ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>Os dados são obtidos pela API local. <br />Os comandos são enviados pela API local.<br />A aplicação ReefBeat não mostra os valores corretos das ondas se tiverem sido alterados pelo HA.<br/>O Home Assistant mostra sempre os valores corretos.<br/>Pode alterar os valores tanto na aplicação ReefBeat como no Home Assistant.</td>
<td>❌</td>
</tr>
</table>

Para os modos Nuvem e Híbrido tem de associar a sua conta na nuvem ReefBeat.
Primeiro crie um dispositivo ["Cloud API"](../../README.md#add-cloud-api) com as suas credenciais, e está feito!
O sensor "Ligado à conta" mostrará o nome da sua conta ReefBeat assim que a ligação for estabelecida.
<p align="center">
<img src="../img/rswave_linked.png" alt="Image">
</p>

## Alterar valores atuais
Para carregar os valores atuais da onda nos campos de pré-visualização, use o botão "Pré-vis. a partir do atual".
<p align="center">
<img src="../img/rswave_set_preview.png" alt="Image">
</p>
Para alterar os valores atuais da onda, defina os valores de pré-visualização e use o botão "Guardar pré-visualização".

O comportamento é o mesmo da aplicação ReefBeat. Todas as ondas com o mesmo ID no agendamento atual serão atualizadas.
<p align="center">
<img src="../img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="../img/rswave_conf.png" alt="Image">
<img src="../img/rswave_sensors.png" alt="Image">
<img src="../img/rswave_diag.png" alt="Image">
</p>

## Grupos
Como na aplicação ReefBeat, todas as ReefWave agrupadas de um aquário formam
um só grupo (apenas com uma conta na nuvem).

| Entidade | Função |
| -------- | ------ |
| `switch` Agrupada com o aquário | Agrupa a bomba com as outras ReefWave do seu aquário, ou desagrupa-a; uma bomba que se junta fica em último lugar. Indisponível sem conta na nuvem |
| `sensor` ReefWave ligadas | Número de bombas do grupo, a sua lista no atributo `waves` (`hwid`, `name`, `model`, `entry_id`, `available`) |

Um programa é escrito em todas as bombas do grupo: os mesmos intervalos,
cada bomba com as suas próprias intensidades. Como na aplicação, uma escrita
é recusada quando uma bomba do grupo não está carregada ou não responde:
nada é enviado, pelo que o grupo se mantém sincronizado. Todas as ReefWave
carregadas são atualizadas após uma mudança de grupo.

## Programa do dia
O `sensor` Tipo de onda transporta todo o programa do dia no
atributo `schedule`: a lista dos seus intervalos, cada um começa em `st`
(minuto do dia) e dura até ao seguinte, com `wave_uid`, `name`, `type`,
`direction`, `frt`, `rrt`, `fti`, `rti`, `sn`, `pd` e `sync`. O
ha-reef-card desenha o dia a partir dele.

## Serviços
Estes serviços gerem a biblioteca de ondas e o programa do dia, como faz a
aplicação ReefBeat; os editores do ha-reef-card usam-nos. `device_id` é a
entrada de configuração da ReefWave.

| Serviço | Função |
| ------- | ------ |
| `redsea.wave_library` | Ondas do aquário da bomba, com as intensidades desta bomba, as bombas que usam cada onda e o grupo da bomba. Sem conta na nuvem: as ondas do seu próprio programa |
| `redsea.wave_library_save` | Cria uma onda, ou atualiza uma (`uid`). A forma é partilhada, as intensidades são as da bomba; os programas que usam uma onda atualizada são escritos de novo. As ondas Red Sea e os nomes já usados são recusados |
| `redsea.wave_library_delete` | Elimina uma das suas ondas; recusado para uma onda Red Sea, ou uma onda usada por um programa |
| `redsea.wave_program_save` | Escreve o programa do dia (`slots`: `st`, `wave_uid`, `direction`; o primeiro começa em 0) em todas as bombas do grupo; na própria bomba sem conta na nuvem |
| `redsea.wave_preview` | Executa uma onda na bomba durante 1 a 10 min, e depois volta ao seu programa |
| `redsea.wave_preview_stop` | Para a pré-visualização |
| `redsea.wave_pump_set` | Direção e intensidades desta bomba na onda atual (mesmo uma Red Sea); as outras bombas do grupo não são alteradas |
| `redsea.wave_group_set` | Agrupa ou desagrupa uma bomba (`grouped`), como o interruptor |
| `redsea.wave_group_order` | Ordem das bombas do grupo (`hwids`, cada bomba indicada uma vez) |

A biblioteca precisa de uma conta na nuvem ReefBeat: sem ela,
`wave_library_save` e `wave_library_delete` são recusados. Todas as recusas
são erros traduzidos do Home Assistant.

## Ícones
Os pictogramas de tipo de onda da aplicação estão disponíveis como
`redsea:wave-uniform`, `redsea:wave-random`, `redsea:wave-regular`,
`redsea:wave-step`, `redsea:wave-surface` e `redsea:wave-none`.

### Tarefas de manutenção
| Tarefa | Por omissão | Intervalo |
| ------ | ----------- | --------- |
| Limpar as gaiolas do rotor | 2 meses | 1 – 3 meses |

Ver a secção [Manutenção](maintenance.pt.md#manutenção).

---

[← Voltar à página principal](README.pt.md)
