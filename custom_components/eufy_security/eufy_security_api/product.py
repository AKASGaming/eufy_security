import asyncio
from collections.abc import Callable
import logging
from typing import Any, Optional

from .const import EventNameToHandler, MessageField, ProductCommand, ProductType, UNSUPPORTED
from .event import Event
from .metadata import Metadata

_LOGGER: logging.Logger = logging.getLogger(__package__)


class Product:
    """Product"""

    def __init__(self, api, product_type: ProductType, serial_no: str, properties: dict, metadata: dict, commands: []) -> None:
        self.api = api
        self.product_type = product_type
        self.serial_no = serial_no

        self.name: str = None
        self.model: str = None
        self.hardware_version: str = None
        self.software_version: str = None

        self.properties: dict = None
        self.metadata: dict = None
        self.metadata_org = metadata
        self.commands = commands
        self.connected = True

        self.state_update_listener: Callable = None

        self._set_properties(properties)
        self._set_metadata(metadata)

        self.pin_verified_future = None
        self._lock_pending_target: Optional[bool] = None

    def begin_lock_command(self, target_locked: bool) -> None:
        """Mark an in-flight lock/unlock so stale MQTT updates are ignored."""
        self._lock_pending_target = target_locked

    def end_lock_command(self) -> None:
        self._lock_pending_target = None

    def _set_properties(self, properties: dict) -> None:
        self.properties = properties
        _LOGGER.debug(f"_set_properties -{self.serial_no} - {str(properties)[0:5000]}")
        self.name = properties.get(MessageField.NAME.value, "UNSUPPORTED")
        self.model = properties.get(MessageField.MODEL.value, "UNSUPPORTED")
        self.hardware_version = properties.get(MessageField.HARDWARE_VERSION.value, "UNSUPPORTED")
        self.software_version = properties.get(MessageField.SOFTWARE_VERSION.value, "UNSUPPORTED")

    def _set_metadata(self, metadata: dict) -> None:
        self.metadata = {}

        for key, value in metadata.items():
            metadata = Metadata.parse(self, value)

            if key == "motionDetected" and metadata.name == "motionDetection":
                metadata.name = key

            self.metadata[key] = metadata

    def set_state_update_listener(self, listener: Callable):
        """Set listener function when state changes"""
        self.state_update_listener = listener

    async def set_property(self, metadata, value: Any):
        """Process set property call"""
        await self.api.set_property(self.product_type, self.serial_no, metadata.name, value)

    async def trigger_alarm(self, duration: int = 10):
        """Process trigger alarm call"""
        await self.api.trigger_alarm(self.product_type, self.serial_no, duration)

    async def reset_alarm(self):
        """Process reset alarm call"""
        await self.api.reset_alarm(self.product_type, self.serial_no)

    async def snooze(self, snooze_time: int, snooze_chime: bool, snooze_motion: bool, snooze_homebase: bool) -> None:
        """Process snooze call"""
        await self.api.snooze(self.product_type, self.serial_no, snooze_time, snooze_chime, snooze_motion, snooze_homebase)
        await self.api.poll_refresh()

    async def unlock(self, code: str) -> bool:
        """Process unlock the safe"""
        self.pin_verified_future = asyncio.get_running_loop().create_future()
        await self.api.verify_pin(self.product_type, self.serial_no, code)
        await asyncio.wait_for(self.pin_verified_future, timeout=5)
        event = self.pin_verified_future.result()
        if event.data[MessageField.SUCCESSFULL.value] is False:
            return False
        await self.api.unlock(self.product_type, self.serial_no)
        return True

    async def process_event(self, event: Event):
        """Act on received event"""
        handler_func = None

        try:
            handler = EventNameToHandler(event.type)
            handler_func = getattr(self, f"_handle_{handler.name}", None)
        except ValueError:
            # event is not acted on, skip it
            _LOGGER.debug(f"event not handled -{self.serial_no} - {event}")
            return

        if handler_func is not None:
            await handler_func(event)

        if self.state_update_listener is not None:
            callback_func = self.state_update_listener
            callback_func()

    def _sync_property_to_paired(self, name: str, value: Any) -> None:
        """Standalone locks share a serial on device + station; keep both in sync."""
        if name not in (MessageField.LOCKED.value, MessageField.LOCK_STATUS.value):
            return
        if self.product_type == ProductType.device:
            other = self.api.stations.get(self.serial_no)
        else:
            other = self.api.devices.get(self.serial_no)
        if other is not None and other is not self:
            other.properties[name] = value

    def _lock_state_from_property(self, name: str, value: Any) -> Optional[bool]:
        if name == MessageField.LOCKED.value:
            return bool(value)
        if name == MessageField.LOCK_STATUS.value:
            return self._lock_status_to_bool(value)
        return None

    def _apply_lock_properties(self, locked: bool) -> None:
        self.properties[MessageField.LOCKED.value] = locked
        self.properties[MessageField.LOCK_STATUS.value] = 4 if locked else 3
        self._sync_property_to_paired(MessageField.LOCKED.value, locked)
        self._sync_property_to_paired(
            MessageField.LOCK_STATUS.value, self.properties[MessageField.LOCK_STATUS.value]
        )

    async def _handle_property_changed(self, event: Event):
        name = event.data[MessageField.NAME.value]
        value = event.data[MessageField.VALUE.value]

        if name in (MessageField.LOCKED.value, MessageField.LOCK_STATUS.value):
            reported = self._lock_state_from_property(name, value)
            if (
                self._lock_pending_target is not None
                and reported is not None
                and reported != self._lock_pending_target
            ):
                _LOGGER.debug(
                    "Ignoring stale lock property %s=%s while pending %s (%s)",
                    name,
                    value,
                    self._lock_pending_target,
                    self.serial_no,
                )
                return

        if name in (MessageField.LOCKED.value, MessageField.LOCK_STATUS.value):
            if name == MessageField.LOCK_STATUS.value:
                locked = self._lock_status_to_bool(value)
                if locked is not None:
                    self._apply_lock_properties(locked)
            else:
                self._apply_lock_properties(bool(value))
            return

        self.properties[name] = value
        self._sync_property_to_paired(name, value)

    async def _handle_pin_verified(self, event: Event):
        self.pin_verified_future.set_result(event)

    async def _handle_connected(self, event: Event):
        self.properties[MessageField.CONNECTED.value] = True

    async def _handle_disconnected(self, event: Event):
        self.properties[MessageField.CONNECTED.value] = False

    async def _handle_connection_error(self, event: Event):
        self.properties[MessageField.CONNECTED.value] = False

    @property
    def is_camera(self):
        """checks if Product is camera"""
        return True if ProductCommand.start_livestream.value.command in self.commands else False

    @property
    def is_safe_lock(self):
        """checks if Product is safe lock"""
        return True if ProductCommand.verify_pin.value.command in self.commands else False

    def has(self, property_name: str) -> bool:
        """Checks if product has required property"""
        return False if self.properties.get(property_name, None) is None else True

    def _paired_device(self) -> Optional["Device"]:
        """Standalone locks use the same serial for station and device."""
        device = self.api.devices.get(self.serial_no)
        if device is not None and device is not self:
            return device
        return None

    def supports_lock_entity(self) -> bool:
        """Whether this product should expose a Home Assistant lock entity."""
        locked_meta = self.metadata.get(MessageField.LOCKED.value)
        if locked_meta is not None and locked_meta.writeable:
            return self.has(MessageField.LOCKED.value) or self.has(MessageField.LOCK_STATUS.value)
        paired = self._paired_device()
        if paired is not None:
            return paired.supports_lock_entity()
        return False

    def get_lock_metadata(self) -> Optional[Metadata]:
        """Writable metadata used for lock/unlock commands (always ``locked`` when present)."""
        locked_meta = self.metadata.get(MessageField.LOCKED.value)
        if locked_meta is not None and locked_meta.writeable:
            return locked_meta
        paired = self._paired_device()
        if paired is not None:
            return paired.get_lock_metadata()
        return locked_meta

    @staticmethod
    def _lock_status_to_bool(lock_status: Any) -> Optional[bool]:
        """Eufy MQTT lockStatus: 4=locked, 3=unlocked."""
        if lock_status is None:
            return None
        try:
            status = int(lock_status)
        except (TypeError, ValueError):
            return None
        if status == 4:
            return True
        if status == 3:
            return False
        return None

    def lock_state_matches(self, target: bool) -> bool:
        """True if either ``locked`` or ``lockStatus`` reflects the target (MQTT may update one first)."""
        locked = self.properties.get(MessageField.LOCKED.value)
        if locked is not None and bool(locked) == target:
            return True
        lock_status = self._lock_status_to_bool(self.properties.get(MessageField.LOCK_STATUS.value))
        return lock_status is not None and lock_status == target

    def get_lock_state(self) -> Optional[bool]:
        """Return lock state; when properties disagree, trust ``locked`` (MQTT) over lagging lockStatus."""
        locked_val = self.properties.get(MessageField.LOCKED.value)
        status_val = self._lock_status_to_bool(self.properties.get(MessageField.LOCK_STATUS.value))
        if locked_val is not None and status_val is not None:
            if bool(locked_val) != status_val:
                return bool(locked_val)
            return status_val
        if status_val is not None:
            return status_val
        if locked_val is not None:
            return bool(locked_val)
        paired = self._paired_device()
        if paired is not None:
            return paired.get_lock_state()
        return None


class Device(Product):
    """Device as Physical Product"""

    def __init__(self, api, serial_no: str, properties: dict, metadata: dict, commands: []) -> None:
        super().__init__(api, ProductType.device, serial_no, properties, metadata, commands)


class Station(Product):
    """Station as Physical Product"""

    def __init__(self, api, serial_no: str, properties: dict, metadata: dict, commands: []) -> None:
        super().__init__(api, ProductType.station, serial_no, properties, metadata, commands)

    async def chime(self, ringtone: int) -> None:
        """Quick response message to camera"""
        await self.api.chime(self.product_type, self.serial_no, ringtone)

    async def reboot(self) -> None:
        """Reboot station"""
        await self.api.reboot(self.product_type, self.serial_no)
