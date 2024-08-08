import logging
import os
import random
import json
import aiohttp
import aiofiles
from homeassistant.core import HomeAssistant
from datetime import datetime

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BASE_62_CHAR_SET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def base62_to_int(part: str) -> int:
    """
    Simple base 62 to integer computation
    """
    t = 0
    for c in part:
        t = t * 62 + BASE_62_CHAR_SET.index(c)
    return t

def get_partition(url_token: str):
    """
    Extract partition from url token.
    """
    partition = 0
    if 'A' == url_token[0]:
        partition = base62_to_int([url_token[1]])
    else:
        partition = base62_to_int(url_token[1:3])
    return partition

def get_url_location(item: dict) -> str:
    """
    Extracts URL location from a given item dictionary.
    """
    return item.get('url_location')

def get_url_path(item: dict) -> str:
    """
    Extracts URL path from a given item dictionary.
    """
    return item.get('url_path')

def get_download_url(item: dict) -> str:
    """
    Constructs the full download URL from item dictionary.
    """
    url_location = get_url_location(item)
    url_path = get_url_path(item)
    return f"https://{url_location}{url_path}"

def get_source_filename(url: str) -> str:
    """
    Extract the source filename from the URL path.
    """
    start_index = url.rindex('/') + 1
    end_index = url.index('?')
    return url[start_index:end_index]

def filter_best_assets(photos: list, asset_urls: dict):
    """
    Makes sure to check which of the derivatives of a photo has the highest quality.
    Lower quality image downloads will be omitted.
    """
    best_checksums = []
    for photo in photos:
        maxdim = 0
        best_derivative = None
        for _, derivative in photo.get('derivatives', {}).items():
            dim = int(derivative.get('width', '0')) * int(derivative.get('height', '0'))
            if dim > maxdim:
                maxdim = dim
                best_derivative = derivative
        if best_derivative:
            best_checksums.append(best_derivative.get('checksum'))

    result = {}
    for checksum in best_checksums:
        if checksum in asset_urls:
            result[checksum] = asset_urls[checksum]
    return result

async def get_stream(session: aiohttp.ClientSession, host: str, token: str, retries: int = 3):
    """
    Download web stream of available photos.
    """
    url = f"https://{host}/{token}/sharedstreams/webstream"
    attempt = 0
    while attempt < retries:
        try:
            async with session.post(url, json={'streamCtag': 'null'}) as response:
                _LOGGER.debug(f"Response status: {response.status}")
                if response.status == 330:
                    redirect_data = await response.json()
                    _LOGGER.debug(f"Redirect data: {redirect_data}")
                    new_host = redirect_data.get("X-Apple-MMe-Host")
                    return await get_stream(session, new_host, token)
                elif response.status == 200:
                    data = await response.json()
                    photos = data.get('photos')
                    asset_urls = await get_asset_urls(session, host, token, [photo['photoGuid'] for photo in photos])
                    return filter_best_assets(photos, asset_urls.get('items', []))
                else:
                    raise ValueError("Received an unexpected response from the server.")
        except Exception as e:
            _LOGGER.error(f"Exception during get_stream: {e}")
            attempt += 1
            if attempt == retries:
                raise e

async def get_asset_urls(session: aiohttp.ClientSession, host: str, token: str, photoGuids: list):
    """
    Get precise asset URLs based on a list of photo GUIDs.
    """
    url = f"https://{host}/{token}/sharedstreams/webasseturls"
    async with session.post(url, json={'photoGuids': photoGuids}) as response:
        _LOGGER.debug(f"Asset URLs response status: {response.status}")
        if response.status == 200:
            return await response.json()
        else:
            raise ValueError("Received an unexpected response from the server.")

async def download_file(session: aiohttp.ClientSession, url: str, directory: str, filename: str):
    """
    Download a single photo from the given URL to the specified directory.
    """
    async with session.get(url) as response:
        _LOGGER.debug(f"Download file response status: {response.status}")
        if response.status != 200:
            _LOGGER.error("Failed to download a photo.")
            _LOGGER.debug(f"Status code: {response.status} (for URL: {url})")
        else:
            output_file = os.path.join(directory, filename)
            async with aiofiles.open(output_file, 'wb') as f:
                await f.write(await response.read())
            _LOGGER.debug(f"File downloaded to: {output_file}")
    return output_file

def select_random_photo(data, ignore_list):
    """
    Select a single random photo that is not in the ignore list.
    """
    available_photos = [guid for guid in data.keys() if guid not in ignore_list]
    _LOGGER.debug(f"Available photos count: {len(available_photos)}")
    if not available_photos:
        raise ValueError("No new photos available to download.")
    return random.choice(available_photos)

async def download_photos(hass: HomeAssistant, token: str, destination: str, ignore: int, log_downloads: int, conf_id: str, entity_name: str):
    """Download a single photo from iCloud shared album."""
    _LOGGER.debug("Starting photo download process")
    partition = get_partition(token)
    host = f"p{partition}-sharedstreams.icloud.com"
    _LOGGER.debug(f"Host: {host}")

    async with aiohttp.ClientSession() as session:
        try:
            data = await get_stream(session, host, token)
            _LOGGER.debug(f"Fetched data: {data}")
        except ValueError as e:
            _LOGGER.error("Could not retrieve item stream!")
            _LOGGER.exception(e)
            return

        if not os.path.exists(destination):
            os.makedirs(destination)
        if not os.path.isdir(destination):
            _LOGGER.error("Destination directory does not exist!")
            return

        log_file = os.path.join(destination, f'{conf_id}_log.txt')
        image_file = f'{conf_id}.jpg'
        log_entries = []

        if os.path.exists(log_file):
            async with aiofiles.open(log_file, 'r') as f:
                log_content = await f.read()
                log_entries = log_content.splitlines()
            _LOGGER.debug(f"Log entries: {log_entries}")

        ignore_list = []
        if ignore:
            ignore_list = [entry.split(':')[0] for entry in log_entries[-ignore:]]
            _LOGGER.debug(f"Ignore list: {ignore_list}")

        last_filename = None
        if data:
            try:
                photo_guid = select_random_photo(data, ignore_list)
                _LOGGER.debug(f"Selected photo GUID: {photo_guid}")
                item = data[photo_guid]
                url = get_download_url(item)
                source_filename = get_source_filename(url)
                _LOGGER.debug(f"Downloading photo GUID {photo_guid}: {url}")

                last_filename = image_file

                await download_file(session, url, destination, image_file)
                log_entries.append(f"{photo_guid}:{source_filename}")
                if ignore and len(log_entries) > ignore:
                    log_entries.pop(0)
                elif log_downloads and len(log_entries) > log_downloads:
                    log_entries.pop(0)
            except ValueError as e:
                _LOGGER.error(e)
        else:
            _LOGGER.error("No photos available to download.")

        async with aiofiles.open(log_file, 'w') as f:
            await f.write('\n'.join(log_entries))
            _LOGGER.debug(f"Log entries saved to: {log_file}")

        for conf in hass.data[DOMAIN].values():
            if conf["entity_name"].replace(" ", "_").lower() == entity_name.lower():
                conf["last_downloaded"] = last_filename if data else None
                conf["downloaded_count"] += 1
                conf["last_download_timestamp"] = datetime.now().isoformat() if data else None
                break

        # Notify state update
        for conf in hass.data[DOMAIN].values():
            if conf["entity_name"].replace(" ", "_").lower() == entity_name.lower():
                for entity in conf["entities"]:
                    _LOGGER.debug(f"Updating state for entity: {entity.name}")
                    entity.async_write_ha_state()

        _LOGGER.debug(f"Download complete. Last downloaded: {last_filename}")
