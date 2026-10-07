# Red Sea (dispositivos ReefBeat) 🐠
> Parte do **[Ecossistema ReefTech Project](https://elwinmage.github.io/reeftank/pt.html)**
<p align="center">
  <img src="../../icon.png" width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/default)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
![Installations](https://img.shields.io/badge/dynamic/json?label=Instalações%20ativas&query=estimated&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-reefbeat-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-reefbeat-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-reefbeat-component/releases)
[![Ruff Status](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-reefbeat-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](../../badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)

Para nos ajudar a traduzir, siga este [guia](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Apresentação
***Gestão local de dispositivos HomeAssistant RedSea Reefbeat (sem cloud): ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave***

<!-- generated:demo-videos:start -->

## 🎬 Vídeos de demonstração

<table>
<tr>
<td><a href="https://www.youtube.com/watch?v=Qee5LH0T9wQ"><img src="https://img.youtube.com/vi/Qee5LH0T9wQ/0.jpg" alt="Demo ReefDose" width="300"/></a><br/><em>Demo ReefDose</em></td>
<td><a href="https://www.youtube.com/watch?v=yyNyUSitb1E"><img src="https://img.youtube.com/vi/yyNyUSitb1E/0.jpg" alt="Demo ReefMat" width="300"/></a><br/><em>Demo ReefMat</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=Xxv38OPqiGI"><img src="https://img.youtube.com/vi/Xxv38OPqiGI/0.jpg" alt="Demo ReefRun" width="300"/></a><br/><em>Demo ReefRun</em></td>
<td><a href="https://www.youtube.com/watch?v=2R0DHp2eqT4"><img src="https://img.youtube.com/vi/2R0DHp2eqT4/0.jpg" alt="Demo ReefATO+" width="300"/></a><br/><em>Demo ReefATO+</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=voFobfc7Slk"><img src="https://img.youtube.com/vi/voFobfc7Slk/0.jpg" alt="Demo ReefControl & ReefControl-Power" width="300"/></a><br/><em>Demo ReefControl & ReefControl-Power</em></td>
<td><a href="https://www.youtube.com/watch?v=pA49z8QjTN4"><img src="https://img.youtube.com/vi/pA49z8QjTN4/0.jpg" alt="Demo ReefLed" width="300"/></a><br/><em>Demo ReefLed</em></td>
</tr>
<tr>
<td><a href="https://www.youtube.com/watch?v=sYVeE0zV3eo"><img src="https://img.youtube.com/vi/sYVeE0zV3eo/0.jpg" alt="Demo ReefWave" width="300"/></a><br/><em>Demo ReefWave</em></td>
</tr>
</table>

<!-- generated:demo-videos:end -->

<!-- ecosystem:start -->

## Projetos relacionados

Os projetos ReefTech encaixam-se entre si: as integrações trazem o seu equipamento para o Home Assistant, o cartão mostra-o e comanda-o, e o backup mantém-no a funcionar durante um corte. Cada um funciona também sozinho.

<table>
  <tr>
    <th width="100px"></th>
    <th>Projeto</th>
    <th>Função</th>
    <th>Funciona com</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td>🐠<br /><b>ha-reefbeat-component</b><br /><i>(este repositório)</i></td>
    <td>Aparelhos Red Sea ReefBeat, comandados localmente sem cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave.<br />blueprint de alertas para modos anómalos, calibrações e bateria fraca. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td>🌊<br /><a href="https://github.com/Elwinmage/ha-aquamedic-component"><b>ha-aquamedic-component</b></a></td>
    <td>Bombas Aqua Medic através da API cloud Gizwits: bombas de circulação EcoDrift e SmartDrift, bombas DC Runner de retorno e do escumador.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td>🐙<br /><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Acompanhamento da limpeza e do desgaste do equipamento que o Home Assistant não consegue interrogar: bombas de circulação, bombas de retorno, escumadores, reatores, tudo o que trata à mão.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td>🪸<br /><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Vista gráfica interativa de cada aparelho no seu painel, e a única forma de editar os programas avançados. Lê as três integrações através do contrato <code>reef_role</code> comum, sem configuração do lado do cartão. Desenha também os fluxos de energia do reefbeatEnergyBackup.</td>
    <td>as três integrações</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-blueprints/main/icon.png" width="64" alt="ha-reef-blueprints" /></td>
    <td>🐬<br /><a href="https://github.com/Elwinmage/ha-reef-blueprints"><b>ha-reef-blueprints</b></a></td>
    <td>Blueprints de notificação comuns a todo o ecossistema: manutenções em atraso encontradas pelo contrato <code>reef_role</code>, e aparelhos que ficaram inacessíveis. Oito idiomas.</td>
    <td>as três integrações</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td>⚡<br /><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Backup por bateria em caso de corte. Um pack 24V LiFePO₄ comandado por um Raspberry Pi, com degradação progressiva da velocidade das bombas conforme o estado de carga.</td>
    <td>sozinho, ou a par do ha-reefbeat-component e do ha-reef-card</td>
  </tr>
</table>

Estão todos documentados em conjunto na [página do projeto ReefTech](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

# Compatibilidade

✅ Testado ☑️ Deve funcionar (Se tiver um, pode confirmar que funciona [aqui](https://github.com/Elwinmage/ha-reefbeat-component/discussions/8))
<table>
<th>
<td colspan="2"><b>Model</b></td>
<td colspan="2"><b>Status</b></td>
<td><b><a href="https://github.com/Elwinmage/reefbeatEnergyBackup">EnergyBackup</a></b></td>
<td><b>Issues</b> <br/>📆(Planned) <br/> 🐛(Bugs)</td>
</th>
<tr>
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefato.pt.md#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="../img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefcontrol.pt.md#reefcontrol">ReefControl</a></td>
<td colspan="2">RSCONTROLPRO</td><td>✅</td>
<td width="200px"><img src="../img/RSCONTROLPRO.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSCONTROLLITE</td><td>☑️</td>
<td width="200px"><img src="../img/RSCONTROLLITE.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefcontrol-power.pt.md#reefcontrol-power">ReefControl-Power</a></td>
<td colspan="2">RSPOWER6</td><td>✅</td>
<td width="200px"><img src="../img/RSPOWER6.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSPOWER8</td><td>☑️</td>
<td width="200px"><img src="../img/RSPOWER8.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefdose.pt.md#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
<td width="200px"><img src="../img/RSDOSE2.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsdose,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSDOSE4</td><td>✅ </td>
<td width="200px"><img src="../img/RSDOSE4.png"/></td>
</tr>
<tr>
<td rowspan="6"> <a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefled.pt.md#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="../img/rsled_g1.png"/></td>
<td align="center" rowspan="6">–</td>
<td rowspan="6">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsled,RSLED90,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td>RSLED90</td>
<td>✅</td>
</tr>
<tr>
<td>RSLED160</td><td>✅ </td>
</tr>
<tr>
<td rowspan="3">G2</td>
<td>RSLED60</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="../img/rsled_g2.png"/></td>
</tr>
<tr>
<td>RSLED115</td><td>✅ </td>
</tr>
<tr>
<td>RSLED170</td><td>☑️</td>
</tr>
<tr>
<td rowspan="3"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefmat.pt.md#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="../img/RSMAT.png"/></td>
<td align="center" rowspan="3">–</td>
<td rowspan="3">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsmat,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSMAT500</td><td>✅</td>
</tr>
<tr>
<td colspan="2">RSMAT1200</td><td>✅ </td>
</tr>
<tr>
<td><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefrun.pt.md#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="../img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefwave.pt.md#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>✅</td>
<td width="200px" rowspan="2"><img src="../img/RSWAVE.png"/></td>
<td align="center" rowspan="2">✅</td>
<td rowspan="2">
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rswave,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rwave,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSWAVE45</td><td>✅</td>
</tr>
</table>

(*) Utilizadores de ReefWave, por favor leiam [isto](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefwave.pt.md#reefwave)

# Resumo
- [Instalação via HACS](#instalação-via-hacs)
- [Funções comuns](#funções-comuns)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefato.pt.md#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefcontrol.pt.md#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefcontrol-power.pt.md#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefdose.pt.md#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefled.pt.md#reefled)
- [LED virtual](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/virtual-led.pt.md#led-virtual)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefmat.pt.md#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefrun.pt.md#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefwave.pt.md#reefwave)
- [Manutenção](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/maintenance.pt.md#manutenção)
- [Cloud API](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/cloud-api.pt.md#api-cloud)
- [FAQ](#faq)

# Instalação via HACS

## Instalação direta

Clique aqui para ir diretamente ao repositório no HACS e clique em "Descarregar": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Para o cartão complementar ha-reef-card com funcionalidades avançadas, clique aqui para ir ao repositório no HACS e clique em "Descarregar": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Pesquisar no HACS
Ou pesquise «redsea» ou «reefbeat» no HACS.

<p align="center">
<img src="../img/hacs_search.png" alt="Image">
</p>

# Funções comuns

# Ícones
Esta integração fornece ícones personalizados acessíveis através de "redsea:icon-name":

<img src="../img/redsea-icons.png"/>

## Adicionar dispositivo
Ao adicionar um novo dispositivo, tem 4 opções:

<p align="center">
<img src="../img/add_devices_main.png" alt="Image">
</p>

### Adicionar API Cloud
***Obrigatório para ReefWave se quiser mantê-lo sincronizado com a aplicação móvel ReefBeat*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/reefwave.pt.md#reefwave)). <br />
***Obrigatório para ser notificado de novas versões de firmware*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#firmware-update)).
- Obter informações do utilizador
- Obter aquários
- Obter biblioteca de Waves
- Obter biblioteca LED

<p align="center">
<img src="../img/add_devices_cloud_api.png" alt="Image">
</p>

### Deteção automática em rede privada
Se não estiver na mesma rede, leia [isto](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#my-device-is-not-detected) e use o ["Modo Manual"](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#manual-mode).
<p align="center">
<img src="../img/auto_detect.png" alt="Image">
</p>

### Modo manual
Pode introduzir o endereço IP do dispositivo ou o endereço de rede para deteção automática.

<p align="center">
<img src="../img/add_devices_manual.png" alt="Image">
</p>

## Configuração do dispositivo

Clique com o botão direito num dispositivo (ou abra as suas opções a partir da página da integração) para aceder à sua configuração. O primeiro ecrã permite alterar a forma como a integração comunica com o dispositivo.

<p align="center">
<img src="../img/configure_device_1.png" alt="Image">
</p>

### Definir intervalo de sondagem do dispositivo

Defina com que frequência (em segundos) a integração consulta o dispositivo para obter novos dados.

<p align="center">
<img src="../img/configure_device_2.png" alt="Image">
</p>

### Mudar de rede WiFi

Pode mover um dispositivo para outra rede WiFi diretamente a partir do Home Assistant, sem voltar à aplicação ReefBeat.

No menu de configuração do dispositivo, escolha **Mudar de rede WiFi**. A integração pede ao dispositivo para procurar redes próximas e mostra-as numa lista pendente, ordenadas por intensidade de sinal. A rede à qual o dispositivo está atualmente ligado aparece pré-selecionada, por isso, se só precisar de atualizar a palavra-passe, pode deixar a seleção como está.

<p align="center">
<img src="../img/device_cfg.png" alt="Image">
</p>

Escolha a rede de destino, introduza a respetiva palavra-passe e confirme. A integração envia as novas credenciais para o dispositivo, reinicia-o e depois procura-o automaticamente na rede para atualizar o seu endereço IP.

<p align="center">
<img src="../img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> Após uma mudança de WiFi, o dispositivo pode juntar-se a uma sub-rede diferente (por exemplo, passar de `192.168.0.x` para `10.0.0.x`). A integração analisa todas as sub-redes às quais o Home Assistant está diretamente ligado. Se o dispositivo aparecer numa sub-rede que o Home Assistant só consegue alcançar através de um router, a redescoberta falhará e ser-lhe-á pedido para introduzir manualmente a sub-rede de destino (por exemplo, `10.0.0.0/24`).

## Atualização em direto

> [!NOTE]
> É possível escolher se ativa ou não o live_update_config. Neste modo (o antigo predefinido), os dados de configuração são obtidos continuamente juntamente com os dados normais. Para RSDOSE ou RSLED, estes grandes pedidos HTTP podem demorar muito (7–9 segundos). Por vezes o dispositivo não responde ao pedido, por isso foi implementada uma função de nova tentativa. Com o live_update_config desativado, os dados de configuração só são obtidos no arranque e quando pedidos através do botão "Obter configuração". Este novo modo está ativo por predefinição. Pode alterá-lo na configuração do dispositivo. <p align="center">
<img src="../img/configure_device_live_update_config.png" alt="Image">
<img src="../img/fetch_config_button.png" alt="Image">
</p>

> [!NOTE]
> Cada aparelho expõe também um botão «Atualizar dados». Força uma leitura imediata das fontes consultadas periodicamente, sem esperar pelo próximo intervalo de sondagem, e funciona seja qual for a definição Live_update_config — ao contrário de «Obter configuração», que só atualiza as fontes de configuração.

## Atualização de Firmware
Pode ser notificado e atualizar o seu dispositivo quando estiver disponível uma nova versão de firmware. Tem de ter um dispositivo ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#add-cloud-api) ativo com as suas credenciais e o interruptor "Usar API na nuvem" tem de estar ativado.
> [!TIP]
> A "Cloud API" só é necessária para obter o número da nova versão e compará-lo com a versão instalada. Para atualizar o firmware, a Cloud API não é estritamente necessária.
> Se não usar a "Cloud API" (interruptor desativado ou nenhum dispositivo Cloud API instalado), não será avisado quando houver uma nova versão, mas pode continuar a usar o botão oculto "Forçar atualização de firmware". Se houver uma nova versão disponível, será instalada.
<p align="center">
  <img src="../img/firmware_update_1.png" alt="Image">
  <img src="../img/firmware_update_2.png" alt="Image">
</p>

# FAQ

## O meu dispositivo não é detetado
- Tente reiniciar a deteção automática com o botão "Adicionar entrada". Sometimes devices do not respond because they are busy.
- Se os seus dispositivos Red Sea não estiverem na mesma sub-rede que o Home Assistant, a deteção automática falhará primeiro e depois oferecerá a opção de introduzir o endereço IP do dispositivo ou o endereço da sub-rede onde os seus dispositivos se encontram. Para a deteção por sub-rede, use o formato IP/MÁSCARA, por exemplo: 192.168.14.0/255.255.255.0.
- You can also use [Manual Mode](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#manual-mode).

<p align="center">
<img src="../img/subnetwork.png" alt="Image">
</p>

## Alguns dados são atualizados corretamente, outros não.
Os dados estão divididos em três partes: dados, configuração e informações do dispositivo.
- Os dados são atualizados regularmente.
- Os dados de configuração só são atualizados no arranque e quando prime o botão "Obter configuração".
- Os dados de informações do dispositivo só são atualizados no arranque.

Para garantir que os dados de configuração sejam atualizados regularmente, ative [Atualização de Configuração em Direto](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md#live-update).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
