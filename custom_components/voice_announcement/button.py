"""Buttons for Voice Announcement."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .activity import VoiceAnnouncementActivity
from .const import AUTO_CLEANUP_KEEP_DAYS, DATA_ACTIVITY, DOMAIN
from .entity import VoiceAnnouncementEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Voice Announcement buttons."""
    activity: VoiceAnnouncementActivity = hass.data[DOMAIN][DATA_ACTIVITY]
    async_add_entities(
        [
            CleanupButton(entry, activity, "cleanup"),
            DeleteLastButton(entry, activity, "delete_last"),
        ]
    )


class CleanupButton(VoiceAnnouncementEntity, ButtonEntity):
    """Delete recordings older than the default retention period."""

    _attr_translation_key = "cleanup"
    _attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        """Run the cleanup."""
        await self._activity.store.async_cleanup(AUTO_CLEANUP_KEEP_DAYS, trigger="button")


class DeleteLastButton(VoiceAnnouncementEntity, ButtonEntity):
    """Delete the most recent recording."""

    _attr_translation_key = "delete_last"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        """Return whether there is a recording to delete."""
        return bool(self._activity.store.recordings)

    async def async_press(self) -> None:
        """Delete the latest recording."""
        if (recording := self._activity.store.latest_recording()) is not None:
            await self._activity.store.async_delete_recording(
                str(recording.get("id")), reason="button"
            )
