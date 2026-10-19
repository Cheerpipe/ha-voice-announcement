"""Services for Voice Announcement."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.service import async_register_admin_service
import voluptuous as vol

from .const import AUTO_CLEANUP_KEEP_DAYS, DATA_STORE, DOMAIN
from .storage import VoiceAnnouncementStore

SERVICE_CLEANUP = "cleanup"
SERVICE_DELETE_RECORDING = "delete_recording"

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    store: VoiceAnnouncementStore = hass.data[DOMAIN][DATA_STORE]
    _LOGGER.debug("Registering Voice Announcement admin services")

    async def async_cleanup(call: ServiceCall) -> None:
        keep_days = call.data["keep_days"]
        deleted = await store.async_cleanup(keep_days, trigger="service_call")
        _LOGGER.info(
            "Voice Announcement cleanup service completed (deleted=%s, keep_days=%s, user_id=%s)",
            deleted,
            keep_days,
            getattr(call.context, "user_id", None),
        )

    async def async_delete_recording(call: ServiceCall) -> None:
        recording_id = call.data["recording_id"]
        deleted = await store.async_delete_recording(
            recording_id,
            reason="service_call",
        )
        level = logging.INFO if deleted else logging.WARNING
        _LOGGER.log(
            level,
            "Voice Announcement delete_recording service completed "
            "(recording_id=%s, deleted=%s, user_id=%s)",
            recording_id,
            deleted,
            getattr(call.context, "user_id", None),
        )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_CLEANUP,
        async_cleanup,
        schema=vol.Schema(
            {vol.Optional("keep_days", default=AUTO_CLEANUP_KEEP_DAYS): cv.positive_int}
        ),
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_RECORDING,
        async_delete_recording,
        schema=vol.Schema({vol.Required("recording_id"): cv.string}),
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister integration services."""
    hass.services.async_remove(DOMAIN, SERVICE_CLEANUP)
    hass.services.async_remove(DOMAIN, SERVICE_DELETE_RECORDING)
    _LOGGER.debug("Unregistered Voice Announcement admin services")
