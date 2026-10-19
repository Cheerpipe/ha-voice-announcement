"""Diagnostics for Voice Announcement."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_STORE, DOMAIN
from .storage import VoiceAnnouncementStore


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    store: VoiceAnnouncementStore = hass.data[DOMAIN][DATA_STORE]
    return {
        "recordings": len(store.recordings),
        "entry_id": entry.entry_id,
    }
