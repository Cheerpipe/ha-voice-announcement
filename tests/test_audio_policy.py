"""Audio policy normalization tests."""

from custom_components.voice_announcement.audio_policy import (
    passthrough_allowed,
    resolve_audio_policy,
)


def test_defaults_for_unknown_input() -> None:
    """Garbage input resolves to the safe default policy."""
    policy = resolve_audio_policy({"transcoding": "sometimes", "output_profile": "nope"})
    assert policy["transcoding"] == "always"
    assert policy["output_profile"] == "default"
    assert policy["transcode_target"]["codec"] == "mp3"


def test_transcode_target_is_clamped() -> None:
    """Out-of-range targets are clamped to supported values."""
    policy = resolve_audio_policy(
        {
            "transcode_target": {
                "codec": "aac",
                "bitrate": "999k",
                "sample_rate": 96000,
                "channels": 6,
            }
        }
    )
    target = policy["transcode_target"]
    assert target["codec"] == "aac"
    assert target["mime_type"] == "audio/mp4"
    assert target["bitrate"] == "192k"
    assert target["sample_rate"] == "48000"
    assert target["channels"] == 2


def test_profile_passthrough_rules() -> None:
    """The Google profile accepts MP3 and AAC without conversion."""
    rules = resolve_audio_policy({"output_profile": "google_home"})["output_passthrough_rules"]
    assert passthrough_allowed("audio/mpeg", "mp3", rules)
    assert passthrough_allowed("audio/mp4", "aac", rules)
    assert not passthrough_allowed("audio/webm", "opus", rules)
