"""Entity, activity and play service tests."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import patch

import aiohttp
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.voice_announcement import upload as upload_module
from custom_components.voice_announcement.const import (
    DATA_ACTIVITY,
    DOMAIN,
    EVENT_PLAYBACK_FINISHED,
    EVENT_PLAYBACK_STARTED,
    EVENT_RECORDED,
    EVENT_UPLOAD_FAILED,
    PLAYBACK_GRACE_SECONDS,
    UPLOAD_URL,
)
from custom_components.voice_announcement.diagnostics import (
    async_get_config_entry_diagnostics,
)

STATUS = "sensor.voice_announcement_status"
PLAYING = "binary_sensor.voice_announcement_playing"
KITCHEN_PLAYING = "binary_sensor.voice_announcement_playing_on_kitchen"


def _form(audio: bytes, entity_id: str) -> aiohttp.FormData:
    form = aiohttp.FormData()
    form.add_field("entity_id", entity_id)
    form.add_field("file", audio, filename="announcement.wav", content_type="audio/wav")
    form.add_field("mime_type", "audio/wav")
    form.add_field("duration", "1")
    return form


@pytest.fixture
def kitchen(hass):
    """A media player that supports announce mode."""
    hass.states.async_set(
        "media_player.kitchen",
        "idle",
        {
            "friendly_name": "Kitchen",
            "supported_features": MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.MEDIA_ANNOUNCE,
        },
    )


async def _upload(hass_client, wav_bytes, target="media_player.kitchen") -> dict:
    client = await hass_client()
    response = await client.post(UPLOAD_URL, data=_form(wav_bytes, target))
    assert response.status == 200, await response.text()
    return await response.json()


async def test_entities_start_idle(hass, setup_integration) -> None:
    """The device starts idle with ffmpeg detected."""
    assert hass.states.get(STATUS).state == "idle"
    assert hass.states.get(PLAYING).state == "off"
    assert hass.states.get("binary_sensor.voice_announcement_receiving").state == "off"
    assert hass.states.get("binary_sensor.voice_announcement_processing").state == "off"
    assert hass.states.get("binary_sensor.voice_announcement_ffmpeg").state == "off"
    assert hass.states.get("binary_sensor.voice_announcement_ffprobe").state == "off"
    assert hass.states.get("sensor.voice_announcement_stored_recordings").state == "0"
    assert hass.states.get("sensor.voice_announcement_recordings_today").state == "0"
    assert hass.states.get("button.voice_announcement_delete_last_recording").state == (
        "unavailable"
    )


async def test_missing_ffmpeg_is_reported(hass, setup_integration) -> None:
    """The problem sensor turns on when ffmpeg disappears."""
    with patch("custom_components.voice_announcement.activity.find_ffmpeg", return_value=None):
        hass.data[DOMAIN][DATA_ACTIVITY].check_tools()
        await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.voice_announcement_ffmpeg").state == "on"


async def test_upload_updates_recording_entities(
    hass, hass_client, setup_integration, wav_bytes
) -> None:
    """A successful upload updates the recording sensors and fires events."""
    recorded = async_capture_events(hass, EVENT_RECORDED)
    body = await _upload(hass_client, wav_bytes, "media_player.kitchen,media_player.office")
    await hass.async_block_till_done()

    last = hass.states.get("sensor.voice_announcement_last_recording")
    assert last.attributes["recording_id"] == body["recording_id"]
    assert last.attributes["targets"] == ["media_player.kitchen", "media_player.office"]
    assert last.attributes["media_source_id"] == body["media_source_id"]
    duration = hass.states.get("sensor.voice_announcement_last_recording_duration")
    assert float(duration.state) == pytest.approx(1, abs=0.1)
    assert hass.states.get("sensor.voice_announcement_recordings_today").state == "1"
    assert hass.states.get("sensor.voice_announcement_stored_recordings").state == "1"
    assert hass.states.get("sensor.voice_announcement_transcoded_uploads").state == "100.0"
    assert hass.states.get("sensor.voice_announcement_last_upload_status").state == "ok"
    assert int(hass.states.get("sensor.voice_announcement_storage_used").state.split(".")[0]) >= 0
    timings = hass.states.get("sensor.voice_announcement_last_processing_time")
    assert "probe_ms" in timings.attributes
    event = hass.states.get("event.voice_announcement_recording")
    assert event.attributes["event_type"] == "recorded"
    assert event.attributes["recording_id"] == body["recording_id"]

    assert len(recorded) == 1
    assert recorded[0].data["targets"] == ["media_player.kitchen", "media_player.office"]
    assert hass.states.get(STATUS).state == "idle"


async def test_failed_upload_is_reported(hass, hass_client, setup_integration) -> None:
    """A rejected upload shows its reason and counts as failed."""
    failed = async_capture_events(hass, EVENT_UPLOAD_FAILED)
    client = await hass_client()
    response = await client.post(UPLOAD_URL, data=_form(b"not audio", "media_player.kitchen"))
    assert response.status == 415
    await hass.async_block_till_done()

    status = hass.states.get("sensor.voice_announcement_last_upload_status")
    assert status.state == "invalid_audio"
    assert status.attributes["http_status"] == 415
    assert status.attributes["targets"] == ["media_player.kitchen"]
    assert hass.states.get("sensor.voice_announcement_failed_uploads").state == "1"
    assert hass.states.get("event.voice_announcement_recording").attributes["event_type"] == (
        "failed"
    )
    assert failed[0].data["status"] == "invalid_audio"
    assert hass.states.get(STATUS).state == "idle"


async def test_processing_phase_shows_targets(
    hass, hass_client, setup_integration, wav_bytes
) -> None:
    """While an upload is converted, the status says where it is going."""
    release = asyncio.Event()
    probing = asyncio.Event()
    real_probe = upload_module.async_probe_audio

    async def slow_probe(path):
        probing.set()
        await release.wait()
        return await real_probe(path)

    client = await hass_client()
    with patch.object(upload_module, "async_probe_audio", slow_probe):
        request = asyncio.ensure_future(
            client.post(UPLOAD_URL, data=_form(wav_bytes, "media_player.kitchen"))
        )
        await probing.wait()
        await hass.async_block_till_done()

        status = hass.states.get(STATUS)
        assert status.state == "processing"
        assert status.attributes["targets"] == ["media_player.kitchen"]
        assert hass.states.get("binary_sensor.voice_announcement_processing").state == "on"
        assert hass.states.get("sensor.voice_announcement_active_uploads").state == "1"

        release.set()
        response = await request
    assert response.status == 200
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "idle"


async def test_play_tracks_speaker_until_it_stops(
    hass, hass_client, setup_integration, wav_bytes, kitchen
) -> None:
    """Playing a recording turns the speaker sensor on until the speaker stops."""
    calls = async_mock_service(hass, "media_player", "play_media")
    started = async_capture_events(hass, EVENT_PLAYBACK_STARTED)
    finished = async_capture_events(hass, EVENT_PLAYBACK_FINISHED)
    body = await _upload(hass_client, wav_bytes)

    response = await hass.services.async_call(
        DOMAIN,
        "play",
        {"entity_id": "media_player.kitchen", "recording_id": "last"},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response["recording_id"] == body["recording_id"]
    assert calls[0].data["media_content_id"] == body["media_source_id"]
    assert calls[0].data["announce"] is True
    assert started[0].data["targets"] == ["media_player.kitchen"]
    assert hass.states.get(STATUS).state == "playing"
    assert hass.states.get(PLAYING).state == "on"
    speaker = hass.states.get(KITCHEN_PLAYING)
    assert speaker.state == "on"
    assert speaker.attributes["recording_id"] == body["recording_id"]
    assert hass.states.get("event.voice_announcement_announcement").attributes["event_type"] == (
        "started"
    )

    content = f"/api/voice_announcement/media/{body['recording_id']}.mp3"
    hass.states.async_set("media_player.kitchen", "playing", {"media_content_id": content})
    await hass.async_block_till_done()
    assert hass.states.get(KITCHEN_PLAYING).state == "on"
    hass.states.async_set("media_player.kitchen", "idle")
    await hass.async_block_till_done()

    assert hass.states.get(KITCHEN_PLAYING).state == "off"
    assert hass.states.get(STATUS).state == "idle"
    last = hass.states.get("sensor.voice_announcement_last_announcement")
    assert last.attributes["result"] == "ok"
    assert last.attributes["end_reason"] == "speaker_stopped"
    assert finished[0].data["result"] == "ok"


async def test_play_ends_after_expected_duration(hass, setup_integration, kitchen) -> None:
    """Speakers that report nothing finish once the message length has passed."""
    async_mock_service(hass, "media_player", "play_media")
    await hass.services.async_call(
        DOMAIN,
        "play",
        {
            "entity_id": "media_player.kitchen",
            "message": "Dinner is ready",
            "tts_engine": "tts.cloud",
            "language": "en-US",
            "announce": False,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(KITCHEN_PLAYING).state == "on"
    status = hass.states.get(STATUS)
    assert status.attributes["type"] == "tts"

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=PLAYBACK_GRACE_SECONDS + 5))
    await hass.async_block_till_done()
    assert hass.states.get(KITCHEN_PLAYING).state == "off"
    last = hass.states.get("sensor.voice_announcement_last_announcement")
    assert last.attributes["end_reason"] == "expected_end"
    assert last.attributes["message"] == "Dinner is ready"


async def test_play_builds_tts_media_id(hass, setup_integration, kitchen) -> None:
    """Text messages use the text-to-speech media source and skip announce when off."""
    calls = async_mock_service(hass, "media_player", "play_media")
    await hass.services.async_call(
        DOMAIN,
        "play",
        {
            "entity_id": "media_player.kitchen",
            "message": "Hola a todos",
            "tts_engine": "tts.cloud",
            "language": "es-ES",
            "voice": "Elvira",
            "announce": False,
        },
        blocking=True,
    )
    assert calls[0].data["media_content_id"] == (
        "media-source://tts/tts.cloud?message=Hola%20a%20todos&cache=true"
        "&language=es-ES&tts_options=%7B%22voice%22%3A%22Elvira%22%7D"
    )
    assert "announce" not in calls[0].data


async def test_play_failure_is_counted(hass, setup_integration, kitchen) -> None:
    """A speaker that refuses to play raises and counts as a failed playback."""

    async def refuse(call: ServiceCall) -> None:
        raise HomeAssistantError("speaker offline")

    hass.services.async_register("media_player", "play_media", refuse)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "play",
            {"entity_id": "media_player.kitchen", "message": "Hi", "tts_engine": "tts.cloud"},
            blocking=True,
        )
    await hass.async_block_till_done()

    failed = hass.states.get("sensor.voice_announcement_failed_playbacks")
    assert failed.state == "1"
    assert failed.attributes["error"] == "speaker offline"
    assert hass.states.get(KITCHEN_PLAYING).state == "off"
    assert hass.states.get("sensor.voice_announcement_last_announcement").attributes["result"] == (
        "failed"
    )
    assert hass.states.get("event.voice_announcement_announcement").attributes["event_type"] == (
        "failed"
    )


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"entity_id": "media_player.kitchen", "message": "Hi"}, "tts_engine_required"),
        ({"entity_id": "media_player.kitchen", "recording_id": "missing"}, "recording_not_found"),
        ({"entity_id": "light.kitchen", "recording_id": "last"}, "no_targets"),
    ],
)
async def test_play_validation(hass, setup_integration, data, error) -> None:
    """Invalid play requests are refused with a translated error."""
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(DOMAIN, "play", data, blocking=True)
    assert err.value.translation_key == error


async def test_buttons_delete_and_clean_up(hass, hass_client, setup_integration, wav_bytes) -> None:
    """The buttons delete the newest recording and record a cleanup."""
    await _upload(hass_client, wav_bytes)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.voice_announcement_delete_last_recording"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.voice_announcement_stored_recordings").state == "0"
    assert hass.states.get("event.voice_announcement_recording").attributes["event_type"] == (
        "deleted"
    )

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.voice_announcement_clean_up_old_recordings"},
        blocking=True,
    )
    await hass.async_block_till_done()
    cleanup = hass.states.get("sensor.voice_announcement_last_cleanup")
    assert cleanup.attributes["trigger"] == "button"
    assert cleanup.attributes["deleted"] == 0


async def test_speaker_sensor_survives_reload(hass, setup_integration, kitchen) -> None:
    """Speakers are remembered, so their sensor comes back after a reload."""
    async_mock_service(hass, "media_player", "play_media")
    await hass.services.async_call(
        DOMAIN,
        "play",
        {"entity_id": "media_player.kitchen", "message": "Hi", "tts_engine": "tts.cloud"},
        blocking=True,
    )
    assert await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(KITCHEN_PLAYING).state == "off"


async def test_diagnostics(hass, hass_client, setup_integration, wav_bytes) -> None:
    """Diagnostics include tools, limits and the last upload without user names."""
    await _upload(hass_client, wav_bytes)
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diagnostics["recordings"] == 1
    assert diagnostics["tools"]["ffmpeg"]
    assert diagnostics["last_upload"]["status"] == "ok"
    assert "user" not in diagnostics["last_upload"]
    assert diagnostics["limits"]["max_stored_recordings"] == 100
