""" Implements the sensor entity """
import logging
import asyncio

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

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
 )

from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfVolume,
    UnitOfTime,
    UnitOfTemperature,
    EntityCategory,
)

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo

from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    MAT_MIN_ROLL_DIAMETER,
    MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
    MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME,
    LED_MOONPHASE_ENABLED_INTERNAL_NAME,
    LED_MOON_DAY_INTERNAL_NAME,
    LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
    LED_ACCLIMATION_DURATION_INTERNAL_NAME,
    LED_ACCLIMATION_INTENSITY_INTERNAL_NAME,
    LED_MANUAL_DURATION_INTERNAL_NAME,
    LED_KELVIN_INTERNAL_NAME,
)

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator, ReefLedCoordinator, ReefRunCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: ""
    dependency: str = None

@dataclass(kw_only=True)
class ReefRunNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefRunCoordinator], bool] = lambda _: True
    dependency: str = None
    value_name: ""
    pump: 0

@dataclass(kw_only=True)
class ReefLedNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: ""
    post_specific: bool = False
    dependency: str = None
    
@dataclass(kw_only=True)
class ReefDoseNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: ""
    head: 0
    dependency: str = None
    
MAT_NUMBERS: tuple[ReefBeatNumberEntityDescription, ...] = (
    ReefBeatNumberEntityDescription(
        key='custom_advance_value',
        translation_key='custom_advance_value',
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        native_max_value=48,
        native_min_value=0.75,
        native_step=0.5,
        value_name=MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
        icon="mdi:arrow-expand-right",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatNumberEntityDescription(
        key='started_roll_diameter',
        translation_key='started_roll_diameter',
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        native_max_value=11.1,
        native_min_value=MAT_MIN_ROLL_DIAMETER,
        native_step=0.1,
        value_name=MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME,
        icon="mdi:arrow-expand-right",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatNumberEntityDescription(
        key='schedule_length',
        translation_key='schedule_length',
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        native_min_value=5,
        native_max_value=45,
        native_step=2.5,
        value_name="$.sources[?(@.name=='/configuration')].data.schedule_length",
        icon="mdi:arrow-expand-right",
        entity_category=EntityCategory.CONFIG,
    ),

)

LED_NUMBERS: tuple[ReefLedNumberEntityDescription, ...] = (
    ReefLedNumberEntityDescription(
        key='moon_day',
        translation_key='moon_day',
        native_max_value=28,
        native_min_value=1,
        native_step=1,
        value_name=LED_MOON_DAY_INTERNAL_NAME,
        post_specific='/moonphase',
        icon="mdi:moon-waning-crescent",
        entity_category=EntityCategory.CONFIG,
        dependency=LED_MOONPHASE_ENABLED_INTERNAL_NAME,
    ),
    ReefLedNumberEntityDescription(
        key='acclimation_duration',
        translation_key='acclimation_duration',
        native_max_value=99,
        native_min_value=2,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_name=LED_ACCLIMATION_DURATION_INTERNAL_NAME,
        icon="mdi:calendar-expand-horizontal",
        post_specific='/acclimation',
        dependency=LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
        entity_category=EntityCategory.CONFIG,
    ),
    ReefLedNumberEntityDescription(
        key='acclimation_start_intensity_factor',
        translation_key='acclimation_start_intensity_factor',
        native_max_value=100,
        native_min_value=1,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        value_name=LED_ACCLIMATION_INTENSITY_INTERNAL_NAME,
        post_specific='/acclimation',
        icon="mdi:sun-wireless-outline",
        dependency=LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
        entity_category=EntityCategory.CONFIG,
    ),
    ReefLedNumberEntityDescription(
        key='manual_duration',
        translation_key='manual_duration',
        native_max_value=120,
        native_min_value=0,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_name=LED_MANUAL_DURATION_INTERNAL_NAME,
        post_specific='/timer',
        icon="mdi:clock-start",
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
    _LOGGER.debug("NUMBERS")
    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefVirtualLedCoordinator' or type(device).__name__=='ReefLedG2Coordinator':
        min_kelvin=9000
        if  type(device).__name__=='ReefLedG2Coordinator':
            min_kelvin=8000
        KELVIN_LED: tuple[ReefLedNumberEntityDescription, ...] = (
            ReefLedNumberEntityDescription(
            key='kelvin',
            translation_key='kelvin',
            native_max_value=23000,
            native_min_value=min_kelvin,
            native_step=500,
            value_name=LED_KELVIN_INTERNAL_NAME,
            icon="mdi:palette",
            post_specific=False,
            native_unit_of_measurement=UnitOfTemperature.KELVIN,
        ),)
        entities += [ReefLedNumberEntity(device, description,hass)
                 for description in LED_NUMBERS
                 if description.exists_fn(device)]
        entities += [ReefLedNumberEntity(device, description,hass)
                    for description in KELVIN_LED
                     if description.exists_fn(device)]

    if type(device).__name__=='ReefMatCoordinator':
        entities += [ReefBeatNumberEntity(device, description)
                 for description in MAT_NUMBERS
                 if description.exists_fn(device)]
    if type(device).__name__=='ReefDoseCoordinator':
        dn=()
        new_head= (ReefDoseNumberEntityDescription(
            key="stock_alert_days",
            translation_key="stock_alert_days",
            native_unit_of_measurement=UnitOfTime.DAYS,
            native_min_value=1,
            native_step=1,
            native_max_value=45,
            value_name="$.sources[?(@.name=='/device-settings')].data.stock_alert_days",
            icon="mdi:hydraulic-oil-level",
            head=0,
            entity_category=EntityCategory.CONFIG,
        ), )
        dn+=new_head
        new_head= (ReefDoseNumberEntityDescription(
            key="dosing_waiting_period",
            translation_key="dosing_waiting_period",
            native_unit_of_measurement=UnitOfTime.SECONDS,
            native_min_value=15,
            native_step=1,
            native_max_value=600,
            value_name="$.sources[?(@.name=='/device-settings')].data.dosing_waiting_period",
            icon="mdi:sleep",
            head=0,
            entity_category=EntityCategory.CONFIG, 
        ), )
        dn+=new_head
        
        for head in range(1,device.heads_nb+1):
            new_head= (ReefDoseNumberEntityDescription(
                key="manual_head_"+str(head)+"_volume",
                translation_key="manual_head_volume",
                mode="box",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=NumberDeviceClass.VOLUME,
                native_min_value=0,
                native_step=1,
                native_max_value=300,
                value_name="$.local.head."+str(head)+".manual_dose",
                icon="mdi:cup-water",
                head=head,
                entity_category=EntityCategory.CONFIG,
            ), )
            dn+=new_head
            new_head= (ReefDoseNumberEntityDescription(
                key="daily_dose_head_"+str(head)+"_volume",
                translation_key="daily_dose",
                mode="box",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=NumberDeviceClass.VOLUME,
                native_min_value=0,
                native_step=1,
                native_max_value=300,
                value_name="$.sources[?(@.name=='/head/"+str(head)+"/settings')].data.schedule.dd",
                icon="mdi:cup-water",
                head=head,
                entity_category=EntityCategory.CONFIG,
            ), )
            dn+=new_head
            new_head= (ReefDoseNumberEntityDescription(
                key="container_volume_head_"+str(head)+"_volume",
                translation_key="container_volume",
                mode="box",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=NumberDeviceClass.VOLUME,
                native_min_value=0,
                native_step=1,
                native_max_value=2000,
                value_name="$.sources[?(@.name=='/head/"+str(head)+"/settings')].data.container_volume",
                icon="mdi:cup-water",
                head=head,
                entity_category=EntityCategory.CONFIG, 
                dependency="$.sources[?(@.name=='/head/"+str(head)+"/settings')].data.slm",
            ), )
            dn+=new_head
            
        entities += [ReefDoseNumberEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]
    if type(device).__name__=='ReefRunCoordinator':
        dn=()
        new_pump= (ReefBeatNumberEntityDescription(
            key="overskimming_threshold",
            translation_key="overskimming_threshold",
            native_unit_of_measurement=PERCENTAGE,
            native_min_value=0,
            native_step=1,
            native_max_value=100,
            value_name="$.sources[?(@.name=='/pump/settings')].data.overskimming.threshold",
            icon="mdi:cloud-percent-outline",
         ), )
        dn+=new_pump
        entities += [ReefBeatNumberEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]
        dn=()
        for pump in range(1,3):
            new_pump= (ReefRunNumberEntityDescription(
                key="pump_"+str(pump)+"_intensity",
                translation_key="speed",
                native_unit_of_measurement=PERCENTAGE,
                native_min_value=0,
                native_step=1,
                native_max_value=100,
                value_name="$.sources[?(@.name=='/pump/settings')].data.pump_"+str(pump)+".schedule[0].ti",
                icon="mdi:waves",
                pump=pump,
            ), )
            dn+=new_pump
            
        entities += [ReefRunNumberEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]
        
    async_add_entities(entities, True)

################################################################################
# BEAT
class ReefBeatNumberEntity(CoordinatorEntity,NumberEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatNumberEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_native_value=3.25

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = self.available
        self._attr_native_value=self._device.get_data(self.entity_description.value_name)
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return self._device.get_data(self.entity_description.value_name)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.debug("Reefbeat.number.set_native_value %f"%value)
        self._attr_native_value=value
        self._device.set_data(self.entity_description.value_name,value)
        await self._device.push_values()
        await self._device.async_request_refresh()

    @property
    def available(self) -> bool:
        if self.entity_description.dependency != None:
            return self._device.get_data(self.entity_description.dependency)
        else:
            return True
       
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

################################################################################
# LED
class ReefLedNumberEntity(ReefBeatNumberEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
            self, device, entity_description: ReefLedNumberEntityDescription,hass
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self.hass = hass
            
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.debug("Reefbeat.number.set_native_value %f"%value)
        self._attr_native_value=value
        self._device.set_data(self.entity_description.value_name,value)
        self.async_write_ha_state()
        if self.entity_description.post_specific==False:
            await self._device.push_values(self.entity_description.value_name.split('\'')[1],'post')
        else:
            await self._device.post_specific(self.entity_description.post_specific)
        await self._device.async_request_refresh()
        
################################################################################
# DOSE
class ReefDoseNumberEntity(ReefBeatNumberEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseNumberEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=self.entity_description.head
        self._attr_native_value=0

    async def async_set_native_value(self, value: int) -> None:
        """Update the current value."""
        _LOGGER.debug("Reefbeat.number.set_native_value %f"%value)
        self._attr_native_value=value
        self._device.set_data(self.entity_description.value_name,value)
        self.async_write_ha_state()  
        if self._head > 0:
            await self._device.push_values(self._head)
        else:
            await self._device.push_values("/device-settings")
        await self._device.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        if self._head > 0:
            di=self._device.device_info
            di['name']+='_head_'+str(self._head)
            identifiers=list(di['identifiers'])[0]
            head=("head_"+str(self._head),)
            identifiers+=head
            di['identifiers']={identifiers}
            return di
        else:
            return self._device.device_info


################################################################################
# RUN
class ReefRunNumberEntity(ReefBeatNumberEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseNumberEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._pump=self.entity_description.pump
        self._attr_native_value=0

    async def async_set_native_value(self, value: int) -> None:
        """Update the current value."""
        _LOGGER.debug("Reefbeat.number.set_native_value %f"%value)
        self._attr_native_value=value
        self._device.set_data(self.entity_description.value_name,int(value))
        self.async_write_ha_state()  
        await self._device.push_values(self._pump)
        await self._device.async_request_refresh()

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


    
