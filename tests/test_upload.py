"""Upload, media and service tests."""

from __future__ import annotations

import json

import aiohttp
from homeassistant.components.media_source import async_resolve_media
import pytest

from custom_components.voice_announcement.const import DATA_STORE, DOMAIN, UPLOAD_URL


def _form(audio: bytes, entity_id: str, **fields: str) -> aiohttp.FormData:
    form = aiohttp.FormData()
    form.add_field("file", audio, filename="announcement.wav", content_type="audio/wav")
    form.add_field("entity_id", entity_id)
    form.add_field("mime_type", "audio/wav")
    form.add_field("duration", "1")
    for name, value in fields.items():
        form.add_field(name, value)
    return form


async def test_upload_transcodes_and_serves_media(
    hass, hass_client, setup_integration, wav_bytes
) -> None:
    """A WAV upload is converted to MP3 and becomes playable."""
    client = await hass_client()
    response = await client.post(UPLOAD_URL, data=_form(wav_bytes, "media_player.kitchen"))
    assert response.status == 200, await response.text()
    body = await response.json()
    assert body["mime_type"] == "audio/mpeg"
    assert body["was_transcoded"] is True

    media = await client.get(body["url"])
    assert media.status == 200
    assert media.headers["Content-Type"] == "audio/mpeg"
    assert (await media.read())[:3] in (b"ID3", b"\xff\xf3", b"\xff\xfb")

    resolved = await async_resolve_media(hass, body["media_source_id"], None)
    assert resolved.mime_type == "audio/mpeg"
    assert resolved.path is not None


async def test_upload_accepts_several_speakers(hass_client, setup_integration, wav_bytes) -> None:
    """A comma-separated target list is accepted and de-duplicated."""
    client = await hass_client()
    targets = "media_player.kitchen, media_player.office,media_player.kitchen"
    response = await client.post(UPLOAD_URL, data=_form(wav_bytes, targets))
    assert response.status == 200, await response.text()


async def test_auto_mode_passes_supported_formats_through(
    hass_client, setup_integration, wav_bytes
) -> None:
    """Passthrough rules let a matching upload skip ffmpeg."""
    policy = {"transcoding": "auto", "output_passthrough_rules": [{"mime_type": "audio/wav"}]}
    client = await hass_client()
    response = await client.post(
        UPLOAD_URL,
        data=_form(wav_bytes, "media_player.kitchen", audio_policy=json.dumps(policy)),
    )
    assert response.status == 200, await response.text()
    body = await response.json()
    assert body["was_transcoded"] is False
    assert body["mime_type"] == "audio/wav"


@pytest.mark.parametrize(
    "entity_id",
    ["", ",", "light.kitchen", "media_player.kitchen,switch.fan", "media_player.Bad Id"],
)
async def test_upload_rejects_invalid_targets(
    hass_client, setup_integration, wav_bytes, entity_id
) -> None:
    """Targets must be one or more valid media_player entity ids."""
    client = await hass_client()
    response = await client.post(UPLOAD_URL, data=_form(wav_bytes, entity_id))
    assert response.status == 400


async def test_upload_rejects_non_audio(hass_client, setup_integration) -> None:
    """Files that are not audio are refused and leave nothing behind."""
    client = await hass_client()
    response = await client.post(UPLOAD_URL, data=_form(b"not audio at all", "media_player.x"))
    assert response.status == 415


async def test_upload_requires_authentication(hass, hass_client_no_auth, setup_integration) -> None:
    """Anonymous uploads are refused."""
    client = await hass_client_no_auth()
    response = await client.post(UPLOAD_URL, data=_form(b"x", "media_player.x"))
    assert response.status == 401


async def test_delete_service_removes_recording(
    hass, hass_client, setup_integration, wav_bytes
) -> None:
    """The delete_recording service removes metadata and files."""
    client = await hass_client()
    body = await (await client.post(UPLOAD_URL, data=_form(wav_bytes, "media_player.x"))).json()
    store = hass.data[DOMAIN][DATA_STORE]
    media_file = store.get_media_file(body["recording_id"])
    assert media_file is not None

    await hass.services.async_call(
        DOMAIN, "delete_recording", {"recording_id": body["recording_id"]}, blocking=True
    )
    assert store.get(body["recording_id"]) is None
    assert not media_file.exists()
    assert (await client.get(body["url"])).status == 404


async def test_unload_entry(hass, setup_integration) -> None:
    """The entry unloads and removes its services."""
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert not hass.services.has_service(DOMAIN, "cleanup")
