#!/usr/bin/env python

import os
import shutil
import sys
import tempfile
import time
import pytest

# Add the parent directories to sys.path so we can import elodie modules and test helpers
test_dir = os.path.dirname(os.path.abspath(__file__))
elodie_root = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, elodie_root)
sys.path.insert(0, test_dir)

from elodie.external.pyexiftool import ExifTool
from elodie.dependencies import get_exiftool
from elodie import constants


# The tests run in GMT unless they set another time zone with
#  helper.time_zone(). ELODIE_TEST_TZ runs them in another one, i.e. to find
#  tests which only pass in UTC. time.tzset() makes all time functions use
#  it, not only some of them.
os.environ['TZ'] = os.environ.get('ELODIE_TEST_TZ', 'GMT')
if hasattr(time, 'tzset'):
    time.tzset()


def pytest_configure(config):
    # Registered by pytest-xdist as well. Tests in the same group run in the
    #  same worker with pytest -n auto --dist loadgroup.
    config.addinivalue_line(
        'markers', 'xdist_group(name): run the tests of a group in one worker'
    )

@pytest.fixture(scope="session", autouse=True)
def setup_exiftool():
    """Start ExifTool once for the entire test session."""
    exiftool_addedargs = [
        u'-config',
        u'"{}"'.format(constants.exiftool_config)
    ]
    exiftool = ExifTool(executable_=get_exiftool(), addedargs=exiftool_addedargs)
    exiftool.start()
    
    yield
    
    # Stop ExifTool after all tests complete
    try:
        exiftool.terminate()
    except:
        pass

@pytest.fixture(scope="function", autouse=True)
def setup_test_environment():
    """
    Set up the test environment before each test function.
    This creates a fresh temporary application directory and config file for each test.
    """
    # elodie caches the config and the MapQuest key for the lifetime of the
    #  process. Reset them so each test uses its own config and does not
    #  depend on which tests ran before it.
    from elodie.config import load_config
    from elodie import geolocation
    if hasattr(load_config, 'config'):
        del load_config.config
    geolocation.__KEY__ = None
    geolocation.__PREFER_ENGLISH_NAMES__ = None
    # The shared Db belongs to the application directory of one test
    from elodie.localstorage import Db
    Db._shared = None

    # Get the test directory
    test_directory = os.path.dirname(os.path.abspath(__file__))

    # Create a temporary directory to use for the application directory while running tests
    temporary_application_directory = tempfile.mkdtemp('-elodie-tests')
    os.environ['ELODIE_APPLICATION_DIRECTORY'] = temporary_application_directory
    
    # Copy config.ini-sample over to the test application directory
    temporary_config_file_sample = '{}/config.ini-sample'.format(
        os.path.dirname(os.path.dirname(test_directory))
    )
    temporary_config_file = '{}/config.ini'.format(temporary_application_directory)
    shutil.copy2(
        temporary_config_file_sample,
        temporary_config_file,
    )
    
    # Read the sample config file and store contents to be replaced
    with open(temporary_config_file_sample, 'r') as f:
        config_contents = f.read()
    
    # Set the mapquest key in the temporary config file and write it to the temporary application directory
    # Check if MAPQUEST_KEY environment variable is set
    if 'MAPQUEST_KEY' in os.environ:
        config_contents = config_contents.replace('your-api-key-goes-here', os.environ['MAPQUEST_KEY'])
    else:
        # If not set, tests that require it will fail with a clear message
        config_contents = config_contents.replace('your-api-key-goes-here', 'test-key-not-set')
    
    with open(temporary_config_file, 'w+') as f:
        f.write(config_contents)
    
    # Yield control to tests
    yield

    # What the test changed in the shared Db is written while its
    #  application directory still exists
    try:
        Db.reset_shared()
    except OSError:
        Db._shared = None

    # Cleanup after each test
    try:
        shutil.rmtree(temporary_application_directory)
    except OSError:
        pass  # Directory might already be cleaned up

    # The folders of helper.create_working_folder(), many tests only remove
    #  the folder inside it. The helper is loaded as helper and as
    #  elodie.tests.helper, each with its own list.
    for name in ('helper', 'elodie.tests.helper'):
        module = sys.modules.get(name)
        while module is not None and module.working_folders:
            shutil.rmtree(module.working_folders.pop(), ignore_errors=True)


# Answers of the fake MapQuest, so that the tests do not use the API, which
#  is billed. A real key and ELODIE_LIVE_MAPQUEST=1 use the real one.
def _mq_location(city=None, state=None, country='US', lat=0.0, lng=0.0):
    location = {'latLng': {'lat': lat, 'lng': lng}, 'geocodeQuality': 'CITY'}
    for i, (kind, value) in enumerate(
            (('City', city), ('State', state), ('Country', country)), 1):
        if value:
            location['adminArea%dType' % i] = kind
            location['adminArea%d' % i] = value
    return location

# Reverse lookups by latitude and longitude, rounded to 2 decimals
_MQ_REVERSE = {
    (37.37, -122.03): _mq_location('Sunnyvale', 'CA'),
    (29.76, -95.37): _mq_location('Houston', 'TX'),
    (33.66, -95.56): _mq_location('Paris', 'TX'),
    (-33.97, 151.10): _mq_location('Sydney', 'NSW', 'AU'),
    (37.85, -122.48): _mq_location('San Francisco', 'CA'),
    (38.19, -119.96): _mq_location('Pinecrest', 'CA'),
    (40.71, -74.01): _mq_location('New York', 'NY'),
    (37.77, -122.42): _mq_location('San Francisco', 'CA'),
    (38.5, -117.0): _mq_location(None, 'NV'),
    (40.57, 8.32): _mq_location('Porto Torres', 'Sardinia', 'IT'),
    (46.84, 29.62): _mq_location('Tiraspol', None, 'MD'),
    (51.43, 12.11): _mq_location('Halle', 'Saxony-Anhalt', 'DE'),
    (51.52, 0.16): _mq_location('Rainham', 'England', 'GB'),
}

# Forward lookups by name
_MQ_FORWARD = {
    'Sunnyvale, CA': _mq_location('Sunnyvale', 'CA', lat=37.37188, lng=-122.03751),
    'San Francisco, CA': _mq_location('San Francisco', 'CA', lat=37.77493, lng=-122.41942),
    'New York, NY': _mq_location('New York', 'NY', lat=40.71273, lng=-74.00602),
    'Paris, Texas': _mq_location('Paris', 'TX', lat=33.6609, lng=-95.5556),
}


def fake_mapquest_response(url):
    import json
    import urllib.parse
    import requests
    params = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(url).query).items()}
    status, body = 200, {'info': {'statuscode': 0}}
    if params.get('key') in (None, '', 'invalid_key'):
        status, body = 401, {'info': {'statuscode': 403}}
    elif 'lat' in params:
        location = _MQ_REVERSE.get((round(float(params['lat']), 2), round(float(params['lon']), 2)))
        if abs(float(params['lat'])) > 90 or abs(float(params['lon'])) > 180:
            body = {'info': {'statuscode': 400}}
        else:
            body['results'] = [{'locations': [location or {'source': 'FALLBACK'}]}]
    else:
        location = _MQ_FORWARD.get(params.get('location'))
        body['results'] = [{'locations': [location or {'source': 'FALLBACK'}]}]
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode()
    return response


@pytest.fixture(scope="function", autouse=True)
def fake_mapquest(monkeypatch):
    import requests
    if os.environ.get('ELODIE_LIVE_MAPQUEST'):
        yield
        return
    real_get = requests.Session.get

    def get(self, url, *args, **kwargs):
        if url.startswith('https://www.mapquestapi.com'):
            return fake_mapquest_response(url)
        return real_get(self, url, *args, **kwargs)

    monkeypatch.setattr(requests.Session, 'get', get)
    yield
