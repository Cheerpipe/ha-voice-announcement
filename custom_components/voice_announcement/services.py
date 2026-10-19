"""Services for Voice Announcement."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import quote

from homeassistant.components.media_player import (
    ATTR_MEDIA_ANNOUNCE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaPlayerEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.target import TargetSelection, async_extract_referenced_entity_ids
import voluptuous as vol

from .activity import VoiceAnnouncementActivity
from .const import (
    AUTO_CLEANUP_KEEP_DAYS,
    DATA_ACTIVITY,
    DATA_STORE,
    DOMAIN,
    MAX_MESSAGE_LENGTH,
    MAX_TARGET_ENTITIES,
    MEDIA_SOURCE_URI_PREFIX,
    TTS_CHARS_PER_SECOND,
    TYPE_TTS,
    TYPE_VOICE,
)
from .storage import VoiceAnnouncementStore

SERVICE_CLEANUP = "cleanup"
SERVICE_DELETE_RECORDING = "delete_recording"
SERVICE_PLAY = "play"

ATTR_RECORDING_ID = "recording_id"
ATTR_MESSAGE = "message"
ATTR_TTS_ENGINE = "tts_engine"
ATTR_LANGUAGE = "language"
ATTR_VOICE = "voice"
ATTR_CACHE = "cache"
LAST_RECORDING = "last"

PLAY_SCHEMA = vol.All(
    vol.Schema(
        {
            **cv.ENTITY_SERVICE_FIELDS,
            vol.Exclusive(ATTR_RECORDING_ID, "source"): cv.string,
            vol.Exclusive(ATTR_MESSAGE, "source"): vol.All(
                cv.string, vol.Length(min=1, max=MAX_MESSAGE_LENGTH)
            ),
            vol.Optional(ATTR_TTS_ENGINE): cv.entity_domain("tts"),
            vol.Optional(ATTR_LANGUAGE): cv.string,
            vol.Optional(ATTR_VOICE): cv.string,
            vol.Optional(ATTR_CACHE, default=True): cv.boolean,
            vol.Optional(ATTR_MEDIA_ANNOUNCE, default=True): cv.boolean,
        }
    ),
    cv.has_at_least_one_key(ATTR_RECORDING_ID, ATTR_MESSAGE),
)

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

    async def async_play(call: ServiceCall) -> ServiceResponse:
        return await _async_play(hass, store, hass.data[DOMAIN][DATA_ACTIVITY], call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY,
        async_play,
        schema=PLAY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
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
    hass.services.async_remove(DOMAIN, SERVICE_PLAY)
    _LOGGER.debug("Unregistered Voice Announcement admin services")


async def _async_play(
    hass: HomeAssistant,
    store: VoiceAnnouncementStore,
    activity: VoiceAnnouncementActivity,
    call: ServiceCall,
) -> ServiceResponse:
    """Play a stored recording or a text-to-speech message on media players."""
    targets = _resolve_targets(hass, call)
    user = await hass.auth.async_get_user(call.context.user_id) if call.context.user_id else None

    if ATTR_MESSAGE in call.data:
        engine = call.data.get(ATTR_TTS_ENGINE)
        if not engine:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="tts_engine_required"
            )
        message: str | None = call.data[ATTR_MESSAGE].strip()
        recording_id = None
        announcement_type = TYPE_TTS
        media_content_id = _tts_media_id(
            engine,
            message,
            language=call.data.get(ATTR_LANGUAGE),
            voice=call.data.get(ATTR_VOICE),
            cache=call.data[ATTR_CACHE],
        )
        duration = len(message) / TTS_CHARS_PER_SECOND
    else:
        message = None
        announcement_type = TYPE_VOICE
        requested = call.data[ATTR_RECORDING_ID]
        recording = (
            store.latest_recording() if requested == LAST_RECORDING else store.get(requested)
        )
        if recording is None or store.get_media_file(str(recording.get("id"))) is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="recording_not_found",
                translation_placeholders={"recording_id": requested},
            )
        recording_id = str(recording["id"])
        media_content_id = f"{MEDIA_SOURCE_URI_PREFIX}/{recording_id}"
        duration = float(recording.get("duration") or 0)

    await activity.async_register_speakers(targets)
    job = activity.async_playback_started(
        announcement_type=announcement_type,
        targets=targets,
        duration=duration,
        user=user,
        recording_id=recording_id,
        message=message,
    )

    async def _play_on(target: str) -> None:
        state = hass.states.get(target)
        features = int(state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)) if state else 0
        data: dict[str, Any] = {
            ATTR_ENTITY_ID: target,
            ATTR_MEDIA_CONTENT_ID: media_content_id,
            ATTR_MEDIA_CONTENT_TYPE: "music",
        }
        # Announce mode is only requested where the speaker supports it.
        if call.data[ATTR_MEDIA_ANNOUNCE] and features & MediaPlayerEntityFeature.MEDIA_ANNOUNCE:
            data[ATTR_MEDIA_ANNOUNCE] = True
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, data, blocking=True, context=call.context
        )

    results = await asyncio.gather(
        *(_play_on(target) for target in targets), return_exceptions=True
    )
    failures = {
        target: str(result) or type(result).__name__
        for target, result in zip(targets, results, strict=True)
        if isinstance(result, BaseException)
    }
    activity.async_playback_dispatched(job, failures)
    for target, error in failures.items():
        _LOGGER.warning(
            "Voice Announcement could not play on a speaker (target=%s, type=%s, error=%s)",
            target,
            announcement_type,
            error,
        )
    if failures:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="playback_failed",
            translation_placeholders={
                "targets": ", ".join(failures),
                "error": next(iter(failures.values())),
            },
        )
    return {
        "announcement_id": job.id,
        "type": announcement_type,
        "targets": targets,
        "recording_id": recording_id,
        "media_content_id": media_content_id,
        "duration": duration,
    }


def _resolve_targets(hass: HomeAssistant, call: ServiceCall) -> list[str]:
    """Expand entity, device, area, floor and label targets into media players."""
    selected = async_extract_referenced_entity_ids(hass, TargetSelection(call.data))
    targets = sorted(
        entity_id
        for entity_id in selected.referenced | selected.indirectly_referenced
        if entity_id.startswith(f"{MEDIA_PLAYER_DOMAIN}.")
    )
    if not targets:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_targets")
    if len(targets) > MAX_TARGET_ENTITIES:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="too_many_targets",
            translation_placeholders={"max": str(MAX_TARGET_ENTITIES)},
        )
    return targets


def _tts_media_id(
    engine: str, message: str, *, language: str | None, voice: str | None, cache: bool
) -> str:
    """Build the same text-to-speech media source id the card uses."""
    params = [("message", message), ("cache", "true" if cache else "false")]
    if language:
        params.append(("language", language))
    if voice:
        params.append(("tts_options", json.dumps({"voice": voice}, separators=(",", ":"))))
    query = "&".join(f"{key}={quote(value, safe='')}" for key, value in params)
    return f"media-source://tts/{engine}?{query}"
