"""HTTP views for Voice Announcement."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
import json
import logging
from math import ceil
from pathlib import Path
import re
from time import monotonic, perf_counter
from typing import Any
from uuid import uuid4

from aiohttp import web
from homeassistant.auth.permissions.const import CAT_ENTITIES, POLICY_CONTROL
from homeassistant.components.http import KEY_HASS_USER, HomeAssistantView
from homeassistant.core import HomeAssistant, valid_entity_id
from homeassistant.exceptions import Unauthorized

from .audio_policy import (
    normalize_codec_name,
    normalize_mime_type,
    passthrough_allowed,
    resolve_audio_policy,
)
from .const import (
    DATA_STORE,
    DATA_UPLOAD_RATE_LIMIT,
    DATA_UPLOAD_SEMAPHORE,
    DEFAULT_MAX_DURATION,
    DOMAIN,
    KEEP_ORIGINAL_UPLOADS,
    MAX_UPLOAD_BYTES,
    MAX_UPLOADS_PER_WINDOW,
    MEDIA_SOURCE_URI_PREFIX,
    MEDIA_URL_BASE,
    MIME_TO_EXTENSION,
    SUPPORTED_MIME_TYPES,
    UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
    UPLOAD_URL,
)
from .exceptions import AudioConversionError, AudioProbeError, FFmpegUnavailableError
from .ffmpeg import async_convert_audio, async_probe_audio
from .storage import VoiceAnnouncementStore

_LOGGER = logging.getLogger(__name__)

_SAFE_EXTENSION = re.compile(r"^[a-z0-9]{1,8}$")
_WHITESPACE = re.compile(r"\s+")
_SUPPORTED_SOURCE_CODECS: dict[str, set[str]] = {
    "audio/mp4": {"aac", "alac", "mp3"},
    "audio/mpeg": {"mp3"},
    "audio/webm": {"opus"},
    "audio/ogg": {"opus", "vorbis"},
    "audio/wav": {"pcm"},
}
_MAX_METADATA_BYTES = 8192
_MAX_TARGET_ENTITIES = 20
_SIGNATURE_BYTES = 32


class VoiceAnnouncementUploadView(HomeAssistantView):
    """Accept browser-recorded audio uploads."""

    url = UPLOAD_URL
    name = "api:voice_announcement:upload"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Handle an audio upload."""
        started = perf_counter()
        remote = request.remote
        if request.content_length and request.content_length > MAX_UPLOAD_BYTES:
            _LOGGER.warning(
                "Rejected Voice Announcement upload because it exceeds the server limit (%s)",
                _context_string(
                    remote=remote,
                    content_length=request.content_length,
                    max_upload_bytes=MAX_UPLOAD_BYTES,
                ),
            )
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_UPLOAD_BYTES,
                actual_size=request.content_length,
            )

        user = _require_request_user(request)
        user_id = str(getattr(user, "id", "unknown"))
        _LOGGER.debug(
            "Received Voice Announcement upload request (%s)",
            _context_string(
                user_id=user_id,
                remote=remote,
                content_length=request.content_length,
            ),
        )
        await _enforce_rate_limit(self.hass, user_id)

        store: VoiceAnnouncementStore = self.hass.data[DOMAIN][DATA_STORE]
        semaphore = self.hass.data[DOMAIN][DATA_UPLOAD_SEMAPHORE]
        if semaphore.locked():
            _LOGGER.debug(
                "Voice Announcement upload is waiting for an available processing slot (%s)",
                _context_string(user_id=user_id, remote=remote),
            )
        async with semaphore:
            recording_id = uuid4().hex
            temp_path = store.build_temp_file_path(recording_id)
            try:
                upload = await _read_multipart_upload(request, store, temp_path)
            except Unauthorized:
                raise
            except web.HTTPException as err:
                _log_upload_http_exception(
                    err,
                    recording_id=recording_id,
                    user_id=user_id,
                    remote=remote,
                )
                await _cleanup_paths(store, temp_path)
                raise
            except Exception:
                _LOGGER.exception(
                    "Unexpected error while receiving Voice Announcement upload (%s)",
                    _context_string(
                        recording_id=recording_id,
                        user_id=user_id,
                        remote=remote,
                    ),
                )
                await _cleanup_paths(store, temp_path)
                raise

            return await async_finalize_recording_upload(
                store=store,
                user=user,
                remote=remote,
                recording_id=recording_id,
                temp_path=temp_path,
                metadata=upload["metadata"],
                upload_size=upload["size"],
                read_ms=round((perf_counter() - started) * 1000),
                mode="classic",
            )


async def async_finalize_recording_upload(
    *,
    store: VoiceAnnouncementStore,
    user: Any,
    remote: str | None,
    recording_id: str,
    temp_path: Path,
    metadata: dict[str, Any],
    upload_size: int,
    read_ms: int = 0,
    mode: str = "classic",
) -> web.Response:
    """Validate, normalize and persist an uploaded recording."""
    started = perf_counter()
    original_path: Path | None = None
    media_path: Path | None = None
    recording_saved = False
    entity_id = ""
    declared_mime_type = ""
    detected_mime_type = ""
    validated_mime_type = ""
    source_codec: str | None = None
    user_id = str(getattr(user, "id", "unknown"))

    try:
        entity_ids = _validate_entity_ids(metadata.get("entity_id"))
        entity_id = ",".join(entity_ids)
        for target in entity_ids:
            _authorize_user_for_entity(user, target)

        policy = resolve_audio_policy(_parse_audio_policy_value(metadata.get("audio_policy")))
        declared_mime_type = normalize_mime_type(metadata.get("mime_type"))
        _LOGGER.debug(
            "Parsed Voice Announcement upload metadata (%s)",
            _context_string(
                mode=mode,
                recording_id=recording_id,
                user_id=user_id,
                entity_id=entity_id,
                remote=remote,
                size_bytes=upload_size,
                declared_mime_type=declared_mime_type,
                input_profile=policy["input_profile"],
                output_profile=policy["output_profile"],
                transcoding=policy["transcoding"],
            ),
        )
        detected_mime_type = await _detect_mime_type(
            store,
            temp_path,
            declared_mime_type,
        )
        if detected_mime_type not in SUPPORTED_MIME_TYPES:
            raise web.HTTPUnsupportedMediaType(
                text=f"Unsupported audio format: {detected_mime_type}"
            )

        try:
            probe = await async_probe_audio(temp_path)
        except AudioProbeError as err:
            raise _http_error_for_probe_failure(err) from err
        probe_done = perf_counter()

        validated_mime_type = _resolve_validated_mime_type(
            detected_mime_type,
            probe,
            recording_id=recording_id,
            user_id=user_id,
            entity_id=entity_id,
        )
        if validated_mime_type not in SUPPORTED_MIME_TYPES:
            raise web.HTTPUnsupportedMediaType(
                text="Uploaded file does not contain a supported audio container"
            )

        source_codec = normalize_codec_name(probe.get("codec_name"))
        if not _is_supported_source_codec(validated_mime_type, source_codec):
            raise web.HTTPUnsupportedMediaType(
                text="Uploaded file uses an unsupported codec for its audio container"
            )

        duration = _resolve_duration(
            metadata.get("duration"),
            probe,
            recording_id=recording_id,
            user_id=user_id,
            entity_id=entity_id,
        )
        if duration is None or duration <= 0:
            raise web.HTTPBadRequest(text="Unable to determine recording duration")
        if duration > DEFAULT_MAX_DURATION:
            raise web.HTTPBadRequest(text="Recording duration exceeds server limit")

        source_extension = _safe_extension(
            MIME_TO_EXTENSION.get(validated_mime_type)
            or MIME_TO_EXTENSION.get(detected_mime_type)
            or "bin"
        )
        _LOGGER.debug(
            "Validated Voice Announcement upload (%s)",
            _context_string(
                mode=mode,
                recording_id=recording_id,
                user_id=user_id,
                entity_id=entity_id,
                detected_mime_type=detected_mime_type,
                validated_mime_type=validated_mime_type,
                source_codec=source_codec,
                duration_seconds=round(duration, 3),
            ),
        )

        should_passthrough = False
        if policy["transcoding"] == "auto":
            should_passthrough = passthrough_allowed(
                validated_mime_type,
                source_codec,
                policy["output_passthrough_rules"],
            )
            if not should_passthrough:
                _LOGGER.warning(
                    "Voice Announcement output profile fallback to transcoding (%s)",
                    _context_string(
                        mode=mode,
                        recording_id=recording_id,
                        user_id=user_id,
                        entity_id=entity_id,
                        output_profile=policy["output_profile"],
                        input_profile=policy["input_profile"],
                        mime_type=validated_mime_type,
                        codec=source_codec or "unknown",
                    ),
                )
            else:
                _LOGGER.debug(
                    "Voice Announcement upload matches passthrough rules (%s)",
                    _context_string(
                        mode=mode,
                        recording_id=recording_id,
                        user_id=user_id,
                        entity_id=entity_id,
                        mime_type=validated_mime_type,
                        codec=source_codec,
                        output_profile=policy["output_profile"],
                    ),
                )
        elif policy["transcoding"] == "never":
            should_passthrough = passthrough_allowed(
                validated_mime_type,
                source_codec,
                policy["output_passthrough_rules"],
            )
            if not should_passthrough:
                _LOGGER.warning(
                    "Voice Announcement output profile rejected upload because passthrough "
                    "was required and transcoding is disabled (%s)",
                    _context_string(
                        mode=mode,
                        recording_id=recording_id,
                        user_id=user_id,
                        entity_id=entity_id,
                        output_profile=policy["output_profile"],
                        input_profile=policy["input_profile"],
                        mime_type=validated_mime_type,
                        codec=source_codec or "unknown",
                    ),
                )
                raise web.HTTPBadRequest(
                    text=(
                        "Uploaded audio is not compatible with the selected "
                        "output_profile while transcoding is disabled"
                    )
                )

        media_mime_type = validated_mime_type
        media_codec = source_codec
        media_extension = source_extension
        was_transcoded = False

        if should_passthrough:
            _LOGGER.debug(
                "Serving Voice Announcement upload without transcoding (%s)",
                _context_string(
                    mode=mode,
                    recording_id=recording_id,
                    user_id=user_id,
                    entity_id=entity_id,
                    mime_type=validated_mime_type,
                    codec=source_codec,
                ),
            )
            media_path = store.build_media_file_path(recording_id, media_extension)
            await store.async_move_file(temp_path, media_path)
            temp_path = None
            if KEEP_ORIGINAL_UPLOADS:
                original_path = media_path
        else:
            target = policy["transcode_target"]
            _LOGGER.debug(
                "Transcoding Voice Announcement upload (%s)",
                _context_string(
                    mode=mode,
                    recording_id=recording_id,
                    user_id=user_id,
                    entity_id=entity_id,
                    source_mime_type=validated_mime_type,
                    source_codec=source_codec,
                    target_codec=target["codec"],
                    target_sample_rate=target["sample_rate"],
                    target_channels=target["channels"],
                    target_bitrate=target["bitrate"],
                ),
            )
            media_extension = _safe_extension(target["extension"])
            media_path = store.build_media_file_path(recording_id, media_extension)
            conversion_input = temp_path
            if KEEP_ORIGINAL_UPLOADS:
                original_path = store.build_original_file_path(
                    recording_id,
                    source_extension,
                )
                await store.async_move_file(temp_path, original_path)
                temp_path = None
                conversion_input = original_path

            try:
                await async_convert_audio(conversion_input, media_path, target)
            except FFmpegUnavailableError as err:
                raise web.HTTPServiceUnavailable(
                    text=f"Audio transcoding is unavailable: {err}"
                ) from err
            except AudioConversionError as err:
                _LOGGER.warning("Voice Announcement ffmpeg conversion failed: %s", err)
                raise web.HTTPBadRequest(text="Audio processing failed") from err

            if not KEEP_ORIGINAL_UPLOADS and temp_path is not None:
                await store.async_delete_file(temp_path)
                temp_path = None

            media_mime_type = target["mime_type"]
            media_codec = target["codec"]
            was_transcoded = True
        process_done = perf_counter()

        now = datetime.now(UTC).isoformat()
        await store.async_add_recording(
            recording_id,
            {
                "id": recording_id,
                "created_at": now,
                "duration": duration,
                "entity_id": entity_id,
                "uploaded_by": user_id,
                "source_mime_type": declared_mime_type,
                "detected_mime_type": detected_mime_type,
                "validated_mime_type": validated_mime_type,
                "source_codec": source_codec,
                "original_filename": _truncate_text(metadata.get("filename")),
                "original_path": str(original_path) if original_path else None,
                "media_path": str(media_path),
                "media_mime_type": media_mime_type,
                "media_codec": media_codec,
                "media_extension": media_extension,
                "size": upload_size,
                "payload_version": _truncate_text(metadata.get("payload_version")),
                "input_profile": policy["input_profile"],
                "output_profile": policy["output_profile"],
                "transcoding": policy["transcoding"],
                "was_transcoded": was_transcoded,
                "upload_mode": mode,
            },
        )
        save_done = perf_counter()
        recording_saved = True

        probe_ms = round((probe_done - started) * 1000)
        process_ms = round((process_done - probe_done) * 1000)
        save_ms = round((save_done - process_done) * 1000)
        timings = {
            "read_ms": max(0, read_ms),
            "probe_ms": probe_ms,
            "process_ms": process_ms,
            "save_ms": save_ms,
            "total_ms": max(0, read_ms) + probe_ms + process_ms + save_ms,
        }

        _LOGGER.info(
            "Processed Voice Announcement upload successfully (%s)",
            _context_string(
                mode=mode,
                recording_id=recording_id,
                user_id=user_id,
                entity_id=entity_id,
                remote=remote,
                size_bytes=upload_size,
                input_profile=policy["input_profile"],
                output_profile=policy["output_profile"],
                transcoding=policy["transcoding"],
                input_mime_type=validated_mime_type,
                output_mime_type=media_mime_type,
                source_codec=source_codec,
                output_codec=media_codec,
                transcoded=was_transcoded,
                total_ms=timings["total_ms"],
                read_ms=timings["read_ms"],
                probe_ms=timings["probe_ms"],
                process_ms=timings["process_ms"],
                save_ms=timings["save_ms"],
            ),
        )

        return web.json_response(
            {
                "recording_id": recording_id,
                "media_source_id": f"{MEDIA_SOURCE_URI_PREFIX}/{recording_id}",
                "media_content_type": "music",
                "mime_type": media_mime_type,
                "url": f"{MEDIA_URL_BASE}/{recording_id}.{media_extension}",
                "was_transcoded": was_transcoded,
                "timings": timings,
                "mode": mode,
            }
        )
    except Unauthorized:
        raise
    except web.HTTPException as err:
        _log_upload_http_exception(
            err,
            mode=mode,
            recording_id=recording_id,
            user_id=user_id,
            entity_id=entity_id,
            remote=remote,
            size_bytes=upload_size,
            declared_mime_type=declared_mime_type,
            detected_mime_type=detected_mime_type,
            validated_mime_type=validated_mime_type,
            source_codec=source_codec,
        )
        raise
    except Exception:
        _LOGGER.exception(
            "Unexpected error while processing Voice Announcement upload (%s)",
            _context_string(
                mode=mode,
                recording_id=recording_id,
                user_id=user_id,
                entity_id=entity_id,
                remote=remote,
                size_bytes=upload_size,
                declared_mime_type=declared_mime_type,
                detected_mime_type=detected_mime_type,
                validated_mime_type=validated_mime_type,
                source_codec=source_codec,
            ),
        )
        raise
    finally:
        if not recording_saved:
            await _cleanup_paths(store, temp_path, original_path, media_path)


class VoiceAnnouncementMediaView(HomeAssistantView):
    """Serve normalized recordings to media players."""

    url = f"{MEDIA_URL_BASE}" + r"/{recording_id:[0-9a-f]+}.{extension:[a-z0-9]{1,8}}"
    name = "api:voice_announcement:media"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(
        self, request: web.Request, recording_id: str, extension: str
    ) -> web.StreamResponse:
        """Serve a converted recording."""
        store: VoiceAnnouncementStore = self.hass.data[DOMAIN][DATA_STORE]
        metadata = store.get(recording_id) or {}
        media_file = store.get_media_file(recording_id)

        if media_file is None:
            _LOGGER.debug(
                "Voice Announcement media request could not find recording (%s)",
                _context_string(recording_id=recording_id, requested_extension=extension),
            )
            raise web.HTTPNotFound(text="Recording not found")

        expected_extension = _safe_extension(
            metadata.get("media_extension") or media_file.suffix.lstrip(".") or "bin"
        )
        if extension != expected_extension:
            _LOGGER.debug(
                "Voice Announcement media request used an unexpected extension (%s)",
                _context_string(
                    recording_id=recording_id,
                    requested_extension=extension,
                    expected_extension=expected_extension,
                ),
            )
            raise web.HTTPNotFound(text="Recording not found")

        _LOGGER.debug(
            "Serving Voice Announcement media file (%s)",
            _context_string(
                recording_id=recording_id,
                entity_id=metadata.get("entity_id"),
                mime_type=metadata.get("media_mime_type"),
                extension=expected_extension,
            ),
        )

        return web.FileResponse(
            media_file,
            headers={
                "Cache-Control": "private, no-store, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": (f'inline; filename="{recording_id}.{expected_extension}"'),
                "Content-Type": str(metadata.get("media_mime_type") or "audio/mpeg"),
            },
        )


async def _read_multipart_upload(
    request: web.Request, store: VoiceAnnouncementStore, temp_path: Path
) -> dict[str, Any]:
    """Read multipart upload data with hard byte limits and store the audio."""
    if not str(request.content_type or "").startswith("multipart/"):
        raise web.HTTPBadRequest(text="Expected multipart/form-data upload")

    reader = await request.multipart()
    metadata: dict[str, str] = {}
    audio: bytes | None = None

    async for part in reader:
        if part.name == "file":
            if audio is not None:
                raise web.HTTPBadRequest(text="Only one audio file is allowed")
            metadata["filename"] = part.filename or ""
            audio = await _read_limited_part(part, MAX_UPLOAD_BYTES)
            if audio is None:
                raise web.HTTPRequestEntityTooLarge(
                    max_size=MAX_UPLOAD_BYTES, actual_size=MAX_UPLOAD_BYTES + 1
                )
        elif part.name:
            value = await _read_limited_part(part, _MAX_METADATA_BYTES)
            if value is None:
                raise web.HTTPBadRequest(text=f"Form field {part.name} is too large")
            metadata[part.name] = value.decode("utf-8", errors="replace").strip()

    if not audio:
        raise web.HTTPBadRequest(text="Missing audio file")

    # The upload is capped at MAX_UPLOAD_BYTES, so buffering it keeps disk
    # writes in a single executor job instead of blocking the event loop.
    await store.async_write_bytes(temp_path, audio)
    return {"metadata": metadata, "size": len(audio)}


async def _read_limited_part(part: Any, max_bytes: int) -> bytes | None:
    """Read a multipart part, or return None when it exceeds max_bytes."""
    data = bytearray()
    while chunk := await part.read_chunk():
        data.extend(chunk)
        if len(data) > max_bytes:
            return None
    return bytes(data)


async def _detect_mime_type(
    store: VoiceAnnouncementStore,
    audio_path: Path,
    declared_mime_type: str,
) -> str:
    """Detect common browser audio containers by signature."""
    audio = await store.async_read_bytes(audio_path, _SIGNATURE_BYTES)
    if audio.startswith(b"RIFF") and audio[8:12] == b"WAVE":
        return "audio/wav"
    if audio.startswith(b"OggS"):
        return "audio/ogg"
    if audio.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    if audio[4:8] == b"ftyp":
        return "audio/mp4"
    if audio.startswith(b"ID3") or (
        len(audio) > 2 and audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0
    ):
        return "audio/mpeg"
    return declared_mime_type


def _resolve_validated_mime_type(
    detected_mime_type: str,
    probe: dict[str, Any],
    *,
    recording_id: str | None = None,
    user_id: str | None = None,
    entity_id: str | None = None,
) -> str:
    """Resolve the final MIME type using ffprobe metadata when available."""
    probed_mime_type = _mime_type_from_probe(probe)
    if not probed_mime_type:
        return detected_mime_type

    if probed_mime_type != detected_mime_type:
        _LOGGER.warning(
            "Voice Announcement MIME mismatch detected; using ffprobe result (%s)",
            _context_string(
                recording_id=recording_id,
                user_id=user_id,
                entity_id=entity_id,
                signature_mime_type=detected_mime_type,
                ffprobe_mime_type=probed_mime_type,
            ),
        )
    return probed_mime_type


def _mime_type_from_probe(probe: dict[str, Any]) -> str | None:
    """Map ffprobe format names to supported MIME types."""
    format_name = str(probe.get("format_name") or "").lower()
    if not format_name:
        return None
    if "wav" in format_name:
        return "audio/wav"
    if "ogg" in format_name:
        return "audio/ogg"
    if "webm" in format_name or "matroska" in format_name:
        return "audio/webm"
    if "mp3" in format_name:
        return "audio/mpeg"
    if "mp4" in format_name or "mov" in format_name or "m4a" in format_name:
        return "audio/mp4"
    return None


def _is_supported_source_codec(mime_type: str, codec: str | None) -> bool:
    """Return whether the source codec is supported for the detected container."""
    if codec is None:
        return False
    return codec in _SUPPORTED_SOURCE_CODECS.get(mime_type, set())


def _resolve_duration(
    client_duration: Any,
    probe: dict[str, Any],
    *,
    recording_id: str | None = None,
    user_id: str | None = None,
    entity_id: str | None = None,
) -> float | None:
    """Return the best validated duration for the upload."""
    reported_duration = _parse_float(client_duration, 0.0)
    for candidate in (probe.get("format_duration"), probe.get("stream_duration")):
        duration = _parse_float(candidate, 0.0)
        if duration > 0:
            if reported_duration > 0 and abs(reported_duration - duration) > 2:
                _LOGGER.warning(
                    "Voice Announcement duration mismatch detected; using ffprobe duration (%s)",
                    _context_string(
                        recording_id=recording_id,
                        user_id=user_id,
                        entity_id=entity_id,
                        reported_duration=round(reported_duration, 3),
                        probed_duration=round(duration, 3),
                    ),
                )
            return duration
    return reported_duration or None


def _require_request_user(request: web.Request) -> Any:
    """Return the authenticated Home Assistant user."""
    return request[KEY_HASS_USER]


def _authorize_user_for_entity(user: Any, entity_id: str) -> None:
    """Ensure the current user can control the target media player."""
    if bool(getattr(user, "is_admin", False)):
        return

    permissions = getattr(user, "permissions", None)
    check_entity = getattr(permissions, "check_entity", None)
    if callable(check_entity) and check_entity(entity_id, POLICY_CONTROL):
        return

    _LOGGER.warning(
        "Rejected Voice Announcement upload because the user lacks control permissions (%s)",
        _context_string(
            user_id=getattr(user, "id", None),
            entity_id=entity_id,
            permission=POLICY_CONTROL,
        ),
    )

    raise Unauthorized(
        permission=POLICY_CONTROL,
        user_id=getattr(user, "id", None),
        perm_category=CAT_ENTITIES,
    )


async def _enforce_rate_limit(hass: HomeAssistant, user_id: str) -> None:
    """Apply a simple per-user sliding-window rate limit."""
    buckets: dict[str, deque[float]] = hass.data[DOMAIN][DATA_UPLOAD_RATE_LIMIT]
    now = monotonic()
    cutoff = now - UPLOAD_RATE_LIMIT_WINDOW_SECONDS
    bucket = buckets.setdefault(user_id, deque())

    while bucket and bucket[0] <= cutoff:
        bucket.popleft()

    if len(bucket) >= MAX_UPLOADS_PER_WINDOW:
        retry_after = max(1, ceil(UPLOAD_RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0])))
        _LOGGER.warning(
            "Rate limit exceeded for Voice Announcement uploads (%s)",
            _context_string(
                user_id=user_id,
                uploads_in_window=len(bucket),
                max_uploads=MAX_UPLOADS_PER_WINDOW,
                window_seconds=UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
                retry_after=retry_after,
            ),
        )
        raise web.HTTPTooManyRequests(
            headers={"Retry-After": str(retry_after)},
            text="Upload rate limit exceeded",
        )

    bucket.append(now)

    for key in list(buckets):
        if buckets[key] and buckets[key][-1] > cutoff:
            continue
        buckets.pop(key, None)


async def _cleanup_paths(
    store: VoiceAnnouncementStore,
    *paths: Path | None,
) -> None:
    """Delete unique filesystem paths when a request fails."""
    seen: set[Path] = set()
    deleted = 0
    for path in paths:
        if path is None or path in seen:
            continue
        seen.add(path)
        await store.async_delete_file(path)
        deleted += 1
    if deleted:
        _LOGGER.debug(
            "Cleaned temporary Voice Announcement files after a failed request (%s)",
            _context_string(deleted_paths=deleted),
        )


def _validate_entity_ids(value: Any) -> list[str]:
    """Validate the comma-separated target media players from the upload payload."""
    items = value.split(",") if isinstance(value, str) else []
    entity_ids = list(dict.fromkeys(item.strip() for item in items if item.strip()))
    if not entity_ids:
        raise web.HTTPBadRequest(text="Missing entity_id")
    if len(entity_ids) > _MAX_TARGET_ENTITIES:
        raise web.HTTPBadRequest(text="Too many target media players")
    for entity_id in entity_ids:
        if not entity_id.startswith("media_player.") or not valid_entity_id(entity_id):
            raise web.HTTPBadRequest(text="entity_id must be a media_player")
    return entity_ids


def _http_error_for_probe_failure(err: AudioProbeError) -> web.HTTPException:
    """Map probe failures to HTTP responses."""
    if "executable was not found" in str(err):
        return web.HTTPServiceUnavailable(
            text="Audio validation is unavailable because ffprobe is not installed"
        )
    # ffprobe output contains server paths, so it stays in the log.
    _LOGGER.debug("Voice Announcement ffprobe rejected the upload: %s", err)
    return web.HTTPUnsupportedMediaType(text="Invalid or unsupported audio upload")


def _parse_audio_policy_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except TypeError, ValueError:
        return default


def _safe_extension(value: Any) -> str:
    if not isinstance(value, str):
        return "bin"
    extension = value.strip().lower().lstrip(".")
    if _SAFE_EXTENSION.fullmatch(extension):
        return extension
    return "bin"


def _truncate_text(value: Any, max_length: int = 255) -> str | None:
    """Store short metadata strings only."""
    if not isinstance(value, str):
        return None
    return value.strip()[:max_length] or None


def _log_upload_http_exception(err: web.HTTPException, **fields: Any) -> None:
    """Log an upload HTTP error with consistent structure."""
    level = logging.ERROR if err.status >= 500 else logging.WARNING
    _LOGGER.log(
        level,
        "Voice Announcement upload failed (%s)",
        _context_string(
            status=err.status,
            reason=_truncate_text(getattr(err, "reason", None), 120),
            detail=_truncate_text(getattr(err, "text", None), 160),
            **fields,
        ),
    )


def _context_string(**fields: Any) -> str:
    """Render a compact key=value context string for logs."""
    parts: list[str] = []
    for key, value in fields.items():
        if value is None or value == "":
            continue
        if isinstance(value, float):
            rendered = f"{value:.3f}"
        elif isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (list, tuple, set)):
            rendered = ",".join(_normalize_log_value(item) for item in value if item is not None)
        else:
            rendered = _normalize_log_value(value)
        if rendered:
            parts.append(f"{key}={rendered}")
    return " ".join(parts) or "no_context"


def _normalize_log_value(value: Any) -> str:
    """Return a compact logging-safe string value."""
    return _WHITESPACE.sub("_", str(value).strip())
