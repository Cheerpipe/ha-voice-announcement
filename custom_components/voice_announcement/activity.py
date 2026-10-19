"""Live activity and statistics for Voice Announcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any
from uuid import uuid4

from homeassistant.const import STATE_PLAYING
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import (
    EVENT_CLEANUP,
    EVENT_DELETED,
    EVENT_PLAYBACK_FAILED,
    EVENT_PLAYBACK_FINISHED,
    EVENT_PLAYBACK_STARTED,
    EVENT_PROCESSING_STARTED,
    EVENT_RECEIVING_STARTED,
    EVENT_RECORDED,
    EVENT_UPLOAD_FAILED,
    FFMPEG_CHECK_INTERVAL_SECONDS,
    MEDIA_SOURCE_URI_PREFIX,
    MEDIA_URL_BASE,
    PHASE_IDLE,
    PHASE_PLAYING,
    PHASE_PROCESSING,
    PHASE_RECEIVING,
    PHASES,
    PLAYBACK_GRACE_SECONDS,
    PLAYBACK_MAX_OVERRUN_SECONDS,
    SIGNAL_ACTIVITY_UPDATED,
    SIGNAL_EVENT,
    SIGNAL_SPEAKER_ADDED,
    TYPE_TTS,
    TYPE_VOICE,
)
from .ffmpeg import find_ffmpeg, find_ffprobe
from .storage import VoiceAnnouncementStore

_LOGGER = logging.getLogger(__name__)

EVENT_CATEGORY_RECORDING = "recording"
EVENT_CATEGORY_ANNOUNCEMENT = "announcement"


@dataclass
class ActivityJob:
    """An upload or an announcement that is in progress."""

    id: str
    phase: str
    type: str
    started_at: datetime
    targets: list[str] = field(default_factory=list)
    user_id: str | None = None
    user_name: str | None = None
    recording_id: str | None = None
    message: str | None = None
    duration: float | None = None
    expected_end: datetime | None = None
    playing_targets: set[str] = field(default_factory=set)
    failed_targets: dict[str, str] = field(default_factory=dict)
    seen_playing: set[str] = field(default_factory=set)
    unsubscribers: dict[str, CALLBACK_TYPE] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return the job as state attributes."""
        data: dict[str, Any] = {
            "id": self.id,
            "phase": self.phase,
            "type": self.type,
            "targets": list(self.targets),
            "started_at": self.started_at.isoformat(),
            "user": self.user_name,
            "recording_id": self.recording_id,
            "duration": None if self.duration is None else round(self.duration, 1),
        }
        if self.message is not None:
            data["message"] = self.message
        if self.phase == PHASE_PLAYING:
            data["playing_targets"] = sorted(self.playing_targets)
            data["expected_end"] = self.expected_end.isoformat() if self.expected_end else None
        return data


class VoiceAnnouncementActivity:
    """Track what the integration is doing right now and keep diagnostics counters."""

    def __init__(self, hass: HomeAssistant, store: VoiceAnnouncementStore) -> None:
        """Initialize the tracker."""
        self.hass = hass
        self.store = store
        self.jobs: dict[str, ActivityJob] = {}
        self.ffmpeg_path: str | None = None
        self.ffprobe_path: str | None = None
        self.storage_bytes: int | None = None
        self.last_upload: dict[str, Any] | None = None
        self.last_timings: dict[str, int] | None = None
        self.failed_uploads = 0
        self.last_cleanup: dict[str, Any] | None = None
        self.last_announcement: dict[str, Any] | None = None
        self.failed_playbacks = 0
        self.last_playback_error: dict[str, Any] | None = None
        # Media player -> id of the announcement currently playing on it.
        self._target_jobs: dict[str, str] = {}
        self._unsubscribers: list[CALLBACK_TYPE] = []

    async def async_start(self) -> None:
        """Start listening to the store and checking the ffmpeg tools."""
        self.check_tools()
        self._unsubscribers.append(self.store.async_add_listener(self._handle_store_change))
        self._unsubscribers.append(
            async_track_time_interval(
                self.hass,
                callback(lambda _now: self.check_tools()),
                timedelta(seconds=FFMPEG_CHECK_INTERVAL_SECONDS),
            )
        )
        await self._async_refresh_storage()

    @callback
    def async_stop(self) -> None:
        """Cancel timers and listeners."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        for job in self.jobs.values():
            for unsub in job.unsubscribers.values():
                unsub()
        self.jobs.clear()
        self._target_jobs.clear()

    # ----- Queries used by the entities -----

    @property
    def phase(self) -> str:
        """Return the most advanced phase among active jobs."""
        active = {job.phase for job in self.jobs.values()}
        return next((phase for phase in PHASES if phase in active), PHASE_IDLE)

    def jobs_in(self, phase: str) -> list[ActivityJob]:
        """Return the active jobs in a phase, oldest first."""
        return sorted(
            (job for job in self.jobs.values() if job.phase == phase),
            key=lambda job: job.started_at,
        )

    def target_job(self, entity_id: str) -> ActivityJob | None:
        """Return the announcement playing on a media player."""
        job_id = self._target_jobs.get(entity_id)
        return self.jobs.get(job_id) if job_id else None

    @callback
    def check_tools(self) -> None:
        """Refresh whether ffmpeg and ffprobe are installed."""
        ffmpeg_path, ffprobe_path = find_ffmpeg(), find_ffprobe()
        if (ffmpeg_path, ffprobe_path) != (self.ffmpeg_path, self.ffprobe_path):
            self.ffmpeg_path, self.ffprobe_path = ffmpeg_path, ffprobe_path
            self._updated()

    # ----- Uploads -----

    @callback
    def async_upload_started(self, job_id: str, user: Any) -> None:
        """Mark an upload as being received."""
        job = ActivityJob(
            id=job_id,
            phase=PHASE_RECEIVING,
            type=TYPE_VOICE,
            started_at=dt_util.utcnow(),
            user_id=_user_id(user),
            user_name=_user_name(user),
            recording_id=job_id,
        )
        self.jobs[job_id] = job
        self._fire(EVENT_RECEIVING_STARTED, None, None, self._event_data(job))
        self._updated()

    @callback
    def async_upload_targets(self, job_id: str, targets: list[str]) -> None:
        """Record where an upload is going as soon as the request says so."""
        if (job := self.jobs.get(job_id)) is not None and targets != job.targets:
            job.targets = list(targets)
            self._updated()

    @callback
    def async_processing_started(self, job_id: str, targets: list[str]) -> None:
        """Mark an upload as being validated and converted."""
        if (job := self.jobs.get(job_id)) is None:
            return
        job.phase = PHASE_PROCESSING
        job.targets = list(targets)
        self._fire(EVENT_PROCESSING_STARTED, None, None, self._event_data(job))
        self._updated()

    @callback
    def async_upload_succeeded(
        self,
        job_id: str,
        metadata: dict[str, Any],
        timings: dict[str, int],
        user: Any,
    ) -> None:
        """Record a successful upload."""
        self.jobs.pop(job_id, None)
        self.last_timings = dict(timings)
        targets = _split_targets(metadata.get("entity_id"))
        self.last_upload = {
            "status": "ok",
            "at": dt_util.utcnow().isoformat(),
            "http_status": 200,
            "detail": None,
            "user": _user_name(user),
            "targets": targets,
            "recording_id": job_id,
        }
        data = {
            "recording_id": job_id,
            "media_source_id": f"{MEDIA_SOURCE_URI_PREFIX}/{job_id}",
            "url": f"{MEDIA_URL_BASE}/{job_id}.{metadata.get('media_extension')}",
            "targets": targets,
            "duration": metadata.get("duration"),
            "was_transcoded": metadata.get("was_transcoded"),
            "user_id": _user_id(user),
            "user": _user_name(user),
        }
        self._fire(EVENT_RECORDED, EVENT_CATEGORY_RECORDING, "recorded", data)
        self._updated()

    @callback
    def async_upload_failed(
        self,
        job_id: str,
        status: str,
        *,
        http_status: int | None,
        detail: str | None,
        user: Any,
    ) -> None:
        """Record a rejected or failed upload."""
        job = self.jobs.pop(job_id, None)
        self.failed_uploads += 1
        self.last_upload = {
            "status": status,
            "at": dt_util.utcnow().isoformat(),
            "http_status": http_status,
            "detail": detail,
            "user": _user_name(user),
            "targets": list(job.targets) if job else [],
            "recording_id": job_id,
        }
        if status == "unavailable":
            self.check_tools()
        data = {
            "recording_id": job_id,
            "status": status,
            "http_status": http_status,
            "detail": detail,
            "targets": self.last_upload["targets"],
            "user_id": _user_id(user),
            "user": _user_name(user),
        }
        self._fire(EVENT_UPLOAD_FAILED, EVENT_CATEGORY_RECORDING, "failed", data)
        self._updated()

    # ----- Announcements -----

    async def async_register_speakers(self, targets: list[str]) -> None:
        """Remember new target speakers so they get their own playing sensor."""
        if added := await self.store.async_add_speakers(targets):
            async_dispatcher_send(self.hass, SIGNAL_SPEAKER_ADDED, added)

    @callback
    def async_playback_started(
        self,
        *,
        announcement_type: str,
        targets: list[str],
        duration: float,
        user: Any,
        recording_id: str | None = None,
        message: str | None = None,
    ) -> ActivityJob:
        """Mark an announcement as playing on its speakers."""
        job_id = uuid4().hex
        job = ActivityJob(
            id=job_id,
            phase=PHASE_PLAYING,
            type=announcement_type,
            started_at=dt_util.utcnow(),
            targets=list(targets),
            user_id=_user_id(user),
            user_name=_user_name(user),
            recording_id=recording_id,
            message=message,
            duration=duration,
            expected_end=dt_util.utcnow() + timedelta(seconds=duration),
        )
        self.jobs[job_id] = job
        for target in targets:
            # A new announcement on a speaker replaces the one it was playing.
            if (previous := self.target_job(target)) is not None:
                self._finish_target(previous, target, "replaced", update=False)
            self._target_jobs[target] = job_id
            job.playing_targets.add(target)
        job.unsubscribers["state"] = async_track_state_change_event(
            self.hass,
            list(targets),
            callback(lambda event: self._handle_speaker_state(job_id, event)),
        )
        self._fire(
            EVENT_PLAYBACK_STARTED,
            EVENT_CATEGORY_ANNOUNCEMENT,
            "started",
            self._event_data(job),
        )
        self._updated()
        return job

    @callback
    def async_playback_dispatched(self, job: ActivityJob, failures: dict[str, str]) -> None:
        """Handle the result of asking each speaker to play."""
        if self.jobs.get(job.id) is not job:
            return
        for target, error in failures.items():
            job.failed_targets[target] = error
            self.failed_playbacks += 1
            self.last_playback_error = {
                "at": dt_util.utcnow().isoformat(),
                "target": target,
                "error": error,
                "type": job.type,
                "recording_id": job.recording_id,
            }
            self._fire(
                EVENT_PLAYBACK_FAILED,
                EVENT_CATEGORY_ANNOUNCEMENT,
                "failed",
                {**self._event_data(job), "target": target, "error": error},
            )
            self._finish_target(job, target, "failed", update=False)
        if self.jobs.get(job.id) is job:
            # Speakers start once play_media returns; time the expected end from here.
            delay = (job.duration or 0) + PLAYBACK_GRACE_SECONDS
            job.expected_end = dt_util.utcnow() + timedelta(seconds=job.duration or 0)
            job.unsubscribers["timer"] = async_call_later(
                self.hass, delay, callback(lambda _now: self._handle_expected_end(job.id))
            )
            job.unsubscribers["cap"] = async_call_later(
                self.hass,
                delay + PLAYBACK_MAX_OVERRUN_SECONDS,
                callback(lambda _now: self._finish_job_targets(job.id, "timeout")),
            )
        self._updated()

    @callback
    def _handle_speaker_state(self, job_id: str, event: Event[EventStateChangedData]) -> None:
        job = self.jobs.get(job_id)
        target = event.data["entity_id"]
        if job is None or target not in job.playing_targets:
            return
        new_state = event.data["new_state"]
        if (
            new_state is not None
            and new_state.state == STATE_PLAYING
            and _content_matches(job, new_state.attributes.get("media_content_id"))
        ):
            job.seen_playing.add(target)
        elif target in job.seen_playing:
            self._finish_target(job, target, "speaker_stopped")

    @callback
    def _handle_expected_end(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if job is None:
            return
        job.unsubscribers.pop("timer", None)
        for target in list(job.playing_targets):
            state = self.hass.states.get(target)
            still_playing = (
                target in job.seen_playing
                and state is not None
                and state.state == STATE_PLAYING
                and _content_matches(job, state.attributes.get("media_content_id"))
            )
            # Speakers that report the announcement keep it until they stop or hit the cap.
            if not still_playing:
                self._finish_target(job, target, "expected_end", update=False)
        self._updated()

    @callback
    def _finish_job_targets(self, job_id: str, reason: str) -> None:
        if (job := self.jobs.get(job_id)) is None:
            return
        job.unsubscribers.pop("cap", None)
        for target in list(job.playing_targets):
            self._finish_target(job, target, reason, update=False)
        self._updated()

    @callback
    def _finish_target(
        self, job: ActivityJob, target: str, reason: str, *, update: bool = True
    ) -> None:
        job.playing_targets.discard(target)
        if self._target_jobs.get(target) == job.id:
            self._target_jobs.pop(target, None)
        if not job.playing_targets:
            self._finish_job(job, reason)
        if update:
            self._updated()

    @callback
    def _finish_job(self, job: ActivityJob, reason: str) -> None:
        self.jobs.pop(job.id, None)
        for unsub in job.unsubscribers.values():
            unsub()
        job.unsubscribers.clear()
        played = [target for target in job.targets if target not in job.failed_targets]
        if not played:
            result = "failed"
        elif job.failed_targets:
            result = "partial"
        else:
            result = "ok"
        self.last_announcement = {
            **self._event_data(job),
            "started_at": job.started_at.isoformat(),
            "finished_at": dt_util.utcnow().isoformat(),
            "result": result,
            "failed_targets": dict(job.failed_targets),
            "end_reason": reason,
        }
        if played:
            self._fire(
                EVENT_PLAYBACK_FINISHED,
                EVENT_CATEGORY_ANNOUNCEMENT,
                "finished",
                {**self._event_data(job), "result": result, "end_reason": reason},
            )

    # ----- Store changes -----

    @callback
    def _handle_store_change(self, kind: str, data: dict[str, Any]) -> None:
        if kind == "deleted":
            self._fire(
                EVENT_DELETED,
                EVENT_CATEGORY_RECORDING,
                "deleted",
                {"recording_id": data.get("id"), "reason": data.get("reason")},
            )
        elif kind == "cleanup":
            self.last_cleanup = {**data, "at": dt_util.utcnow().isoformat()}
            self._fire(EVENT_CLEANUP, EVENT_CATEGORY_RECORDING, "cleanup", data)
        self.hass.async_create_background_task(
            self._async_refresh_storage(), "voice_announcement_storage_size"
        )
        self._updated()

    async def _async_refresh_storage(self) -> None:
        try:
            self.storage_bytes = await self.store.async_get_storage_bytes()
        except OSError as err:
            _LOGGER.debug("Could not measure Voice Announcement storage: %s", err)
            return
        self._updated()

    # ----- Helpers -----

    @staticmethod
    def _event_data(job: ActivityJob) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": job.id,
            "type": job.type,
            "targets": list(job.targets),
            "recording_id": job.recording_id,
            "duration": job.duration,
            "user_id": job.user_id,
            "user": job.user_name,
        }
        if job.message is not None:
            data["message"] = job.message
        return data

    @callback
    def _fire(
        self,
        bus_event: str,
        category: str | None,
        event_type: str | None,
        data: dict[str, Any],
    ) -> None:
        self.hass.bus.async_fire(bus_event, data)
        if category is not None:
            async_dispatcher_send(self.hass, SIGNAL_EVENT, category, event_type, data)

    @callback
    def _updated(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_ACTIVITY_UPDATED)


def _content_matches(job: ActivityJob, content_id: Any) -> bool:
    """Return whether a speaker's media content belongs to the announcement."""
    if not isinstance(content_id, str):
        return False
    if job.type == TYPE_TTS:
        return "tts" in content_id
    return bool(job.recording_id) and job.recording_id in content_id


def _split_targets(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [item for item in value.split(",") if item]


def _user_id(user: Any) -> str | None:
    value = getattr(user, "id", None)
    return str(value) if value else None


def _user_name(user: Any) -> str | None:
    value = getattr(user, "name", None)
    return str(value) if value else None
