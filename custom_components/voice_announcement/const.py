"""Constants for Voice Announcement."""

from __future__ import annotations

from pathlib import Path

DOMAIN = "voice_announcement"
NAME = "Voice Announcement"

DATA_INITIALIZED = "initialized"
DATA_STORE = "store"
DATA_FRONTEND_URL = "frontend_url"
DATA_FRONTEND_REGISTERED = "frontend_registered"
DATA_HTTP_REGISTERED = "http_registered"
DATA_STATIC_REGISTERED = "static_registered"
DATA_UPLOAD_SEMAPHORE = "upload_semaphore"
DATA_UPLOAD_RATE_LIMIT = "upload_rate_limit"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.recordings"

MEDIA_SOURCE_URI_PREFIX = f"media-source://{DOMAIN}"
MEDIA_URL_BASE = f"/api/{DOMAIN}/media"
UPLOAD_URL = f"/api/{DOMAIN}/upload"

STATIC_URL_BASE = f"/{DOMAIN}_static"
CARD_FILENAME = "voice-announcement-card.js"
CARD_URL = f"{STATIC_URL_BASE}/{CARD_FILENAME}"
WWW_DIR = Path(__file__).parent / "www"

DEFAULT_MAX_DURATION = 120
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_CONCURRENT_UPLOADS = 2
MAX_UPLOADS_PER_WINDOW = 10
UPLOAD_RATE_LIMIT_WINDOW_SECONDS = 60
MAX_FFPROBE_SECONDS = 10
MAX_FFMPEG_SECONDS = 30
AUTO_CLEANUP_KEEP_DAYS = 7
MAX_STORED_RECORDINGS = 100
MEDIA_BROWSE_LIMIT = 25
KEEP_ORIGINAL_UPLOADS = False
DEFAULT_OUTPUT_SAMPLE_RATE = "24000"
DEFAULT_OUTPUT_BITRATE = "64k"
DEFAULT_OUTPUT_CHANNELS = 1

SUPPORTED_MIME_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
}

MIME_TO_EXTENSION = {
    "audio/webm": "webm",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
}
