""" Implements the binary sensor entity """
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

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType

from homeassistant.const import EntityCategory

from .const import (
    DOMAIN,
)

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator, ReefRunCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes ReefLed binary sensor entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefBeatCoordinator], StateType]

@dataclass(kw_only=True)
class ReefDoseBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes ReefLed binary sensor entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: ""
    head: 0

@dataclass(kw_only=True)
class ReefRunBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes ReefLed binary sensor entity."""
    exists_fn: Callable[[ReefRunCoordinator], bool] = lambda _: True
    value_name: ""
    pump: 0


""" Reefbeat device common binary_sesors """
COMMON_SENSORS:tuple[ReefBeatBinarySensorEntityDescription, ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="battery_level",
        translation_key="battery_level",
        device_class=BinarySensorDeviceClass.BATTERY,
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.battery_level")=='low',
        icon="mdi:battery-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

    
""" ReefLed Binary Sensor List """    
LED_SENSORS: tuple[ReefBeatBinarySensorEntityDescription, ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=BinarySensorDeviceClass.LIGHT,
        value_fn=lambda device: device.get_data("$.local.status"),
        icon="mdi:wall-sconce-flat",
    ),
)

""" ReefMat Binary Sensor List """    
MAT_SENSORS: tuple[ReefBeatBinarySensorEntityDescription, ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="unclean_sensor",
        translation_key="unclean_sensor",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.unclean_sensor"),
        icon="mdi:liquid-spot",
    ),
    ReefBeatBinarySensorEntityDescription(
        key='is_ec_sensor_connected',
        translation_key='is_ec_sensor_connected',
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.is_ec_sensor_connected"),
        icon="mdi:connection",
    ),
)

ATO_SENSORS: tuple[ReefBeatBinarySensorEntityDescription, ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="water_level",
        translation_key='water_level',
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: not device.get_data("$.sources[?(@.name=='/dashboard')].data.water_level").startswith("desired"),
        icon="mdi:water-alert",
    ),
    ReefBeatBinarySensorEntityDescription(
        key='connected',
        translation_key='connected',
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.leak_sensor.connected"),
        icon="mdi:connection",
    ),
    ReefBeatBinarySensorEntityDescription(
        key='enabled',
        translation_key='enabled',
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.leak_sensor.enabled"),
        icon="mdi:leak",
    ),
    ReefBeatBinarySensorEntityDescription(
        key='buzzer_enabled',
        translation_key='buzzer_enabled',
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.leak_sensor.buzzer_enabled"),
        icon="mdi:volume-high",
    ),
    ReefBeatBinarySensorEntityDescription(
        key='status',
        translation_key='status',
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.leak_sensor.status")!="dry",
        icon="mdi:water-off",
    ),
    ReefBeatBinarySensorEntityDescription(
        key='is_sensor_error',
        translation_key='is_sensor_error',
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.ato_sensor.is_sensor_error"),
        icon="mdi:alert-circle-outline",
    ),
    ReefBeatBinarySensorEntityDescription(
        key='is_temp_enabled',
        translation_key='is_temp_enabled',
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.ato_sensor.is_temp_enabled"),
        icon="mdi:thermometer-check",
    ),
    ReefBeatBinarySensorEntityDescription(
        key='is_pump_on',
        translation_key='is_pump_on',
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.is_pump_on"),
        icon="mdi:pump",
    ),
)

""" ReefRunBinary Sensor List """
RUN_SENSORS: tuple[ReefBeatBinarySensorEntityDescription, ...] = (
    ReefBeatBinarySensorEntityDescription(
        key='ec_sensor_connected',
        translation_key='ec_sensor_connected',
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data("$.sources[?(@.name=='/dashboard')].data.ec_sensor_connected"),
        icon="mdi:connection",
    ),
)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None,
):
    """ Configure binary entities """
    device = hass.data[DOMAIN][entry.entry_id]
    entities=[]
    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefVirtualLedCoordinator' or type(device).__name__=='ReefLedG2Coordinator':
        entities += [ReefBeatBinarySensorEntity(device, description)
                     for description in LED_SENSORS
                     if description.exists_fn(device)]
    elif type(device).__name__=="ReefMatCoordinator":
        entities += [ReefBeatBinarySensorEntity(device, description)
                     for description in MAT_SENSORS
                     if description.exists_fn(device)]
    elif type(device).__name__=="ReefATOCoordinator":
        entities += [ReefBeatBinarySensorEntity(device, description)
                     for description in ATO_SENSORS
                     if description.exists_fn(device)]
    elif type(device).__name__=='ReefDoseCoordinator':
        ds=()
        for head in range (1,device.heads_nb+1):
            new_head= (ReefDoseBinarySensorEntityDescription(
                key="recalibration_required_head_"+str(head),
                translation_key="recalibration_required",
                icon="mdi:water-percent-alert",
                device_class=BinarySensorDeviceClass.PROBLEM,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_name="$.sources[?(@.name=='/dashboard')].data.heads."+str(head)+".recalibration_required",
                head=head,
            ),)
            ds+=new_head
    
        entities += [ReefDoseBinarySensorEntity(device, description)
                     for description in ds
                     if description.exists_fn(device)]
    elif  type(device).__name__=='ReefRunCoordinator':

        ds=()
        for pump in range (1,3):

            new_pump= (ReefRunBinarySensorEntityDescription(
                key="sensor_controlled_pump_"+str(pump),
                translation_key="sensor_controlled",
                icon="mdi:car-cruise-control",
                value_name="$.sources[?(@.name=='/dashboard')].data.pump_"+str(pump)+".sensor_controlled",
                pump=pump,
            ),)
            ds+=new_pump
            new_pump= (ReefRunBinarySensorEntityDescription(
                key="schedule_enabled_pump_"+str(pump),
                translation_key="schedule_enabled",
                icon="mdi:calendar-arrow-right",
                value_name="$.sources[?(@.name=='/dashboard')].data.pump_"+str(pump)+".schedule_enabled",
                pump=pump,
            ),)
            ds+=new_pump
            new_pump= (ReefRunBinarySensorEntityDescription(
                key="missing_sensor_pump_"+str(pump),
                translation_key="missing_sensor",
                device_class=BinarySensorDeviceClass.PROBLEM,
                entity_category=EntityCategory.DIAGNOSTIC,
                icon="mdi:leak-off",
                value_name="$.sources[?(@.name=='/dashboard')].data.pump_"+str(pump)+".missing_sensor",
                pump=pump,
            ),)
            ds+=new_pump
            new_pump= (ReefRunBinarySensorEntityDescription(
                key="missing_pump_pump_"+str(pump),
                translation_key="missing_pump",
                device_class=BinarySensorDeviceClass.PROBLEM,
                entity_category=EntityCategory.DIAGNOSTIC,
                icon="mdi:alert-outline",
                value_name="$.sources[?(@.name=='/dashboard')].data.pump_"+str(pump)+".missing_pump",
                pump=pump,
            ),)
            ds+=new_pump
        entities += [ReefRunBinarySensorEntity(device, description)
                     for description in ds
                     if description.exists_fn(device)]
        entities += [ReefBeatBinarySensorEntity(device, description)
                     for description in RUN_SENSORS
                     if description.exists_fn(device)]

    entities += [ReefBeatBinarySensorEntity(device, description)
                 for description in  COMMON_SENSORS
                 if description.exists_fn(device)]
        
    async_add_entities(entities, True)

class ReefBeatBinarySensorEntity(CoordinatorEntity,BinarySensorEntity):
    """Represent an binary sensor."""
    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._state=self._get_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = True
        self._state=self._get_value()
        self.async_write_ha_state()

    def _get_value(self):
        if hasattr(self.entity_description, 'value_fn'):
            return self.entity_description.value_fn(self._device)
        elif hasattr(self.entity_description, 'value_name'):
            return self._device.get_data(self.entity_description.value_name)
        else:
            _LOGGER.error("redsea.binary_sensor.ReefBeatBinarySensorEntity._get_value: no method to get value")
        
    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""
        self._state=self._get_value()
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

class ReefDoseBinarySensorEntity(ReefBeatBinarySensorEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseBinarySensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=self.entity_description.head

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

class ReefRunBinarySensorEntity(ReefBeatBinarySensorEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefRunBinarySensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._pump=self.entity_description.pump

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
