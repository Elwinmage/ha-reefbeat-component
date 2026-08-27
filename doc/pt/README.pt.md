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
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-reefbeat-component)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" style="width: 5%;"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/pt/README.pt.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" style="width: 5%"/>](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/it/README.it.md)

Para nos ajudar a traduzir, siga este [guia](https://github.com/Elwinmage/ha-reefbeat-component/blob/main/doc/TRANSLATION.md).

# Apresentação
***Gestão local de dispositivos HomeAssistant RedSea Reefbeat (sem cloud): ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave***

## Projetos relacionados

Esta integração é um dos três projetos complementares para um aquário de recife Red Sea:

| Projeto | Função |
| --- | --- |
| [**ha-reefbeat-component**](https://github.com/Elwinmage/ha-reefbeat-component) | Esta integração. Controlo local dos dispositivos ReefBeat a partir do Home Assistant, sem nuvem: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave. |
| [**ReefBeat watch**](https://github.com/Elwinmage/ha-reefbeat-component/tree/main/blueprints/automation) | Blueprint de alertas incluído nesta integração. Avisa-te de manutenções e calibrações em atraso, modos anómalos, baterias fracas e dispositivos inacessíveis, nos telemóveis que escolheres. [![Abre a tua instância do Home Assistant e mostra a janela de importação do blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml) |
| [**ha-reef-card**](https://github.com/Elwinmage/ha-reef-card) | Cartão Lovelace complementar. Necessário para editar programações avançadas do ReefDose, ReefLed, ReefRun e ReefWave, e dá a cada dispositivo uma vista gráfica interativa. |
| [**reefbeatEnergyBackup**](https://github.com/Elwinmage/reefbeatEnergyBackup) | Reserva por bateria em caso de falha de energia. Conjunto 24V LiFePO₄ comandado por um Raspberry Pi, com redução progressiva da velocidade das bombas conforme o estado de carga. Funciona sozinho ou a par desta integração. |

Os três, e outros projetos de recife, estão documentados em conjunto na [página do projeto](https://elwinmage.github.io/reeftank/).

> [!TIP]
> A lista de implementações futuras está disponível [aqui](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement)<br />
> A lista de erros está disponível [aqui](https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is%3Aissue%20state%3Aopen%20label%3Abug)<br />

***Se precisar de outros sensores ou atuadores, não hesite em contactar-me [aqui](https://github.com/Elwinmage/ha-reefbeat-component/discussions).***

> [!IMPORTANT]
> Se os seus dispositivos não estiverem na mesma sub-rede que o seu Home Assistant, por favor [leia isto](https://github.com/Elwinmage/ha-reefbeat-component/#my-device-is-not-detected).

> [!CAUTION]
> ⚠️ Este não é um repositório oficial da RedSea. Utilize por sua conta e risco.⚠️

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
<td><a href="#reefato">ReefATO+</a></td>
<td colspan="2">RSATO+</td><td>✅ </td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSATO+.png"/></td>
<td align="center">–</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsato,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefcontrol">ReefControl</a></td>
<td colspan="2">RSCONTROLPRO</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROLPRO.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rscontrol,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSCONTROLLITE</td><td>☑️</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSCONTROLLITE.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="#reefcontrol-power">ReefControl-Power</a></td>
<td colspan="2">RSPOWER6</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSPOWER6.png"/></td>
<td align="center" rowspan="2">–</td>
<td rowspan="2">
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:enhancement" style="text-decoration:none">📆</a>
  <a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rspower,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td colspan="2">RSPOWER8</td><td>☑️</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSPOWER8.png"/></td>
</tr>
<tr>
<td rowspan="2"><a href="#reefdose">ReefDose</a></td>
<td colspan="2">RSDOSE2</td>
<td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSDOSE2.png"/></td>
<td align="center" rowspan="2">–</td>
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
<td rowspan="6"> <a href="#reefled">ReefLed</a></td>
<td rowspan="3">G1</td>
<td>RSLED50</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g1.png"/></td>
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
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsled_g2.png"/></td>
</tr>
<tr>
<td>RSLED115</td><td>✅ </td>
</tr>
<tr>
<td>RSLED170</td><td>☑️</td>
</tr>
<tr>
<td rowspan="3"><a href="#reefmat">ReefMat</a></td>
<td colspan="2">RSMAT250</td>
<td>✅</td>
<td rowspan="3" width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSMAT.png"/></td>
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
<td><a href="#reefrun">ReefRun & DC Skimmer</a></td>
<td colspan="2">RSRUN</td><td>✅</td>
<td width="200px"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSRUN.png"/></td>
<td align="center">✅</td>
<td>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:enhancement" style="text-decoration:none">📆</a>
<a href="https://github.com/Elwinmage/ha-reefbeat-component/issues?q=is:issue state:open label:rsrun,all label:bug" style="text-decoration:none">🐛</a>
</td>
</tr>
<tr>
<td rowspan="2"><a href="#reefwave">ReefWave (*)</a></td>
<td colspan="2">RSWAVE25</td>
<td>✅</td>
<td width="200px" rowspan="2"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/RSWAVE.png"/></td>
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

(*) Utilizadores de ReefWave, por favor leiam [isto](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)

# Resumo
- [Instalação via HACS](https://github.com/Elwinmage/ha-reefbeat-component/#installation-via-hacs)
- [Funções comuns](https://github.com/Elwinmage/ha-reefbeat-component/#common-functions)
- [ReefATO+](https://github.com/Elwinmage/ha-reefbeat-component/#reefato)
- [ReefControl](https://github.com/Elwinmage/ha-reefbeat-component/#reefcontrol)
- [ReefControl-Power](https://github.com/Elwinmage/ha-reefbeat-component/#reefcontrol-power)
- [ReefDose](https://github.com/Elwinmage/ha-reefbeat-component/#reefdose)
- [ReefLED](https://github.com/Elwinmage/ha-reefbeat-component/#reefled)
- [LED virtual](https://github.com/Elwinmage/ha-reefbeat-component/#virtual-led)
- [ReefMat](https://github.com/Elwinmage/ha-reefbeat-component/#reefmat)
- [ReefRun](https://github.com/Elwinmage/ha-reefbeat-component/#reefrun)
- [ReefWave](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)
- [Manutenção](https://github.com/Elwinmage/ha-reefbeat-component/#maintenance)
- [Cloud API](https://github.com/Elwinmage/ha-reefbeat-component/#cloud-api)
- [FAQ](https://github.com/Elwinmage/ha-reefbeat-component/#faq)

# Instalação via HACS

## Instalação direta

Clique aqui para ir diretamente ao repositório no HACS e clique em "Descarregar": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reefbeat-component&category=integration)

Para o cartão complementar ha-reef-card com funcionalidades avançadas, clique aqui para ir ao repositório no HACS e clique em "Descarregar": [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-reef-card&category=plugin)

## Pesquisar no HACS
Ou pesquise «redsea» ou «reefbeat» no HACS.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/hacs_search.png" alt="Image">
</p>

# Funções comuns

# Ícones
Esta integração fornece ícones personalizados acessíveis através de "redsea:icon-name":

<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/redsea-icons.png"/>

## Adicionar dispositivo
Ao adicionar um novo dispositivo, tem 4 opções:

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_main.png" alt="Image">
</p>

### Adicionar API Cloud
***Obrigatório para ReefWave se quiser mantê-lo sincronizado com a aplicação móvel ReefBeat*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)). <br />
***Obrigatório para ser notificado de novas versões de firmware*** (Read [this](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update)).
- Obter informações do utilizador
- Obter aquários
- Obter biblioteca de Waves
- Obter biblioteca LED

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_cloud_api.png" alt="Image">
</p>

### Deteção automática em rede privada
Se não estiver na mesma rede, leia [isto](#my-device-is-not-detected) e use o ["Modo Manual"](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/auto_detect.png" alt="Image">
</p>

### Modo manual
Pode introduzir o endereço IP do dispositivo ou o endereço de rede para deteção automática.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/add_devices_manual.png" alt="Image">
</p>

## Configuração do dispositivo

Clique com o botão direito num dispositivo (ou abra as suas opções a partir da página da integração) para aceder à sua configuração. O primeiro ecrã permite alterar a forma como a integração comunica com o dispositivo.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_1.png" alt="Image">
</p>

### Definir intervalo de sondagem do dispositivo

Defina com que frequência (em segundos) a integração consulta o dispositivo para obter novos dados.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_2.png" alt="Image">
</p>

### Mudar de rede WiFi

Pode mover um dispositivo para outra rede WiFi diretamente a partir do Home Assistant, sem voltar à aplicação ReefBeat.

No menu de configuração do dispositivo, escolha **Mudar de rede WiFi**. A integração pede ao dispositivo para procurar redes próximas e mostra-as numa lista pendente, ordenadas por intensidade de sinal. A rede à qual o dispositivo está atualmente ligado aparece pré-selecionada, por isso, se só precisar de atualizar a palavra-passe, pode deixar a seleção como está.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/device_cfg.png" alt="Image">
</p>

Escolha a rede de destino, introduza a respetiva palavra-passe e confirme. A integração envia as novas credenciais para o dispositivo, reinicia-o e depois procura-o automaticamente na rede para atualizar o seu endereço IP.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/wifi_choice.png" alt="Image">
</p>

> [!NOTE]
> Após uma mudança de WiFi, o dispositivo pode juntar-se a uma sub-rede diferente (por exemplo, passar de `192.168.0.x` para `10.0.0.x`). A integração analisa todas as sub-redes às quais o Home Assistant está diretamente ligado. Se o dispositivo aparecer numa sub-rede que o Home Assistant só consegue alcançar através de um router, a redescoberta falhará e ser-lhe-á pedido para introduzir manualmente a sub-rede de destino (por exemplo, `10.0.0.0/24`).

## Atualização em direto

> [!NOTE]
> It is possible to choose whether to enable live_update_config or not. In this mode (old default), configuration data is continuously retrieved along with normal data. For RSDOSE or RSLED, these large HTTP requests can take a long time (7–9 seconds). Sometimes the device does not respond to the request, so a retry function has been implemented. When live_update_config is disabled, configuration data is only retrieved at startup and when requested via the "Fetch Configuration" button. This new mode is activated by default. You can change it in the device configuration. <p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/configure_device_live_update_config.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/fetch_config_button.png" alt="Image">
</p>

## Atualização de Firmware
Pode ser notificado e atualizar o seu dispositivo quando estiver disponível uma nova versão de firmware. You must have an active ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) device with your credentials and the "Use Cloud API" switch must be enabled.
> [!TIP]
> The "Cloud API" is only needed to get the version number of the new release and compare it to the installed version. To update your firmware, the Cloud API is not strictly required.
> If you do not use the "Cloud API" (switch disabled or no Cloud API device installed), you will not be alerted when a new version is available, but you can still use the hidden "Force Firmware Update" button. If a new version is available, it will be installed.
<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_1.png" alt="Image">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/firmware_update_2.png" alt="Image">
</p>

# ReefATO:
- Ativar/desativar enchimento automático
- Enchimento manual
- Ativar/desativar o buzzer de alarme de fuga
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsato_diag.png" alt="Image">
</p>

### Tarefas de manutenção
| Tarefa | Por omissão | Intervalo |
| ------ | ----------- | --------- |
| Limpar a sonda EC | 6 semanas | 3 – 9 semanas |
| Limpar a bomba de retorno | 4,5 meses | 2 – 7 meses |

Ver a secção [Manutenção](README.pt.md#manutenção).

# ReefControl:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_devices.png" alt="Image">
</p>

- Leitura de todas as sondas ReefSense ligadas (pH, ORP, salinidade, temperatura, ATO, fuga) com valor e nível de qualidade
- Estado do sinal sonoro e do detetor de fugas
- Ligar/desligar portas 12V DC (RSCONTROL)
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rscontrol_diag.png" alt="Image">
</p>

## ReefControl-Power

O RSPOWER (Power Center) é um dispositivo autónomo com o seu próprio endereço IP, exposto separadamente no Home Assistant.

- Estado, modo, consumo e ligar/desligar por tomada
- 6 ou 8 tomadas controláveis consoante o modelo (RSPOWER6 / RSPOWER8)
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_devices.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rspower_diag.png" alt="Image">
</p>

# ReefDose:
- Editar a dose diária
- Dose manual
- Adicionar e remover suplementos
- Editar e controlar o volume do recipiente. Container volume settings are automatically enabled or disabled according to the volume control switch.
- Ativar/desativar programação por bomba
- Configuração de alertas de stock
- Atraso de dosagem entre suplementos
- Cebagem (Por favor leia [this](https://github.com/Elwinmage/ha-reefbeat-component/#calibration-and-priming))
- Calibração (Por favor leia [this](https://github.com/Elwinmage/ha-reefbeat-component/#calibration-and-priming))

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_main_diag.png" alt="Image">
</p>

### Cabeças
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsdose_diag.png" alt="Image">
</p>

#### Calibration and Priming

> [!CAUTION]
> Deve seguir rigorosamente a seguinte ordem (Using the [ha-reef-card](https://github.com/Elwinmage/ha-reef-card) is safer).<br /><br />
> <ins>Calibration</ins>:
>  1. Place the graduated container and press "Start Calibration"
>  2. Enter the measured value using the "Dose of Calibration" field
>  3. Press "Set Calibration Value"
>  4. Empty the graduated container and press "Test new Calibration". If the value obtained is not 4 mL, go back to step 1.
>  5. Press "Stop and Save Graduation"
>
> <ins>For priming</ins>:
>  1. (a) Press "Start Priming"
>  2. (b) When the liquid flows out, press "Stop Priming"
>  3. (1) Place the graduated container and press "Start Calibration"
>  4. (2) Enter the measured value using the "Dose of Calibration" field
>  5. (3) Press "Set Calibration Value"
>  6. (4) Empty the graduated container and press "Test new Calibration". If the value obtained is not 4 mL, go back to step 1.
>  7. (5) Press "Stop and Save Graduation"
>
> ⚠️ Priming must always be followed by a calibration (steps 1 to 5)!⚠️

<p align="center">
  <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/calibration.png" alt="Image">
</p>

### Tarefas de manutenção
| Tarefa | Nível | Por omissão | Intervalo |
| ------ | ----- | ----------- | --------- |
| Calibrar as cabeças de doseamento | Aparelho | 90 dias | 80 – 120 dias |
| Substituir cabeças e tubos | Por cabeça | 15 meses | 11 – 19 meses |

A substituição é seguida **por cabeça**: trocar a cabeça 2 não reinicia a
contagem das outras três. Ver a secção [Manutenção](README.pt.md#manutenção).

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

Color Temperature support for G1 LEDs takes into account the specificities of each of the three models.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/leds_specs.png" alt="Image">
</p>

***
## IMPORTANTE para as lâmpadas G1 e G2

### LÂMPADAS G2

#### Intensidade
Because G2 LEDs ensure constant intensity across the entire color range, your LEDs do not utilize their full capacity in the middle of the spectrum. At 8,000K, the white channel is at 100% and the blue channel at 0% (the opposite at 23,000K). At 14,000K with 100% intensity for G2 lights, the power of the white and blue channels is approximately 85%.
Here is the loss curve for the G2s.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_factor.png" alt="Image">
</p>

#### Temperatura de Cor
The G2 interface does not support the entire temperature range. From 8,000K to 10,000K, values are incremented in 200K steps, and from 10,000K to 23,000K in 500K steps. This behavior is handled automatically: if you choose an invalid value (e.g. 8,300K), a valid value will be automatically selected (8,200K in this example). This is why you may sometimes observe a slight cursor adjustment when selecting the color on a G2 light — the cursor repositions itself to an allowed value.

### LÂMPADAS G1

G1 LEDs use white and blue channel control, which allows full power across the entire range, but not constant intensity without compensation.
That is why intensity compensation has been implemented.
This compensation ensures you get the same [PAR](https://en.wikipedia.org/wiki/Photosynthetically_active_radiation) (light intensity) regardless of your color temperature choice (in the range 12,000 to 23,000K).
> [!NOTE]
> Because Red Sea does not publish PAR values below 12,000K, compensation is only available in the 12,000 to 23,000K range. If you have a G1 LED and a PAR meter, you can [contact me](https://github.com/Elwinmage/ha-reefbeat-component/discussions/) to add compensation for the full range (9,000 to 23,000K).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/intensity_compensation.png" alt="Image">
</p>

In other words, without compensation, an intensity of x% at 9,000K does not provide the same PAR as at 23,000K or 15,000K.

Here are the power curves:
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/PAR_curves.png" alt="Image">
</p>

If you want to use the full power of your LED, disable intensity compensation (default).

If you enable intensity compensation, the light intensity will be constant across all color temperature values, but in the middle of the range you will not use the full capacity of your LEDs (as with G2 models).

Also note that if compensation is enabled, the intensity factor can exceed 100% for G1 lights if you manually adjust the White/Blue channels. This allows you to harness the full power of your LEDs!

***

### Tarefas de manutenção
| Tarefa | Por omissão | Intervalo |
| ------ | ----------- | --------- |
| Limpar as lentes | 3 semanas | 1 – 5 semanas |
| Limpar o pó da ventoinha e das grelhas | 6 meses | 5 – 7 meses |

Estas duas tarefas são criadas para todas as gerações de ReefLED, incluindo o
LED virtual. Ver a secção [Manutenção](README.pt.md#manutenção).

# LED virtual
- Agrupar e gerir LEDs com um dispositivo virtual (create a virtual device from the integration panel, then use the configure button to link the LEDs).
- Só pode usar Kelvin e intensidade para controlar os seus LEDs se tiver G2 ou uma mistura de G1 e G2.
- Pode usar tanto Kelvin/Intensidade como Branco e Azul se tiver apenas lâmpadas G1.

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_1.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/virtual_led_config_2.png" alt="Image">
</p>

# ReefMat:
- Interruptor de avanço automático (ativar/desativar)
- Avanço programado
- Valor de avanço personalizado: permite selecionar o valor de avanço do rolo
- Avanço manual
- Trocar o rolo.
>[!TIP]
> For a new full roll, please set "roll diameter" to the minimum (4.0 cm). The size will be adjusted according to your RSMAT version. For a partially used roll, enter the value in cm.
- Dois parâmetros ocultos: modelo e posição, se precisar de reconfigurar o seu RSMAT
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_ctr.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsmat_diag.png" alt="Image">
</p>

### Tarefas de manutenção
| Tarefa | Por omissão | Intervalo |
| ------ | ----------- | --------- |
| Substituir o carvão ativado | 25 dias | 2 – 5 semanas |

Ver a secção [Manutenção](README.pt.md#manutenção).

# ReefRun:
- Ajustar a velocidade da bomba
- Gerir o sobredesnatamento
- Gerir a deteção de copo cheio
- Possibilidade de alterar o modelo de skimmer

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_devices.png" alt="Image">
</p>

### Principal
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_ctrl.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_main_diag.png" alt="Image">
</p>

### Bombas
<p align="center"><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_conf.png" alt="Image">
</p>
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rsrun_diag.png" alt="Image">
</p>

### Tarefas de manutenção
As tarefas são associadas ao subaparelho bomba e dependem do seu tipo.

| Tarefa | Bomba | Por omissão | Intervalo |
| ------ | ----- | ----------- | --------- |
| Limpar motor e rotor | Retorno | 4,5 meses | 2 – 7 meses |
| Limpar o filtro de aspiração | Retorno | 6 semanas | 3 – 9 semanas |
| Limpar venturi e tubo de ar | Escumador | 5 semanas | 3 – 7 semanas |
| Limpar o rotor do escumador | Escumador | 4,5 meses | 2 – 7 meses |
| Calibrar a sonda de copo cheio | Escumador | 4 semanas | 2 – 6 semanas |
| Calibrar a sonda de sobre-escumação | Escumador | 4 semanas | 2 – 6 semanas |

As duas tarefas de calibração são também vigiadas pelo blueprint de alertas, que
compara a data da última calibração comunicada pelo aparelho com o intervalo
definido aqui. Ver a secção [Manutenção](README.pt.md#manutenção).

### Chave para desmontar o rotor

A tarefa *Limpar o rotor do escumador* acima obriga a desenroscar o
corpo da bomba, que molhado quase não oferece pega. Uma chave imprimível em 3D
para essa operação, com um vídeo de utilização, está disponível aqui:
[Chave para rotor de DC Skimmer Red Sea](https://elwinmage.github.io/reeftank/#-red-sea-dc-skimmer-impeller-tool).

# ReefWave:
> [!IMPORTANT]
> ReefWave devices are different from other ReefBeat devices. They are the only devices that are slaves to the ReefBeat cloud.<br/>
> When you launch the ReefBeat mobile app, the status of all devices is queried and data from the ReefBeat app is retrieved from device state.<br/>
> For ReefWave, it is the opposite: there is no local control point (as you can see in the ReefBeat app, you cannot add a ReefWave to a disconnected aquarium).<br/>
> <center><img width="20%" src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/reefbeat_rswave.jpg" alt="Image"></center><br />
> Waves are stored in the cloud user library. When you change a wave's value, it is changed in the cloud library and applied to the new schedule.<br/>
> So there is no local mode? Not so simple. There is a hidden local API to control ReefWave, but the ReefBeat app will not detect the changes. As a result, the device and Home Assistant on one side, and the ReefBeat mobile app on the other, will be out of sync. The device and Home Assistant will always be synchronized.<br/>
> Now that you know, make your choice!

> [!NOTE]
> ReefWave waves have many linked parameters, and the range of some parameters depends on other parameters. I was not able to test all possible combinations. If you find a bug, you can create an issue [here](https://github.com/Elwinmage/ha-reefbeat-component/issues).

## Modos ReefWave
As explained above, ReefWave devices are the only devices that can become unsynchronized with the ReefBeat app if you use the local API.
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
<td>Data is fetched via the local API. <br />On/off commands are also sent via the local API. <br />Wave commands are sent via the cloud API.</td>
<td>✅</td>
</tr>
<tr>
<td>Local</td>
<td>❌</td>
<td>❌</td>
<td>Data is fetched via the local API. <br />Commands are sent via the local API. <br />Device is shown as "off" in the ReefBeat app.</td>
<td>❌</td>
</tr>
<tr>
<td>Hybrid</td>
<td>✅</td>
<td>❌</td>
<td>Data is fetched via the local API. <br />Commands are sent via the local API.<br />The ReefBeat mobile app does not display the correct wave values if they have been changed via HA.<br/>Home Assistant always displays the correct values.<br/>You can change values from both the ReefBeat app and Home Assistant.</td>
<td>❌</td>
</tr>
</table>

For Cloud and Hybrid modes you must link your ReefBeat cloud account.
First create a ["Cloud API"](https://github.com/Elwinmage/ha-reefbeat-component/#add-cloud-api) device with your credentials, and that's it!
The "Linked to account" sensor will be updated with the name of your ReefBeat account once the connection is established.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_linked.png" alt="Image">
</p>

## Alterar valores atuais
To load current wave values into the preview fields, use the "Set Preview From Current Wave" button.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_set_preview.png" alt="Image">
</p>
To change the current wave values, set the preview values and use the "Save Preview" button.

The behavior is the same as the ReefBeat mobile app. All waves with the same ID in the current schedule will be updated.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_save_preview.png" alt="Image">
</p>

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_conf.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/rswave_diag.png" alt="Image">
</p>

### Tarefas de manutenção
| Tarefa | Por omissão | Intervalo |
| ------ | ----------- | --------- |
| Limpar as gaiolas do rotor | 2 meses | 1 – 3 meses |

Ver a secção [Manutenção](README.pt.md#manutenção).

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
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/maintenance_task.png" alt="Tarefas de manutenção no ha-reef-card">
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

# API Cloud
A API Cloud permite-lhe:
- Iniciar ou parar atalhos: emergência, manutenção e alimentação,
- Obter informações do utilizador,
- Recuperar a biblioteca de waves,
- Recuperar a biblioteca de suplementos,
- Recuperar a biblioteca de programas LED,
- Ser notificado de uma [nova versão de firmware](https://github.com/Elwinmage/ha-reefbeat-component/#firmware-update),
- Enviar comandos ao ReefWave quando o modo "[Cloud ou Híbrido](https://github.com/Elwinmage/ha-reefbeat-component/#reefwave)" mode is selected.

Os atalhos, parâmetros de waves e LED estão ordenados por aquário.
<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_devices.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_ctrl.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_supplements.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_sensors.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_led_and_waves.png" alt="Image">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_api_conf.png" alt="Image">
</p>

>[!TIP]
> Pode desativar a obtenção da lista de suplementos na configuração do dispositivo API Cloud.
>    <img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/cloud_config.png" alt="Image">
***
# FAQ

## O meu dispositivo não é detetado
- Tente reiniciar a deteção automática com o botão "Adicionar entrada". Sometimes devices do not respond because they are busy.
- If your Red Sea devices are not on the same subnet as your Home Assistant, auto-detection will first fail and then offer you the option to enter the IP address of your device or the address of the subnet where your devices are located. For subnet detection, please use the format IP/MASK, for example: 192.168.14.0/255.255.255.0.
- You can also use [Manual Mode](https://github.com/Elwinmage/ha-reefbeat-component/#manual-mode).

<p align="center">
<img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/doc/img/subnetwork.png" alt="Image">
</p>

## Alguns dados são atualizados corretamente, outros não.
Os dados estão divididos em três partes: dados, configuração e informações do dispositivo.
- Os dados são atualizados regularmente.
- Os dados de configuração só são atualizados no arranque e quando prime o botão "Obter configuração".
- Os dados de informações do dispositivo só são atualizados no arranque.

Para garantir que os dados de configuração sejam atualizados regularmente, ative [Atualização de Configuração em Direto](#live-update).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
