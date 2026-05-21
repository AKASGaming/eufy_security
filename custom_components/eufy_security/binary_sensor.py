import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import COORDINATOR, DOMAIN, Platform, PlatformToPropertyType
from .coordinator import EufySecurityDataUpdateCoordinator
from .entity import EufySecurityEntity
from .eufy_security_api.metadata import Metadata
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

    for device in coordinator.devices.values():
        entities.append(EufySecurityProductEntity(coordinator, device))

    for device in coordinator.stations.values():
        entities.append(EufySecurityProductEntity(coordinator, device))
    async_add_entities(entities)


class EufySecurityBinarySensor(EufySecurityEntity, BinarySensorEntity):
    """Base binary sensor entity for integration"""

    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, metadata: Metadata) -> None:
        super().__init__(coordinator, metadata)

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return bool(get_child_value(self.product.properties, self.metadata.name))


class EufySecurityProductEntity(EufySecurityEntity, BinarySensorEntity):
    """Debug entity for integration"""

    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, product: Product) -> None:
        metadata = Metadata.parse(
            product,
            {"name": "debug", "label": "Debug", "readable": True, "writeable": False},
        )
        super().__init__(coordinator, metadata)
        self._debug_product = product
        self._attr_unique_id = f"{DOMAIN}_{product.product_type.value}_{product.serial_no}_debug"
        self._attr_name = f"{product.name} Debug ({product.product_type.value})"
        self._attr_entity_category = None
        self._attr_entity_registry_enabled_default = False

    @property
    def product(self) -> Product:
        return self._debug_product

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return True

    @property
    def extra_state_attributes(self):
        return {
            "properties": {i: self.product.properties[i] for i in self.product.properties if i != "picture"},
            # "metadata": self.product.metadata_org,
            "commands": self.product.commands,
            "voices": self.product.voices if self.product.is_camera else None,
        }

    @property
    def device_info(self):
        return get_device_info(self.product)
