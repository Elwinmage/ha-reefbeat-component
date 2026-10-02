[← Voltar à página principal](README.pt.md)

# ReefLED:

- Obter e definir canais Branco e Azul (only for G1: RSLED50, RSLED90, RSLED160)
- Obter e definir Temperatura de Cor, Intensidade e Lua (all LEDs)
- Gerir a aclimatação. Acclimation settings are automatically enabled or disabled according to the acclimation switch.
- Gerir as fases lunares. Moon phase settings are automatically enabled or disabled according to the moon phase switch.
- Definir modo de cor manual com ou sem duração.
- Obter valores de ventilador e temperatura.
- Obter nome e valor dos programas (with cloud support). Only for G1 LEDs.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Image">
</p>

***

O suporte da temperatura de cor dos LED G1 tem em conta as especificidades de cada um dos três modelos.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## IMPORTANTE para as lâmpadas G1 e G2

### LÂMPADAS G2

#### Intensidade
Como os LED G2 garantem uma intensidade constante em toda a gama de cores, os seus LED não usam toda a capacidade no meio do espetro. A 8.000K, o canal branco está a 100 % e o azul a 0 % (o inverso a 23.000K). A 14.000K com 100 % de intensidade nas luzes G2, a potência dos canais branco e azul é de cerca de 85 %.
Eis a curva de perda dos G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
</p>

#### Temperatura de Cor
A interface G2 não suporta toda a gama de temperaturas. De 8.000K a 10.000K, os valores avançam em passos de 200K, e de 10.000K a 23.000K em passos de 500K. Isto é tratado automaticamente: se escolher um valor inválido (p. ex. 8.300K), é selecionado automaticamente um valor válido (8.200K neste exemplo). É por isso que por vezes o cursor se reajusta ligeiramente ao escolher a cor numa luz G2: reposiciona-se num valor permitido.

### LÂMPADAS G1

Os LED G1 são controlados pelos canais branco e azul, o que permite a potência máxima em toda a gama, mas não uma intensidade constante sem compensação.
Por isso foi implementada a compensação de intensidade.
Esta compensação garante o mesmo [PAR](https://en.wikipedia.org/wiki/Photosynthetically_active_radiation) (intensidade luminosa) seja qual for a temperatura de cor escolhida (na gama de 12.000 a 23.000K).
> [!NOTE]
> Como a Red Sea não publica valores de PAR abaixo de 12.000K, a compensação só está disponível na gama de 12.000 a 23.000K. Se tiver um LED G1 e um medidor de PAR, pode [contactar-me](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) para acrescentar a compensação em toda a gama (9.000 a 23.000K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

Por outras palavras, sem compensação, uma intensidade de x % a 9.000K não dá o mesmo PAR que a 23.000K ou a 15.000K.

Eis as curvas de potência:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

Se quiser usar toda a potência do seu LED, desative a compensação de intensidade (predefinição).

Se ativar a compensação de intensidade, a intensidade luminosa será constante em todas as temperaturas de cor, mas no meio da gama não usará toda a capacidade dos seus LED (como nos modelos G2).

Note também que, com a compensação ativa, o fator de intensidade pode ultrapassar 100 % nas luzes G1 se ajustar à mão os canais branco/azul. Assim pode aproveitar toda a potência dos seus LED!

***

### Programa meteorológico
A lâmpada pode seguir o tempo de um local: em **modo meteorológico GPS**, a
sua semana é construída a partir do tempo dos próximos sete dias (previsão)
ou dos sete dias que acabaram de passar (tempo medido), fornecido pelo
[Open-Meteo](https://open-meteo.com) (gratuito, sem chave). Não há nada a
validar: ao ativar o modo, os programas próprios da lâmpada são postos de
lado e a semana meteorológica é enviada de imediato; o tempo é depois
consultado de novo a cada poucos dias (de 3 a 15, à sua escolha; verificado
uma vez por dia, às 00:10) e sempre que uma definição muda (30 s após a
última alteração). Ao desativar o modo, os programas próprios da lâmpada são
escritos de novo.

| Entidade | Função |
| -------- | ------ |
| `switch` Modo tempo GPS | Tempo GPS, ou os programas padrão da lâmpada |
| `select` Período meteorológico | Próxima semana (previsão) ou semana passada (medida) |
| `number` Atualização do tempo (dias) | Dias entre duas consultas do tempo, de 3 a 15 |
| `text` Local meteorológico | `lat, lon`, um URI `geo:` ou uma ligação do Google Maps / OpenStreetMap / Apple Maps; vazio para a casa do Home Assistant |
| `select` Dia meteorológico no aquário | Hora do local, ancorada ao nascer do sol, ao pôr do sol, ou esticada entre ambos |
| `time` Nascer do sol meteorológico / Pôr do sol meteorológico | Horas do aquário usadas por essas âncoras |
| `number` Intensidade mínima meteorológica / Intensidade máxima meteorológica | Limites da intensidade |
| `switch` Nuvens do tempo | Define as nuvens da lâmpada nas horas nubladas |
| `sensor` Programa meteorológico | Resultado da última consulta (estado, local e, para cada dia, sol, horas de sol, nebulosidade e intensidade máxima); `writing` (`{done, total}` dias) enquanto uma semana é enviada para a lâmpada |

Como se constrói um dia:
- **Horários** — do nascer ao pôr do sol do local, à hora do local (um
  recife das Fiji também nasce às 06:00 na lâmpada), ou ancorados ao
  aquário: *nascer do sol* (o dia do local começa à hora escolhida), *pôr do
  sol* (termina à hora escolhida) ou *ambos* (o dia do local é esticado
  entre as duas horas).
- **Intensidade** — segue o sol realmente recebido (radiação solar horária,
  1000 W/m² correspondem a sol pleno), entre o mínimo e o máximo; até 8
  pontos por dia.
- **Cor** — a do programa padrão da lâmpada no mesmo momento do seu dia: o
  seu equilíbrio branco/azul numa G1, a sua temperatura de cor numa G2. Em
  vez disso pode escolher as suas próprias cores, por dia da semana
  (definição `colors`: `{dia: [{at, k}]}`, `at` do nascer, 0, ao pôr do sol,
  1, `k` a temperatura de cor de 8.000 a 23.000 K); uma G1 converte-as com a
  tabela do seu modelo. Esta definição não tem entidade: define-se no editor
  de programas do ha-reef-card, ou com `redsea.led_weather_save`.
- **Nuvens** — nas horas com pelo menos 40 % de nebulosidade: Low, Medium ou
  High consoante a nebulosidade média; removidas num dia limpo.
- **Lua** — mantém o seu lugar depois do pôr do sol.

O programa chama-se *Weather* na lâmpada. Os pedidos escritos numa lâmpada
são espaçados (2 s): uma ReefLED responde tarde, ou não responde, a um
comando enviado cedo de mais; escrever uma semana demora por isso um pouco.

As lâmpadas de um grupo ([LED virtual](virtual-led.pt.md#led-virtual)) partilham um único
programa meteorológico: ativado ou definido em qualquer uma delas, fica
ativado e definido para todas. Cada lâmpada recebe a sua própria semana
meteorológica, no seu formato, e a verificação diária é feita uma só vez,
pelo grupo.

| Serviço | Função |
| ------- | ------ |
| `redsea.led_weather_apply` | Consulta de novo o tempo e envia a semana de imediato (apenas em modo meteorológico), a partir de uma automatização, por exemplo |
| `redsea.led_weather_preview` | A semana que certas definições dariam, e a própria da lâmpada: nada é escrito |
| `redsea.led_weather_save` | Guarda de uma vez as definições e o modo (`enabled`), e depois escreve a semana (em segundo plano, ou antes de responder com `wait`) |

***

### Desfasamento do nascer do sol
Cada ReefLED que responde a `/offset` (verificado no arranque) recebe um
`number` Desfasamento do nascer do sol (minutos): a lâmpada reproduz todo o
seu programa com esse atraso. Num grupo, o
[nascer do sol escalonado](virtual-led.pt.md#led-virtual) do LED virtual define-o para cada
lâmpada.

***

### Biblioteca na nuvem
Com uma conta na nuvem ReefBeat ([API Cloud](README.pt.md#adicionar-api-cloud)), os programas de
luz da biblioteca da aplicação ReefBeat podem ser lidos e escritos, como faz
o editor de programas do ha-reef-card. Os programas G1 são guardados por
aquário, os G2 por conta; os da Red Sea não podem ser alterados nem
eliminados.

| Serviço | Função |
| ------- | ------ |
| `redsea.led_library` | Lista os programas que a lâmpada pode usar (`linked: false` sem conta na nuvem) |
| `redsea.led_library_save` | Adiciona um programa (`name`, `program`, `clouds`), ou atualiza um dos seus (`uid`) |
| `redsea.led_library_delete` | Elimina um dos seus programas (`uid`) |
| `redsea.led_convert` | Converte pontos G1 entre branco/azul e kelvin/intensidade, com a tabela do modelo e a compensação de intensidade |

***

### Tarefas de manutenção
| Tarefa | Por omissão | Intervalo |
| ------ | ----------- | --------- |
| Limpar as lentes | 3 semanas | 1 – 5 semanas |
| Limpar o pó da ventoinha e das grelhas | 6 meses | 5 – 7 meses |

Estas duas tarefas são criadas para todas as gerações de ReefLED, incluindo o
LED virtual. Ver a secção [Manutenção](maintenance.pt.md#manutenção).

---

[← Voltar à página principal](README.pt.md)
