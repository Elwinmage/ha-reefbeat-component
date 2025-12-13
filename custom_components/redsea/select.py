""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import (
    HomeAssistant,
    callback,
    )

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    )

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo


from homeassistant.const import (
    EntityCategory,
)

from .const import (
    DOMAIN,
    HW_MAT_MODEL,
    MAT_MODEL_INTERNAL_NAME,
    MAT_POSITION_INTERNAL_NAME,
    LED_MODE_INTERNAL_NAME,
    LED_MODES,
    SKIMMER_MODELS,
    WAVE_TYPES,
    WAVE_DIRECTIONS
)

from .supplements_list import (SUPPLEMENTS)

from .coordinator import ReefBeatCoordinator

from .i18n import translate_list,translate

SUPPLEMENTS=sorted(SUPPLEMENTS, key=lambda d: d['fullname'])
_LOGGER = logging.getLogger(__name__)
       
@dataclass(kw_only=True)
class ReefBeatSelectEntityDescription(SelectEntityDescription):
    """Describes reefbeat Select entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    entity_registry_visible_default: bool = True
    value_name: str = ''
    options: []
    method: str = 'put'

@dataclass(kw_only=True)
class ReefRunSelectEntityDescription(SelectEntityDescription):
    """Describes reefbeat Select entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    entity_registry_visible_default: bool = True
    value_name: str = ''
    pump: int = 0 
    options: []
    method: str = 'put'


@dataclass(kw_only=True)
class ReefWaveSelectEntityDescription(SelectEntityDescription):
    """Describes reefbeat Select entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ''
    options: []
    method: str = 'post'
    i18n_options: []

@dataclass(kw_only=True)
class ReefDoseSelectEntityDescription(SelectEntityDescription):
    """Describes reefbeat Select entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ''
    options: []
    head: int = 0
    method: str = 'post'
    
MAT_SELECTS: tuple[ReefBeatSelectEntityDescription, ...] = (
    ReefBeatSelectEntityDescription(
        key="model",
        translation_key="model",
        value_name=MAT_MODEL_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:movie-roll",
        options=HW_MAT_MODEL,
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=False,
    ),
    ReefBeatSelectEntityDescription(
        key="position",
        translation_key="position",
        value_name=MAT_POSITION_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:set-left-right",
        options=['left','right'],
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=False,
    ),
)

LED_SELECTS: tuple[ReefBeatSelectEntityDescription, ...] = (
    ReefBeatSelectEntityDescription(
        key="mode",
        translation_key="mode",
        value_name=LED_MODE_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:auto-mode",
        options=LED_MODES,
        entity_category=EntityCategory.CONFIG,
        method='post',
    ),
)

# TODO : Add speed change management
#  labels: enhancement, rsdose

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,  
):
    """Configuration de la plate-forme tuto_hacs à partir de la configuration graphique"""
    device = hass.data[DOMAIN][config_entry.entry_id]
    
    entities=[]
    _LOGGER.debug("SELECTS")
    if type(device).__name__=='ReefMatCoordinator':
        entities += [ReefBeatSelectEntity(device, description)
                 for description in MAT_SELECTS
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefDoseCoordinator':
        dn=()
        for head in range(1,device.heads_nb+1):
            new_head=(ReefDoseSelectEntityDescription(
                key="supplements_"+str(head),
                translation_key="supplements",
                value_name="$.local.head."+str(head)+".new_supplement",
                exists_fn=lambda _: True,
                icon="mdi:shaker",
                options=translate_list(SUPPLEMENTS,"fullname"),
                entity_category=EntityCategory.CONFIG,
                head=head,
            ),)
            dn+=new_head
        entities += [ReefDoseSelectEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefLedG2Coordinator' or type(device).__name__=='ReefVirtualLedCoordinator' :
        entities += [ReefBeatSelectEntity(device, description)
                 for description in LED_SELECTS
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefWaveCoordinator':
        waves=(
            ReefWaveSelectEntityDescription(
                key="preview_wave_type",
                translation_key="preview_wave_type",
                value_name="$.sources[?(@.name=='/preview')].data.type",
                exists_fn=lambda _: True,
                icon="mdi:wave",
                i18n_options=WAVE_TYPES,
                options=translate_list(WAVE_TYPES,hass.config.language),
                entity_category=EntityCategory.CONFIG,
            ),
            ReefWaveSelectEntityDescription(
                key="preview_wave_direction",
                translation_key="preview_wave_direction",
                value_name="$.sources[?(@.name=='/preview')].data.direction",
                exists_fn=lambda _: True,
                icon="mdi:waves-arrow-right",
                i18n_options=WAVE_DIRECTIONS,
                options=translate_list(WAVE_DIRECTIONS,hass.config.language),
                entity_category=EntityCategory.CONFIG,
            ),
        )
        entities += [ReefWaveSelectEntity(device, description)
                     for description in waves
                     if description.exists_fn(device)]

    elif type(device).__name__=='ReefRunCoordinator':
        ds=()
        for pump in range (1,3):
            if(device.get_data("$.sources[?(@.name=='/pump/settings')].data.pump_"+str(pump)+".type")=="skimmer"):
                new_pump=(
                    ReefRunSelectEntityDescription(
                        key="model_skimmer_pump_"+str(pump),
                        translation_key="model",
                        value_name="$.sources[?(@.name=='/pump/settings')].data.pump_"+str(pump)+".model",
                        exists_fn=lambda _: True,
                        icon="mdi:raspberry-pi",
                        options=SKIMMER_MODELS,
                        entity_category=EntityCategory.CONFIG,
                        pump=pump,
                        method='put',
                    ),)
                ds+=new_pump
            entities += [ReefRunSelectEntity(device, description)
                     for description in ds
                     if description.exists_fn(device)]
        
    async_add_entities(entities, True)

################################################################################
# BEAT
class ReefBeatSelectEntity(CoordinatorEntity,SelectEntity):
    """Represent an ReefBeat select."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatSelectEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        other=translate("other",self._device.hass.config.language)
        self._attr_options = entity_description.options+[other]
        self._value_name=entity_description.value_name
        self._attr_current_option = self._device.get_data(self._value_name)
        try: 
            self._source = self.entity_description.value_name.split('\'')[1]
            self._method=entity_description.method
        except Exception:
            #ReefDose
            pass

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = True
        self._attr_current_option = self._device.get_data(self._value_name)
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        self._device.set_data(self._value_name,option)
        self.async_write_ha_state()        
        await self._device.push_values(self._source,self._method)
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info
    
################################################################################
# RUN
class ReefRunSelectEntity(ReefBeatSelectEntity):
    """Represent an ReefBeat sensor."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefRunSelectEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._pump=self.entity_description.pump

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        self._device.set_data(self._value_name,option)
        self.async_write_ha_state()        
        await self._device.push_values(pump=self._pump)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di=self._device.device_info
        di['name']+='_pump_'+str(self._pump)
        identifiers=list(di['identifiers'])[0]
        pump=("pump_"+str(self._pump),)
        identifiers+=pump
        di['identifiers']={identifiers}
        return di
################################################################################
# DOSE
class ReefDoseSelectEntity(ReefBeatSelectEntity):
    """Represent an ReefBeat sensor."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefRunSelectEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=self.entity_description.head
        self._attr_current_option = translate(self._device.get_data(self._value_name),'fullname',dictionnary=SUPPLEMENTS,src_lang='uid')
        
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = True
        value=self._device.get_data(self._value_name)
        if value == "other":
            self._attr_current_option = translate("other",self._device._hass.config.language)
        else:
            self._attr_current_option = translate(self._device.get_data(self._value_name),'fullname',dictionnary=SUPPLEMENTS,src_lang='uid')                
        self.async_write_ha_state()
                
    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        if option==translate("other",self._device._hass.config.language):
            value="other"
            self._device._hass.bus.fire(self.entity_description.value_name, {"other":True})
        else:
            value=translate(option,"uid",dictionnary=SUPPLEMENTS,src_lang="fullname")
            self._device._hass.bus.fire(self.entity_description.value_name, {"other":False})
        _LOGGER.debug("Setting new supplement %s"%value)
        self._device.set_data(self._value_name,value)
        #self._device.async_update_listeners()
        self.async_write_ha_state()        

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di=self._device.device_info
        di['name']+='_head_'+str(self._head)
        identifiers=list(di['identifiers'])[0]
        head=("head_"+str(self._head),)
        identifiers+=head
        di['identifiers']={identifiers}
        return di
    
################################################################################
# WAVE
class ReefWaveSelectEntity(ReefBeatSelectEntity):
    """Represent an ReefBeat sensor."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefWaveSelectEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._attr_current_option = translate(self._device.get_data(self._value_name),self._device._hass.config.language,dictionnary=self.entity_description.i18n_options)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = True
        self._attr_current_option = translate(self._device.get_data(self._value_name),self._device._hass.config.language,dictionnary=self.entity_description.i18n_options)
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        value=translate(option,"id",dictionnary=self.entity_description.i18n_options,src_lang=self._device._hass.config.language)
        self._device.set_data(self._value_name,value)
        self._device.async_update_listeners()
        self.async_write_ha_state()        
