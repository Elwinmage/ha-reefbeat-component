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

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
    SwitchDeviceClass,
 )

from homeassistant.const import (
    EntityCategory,
)


from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo

from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    DAILY_PROG_INTERNAL_NAME,
    MAT_AUTO_ADVANCE_INTERNAL_NAME,
    MAT_SCHEDULE_ADVANCE_INTERNAL_NAME,
    ATO_AUTO_FILL_INTERNAL_NAME,
    LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
    LED_MOONPHASE_ENABLED_INTERNAL_NAME,
)

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator, ReefLedCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatSwitchEntityDescription(SwitchEntityDescription):
    """Describes reefbeat Switch entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: ''
    method: str = 'put'
    
@dataclass(kw_only=True)
class ReefLedSwitchEntityDescription(SwitchEntityDescription):
    """Describes reefbeat Switch entity."""
    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: ''
    method: str ='put'
#    delete: bool= False
    
@dataclass(kw_only=True)
class ReefDoseSwitchEntityDescription(SwitchEntityDescription):
    """Describes reefbeat Switch entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: ''
    head: 0
    method: str = 'put'

    
LED_SWITCHES: tuple[ReefLedSwitchEntityDescription, ...] = (
    ReefLedSwitchEntityDescription(
        key="sw_acclimation_enabled",
        translation_key="acclimation",
        value_name= LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
        icon="mdi:fish",
        method='post',
        entity_category=EntityCategory.CONFIG,
    ),
    ReefLedSwitchEntityDescription(
        key="sw_moonphase_enabled",
        translation_key="moon_phase",
        value_name= LED_MOONPHASE_ENABLED_INTERNAL_NAME,
        icon="mdi:weather-night",
        method='post',
        entity_category=EntityCategory.CONFIG,
    ),
)

MAT_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="auto_advance",
        translation_key="auto_advance",
        value_name=MAT_AUTO_ADVANCE_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:auto-mode",
        entity_category=EntityCategory.CONFIG,
        
    ),
    ReefBeatSwitchEntityDescription(
        key="scheduled_advance",
        translation_key="scheduled_advance",
        value_name=MAT_SCHEDULE_ADVANCE_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:auto-mode",
        entity_category=EntityCategory.CONFIG,
    ),

)

ATO_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="auto_fill",
        translation_key="auto_fill",
        value_name=ATO_AUTO_FILL_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:waves-arrow-up",
        entity_category=EntityCategory.CONFIG,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,  
):
    """Configuration de la plate-forme tuto_hacs à partir de la configuration graphique"""
    device = hass.data[DOMAIN][config_entry.entry_id]
        
    entities=[]
    _LOGGER.debug("SWITCHES")
    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefVirtualLedCoordinator'or type(device).__name__=='ReefLedG2Coordinator':
        entities += [ReefLedSwitchEntity(device, description, hass)
                 for description in LED_SWITCHES
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefMatCoordinator':
        entities += [ReefBeatSwitchEntity(device, description)
                 for description in MAT_SWITCHES
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefATOCoordinator':
        entities += [ReefBeatSwitchEntity(device, description)
                 for description in ATO_SWITCHES
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefDoseCoordinator':
        dn=()
        for head in range(1,device.heads_nb+1):
            new_head= (ReefDoseSwitchEntityDescription(
                key="schedule_enabled_head_"+str(head),
                translation_key="schedule_enabled",
                icon="mdi:pump",
                value_name="$.sources[?(@.name=='/head/"+str(head)+"/settings')].data.schedule_enabled",
                head=head,
                entity_category=EntityCategory.CONFIG,
            ), )
            dn+=new_head
            new_head= (ReefDoseSwitchEntityDescription(
                key="slm_head_"+str(head),
                translation_key="slm",
                icon="mdi:hydraulic-oil-level",
                value_name="$.sources[?(@.name=='/head/"+str(head)+"/settings')].data.slm",
                head=head,
                entity_category=EntityCategory.CONFIG, 
            ), )
            dn+=new_head
            
        entities += [ReefDoseSwitchEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]

    async_add_entities(entities, True)


class ReefBeatSwitchEntity(CoordinatorEntity,SwitchEntity):
    """Represent an ReefBeat switch."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatSwitchEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._source = self.entity_description.value_name.split('\'')[1]
        self._state = False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = True
        self._state = self._device.get_data(self.entity_description.value_name)
        self.async_write_ha_state()

        
    async def async_update(self) -> None:
        """Update entity state."""
        self._attr_available = True
        self._state = self._device.get_data(self.entity_description.value_name)

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state=True
        self._device.set_data(self.entity_description.value_name,True)
        self._device.async_update_listeners()
        self.async_write_ha_state()

        await self._device.push_values(self._source,self.entity_description.method)
        #await self._device.async_request_refresh()
        await self._device.async_quick_request_refresh(self._source)
        
        
    async def async_turn_off(self, **kwargs):
        self._state=False
        self._device.set_data(self.entity_description.value_name,False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        await self._device.push_values(self._source,self.entity_description.method)
        #await self._device.async_request_refresh()
        await self._device.async_quick_request_refresh(self._source)

        
    @property
    def is_on(self) -> bool:
        return self._state
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

################################################################################
# LED
class ReefLedSwitchEntity(ReefBeatSwitchEntity):
    """Represent an ReefBeat switch."""
    _attr_has_entity_name = True

    def __init__(
            self, device, entity_description: ReefDoseSwitchEntityDescription,hass
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self.hass = hass

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state=True
        self._device.set_data(self.entity_description.value_name,False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        await self._device.post_specific(self._source)
        await self._device.async_quick_request_refresh(self._source)
        #        await self._device.async_request_refresh()
        #self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._state=False
        self._device.set_data(self.entity_description.value_name,False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        await self._device.delete(self._source)
        await self._device.async_quick_request_refresh(self._source)
        #        await self._device.async_request_refresh()
        #self.async_write_ha_state()


###############################################################################
# DOSE
class ReefDoseSwitchEntity(ReefBeatSwitchEntity):
    """Represent an ReefBeat switch."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseSwitchEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=entity_description.head

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state=True
        self._device.set_data(self.entity_description.value_name,True)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        #await self._device.push_values('/head/'+str(self._head)+'/settings',self.entity_description.method)
        await self._device.push_values(self._head)
        await self._device.async_quick_request_refresh('/head/'+str(self._head)+'/settings')
        #await self._device.async_request_refresh()
        
    async def async_turn_off(self, **kwargs):
        self._state=False
        self._device.set_data(self.entity_description.value_name,False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        await self._device.push_values(self._head)
        await self._device.async_quick_request_refresh('/head/'+str(self._head)+'/settings')
        #await self._device.async_request_refresh()

        
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
    
