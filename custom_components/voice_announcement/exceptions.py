"""Exceptions for Voice Announcement."""

from __future__ import annotations


class VoiceAnnouncementError(Exception):
    """Base error for this integration."""


class FFmpegUnavailableError(VoiceAnnouncementError):
    """Raised when ffmpeg is not available."""


class AudioConversionError(VoiceAnnouncementError):
    """Raised when ffmpeg cannot convert the uploaded audio."""


class AudioProbeError(VoiceAnnouncementError):
    """Raised when ffprobe cannot validate the uploaded audio."""


class InvalidAudioUploadError(VoiceAnnouncementError):
    """Raised when an upload cannot be accepted."""
