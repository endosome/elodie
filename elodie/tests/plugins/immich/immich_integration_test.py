# Tests of the Immich plugin against a real Immich, see server/setup.py:
#
#   cd elodie/tests/plugins/immich/server
#   export IMMICH_TEST_LIBRARY_PATH=$(mktemp -d)
#   docker compose up -d && eval "$(python setup.py)"
#   pytest elodie/tests/plugins/immich/immich_integration_test.py
#
# They are skipped without the environment variables of setup.py.
import os
import shutil
import sys
import time
import unittest.mock as mock
import uuid

import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import helper
from elodie import constants
from elodie.config import load_config
from elodie.media.photo import Photo
from elodie.plugins.immich.immich import Immich, ImmichApiClient, get_album_names

ENV = {name: os.environ.get('IMMICH_TEST_' + name) for name in (
    'API_URL', 'API_KEY', 'ADMIN_API_KEY', 'LIBRARY_ID', 'LIBRARY_PATH', 'EXTERNAL_PATH')}

pytestmark = [
    pytest.mark.skipif(not all(ENV.values()), reason='No Immich to test with, see server/setup.py'),
    # The tests scan the same library of one Immich
    pytest.mark.xdist_group('immich'),
]


class Server(object):
    """Access to the test Immich with all permissions to set up the tests."""

    def __init__(self, folder):
        self.session = requests.Session()
        self.session.headers['x-api-key'] = ENV['ADMIN_API_KEY']
        self.prefix = ENV['EXTERNAL_PATH'] + '/' + folder + '/'

    def call(self, method, path, **kwargs):
        response = self.session.request(method, ENV['API_URL'] + path, timeout=30, **kwargs)
        assert response.status_code < 400, (method, path, response.status_code, response.text)
        return response.json() if response.content else None

    def assets(self):
        """Assets of the test, by file name without the date Elodie adds."""
        items = self.call('POST', '/search/metadata', json={'filter': {
            'originalPath': {'startsWith': self.prefix}, 'isOffline': {'eq': False}}, 'size': 1000})
        return {a['originalFileName'].split('-')[-1]: a for a in items['assets']['items']}

    def scan(self, library):
        """Scan the library and wait until Immich has all files of the test."""
        expected = set()
        for dirname, _, filenames in os.walk(library):
            for filename in filenames:
                relative = os.path.relpath(os.path.join(dirname, filename), library)
                expected.add(self.prefix + relative.replace(os.sep, '/'))
        self.call('POST', '/libraries/%s/scan' % ENV['LIBRARY_ID'])
        for _ in range(120):
            paths = set(a['originalPath'] for a in self.assets().values())
            if paths == expected:
                return
            time.sleep(0.5)
        raise AssertionError('Immich has %s instead of %s' % (sorted(paths), sorted(expected)))

    def album(self, name):
        return [a for a in self.call('GET', '/albums') if a['albumName'] == name][0]

    def albums_of(self, name):
        asset_id = self.assets()[name]['id']
        return sorted(a['albumName'] for a in self.call('GET', '/albums', params={'assetId': asset_id}))


@pytest.fixture
def setup():
    """A folder of the library for the test and a config for the plugin."""
    folder = 'test-' + uuid.uuid4().hex[:8]
    library = os.path.join(ENV['LIBRARY_PATH'], folder)
    os.makedirs(library)
    with open('%s/config.ini' % constants.application_directory(), 'a') as f:
        f.write('\n[PluginImmich]\napi_url=%s\napi_key=%s\nexternal_library_path=%s/%s\n'
                'elodie_library_path=%s\n' % (ENV['API_URL'], ENV['API_KEY'], ENV['EXTERNAL_PATH'], folder, library))
    if hasattr(load_config, 'config'):
        del load_config.config
    # Album names of the test, the albums of all tests are in the same Immich
    def names(*albums):
        return ';'.join('%s %s' % (folder, a) for a in albums)
    yield library, Server(folder), names
    shutil.rmtree(library)
    if hasattr(load_config, 'config'):
        del load_config.config


def create_photo(library, name, album='', rating=''):
    folder = os.path.join(library, '2015-12-Dec', album or 'Unknown Location')
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    shutil.copyfile(helper.get_file('plain.jpg'), path)
    photo = Photo(path)
    photo.set_album(album)
    photo.set_rating(rating)
    return path


def file_state(library, name):
    paths = [os.path.join(d, f) for d, _, files in os.walk(library) for f in files if f.endswith(name)]
    assert len(paths) == 1, paths
    photo = Photo(paths[0])
    return get_album_names(photo.get_album()), photo.get_rating() == 5, paths[0]


def run_batch():
    with mock.patch.object(Immich, 'display') as display:
        result = Immich().batch()
    messages = [c[0][0] for c in display.call_args_list]
    assert result[0] is True, messages
    return result, messages


def test_client_against_immich():
    client = ImmichApiClient(ENV['API_URL'], ENV['API_KEY'])
    assert client.get_version() >= (3, 2, 0)
    # The plugin key can list albums and search
    assert isinstance(client.get_albums(), list)
    list(client.search_assets({'isFavorite': {'eq': True}}))

def test_search_follows_pages(setup):
    library, server, names = setup
    for name in ('a.jpg', 'b.jpg', 'c.jpg'):
        create_photo(library, name, rating=5)
    server.scan(library)
    client = ImmichApiClient(ENV['API_URL'], ENV['API_KEY'])

    with mock.patch.object(ImmichApiClient, 'PAGE_SIZE', 2):
        assets = list(client.search_assets({'originalPath': {'startsWith': server.prefix}}))

    assert sorted(a['originalFileName'] for a in assets) == ['a.jpg', 'b.jpg', 'c.jpg']

def test_first_sync_adds_albums_and_favorites_of_files(setup):
    library, server, names = setup
    create_photo(library, 'a.jpg', album=names('Summer', 'Family'), rating=5)
    create_photo(library, 'b.jpg', album=names('Summer'))
    create_photo(library, 'c.jpg')
    server.scan(library)

    result, messages = run_batch()

    assets = server.assets()
    assert result == (True, 2), messages
    assert server.albums_of('a.jpg') == [names('Family'), names('Summer')]
    assert server.albums_of('b.jpg') == [names('Summer')]
    assert server.albums_of('c.jpg') == []
    assert [assets[n]['isFavorite'] for n in ('a.jpg', 'b.jpg', 'c.jpg')] == [True, False, False]

def test_changes_in_immich_are_written_to_the_files(setup):
    library, server, names = setup
    create_photo(library, 'a.jpg', album=names('Summer'), rating=5)
    create_photo(library, 'b.jpg', album=names('Summer'))
    server.scan(library)
    run_batch()
    assets = server.assets()
    trip = server.call('POST', '/albums', json={'albumName': names('Trip')})
    server.call('PUT', '/albums/%s/assets' % trip['id'], json={'ids': [assets['a.jpg']['id']]})
    server.call('DELETE', '/albums/%s/assets' % server.album(names('Summer'))['id'], json={'ids': [assets['b.jpg']['id']]})
    server.call('PUT', '/assets', json={'ids': [assets['a.jpg']['id']], 'isFavorite': False})
    server.call('PUT', '/assets', json={'ids': [assets['b.jpg']['id']], 'isFavorite': True})

    run_batch()

    albums, favorite, path = file_state(library, 'a.jpg')
    assert (albums, favorite) == ([names('Summer'), names('Trip')], False)
    assert os.path.basename(os.path.dirname(path)) == names('Summer', 'Trip')
    albums, favorite, path = file_state(library, 'b.jpg')
    assert (albums, favorite) == ([], True)
    assert os.path.basename(os.path.dirname(path)) == 'Unknown Location'

    # Immich sees the moved files as new assets which get their albums and
    #  favorite back from the files.
    server.scan(library)
    run_batch()

    assets = server.assets()
    assert server.albums_of('a.jpg') == [names('Summer'), names('Trip')]
    assert server.albums_of('b.jpg') == []
    assert [assets[n]['isFavorite'] for n in ('a.jpg', 'b.jpg')] == [False, True]

    # Both sides agree now
    result, messages = run_batch()
    assert result == (True, 0), messages

def test_changes_made_with_elodie_are_applied_in_immich(setup):
    library, server, names = setup
    path = create_photo(library, 'a.jpg', album=names('Summer'))
    server.scan(library)
    run_batch()
    # Like elodie.py update --album which moves the file
    photo = Photo(path)
    photo.set_album(names('Wedding'))
    photo.set_rating(5)
    new_folder = os.path.join(library, '2015-12-Dec', names('Wedding'))
    os.makedirs(new_folder)
    shutil.move(path, os.path.join(new_folder, 'a.jpg'))
    server.scan(library)

    run_batch()

    assert server.albums_of('a.jpg') == [names('Wedding')]
    assert server.assets()['a.jpg']['isFavorite'] is True

def test_dry_run_changes_nothing(setup):
    library, server, names = setup
    path = create_photo(library, 'a.jpg', album=names('Summer'), rating=5)
    server.scan(library)

    with mock.patch('elodie.constants.dry_run', True), mock.patch('builtins.print'):
        run_batch()

    assert server.albums_of('a.jpg') == []
    assert server.assets()['a.jpg']['isFavorite'] is False
    assert file_state(library, 'a.jpg') == ([names('Summer')], True, path)
