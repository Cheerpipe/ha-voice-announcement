"""Binary sensors for Voice Announcement."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import slugify

from .activity import VoiceAnnouncementActivity
from .const import (
    DATA_ACTIVITY,
    DOMAIN,
    PHASE_PLAYING,
    PHASE_PROCESSING,
    PHASE_RECEIVING,
    SIGNAL_SPEAKER_ADDED,
)
from .entity import VoiceAnnouncementEntity


@dataclass(frozen=True, kw_only=True)
class VoiceAnnouncementBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Voice Announcement binary sensor."""

    is_on_fn: Callable[[VoiceAnnouncementActivity], bool]
    attrs_fn: Callable[[VoiceAnnouncementActivity], dict[str, Any] | None] = lambda _a: None


def _phase_attrs(phase: str) -> Callable[[VoiceAnnouncementActivity], dict[str, Any]]:
    def _attrs(activity: VoiceAnnouncementActivity) -> dict[str, Any]:
        jobs = activity.jobs_in(phase)
        return {
            "targets": sorted({target for job in jobs for target in job.targets}),
            "jobs": [job.as_dict() for job in jobs],
        }

    return _attrs


BINARY_SENSORS: tuple[VoiceAnnouncementBinarySensorDescription, ...] = (
    VoiceAnnouncementBinarySensorDescription(
        key="receiving",
        translation_key="receiving",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda activity: bool(activity.jobs_in(PHASE_RECEIVING)),
        attrs_fn=_phase_attrs(PHASE_RECEIVING),
    ),
    VoiceAnnouncementBinarySensorDescription(
        key="processing",
        translation_key="processing",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda activity: bool(activity.jobs_in(PHASE_PROCESSING)),
        attrs_fn=_phase_attrs(PHASE_PROCESSING),
    ),
    VoiceAnnouncementBinarySensorDescription(
        key="playing",
        translation_key="playing",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda activity: bool(activity.jobs_in(PHASE_PLAYING)),
        attrs_fn=_phase_attrs(PHASE_PLAYING),
    ),
    VoiceAnnouncementBinarySensorDescription(
        key="ffmpeg",
        translation_key="ffmpeg",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda activity: activity.ffmpeg_path is None,
        attrs_fn=lambda activity: {"path": activity.ffmpeg_path},
    ),
    VoiceAnnouncementBinarySensorDescription(
        key="ffprobe",
        translation_key="ffprobe",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda activity: activity.ffprobe_path is None,
        attrs_fn=lambda activity: {"path": activity.ffprobe_path},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Voice Announcement binary sensors."""
    activity: VoiceAnnouncementActivity = hass.data[DOMAIN][DATA_ACTIVITY]
    entities: list[BinarySensorEntity] = [
        VoiceAnnouncementBinarySensor(entry, activity, description)
        for description in BINARY_SENSORS
    ]
    entities.extend(
        SpeakerPlayingBinarySensor(entry, activity, speaker) for speaker in activity.store.speakers
    )
    async_add_entities(entities)

    @callback
    def _add_speakers(speakers: list[str]) -> None:
        async_add_entities(
            SpeakerPlayingBinarySensor(entry, activity, speaker) for speaker in speakers
        )

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_SPEAKER_ADDED, _add_speakers))


class VoiceAnnouncementBinarySensor(VoiceAnnouncementEntity, BinarySensorEntity):
    """A binary sensor computed from the activity tracker."""

    entity_description: VoiceAnnouncementBinarySensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        activity: VoiceAnnouncementActivity,
        description: VoiceAnnouncementBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(entry, activity, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return the sensor state."""
        return self.entity_description.is_on_fn(self._activity)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra details."""
        return self.entity_description.attrs_fn(self._activity)


class SpeakerPlayingBinarySensor(VoiceAnnouncementEntity, BinarySensorEntity):
    """On while an announcement plays on one media player."""

    _attr_translation_key = "speaker_playing"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self, entry: ConfigEntry, activity: VoiceAnnouncementActivity, speaker: str
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(entry, activity, f"playing_{slugify(speaker)}")
        self._speaker = speaker
        self._attr_translation_placeholders = {"speaker": _speaker_name(activity.hass, speaker)}

    @property
    def is_on(self) -> bool:
        """Return whether an announcement is playing on the speaker."""
        return self._activity.target_job(self._speaker) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the announcement playing on the speaker."""
        job = self._activity.target_job(self._speaker)
        return {
            "media_player": self._speaker,
            "announcement_id": job.id if job else None,
            "type": job.type if job else None,
            "recording_id": job.recording_id if job else None,
            "started_at": job.started_at.isoformat() if job else None,
            "expected_end": job.expected_end.isoformat() if job and job.expected_end else None,
        }


def _speaker_name(hass: HomeAssistant, entity_id: str) -> str:
    """Return a readable name for a media player, even before it has loaded."""
    if (state := hass.states.get(entity_id)) is not None and state.name:
        return state.name
    if (entry := er.async_get(hass).async_get(entity_id)) is not None and (
        name := entry.name or entry.original_name
    ):
        return name
    return entity_id.split(".", 1)[-1].replace("_", " ").capitalize()
