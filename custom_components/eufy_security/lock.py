import logging
from typing import Any, Optional

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_CODE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EufySecurityDataUpdateCoordinator
from .entity import EufySecurityEntity
from .eufy_security_api.const import MessageField, ProductType
from .eufy_security_api.metadata import Metadata
from .eufy_security_api.product import Product

_LOGGER: logging.Logger = logging.getLogger(__package__)


def _iter_lock_products(coordinator: EufySecurityDataUpdateCoordinator):
    """Devices and standalone-lock stations that support lock control."""
    seen: set[str] = set()
    for product in coordinator.devices.values():
        if product.supports_lock_entity() and product.serial_no not in seen:
            seen.add(product.serial_no)
            yield product
    for product in coordinator.stations.values():
        if product.serial_no in seen:
            continue
        if product.supports_lock_entity():
            seen.add(product.serial_no)
            yield product


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup lock entities."""
    coordinator: EufySecurityDataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]
    metadatas: list[Metadata] = []
    for product in _iter_lock_products(coordinator):
        locked_meta = product.metadata.get(MessageField.LOCKED.value)
        if locked_meta is not None:
            metadatas.append(locked_meta)
            _LOGGER.debug(
                "Registering lock entity for %s (%s)",
                product.name,
                product.serial_no,
            )

    entities = [EufySecurityLock(coordinator, metadata) for metadata in metadatas]
    async_add_entities(entities)


class EufySecurityLock(LockEntity, EufySecurityEntity):
    """Lock entity for Eufy smart locks (including T85D0 / T85L0 MQTT locks)."""

    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, metadata: Metadata) -> None:
        super().__init__(coordinator, metadata)
        self._attr_name = f"{self.product.name}"

    @property
    def is_locked(self) -> Optional[bool]:
        return self.product.get_lock_state()

    async def _set_locked(self, value: bool) -> None:
        if self.product.is_safe_lock is True and value is False:
            raise HomeAssistantError(f"Unlocking is not supported for safe lock ({self.product.name})")
        if self.product.product_type == ProductType.station:
            await self.coordinator.api.set_property(
                ProductType.device, self.product.serial_no, self.metadata.name, value
            )
        else:
            await self.product.set_property(self.metadata, value)

    async def async_lock(self, **kwargs: Any) -> None:
        if self.product.is_safe_lock is True:
            raise HomeAssistantError(f"Locking is not supported for lock ({self.product.name})")
        await self._set_locked(True)

    async def async_unlock(self, **kwargs: Any) -> None:
        code = kwargs.get(ATTR_CODE, None)
        if self.product.is_safe_lock is True and code is not None:
            if await self.product.unlock(code) is False:
                raise HomeAssistantError(f"PIN verification failed for lock ({self.product.name})")
        else:
            await self._set_locked(False)
