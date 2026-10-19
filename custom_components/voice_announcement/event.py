"""Event entities for Voice Announcement."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .activity import (
    EVENT_CATEGORY_ANNOUNCEMENT,
    EVENT_CATEGORY_RECORDING,
    VoiceAnnouncementActivity,
)
from .const import DATA_ACTIVITY, DOMAIN, SIGNAL_EVENT
from .entity import VoiceAnnouncementEntity

EVENT_TYPES = {
    EVENT_CATEGORY_RECORDING: ["recorded", "deleted", "cleanup", "failed"],
    EVENT_CATEGORY_ANNOUNCEMENT: ["started", "finished", "failed"],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Voice Announcement event entities."""
    activity: VoiceAnnouncementActivity = hass.data[DOMAIN][DATA_ACTIVITY]
    async_add_entities(
        VoiceAnnouncementEvent(entry, activity, category) for category in EVENT_TYPES
    )


class VoiceAnnouncementEvent(VoiceAnnouncementEntity, EventEntity):
    """Fire an event entity for recordings or announcements."""

    def __init__(
        self, entry: ConfigEntry, activity: VoiceAnnouncementActivity, category: str
    ) -> None:
        """Initialize the event entity."""
        super().__init__(entry, activity, category)
        self._category = category
        self._attr_translation_key = category
        self._attr_event_types = EVENT_TYPES[category]

    async def async_added_to_hass(self) -> None:
        """Restore the last event and listen for new ones."""
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_EVENT, self._handle))

    @callback
    def _handle(self, category: str, event_type: str, data: dict[str, Any]) -> None:
        if category != self._category:
            return
        self._trigger_event(event_type, {k: v for k, v in data.items() if v is not None})
        self.async_write_ha_state()
