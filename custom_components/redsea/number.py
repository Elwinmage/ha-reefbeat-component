""" Implements the sensor entity """
# ruff: noqa: I001
# ruff: noqa: F401
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
    ATO_VOLUME_LEFT_INTERNAL_NAME,
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
    WAVE_SHORTCUT_OFF_DELAY,
    WAVE_TYPES,
)

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator, ReefLedCoordinator, ReefRunCoordinator, ReefWaveCoordinator, ReefATOCoordinator

from .i18n import translate_list,translate

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ""
    dependency: str = None
    dependency_values: [] = None
    translate: [] = None
    
@dataclass(kw_only=True)
class ReefRunNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefRunCoordinator], bool] = lambda _: True
    dependency: str = None
    dependency_values: [] = None
    translate: [] = None
    value_name: str = ""
    pump: int = 0

@dataclass(kw_only=True)
class ReefLedNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: str = ""
    post_specific: bool = False
    dependency: str = None
    dependency_values: [] = None
    translate: [] = None
    
@dataclass(kw_only=True)
class ReefDoseNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: str =  ""
    head: int = 0
    dependency: str = None
    dependency_values: [] = None
    translate: [] = None

WAVE_NUMBERS: tuple[ReefBeatNumberEntityDescription, ...] = (
    ReefBeatNumberEntityDescription(
        key='shortcut_off_delay',
        translation_key='shortcut_off_delay',
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=600,
        native_min_value=0,
        native_step=1,
        value_name=WAVE_SHORTCUT_OFF_DELAY,
        icon="mdi:arrow-expand-right",
        entity_category=EntityCategory.CONFIG,
    ),
)

WAVE_PREVIEW_NUMBERS: tuple[ReefBeatNumberEntityDescription, ...] = (
    ReefBeatNumberEntityDescription(
        key='wave_forward_time',
        translation_key='wave_forward_time',
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=60,
        native_min_value=2,
        native_step=1,
        value_name="$.sources[?(@.name=='/preview')].data.frt",
        icon="mdi:waves-arrow-right",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        translate=WAVE_TYPES,
        dependency_values=["st","ra","re","un"],
    ),
    ReefBeatNumberEntityDescription(
        key='wave_backward_time',
        translation_key='wave_backward_time',
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=60,
        native_min_value=2,
        native_step=1,
        value_name="$.sources[?(@.name=='/preview')].data.rrt",
        icon="mdi:waves-arrow-left",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        translate=WAVE_TYPES,
        dependency_values=["st","ra","re","un"],
    ),
    ReefBeatNumberEntityDescription(
        key='wave_forward_intensity',
        translation_key='wave_forward_intensity',
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.POWER_FACTOR,
        native_max_value=100,
        native_min_value=10,
        native_step=10,
        value_name="$.sources[?(@.name=='/preview')].data.fti",
        icon="mdi:waves-arrow-right",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        translate=WAVE_TYPES,
        dependency_values=["st","ra","re","su","un"],
    ),
    ReefBeatNumberEntityDescription(
        key='wave_backward_intensity',
        translation_key='wave_backward_intensity',
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.POWER_FACTOR,
        native_max_value=100,
        native_min_value=10,
        native_step=10,
        value_name="$.sources[?(@.name=='/preview')].data.rti",
        icon="mdi:waves-arrow-left",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        translate=WAVE_TYPES,
        dependency_values=["st","ra","re","su","un"],
    ),
    ReefBeatNumberEntityDescription(
        key='wave_preview_duration',
        translation_key='wave_preview_duration',
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=600000,
        native_min_value=60000,
        native_step=60000,
        value_name="$.sources[?(@.name=='/preview')].data.duration",
        icon="mdi:timer-sand",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatNumberEntityDescription(
        key='wave_preview_step',
        translation_key='wave_preview_step',
        device_class=NumberDeviceClass.DURATION,
        native_max_value=10,
        native_min_value=3,
        native_step=1,
        value_name="$.sources[?(@.name=='/preview')].data.sn",
        icon="mdi:stairs",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        translate=WAVE_TYPES,
        dependency_values=["st"],
    ),
    ReefBeatNumberEntityDescription(
        key='wave_preview_wave_duration',
        translation_key='wave_preview_wave_duration',
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=25,
        native_min_value=2,
        native_step=1,
        value_name="$.sources[?(@.name=='/preview')].data.pd",
        icon="mdi:clock-time-five",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        translate=WAVE_TYPES,
        dependency_values=["st","un","su"],
    ),

)

    
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
        entities += [ReefLedNumberEntity(device, description,hass)
                 for description in LED_NUMBERS
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefMatCoordinator':
        entities += [ReefBeatNumberEntity(device, description)
                 for description in MAT_NUMBERS
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefDoseCoordinator':
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
                key="calibration_dose_value_head_"+str(head),
                translation_key="calibration_dose_value",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                native_min_value=4.5,
                native_step=0.05,
                native_max_value=5.5,
                value_name="$.local.head."+str(head)+".calibration_dose",
                icon="mdi:test-tube-empty",
                head=head,
                entity_category=EntityCategory.CONFIG,
                entity_registry_visible_default=False,
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
                native_max_value=6000,
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
    elif type(device).__name__=='ReefRunCoordinator':
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
                value_name="$.sources[?(@.name=='/dashboard')].data.pump_"+str(pump)+".intensity",
                icon="mdi:waves",
                pump=pump,
            ), )
            dn+=new_pump
            new_pump= (ReefRunNumberEntityDescription(
                key="preview_pump_"+str(pump)+"_intensity",
                translation_key="preview_speed",
                native_unit_of_measurement=PERCENTAGE,
                native_min_value=1,
                native_step=1,
                native_max_value=100,
                value_name="$.sources[?(@.name=='/preview')].data.pump_"+str(pump)+".ti",
                icon="mdi:waves",
                pump=pump,
                entity_category=EntityCategory.CONFIG,
            ), )
            dn+=new_pump
            
        entities += [ReefRunNumberEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefWaveCoordinator':
        entities += [ReefBeatNumberEntity(device, description)
                 for description in WAVE_NUMBERS
                 if description.exists_fn(device)]
        entities += [ReefWaveNumberEntity(device, description)
                 for description in WAVE_PREVIEW_NUMBERS
                 if description.exists_fn(device)]

    elif type(device).__name__ == "ReefATOCoordinator":
        dn = ()
        dn += (ReefBeatNumberEntityDescription(
            key="ato_volume_left",
            translation_key="ato_volume_left",
            mode="box",
            native_unit_of_measurement=UnitOfVolume.MILLILITERS,
            device_class=NumberDeviceClass.VOLUME,
            native_min_value=0,
            native_step=1,
            native_max_value=200000,  # pick a safe ceiling
            value_name=ATO_VOLUME_LEFT_INTERNAL_NAME,
            icon="mdi:cup-water",
            entity_category=EntityCategory.CONFIG,
        ),)

        entities += [ReefATOVolumeLeftNumberEntity(device, description)
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
        try:
            self._source = self.entity_description.value_name.split('\'')[1]
        except Exception:
            self._source='/configuration'
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_native_value=3.25
        if self.entity_description.dependency is not None:
            self._device._hass.bus.async_listen(self.entity_description.dependency, self._handle_coordinator_update)


    @callback
    def _handle_coordinator_update(self,event=None) -> None:
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
        if self.entity_description.native_unit_of_measurement==UnitOfTime.SECONDS:
            f_value=int(value)
        else:
            f_value=value
        self._attr_native_value=f_value
        self._device.set_data(self.entity_description.value_name,f_value)
        await self._device.push_values(self._source)
        await self._device.async_request_refresh()

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
        if self.entity_description.post_specific is False:
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
            if self.entity_description.translation_key!='calibration_dose_value':
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
        _LOGGER.debug("Reefbeat.number.set_native_value %d"%int(value))
        self._attr_native_value=value
        if self.entity_description.key=="preview_pump_"+str(self._pump)+"_intensity":
            # do not send push request for changing speed preview. It's done by the preview start button
            self._device.set_data(self.entity_description.value_name,int(value))
            return 
        elif self.entity_description.key=='pump_'+str(self._pump)+'_intensity':
            await self._device.set_pump_intensity(self._pump,int(value))
            self.async_write_ha_state()  
            await self._device.push_values(source='/pump/settings',pump=self._pump)
            await self._device.async_request_refresh()
        else:
            self._device.set_data(self.entity_description.value_name,int(value))
            self.async_write_ha_state()  
            await self._device.push_values(source=self._source,pump=self._pump)
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


    
################################################################################
# WAVE
class ReefWaveNumberEntity(ReefBeatNumberEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatNumberEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        value=self._device.get_data(self.entity_description.value_name,True)
        if self.entity_description.key=='wave_preview_wave_duration' and self._device.get_data("$.sources[?(@.name=='/preview')].data.type") == 'su':
            # limite values for surface 
            self._attr_native_min_value=0.5
            self._attr_native_max_value=5.9
            self._attr_native_step=0.1
        else:
            self._attr_native_min_value=self.entity_description.native_min_value
            self._attr_native_max_value=self.entity_description.native_max_value
            self._attr_native_step=self.entity_description.native_step
            if value is not None:
                value=int(value)
        if value is None:
            _LOGGER.debug("%s is None!!!"%self.entity_description.value_name)
            self._attr_available = False
            self._attr_native_value = None
        else:
            self._attr_available = self.available
            self._attr_native_value=value
        self.async_write_ha_state()

        
    async def async_set_native_value(self, value: int) -> None:
        self._attr_native_value=value
        self._device.set_data(self.entity_description.value_name,int(value)) 
        self.async_write_ha_state()
    


################################################################################
# ATO
class ReefATOVolumeLeftNumberEntity(ReefBeatNumberEntity):
    async def async_set_native_value(self, value: float) -> None:
        volume_ml = int(value)
        await self._device.set_volume_left(volume_ml)
        await self._device.async_request_refresh()
