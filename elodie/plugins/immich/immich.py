"""
Immich plugin which keeps albums and favorites in sync between an Elodie
library and Immich, which reads the library as an external library.

- Albums and favorites changed in Immich are written to the files, which
  Elodie then organizes, i.e. moves to the folder of their album.
- Albums and favorites stored in the files, i.e. set with ``elodie.py update``
  or when importing, are applied in Immich.

Each run compares three states of every asset: the one both sides had after
the last run, the file now and Immich now. A change on one side is applied to
the other one. When both changed, albums are merged and Immich wins for the
favorite. A file is only read again when it changed since the last run.

Requires Immich 3.2 or later.

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""

import os
import time

import requests

from elodie import constants
from elodie.filesystem import FileSystem
from elodie.media.base import Base
from elodie.media.photo import Photo
from elodie.media.video import Video
from elodie.plugins.plugins import PluginBase

#: Oldest Immich version with the search filters this plugin uses.
MINIMUM_IMMICH_VERSION = (3, 2, 0)

#: A rating of 5 in the file is a favorite in Immich.
FAVORITE_RATING = 5

#: Multiple albums are stored in the file separated by it, i.e. "A;B".
ALBUM_SEPARATOR = ';'

#: Immich has photos and videos.
MEDIA_CLASSES = (Photo, Video)


def is_album_name_storable(name):
    """Check if an album name can be stored in a file. Elodie uses it as a
    folder name, it must not be a path, i.e. "../Trip" or "2024/Trip".
    """
    return (name == name.strip() and name not in ('', '.', '..') and
            ALBUM_SEPARATOR not in name and
            '/' not in name and '\\' not in name)


class ImmichError(Exception):
    """A request to Immich failed."""
    pass


class ImmichApiClient(object):
    """Client for the parts of the Immich API this plugin uses.

    Failed requests are retried when Immich is busy (HTTP 429) or temporarily
    unavailable (HTTP 5xx, connection errors). Methods which change something
    only print what they would do in dry-run mode.
    """

    RETRY_STATUS = (429, 500, 502, 503, 504)
    #: Number of results per page when searching, the maximum of Immich.
    PAGE_SIZE = 1000
    #: Number of assets per request when changing many assets at once.
    CHUNK_SIZE = 500

    def __init__(self, api_url, api_key, timeout=30, retries=4, backoff=1.0):
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': api_key,
            'Accept': 'application/json',
        })

    def _request(self, method, endpoint, retry=True, **kwargs):
        """Make a request and return its decoded JSON response.

        :param bool retry: Retry on errors which may be temporary. Disable it
            for requests which must not be repeated, i.e. creating an album.
        :raises ImmichError: when the request failed.
        """
        url = self.api_url + endpoint
        kwargs.setdefault('timeout', self.timeout)
        attempts = self.retries + 1 if retry else 1
        for attempt in range(attempts):
            last_attempt = attempt == attempts - 1
            try:
                response = self.session.request(method, url, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as e:
                if last_attempt:
                    raise ImmichError('{} {} failed: {}'.format(
                        method, endpoint, e))
                delay = self.backoff * 2 ** attempt
            else:
                if response.status_code < 400:
                    return self._decode(response, method, endpoint)
                if response.status_code == 406:
                    # The web app of Immich for a JSON request
                    raise self._not_the_api(method, endpoint)
                if (response.status_code not in self.RETRY_STATUS or
                        last_attempt):
                    raise ImmichError('{} {} failed: HTTP {} {}'.format(
                        method, endpoint, response.status_code,
                        response.text[:200]))
                delay = self._retry_after(response, attempt)
            time.sleep(delay)

    def _decode(self, response, method, endpoint):
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            # i.e. the web app of Immich which answers with HTML
            raise self._not_the_api(method, endpoint)

    def _not_the_api(self, method, endpoint):
        return ImmichError(
            '{} {} failed: not a response of the Immich API, api_url must '
            'end with /api'.format(method, endpoint))

    def _retry_after(self, response, attempt):
        try:
            return float(response.headers['Retry-After'])
        except (KeyError, ValueError):
            return self.backoff * 2 ** attempt

    def get_version(self):
        """Get the version of the Immich server.

        :returns: tuple of (major, minor, patch)
        """
        version = self._request('GET', '/server/version')
        return (version['major'], version['minor'], version['patch'])

    def get_my_user_id(self):
        """Get the ID of the user of the API key."""
        return self._request('GET', '/users/me')['id']

    def get_albums(self, owned=False, asset_id=None):
        """Get the albums the user can see.

        :param bool owned: Only the albums of the user, not the ones other
            users share with them.
        :param str asset_id: Only the albums which contain the asset.
        """
        params = {}
        if owned:
            params['isOwned'] = 'true'
        if asset_id:
            params['assetId'] = asset_id
        return self._request('GET', '/albums', params=params)

    def create_album(self, name):
        """Create an album.

        :returns: dict of the album
        """
        if constants.dry_run:
            print('[DRY-RUN][Immich] Would create album: {}'.format(name))
            return {'id': 'dry-run-album-id', 'albumName': name}
        # Not retried, a request which timed out may have created it.
        return self._request('POST', '/albums', retry=False,
                             json={'albumName': name})

    def add_assets_to_album(self, album_id, asset_ids):
        """Add assets to an album.

        :returns: set of the asset IDs which could not be added
        """
        if constants.dry_run:
            print('[DRY-RUN][Immich] Would add {} assets to album {}'.format(
                len(asset_ids), album_id))
            return set()
        return self._change_album(
            'PUT', album_id, asset_ids, ignore_error='duplicate')

    def remove_assets_from_album(self, album_id, asset_ids):
        """Remove assets from an album.

        :returns: set of the asset IDs which could not be removed
        """
        if constants.dry_run:
            print('[DRY-RUN][Immich] Would remove {} assets from album '
                  '{}'.format(len(asset_ids), album_id))
            return set()
        return self._change_album(
            'DELETE', album_id, asset_ids, ignore_error='not_found')

    def _change_album(self, method, album_id, asset_ids, ignore_error):
        failed = set()
        asset_ids = sorted(asset_ids)
        for start in range(0, len(asset_ids), self.CHUNK_SIZE):
            chunk = asset_ids[start:start + self.CHUNK_SIZE]
            results = self._request(
                method, '/albums/{}/assets'.format(album_id),
                json={'ids': chunk})
            for result in results or []:
                # Adding an asset which is in the album already is a
                #  "duplicate", removing one which is not a "not_found".
                if not result.get('success') and \
                        result.get('error') != ignore_error:
                    failed.add(result.get('id'))
        return failed

    def set_favorite(self, asset_ids, is_favorite):
        """Set or clear the favorite of assets."""
        if constants.dry_run:
            print('[DRY-RUN][Immich] Would set favorite to {} for {} '
                  'assets'.format(is_favorite, len(asset_ids)))
            return
        asset_ids = sorted(asset_ids)
        for start in range(0, len(asset_ids), self.CHUNK_SIZE):
            self._request('PUT', '/assets', json={
                'ids': asset_ids[start:start + self.CHUNK_SIZE],
                'isFavorite': is_favorite,
            })

    def search_assets(self, search_filter):
        """Search for assets, following all pages of the results.

        :param dict search_filter: A SearchFilter of the Immich API.
        :returns: generator of asset dicts
        """
        cursor = None
        while True:
            payload = {'filter': search_filter, 'size': self.PAGE_SIZE}
            if cursor:
                payload['cursor'] = cursor
            assets = self._request(
                'POST', '/search/metadata', json=payload)['assets']
            for item in assets['items']:
                yield item
            cursor = assets.get('nextCursor')
            if not cursor:
                return


class Immich(PluginBase):
    """Syncs albums and favorites between Elodie and Immich in batch().

    Configured in the [PluginImmich] section of config.ini:

    api_url:
        The API URL of Immich, i.e. https://immich.example.com/api
    api_key:
        An API key of Immich, see the Readme for the permissions it needs.
    external_library_path:
        The folder of the Elodie library as Immich sees it, the import path
        of the external library.
    elodie_library_path:
        The folder of the Elodie library as Elodie sees it. Only needed if it
        is different, i.e. when Immich runs on another computer.
    timeout:
        Seconds to wait for a response of Immich, 30 by default.
    """

    __name__ = 'Immich'

    #: Seconds between saving the state during long runs.
    SAVE_INTERVAL = 60

    #: Seconds until the state of an asset which is not in Immich anymore is
    #: removed. Longer than Immich keeps assets in the trash (30 days), it
    #: restores them with their albums, and a search can miss an asset which
    #: changes while it is read.
    FORGET_AFTER = 60 * 24 * 3600

    #: Keys of the plugin database of earlier versions of this plugin.
    OBSOLETE_KEYS = (
        'bootstrap_completed', 'bootstrap_processed_files', 'immich_states',
        'album_membership', 'favorite_state', 'file_moves',
        'last_sync_timestamp', 'last_processed_created_at',
    )

    def __init__(self):
        super(Immich, self).__init__()
        config = self.config_for_plugin
        self.api_url = config.get('api_url')
        self.api_key = config.get('api_key')
        self.external_library_path = self._clean_path(
            config.get('external_library_path'))
        self.elodie_library_path = self._clean_path(
            config.get('elodie_library_path')) or self.external_library_path
        self.timeout = config.get('timeout', '30')
        self.client = None
        if self.api_url and self.api_key and not self.check_config():
            self.client = ImmichApiClient(
                self.api_url, self.api_key, timeout=float(self.timeout))
        self.filesystem = FileSystem()

    @staticmethod
    def _clean_path(path):
        if not path:
            return None
        return path.rstrip('/\\') or path

    def check_config(self):
        """Check the configuration.

        :returns: list of errors
        """
        errors = []
        for key in ('api_url', 'api_key', 'external_library_path'):
            if not self.config_for_plugin.get(key):
                errors.append('{} is not set in [PluginImmich]'.format(key))
        try:
            if float(self.timeout) <= 0:
                raise ValueError()
        except ValueError:
            errors.append('timeout must be a number of seconds')
        if (self.elodie_library_path and
                not os.path.isdir(self.elodie_library_path)):
            errors.append('The Elodie library {} does not exist'.format(
                self.elodie_library_path))
        return errors

    def before(self, file_path, destination_folder):
        pass

    def after(self, file_path, destination_folder, final_file_path, metadata):
        # Imported files are synced by batch() once Immich scanned them.
        pass

    def batch(self):
        """Sync albums and favorites.

        :returns: tuple of whether it succeeded and the number of assets
            which were changed
        """
        errors = self.check_config()
        if errors:
            for error in errors:
                self.display(error)
            return (False, 0)

        lock = self.lock()
        if lock is None:
            self.display('Another sync with Immich is running')
            return (False, 0)
        try:
            return self._batch()
        finally:
            lock.close()

    def _batch(self):
        try:
            version = self.client.get_version()
        except ImmichError as e:
            self.display('Could not connect to Immich: {}'.format(e))
            return (False, 0)
        if version < MINIMUM_IMMICH_VERSION:
            self.display('Immich {} is not supported, 3.2 or later is '
                         'required'.format('.'.join(map(str, version))))
            return (False, 0)

        try:
            return Sync(self).run()
        except Exception as e:
            # Elodie only logs other exceptions of plugins with --debug
            self.display('Immich sync failed: {}'.format(e))
            return (False, 0)

    # Paths
    def to_elodie_path(self, immich_path):
        """Translate the path of an asset in Immich to the path of the file
        in the Elodie library.

        :returns: str or None if it is not in the library
        """
        prefix = self.external_library_path + '/'
        if not immich_path or not immich_path.startswith(prefix):
            return None
        relative_path = immich_path[len(prefix):]
        return os.path.join(self.elodie_library_path,
                            *relative_path.split('/'))

    def lock(self):
        """Lock the sync so only one runs at a time, i.e. when a long first
        run is still running when cron starts the next one.

        :returns: the lock file, closing it releases the lock, or None if
            another sync has the lock
        """
        lock_file = open(self.db.db_file + '.lock', 'a')
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock_file.close()
            return None
        return lock_file

    # State of the plugin database
    def load_state(self):
        try:
            return self.db.get('assets') or {}
        except ValueError:
            # The state can be rebuilt, the first sync of an asset keeps
            #  everything of both sides.
            corrupt_file = self.db.db_file + '.corrupt'
            self.display('The state of the plugin in {} could not be read, it '
                         'was moved to {} and all files are synced '
                         'again'.format(self.db.db_file, corrupt_file))
            if not constants.dry_run:
                os.replace(self.db.db_file, corrupt_file)
                with open(self.db.db_file, 'w') as f:
                    f.write('{}')
            return {}

    def save_state(self, state):
        if constants.dry_run:
            return
        self.db.set('assets', state)
        for key in self.OBSOLETE_KEYS:
            if self.db.get(key) is not None:
                self.db.delete(key)


def get_album_names(album):
    """Split the album of a file into the names of its albums.

    :param str album: Album of the file, i.e. "A;B".
    :returns: list of names, sorted
    """
    if not album:
        return []
    return sorted(set(
        name.strip() for name in str(album).split(ALBUM_SEPARATOR)
        if name.strip()))


def merge_states(baseline, file_state, immich_state):
    """Merge the state of an asset in the file and in Immich.

    Each state is a dict of 'albums' (list of names) and 'favorite' (bool).

    :param dict baseline: The state after the last run or None if the asset
        was not synced before, i.e. a new or moved file.
    :returns: dict of the merged state
    """
    file_albums = set(file_state['albums'])
    immich_albums = set(immich_state['albums'])
    if baseline is None:
        # Nothing is known about earlier changes, keep all albums and the
        #  favorite of both sides.
        return {
            'albums': sorted(file_albums | immich_albums),
            'favorite': file_state['favorite'] or immich_state['favorite'],
        }

    baseline_albums = set(baseline['albums'])
    added = (file_albums | immich_albums) - baseline_albums
    removed = ((baseline_albums - file_albums) |
               (baseline_albums - immich_albums))
    albums = (baseline_albums - removed) | added

    # Immich wins when the favorite was changed on both sides.
    if immich_state['favorite'] != baseline['favorite']:
        favorite = immich_state['favorite']
    else:
        favorite = file_state['favorite']

    return {'albums': sorted(albums), 'favorite': favorite}


def file_signature(path):
    """Signature of a file which changes when the file is changed. The change
    time is included since Elodie keeps the modification time when writing
    metadata.
    """
    stat = os.stat(path)
    return [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


class Sync(object):
    """One run of the sync of the Immich plugin."""

    def __init__(self, plugin):
        self.plugin = plugin
        self.client = plugin.client
        self.state = plugin.load_state()
        self.subclasses = MEDIA_CLASSES
        # Changes for Immich are collected and applied together:
        #  album name -> set of asset IDs, favorite -> set of asset IDs
        self.album_additions = {}
        self.album_removals = {}
        self.favorites = {True: set(), False: set()}
        # States to save once the changes are applied in Immich
        self.pending = {}
        # Album name -> IDs of the albums with the name, the oldest first
        self.album_ids = {}
        self.counts = {'assets': 0, 'files_changed': 0, 'files_moved': 0,
                       'immich_changed': 0, 'skipped': 0, 'errors': 0}

    def log(self, message):
        self.plugin.log(message)

    def library_filter(self, active=True):
        """Filter for the assets of the library.

        :param bool active: Only assets which are not offline, i.e. moved,
            and not in the trash. Immich includes both otherwise.
        """
        search_filter = {
            # Immich matches it ignoring case and accents, so it can find
            #  more, to_elodie_path() only accepts the exact folder.
            'originalPath': {
                'startsWith': self.plugin.external_library_path + '/'},
            # Not locked assets and not hidden ones like the video of a Live
            #  Photo which Immich shows with the photo.
            'visibility': {'in': ['timeline', 'archive']},
        }
        if active:
            search_filter['isOffline'] = {'eq': False}
            search_filter['trashedAt'] = {'eq': None}
        return search_filter

    def run(self):
        # The assets of the user, not the ones of partners which Immich
        #  includes, i.e. a partner's external library of the same folder.
        #  Only what is needed is kept, a library can have hundreds of
        #  thousands.
        user_id = self.client.get_my_user_id()
        assets = {}
        known = set()
        for asset in self.client.search_assets(self.library_filter(False)):
            if asset.get('ownerId') != user_id:
                continue
            known.add(asset['id'])
            if asset.get('isOffline') or asset.get('isTrashed'):
                continue
            assets[asset['id']] = {
                'id': asset['id'],
                'originalPath': asset['originalPath'],
                'isFavorite': asset.get('isFavorite', False),
            }
        memberships = self.get_album_memberships()
        self.log('{} assets and {} albums in Immich'.format(
            len(assets), len(self.album_ids)))

        last_save = time.time()
        by_path = sorted(assets, key=lambda i: assets[i]['originalPath'])
        for asset_id in by_path:
            self.counts['assets'] += 1
            try:
                self.sync_asset(assets[asset_id],
                                memberships.get(asset_id, set()))
            except Exception as e:
                # One file must not stop the sync of all others
                self.counts['errors'] += 1
                self.plugin.display('Could not sync {}: {}'.format(
                    assets[asset_id]['originalPath'], e))
            if time.time() - last_save > self.plugin.SAVE_INTERVAL:
                self.apply_immich_changes()
                self.plugin.save_state(self.state)
                last_save = time.time()
                self.plugin.display('{}/{} assets synced'.format(
                    self.counts['assets'], len(assets)))

        self.apply_immich_changes()
        # Forget assets which are not in Immich anymore. The state of offline
        #  and trashed assets is kept, Immich restores them with their albums
        #  and favorite when their file is back, i.e. when a file is moved
        #  back to a folder of an album.
        now = time.time()
        for asset_id, state in list(self.state.items()):
            if asset_id in known:
                state.pop('missing_since', None)
            elif now - state.setdefault('missing_since', now) > \
                    self.plugin.FORGET_AFTER:
                del self.state[asset_id]
        self.plugin.save_state(self.state)

        self.plugin.display(
            'Synced {assets} assets: {files_changed} files changed, '
            '{files_moved} moved, {immich_changed} changed in Immich, '
            '{skipped} skipped, {errors} errors'.format(**self.counts))
        changed = self.counts['files_changed'] + self.counts['immich_changed']
        return (self.counts['errors'] == 0, changed)

    def get_album_memberships(self):
        """Get the albums of all assets in the library.

        :returns: dict of asset ID -> set of album names
        """
        memberships = {}
        # Only the albums of the user, albums which others share with them
        #  must not change or move the user's files.
        albums = sorted(self.client.get_albums(owned=True),
                        key=lambda album: album.get('createdAt', ''))
        for album in albums:
            name = album['albumName']
            if not is_album_name_storable(name):
                self.plugin.display(
                    'Album "{}" is not synced, its name cannot be stored in '
                    'a file'.format(name))
                continue
            # Albums with the same name are one album in the file, new
            #  assets are added to the oldest one.
            self.album_ids.setdefault(name, []).append(album['id'])
            if not album.get('assetCount'):
                continue
            # Without the filters for offline and trashed assets: Immich pages
            #  by offset and an asset becoming offline while the pages are
            #  read, i.e. during a scan, would move the next page.
            album_filter = self.library_filter(active=False)
            album_filter['albumIds'] = {'any': [album['id']]}
            for asset in self.client.search_assets(album_filter):
                memberships.setdefault(asset['id'], set()).add(name)
        return memberships

    def sync_asset(self, asset, album_names):
        asset_id = asset['id']
        path = self.plugin.to_elodie_path(asset['originalPath'])
        if path is None or not os.path.isfile(path):
            # i.e. moved by Elodie and not scanned by Immich yet
            self.log('Skipping {}, the file does not exist'.format(
                asset['originalPath']))
            self.counts['skipped'] += 1
            return

        immich_state = {'albums': sorted(album_names),
                        'favorite': bool(asset.get('isFavorite'))}
        baseline = self.state.get(asset_id)
        media = None
        writable = True
        if (baseline is not None and baseline.get('path') == path and
                baseline.get('signature') == file_signature(path)):
            # The file did not change, it has the state of the last run
            file_state = {'albums': baseline['albums'],
                          'favorite': baseline['favorite']}
            writable = baseline.get('writable', True)
        else:
            if baseline is not None and not baseline.get('writable', True):
                # The file never had the state of the last run, what is
                #  missing in it was not removed.
                baseline = None
            media = Base.get_class_by_file(path, self.subclasses)
            if not media:
                self.log('Skipping {}, not a supported file'.format(path))
                self.counts['skipped'] += 1
                return
            file_state = self.read_file_state(media)

        merged = merge_states(baseline, file_state, immich_state)
        removed_in_immich = set(file_state['albums']) - set(merged['albums'])
        if baseline is not None and removed_in_immich:
            # A search can miss an asset which changes while it is read, the
            #  albums of the asset tell if it was removed from them.
            immich_state['albums'] = self.get_albums_of_asset(asset_id)
            merged = merge_states(baseline, file_state, immich_state)
        new_path = path
        if merged != file_state and writable:
            if media is None:
                media = Base.get_class_by_file(path, self.subclasses)
            new_path = self.write_file_state(media, path, file_state, merged)
            if new_path is None:
                self.counts['errors'] += 1
                return
            if new_path is False:
                # i.e. ExifTool cannot change the format
                self.plugin.display(
                    'Albums and favorites cannot be stored in {}, they are '
                    'kept in Immich only'.format(path))
                writable = False
                new_path = path

        if new_path != path:
            # Immich sees the moved file as a new asset, its albums and
            #  favorite are restored from the file then. The asset becomes
            #  offline, if the file comes back to its path Immich restores
            #  it and its state tells what changed since.
            self.state[asset_id] = {'path': path, 'signature': None}
            self.state[asset_id].update(merged)
            return

        if merged != immich_state:
            self.queue_immich_changes(asset_id, immich_state, merged)
        if constants.dry_run:
            return
        new_state = {'path': path, 'signature': file_signature(path)}
        new_state.update(merged)
        if not writable:
            new_state['writable'] = False
        if merged != immich_state:
            # Saved once the changes are applied in Immich
            self.pending[asset_id] = new_state
        else:
            self.state[asset_id] = new_state

    def get_albums_of_asset(self, asset_id):
        names = set()
        for album in self.client.get_albums(owned=True, asset_id=asset_id):
            if is_album_name_storable(album['albumName']):
                names.add(album['albumName'])
        return sorted(names)

    def read_file_state(self, media):
        metadata = media.get_metadata() or {}
        # Albums which cannot be synced stay in the file as they are
        albums = [name for name in get_album_names(metadata.get('album'))
                  if is_album_name_storable(name)]
        return {
            'albums': albums,
            'favorite': metadata.get('rating') == FAVORITE_RATING,
        }

    def write_file_state(self, media, path, file_state, merged):
        """Write the merged state to the file and organize it.

        :returns: str path of the file afterwards, None on errors or False
            if the file cannot store it
        """
        albums_changed = merged['albums'] != file_state['albums']
        favorite_changed = merged['favorite'] != file_state['favorite']
        if constants.dry_run:
            self.counts['files_changed'] += 1
            print('[DRY-RUN][Immich] Would set albums {} and favorite {} '
                  'of {}'.format(merged['albums'], merged['favorite'], path))
            return path

        self.log('Writing albums {} and favorite {} to {}'.format(
            merged['albums'], merged['favorite'], path))
        if albums_changed:
            kept = [name for name in get_album_names(media.get_album())
                    if not is_album_name_storable(name)]
            media.set_album(ALBUM_SEPARATOR.join(
                sorted(merged['albums'] + kept)))
        if favorite_changed:
            media.set_rating(FAVORITE_RATING if merged['favorite'] else '')
        # Elodie reports success also when ExifTool cannot write the file
        written = Base.get_class_by_file(path, self.subclasses)
        if not written or self.read_file_state(written) != merged:
            return False
        self.counts['files_changed'] += 1
        if not albums_changed:
            return path

        # The album can be part of the folder, Elodie moves the file there.
        #  Elodie reports it as a failure when the file is there already.
        filesystem = self.plugin.filesystem
        media = Base.get_class_by_file(path, self.subclasses)
        metadata = media.get_metadata()
        destination = os.path.join(
            self.plugin.elodie_library_path,
            filesystem.get_folder_path(metadata),
            filesystem.get_file_name(metadata))
        if filesystem.is_same_file(path, destination):
            return path
        new_path = self.plugin.filesystem.process_file(
            path, self.plugin.elodie_library_path, media,
            move=True, allowDuplicate=True)
        if not new_path:
            self.plugin.display('Could not organize {}'.format(path))
            return None
        if new_path != path:
            self.counts['files_moved'] += 1
            self.log('Moved {} to {}'.format(path, new_path))
            directory = os.path.dirname(path)
            self.plugin.filesystem.delete_directory_if_empty(directory)
            self.plugin.filesystem.delete_directory_if_empty(
                os.path.dirname(directory))
        return new_path

    def queue_immich_changes(self, asset_id, immich_state, merged):
        self.counts['immich_changed'] += 1
        for name in set(merged['albums']) - set(immich_state['albums']):
            self.album_additions.setdefault(name, set()).add(asset_id)
        for name in set(immich_state['albums']) - set(merged['albums']):
            self.album_removals.setdefault(name, set()).add(asset_id)
        if merged['favorite'] != immich_state['favorite']:
            self.favorites[merged['favorite']].add(asset_id)

    def apply_immich_changes(self):
        """Apply the collected changes in Immich. The state of an asset is
        only saved when all its changes were applied, otherwise the next run
        would take the missing change for one made in Immich.
        """
        failed = set()
        for name, asset_ids in sorted(self.album_additions.items()):
            try:
                if name not in self.album_ids:
                    album = self.client.create_album(name)
                    self.album_ids[name] = [album['id']]
                    self.log('Created album {}'.format(name))
                failed |= self.client.add_assets_to_album(
                    self.album_ids[name][0], asset_ids)
            except ImmichError as e:
                self.plugin.display('Could not add {} assets to album {}: '
                                    '{}'.format(len(asset_ids), name, e))
                failed |= asset_ids
        for name, asset_ids in sorted(self.album_removals.items()):
            try:
                # From all albums with the name, the asset can be in any
                for album_id in self.album_ids[name]:
                    failed |= self.client.remove_assets_from_album(
                        album_id, asset_ids)
            except ImmichError as e:
                self.plugin.display('Could not remove {} assets from album '
                                    '{}: {}'.format(len(asset_ids), name, e))
                failed |= asset_ids
        for is_favorite, asset_ids in self.favorites.items():
            if not asset_ids:
                continue
            try:
                self.client.set_favorite(asset_ids, is_favorite)
            except ImmichError as e:
                self.plugin.display('Could not set favorite of {} assets: '
                                    '{}'.format(len(asset_ids), e))
                failed |= asset_ids

        self.counts['errors'] += len(failed)
        for asset_id, new_state in self.pending.items():
            if asset_id not in failed:
                self.state[asset_id] = new_state
        self.album_additions = {}
        self.album_removals = {}
        self.favorites = {True: set(), False: set()}
        self.pending = {}
