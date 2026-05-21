import logging



from homeassistant.components.binary_sensor import BinarySensorEntity

from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant

from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.helpers.update_coordinator import CoordinatorEntity



from .const import COORDINATOR, DOMAIN, Platform, PlatformToPropertyType

from .coordinator import EufySecurityDataUpdateCoordinator

from .entity import EufySecurityEntity

from .eufy_security_api.product import Product

from .eufy_security_api.util import get_child_value

from .util import get_device_info, get_product_properties_by_filter



_LOGGER: logging.Logger = logging.getLogger(__package__)





async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:

    """Setup binary sensor entities."""

    coordinator: EufySecurityDataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]

    product_properties = get_product_properties_by_filter(

        [coordinator.devices.values(), coordinator.stations.values()],

        PlatformToPropertyType[Platform.BINARY_SENSOR.name].value,

    )

    entities = [EufySecurityBinarySensor(coordinator, metadata) for metadata in product_properties]



    seen_debug: set[str] = set()

    for product in list(coordinator.devices.values()) + list(coordinator.stations.values()):

        key = f"{product.product_type.value}_{product.serial_no}"

        if key in seen_debug:

            continue

        seen_debug.add(key)

        entities.append(EufySecurityProductEntity(coordinator, product))



    async_add_entities(entities)





class EufySecurityBinarySensor(EufySecurityEntity, BinarySensorEntity):

    """Base binary sensor entity for integration"""



    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, metadata) -> None:

        super().__init__(coordinator, metadata)



    @property

    def is_on(self):

        """Return true if the binary sensor is on."""

        return bool(get_child_value(self.product.properties, self.metadata.name))





class EufySecurityProductEntity(BinarySensorEntity, CoordinatorEntity):

    """Debug entity (properties/commands) shown next to person sensor on the device."""



    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, product: Product) -> None:

        super().__init__(coordinator)

        self.product = product

        self.product.set_state_update_listener(coordinator.async_update_listeners)



        self._attr_unique_id = f"{DOMAIN}_{product.product_type.value}_{product.serial_no}_debug"

        self._attr_should_poll = False

        self._attr_name = f"{product.name} Debug ({product.product_type.value})"

        self._attr_entity_registry_enabled_default = True

        self._attr_available = True



    @property

    def available(self) -> bool:

        api = getattr(self.coordinator, "_api", None)

        if api is None:

            return False

        return bool(api.devices or api.stations)



    @property

    def is_on(self):

        """Return true if the binary sensor is on."""

        return True



    @property

    def extra_state_attributes(self):

        return {

            "properties": {i: self.product.properties[i] for i in self.product.properties if i != "picture"},

            "commands": self.product.commands,

            "voices": self.product.voices if getattr(self.product, "is_camera", False) else None,

        }



    @property

    def device_info(self):

        return get_device_info(self.product)


