"""Shared fixtures for Voice Announcement tests."""

from __future__ import annotations

import io
import math
import struct
import wave

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voice_announcement.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load the integration from custom_components."""
    return


@pytest.fixture
async def setup_integration(hass):
    """Set up the integration through a config entry."""
    entry = MockConfigEntry(domain=DOMAIN, title="Voice Announcement")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
def wav_bytes() -> bytes:
    """Return one second of a 440 Hz mono tone as WAV."""
    rate = 16000
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
                for i in range(rate)
            )
        )
    return buffer.getvalue()
