[← Voltar à página principal](README.pt.md)

# ReefControl-Power

O RSPOWER (Power Center) é um aparelho autónomo com o seu próprio endereço IP, exposto separadamente no Home Assistant.

<p align="center">
<img src="../img/rspower_devices.png" alt="Image">
</p>

- 6 ou 8 tomadas controláveis consoante o modelo (RSPOWER6 / RSPOWER8)
- **Por tomada**: nome editável, interruptor ligar/desligar, estado, modo, modo anterior, consumo e um botão «Eliminar tomada» que repõe a tomada no estado de fábrica (modo `setup`, nome de fábrica)
- **Aparelho**: consumo total, nível da bateria, modo, região do modelo e número de tomadas
- **Sonda de temperatura local** (opcional): botões para adicionar / remover, botão «Obter temperatura», calibração com a temperatura real, intervalos de temperatura desejado e aceitável, nome, interruptores de notificações e registo — tudo disponível depois de instalada a sonda. O sensor de temperatura tem os atributos `ranges` e `level`, como as sondas do hub.
- **Emparelhamento ReefControl**: hub emparelhado, o seu tipo e estado, estado da ligação e da internet, e um botão «Desemparelhar hub de controlo»
- As escritas aparecem de imediato (atualização otimista) e são depois confirmadas por uma nova leitura do aparelho

<p align="center">
<img src="../img/rspower_ctrl.png" alt="Image">
<img src="../img/rspower_conf.png" alt="Image">
<img src="../img/rspower_diag.png" alt="Image">
</p>

> [!NOTE]
> A sonda de temperatura local e o hub ReefControl excluem-se: «Adicionar sonda de temperatura» só está disponível sem nenhum dos dois, «Remover sonda de temperatura» com uma sonda local e «Desemparelhar hub de controlo» com um hub emparelhado. Os botões continuam visíveis mas indisponíveis quando não se aplicam.

## Emparelhamento com um ReefControl
O emparelhamento inicia-se sempre a partir do hub, com o seu botão **Emparelhar Power Center**: o hub emparelha-se com o Power Center que encontra na rede. O desemparelhamento funciona dos dois lados. Quando os dois aparelhos estão configurados no Home Assistant, a alteração aparece em ambos ao mesmo tempo — num emparelhamento, apenas quando um único Power Center livre não deixa dúvidas sobre qual é.

Depois de emparelhado, as sondas do hub podem controlar as tomadas. O Power Center guarda apenas o tipo de sonda que uma tomada segue; a própria sonda e os limiares ficam no hub. Dois serviços permitem a um cartão ou a uma automação ler esse lado:

- `redsea.get_control_probes` — as sondas de um hub (identidade e valores atuais), pelo seu identificador de hardware
- `redsea.get_control_subscriptions` — as regras que o hub aplica às tomadas do seu Power Center, pelo seu identificador de hardware

Eliminar uma tomada no Power Center apaga apenas a sua metade de uma regra de sonda: o botão **Cancelar subscrição tomada N** do hub apaga a outra metade.

## Modo das tomadas e tomadas controladas por sensor
O modo de uma tomada (off / on / schedule / sensor) e as suas definições de programa ou de limiar de sensor (por ex. «ligar esta tomada quando a temperatura local descer abaixo de 24 °C») configuram-se a partir do [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), tal como as [portas do hub](reefcontrol.pt.md#modos-das-portas-e-das-tomadas).

Cada tomada expõe uma entidade `sensor.socket_N_mode` para as automações: o seu estado é o modo atual da tomada, e os seus atributos têm o `schedule` atual e (em modo sensor) a `sensor_config`, marcada por `sensor_source`: `local` para a sonda própria do Power Center, `control` para uma regra do hub emparelhado.

Uma tomada controlada por um programa ou por uma sonda pode ser desligada à mão: o seu modo indica então `off`, enquanto o sensor **modo anterior** guarda o modo automático para o qual voltará.

O aparelho sai automaticamente do seu estado inicial «setup» assim que a primeira tomada é configurada, tal como a aplicação ReefBeat — não é necessária qualquer ação manual.

---

[← Voltar à página principal](README.pt.md)
