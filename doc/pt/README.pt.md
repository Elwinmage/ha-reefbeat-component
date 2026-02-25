[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/commits/main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=clones&query=count&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-reefbeat-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

<!-- [![Clones GitHub](https://img.shields.io/badge/dynamic/json?color=success&label=uniques-clones&query=uniques&url=https://gist.githubusercontent.com/Elwinmage/cd478ead8334b09d3d4f7dc0041981cb/raw/clone.json&logo=github)](https://github.com/MShawon/github-clone-count-badge) -->

# Apresentação
***Gestão local de dispositivos HomeAssistant RedSea Reefbeat (sem nuvem): ReefATO+, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave***

> [!TIP]
> ***Para editar a programação avançada do ReefDose, ReefLed, ReefRun e ReefWave, é necessário usar o [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) (em desenvolvimento)***

> [!TIP]
> A lista de futuras implementações está disponível [aqui](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> A lista de erros está disponível [aqui](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***Se precisar de outros sensores ou atuadores, não hesite em contactar-me [aqui](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Se os seus dispositivos não estiverem na mesma sub-rede que o seu Home Assistant, por favor [leia isto](README.pt.md#o-meu-dispositivo-não-é-detetado).

> [!CAUTION]
> ⚠️ Este não é um repositório oficial RedSea. Utilize por sua própria conta e risco.⚠️

# Compatibilidade

✅ Testado ☑️ Deve funcionar (Se tiver um, pode confirmar que funciona [aqui](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))❌ Ainda não suportado
<table>
<th>
<td colspan="2"><b>Modelo</b></td>
<td colspan="2"><b>Estado</b></td>
<td><b>Problemas</b> <br/>📆(Planeado) <br/> 🐛(Erros)</td>
</th>
<tr>
<td><a href="#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td><a href="#reefcontrol">ReefControl</a></td>
<td colspan="2">RSSENSE<br />Se tiver um, contacte-me <a href="https://github.com/Elwinmage/ha-reefbeat-component/discussions/8">aqui</a> para que eu possa adicionar o suporte.</td><td>❌</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROL.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE2.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"><a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
<td rowspan="6">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,RSLED90,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td>RSLED90</td><td>✅</td></tr>
<tr><td>RSLED160</td><td>✅ </td></tr>
<tr>
<td rowspan="3">G2</td>
<td>RSLED60</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g2.png"/></td>
</tr>
<tr><td>RSLED115</td><td>✅ </td></tr>
<tr><td>RSLED170</td><td>☑️</td></tr>
<tr>
<td rowspan="3"><a href="#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td><td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSMAT.png"/></td>
<td rowspan="3">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td colspan="2">RSMAT500</td><td>✅</td></tr>
<tr><td colspan="2">RSMAT1200</td><td>✅ </td></tr>
<tr>
<td><a href="#reefrun">ReefRun e DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td><td>☑️</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr><td colspan="2">RSWAVE45</td><td>✅</td></tr>
</table>

(*) Utilizadores do ReefWave, por favor leia [isto](README.pt.md#reefwave)

# Resumo
- [Instalação via HACS](README.pt.md#instalação-via-hacs)
- [Funções comuns](README.pt.md#funções-comuns)
- [ReefATO+](README.pt.md#reefato)
- [ReefControl](README.pt.md#reefcontrol)
- [ReefDose](README.pt.md#reefdose)
- [ReefLED](README.pt.md#reefled)
- [LED virtual](README.pt.md#led-virtual)
- [ReefMat](README.pt.md#reefmat)
- [ReefRun](README.pt.md#reefrun)
- [ReefWave](README.pt.md#reefwave)
- [API Cloud](README.pt.md#api-cloud)
- [FAQ](README.pt.md#faq)

# Instalação via HACS

## Instalação direta

Clique aqui para ir diretamente ao repositório no HACS e clique em «Transferir»: [![Abra a sua instância Home Assistant e abra um repositório na loja da comunidade Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Para o cartão companheiro ha-reef-card que oferece funcionalidades avançadas e ergonómicas, clique aqui para aceder diretamente ao repositório no HACS e clique em «Transferir»: [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Pesquisar no HACS
Ou pesquise «redsea» ou «reefbeat» no HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Imagem">
</p>

# Funções comuns

## Adicionar um dispositivo
Ao adicionar um novo dispositivo, tem quatro opções:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Imagem">
</p>

### Adicionar a API Cloud
***Obrigatório para manter os ReefWave sincronizados com a aplicação móvel ReefBeat*** (Leia [isto](README.pt.md#reefwave)). <br />
***Obrigatório para ser notificado de novas versões de firmware*** (Leia [isto](README.pt.md#atualização-de-firmware)).
- Informações do utilizador
- Aquários
- Biblioteca de Waves
- Biblioteca de LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Imagem">
</p>

### Deteção automática na rede privada
Se não estiver na mesma rede, leia [isto](README.pt.md#o-meu-dispositivo-não-é-detetado) e use o modo [«Manual»](README.pt.md#modo-manual).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Imagem">
</p>

### Modo manual
Pode introduzir o endereço IP ou o endereço de rede do seu dispositivo para a deteção automática.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Imagem">
</p>

### Definir o intervalo de análise do dispositivo

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Imagem">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Imagem">
</p>

## Atualização em tempo real

> [!NOTE]
> É possível escolher se ativa ou não o modo Live_update_config. Neste modo (antigo padrão), os dados de configuração são obtidos continuamente juntamente com os dados normais. Para o RSDOSE ou RSLED, estes pedidos HTTP volumosos podem demorar muito tempo (7-9 segundos). Por vezes o dispositivo não responde ao pedido, pelo que foi implementada uma função de repetição. Quando o Live_update_config está desativado, os dados de configuração apenas são obtidos no arranque e quando solicitados através do botão «Obter configuração». Este novo modo está ativado por predefinição. Pode alterá-lo na configuração do dispositivo. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Imagem">
</p>

## Atualização de Firmware
Pode ser notificado e atualizar o seu dispositivo quando estiver disponível uma nova versão de firmware. Deve ter um componente [«API Cloud»](README.pt.md#adicionar-a-api-cloud) ativo com as suas credenciais e o interruptor «Usar a API Cloud» deve estar ativado.
> [!TIP]
> A «API Cloud» só é necessária para obter o número de versão da nova versão e compará-lo com a versão instalada. Para atualizar o firmware, a API Cloud não é imprescindível.
> Se não usar a «API Cloud» (opção desativada ou componente API Cloud não instalado), não será notificado quando estiver disponível uma nova versão, mas ainda pode usar o botão oculto «Forçar atualização de firmware». Se estiver disponível uma nova versão, será instalada.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Imagem">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Imagem">
</p>

# ReefATO:
- Ativar/desativar o enchimento automático
- Enchimento manual
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Imagem">
</p>

# ReefControl:
Ainda não suportado. Se tiver um, contacte-me [aqui](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8) para que eu possa adicionar o suporte.

# ReefDose:
- Modificar a dose diária
- Dose manual
- Adicionar e remover suplementos
- Modificar e controlar o volume do recipiente. A definição do volume do recipiente é ativada ou desativada automaticamente consoante o volume selecionado.
- Ativar/desativar o agendamento por bomba
- Configuração de alertas de stock
- Atraso de dosagem entre suplementos
- Preparação (Por favor leia [isto](README.pt.md#calibração-e-preparação))
- Calibração (Por favor leia [isto](README.pt.md#calibração-e-preparação))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Imagem">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Imagem">
</p>

### Cabeças
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Imagem">
</p>

#### Calibração e preparação

> [!CAUTION]
> Deve seguir exatamente a seguinte ordem (A utilização do [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) é mais segura).<br /><br />
> <ins>Calibração</ins>:
>  1. Posicione a proveta e prima "Start Calibration"
>  2. Indique o valor medido utilizando o campo "Dose of Calibration"
>  3. Prima "Set Calibration Value"
>  4. Esvazie a proveta e prima "Test new Calibration". Se o valor obtido for diferente de 4 mL, volte ao passo 1.
>  5. Prima "Stop and Save Graduation"
>
> <ins>Preparação</ins>:
>  1. (a) Prima "Start Priming"
>  2. (b) Quando o líquido fluir, prima "Stop Priming"
>  3. (1) Posicione a proveta e prima "Start Calibration"
>  4. (2) Indique o valor medido utilizando o campo "Dose of Calibration"
>  5. (3) Prima "Set Calibration Value"
>  6. (4) Esvazie a proveta e prima "Test new Calibration". Se o valor obtido for diferente de 4 mL, volte ao passo 1.
>  7. (5) Prima "Stop and Save Graduation"
>
> ⚠️ A preparação deve ser obrigatoriamente seguida de uma calibração (passos 1 a 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Imagem">
</p>

# ReefLED:
- Obter e definir os valores de branco, azul e lua (apenas para G1: RSLED50, RSLED90, RSLED160)
- Obter e definir a temperatura de cor, a intensidade e a lua (todos os LED)
- Gerir a aclimatação. As definições de aclimatação são ativadas ou desativadas automaticamente de acordo com o interruptor de aclimatação.
- Gerir as fases lunares. As definições de fase lunar são ativadas ou desativadas automaticamente de acordo com a mudança de fase lunar.
- Definir o modo de cor manual com ou sem duração.
- Mostrar os parâmetros da ventoinha e da temperatura.
- Mostrar o nome e o valor dos programas (com suporte de nuvem). Apenas para LED G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_ctrl.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_diag.png" alt="Imagem">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_G1_sensors.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_conf.png" alt="Imagem">
</p>

***

O suporte de temperatura de cor para os LED G1 tem em conta as especificidades de cada um dos três modelos.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Imagem">
</p>

***
## IMPORTANTE para as lâmpadas G1 e G2

### LÂMPADAS G2

#### Intensidade
Este tipo de LED garante uma intensidade constante em toda a gama de cores, pelo que os seus LED não aproveitam a sua capacidade total no meio do espectro. A 8 000 K, o canal branco está a 100% e o canal azul a 0% (o inverso a 23 000 K). A 14 000 K e com uma intensidade de 100% para as lâmpadas G2, a potência dos canais branco e azul é de aproximadamente 85%.
Aqui está a curva de perda dos G2.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Imagem">
</p>

#### Temperatura de cor
A interface das lâmpadas G2 não suporta toda a gama de temperaturas. De 8 000 K a 10 000 K, os valores incrementam em passos de 200 K e de 10 000 K a 23 000 K em passos de 500 K. Este comportamento é tido em conta: se escolher um valor incorreto (por exemplo, 8 300 K), será automaticamente selecionado um valor válido (8 200 K no nosso exemplo). É por isso que por vezes pode observar um pequeno reajuste do cursor ao selecionar a cor numa lâmpada G2: o cursor reposiciona-se num valor permitido.

### LÂMPADAS G1

Os LED G1 utilizam o controlo dos canais branco e azul, o que permite plena potência em toda a gama, mas sem uma intensidade constante sem compensação.
Por isso foi implementada uma compensação de intensidade.
Esta compensação garante o mesmo [PAR](https://pt.wikipedia.org/wiki/Radia%C3%A7%C3%A3o_fotossinteticamente_ativa) (intensidade luminosa) independentemente da temperatura de cor escolhida (na gama de 12 000 a 23 000 K).
> [!NOTE]
> Como a RedSea não publica valores de PAR abaixo de 12 000 K, a compensação só funciona na gama de 12 000 a 23 000 K. Se tiver um LED G1 e um medidor de PAR, pode [contactar-me](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) para adicionar a compensação na gama completa (9 000 a 23 000 K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Imagem">
</p>

Por outras palavras, sem compensação, uma intensidade de x% a 9 000 K não fornece o mesmo valor de PAR que a 23 000 K ou 15 000 K.

Aqui estão as curvas de potência:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Imagem">
</p>

Se quiser aproveitar ao máximo a potência do seu LED, desative a compensação de intensidade (predefinição).

Se ativar a compensação de intensidade, a intensidade luminosa será constante em todos os valores de temperatura, mas no meio da gama não utilizará a capacidade total dos seus LED (como nos modelos G2).

Recorde também que, se ativar o modo de compensação, o fator de intensidade pode ultrapassar os 100% para os G1 se tocar manualmente nos canais Branco/Azul. Pode assim aproveitar toda a potência dos seus LED!

***

# LED virtual
- Agrupe e gira os LED com um dispositivo virtual (crie um dispositivo virtual a partir do painel de integração e use o botão de configuração para ligar os LED).
- Só pode utilizar Kelvin e intensidade para controlar os seus LED se tiver G2 ou uma combinação de G1 e G2.
- Pode utilizar tanto Kelvin/Intensidade como Branco e Azul se tiver apenas G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Imagem">
</p>

# ReefMat:
- Interruptor de avanço automático (ativar/desativar)
- Avanço programado
- Valor de avanço personalizado: permite selecionar o valor de avanço do rolo
- Avanço manual
- Mudar o rolo.
>[!TIP]
> Para um rolo novo completo, defina o «diâmetro do rolo» para o mínimo (4,0 cm). O tamanho será ajustado de acordo com a sua versão RSMAT. Para um rolo já utilizado, introduza o valor em cm.
- Dois parâmetros ocultos: modelo e posição, se precisar de reconfigurar o seu RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Imagem">
</p>

# ReefRun:
- Ajustar a velocidade da bomba
- Gerir o sobre-espumagem
- Gerir a deteção de copo cheio
- Possibilidade de alterar o modelo de skimmer

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Imagem">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Imagem">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Imagem">
</p>

### Bombas
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Imagem">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Imagem">
</p>

# ReefWave:
> [!IMPORTANT]
> Os dispositivos ReefWave são diferentes dos outros dispositivos ReefBeat. São os únicos dispositivos dependentes da nuvem ReefBeat.<br/>
> Quando inicia a aplicação móvel ReefBeat, o estado de todos os dispositivos é consultado e os dados da aplicação ReefBeat são obtidos a partir do estado do dispositivo.<br/>
> Para o ReefWave, é o inverso: não existe um ponto de controlo local (como pode ver na aplicação ReefBeat, não pode adicionar um ReefWave a um aquário desligado).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Imagem"></center><br />
> As ondas são armazenadas na biblioteca de utilizadores da nuvem. Quando modifica o valor de uma onda, esta é modificada na biblioteca da nuvem e aplicada à nova programação.<br/>
> Então não existe modo local? Não é tão simples. Existe uma API local oculta para controlar o ReefWave, mas a aplicação ReefBeat não deteta as alterações. Assim, o dispositivo e o HomeAssistant por um lado, e a aplicação móvel ReefBeat por outro, ficarão dessincronizados. O dispositivo e o HomeAssistant estarão sempre sincronizados.<br/>
> Agora que sabe, faça a sua escolha!

> [!NOTE]
> As ondas do ReefWave têm muitos parâmetros ligados, e o intervalo de alguns parâmetros depende de outros parâmetros. Não consegui testar todas as combinações possíveis. Se encontrar um erro, pode criar um ticket [aqui](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modos ReefWave
Como explicado anteriormente, os dispositivos ReefWave são os únicos que podem ficar dessincronizados da aplicação ReefBeat ao utilizar a API local.
Estão disponíveis três modos: Cloud, Local e Híbrido.
Pode alterar as definições de modo «Ligação à nuvem» e «Usar a API Cloud» conforme descrito na tabela abaixo.

<table>
<tr>
<td>Nome do modo</td>
<td>Interruptor Ligação à nuvem</td>
<td>Interruptor Usar a API Cloud</td>
<td>Comportamento</td>
<td>ReefBeat e HA estão sincronizados</td>
</tr>
<tr>
<td>Cloud (predefinição)</td>
<td>✅</td>
<td>✅</td>
<td>Os dados são obtidos através da API local. <br />Os comandos ligar/desligar também são enviados através da API local. <br />Os comandos são enviados através da API Cloud.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Os dados são obtidos através da API local. <br />Os comandos são enviados através da API local. <br />O dispositivo é apresentado como «desligado» na aplicação ReefBeat.</td>
<td>❌</td>
</tr>
<tr>
<td>Híbrido</td>
<td>✅</td>
<td>❌</td>
<td>Os dados são obtidos através da API local. <br />Os comandos são enviados através da API local.<br />A aplicação móvel ReefBeat não apresenta os valores corretos das ondas se forem modificados através do HA.<br/>O Home Assistant apresenta-os sempre corretamente.<br/>Pode modificar os valores a partir da aplicação ReefBeat e do Home Assistant.</td>
<td>❌</td>
</tr>
</table>

Para os modos Cloud e Híbrido, deve ligar a sua conta ReefBeat Cloud.
Primeiro crie uma [«API Cloud»](README.pt.md#adicionar-a-api-cloud) com as suas credenciais, e é só isso!
O sensor «Ligado à conta» será atualizado com o nome da sua conta ReefBeat assim que a ligação for estabelecida.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Imagem">
</p>

## Modificar os valores atuais
Para carregar os valores das ondas atuais nos campos de pré-visualização, use o botão «Definir pré-visualização a partir da onda atual».
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Imagem">
</p>
Para modificar os valores das ondas atuais, defina os valores de pré-visualização e use o botão «Guardar pré-visualização».

O funcionamento é idêntico ao da aplicação móvel ReefBeat. Todas as ondas com o mesmo identificador na programação atual serão atualizadas.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Imagem">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Imagem">
</p>

# API Cloud
A API Cloud permite:
- Iniciar ou parar atalhos: emergência, manutenção e alimentação,
- Obter informações do utilizador,
- Recuperar a biblioteca de ondas,
- Recuperar a biblioteca de suplementos,
- Recuperar a biblioteca de programas LED,
- Ser notificado de [novas versões de firmware](README.pt.md#atualização-de-firmware),
- Enviar comandos ao ReefWave quando o modo «[Cloud ou Híbrido](README.pt.md#reefwave)» está selecionado.

Os atalhos, os parâmetros de ondas e de LED estão ordenados por aquário.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Imagem">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Imagem">
</p>

>[!TIP]
> É possível desativar a obtenção da lista de suplementos na interface de configuração do dispositivo API Cloud.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Imagem">
***
# FAQ

## O meu dispositivo não é detetado
- Tente relançar a deteção automática com o botão «Adicionar entrada». Por vezes os dispositivos não respondem porque estão ocupados.
- Se os seus dispositivos RedSea não estiverem na mesma sub-rede que o seu Home Assistant, a deteção automática falhará primeiro e proporá que introduza o endereço IP do seu dispositivo ou o endereço da sub-rede onde se encontram os seus dispositivos. Para a deteção de sub-rede, utilize o formato IP/MÁSCARA, como neste exemplo: 192.168.14.0/255.255.255.0.
- Também pode usar o [modo manual](README.pt.md#modo-manual).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Imagem">
</p>

## Alguns dados são atualizados corretamente, outros não.
Os dados são divididos em três partes: dados, configuração e informações do dispositivo.
- Os dados são atualizados regularmente.
- Os dados de configuração são atualizados apenas no arranque e quando prime o botão «fetch-config».
- As informações do dispositivo são atualizadas apenas no arranque.

Para garantir que os dados de configuração são atualizados regularmente, ative a [atualização de configuração em tempo real](README.pt.md#atualização-em-tempo-real).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
