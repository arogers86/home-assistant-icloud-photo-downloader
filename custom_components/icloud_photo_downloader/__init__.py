import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.discovery import async_load_platform

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the iCloud Photo Downloader component."""
    _LOGGER.debug("Setting up iCloud Photo Downloader component")
    
    if DOMAIN not in config:
        _LOGGER.debug("iCloud Photo Downloader not found in config")
        return True

    confs = config[DOMAIN]
    hass.data[DOMAIN] = {}

    for conf in confs:
        conf_id = conf["id"]
        hass.data[DOMAIN][conf_id] = {
            "token": conf["token"],
            "destination": conf["destination"],
            "ignore": conf["ignore"],
            "log_downloads": conf["log_downloads"],
            "last_downloaded": None,
            "downloaded_count": 0,
            "entities": [],
            "entity_name": conf["entity_name"]
        }

        _LOGGER.debug(f"iCloud Photo Downloader configuration {conf_id}: {hass.data[DOMAIN][conf_id]}")

    # Register the service
    async def handle_download_photos(service_call):
        _LOGGER.debug("Handling download photos service call")
        try:
            entity_id = service_call.data["entity_name"]
            entity_name = entity_id.split(".")[-1]  # Extract the name part after "image."

            # Find the corresponding configuration
            conf_id = None
            for cid, data in hass.data[DOMAIN].items():
                if data["entity_name"].replace(" ", "_").lower() == entity_name.lower():
                    conf_id = cid
                    break

            if not conf_id:
                _LOGGER.error(f"No configuration found for entity name: {entity_id}")
                return

            conf = hass.data[DOMAIN][conf_id]
            token = conf["token"]
            destination = conf["destination"]
            ignore = conf["ignore"]
            log_downloads = conf["log_downloads"]

            from .icloud_photo_downloader import download_photos
            await download_photos(hass, token, destination, ignore, log_downloads, conf_id, entity_name)

            # Notify state update
            for entity in conf["entities"]:
                _LOGGER.debug(f"Updating state for entity: {entity.name}")
                entity.async_write_ha_state()
        except KeyError as e:
            _LOGGER.error(f"Missing required service parameter: {e}")
        except Exception as e:
            _LOGGER.error(f"Exception during handle_download_photos: {e}")

    hass.services.async_register(DOMAIN, "download_photos", handle_download_photos)

    # Load the image platform
    for conf_id in hass.data[DOMAIN]:
        hass.async_create_task(async_load_platform(hass, "image", DOMAIN, {"conf_id": conf_id}, config))

    return True
