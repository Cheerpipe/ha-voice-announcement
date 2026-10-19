"""Sensors for Voice Announcement."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .activity import VoiceAnnouncementActivity
from .const import (
    DATA_ACTIVITY,
    DOMAIN,
    MAX_CONCURRENT_UPLOADS,
    MAX_STORED_RECORDINGS,
    MEDIA_SOURCE_URI_PREFIX,
    MEDIA_URL_BASE,
    PHASE_PROCESSING,
    PHASE_RECEIVING,
    PHASES,
    UPLOAD_STATUSES,
)
from .entity import VoiceAnnouncementEntity


@dataclass(frozen=True, kw_only=True)
class VoiceAnnouncementSensorDescription(SensorEntityDescription):
    """Describe a Voice Announcement sensor."""

    value_fn: Callable[[VoiceAnnouncementActivity], Any]
    attrs_fn: Callable[[VoiceAnnouncementActivity], dict[str, Any] | None] = lambda _a: None


def _status_attrs(activity: VoiceAnnouncementActivity) -> dict[str, Any]:
    jobs = sorted(activity.jobs.values(), key=lambda job: job.started_at)
    current = next(iter(activity.jobs_in(activity.phase)), None)
    return {
        "targets": sorted({target for job in jobs for target in job.targets}),
        "type": current.type if current else None,
        "user": current.user_name if current else None,
        "recording_id": current.recording_id if current else None,
        "started_at": current.started_at.isoformat() if current else None,
        "active_jobs": [job.as_dict() for job in jobs],
    }


def _last_recording(activity: VoiceAnnouncementActivity) -> dict[str, Any] | None:
    return activity.store.latest_recording()


def _last_recording_attrs(activity: VoiceAnnouncementActivity) -> dict[str, Any] | None:
    if (recording := _last_recording(activity)) is None:
        return None
    recording_id = recording.get("id")
    return {
        "recording_id": recording_id,
        "media_source_id": f"{MEDIA_SOURCE_URI_PREFIX}/{recording_id}",
        "url": f"{MEDIA_URL_BASE}/{recording_id}.{recording.get('media_extension')}",
        "targets": [t for t in str(recording.get("entity_id") or "").split(",") if t],
        "uploaded_by": recording.get("uploaded_by"),
        "user": recording.get("uploaded_by_name"),
        "duration": recording.get("duration"),
        "was_transcoded": recording.get("was_transcoded"),
    }


def _recording_time(recording: dict[str, Any] | None) -> datetime | None:
    if recording is None:
        return None
    return dt_util.parse_datetime(str(recording.get("created_at") or ""))


def _parse_time(data: dict[str, Any] | None, key: str) -> datetime | None:
    if not data or not data.get(key):
        return None
    return dt_util.parse_datetime(str(data[key]))


def _recordings_today(activity: VoiceAnnouncementActivity) -> int:
    today = dt_util.now().date()
    return sum(
        1
        for recording in activity.store.recordings.values()
        if (created := _recording_time(recording)) is not None
        and dt_util.as_local(created).date() == today
    )


def _transcoded_ratio(activity: VoiceAnnouncementActivity) -> float | None:
    recordings = activity.store.recordings.values()
    if not recordings:
        return None
    transcoded = sum(1 for recording in recordings if recording.get("was_transcoded"))
    return round(transcoded * 100 / len(recordings), 1)


def _active_uploads(activity: VoiceAnnouncementActivity) -> int:
    return len(activity.jobs_in(PHASE_RECEIVING)) + len(activity.jobs_in(PHASE_PROCESSING))


SENSORS: tuple[VoiceAnnouncementSensorDescription, ...] = (
    VoiceAnnouncementSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=list(reversed(PHASES)),
        value_fn=lambda activity: activity.phase,
        attrs_fn=_status_attrs,
    ),
    VoiceAnnouncementSensorDescription(
        key="last_recording",
        translation_key="last_recording",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda activity: _recording_time(_last_recording(activity)),
        attrs_fn=_last_recording_attrs,
    ),
    VoiceAnnouncementSensorDescription(
        key="last_duration",
        translation_key="last_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_display_precision=1,
        value_fn=lambda activity: (_last_recording(activity) or {}).get("duration"),
    ),
    VoiceAnnouncementSensorDescription(
        key="last_announcement",
        translation_key="last_announcement",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda activity: _parse_time(activity.last_announcement, "started_at"),
        attrs_fn=lambda activity: activity.last_announcement,
    ),
    VoiceAnnouncementSensorDescription(
        key="stored_recordings",
        translation_key="stored_recordings",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda activity: len(activity.store.recordings),
        attrs_fn=lambda _activity: {"max": MAX_STORED_RECORDINGS},
    ),
    VoiceAnnouncementSensorDescription(
        key="storage_used",
        translation_key="storage_used",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        suggested_display_precision=2,
        value_fn=lambda activity: activity.storage_bytes,
    ),
    VoiceAnnouncementSensorDescription(
        key="oldest_recording",
        translation_key="oldest_recording",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda activity: _recording_time(activity.store.oldest_recording()),
    ),
    VoiceAnnouncementSensorDescription(
        key="last_upload_status",
        translation_key="last_upload_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=list(UPLOAD_STATUSES),
        value_fn=lambda activity: (activity.last_upload or {}).get("status"),
        attrs_fn=lambda activity: activity.last_upload,
    ),
    VoiceAnnouncementSensorDescription(
        key="failed_uploads",
        translation_key="failed_uploads",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda activity: activity.failed_uploads,
    ),
    VoiceAnnouncementSensorDescription(
        key="last_processing_time",
        translation_key="last_processing_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        value_fn=lambda activity: (activity.last_timings or {}).get("total_ms"),
        attrs_fn=lambda activity: activity.last_timings,
    ),
    VoiceAnnouncementSensorDescription(
        key="transcoded_ratio",
        translation_key="transcoded_ratio",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_transcoded_ratio,
    ),
    VoiceAnnouncementSensorDescription(
        key="active_uploads",
        translation_key="active_uploads",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_active_uploads,
        attrs_fn=lambda _activity: {"max": MAX_CONCURRENT_UPLOADS},
    ),
    VoiceAnnouncementSensorDescription(
        key="last_cleanup",
        translation_key="last_cleanup",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda activity: _parse_time(activity.last_cleanup, "at"),
        attrs_fn=lambda activity: activity.last_cleanup,
    ),
    VoiceAnnouncementSensorDescription(
        key="failed_playbacks",
        translation_key="failed_playbacks",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda activity: activity.failed_playbacks,
        attrs_fn=lambda activity: activity.last_playback_error,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Voice Announcement sensors."""
    activity: VoiceAnnouncementActivity = hass.data[DOMAIN][DATA_ACTIVITY]
    entities: list[SensorEntity] = [
        VoiceAnnouncementSensor(entry, activity, description) for description in SENSORS
    ]
    entities.append(RecordingsTodaySensor(entry, activity))
    async_add_entities(entities)


class VoiceAnnouncementSensor(VoiceAnnouncementEntity, SensorEntity):
    """A sensor computed from the activity tracker."""

    entity_description: VoiceAnnouncementSensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        activity: VoiceAnnouncementActivity,
        description: VoiceAnnouncementSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(entry, activity, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self._activity)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra details."""
        return self.entity_description.attrs_fn(self._activity)


class RecordingsTodaySensor(VoiceAnnouncementEntity, SensorEntity):
    """Count the recordings made since local midnight."""

    _attr_translation_key = "recordings_today"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, entry: ConfigEntry, activity: VoiceAnnouncementActivity) -> None:
        """Initialize the sensor."""
        super().__init__(entry, activity, "recordings_today")

    async def async_added_to_hass(self) -> None:
        """Refresh at midnight so the count starts over."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(self.hass, self._midnight, hour=0, minute=0, second=0)
        )

    @callback
    def _midnight(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        """Return today's recordings."""
        return _recordings_today(self._activity)

    @property
    def last_reset(self) -> datetime:
        """Return local midnight."""
        return dt_util.start_of_local_day()
