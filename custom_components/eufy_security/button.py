import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EufySecurityDataUpdateCoordinator
from .entity import EufySecurityEntity
from .eufy_security_api.metadata import Metadata
from .eufy_security_api.const import ProductCommand

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Setup binary sensor entities."""
    coordinator: EufySecurityDataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]
    product_properties = []
    for product in list(coordinator.devices.values()) + list(coordinator.stations.values()):
        for command in ProductCommand:
            if getattr(product, command.name, None) is None:
                continue
            remote_cmd = command.value.command
            if remote_cmd is not None:
                if remote_cmd == "is_rtsp_enabled":
                    if product.is_rtsp_enabled is False:
                        continue
                elif remote_cmd not in product.commands:
                    continue
            elif command.name not in product.commands:
                # e.g. trigger_alarm / reset_alarm without a remote command id
                continue

            product_properties.append(
                Metadata.parse(product, {"name": command.name, "label": command.value.description, "command": command.value})
            )

    entities = [EufySecurityButtonEntity(coordinator, metadata) for metadata in product_properties]
    async_add_entities(entities)


class EufySecurityButtonEntity(EufySecurityEntity, ButtonEntity):
    """Base button entity for integration"""

    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, metadata: Metadata) -> None:
        super().__init__(coordinator, metadata)
        # Command buttons must be enabled controls, not hidden diagnostic entities.
        self._attr_entity_category = None
        self._attr_entity_registry_enabled_default = True

    async def async_press(self) -> None:
        """Press the button."""
        handler_func = getattr(self.product, f"{self.metadata.name}")
        await handler_func()
