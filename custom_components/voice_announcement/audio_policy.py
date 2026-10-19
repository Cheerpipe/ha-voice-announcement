"""Audio policy presets and resolution helpers."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .const import (
    DEFAULT_OUTPUT_BITRATE,
    DEFAULT_OUTPUT_CHANNELS,
    DEFAULT_OUTPUT_SAMPLE_RATE,
    SUPPORTED_MIME_TYPES,
)

DEFAULT_INPUT_PROFILE = "default"
DEFAULT_OUTPUT_PROFILE = "default"
DEFAULT_TRANSCODING_MODE = "always"

TRANSCODING_MODES = {"always", "auto", "never"}
ALLOWED_TRANSCODE_CODECS = {"aac", "mp3"}
ALLOWED_PASSTHROUGH_CODECS = {"aac", "mp3", "opus", "pcm", "vorbis"}
ALLOWED_INPUT_MIME_CANDIDATES = {
    "audio/mp4",
    "audio/webm;codecs=opus",
    "audio/ogg;codecs=opus",
    "audio/wav",
    "audio/mpeg",
}
ALLOWED_SAMPLE_RATES = (8000, 12000, 16000, 22050, 24000, 32000, 44100, 48000)
MIN_BITRATE_KBPS = 16
MAX_BITRATE_KBPS = 192
MAX_INPUT_MIME_CANDIDATES = 8
MAX_PASSTHROUGH_RULES = 12
MAX_CODECS_PER_RULE = 6

INPUT_PROFILES: dict[str, list[str]] = {
    "default": [
        "audio/webm;codecs=opus",
        "audio/mp4",
        "audio/ogg;codecs=opus",
    ],
    "chrome": [
        "audio/mp4",
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
    ],
    "safari": [
        "audio/mp4",
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
    ],
}

DEFAULT_MP3_TARGET = {
    "mime_type": "audio/mpeg",
    "codec": "mp3",
    "extension": "mp3",
    "ffmpeg_codec": "libmp3lame",
    "ffmpeg_format": "mp3",
    "sample_rate": DEFAULT_OUTPUT_SAMPLE_RATE,
    "bitrate": DEFAULT_OUTPUT_BITRATE,
    "channels": DEFAULT_OUTPUT_CHANNELS,
}

DEFAULT_AAC_TARGET = {
    "mime_type": "audio/mp4",
    "codec": "aac",
    "extension": "m4a",
    "ffmpeg_codec": "aac",
    "ffmpeg_format": "mp4",
    "sample_rate": DEFAULT_OUTPUT_SAMPLE_RATE,
    "bitrate": DEFAULT_OUTPUT_BITRATE,
    "channels": DEFAULT_OUTPUT_CHANNELS,
    "movflags": "+faststart",
}

OUTPUT_PROFILES: dict[str, dict[str, Any]] = {
    "default": {
        "passthrough_rules": [],
        "transcode_target": DEFAULT_MP3_TARGET,
    },
    "homepod": {
        "passthrough_rules": [
            {"mime_type": "audio/mpeg"},
        ],
        "transcode_target": DEFAULT_MP3_TARGET,
    },
    "google_home": {
        "passthrough_rules": [
            {"mime_type": "audio/mpeg"},
            {"mime_type": "audio/mp4"},
        ],
        "transcode_target": DEFAULT_MP3_TARGET,
    },
    "custom": {
        "passthrough_rules": [],
        "transcode_target": DEFAULT_MP3_TARGET,
    },
}

MIME_TYPE_ALIASES = {
    "audio/mp3": "audio/mpeg",
    "audio/x-m4a": "audio/mp4",
    "audio/m4a": "audio/mp4",
    "audio/x-wav": "audio/wav",
}

CODEC_ALIASES = {
    "mpeg": "mp3",
    "mp3float": "mp3",
    "aac_latm": "aac",
}
_BITRATE_PATTERN = re.compile(r"^(\d{2,3})k$", re.IGNORECASE)


def resolve_audio_policy(raw_policy: Any) -> dict[str, Any]:
    """Resolve a user-provided policy into a normalized backend policy."""
    data = raw_policy if isinstance(raw_policy, dict) else {}
    input_profile = _valid_key(data.get("input_profile"), INPUT_PROFILES, DEFAULT_INPUT_PROFILE)
    output_profile = _valid_key(data.get("output_profile"), OUTPUT_PROFILES, DEFAULT_OUTPUT_PROFILE)
    transcoding = _normalize_transcoding_mode(data.get("transcoding"))

    input_mime_candidates = _normalize_string_list(data.get("input_mime_candidates"))
    input_mime_candidates = [
        candidate
        for candidate in input_mime_candidates
        if candidate in ALLOWED_INPUT_MIME_CANDIDATES
    ]
    if not input_mime_candidates:
        input_mime_candidates = list(INPUT_PROFILES[input_profile])

    raw_passthrough_rules = data.get("output_passthrough_rules")
    if isinstance(raw_passthrough_rules, list):
        passthrough_rules = _normalize_passthrough_rules(raw_passthrough_rules)
    else:
        passthrough_rules = deepcopy(OUTPUT_PROFILES[output_profile]["passthrough_rules"])

    transcode_target = deepcopy(OUTPUT_PROFILES[output_profile]["transcode_target"])
    transcode_target.update(_normalize_transcode_target(data.get("transcode_target")))
    transcode_target = _finalize_transcode_target(transcode_target)

    return {
        "input_profile": input_profile,
        "output_profile": output_profile,
        "transcoding": transcoding,
        "input_mime_candidates": input_mime_candidates,
        "output_passthrough_rules": passthrough_rules,
        "transcode_target": transcode_target,
    }


def normalize_mime_type(value: Any) -> str:
    """Normalize MIME aliases."""
    if not isinstance(value, str) or not value.strip():
        return "application/octet-stream"
    normalized = value.split(";", 1)[0].strip().lower()
    return MIME_TYPE_ALIASES.get(normalized, normalized) or "application/octet-stream"


def normalize_codec_name(value: Any) -> str | None:
    """Normalize codec aliases."""
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().lower()
    if normalized.startswith("pcm_"):
        return "pcm"
    return CODEC_ALIASES.get(normalized, normalized)


def passthrough_allowed(
    mime_type: str, codec: str | None, passthrough_rules: list[dict[str, Any]]
) -> bool:
    """Return whether an upload may be served without transcoding."""
    normalized_mime = normalize_mime_type(mime_type)
    normalized_codec = normalize_codec_name(codec)
    for rule in passthrough_rules:
        if rule["mime_type"] != normalized_mime:
            continue
        required_codecs = rule.get("codecs")
        if not required_codecs:
            return True
        if normalized_codec and normalized_codec in required_codecs:
            return True
    return False


def _valid_key(value: Any, mapping: dict[str, Any], default: str) -> str:
    if isinstance(value, str) and value in mapping:
        return value
    return default


def _normalize_transcoding_mode(value: Any) -> str:
    if isinstance(value, str) and value in TRANSCODING_MODES:
        return value
    return DEFAULT_TRANSCODING_MODE


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        candidate = item.strip()
        if candidate:
            normalized.append(candidate)
        if len(normalized) >= MAX_INPUT_MIME_CANDIDATES:
            break
    return normalized


def _normalize_passthrough_rules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        mime_type = normalize_mime_type(item.get("mime_type") or item.get("mime"))
        if mime_type not in SUPPORTED_MIME_TYPES:
            continue
        codecs = [
            codec
            for codec in (
                normalize_codec_name(codec)
                for codec in _normalize_string_list(item.get("codecs"))[:MAX_CODECS_PER_RULE]
            )
            if codec and codec in ALLOWED_PASSTHROUGH_CODECS
        ]
        normalized.append({"mime_type": mime_type, "codecs": codecs})
        if len(normalized) >= MAX_PASSTHROUGH_RULES:
            break
    return normalized


def _normalize_transcode_target(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, Any] = {}
    codec = normalize_codec_name(value.get("codec"))
    if codec in ALLOWED_TRANSCODE_CODECS:
        normalized["codec"] = codec
    bitrate = _normalize_bitrate(value.get("bitrate"))
    if bitrate is not None:
        normalized["bitrate"] = bitrate
    sample_rate = _normalize_sample_rate(value.get("sample_rate"))
    if sample_rate is not None:
        normalized["sample_rate"] = str(sample_rate)
    channels = _normalize_channels(value.get("channels"))
    if channels is not None:
        normalized["channels"] = channels
    return normalized


def _finalize_transcode_target(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    codec = normalize_codec_name(normalized.get("codec")) or DEFAULT_MP3_TARGET["codec"]

    if codec == "aac":
        normalized["ffmpeg_codec"] = "aac"
        normalized["ffmpeg_format"] = "mp4"
        normalized["mime_type"] = "audio/mp4"
        normalized["extension"] = "m4a"
        normalized["movflags"] = normalized.get("movflags") or "+faststart"
    else:
        codec = "mp3"
        normalized["ffmpeg_codec"] = "libmp3lame"
        normalized["ffmpeg_format"] = "mp3"
        normalized["mime_type"] = "audio/mpeg"
        normalized["extension"] = "mp3"
        normalized.pop("movflags", None)

    normalized["codec"] = codec
    normalized["bitrate"] = _normalize_bitrate(normalized.get("bitrate")) or DEFAULT_OUTPUT_BITRATE
    normalized["sample_rate"] = str(
        _normalize_sample_rate(normalized.get("sample_rate")) or int(DEFAULT_OUTPUT_SAMPLE_RATE)
    )
    normalized["channels"] = (
        _normalize_channels(normalized.get("channels")) or DEFAULT_OUTPUT_CHANNELS
    )
    return normalized


def _coerce_positive_int(value: Any) -> int | None:
    try:
        coerced = int(value)
    except TypeError, ValueError:
        return None
    return coerced if coerced > 0 else None


def _normalize_bitrate(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _BITRATE_PATTERN.fullmatch(value.strip())
    if not match:
        return None
    kbps = min(MAX_BITRATE_KBPS, max(MIN_BITRATE_KBPS, int(match.group(1))))
    return f"{kbps}k"


def _normalize_sample_rate(value: Any) -> int | None:
    parsed = _coerce_positive_int(value)
    if parsed is None:
        return None
    return min(ALLOWED_SAMPLE_RATES, key=lambda allowed: abs(allowed - parsed))


def _normalize_channels(value: Any) -> int | None:
    parsed = _coerce_positive_int(value)
    if parsed is None:
        return None
    if parsed <= 1:
        return 1
    return 2
