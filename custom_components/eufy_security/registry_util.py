"""Entity registry helpers for eufy_security."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__package__)

# Unique-id fragments for entities users expect enabled (lock, commands, debug).
_CONTROL_UNIQUE_PARTS = (
    "_debug",
    "trigger_alarm",
    "reset_alarm",
    "reboot",
    "locked",
    "lockStatus",
)

_CONTROL_PLATFORMS = frozenset({"lock", "button"})


async def async_disable_unsupported_buttons(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Disable button entities the add-on does not advertise (avoids 'not supported' presses)."""
    from .const import COORDINATOR, DOMAIN
    from .eufy_security_api.const import ProductCommand

    coordinator = hass.data.get(DOMAIN, {}).get(COORDINATOR)
    if coordinator is None:
        return

    unsupported_uids: set[str] = set()
    for product in list(coordinator.devices.values()) + list(coordinator.stations.values()):
        for command in ProductCommand:
            remote_cmd = command.value.command
            if remote_cmd is not None:
                if remote_cmd == "is_rtsp_enabled":
                    supported = product.is_rtsp_enabled
                else:
                    supported = remote_cmd in product.commands
            else:
                supported = command.name in product.commands
            if not supported:
                unsupported_uids.add(
                    f"eufy_security_{product.serial_no}_{product.product_type.value}_{command.name}"
                )

    registry = er.async_get(hass)
    disabled: list[str] = []
    for entity_entry in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entity_entry.platform != "button":
            continue
        if entity_entry.unique_id not in unsupported_uids:
            continue
        if entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
            continue
        registry.async_update_entity(
            entity_entry.entity_id,
            disabled_by=er.RegistryEntryDisabler.INTEGRATION,
        )
        disabled.append(entity_entry.entity_id)

    if disabled:
        _LOGGER.info("Disabled %d unsupported eufy_security button entities", len(disabled))


async def async_enable_preferred_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    *,
    include_user_disabled: bool = False,
) -> None:
    """Clear disabled_by for lock/button/debug and integration-disabled entities."""
    registry = er.async_get(hass)
    enabled: list[str] = []

    for entity_entry in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entity_entry.disabled_by is None:
            continue

        unique_id = entity_entry.unique_id or ""
        is_control = (
            entity_entry.platform in _CONTROL_PLATFORMS
            or any(part in unique_id for part in _CONTROL_UNIQUE_PARTS)
        )

        if entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
            pass
        elif include_user_disabled and is_control:
            pass
        else:
            continue

        registry.async_update_entity(entity_entry.entity_id, disabled_by=None)
        enabled.append(entity_entry.entity_id)

    if enabled:
        _LOGGER.info(
            "Enabled %d eufy_security entities (include_user_disabled=%s)",
            len(enabled),
            include_user_disabled,
        )
