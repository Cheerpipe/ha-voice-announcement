"""Base entity for Voice Announcement."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .activity import VoiceAnnouncementActivity
from .const import DATA_VERSION, DOMAIN, NAME, SIGNAL_ACTIVITY_UPDATED


class VoiceAnnouncementEntity(Entity):
    """An entity that refreshes whenever the integration's activity changes."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, activity: VoiceAnnouncementActivity, key: str) -> None:
        """Initialize the entity."""
        self._activity = activity
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            entry_type=DeviceEntryType.SERVICE,
            sw_version=activity.hass.data[DOMAIN].get(DATA_VERSION),
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to activity updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_ACTIVITY_UPDATED, self.async_write_ha_state)
        )
