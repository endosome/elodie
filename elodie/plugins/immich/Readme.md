# Immich Plugin

This plugin keeps albums and favorites in sync between your Elodie library and [Immich](https://immich.app), which shows the library as an [external library](https://docs.immich.app/guides/external-library). You can organize your photos in Immich's UI while:

* all albums and favorites are **stored in the photos themselves**,
* Elodie remains the **organizer of your folders**,
* moving files does not lose their albums or favorites in Immich.

## Requirements

* Immich 3.2 or later.
* The Elodie library added to Immich as an external library.
* The requirements of the plugin:

```bash
pip install -r elodie/plugins/immich/requirements.txt
```

## Configuration

Add the following to your `config.ini` file:

```ini
[Plugins]
plugins=Immich

[PluginImmich]
api_url=https://immich.example.com/api
api_key=your_immich_api_key
external_library_path=/path/to/your/library/in/immich
```

* **api_url**: The API URL of Immich, it ends with `/api`.
* **api_key**: An [API key](https://docs.immich.app/features/command-line-interface#obtain-the-api-key) of the Immich user who owns the external library. It needs these permissions: `album.read`, `album.create`, `albumAsset.create`, `albumAsset.delete`, `asset.read` and `asset.update`.
* **external_library_path**: The folder of your Elodie library as Immich sees it, the import path of the external library.
* **elodie_library_path** (optional): The folder of your Elodie library as Elodie sees it. It's only needed when it differs from `external_library_path`, i.e. when Immich runs in Docker or on another computer. For example `external_library_path=/mnt/photos` and `elodie_library_path=/home/me/photos`.
* **timeout** (optional): Seconds to wait for a response of Immich, 30 by default.

## Usage

Run the sync whenever you like, i.e. with cron:

```bash
./elodie.py batch
```

Add `--dry-run` to see what would change without changing anything, and `--debug` for details.

Immich only notices new and moved files when it scans the external library. Set up a scan schedule or enable watching the library for changes in Immich's settings. Files which Immich did not scan yet are synced by a later run.

## How it works

Each run compares three states of every photo: the one Elodie and Immich had after the last run, the photo now and Immich now.

* **Changed in Immich**: the change is written to the photo. When an album changes, Elodie moves the photo to the folder of its album, like `elodie.py update --album` does.
* **Changed in the photo**, i.e. with `elodie.py update` or when importing: the change is applied in Immich.
* **Changed on both sides**: the album changes of both sides are kept and Immich wins for the favorite.
* **A photo seen for the first time**, including every photo on the first run and every moved photo: the albums and favorites of both sides are kept.

Immich sees a moved file as a new photo. Since its albums and favorite are stored in the photo, they are restored in Immich on the next run after Immich scanned it.

A photo is only read again when its file changed since the last run, so runs on large libraries are fast after the first one. A long first run can be stopped, the next run continues where it stopped.

### Albums

Albums are stored in `XMP-xmpDM:Album`, the album Elodie uses. Immich lets a photo be in several albums, they are stored separated by `;`, i.e. `Summer;Family`. That's also the name of the folder when your folders include the album.

Album names containing `;` can't be stored and are not synced. Immich albums with the same name are one album for the plugin, photos are added to the oldest one.

### Favorites

A favorite in Immich is a rating of 5 in the photo (`XMP:Rating`). Removing the favorite removes the rating.

## Limitations

* Only albums and favorites are synced. Immich reads descriptions, locations and dates from the photos when it scans them.
* When you change the album of a photo with Elodie before a run synced a change made in Immich, the change made in Immich is lost. Run `./elodie.py batch` before updating photos with Elodie.
* Only photos and videos in the external library are synced, not the ones uploaded to Immich.
