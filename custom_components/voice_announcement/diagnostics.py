"""Diagnostics for Voice Announcement."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .activity import VoiceAnnouncementActivity
from .const import (
    AUTO_CLEANUP_KEEP_DAYS,
    DATA_ACTIVITY,
    DATA_STORE,
    DATA_VERSION,
    DEFAULT_MAX_DURATION,
    DOMAIN,
    MAX_CONCURRENT_UPLOADS,
    MAX_STORED_RECORDINGS,
    MAX_UPLOAD_BYTES,
    MAX_UPLOADS_PER_WINDOW,
    UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
)
from .storage import VoiceAnnouncementStore


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    store: VoiceAnnouncementStore = hass.data[DOMAIN][DATA_STORE]
    activity: VoiceAnnouncementActivity = hass.data[DOMAIN][DATA_ACTIVITY]
    oldest = store.oldest_recording()
    latest = store.latest_recording()
    return {
        "entry_id": entry.entry_id,
        "version": hass.data[DOMAIN].get(DATA_VERSION),
        "recordings": len(store.recordings),
        "oldest_recording_at": oldest.get("created_at") if oldest else None,
        "latest_recording_at": latest.get("created_at") if latest else None,
        "storage_bytes": activity.storage_bytes,
        "speakers": list(store.speakers),
        "tools": {"ffmpeg": activity.ffmpeg_path, "ffprobe": activity.ffprobe_path},
        "limits": {
            "max_upload_bytes": MAX_UPLOAD_BYTES,
            "max_duration_seconds": DEFAULT_MAX_DURATION,
            "max_concurrent_uploads": MAX_CONCURRENT_UPLOADS,
            "max_uploads_per_window": MAX_UPLOADS_PER_WINDOW,
            "rate_limit_window_seconds": UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
            "max_stored_recordings": MAX_STORED_RECORDINGS,
            "auto_cleanup_keep_days": AUTO_CLEANUP_KEEP_DAYS,
        },
        "activity": {
            "phase": activity.phase,
            "jobs": [_redact_job(job.as_dict()) for job in activity.jobs.values()],
        },
        "last_upload": _redact_user(activity.last_upload),
        "last_timings": activity.last_timings,
        "failed_uploads": activity.failed_uploads,
        "last_cleanup": activity.last_cleanup,
        "last_announcement": _redact_job(activity.last_announcement),
        "failed_playbacks": activity.failed_playbacks,
        "last_playback_error": activity.last_playback_error,
    }


def _redact_user(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return {key: value for key, value in data.items() if key not in ("user", "user_id")}


def _redact_job(data: dict[str, Any] | None) -> dict[str, Any] | None:
    # Messages are user content; diagnostics only say whether there was one.
    if (data := _redact_user(data)) is None:
        return None
    if "message" in data:
        data["message"] = "**REDACTED**"
    return data
