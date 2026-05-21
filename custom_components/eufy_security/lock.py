import asyncio
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

LOCK_CONFIRM_TIMEOUT = 25
LOCK_CONFIRM_POLL_SECONDS = 5
LOCK_GRACE_SECONDS = 0.5


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

    def _set_busy(self, value: bool, *, locking: bool) -> None:
        """Show HA that a single command is in progress."""
        self._attr_is_locking = locking if value else False
        self._attr_is_unlocking = (not locking) if value else False

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        if not self.coordinator.is_lock_command_busy(self._control_product.serial_no):
            self.async_write_ha_state()

    async def _wait_for_lock_state(self, target: bool, timeout: float = LOCK_CONFIRM_TIMEOUT) -> bool:
        """Wait until MQTT/heartbeat reports the requested state on any lock property."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if self._control_product.lock_state_matches(target):
                self._control_product._apply_lock_properties(target)
                return True
            await asyncio.sleep(0.25)
        return False

    async def _set_locked(self, value: bool) -> None:
        if self._control_product.is_safe_lock is True and value is False:
            raise HomeAssistantError(
                f"Unlocking is not supported for safe lock ({self._control_product.name})"
            )

        serial = self._control_product.serial_no

        if self.coordinator.is_lock_command_busy(serial):
            _LOGGER.debug("Ignoring lock toggle while command in progress (%s)", serial)
            self.async_write_ha_state()
            return

        current = self._control_product.get_lock_state()
        if current == value:
            return

        if not await self.coordinator.try_begin_lock_command(serial):
            _LOGGER.debug("Ignoring lock toggle, could not acquire command slot (%s)", serial)
            self.async_write_ha_state()
            return

        self._set_busy(True, locking=value)
        self._control_product.begin_lock_command(value)
        self.async_write_ha_state()

        try:
            _LOGGER.info("Lock command %s -> locked=%s", serial, value)
            await self.coordinator.api.set_property(
                self._control_product.product_type,
                serial,
                MessageField.LOCKED.value,
                value,
            )
            confirmed = await self._wait_for_lock_state(value)
            if not confirmed:
                try:
                    await self.coordinator.api.poll_refresh()
                except WebSocketConnectionException:
                    pass
                confirmed = await self._wait_for_lock_state(value, timeout=LOCK_CONFIRM_POLL_SECONDS)
            if not confirmed:
                # Add-on accepted the command; MQTT echo can lag behind the physical lock.
                _LOGGER.warning(
                    "Lock %s: no property echo for locked=%s, assuming success after add-on OK",
                    serial,
                    value,
                )
                self._control_product._apply_lock_properties(value)
        except (FailedCommandException, WebSocketConnectionException) as exc:
            raise HomeAssistantError(f"Lock command failed: {exc}") from exc
        finally:
            await asyncio.sleep(LOCK_GRACE_SECONDS)
            self._control_product.end_lock_command()
            self.coordinator.end_lock_command(serial)
            self._set_busy(False, locking=value)
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
