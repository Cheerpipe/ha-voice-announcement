"""Media source platform for Voice Announcement."""

from __future__ import annotations

import logging

from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DATA_STORE, DOMAIN, MEDIA_BROWSE_LIMIT, MEDIA_URL_BASE
from .storage import VoiceAnnouncementStore

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Set up the Voice Announcement media source."""
    _LOGGER.debug("Creating Voice Announcement media source")
    return VoiceAnnouncementMediaSource(hass)


class VoiceAnnouncementMediaSource(MediaSource):
    """Expose generated announcements as media source items."""

    name = "Voice Announcement"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the media source."""
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a recording to a playable URL."""
        store = self._get_store()
        recording_id = item.identifier
        metadata = None if store is None or not recording_id else store.get(recording_id)
        media_file = (
            None if store is None or not recording_id else store.get_media_file(recording_id)
        )
        if media_file is None:
            _LOGGER.debug(
                "Voice Announcement media resolve failed because recording was not found "
                "(recording_id=%s)",
                recording_id,
            )
            raise Unresolvable("Recording not found")

        media_extension = "mp3"
        media_mime_type = "audio/mpeg"
        if isinstance(metadata, dict):
            media_extension = str(
                metadata.get("media_extension") or media_file.suffix.lstrip(".") or "mp3"
            )
            media_mime_type = str(metadata.get("media_mime_type") or "audio/mpeg")

        _LOGGER.debug(
            "Resolved Voice Announcement media item (recording_id=%s, mime_type=%s, extension=%s)",
            recording_id,
            media_mime_type,
            media_extension,
        )

        return PlayMedia(
            f"{MEDIA_URL_BASE}/{recording_id}.{media_extension}",
            media_mime_type,
            path=media_file,
        )

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Return a browsable list of recordings."""
        store = self._get_store()
        children: list[BrowseMediaSource] = []

        if store is not None:
            for recording_id, metadata in sorted(
                store.recordings.items(),
                key=lambda entry: entry[1].get("created_at", ""),
                reverse=True,
            )[:MEDIA_BROWSE_LIMIT]:
                if store.get_media_file(recording_id) is None:
                    continue

                created_at = dt_util.parse_datetime(str(metadata.get("created_at", "")))
                label = (
                    dt_util.as_local(created_at).strftime("%Y-%m-%d %H:%M:%S")
                    if created_at
                    else recording_id
                )
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=recording_id,
                        media_class=MediaClass.MUSIC,
                        media_content_type=MediaType.MUSIC,
                        title=label,
                        can_play=True,
                        can_expand=False,
                    )
                )

        _LOGGER.debug(
            "Browsed Voice Announcement media source (children=%s, limit=%s)",
            len(children),
            MEDIA_BROWSE_LIMIT,
        )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=self.name,
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _get_store(self) -> VoiceAnnouncementStore | None:
        return self.hass.data.get(DOMAIN, {}).get(DATA_STORE)
