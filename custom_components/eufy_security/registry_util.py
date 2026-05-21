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
