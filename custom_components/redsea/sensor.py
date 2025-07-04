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
    FAN_INTERNAL_NAME,
    TEMPERATURE_INTERNAL_NAME,
    IP_INTERNAL_NAME,
    MAT_TODAY_USAGE_INTERNAL_NAME,
    MAT_DAILY_AVERAGE_USAGE_INTERNAL_NAME,
    MAT_TOTAL_USAGE_INTERNAL_NAME,
    MAT_REMAINING_LENGTH_INTERNAL_NAME,
    MAT_DAYS_TILL_END_OF_ROLL_INTERNAL_NAME,
    DOSE_SUPPLEMENT_INTERNAL_NAME,
    DOSE_STATE_INTERNAL_NAME,
    DOSE_AUTO_DOSED_TODAY_INTERNAL_NAME,
    DOSE_MANUAL_DOSED_TODAY_INTERNAL_NAME,
    DOSE_DOSES_TODAY_INTERNAL_NAME,
    DOSE_DAILY_DOSE_INTERNAL_NAME,
    DOSE_REMAINING_DAYS_INTERNAL_NAME,
    DOSE_STOCK_LEVEL_INTERNAL_NAME,
    DOSE_DAILY_DOSES_INTERNAL_NAME,
    ATO_TODAY_FILLS_INTERNAL_NAME,
    ATO_TODAY_VOLUME_USAGE_INTERNAL_NAME,
    ATO_TOTAL_VOLUME_USAGE_INTERNAL_NAME,
    ATO_TOTAL_FILLS_INTERNAL_NAME,
    ATO_DAILY_FILLS_AVERAGE_INTERNAL_NAME,
    ATO_DAILY_VOLUME_AVERAGE_INTERNAL_NAME,
    ATO_VOLUME_LEFT_INTERNAL_NAME,
    ATO_DAYS_TILL_EMPTY_INTERNAL_NAME,
    ATO_ATO_SENSOR_CURRENT_LEVEL_INTERNAL_NAME,
    ATO_ATO_SENSOR_CURRENT_READ_INTERNAL_NAME,
    ATO_ATO_SENSOR_TEMPERATURE_PROBE_STATUS_INTERNAL_NAME,
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

""" Reefbeat sensors list """
SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="fan",
        translation_key="fan",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(FAN_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(FAN_INTERNAL_NAME),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan",
    ),
    ReefBeatSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(TEMPERATURE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(TEMPERATURE_INTERNAL_NAME),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer",
    ),
    ReefBeatSensorEntityDescription(
        key="ip",
        translation_key="ip",
        value_fn=lambda device:  device.get_data(IP_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(IP_INTERNAL_NAME),
        icon="mdi:check-network-outline",
    ),
)

""" ReefMat sensors list """
MAT_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (

    ReefBeatSensorEntityDescription(
        key="days_till_end_of_roll",
        translation_key="days_till_end_of_roll",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda device:  device.get_data(MAT_DAYS_TILL_END_OF_ROLL_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_DAYS_TILL_END_OF_ROLL_INTERNAL_NAME),
        icon="mdi:sort-calendar-ascending",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="today_usage",
        translation_key="today_usage",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(MAT_TODAY_USAGE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_TODAY_USAGE_INTERNAL_NAME),
        icon="mdi:tape-measure",
        suggested_display_precision=2,
    ),
    ReefBeatSensorEntityDescription(
        key="daily_average_usage",
        translation_key="daily_average_usage",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(MAT_DAILY_AVERAGE_USAGE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_DAILY_AVERAGE_USAGE_INTERNAL_NAME),
        icon="mdi:tape-measure",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key="total_usage",
        translation_key="total_usage",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(MAT_TOTAL_USAGE_INTERNAL_NAME)/100,
        exists_fn=lambda device: device.data_exist(MAT_TOTAL_USAGE_INTERNAL_NAME),
        icon="mdi:paper-roll",
        suggested_display_precision=2,
    ),
    ReefBeatSensorEntityDescription(
        key="remaining_length",
        translation_key="remaining_length",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(MAT_REMAINING_LENGTH_INTERNAL_NAME)/100,
        exists_fn=lambda device: device.data_exist(MAT_REMAINING_LENGTH_INTERNAL_NAME),
        icon="mdi:paper-roll-outline",
        suggested_display_precision=2,
    ),
)


SCHEDULES = ()
""" Lights and cloud schedule as sensors """
for auto_id in range(1,8):
    SCHEDULES += (ReefBeatSensorEntityDescription(
        key="auto_"+str(auto_id),
        translation_key="auto_"+str(auto_id),
        value_fn=lambda device: device.get_prog_name("auto_"+str(auto_id)),
        exists_fn=lambda device: device.data_exist("auto_"+str(auto_id)),
        icon="mdi:calendar",
    ),)


""" ReefMat sensors list """
ATO_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (

    ReefBeatSensorEntityDescription(
        key=ATO_TODAY_FILLS_INTERNAL_NAME,
        translation_key=ATO_TODAY_FILLS_INTERNAL_NAME,
        value_fn=lambda device:  device.get_data(ATO_TODAY_FILLS_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_TODAY_FILLS_INTERNAL_NAME),
        icon="mdi:counter",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_TODAY_VOLUME_USAGE_INTERNAL_NAME,
        translation_key=ATO_TODAY_VOLUME_USAGE_INTERNAL_NAME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,   
        value_fn=lambda device:  device.get_data(ATO_TODAY_VOLUME_USAGE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_TODAY_VOLUME_USAGE_INTERNAL_NAME),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_TOTAL_VOLUME_USAGE_INTERNAL_NAME,
        translation_key=ATO_TOTAL_VOLUME_USAGE_INTERNAL_NAME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,   
        value_fn=lambda device:  device.get_data(ATO_TOTAL_VOLUME_USAGE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_TOTAL_VOLUME_USAGE_INTERNAL_NAME),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_TOTAL_FILLS_INTERNAL_NAME,
        translation_key=ATO_TOTAL_FILLS_INTERNAL_NAME,
        value_fn=lambda device:  device.get_data(ATO_TOTAL_FILLS_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_TOTAL_FILLS_INTERNAL_NAME),
        icon="mdi:counter",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_DAILY_FILLS_AVERAGE_INTERNAL_NAME,
        translation_key=ATO_DAILY_FILLS_AVERAGE_INTERNAL_NAME,
        value_fn=lambda device:  device.get_data(ATO_DAILY_FILLS_AVERAGE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_DAILY_FILLS_AVERAGE_INTERNAL_NAME),
        icon="mdi:counter",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_DAILY_VOLUME_AVERAGE_INTERNAL_NAME,
        translation_key=ATO_DAILY_VOLUME_AVERAGE_INTERNAL_NAME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,   
        value_fn=lambda device:  device.get_data(ATO_DAILY_VOLUME_AVERAGE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_DAILY_VOLUME_AVERAGE_INTERNAL_NAME),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_VOLUME_LEFT_INTERNAL_NAME,
        translation_key=ATO_VOLUME_LEFT_INTERNAL_NAME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,
        value_fn=lambda device:  device.get_data(ATO_VOLUME_LEFT_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_VOLUME_LEFT_INTERNAL_NAME),
        icon="mdi:water-pump-off",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_ATO_SENSOR_CURRENT_LEVEL_INTERNAL_NAME,
        translation_key=ATO_ATO_SENSOR_CURRENT_LEVEL_INTERNAL_NAME,
        value_fn=lambda device:  device.get_data(ATO_ATO_SENSOR_CURRENT_LEVEL_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_ATO_SENSOR_CURRENT_LEVEL_INTERNAL_NAME),
        icon="mdi:car-coolant-level",
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_ATO_SENSOR_CURRENT_READ_INTERNAL_NAME,
        translation_key=ATO_ATO_SENSOR_CURRENT_READ_INTERNAL_NAME,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(ATO_ATO_SENSOR_CURRENT_READ_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_ATO_SENSOR_CURRENT_READ_INTERNAL_NAME),
        icon="mdi:water-thermometer-outline",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key=ATO_ATO_SENSOR_TEMPERATURE_PROBE_STATUS_INTERNAL_NAME,
        translation_key=ATO_ATO_SENSOR_TEMPERATURE_PROBE_STATUS_INTERNAL_NAME,
        value_fn=lambda device:  device.get_data(ATO_ATO_SENSOR_TEMPERATURE_PROBE_STATUS_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_ATO_SENSOR_TEMPERATURE_PROBE_STATUS_INTERNAL_NAME),
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
    _LOGGER.debug(type(device).__name__)
    if type(device).__name__=='ReefLedCoordinator':
        entities += [ReefBeatSensorEntity(device, description)
                     for description in SENSORS
                     if description.exists_fn(device)]
    elif type(device).__name__=='ReefMatCoordinator':
        _LOGGER.debug(MAT_SENSORS)
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
                exists_fn=lambda device: device.data_exist(str(head)+'_'+DOSE_SUPPLEMENT_INTERNAL_NAME),
                icon="mdi:shaker",
                head=head,
                value_name=DOSE_SUPPLEMENT_INTERNAL_NAME,
            ),)
            ds+=new_head
            new_head=(ReefDoseSensorEntityDescription(
                key="auto_dosed_today_head_"+str(head),
                translation_key="auto_dosed_today",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=SensorDeviceClass.VOLUME,
                exists_fn=lambda device: device.data_exist(str(head)+'_'+DOSE_AUTO_DOSED_TODAY_INTERNAL_NAME),
                icon="mdi:cup-water",
                suggested_display_precision=0,
                head=head,
                value_name=DOSE_AUTO_DOSED_TODAY_INTERNAL_NAME,
            ),)
            ds+=new_head
            new_head=( ReefDoseSensorEntityDescription(
                key="manual_dosed_today_head_"+str(head),
                translation_key="manual_dosed_today",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=SensorDeviceClass.VOLUME,
                exists_fn=lambda device: device.data_exist(str(head)+'_'+DOSE_MANUAL_DOSED_TODAY_INTERNAL_NAME),
                icon="mdi:cup-water",
                suggested_display_precision=0,
                head=head,
                value_name=DOSE_MANUAL_DOSED_TODAY_INTERNAL_NAME,
            ),)
            ds+=new_head
            new_head=(ReefDoseSensorEntityDescription(
                key="doses_today_head_"+str(head),
                translation_key="doses_today",
                exists_fn=lambda device: device.data_exist(str(head)+'_'+DOSE_DOSES_TODAY_INTERNAL_NAME),
                icon="mdi:counter",
                suggested_display_precision=0,
                head=head,
                value_name=DOSE_DOSES_TODAY_INTERNAL_NAME,
            ),)
            ds+=new_head
            new_head=( ReefDoseSensorEntityDescription(
                key="daily_dose_head_"+str(head),
                translation_key="daily_dose",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=SensorDeviceClass.VOLUME,
                exists_fn=lambda device: device.data_exist(str(head)+'_'+DOSE_DAILY_DOSE_INTERNAL_NAME),
                icon="mdi:cup-water",
                suggested_display_precision=0,
                head=head,
                value_name=DOSE_DAILY_DOSE_INTERNAL_NAME,
            ),)
            ds+=new_head
            new_head=(ReefDoseSensorEntityDescription(
                key="remaining_days_head_"+str(head),
                translation_key="remaining_days",
                native_unit_of_measurement=UnitOfTime.DAYS,
                exists_fn=lambda device: device.data_exist(str(head)+'_'+DOSE_REMAINING_DAYS_INTERNAL_NAME),
                icon="mdi:sort-calendar-ascending",
                suggested_display_precision=0,
                head=head,
                value_name=DOSE_REMAINING_DAYS_INTERNAL_NAME,
            ),)
            ds+=new_head
            new_head=( ReefDoseSensorEntityDescription(
                key="daily_doses_head_"+str(head),
                translation_key="daily_doses",
                exists_fn=lambda device: device.data_exist(str(head)+'_'+DOSE_DAILY_DOSES_INTERNAL_NAME),
                icon="mdi:counter",
                suggested_display_precision=0,
                head=head,
                value_name=DOSE_DAILY_DOSES_INTERNAL_NAME,
            ),)
            ds+=new_head

        entities += [ReefDoseSensorEntity(device, description)
                     for description in ds
                     if description.exists_fn(device)]
        
    elif type(device).__name__=='ReefATOCoordinator':
        _LOGGER.debug(ATO_SENSORS)
        entities += [ReefBeatSensorEntity(device, description)
                     for description in ATO_SENSORS
                     if description.exists_fn(device)]

    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefLedVirtualCoordinator':
        entities += [ReefBeatSensorEntity(device, description)
                     for description in SCHEDULES
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
        self._attr_native_value =  self.entity_description.value_fn(
            self._device
        )  # Update "native_value" property
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info


class ReefDoseSensorEntity(ReefBeatSensorEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseSensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=self.entity_description.head
        

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
        self._attr_native_value =  self._device.get_data(str(self._head)+'_'+self.entity_description.value_name)
            
        


    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di=self._device.device_info
        di['name']+='_head_'+str(self._head)
        identifiers=list(di['identifiers'])[0]
        head=("head_"+str(self._head),)
        identifiers+=head
        di['identifiers']={identifiers}
        _LOGGER.info(di)
        return di
