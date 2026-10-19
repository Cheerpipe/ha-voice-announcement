"""Config flow for Voice Announcement."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN, NAME


class VoiceAnnouncementConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Voice Announcement."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Create the single integration entry (single_config_entry in manifest)."""
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(step_id="user")
