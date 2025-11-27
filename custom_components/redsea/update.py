""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import (
    HomeAssistant,
    callback,
    )

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
    UpdateDeviceClass,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo


from homeassistant.const import (
    EntityCategory,
)

from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    )

from .coordinator import ReefBeatCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatUpdateEntityDescription(UpdateEntityDescription):
    """Describes reefbeat Update entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    version_installed: str
    
FIRMWARE_UPDATES: tuple[ReefBeatUpdateEntityDescription, ...] = (
    ReefBeatUpdateEntityDescription(
        key='firmware_update',
        translation_key='schedule_update',
        version_installed="$.sources[?(@.name=='/firmware')].data.version",
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
        device_class=UpdateDeviceClass.FIRMWARE,
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
    _LOGGER.debug("UPDATES")
    if device.__class__.__bases__[0].__name__=='ReefBeatCloudLinkedCoordinator':
        entities += [ReefBeatUpdateEntity(device, description)
                     for description in FIRMWARE_UPDATES
                     if description.exists_fn(device)]
    async_add_entities(entities, True)

class ReefBeatUpdateEntity(UpdateEntity):
    """Represent an ReefMat Update."""
    _attr_has_entity_name = True
    _attr_supported_features = (UpdateEntityFeature.INSTALL)
    
    def __init__(
        self, device, entity_description: ReefBeatUpdateEntityDescription
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_installed_version=self._device.sw_version
        self._attr_latest_version=self._attr_installed_version
        self._device._hass.bus.async_listen("request_latest_firmware",self._handle_ask_for_latest_firmware)
	
    @property
    def installed_version(self) -> str | None:
        """Version currently in use."""
        return self._device.sw_version

    def _handle_ask_for_latest_firmware(self,event):
        if event.data.get('device_name')==self._device._title:
            temp=self.latest_version
            _LOGGER.info("Last firmware version for %s is %s. Current installed versions is: %s"%(self._device._title,temp,self.installed_version))
    
    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        if self._device._cloud_link!= None and self._device.latest_firmware_url!=None:
            new_version = self._device._cloud_link.get_data("$.sources[?(@.name='"+self._device.latest_firmware_url+"')].data.version",True)
            if new_version:
                return new_version
        return self.installed_version
        
    async def async_install(self, version: str | None, backup: bool, **kwargs) -> None:
        await self.my_api.press("firmware")
        self._attr_installed_version = self._attr_latest_version

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

