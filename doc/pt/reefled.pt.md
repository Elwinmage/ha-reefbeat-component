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

### Tarefas de manutenção
| Tarefa | Por omissão | Intervalo |
| ------ | ----------- | --------- |
| Limpar as lentes | 3 semanas | 1 – 5 semanas |
| Limpar o pó da ventoinha e das grelhas | 6 meses | 5 – 7 meses |

Estas duas tarefas são criadas para todas as gerações de ReefLED, incluindo o
LED virtual. Ver a secção [Manutenção](maintenance.pt.md#manutenção).

---

[← Voltar à página principal](README.pt.md)
