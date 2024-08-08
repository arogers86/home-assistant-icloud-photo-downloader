
# iCloud Photo Downloader for Home Assistant

![GitHub](https://img.shields.io/github/license/arogers86/home-assistant-icloud-photo-downloader)
![GitHub issues](https://img.shields.io/github/issues/arogers86/home-assistant-icloud-photo-downloader)

A custom Home Assistant integration to download and display photos from an iCloud shared album. This integration allows you to configure multiple photo download entities, each with unique settings, and display the latest downloaded photo as an image entity in Home Assistant.

## Features

- Download a single random photo from an iCloud shared album.
- Configure multiple entities with different settings.
- Display the latest downloaded photo in Home Assistant.
- Optional settings for ignoring previously downloaded photos and logging downloads.

## Installation

1. **Copy to Custom Components**
   - Copy the `icloud_photo_downloader` directory to your Home Assistant `custom_components` directory. The final path should look like this:
     ```
     <config directory>/custom_components/icloud_photo_downloader
     ```

2. **Restart Home Assistant**
   - Restart Home Assistant to load the new integration.

## Configuration

Add the `icloud_photo_downloader` integration to your `configuration.yaml` file. You can configure multiple instances, each with its own settings.

```yaml
icloud_photo_downloader:
  - id: "icloud_photo_downloader_1"
    token: "your_icould_shared_album_token"
    destination: "/config/www/images/icloud"
    ignore: 50
    log_downloads: 150
    entity_name: "iCloud Photo Downloader 1"
  - id: "icloud_photo_downloader_2"
    token: "your_other_icould_shared_album_token"
    destination: "/config/www/images/icloud"
    ignore: 100
    log_downloads: 200
    entity_name: "iCloud Photo Downloader 2"
```

- `id`: Unique identifier for this configuration.
- `token`: Your iCloud shared album token.
- `destination`: Path to save the downloaded photos.
- `ignore`: Number of previously downloaded photos to ignore (optional).
- `log_downloads`: Number of download logs to maintain (optional).
- `entity_name`: Friendly name for the image entity.

### Note on Token

The token is found at the end of the shared album URL after the `#` (and before any potential semicolon). The tokens seem to be 15 characters long.

e.g. https​://www​.icloud.com/sharedalbum/#`ABCdefG1237654`

## Usage

### Service Call

You can manually trigger the photo download using a service call in Home Assistant.

1. Go to Developer Tools > Services.
2. Select `icloud_photo_downloader.download_photos`.
3. Enter the `entity_name` of the photo downloader entity you want to trigger.

Example:
```yaml
service: icloud_photo_downloader.download_photos
data:
  entity_name: "iCloud Photo Downloader 1"
```

### Displaying the Photo

To display the downloaded photo in your Home Assistant dashboard, use the `picture-entity` card with the image entity created by the integration.

```yaml
type: picture-entity
entity: image.icloud_photo_downloader_1
name: Latest iCloud Photo
```

## Example Configuration

Here's a complete example including the configuration and a Lovelace card to display the downloaded photo.

### `configuration.yaml`

```yaml
icloud_photo_downloader:
  - id: "icloud_photo_downloader_1"
    token: "your_icould_shared_album_token"
    destination: "/config/www/images/icloud"
    ignore: 50
    log_downloads: 150
    entity_name: "iCloud Photo Downloader 1"
```

### Lovelace Configuration

```yaml
type: picture-entity
entity: image.icloud_photo_downloader_1
name: Latest iCloud Photo
```

## Debugging

If you encounter any issues, you can enable debug logging for more detailed output.

```yaml
logger:
  default: info
  logs:
    custom_components.icloud_photo_downloader: debug
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
