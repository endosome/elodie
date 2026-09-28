# Tests of the Immich plugin against a fake Immich. The tests in
#  immich_integration_test.py run against a real Immich.
import itertools
import os
import shutil
import sys
import time
import unittest.mock as mock

import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import helper
from elodie import constants
from elodie.config import load_config
from elodie.filesystem import FileSystem
from elodie.media.photo import Photo
from elodie.media.video import Video
from elodie.plugins.immich import immich as immich_module
from elodie.plugins.immich.immich import (
    Immich, ImmichApiClient, ImmichError, get_album_names, merge_states)

EXTERNAL_LIBRARY_PATH = '/external/library'


class FakeImmich(object):
    """In-memory Immich with the methods of ImmichApiClient.

    scan() does what Immich 3.2 does with an external library: a file at a
    new path becomes a new asset, an asset whose file is gone becomes offline
    and is moved to the trash, and it is restored with its albums and
    favorite when its file is back at its path (LibraryService in Immich).
    Like Immich 3.2, search includes offline and trashed assets and the
    assets of partners unless filtered.
    """

    def __init__(self, library, version=(3, 2, 2)):
        self.library = library
        self.version = version
        self.assets = {}  # id -> asset
        self.albums = {}  # id -> {'albumName', 'createdAt', 'assetIds'}
        self.ids = itertools.count(1)
        self.requests = []
        self.fail_album_additions = False
        # Asset IDs which the next album search misses, like Immich does
        #  when assets change while its offset based pages are read
        self.skip_in_album_search = set()
        self.skip_in_search = set()

    def scan(self):
        own = [a for a in self.assets.values() if a['ownerId'] == 'me']
        found = set()
        for dirname, dirnames, filenames in os.walk(self.library):
            for filename in filenames:
                relative = os.path.relpath(os.path.join(dirname, filename), self.library)
                path = EXTERNAL_LIBRARY_PATH + '/' + relative.replace(os.sep, '/')
                found.add(path)
                existing = [a for a in own if a['originalPath'] == path]
                if existing:
                    if existing[0]['isOffline']:
                        # Restored with its albums and favorite
                        existing[0]['isOffline'] = False
                        existing[0]['isTrashed'] = False
                else:
                    self.add_asset(path)
        for asset in own:
            if asset['originalPath'] not in found and not asset['isOffline']:
                asset['isOffline'] = True
                asset['isTrashed'] = True

    def add_asset(self, path, owner='me'):
        asset_id = 'asset-%d' % next(self.ids)
        self.assets[asset_id] = {
            'id': asset_id, 'originalPath': path, 'isFavorite': False, 'ownerId': owner,
            'isOffline': False, 'isTrashed': False, 'visibility': 'timeline'}
        return self.assets[asset_id]

    # Helpers for the tests
    def asset_for(self, name):
        matches = [a for a in self.assets.values()
                   if not a['isOffline'] and not a['isTrashed'] and a['ownerId'] == 'me' and
                   a['originalPath'].endswith(name)]
        assert len(matches) == 1, (name, matches)
        return matches[0]

    def albums_of(self, name):
        asset_id = self.asset_for(name)['id']
        return sorted(album['albumName'] for album in self.albums.values()
                      if asset_id in album['assetIds'])

    def add_album(self, name, asset_names=(), owner='me'):
        album_id = 'album-%d' % next(self.ids)
        self.albums[album_id] = {
            'albumName': name, 'createdAt': '2026-01-01T00:00:%02d' % len(self.albums),
            'owner': owner, 'assetIds': set(self.asset_for(n)['id'] for n in asset_names)}
        return album_id

    def album_id(self, name):
        return [i for i, a in self.albums.items() if a['albumName'] == name][0]

    # Methods of ImmichApiClient
    def get_version(self):
        return self.version

    def get_my_user_id(self):
        return 'me'

    def get_albums(self, owned=False, asset_id=None):
        self.requests.append('get_albums')
        return [{'id': album_id, 'albumName': a['albumName'], 'createdAt': a['createdAt'],
                 'assetCount': len(a['assetIds'])} for album_id, a in self.albums.items()
                if (not owned or a['owner'] == 'me') and
                (asset_id is None or asset_id in a['assetIds'])]

    def create_album(self, name):
        self.requests.append(('create_album', name))
        if constants.dry_run:
            return {'id': 'dry-run-album-id', 'albumName': name}
        album_id = self.add_album(name)
        return {'id': album_id, 'albumName': name}

    def add_assets_to_album(self, album_id, asset_ids):
        self.requests.append(('add_assets_to_album', album_id, sorted(asset_ids)))
        if self.fail_album_additions:
            raise ImmichError('PUT /albums/%s/assets failed: HTTP 500' % album_id)
        if not constants.dry_run:
            self.albums[album_id]['assetIds'] |= set(asset_ids)
        return set()

    def remove_assets_from_album(self, album_id, asset_ids):
        self.requests.append(('remove_assets_from_album', album_id, sorted(asset_ids)))
        if not constants.dry_run:
            self.albums[album_id]['assetIds'] -= set(asset_ids)
        return set()

    def set_favorite(self, asset_ids, is_favorite):
        self.requests.append(('set_favorite', sorted(asset_ids), is_favorite))
        if not constants.dry_run:
            for asset_id in asset_ids:
                self.assets[asset_id]['isFavorite'] = is_favorite

    def set_live_photo_video(self, asset_id, video_id):
        self.requests.append(('set_live_photo_video', asset_id, video_id))
        if not constants.dry_run:
            self.assets[asset_id]['livePhotoVideoId'] = video_id

    def search_assets(self, search_filter):
        self.requests.append('search_assets')
        prefix = search_filter['originalPath']['startsWith']
        for asset in sorted(self.assets.values(), key=lambda a: a['id']):
            if not asset['originalPath'].startswith(prefix):
                continue
            if 'isOffline' in search_filter and asset['isOffline'] != search_filter['isOffline']['eq']:
                continue
            if 'trashedAt' in search_filter and asset['isTrashed']:
                continue
            if asset['visibility'] not in search_filter['visibility']['in']:
                continue
            if 'albumIds' in search_filter:
                album_ids = search_filter['albumIds']['any']
                if not any(asset['id'] in self.albums[i]['assetIds'] for i in album_ids):
                    continue
                if asset['id'] in self.skip_in_album_search:
                    self.skip_in_album_search.discard(asset['id'])
                    continue
            elif asset['id'] in self.skip_in_search:
                self.skip_in_search.discard(asset['id'])
                continue
            yield dict(asset)


@pytest.fixture
def library(tmp_path):
    """An Elodie library and a config for the plugin."""
    library = str(tmp_path / 'library')
    os.makedirs(library)
    with open('%s/config.ini' % constants.application_directory(), 'a') as f:
        f.write('\n[PluginImmich]\napi_url=http://immich.test/api\napi_key=key\n'
                'external_library_path=%s\nelodie_library_path=%s\n' % (
                    EXTERNAL_LIBRARY_PATH, library))
    if hasattr(load_config, 'config'):
        del load_config.config
    yield library
    if hasattr(load_config, 'config'):
        del load_config.config


@pytest.fixture
def immich(library):
    return FakeImmich(library)


def create_photo(library, name, album=None, rating=None, fixture='plain.jpg'):
    """Create a photo in the library, in a folder like Elodie would."""
    folder = os.path.join(library, '2015-12-Dec', album or 'Unknown Location')
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    shutil.copyfile(helper.get_file(fixture), path)
    photo = Photo(path)
    photo.set_album(album or '')
    photo.set_rating(rating if rating else '')
    return path


def find_file(library, name):
    # Elodie adds the date to the name when it moves a file
    matches = [os.path.join(d, f) for d, _, files in os.walk(library) for f in files
               if f == name or f.endswith('-' + name)]
    assert len(matches) == 1, (name, matches)
    return matches[0]


def file_state(library, name):
    photo = Photo(find_file(library, name))
    return get_album_names(photo.get_album()), photo.get_rating() == 5


def run_batch(immich):
    plugin = Immich()
    plugin.client = immich
    return plugin.batch()


# Merging the state of the file and Immich
@pytest.mark.parametrize('baseline,file_state,immich_state,expected', [
    # First sync: everything from both sides is kept
    (None, (['A'], False), (['B'], True), (['A', 'B'], True)),
    (None, ([], True), ([], False), ([], True)),
    # Nothing changed
    ((['A'], True), (['A'], True), (['A'], True), (['A'], True)),
    # Changed in Immich
    ((['A'], False), (['A'], False), (['A', 'B'], True), (['A', 'B'], True)),
    ((['A', 'B'], True), (['A', 'B'], True), (['B'], False), (['B'], False)),
    # Changed in the file
    ((['A'], False), (['A', 'C'], True), (['A'], False), (['A', 'C'], True)),
    ((['A', 'B'], True), ([], False), (['A', 'B'], True), ([], False)),
    # Changed on both sides: albums are merged, Immich wins for the favorite
    ((['A', 'B'], False), (['A', 'C'], False), (['B', 'D'], True), (['C', 'D'], True)),
    ((['A'], True), (['A'], False), (['A'], True), (['A'], False)),
    ((['A'], True), (['A'], True), (['A'], False), (['A'], False)),
])
def test_merge_states(baseline, file_state, immich_state, expected):
    def state(value):
        return {'albums': value[0], 'favorite': value[1]}
    merged = merge_states(baseline and state(baseline), state(file_state), state(immich_state))
    assert merged == state(expected), merged

@pytest.mark.parametrize('album,expected', [
    (None, []),
    ('', []),
    ('Trip', ['Trip']),
    ('Trip;Family', ['Family', 'Trip']),
    (' Trip ; ;Family;Trip', ['Family', 'Trip']),
])
def test_get_album_names(album, expected):
    assert get_album_names(album) == expected

@pytest.mark.parametrize('elodie_library_path,immich_path,expected', [
    ('/home/me/photos', '/external/library/2015-12-Dec/a.jpg', '/home/me/photos/2015-12-Dec/a.jpg'),
    ('/home/me/photos/', '/external/library/a b/c;d.jpg', '/home/me/photos/a b/c;d.jpg'),
    # Not in the library
    ('/home/me/photos', '/external/library-other/a.jpg', None),
    ('/home/me/photos', '/upload/a.jpg', None),
    ('/home/me/photos', None, None),
])
def test_to_elodie_path(elodie_library_path, immich_path, expected):
    plugin = Immich.__new__(Immich)
    plugin.external_library_path = Immich._clean_path('/external/library/')
    plugin.elodie_library_path = Immich._clean_path(elodie_library_path)
    assert plugin.to_elodie_path(immich_path) == expected

def test_elodie_library_path_defaults_to_external_library_path(tmp_path):
    library = str(tmp_path)
    with open('%s/config.ini' % constants.application_directory(), 'a') as f:
        f.write('\n[PluginImmich]\napi_url=http://immich.test/api\napi_key=key\n'
                'external_library_path=%s/\n' % library)
    if hasattr(load_config, 'config'):
        del load_config.config
    plugin = Immich()
    del load_config.config

    assert plugin.check_config() == []
    assert plugin.elodie_library_path == library

# Configuration
@pytest.mark.parametrize('config,error', [
    ('', 'api_url is not set in [PluginImmich]'),
    ('api_url=http://immich.test/api\nexternal_library_path=/external/library\n', 'api_key is not set in [PluginImmich]'),
    ('api_url=http://immich.test/api\napi_key=key\n', 'external_library_path is not set in [PluginImmich]'),
    ('api_url=http://immich.test/api\napi_key=key\nexternal_library_path=/external/library\n'
     'elodie_library_path=/does/not/exist\n', 'The Elodie library /does/not/exist does not exist'),
    ('api_url=http://immich.test/api\napi_key=key\nexternal_library_path=/external/library\n'
     'elodie_library_path={library}\ntimeout=soon\n', 'timeout must be a number of seconds'),
])
def test_batch_with_invalid_config(tmp_path, config, error):
    with open('%s/config.ini' % constants.application_directory(), 'a') as f:
        f.write('\n[PluginImmich]\n' + config.format(library=tmp_path))
    if hasattr(load_config, 'config'):
        del load_config.config

    with mock.patch.object(Immich, 'display') as display, \
            mock.patch('requests.Session.request') as request:
        plugin = Immich()
        result = plugin.batch()
    del load_config.config

    assert result == (False, 0)
    assert mock.call(error) in display.call_args_list, display.call_args_list
    assert request.call_count == 0

def test_config_section_from_the_readme_is_used(library):
    readme = os.path.join(os.path.dirname(immich_module.__file__), 'Readme.md')
    with open(readme) as f:
        assert '[PluginImmich]' in f.read()

def test_batch_requires_immich_3_2(library, immich):
    immich.version = (3, 1, 9)
    with mock.patch.object(Immich, 'display') as display:
        result = run_batch(immich)

    assert result == (False, 0)
    assert mock.call('Immich 3.1.9 is not supported, 3.2 or later is required') in display.call_args_list
    assert immich.requests == []

def test_batch_when_immich_is_not_reachable(library):
    plugin = Immich()
    plugin.client = mock.Mock(get_version=mock.Mock(side_effect=ImmichError('GET /server/version failed: refused')))
    with mock.patch.object(Immich, 'display') as display:
        result = plugin.batch()

    assert result == (False, 0)
    assert 'Could not connect to Immich' in display.call_args_list[0][0][0]

# Syncing
def test_first_sync_adds_albums_and_favorites_of_files_to_immich(library, immich):
    create_photo(library, 'a.jpg', album='Summer;Family', rating=5)
    create_photo(library, 'b.jpg', album='Summer')
    create_photo(library, 'c.jpg')
    immich.scan()

    result = run_batch(immich)

    assert result == (True, 2), result
    assert immich.albums_of('a.jpg') == ['Family', 'Summer']
    assert immich.albums_of('b.jpg') == ['Summer']
    assert immich.albums_of('c.jpg') == []
    assert [immich.asset_for(n)['isFavorite'] for n in ('a.jpg', 'b.jpg', 'c.jpg')] == [True, False, False]
    # One album is created once for all its assets
    assert [r for r in immich.requests if r[0] == 'create_album'] == [('create_album', 'Family'), ('create_album', 'Summer')]

def test_first_sync_keeps_albums_and_favorites_of_immich(library, immich):
    create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    immich.add_album('Trip', ['a.jpg'])
    immich.asset_for('a.jpg')['isFavorite'] = True

    run_batch(immich)
    immich.scan()
    run_batch(immich)

    assert file_state(library, 'a.jpg') == (['Summer', 'Trip'], True)
    assert immich.albums_of('a.jpg') == ['Summer', 'Trip']
    assert immich.asset_for('a.jpg')['isFavorite'] is True

def test_album_added_in_immich_is_written_to_the_file_which_is_moved(library, immich):
    path = create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    run_batch(immich)
    immich.albums[immich.add_album('Trip')]['assetIds'].add(immich.asset_for('a.jpg')['id'])

    result = run_batch(immich)

    new_path = find_file(library, 'a.jpg')
    assert result == (True, 1), result
    assert file_state(library, 'a.jpg') == (['Summer', 'Trip'], False)
    assert not os.path.exists(path)
    assert os.path.basename(os.path.dirname(new_path)) == 'Summer;Trip', new_path

def test_moved_file_gets_its_albums_and_favorite_back_in_immich(library, immich):
    create_photo(library, 'a.jpg', album='Summer', rating=5)
    immich.scan()
    run_batch(immich)
    immich.albums[immich.add_album('Trip')]['assetIds'].add(immich.asset_for('a.jpg')['id'])
    run_batch(immich)
    old_asset_id = [a['id'] for a in immich.assets.values() if a['originalPath'].endswith('a.jpg')][0]

    # Immich sees the moved file as a new asset
    immich.scan()
    run_batch(immich)

    new_asset = immich.asset_for('a.jpg')
    assert new_asset['id'] != old_asset_id
    assert immich.albums_of('a.jpg') == ['Summer', 'Trip']
    assert new_asset['isFavorite'] is True

def test_album_removed_in_immich_is_removed_from_the_file(library, immich):
    # The album is also in XMP:Album which Elodie reads when XMP-xmpDM:Album is empty
    path = os.path.join(library, '2015-12-Dec', 'Test Album', 'a.jpg')
    os.makedirs(os.path.dirname(path))
    shutil.copyfile(helper.get_file('with-album.jpg'), path)
    immich.scan()
    run_batch(immich)
    assert immich.albums_of('a.jpg') == ['Test Album']

    immich.albums[immich.album_id('Test Album')]['assetIds'].clear()
    run_batch(immich)

    assert file_state(library, 'a.jpg')[0] == []
    assert os.path.basename(os.path.dirname(find_file(library, 'a.jpg'))) == 'Unknown Location'

def test_favorite_changed_in_immich_is_written_to_the_file(library, immich):
    path = create_photo(library, 'a.jpg')
    create_photo(library, 'b.jpg', rating=5)
    immich.scan()
    run_batch(immich)
    immich.asset_for('a.jpg')['isFavorite'] = True
    immich.asset_for('b.jpg')['isFavorite'] = False

    result = run_batch(immich)

    assert result == (True, 2), result
    assert file_state(library, 'a.jpg') == ([], True)
    assert file_state(library, 'b.jpg') == ([], False)
    # A favorite does not move the file
    assert find_file(library, 'a.jpg') == path

def test_changes_in_the_file_are_applied_in_immich(library, immich):
    create_photo(library, 'a.jpg', album='Summer')
    create_photo(library, 'b.jpg', album='Summer', rating=5)
    immich.scan()
    run_batch(immich)
    # i.e. with exiftool or another program, without moving the file
    photo = Photo(find_file(library, 'a.jpg'))
    photo.set_album('Summer;Trip')
    photo.set_rating(5)
    Photo(find_file(library, 'b.jpg')).set_album('')
    Photo(find_file(library, 'b.jpg')).set_rating('')

    run_batch(immich)

    assert immich.albums_of('a.jpg') == ['Summer', 'Trip']
    assert immich.asset_for('a.jpg')['isFavorite'] is True
    assert immich.albums_of('b.jpg') == []
    assert immich.asset_for('b.jpg')['isFavorite'] is False

def test_changes_on_both_sides_are_merged(library, immich):
    create_photo(library, 'a.jpg', album='A;B', rating=5)
    immich.scan()
    run_batch(immich)
    Photo(find_file(library, 'a.jpg')).set_album('A;C')
    Photo(find_file(library, 'a.jpg')).set_rating('')
    immich.albums[immich.album_id('A')]['assetIds'].clear()
    immich.albums[immich.add_album('D')]['assetIds'].add(immich.asset_for('a.jpg')['id'])

    run_batch(immich)
    immich.scan()
    run_batch(immich)

    # A was removed in Immich, B in the file, C and D were added. The
    #  favorite was only removed in the file.
    assert file_state(library, 'a.jpg') == (['C', 'D'], False)
    assert immich.albums_of('a.jpg') == ['C', 'D']
    assert immich.asset_for('a.jpg')['isFavorite'] is False

def test_nothing_changes_when_both_sides_agree(library, immich):
    create_photo(library, 'a.jpg', album='Summer', rating=5)
    immich.scan()
    run_batch(immich)
    immich.requests = []

    result = run_batch(immich)

    assert result == (True, 0), result
    assert [r for r in immich.requests if r not in ('get_albums', 'search_assets')] == []

def test_unchanged_files_are_not_read_again(library, immich):
    # Reading metadata is slow, a large library must not be read every run
    for i in range(3):
        create_photo(library, '%d.jpg' % i, album='Summer')
    immich.scan()
    run_batch(immich)

    with mock.patch('elodie.plugins.immich.immich.Base.get_class_by_file',
                    wraps=immich_module.Base.get_class_by_file) as get_class_by_file:
        run_batch(immich)
        Photo(find_file(library, '1.jpg')).set_rating(5)
        run_batch(immich)

    assert get_class_by_file.call_count == 1, get_class_by_file.call_args_list
    assert immich.asset_for('1.jpg')['isFavorite'] is True

def test_failed_change_in_immich_is_retried_and_not_taken_for_a_removal(library, immich):
    # If the state was saved although adding to the album failed, the next
    #  run would take the missing album for one removed in Immich and remove
    #  it from the file.
    create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    immich.fail_album_additions = True
    with mock.patch.object(Immich, 'display'):
        result = run_batch(immich)
    assert result[0] is False

    immich.fail_album_additions = False
    result = run_batch(immich)

    assert result[0] is True
    assert file_state(library, 'a.jpg') == (['Summer'], False)
    assert immich.albums_of('a.jpg') == ['Summer']

def test_one_failing_file_does_not_stop_the_sync(library, immich):
    create_photo(library, 'a.jpg', album='A')
    create_photo(library, 'b.jpg', album='B')
    immich.scan()
    read = immich_module.Sync.read_file_state

    def fail_for_a(self, media):
        if media.source.endswith('a.jpg'):
            raise OSError('Permission denied')
        return read(self, media)

    with mock.patch.object(immich_module.Sync, 'read_file_state', fail_for_a), \
            mock.patch.object(Immich, 'display') as display:
        result = run_batch(immich)

    assert result == (False, 1), result
    assert immich.albums_of('b.jpg') == ['B']
    assert any('Could not sync' in c[0][0] and 'a.jpg' in c[0][0] for c in display.call_args_list)

def test_files_which_do_not_exist_are_skipped(library, immich):
    create_photo(library, 'a.jpg', album='A')
    immich.scan()
    # Moved by Elodie, Immich did not scan the library yet
    os.remove(find_file(library, 'a.jpg'))
    # Not in the library
    immich.assets['upload'] = {'id': 'upload', 'originalPath': '/upload/b.jpg', 'isFavorite': True,
                               'isOffline': False, 'visibility': 'timeline'}

    result = run_batch(immich)

    assert result == (True, 0), result
    assert [r for r in immich.requests if r[0] in ('create_album', 'set_favorite')] == []

def test_hidden_and_offline_assets_are_not_synced(library, immich):
    create_photo(library, 'a.jpg', album='A')
    create_photo(library, 'b.jpg', album='B')
    immich.scan()
    # i.e. the video of a Live Photo which Immich shows with the photo
    immich.asset_for('a.jpg')['visibility'] = 'hidden'
    immich.asset_for('b.jpg')['isOffline'] = True

    run_batch(immich)

    assert [r for r in immich.requests if r[0] == 'create_album'] == []

def test_album_names_which_cannot_be_stored_are_not_synced(library, immich):
    create_photo(library, 'a.jpg')
    immich.scan()
    immich.add_album('Rock;Roll', ['a.jpg'])

    with mock.patch.object(Immich, 'display') as display:
        run_batch(immich)

    assert file_state(library, 'a.jpg') == ([], False)
    assert mock.call('Album "Rock;Roll" is not synced, its name cannot be stored in a file') in display.call_args_list

def test_assets_are_added_to_the_oldest_album_of_a_name(library, immich):
    create_photo(library, 'a.jpg', album='Trip')
    immich.scan()
    first = immich.add_album('Trip')
    second = immich.add_album('Trip')

    run_batch(immich)

    assert immich.albums[first]['assetIds'] == {immich.asset_for('a.jpg')['id']}
    assert immich.albums[second]['assetIds'] == set()

def test_dry_run_changes_nothing(library, immich):
    path = create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    immich.add_album('Trip', ['a.jpg'])
    immich.asset_for('a.jpg')['isFavorite'] = True

    with mock.patch('elodie.constants.dry_run', True), \
            mock.patch('builtins.print') as mock_print:
        result = run_batch(immich)
    plugin = Immich()

    assert result[0] is True
    assert find_file(library, 'a.jpg') == path
    assert file_state(library, 'a.jpg') == (['Summer'], False)
    assert immich.albums_of('a.jpg') == ['Trip']
    assert plugin.load_state() == {}
    assert any('Would set albums' in str(c) for c in mock_print.call_args_list), mock_print.call_args_list

def test_state_of_earlier_versions_is_removed(library, immich):
    create_photo(library, 'a.jpg')
    immich.scan()
    plugin = Immich()
    plugin.db.set('bootstrap_completed', True)
    plugin.db.set('file_moves', {'x': {}})

    run_batch(immich)

    assert plugin.db.get('bootstrap_completed') is None
    assert plugin.db.get('file_moves') is None
    assert list(plugin.load_state()) == [immich.asset_for('a.jpg')['id']]

def test_state_of_assets_which_are_gone_is_removed(library, immich):
    create_photo(library, 'a.jpg')
    create_photo(library, 'b.jpg')
    immich.scan()
    run_batch(immich)
    a, b = immich.asset_for('a.jpg')['id'], immich.asset_for('b.jpg')['id']
    os.remove(find_file(library, 'b.jpg'))
    immich.scan()

    # Offline, Immich can restore it until it is removed from the trash
    run_batch(immich)
    offline = sorted(Immich().load_state())
    del immich.assets[b]
    # Kept for a while, a search can miss an asset when Immich changes
    #  while it is read
    run_batch(immich)
    missing = sorted(Immich().load_state())
    with mock.patch('time.time', return_value=time.time() + 61 * 24 * 3600):
        run_batch(immich)

    assert offline == missing == sorted([a, b])
    assert list(Immich().load_state()) == [a]

# The API client
def response(status, json_body=None, headers=None):
    r = requests.Response()
    r.status_code = status
    r._content = b'' if json_body is None else __import__('json').dumps(json_body).encode()
    r.headers.update(headers or {})
    return r

@mock.patch('time.sleep')
def test_client_retries_when_immich_is_busy(sleep):
    client = ImmichApiClient('http://immich.test/api/', 'key')
    responses = [response(429, headers={'Retry-After': '7'}), response(503), response(200, {'major': 3, 'minor': 2, 'patch': 2})]
    with mock.patch.object(client.session, 'request', side_effect=responses) as request:
        version = client.get_version()

    assert version == (3, 2, 2)
    assert request.call_args_list[0] == mock.call('GET', 'http://immich.test/api/server/version', timeout=30)
    assert [c[0][0] for c in sleep.call_args_list] == [7.0, 2.0]

@mock.patch('time.sleep')
def test_client_retries_on_connection_errors_and_gives_up(sleep):
    client = ImmichApiClient('http://immich.test/api', 'key', retries=2)
    with mock.patch.object(client.session, 'request', side_effect=requests.ConnectionError('refused')) as request:
        with pytest.raises(ImmichError, match='GET /albums failed: refused'):
            client.get_albums()

    assert request.call_count == 3

@mock.patch('time.sleep')
def test_client_does_not_retry_client_errors_or_creating_albums(sleep):
    client = ImmichApiClient('http://immich.test/api', 'key')
    with mock.patch.object(client.session, 'request', return_value=response(401, {'message': 'Invalid API key'})) as request:
        with pytest.raises(ImmichError, match='HTTP 401'):
            client.get_albums()
    assert request.call_count == 1

    with mock.patch.object(client.session, 'request', side_effect=requests.Timeout('timed out')) as request:
        with pytest.raises(ImmichError):
            client.create_album('Trip')
    # A request which timed out may have created the album
    assert request.call_count == 1

def test_client_sends_the_api_key():
    client = ImmichApiClient('http://immich.test/api', 'secret')
    assert client.session.headers['x-api-key'] == 'secret'

def test_client_search_follows_the_cursor():
    client = ImmichApiClient('http://immich.test/api', 'key')
    pages = [
        response(200, {'assets': {'items': [{'id': '1'}, {'id': '2'}], 'nextCursor': 'abc'}}),
        response(200, {'assets': {'items': [{'id': '3'}], 'nextCursor': None}}),
    ]
    with mock.patch.object(client.session, 'request', side_effect=pages) as request:
        assets = list(client.search_assets({'isFavorite': {'eq': True}}))

    assert [a['id'] for a in assets] == ['1', '2', '3']
    payloads = [c[1]['json'] for c in request.call_args_list]
    assert payloads[0] == {'filter': {'isFavorite': {'eq': True}}, 'size': 1000}
    assert payloads[1]['cursor'] == 'abc'

def test_client_album_changes_return_failed_assets():
    client = ImmichApiClient('http://immich.test/api', 'key')
    results = response(200, [
        {'id': '1', 'success': True},
        {'id': '2', 'success': False, 'error': 'duplicate'},
        {'id': '3', 'success': False, 'error': 'no_permission'},
    ])
    with mock.patch.object(client.session, 'request', return_value=results) as request:
        failed = client.add_assets_to_album('album', ['3', '1', '2'])

    assert failed == {'3'}
    assert request.call_args[0][:2] == ('PUT', 'http://immich.test/api/albums/album/assets')
    assert request.call_args[1]['json'] == {'ids': ['1', '2', '3']}

def test_client_changes_many_assets_in_chunks():
    client = ImmichApiClient('http://immich.test/api', 'key')
    asset_ids = ['%04d' % i for i in range(1200)]
    with mock.patch.object(client.session, 'request', return_value=response(204)) as request:
        client.set_favorite(asset_ids, True)

    assert [len(c[1]['json']['ids']) for c in request.call_args_list] == [500, 500, 200]
    assert all(c[1]['json']['isFavorite'] is True for c in request.call_args_list)

@mock.patch('elodie.constants.dry_run', True)
@mock.patch('builtins.print')
def test_client_dry_run_changes_nothing(mock_print):
    client = ImmichApiClient('http://immich.test/api', 'key')
    with mock.patch.object(client.session, 'request') as request:
        album = client.create_album('Trip')
        client.add_assets_to_album('album123', ['1', '2', '3'])
        client.remove_assets_from_album('album123', ['1'])
        client.set_favorite(['1', '2'], True)

    assert request.call_count == 0
    assert album == {'id': 'dry-run-album-id', 'albumName': 'Trip'}
    assert [c[0][0] for c in mock_print.call_args_list] == [
        '[DRY-RUN][Immich] Would create album: Trip',
        '[DRY-RUN][Immich] Would add 3 assets to album album123',
        '[DRY-RUN][Immich] Would remove 1 assets from album album123',
        '[DRY-RUN][Immich] Would set favorite to True for 2 assets',
    ]

def test_album_change_in_folders_without_albums(library, immich):
    # When the folders do not include the album the file is not moved,
    #  Elodie reports the same path which is not an error.
    with open('%s/config.ini' % constants.application_directory(), 'a') as f:
        f.write('\n[Directory]\ndate=%Y-%m\nfull_path=%date\n')
    if hasattr(load_config, 'config'):
        del load_config.config
    # Imported by Elodie so it is where Elodie puts it
    source = os.path.join(os.path.dirname(library), 'a.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), source)
    Photo(source).set_rating('')
    path = FileSystem().process_file(source, library, Photo(source))
    assert os.path.dirname(path) == os.path.join(library, '2015-12'), path
    immich.scan()
    run_batch(immich)
    immich.add_album('Trip', ['a.jpg'])

    with mock.patch.object(Immich, 'display') as display:
        result = run_batch(immich)
        second = run_batch(immich)

    assert result == (True, 1), display.call_args_list
    assert find_file(library, 'a.jpg') == path
    assert file_state(library, 'a.jpg') == (['Trip'], False)
    assert second == (True, 0), display.call_args_list

def test_album_removed_from_all_albums_with_its_name(library, immich):
    create_photo(library, 'a.jpg', album='Trip')
    immich.scan()
    first = immich.add_album('Trip')
    second = immich.add_album('Trip', ['a.jpg'])
    run_batch(immich)
    immich.albums[first]['assetIds'].add(immich.asset_for('a.jpg')['id'])
    # Removed in the file, i.e. with elodie.py update
    Photo(find_file(library, 'a.jpg')).set_album('')

    run_batch(immich)
    immich.scan()
    result = run_batch(immich)

    assert immich.albums[first]['assetIds'] == set()
    assert immich.albums[second]['assetIds'] == set()
    assert file_state(library, 'a.jpg') == ([], False)
    assert result == (True, 0), result

def test_unexpected_errors_fail_the_batch_with_a_message(library, immich):
    create_photo(library, 'a.jpg')
    immich.scan()
    immich.get_albums = mock.Mock(side_effect=KeyError('albumName'))

    with mock.patch.object(Immich, 'display') as display:
        result = run_batch(immich)

    assert result == (False, 0)
    assert "Immich sync failed: 'albumName'" in [c[0][0] for c in display.call_args_list]

@pytest.mark.parametrize('status,body', [
    # The web app of Immich answers requests for JSON with 406, others with
    #  its HTML
    (406, b'{"message":"The route /server/version was requested as application/json, but only returns text/html"}'),
    (200, b'<!doctype html><html></html>'),
])
def test_client_reports_an_api_url_without_api(status, body):
    client = ImmichApiClient('http://immich.test', 'key')
    web_app = requests.Response()
    web_app.status_code = status
    web_app._content = body
    with mock.patch.object(client.session, 'request', return_value=web_app) as request:
        with pytest.raises(ImmichError, match='not a response of the Immich API, api_url must end with /api'):
            client.get_version()
    assert request.call_count == 1

def create_file(library, name, fixture, album='', rating=''):
    """Import a file into the library with Elodie, so it has the path Elodie
    gives it."""
    source = os.path.join(os.path.dirname(library), name)
    shutil.copyfile(helper.get_file(fixture), source)
    media = Video(source) if name.endswith(('.mov', '.webm')) else Photo(source)
    media.set_album(album)
    media.set_rating(rating)
    media = Video(source) if name.endswith(('.mov', '.webm')) else Photo(source)
    return FileSystem().process_file(source, library, media, move=True)

def test_videos_are_synced(library, immich):
    path = create_file(library, 'clip.mov', 'video.mov')
    immich.scan()
    run_batch(immich)
    immich.add_album('Trip', ['clip.mov'])
    immich.asset_for('clip.mov')['isFavorite'] = True

    result = run_batch(immich)

    video = Video(find_file(library, 'clip.mov'))
    assert result == (True, 1), result
    assert (video.get_album(), video.get_rating()) == ('Trip', 5)
    assert not os.path.exists(path)

def test_files_which_cannot_store_albums_keep_them_in_immich(library, immich):
    # ExifTool cannot write to WebM files. If the plugin took the album for
    #  stored, it would remove it from Immich once the file changes.
    path = create_file(library, 'clip.webm', 'video.webm')
    immich.scan()
    run_batch(immich)
    immich.add_album('Trip', ['clip.webm'])
    immich.asset_for('clip.webm')['isFavorite'] = True

    with mock.patch.object(Immich, 'display') as display:
        result = run_batch(immich)
    messages = [c[0][0] for c in display.call_args_list]
    # The file changes, i.e. it was copied back from a backup
    os.utime(path, (0, 0))
    with mock.patch.object(Immich, 'display') as display:
        second = run_batch(immich)
        third = run_batch(immich)

    assert result == (True, 0), messages
    assert 'Albums and favorites cannot be stored in %s, they are kept in Immich only' % path in messages
    assert find_file(library, 'clip.webm') == path
    assert immich.albums_of('clip.webm') == ['Trip']
    assert immich.asset_for('clip.webm')['isFavorite'] is True
    assert second == third == (True, 0), display.call_args_list

@pytest.mark.parametrize('name', ['../../escape', '..', 'Trips/2024', 'Trips\\2024', ''])
def test_album_names_which_are_no_folder_name_are_not_synced(library, immich, name):
    # The album of a file is part of its folder, Elodie uses it as it is
    path = create_photo(library, 'a.jpg')
    immich.scan()
    immich.add_album(name, ['a.jpg'])

    with mock.patch.object(Immich, 'display') as display:
        result = run_batch(immich)

    assert result == (True, 0), display.call_args_list
    assert find_file(library, 'a.jpg') == path
    assert file_state(library, 'a.jpg') == ([], False)
    assert mock.call('Album "%s" is not synced, its name cannot be stored in a file' % name) in display.call_args_list

def test_album_names_of_files_which_are_no_folder_name_stay_as_they_are(library, immich):
    # i.e. set with elodie.py update --album "2024/Trips"
    path = create_photo(library, 'a.jpg', album='Summer')
    Photo(path).set_album('2024/Trips;Summer')
    immich.scan()
    run_batch(immich)
    immich.add_album('Family', ['a.jpg'])

    with mock.patch.object(Immich, 'display'):
        run_batch(immich)
        immich.scan()
        run_batch(immich)
        result = run_batch(immich)

    assert result == (True, 0), result
    assert get_album_names(Photo(find_file(library, 'a.jpg')).get_album()) == ['2024/Trips', 'Family', 'Summer']
    assert immich.albums_of('a.jpg') == ['Family', 'Summer']

def test_unreadable_state_is_moved_aside_and_rebuilt(library, immich):
    # i.e. cut off by a crash. The first sync keeps everything of both sides
    #  so nothing is lost when it starts over.
    create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    run_batch(immich)
    plugin = Immich()
    with open(plugin.db.db_file) as f:
        content = f.read()
    with open(plugin.db.db_file, 'w') as f:
        f.write(content[:len(content) // 2])
    immich.add_album('Trip', ['a.jpg'])

    with mock.patch.object(Immich, 'display') as display:
        result = run_batch(immich)
        second = run_batch(immich)

    messages = [c[0][0] for c in display.call_args_list]
    assert result[0] is True, messages
    assert any('could not be read, it was moved to %s.corrupt' % plugin.db.db_file in m for m in messages), messages
    assert os.path.isfile(plugin.db.db_file + '.corrupt')
    assert file_state(library, 'a.jpg') == (['Summer', 'Trip'], False)
    assert second[0] is True, messages

def test_two_runs_at_the_same_time_are_not_possible(library, immich):
    # i.e. a long first run and the next run started by cron
    create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    first = Immich()
    first.client = immich
    lock = first.lock()
    assert lock is not None

    with mock.patch.object(Immich, 'display') as display:
        result = run_batch(immich)
    requests_while_locked = list(immich.requests)
    lock.close()
    after = run_batch(immich)

    assert result == (False, 0)
    assert mock.call('Another sync with Immich is running') in display.call_args_list
    assert requests_while_locked == []
    assert after == (True, 1), after

def test_restored_asset_does_not_bring_back_what_was_removed(library, immich):
    # Immich restores an offline asset with its albums when its file is back
    #  at its path, i.e. when an album is added and removed again.
    create_file(library, 'a.jpg', 'plain.jpg', album='Summer')
    immich.scan()
    run_batch(immich)
    first = immich.asset_for('a.jpg')
    immich.albums[immich.add_album('Trip')]['assetIds'].add(first['id'])
    run_batch(immich)
    immich.scan()
    run_batch(immich)
    # Trip removed from the new asset, the file goes back to Summer/
    immich.albums[immich.album_id('Trip')]['assetIds'].discard(immich.asset_for('a.jpg')['id'])
    run_batch(immich)

    immich.scan()
    assert immich.asset_for('a.jpg')['id'] == first['id']
    assert immich.albums_of('a.jpg') == ['Summer', 'Trip']
    run_batch(immich)
    immich.scan()
    result = run_batch(immich)

    assert result == (True, 0), result
    assert file_state(library, 'a.jpg') == (['Summer'], False)
    assert immich.albums_of('a.jpg') == ['Summer']

def test_restored_asset_does_not_bring_back_a_removed_favorite(library, immich):
    create_file(library, 'a.jpg', 'plain.jpg', album='Summer', rating=5)
    immich.scan()
    run_batch(immich)
    first = immich.asset_for('a.jpg')
    immich.albums[immich.add_album('Trip')]['assetIds'].add(first['id'])
    run_batch(immich)
    immich.scan()
    run_batch(immich)
    second = immich.asset_for('a.jpg')
    second['isFavorite'] = False
    immich.albums[immich.album_id('Trip')]['assetIds'].discard(second['id'])
    run_batch(immich)
    immich.scan()
    run_batch(immich)

    assert immich.asset_for('a.jpg')['id'] == first['id']
    assert file_state(library, 'a.jpg') == (['Summer'], False)
    assert immich.asset_for('a.jpg')['isFavorite'] is False

def test_trashed_assets_are_not_synced(library, immich):
    path = create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    run_batch(immich)
    asset = immich.asset_for('a.jpg')
    asset['isTrashed'] = True
    immich.albums[immich.add_album('Trip')]['assetIds'].add(asset['id'])

    result = run_batch(immich)

    assert result == (True, 0), result
    assert find_file(library, 'a.jpg') == path
    assert file_state(library, 'a.jpg') == (['Summer'], False)
    # Restored from the trash it is synced again
    asset['isTrashed'] = False
    run_batch(immich)
    assert file_state(library, 'a.jpg') == (['Summer', 'Trip'], False)

def test_assets_of_partners_are_not_synced(library, immich):
    # i.e. a partner with an external library of the same folder
    path = create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    theirs = immich.add_asset(immich.asset_for('a.jpg')['originalPath'], owner='partner')
    theirs['isFavorite'] = True
    immich.albums[immich.add_album('Theirs')]['assetIds'].add(theirs['id'])

    run_batch(immich)
    result = run_batch(immich)

    assert result == (True, 0), result
    assert find_file(library, 'a.jpg') == path
    assert file_state(library, 'a.jpg') == (['Summer'], False)
    assert theirs['isFavorite'] is True
    assert not any(theirs['id'] in str(r) for r in immich.requests)

def test_albums_shared_by_other_users_are_not_synced(library, immich):
    # Albums of others must not change or move the files of the user, i.e.
    #  an album which a partner shares with the user and contains their photo
    path = create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    theirs = immich.add_album('Summer', ['a.jpg'], owner='partner')
    immich.add_album('Theirs', ['a.jpg'], owner='partner')

    run_batch(immich)
    immich.albums[theirs]['assetIds'].clear()
    result = run_batch(immich)

    assert result == (True, 0), result
    assert find_file(library, 'a.jpg') == path
    assert file_state(library, 'a.jpg') == (['Summer'], False)
    # The album of the file is an own album, the ones of the partner stay
    asset_id = immich.asset_for('a.jpg')['id']
    own = [a['albumName'] for a in immich.albums.values() if a['owner'] == 'me' and asset_id in a['assetIds']]
    assert own == ['Summer'], own
    assert immich.albums[theirs]['assetIds'] == set()
    assert immich.albums_of('a.jpg') == ['Summer', 'Theirs']

def test_album_missing_from_a_page_of_the_search_is_not_removed(library, immich):
    # Immich pages search results by offset, when assets change while they
    #  are read one can be missing. That is no removal.
    path = create_photo(library, 'a.jpg', album='Summer')
    immich.scan()
    run_batch(immich)
    immich.skip_in_album_search.add(immich.asset_for('a.jpg')['id'])

    result = run_batch(immich)

    assert result == (True, 0), result
    assert find_file(library, 'a.jpg') == path
    assert file_state(library, 'a.jpg') == (['Summer'], False)

def test_asset_missing_from_a_page_of_the_search_keeps_its_state(library, immich):
    create_file(library, 'a.jpg', 'plain.jpg', album='Summer')
    immich.scan()
    run_batch(immich)
    asset = immich.asset_for('a.jpg')
    immich.skip_in_search.add(asset['id'])
    run_batch(immich)
    # A removal in Immich is still recognized as one
    immich.albums[immich.album_id('Summer')]['assetIds'].discard(asset['id'])

    run_batch(immich)

    assert file_state(library, 'a.jpg') == ([], False)

def _create_live_photo(library):
    # Like Elodie imports it: the video next to the photo with its name
    folder = os.path.join(library, '2019-05-May', 'Unknown Location')
    os.makedirs(folder)
    photo, video = helper.create_live_photo(folder, name='2019-05-26_10-33-20-img_1234', photo_extension='heic',
                                            video_extension='mov')
    return photo, video

def test_live_photo_video_gets_the_albums_and_favorite_of_its_photo_and_moves_with_it(library, immich):
    # gh-474: Immich shows the video with the photo and hides it, it was
    #  left behind without the album when the photo moved to the album folder
    photo, video = _create_live_photo(library)
    immich.scan()
    immich.asset_for('img_1234.mov')['visibility'] = 'hidden'
    run_batch(immich)
    immich.albums[immich.add_album('Trip')]['assetIds'].add(immich.asset_for('img_1234.heic')['id'])
    immich.asset_for('img_1234.heic')['isFavorite'] = True

    result = run_batch(immich)
    new_photo = find_file(library, 'img_1234.heic')
    new_video = find_file(library, 'img_1234.mov')
    video_media = Video(new_video)

    assert result == (True, 1), result
    assert os.path.basename(os.path.dirname(new_photo)) == 'Trip', new_photo
    assert os.path.splitext(new_video)[0] == os.path.splitext(new_photo)[0], (new_photo, new_video)
    assert not os.path.exists(video)
    assert get_album_names(video_media.get_album()) == ['Trip']
    assert video_media.get_rating() == 5

def test_live_photo_video_gets_the_favorite_of_its_photo(library, immich):
    # Without an album change the photo does not move, the video neither
    photo, video = _create_live_photo(library)
    immich.scan()
    immich.asset_for('img_1234.mov')['visibility'] = 'hidden'
    run_batch(immich)
    immich.asset_for('img_1234.heic')['isFavorite'] = True

    run_batch(immich)

    assert os.path.exists(video)
    assert Video(video).get_rating() == 5

def _linked_live_photo(immich, library, folder):
    """A Live Photo in a folder whose photo Immich links to its video."""
    path = os.path.join(library, '2019-05-May', folder)
    os.makedirs(path, exist_ok=True)
    photo, video = helper.create_live_photo(path, name='2019-05-26_10-33-20-img_1234', photo_extension='heic',
                                            video_extension='mov')
    immich.scan()
    video_asset = [a for a in immich.assets.values() if a['originalPath'].endswith(folder + '/2019-05-26_10-33-20-img_1234.mov')][0]
    photo_asset = [a for a in immich.assets.values() if a['originalPath'].endswith(folder + '/2019-05-26_10-33-20-img_1234.heic')][0]
    video_asset['visibility'] = 'hidden'
    photo_asset['livePhotoVideoId'] = video_asset['id']
    return photo, video, photo_asset, video_asset

def test_live_photo_moved_is_linked_to_its_moved_video(library, immich):
    # Immich links the moved photo to the video with the same identifier
    #  which it read first, it can be the old one which is offline then
    photo, video, old_photo, old_video = _linked_live_photo(immich, library, 'Old')
    new_folder = os.path.join(library, '2019-05-May', 'New')
    os.makedirs(new_folder)
    shutil.move(photo, new_folder)
    shutil.move(video, new_folder)
    immich.scan()
    new_photo = immich.asset_for('New/2019-05-26_10-33-20-img_1234.heic')
    new_video = immich.asset_for('New/2019-05-26_10-33-20-img_1234.mov')
    new_video['visibility'] = 'hidden'
    new_photo['livePhotoVideoId'] = old_video['id']

    result = run_batch(immich)

    assert new_photo['livePhotoVideoId'] == new_video['id'], new_photo
    assert ('set_live_photo_video', new_photo['id'], new_video['id']) in immich.requests
    assert result[0] is True, result

@pytest.mark.parametrize('case', ['online', 'motion photo', 'two videos'])
def test_live_photo_link_which_is_not_repaired(library, immich, case):
    photo, video, photo_asset, video_asset = _linked_live_photo(immich, library, 'Old')
    if case == 'motion photo':
        # Its video is extracted by Immich, it is not a file of the library
        photo_asset['livePhotoVideoId'] = 'asset-of-immich'
    elif case == 'two videos':
        # The video it is linked to is offline but which one is its video
        #  cannot be told
        video_asset['isOffline'] = video_asset['isTrashed'] = True
        other = immich.add_asset(video_asset['originalPath'].replace('.mov', '.MOV'))
        other['visibility'] = 'hidden'
        immich.add_asset(video_asset['originalPath'].replace('.mov', '.mp4'))['visibility'] = 'hidden'
    linked = photo_asset['livePhotoVideoId']

    run_batch(immich)

    assert photo_asset['livePhotoVideoId'] == linked
    assert not [r for r in immich.requests if r[0] == 'set_live_photo_video'], immich.requests

@mock.patch('elodie.constants.dry_run', True)
@mock.patch('builtins.print')
def test_live_photo_link_dry_run(mock_print, library, immich):
    photo, video, old_photo, old_video = _linked_live_photo(immich, library, 'Old')
    old_video['isOffline'] = old_video['isTrashed'] = True
    new_video = immich.add_asset(old_video['originalPath'].replace('/Old/', '/New/'))
    new_video['visibility'] = 'hidden'
    old_photo['originalPath'] = old_photo['originalPath'].replace('/Old/', '/New/')

    run_batch(immich)

    assert old_photo['livePhotoVideoId'] == old_video['id']
