import logging
from typing import Any, Optional

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_CODE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EufySecurityDataUpdateCoordinator
from .entity import EufySecurityEntity
from .eufy_security_api.const import MessageField
from .eufy_security_api.exceptions import FailedCommandException, WebSocketConnectionException
from .eufy_security_api.metadata import Metadata
from .eufy_security_api.product import Device, Product

_LOGGER: logging.Logger = logging.getLogger(__package__)


def _iter_lock_setups(coordinator: EufySecurityDataUpdateCoordinator):
    """Yield (control_product, locked_metadata) for each smart lock."""
    seen: set[str] = set()

    for device in coordinator.devices.values():
        if device.serial_no in seen:
            continue
        locked_meta = device.get_lock_metadata()
        if locked_meta is None or not device.supports_lock_entity():
            continue
        seen.add(device.serial_no)
        yield device, locked_meta

    for station in coordinator.stations.values():
        if station.serial_no in seen:
            continue
        paired: Optional[Device] = coordinator.devices.get(station.serial_no)
        if paired is not None:
            locked_meta = paired.get_lock_metadata()
            if locked_meta is not None and paired.supports_lock_entity():
                seen.add(station.serial_no)
                yield paired, locked_meta
            continue
        locked_meta = station.get_lock_metadata()
        if locked_meta is not None and station.supports_lock_entity():
            seen.add(station.serial_no)
            yield station, locked_meta


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup lock entities."""
    coordinator: EufySecurityDataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]
    entities = []
    for product, locked_meta in _iter_lock_setups(coordinator):
        _LOGGER.info(
            "Registering lock entity for %s (%s)",
            product.name,
            product.serial_no,
        )
        entities.append(EufySecurityLock(coordinator, locked_meta, product))

    if not entities:
        _LOGGER.warning(
            "No lock entities created (devices=%s stations=%s)",
            list(coordinator.devices),
            list(coordinator.stations),
        )
    async_add_entities(entities)


class EufySecurityLock(EufySecurityEntity, LockEntity):
    """Lock entity for Eufy smart locks (including T85D0 / T85L0 MQTT locks)."""

    def __init__(
        self,
        coordinator: EufySecurityDataUpdateCoordinator,
        metadata: Metadata,
        control_product: Product,
    ) -> None:
        self._control_product = control_product
        super().__init__(coordinator, metadata)
        self._attr_name = f"{control_product.name}"
        self._attr_entity_category = None
        self._attr_entity_registry_enabled_default = True

    @property
    def product(self) -> Product:
        return self._control_product

    @property
    def is_locked(self) -> Optional[bool]:
        return self._control_product.get_lock_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        self.async_write_ha_state()

    def _apply_local_lock_state(self, value: bool) -> None:
        """Optimistic UI update; MQTT heartbeats will confirm."""
        self._control_product.properties[MessageField.LOCKED.value] = value
        self._control_product.properties[MessageField.LOCK_STATUS.value] = 4 if value else 3
        self._control_product._sync_property_to_paired(MessageField.LOCKED.value, value)
        self._control_product._sync_property_to_paired(
            MessageField.LOCK_STATUS.value, self._control_product.properties[MessageField.LOCK_STATUS.value]
        )

    async def _set_locked(self, value: bool) -> None:
        if self._control_product.is_safe_lock is True and value is False:
            raise HomeAssistantError(
                f"Unlocking is not supported for safe lock ({self._control_product.name})"
            )
        _LOGGER.info(
            "Lock command %s -> locked=%s",
            self._control_product.serial_no,
            value,
        )
        try:
            await self.coordinator.api.set_property(
                self._control_product.product_type,
                self._control_product.serial_no,
                MessageField.LOCKED.value,
                value,
            )
        except (FailedCommandException, WebSocketConnectionException) as exc:
            raise HomeAssistantError(f"Lock command failed: {exc}") from exc
        self._apply_local_lock_state(value)
        self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        if self._control_product.is_safe_lock is True:
            raise HomeAssistantError(
                f"Locking is not supported for lock ({self._control_product.name})"
            )
        await self._set_locked(True)

    async def async_unlock(self, **kwargs: Any) -> None:
        code = kwargs.get(ATTR_CODE, None)
        if self._control_product.is_safe_lock is True and code is not None:
            if await self._control_product.unlock(code) is False:
                raise HomeAssistantError(
                    f"PIN verification failed for lock ({self._control_product.name})"
                )
        else:
            await self._set_locked(False)
