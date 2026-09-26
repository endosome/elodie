from __future__ import absolute_import
# Project imports

import os
import sys
import unittest 

from importlib import reload

from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from elodie import constants

BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

@pytest.fixture
def environ(monkeypatch):
    # constants reads environment variables when it is loaded.
    # Restore them and reload constants after the test so that changes
    #  (e.g. removing ELODIE_MAPQUEST_KEY) do not leak into other tests.
    yield monkeypatch
    monkeypatch.undo()
    reload(constants)

def test_debug():
    # This seems pointless but on Travis we explicitly modify the file to be True
    assert constants.debug == constants.debug, constants.debug

def test_application_directory_default(environ):
    environ.delenv('ELODIE_APPLICATION_DIRECTORY', raising=False)
    reload(constants)
    expected_path = '{}/.elodie'.format(os.path.expanduser('~'))
    assert constants.application_directory() == expected_path, constants.application_directory()

def test_application_directory_override_invalid(environ):
    environ.setenv('ELODIE_APPLICATION_DIRECTORY', '/foo/bar')
    reload(constants)
    directory_to_check = constants.application_directory()

    expected_path = '{}/.elodie'.format(os.path.expanduser('~'))
    assert directory_to_check == expected_path, constants.application_directory()

def test_application_directory_override_valid(environ):
    cwd = os.getcwd()
    environ.setenv('ELODIE_APPLICATION_DIRECTORY', cwd)
    reload(constants)
    directory_to_check = constants.application_directory()
    hash_db_to_check = constants.hash_db()

    assert directory_to_check == cwd, constants.application_directory()
    assert cwd in hash_db_to_check, constants.hash_db()

def test_hash_db():
    assert constants.hash_db() == '{}/hash.json'.format(constants.application_directory()), constants.hash_db()

def test_location_db():
    assert constants.location_db() == '{}/location.json'.format(constants.application_directory()), constants.location_db()

def test_script_directory():
    path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    assert path == constants.script_directory, constants.script_directory

def test_exiftool_config():
    path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    assert '{}/configs/ExifTool_config'.format(path) == constants.exiftool_config, constants.exiftool_config

def test_mapquest_base_url_default():
    assert constants.mapquest_base_url == 'https://www.mapquestapi.com', constants.mapquest_base_url

def test_mapquest_base_url_override(environ):
    environ.setenv('ELODIE_MAPQUEST_BASE_URL', 'foobar')
    reload(constants)
    url_to_check = constants.mapquest_base_url

    assert url_to_check == 'foobar', constants.mapquest_base_url

def test_mapquest_key_default(environ):
    environ.delenv('ELODIE_MAPQUEST_KEY', raising=False)
    reload(constants)
    assert constants.mapquest_key == None, constants.mapquest_key

def test_mapquest_key_override(environ):
    environ.setenv('ELODIE_MAPQUEST_KEY', 'foobar')
    reload(constants)
    key_to_check = constants.mapquest_key

    assert key_to_check == 'foobar', key_to_check

def test_accepted_language():
    assert constants.accepted_language == 'en', constants.accepted_language

def test_python_version():
    assert constants.python_version == sys.version_info.major, constants.python_version
