"""Persistent recording storage for Voice Announcement."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path
import shutil
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    AUTO_CLEANUP_KEEP_DAYS,
    DOMAIN,
    MAX_STORED_RECORDINGS,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class VoiceAnnouncementStore:
    """Manage recording files and metadata."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store."""
        self.hass = hass
        self.base_path = Path(hass.config.path(DOMAIN))
        self.temp_path = self.base_path / "tmp"
        self.original_path = self.base_path / "original"
        self.media_path = self.base_path / "media"
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._recordings: dict[str, dict[str, Any]] = {}
        self._mutation_lock = asyncio.Lock()

    @property
    def recordings(self) -> dict[str, dict[str, Any]]:
        """Return all known recordings."""
        return self._recordings

    async def async_load(self) -> None:
        """Load metadata and ensure directories exist."""
        await self.hass.async_add_executor_job(self._ensure_directories)
        deleted_temp_files = await self.hass.async_add_executor_job(self._cleanup_temp_directory)
        data = await self._store.async_load()
        if isinstance(data, dict):
            self._recordings = dict(data.get("recordings", {}))
        _LOGGER.debug(
            "Loaded Voice Announcement store (recordings=%s, deleted_temp_files=%s)",
            len(self._recordings),
            deleted_temp_files,
        )
        await self.async_enforce_limits()

    async def async_save(self) -> None:
        """Persist metadata."""
        await self._store.async_save({"recordings": self._recordings})

    async def async_write_bytes(self, path: Path, data: bytes) -> None:
        """Write bytes outside the event loop."""
        await self.hass.async_add_executor_job(path.write_bytes, data)

    async def async_append_bytes(self, path: Path, data: bytes) -> None:
        """Append bytes to a file outside the event loop."""
        await self.hass.async_add_executor_job(self._append_bytes, path, data)

    async def async_move_file(self, source: Path, destination: Path) -> None:
        """Move a file outside the event loop."""
        await self.hass.async_add_executor_job(self._move_file, source, destination)

    async def async_read_bytes(self, path: Path, max_bytes: int) -> bytes:
        """Read up to max_bytes from a file outside the event loop."""
        return await self.hass.async_add_executor_job(
            self._read_bytes,
            path,
            max_bytes,
        )

    async def async_delete_file(self, path: Path) -> None:
        """Delete a file if present."""
        await self.hass.async_add_executor_job(self._delete_file, path)

    async def async_add_recording(self, recording_id: str, metadata: dict[str, Any]) -> None:
        """Add or replace a recording entry."""
        async with self._mutation_lock:
            self._recordings[recording_id] = metadata
            _LOGGER.debug(
                "Stored Voice Announcement recording metadata (recording_id=%s, entity_id=%s)",
                recording_id,
                metadata.get("entity_id"),
            )
            await self._async_enforce_limits_locked()
            await self.async_save()

    async def async_delete_recording(
        self,
        recording_id: str,
        *,
        reason: str = "unspecified",
    ) -> bool:
        """Delete a recording and its files."""
        async with self._mutation_lock:
            deleted = await self._async_delete_recording_locked(
                recording_id,
                reason=reason,
            )
            if deleted:
                await self.async_save()
            return deleted

    async def _async_delete_recording_locked(
        self,
        recording_id: str,
        *,
        reason: str,
    ) -> bool:
        """Delete a recording while the mutation lock is held."""
        metadata = self._recordings.pop(recording_id, None)
        if metadata is None:
            _LOGGER.debug(
                "Voice Announcement recording delete skipped because it does not exist "
                "(recording_id=%s, reason=%s)",
                recording_id,
                reason,
            )
            return False

        paths = [
            metadata.get("original_path"),
            metadata.get("media_path"),
        ]
        for path in self._iter_valid_paths(paths):
            await self.async_delete_file(path)

        _LOGGER.debug(
            "Deleted Voice Announcement recording (recording_id=%s, entity_id=%s, reason=%s)",
            recording_id,
            metadata.get("entity_id"),
            reason,
        )
        return True

    async def async_cleanup(
        self,
        keep_days: int,
        *,
        trigger: str = "automatic",
    ) -> int:
        """Delete recordings older than the retention window."""
        async with self._mutation_lock:
            deleted = await self._async_cleanup_locked(keep_days)
            if deleted:
                await self.async_save()

        if deleted:
            level = logging.INFO if trigger == "automatic" else logging.DEBUG
            _LOGGER.log(
                level,
                "Voice Announcement retention cleanup deleted recordings "
                "(deleted=%s, keep_days=%s, trigger=%s)",
                deleted,
                keep_days,
                trigger,
            )
        else:
            _LOGGER.debug(
                "Voice Announcement retention cleanup completed without deletions "
                "(keep_days=%s, trigger=%s)",
                keep_days,
                trigger,
            )
        return deleted

    async def _async_cleanup_locked(self, keep_days: int) -> int:
        """Delete old recordings while the mutation lock is held."""
        keep_days = max(1, keep_days)
        threshold = datetime.now(UTC) - timedelta(days=keep_days)
        deleted = 0

        for recording_id, metadata in list(self._recordings.items()):
            created_at = self._parse_datetime(metadata.get("created_at"))
            if (
                created_at is not None
                and created_at < threshold
                and await self._async_delete_recording_locked(recording_id, reason="retention")
            ):
                deleted += 1
        return deleted

    async def async_enforce_limits(self) -> int:
        """Apply retention and count limits automatically."""
        async with self._mutation_lock:
            deleted = await self._async_enforce_limits_locked()
            if deleted:
                await self.async_save()
        return deleted

    async def _async_enforce_limits_locked(self) -> int:
        """Apply retention and count limits while the mutation lock is held."""
        deleted = await self._async_cleanup_locked(AUTO_CLEANUP_KEEP_DAYS)
        deleted += await self._async_trim_to_max_recordings_locked(MAX_STORED_RECORDINGS)
        if deleted:
            _LOGGER.debug(
                "Voice Announcement automatic storage enforcement completed with deletions "
                "(deleted=%s, keep_days=%s, max_recordings=%s)",
                deleted,
                AUTO_CLEANUP_KEEP_DAYS,
                MAX_STORED_RECORDINGS,
            )
        return deleted

    async def async_trim_to_max_recordings(self, max_recordings: int) -> int:
        """Delete oldest recordings when the cap is exceeded."""
        async with self._mutation_lock:
            deleted = await self._async_trim_to_max_recordings_locked(max_recordings)
            if deleted:
                await self.async_save()
            return deleted

    async def _async_trim_to_max_recordings_locked(self, max_recordings: int) -> int:
        """Delete oldest recordings while the mutation lock is held."""
        if max_recordings <= 0 or len(self._recordings) <= max_recordings:
            return 0

        deleted = 0
        ordered_ids = [
            recording_id
            for recording_id, _metadata in sorted(
                self._recordings.items(),
                key=lambda entry: (
                    self._parse_datetime(entry[1].get("created_at"))
                    or datetime.min.replace(tzinfo=UTC)
                ),
            )
        ]
        overflow = len(ordered_ids) - max_recordings
        for recording_id in ordered_ids[:overflow]:
            if await self._async_delete_recording_locked(
                recording_id,
                reason="capacity_limit",
            ):
                deleted += 1
        if deleted:
            _LOGGER.info(
                "Voice Announcement capacity trim deleted recordings "
                "(deleted=%s, max_recordings=%s)",
                deleted,
                max_recordings,
            )
        return deleted

    def get(self, recording_id: str) -> dict[str, Any] | None:
        """Return a recording by id."""
        return self._recordings.get(recording_id)

    def get_media_file(self, recording_id: str) -> Path | None:
        """Return the normalized media file for a recording."""
        metadata = self.get(recording_id)
        if metadata is None:
            return None

        media_path = metadata.get("media_path")
        if not isinstance(media_path, str):
            return None

        path = Path(media_path)
        if not self._is_safe_child(path) or not path.is_file():
            return None

        return path

    def build_original_file_path(self, recording_id: str, extension: str) -> Path:
        """Return the original file path for a recording."""
        return self.original_path / f"{recording_id}.{extension}"

    def build_temp_file_path(self, recording_id: str, extension: str = "upload") -> Path:
        """Return the temporary upload file path for a recording."""
        return self.temp_path / f"{recording_id}.{extension}"

    def build_media_file_path(self, recording_id: str, extension: str) -> Path:
        """Return the normalized media file path for a recording."""
        return self.media_path / f"{recording_id}.{extension}"

    def _ensure_directories(self) -> None:
        self.temp_path.mkdir(parents=True, exist_ok=True)
        self.original_path.mkdir(parents=True, exist_ok=True)
        self.media_path.mkdir(parents=True, exist_ok=True)

    def _append_bytes(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as handle:
            handle.write(data)

    def _cleanup_temp_directory(self) -> int:
        deleted = 0
        for path in self.temp_path.glob("*"):
            if path.is_file():
                self._delete_file(path)
                deleted += 1
        return deleted

    def _is_safe_child(self, path: Path) -> bool:
        # Stored paths are always built from these directories; a lexical check
        # rejects tampered metadata without filesystem calls in the event loop.
        return path.name not in ("", ".", "..") and path.parent in (
            self.temp_path,
            self.original_path,
            self.media_path,
        )

    @staticmethod
    def _delete_file(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return

    @staticmethod
    def _move_file(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))

    @staticmethod
    def _read_bytes(path: Path, max_bytes: int) -> bytes:
        with path.open("rb") as file_handle:
            return file_handle.read(max_bytes)

    def _iter_valid_paths(self, paths: Iterable[Any]) -> Iterable[Path]:
        for raw_path in paths:
            if isinstance(raw_path, str):
                path = Path(raw_path)
                if self._is_safe_child(path):
                    yield path

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
