"""Frontend registration for Voice Announcement."""

from __future__ import annotations

import logging

from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    CARD_URL,
    DATA_FRONTEND_REGISTERED,
    DATA_FRONTEND_URL,
    DATA_STATIC_REGISTERED,
    DOMAIN,
    STATIC_URL_BASE,
    WWW_DIR,
)

_LOGGER = logging.getLogger(__name__)


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Expose the bundled custom card and load it globally."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    if not domain_data.get(DATA_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL_BASE, str(WWW_DIR), True)]
        )
        domain_data[DATA_STATIC_REGISTERED] = True
        _LOGGER.debug(
            "Registered Voice Announcement static frontend path at %s",
            STATIC_URL_BASE,
        )

    if not domain_data.get(DATA_FRONTEND_REGISTERED):
        # The version query string busts browser caches after every update.
        integration = await async_get_integration(hass, DOMAIN)
        module_url = f"{CARD_URL}?v={integration.version}"
        add_extra_js_url(hass, module_url)
        domain_data[DATA_FRONTEND_REGISTERED] = True
        domain_data[DATA_FRONTEND_URL] = module_url
        _LOGGER.info("Registered Voice Announcement frontend module at %s", module_url)


async def async_unregister_frontend(hass: HomeAssistant) -> None:
    """Unload the bundled card from the frontend module list."""
    domain_data = hass.data.get(DOMAIN, {})
    frontend_url = domain_data.get(DATA_FRONTEND_URL)
    if domain_data.get(DATA_FRONTEND_REGISTERED) and frontend_url:
        remove_extra_js_url(hass, frontend_url)
        domain_data[DATA_FRONTEND_REGISTERED] = False
        _LOGGER.info("Unregistered Voice Announcement frontend module at %s", frontend_url)
