"""FFmpeg helpers for Voice Announcement."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import shutil
from time import perf_counter
from typing import Any

from .const import MAX_FFMPEG_SECONDS, MAX_FFPROBE_SECONDS
from .exceptions import AudioConversionError, AudioProbeError, FFmpegUnavailableError

_LOGGER = logging.getLogger(__name__)


def find_ffmpeg() -> str | None:
    """Return the ffmpeg executable path if available."""
    return shutil.which("ffmpeg")


async def async_assert_ffmpeg_available() -> None:
    """Raise if ffmpeg is not available."""
    if find_ffmpeg() is None:
        raise FFmpegUnavailableError("ffmpeg executable was not found")


def find_ffprobe() -> str | None:
    """Return the ffprobe executable path if available."""
    return shutil.which("ffprobe")


async def async_assert_ffprobe_available() -> None:
    """Raise if ffprobe is not available."""
    if find_ffprobe() is None:
        raise AudioProbeError("ffprobe executable was not found")


async def async_probe_audio(input_path: Path) -> dict[str, Any] | None:
    """Inspect the first audio stream using ffprobe when available."""
    ffprobe = find_ffprobe()
    if ffprobe is None:
        raise AudioProbeError("ffprobe executable was not found")
    started = perf_counter()
    _LOGGER.debug("Running ffprobe for Voice Announcement input %s", input_path.name)

    process = await asyncio.create_subprocess_exec(
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,channels,sample_rate,duration:format=format_name,duration",
        "-of",
        "json",
        str(input_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await _communicate_with_timeout(
        process,
        MAX_FFPROBE_SECONDS,
        AudioProbeError("ffprobe timed out while validating audio"),
    )
    if process.returncode != 0:
        error = stderr.decode("utf-8", errors="replace").strip()
        raise AudioProbeError(error or "ffprobe failed to inspect audio")

    try:
        payload = json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as err:
        raise AudioProbeError("ffprobe returned invalid JSON") from err

    streams = payload.get("streams")
    if not isinstance(streams, list) or not streams:
        raise AudioProbeError("ffprobe did not find an audio stream")

    stream = streams[0] if isinstance(streams[0], dict) else {}
    format_data = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    result = {
        "codec_name": stream.get("codec_name"),
        "channels": stream.get("channels"),
        "sample_rate": stream.get("sample_rate"),
        "stream_duration": stream.get("duration"),
        "format_name": format_data.get("format_name"),
        "format_duration": format_data.get("duration"),
    }
    _LOGGER.debug(
        "ffprobe completed for Voice Announcement input %s in %sms "
        "(codec=%s, sample_rate=%s, channels=%s, format=%s)",
        input_path.name,
        round((perf_counter() - started) * 1000),
        result.get("codec_name"),
        result.get("sample_rate"),
        result.get("channels"),
        result.get("format_name"),
    )
    return result


async def async_convert_audio(input_path: Path, output_path: Path, target: dict[str, Any]) -> None:
    """Normalize an audio file to the requested output target."""
    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise FFmpegUnavailableError("ffmpeg executable was not found")

    started = perf_counter()
    _LOGGER.debug(
        "Running ffmpeg for Voice Announcement conversion "
        "(input=%s, output=%s, codec=%s, format=%s, sample_rate=%s, channels=%s, bitrate=%s)",
        input_path.name,
        output_path.name,
        target.get("codec"),
        target.get("ffmpeg_format"),
        target.get("sample_rate"),
        target.get("channels"),
        target.get("bitrate"),
    )

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-sn",
        "-dn",
        "-ac",
        str(target["channels"]),
        "-ar",
        str(target["sample_rate"]),
        "-map_metadata",
        "-1",
        "-codec:a",
        str(target["ffmpeg_codec"]),
        "-b:a",
        str(target["bitrate"]),
    ]
    movflags = target.get("movflags")
    if movflags:
        command.extend(["-movflags", str(movflags)])
    command.extend(
        [
            "-f",
            str(target["ffmpeg_format"]),
            str(output_path),
        ]
    )

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await _communicate_with_timeout(
        process,
        MAX_FFMPEG_SECONDS,
        AudioConversionError("ffmpeg timed out while converting audio"),
    )

    if process.returncode != 0:
        error = stderr.decode("utf-8", errors="replace").strip()
        raise AudioConversionError(error or "ffmpeg failed to convert audio")
    _LOGGER.debug(
        "ffmpeg completed for Voice Announcement conversion in %sms (input=%s, output=%s)",
        round((perf_counter() - started) * 1000),
        input_path.name,
        output_path.name,
    )


async def _communicate_with_timeout(
    process: asyncio.subprocess.Process,
    timeout_seconds: int,
    timeout_error: Exception,
) -> tuple[bytes, bytes]:
    """Wait for a subprocess with a hard timeout and guaranteed cleanup."""
    try:
        async with asyncio.timeout(timeout_seconds):
            return await process.communicate()
    except TimeoutError as err:
        process.kill()
        await process.communicate()
        raise timeout_error from err
