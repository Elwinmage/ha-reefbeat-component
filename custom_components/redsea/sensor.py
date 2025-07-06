""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType

from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    UnitOfLength,
    UnitOfVolume,
    UnitOfTime,
    EntityCategory,
)

from .const import (
    DOMAIN,
)

from .coordinator import ReefBeatCoordinator, ReefDoseCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefBeatCoordinator], StateType]

@dataclass(kw_only=True)
class ReefDoseSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: ''
    head: 0

@dataclass(kw_only=True)
class ReefLedScheduleSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: ''
    id_name: 0
    
COMMON_SENSORS:tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription( 
       key="ip",
        translation_key="ip",
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/')].data.wifi_ip"),
        icon="mdi:check-network-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)
    
""" Reefbeat sensors list """
LED_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="fan",
        translation_key="fan",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/manual')].data.fan"),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan",
    ),
    ReefBeatSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/manual')].data.temperature"),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer",
        suggested_display_precision=1,
    ),
)

""" ReefMat sensors list """
MAT_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (

    ReefBeatSensorEntityDescription(
        key="days_till_end_of_roll",
        translation_key="days_till_end_of_roll",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.days_till_end_of_roll"),
        icon="mdi:sort-calendar-ascending",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="today_usage",
        translation_key="today_usage",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.today_usage"),
        icon="mdi:tape-measure",
        suggested_display_precision=2,
    ),
    ReefBeatSensorEntityDescription(
        key="daily_average_usage",
        translation_key="daily_average_usage",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.daily_average_usage"),
        icon="mdi:tape-measure",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key="total_usage",
        translation_key="total_usage",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.total_usage")/100,
        icon="mdi:paper-roll",
        suggested_display_precision=2,
    ),
    ReefBeatSensorEntityDescription(
        key="remaining_length",
        translation_key="remaining_length",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.remaining_length")/100,
        icon="mdi:paper-roll-outline",
        suggested_display_precision=2,
    ),
)


LED_SCHEDULES = ()
""" Lights and cloud schedule as sensors """
for auto_id in range(1,8):
    LED_SCHEDULES += (ReefLedScheduleSensorEntityDescription(
        key="auto_"+str(auto_id),
        translation_key="auto_"+str(auto_id),
        value_name="$.sources[?(@.name=='/preset_name')].data[?(@.day=="+str(auto_id)+")].name",
        id_name=auto_id,
        icon="mdi:calendar",
    ),)


""" ReefMat sensors list """
ATO_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (

    ReefBeatSensorEntityDescription(
        key='today_fills',
        translation_key='today_fills',
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.today_fills"),
        icon="mdi:counter",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key='today_volume_usage',
        translation_key='today_volume_usage',
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,   
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.today_volume_usage"),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key='total_volume_usage',
        translation_key='total_volume_usage',
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,   
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.total_volume_usage"),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key='total_fills',
        translation_key='total_fills',
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.total_fills"),
        icon="mdi:counter",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key='daily_fills_average',
        translation_key='daily_fills_average',
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.daily_fills_average"),
        icon="mdi:counter",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key='daily_volume_average',
        translation_key='daily_volume_average',
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,   
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.daily_volume_average"),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key='volume_left',
        translation_key='volume_left',
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.volume_left"),
        icon="mdi:water-pump-off",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key='current_level',
        translation_key='current_level',
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.ato_sensor.current_level"),
        icon="mdi:car-coolant-level",
    ),
    ReefBeatSensorEntityDescription(
        key='current_read',
        translation_key='current_read',
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.ato_sensor.current_read"),
        icon="mdi:water-thermometer-outline",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key='temperature_probe_status',
        translation_key='temperature_probe_status',
        value_fn=lambda device:  device.get_data("$.sources[?(@.name=='/dashboard')].data.ato_sensor.temperature_probe_status"),
        icon="mdi:thermometer-check",
    ),
)


    
async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None,
):
    """Configure reefbeat sensors from graphic user interface data"""
    device = hass.data[DOMAIN][entry.entry_id]
    entities=[]
    _LOGGER.debug("SENSORS")
    if type(device).__name__=='ReefLedCoordinator':
        entities += [ReefBeatSensorEntity(device, description)
                     for description in LED_SENSORS
                     if description.exists_fn(device)]
    elif type(device).__name__=='ReefMatCoordinator':
        entities += [ReefBeatSensorEntity(device, description)
                     for description in MAT_SENSORS
                     if description.exists_fn(device)]
    # REEFDOSE
    elif type(device).__name__=='ReefDoseCoordinator':
        ds=()
        for head in range (1,device.heads_nb+1):
            new_head= (ReefDoseSensorEntityDescription(
                key="supplement_head_"+str(head),
                translation_key="supplement",
                icon="mdi:shaker",
                value_name="$.sources[?(@.name=='/dashboard')].data.heads."+str(head)+".supplement",
                head=head,
            ),)
            ds+=new_head
            new_head=(ReefDoseSensorEntityDescription(
                key="auto_dosed_today_head_"+str(head),
                translation_key="auto_dosed_today",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=SensorDeviceClass.VOLUME,
                icon="mdi:cup-water",
                suggested_display_precision=0,
                value_name="$.sources[?(@.name=='/dashboard')].data.heads."+str(head)+".auto_dosed_today",
                head=head,
            ),)
            ds+=new_head
            new_head=( ReefDoseSensorEntityDescription(
                key="manual_dosed_today_head_"+str(head),
                translation_key="manual_dosed_today",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=SensorDeviceClass.VOLUME,
                icon="mdi:cup-water",
                suggested_display_precision=0,
                value_name="$.sources[?(@.name=='/dashboard')].data.heads."+str(head)+".manual_dosed_today",
                head=head,
            ),)
            ds+=new_head
            new_head=(ReefDoseSensorEntityDescription(
                key="doses_today_head_"+str(head),
                translation_key="doses_today",
                icon="mdi:counter",
                suggested_display_precision=0,
                value_name="$.sources[?(@.name=='/dashboard')].data.heads."+str(head)+".doses_today",
                head=head,
            ),)
            ds+=new_head
            new_head=( ReefDoseSensorEntityDescription(
                key="daily_dose_head_"+str(head),
                translation_key="daily_dose",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=SensorDeviceClass.VOLUME,
                icon="mdi:cup-water",
                suggested_display_precision=0,
                value_name="$.sources[?(@.name=='/dashboard')].data.heads."+str(head)+".daily_dose",
                head=head,
            ),)
            ds+=new_head
            new_head=(ReefDoseSensorEntityDescription(
                key="remaining_days_head_"+str(head),
                translation_key="remaining_days",
                native_unit_of_measurement=UnitOfTime.DAYS,
                icon="mdi:sort-calendar-ascending",
                suggested_display_precision=0,
                value_name="$.sources[?(@.name=='/dashboard')].data.heads."+str(head)+".remaining_days",
                head=head,
            ),)
            ds+=new_head
            new_head=( ReefDoseSensorEntityDescription(
                key="daily_doses_head_"+str(head),
                translation_key="daily_doses",
                icon="mdi:counter",
                suggested_display_precision=0,
                value_name="$.sources[?(@.name=='/dashboard')].data.heads."+str(head)+".daily_doses",
                head=head,
            ),)
            ds+=new_head
            new_head=( ReefDoseSensorEntityDescription(
                key="container_volume_head_"+str(head),
                translation_key="container_volume",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=SensorDeviceClass.VOLUME,
                icon="mdi:hydraulic-oil-level",
                suggested_display_precision=0,
                value_name="$.sources[?(@.name=='/head/"+str(head)+"/settings')].data.container_volume",
                head=head,
            ),)
            ds+=new_head

        entities += [ReefDoseSensorEntity(device, description)
                     for description in ds
                     if description.exists_fn(device)]
        
    elif type(device).__name__=='ReefATOCoordinator':
        entities += [ReefBeatSensorEntity(device, description)
                     for description in ATO_SENSORS
                     if description.exists_fn(device)]

    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefVirtualLedCoordinator':
        entities += [ReefLedScheduleSensorEntity(device, description)
                     for description in LED_SCHEDULES
                     if description.exists_fn(device)]

    entities += [ReefBeatSensorEntity(device, description)
                 for description in  COMMON_SENSORS
                 if description.exists_fn(device)]

    async_add_entities(entities, True)


class ReefBeatSensorEntity(SensorEntity):
    """Represent an ReefBeat sensor."""
    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False  
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        
    async def async_update(self) -> None:
        """Update entity state."""
        try:
            await self._device.update()
        except Exception as e:
           # _LOGGER.warning("Update failed for %s: %s", self.entity_id,e)
           # self._attr_available = False  # Set property value
           # return
            pass
        self._attr_available = True
        # We don't need to check if device available here
        self._attr_native_value =  self._get_value()
        
    def _get_value(self):
        if hasattr(self.entity_description, 'value_fn'):
            return self.entity_description.value_fn(self._device)
        elif hasattr(self.entity_description, 'value_name'):
            return self._device.get_data(self.entity_description.value_name)
        else:
            _LOGGER.error("redsea.binary_sensor.ReefBeatBinarySensorEntity._get_value: no method to get value")
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info


class ReefLedScheduleSensorEntity(ReefBeatSensorEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseSensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)

    async def async_update(self) -> None:
        """Update entity state."""
        try:
            await self._device.update()
        except Exception as e:
            pass
        self._attr_available = True
        # We don't need to check if device available here
        self._attr_native_value =  self._device.get_data(self.entity_description.value_name)
        prog_data=self._device.get_data("$.sources[?(@.name=='/auto/"+str(self.entity_description.id_name)+"')].data")
        cloud_data=self._device.get_data("$.sources[?(@.name=='/clouds/"+str(self.entity_description.id_name)+"')].data")
        self._attr_extra_state_attributes={'data':prog_data,'clouds':cloud_data}    

class ReefDoseSensorEntity(ReefBeatSensorEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseSensorEntityDescription
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
