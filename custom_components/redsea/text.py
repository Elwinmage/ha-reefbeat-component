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

from homeassistant.components.text import (
    TextEntity,
    TextEntityDescription,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo


from homeassistant.const import (
    EntityCategory,
)

from .const import (
    DOMAIN,
)



from .coordinator import ReefBeatCoordinator

from .i18n import translate

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatTextEntityDescription(TextEntityDescription):
    """Describes reefbeat Text entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = None
    
@dataclass(kw_only=True)
class ReefDoseTextEntityDescription(TextEntityDescription):
    """Describes reefbeat Text entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    dependency: str = None
    value_name: str = None
    head: int = 0
    
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,  
):
    """Configuration de la plate-forme tuto_hacs à partir de la configuration graphique"""
    device = hass.data[DOMAIN][config_entry.entry_id]
    
    entities=[]
    _LOGGER.debug("TEXTS")
    if type(device).__name__=='ReefDoseCoordinator':
        dn=()
        for head in range(1,device.heads_nb+1):
            new_head=(ReefDoseTextEntityDescription(
                key="new_supplement_brand_name"+str(head),
                translation_key="new_supplement_brand_name",
                value_name="$.local.head."+str(head)+".new_supplement_brand_name",
                exists_fn=lambda _: True,
                icon="mdi:domain",
                dependency="$.local.head."+str(head)+".new_supplement",
                entity_category=EntityCategory.CONFIG,
                head=head,
            ),)
            dn+=new_head
            new_head=(ReefDoseTextEntityDescription(
                key="new_supplement_name"+str(head),
                translation_key="new_supplement_name",
                value_name="$.local.head."+str(head)+".new_supplement_name",
                exists_fn=lambda _: True,
                icon="mdi:tag-text-outline",
                entity_category=EntityCategory.CONFIG,
                dependency="$.local.head."+str(head)+".new_supplement",
                head=head,
            ),)
            dn+=new_head
            new_head=(ReefDoseTextEntityDescription(
                key="new_supplement_short_name"+str(head),
                translation_key="new_supplement_short_name",
                value_name="$.local.head."+str(head)+".new_supplement_short_name",
                exists_fn=lambda _: True,
                icon="mdi:text-short",
                dependency="$.local.head."+str(head)+".new_supplement",
                entity_category=EntityCategory.CONFIG,
                head=head,
            ),)
            dn+=new_head
        entities += [ReefDoseTextEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]
    async_add_entities(entities, True)

################################################################################
# BEAT
class ReefBeatTextEntity(CoordinatorEntity,TextEntity):
    """Represent an ReefBeat text."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatTextEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._value_name=entity_description.value_name
        self._attr_native_value =self._device.get_data(self._value_name)
        
    async def async_set_value(self, value: str) -> None:
        """Update the current texted option."""
        self._attr_native_value = value
        self._device.set_data(self._value_name,value)
        self.async_write_ha_state()        
        #await self._device.push_values(self._source,self._method)

    @property
    def available(self) -> bool:
        if self.entity_description.dependency is not None:
            if self.entity_description.dependency_values is not None:
                val=self._device.get_data(self.entity_description.dependency)
                if self.entity_description.translate is not None:
                    val=translate(val,"id",dictionnary=self.entity_description.translate,src_lang=self._device._hass.config.language)
                return val in self.entity_description.dependency_values
            else:
                return self._device.get_data(self.entity_description.dependency)
        else:
            return True
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info
 
    

################################################################################
# DOSE
class ReefDoseTextEntity(ReefBeatTextEntity):
    """Represent an ReefBeat sensor."""
    _attr_has_entity_name = True
    
    def __init__(
            self, device, entity_description: ReefDoseTextEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=self.entity_description.head
        self._attr_native_value = self._device.get_data(self._value_name)
        self._device._hass.bus.async_listen(self.entity_description.dependency, self._handle_update)
        self._attr_available = False
        
    @callback
    def _handle_update(self,event) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = event.data.get('other')
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._attr_available

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
