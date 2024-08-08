import logging
import os
import aiofiles
from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None):
    """Set up the image platform."""
    _LOGGER.debug("Setting up iCloud Photo Downloader image platform")
    
    if discovery_info is None:
        _LOGGER.debug("No discovery info for image platform")
        return

    conf_id = discovery_info["conf_id"]
    conf = hass.data[DOMAIN][conf_id]

    entity = ICloudPhotoDownloaderImage(hass, conf["entity_name"], conf_id)
    async_add_entities([entity], True)
    
    if "entities" not in conf:
        conf["entities"] = []
    conf["entities"].append(entity)
    _LOGGER.debug(f"Image entity registered: {entity.name}")

class ICloudPhotoDownloaderImage(ImageEntity):
    """Representation of an iCloud Photo Downloader image."""

    def __init__(self, hass, name, conf_id):
        """Initialize the image entity."""
        self.hass = hass
        self._name = name
        self._conf_id = conf_id
        self._access_tokens = [self._generate_access_token()]
        _LOGGER.debug(f"Initialized iCloud Photo Downloader image with name: {name}")

    @property
    def name(self):
        """Return the name of the image."""
        return self._name

    @property
    def state(self):
        """Return the state of the image."""
        conf = self.hass.data[DOMAIN][self._conf_id]
        return conf.get("last_downloaded", "Unknown")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        conf = self.hass.data[DOMAIN][self._conf_id]
        return {
            "last_downloaded": conf.get("last_downloaded"),
            "downloaded_count": conf.get("downloaded_count"),
            "last_download_timestamp": conf.get("last_download_timestamp")
        }

    @property
    def access_tokens(self):
        """Return the list of access tokens."""
        return self._access_tokens

    async def async_image(self):
        """Return the image bytes."""
        conf = self.hass.data[DOMAIN][self._conf_id]
        last_downloaded = conf.get("last_downloaded")
        if not last_downloaded:
            return None
        
        destination = conf.get("destination")
        if not destination:
            return None

        image_path = os.path.join(destination, last_downloaded)
        
        if not os.path.exists(image_path):
            _LOGGER.error(f"Image file not found: {image_path}")
            return None

        async with aiofiles.open(image_path, 'rb') as image_file:
            return await image_file.read()

    def _generate_access_token(self):
        """Generate a new access token."""
        from secrets import token_hex
        return token_hex(16)

    async def async_generate_access_token(self):
        """Generate and return a new access token."""
        new_token = self._generate_access_token()
        self._access_tokens.append(new_token)
        self.async_write_ha_state()
        _LOGGER.debug("Generated new access token and updated state")
        return new_token

    def async_write_ha_state(self):
        """Update the state of the entity."""
        _LOGGER.debug(f"Updating state for image entity: {self.name}")
        super().async_write_ha_state()
