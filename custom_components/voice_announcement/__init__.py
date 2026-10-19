"""Voice Announcement integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    AUTO_CLEANUP_KEEP_DAYS,
    DATA_HTTP_REGISTERED,
    DATA_INITIALIZED,
    DATA_STORE,
    DATA_UPLOAD_RATE_LIMIT,
    DATA_UPLOAD_SEMAPHORE,
    DOMAIN,
    MAX_CONCURRENT_UPLOADS,
    MAX_STORED_RECORDINGS,
    MAX_UPLOAD_BYTES,
)
from .ffmpeg import async_assert_ffmpeg_available, async_assert_ffprobe_available
from .frontend import async_register_frontend, async_unregister_frontend
from .services import async_setup_services, async_unload_services
from .storage import VoiceAnnouncementStore
from .upload import VoiceAnnouncementMediaView, VoiceAnnouncementUploadView

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Voice Announcement from a config entry."""
    await _async_setup_once(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Voice Announcement integration")
    await async_unload_services(hass)
    await async_unregister_frontend(hass)
    hass.data.get(DOMAIN, {}).pop(DATA_INITIALIZED, None)
    _LOGGER.info("Voice Announcement integration unloaded")
    return True


async def _async_setup_once(hass: HomeAssistant) -> None:
    """Initialize global integration resources once."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_INITIALIZED):
        _LOGGER.debug("Voice Announcement integration already initialized")
        return

    _LOGGER.info(
        "Initializing Voice Announcement integration (max_upload_bytes=%s, "
        "max_concurrent_uploads=%s, auto_cleanup_keep_days=%s, max_recordings=%s)",
        MAX_UPLOAD_BYTES,
        MAX_CONCURRENT_UPLOADS,
        AUTO_CLEANUP_KEEP_DAYS,
        MAX_STORED_RECORDINGS,
    )

    try:
        await async_assert_ffmpeg_available()
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "ffmpeg is not available; uploads that need conversion will fail "
            "until ffmpeg is installed: %s",
            err,
        )
    try:
        await async_assert_ffprobe_available()
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "ffprobe is not available; uploads cannot be validated until ffprobe is installed: %s",
            err,
        )

    store = VoiceAnnouncementStore(hass)
    await store.async_load()
    domain_data[DATA_STORE] = store
    domain_data[DATA_UPLOAD_SEMAPHORE] = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)
    domain_data[DATA_UPLOAD_RATE_LIMIT] = {}

    if not domain_data.get(DATA_HTTP_REGISTERED):
        hass.http.register_view(VoiceAnnouncementUploadView(hass))
        hass.http.register_view(VoiceAnnouncementMediaView(hass))
        domain_data[DATA_HTTP_REGISTERED] = True
    await async_register_frontend(hass)
    await async_setup_services(hass)

    domain_data[DATA_INITIALIZED] = True
    _LOGGER.info(
        "Voice Announcement integration initialized (recordings=%s, http_views_registered=%s)",
        len(store.recordings),
        bool(domain_data.get(DATA_HTTP_REGISTERED)),
    )
