from __future__ import absolute_import
# Project imports
import calendar
import unittest.mock as mock
import os
import re
import shutil
import sys
import time
from datetime import datetime
from datetime import timedelta
from tempfile import gettempdir

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from . import helper
from elodie.config import load_config
from elodie.filesystem import FileSystem
from elodie.media.audio import Audio
from elodie.media.text import Text
from elodie.media.media import Media
from elodie.media.photo import Photo
from elodie.media.video import Video
import pytest

os.environ['TZ'] = 'GMT'

def test_create_directory_success():
    filesystem = FileSystem()
    folder = os.path.join(helper.temp_dir(), helper.random_string(10))
    status = filesystem.create_directory(folder)

    # Needs to be a subdirectory
    assert helper.temp_dir() != folder

    assert status == True
    assert os.path.isdir(folder) == True
    assert os.path.exists(folder) == True

    # Clean up
    shutil.rmtree(folder)


def test_create_directory_recursive_success():
    filesystem = FileSystem()
    folder = os.path.join(helper.temp_dir(), helper.random_string(10), helper.random_string(10))
    status = filesystem.create_directory(folder)

    # Needs to be a subdirectory
    assert helper.temp_dir() != folder

    assert status == True
    assert os.path.isdir(folder) == True
    assert os.path.exists(folder) == True

    shutil.rmtree(folder)

@mock.patch('elodie.filesystem.os.makedirs')
def test_create_directory_invalid_permissions(mock_makedirs):
    if os.name == 'nt':
       pytest.skip("It isn't implemented on Windows")

    # Mock the case where makedirs raises an OSError because the user does
    # not have permission to create the given directory.
    mock_makedirs.side_effect = OSError()

    filesystem = FileSystem()
    status = filesystem.create_directory('/apathwhichdoesnotexist/afolderwhichdoesnotexist')

    assert status == False

@mock.patch('elodie.constants.dry_run', True)
def test_create_directory_dry_run():
    filesystem = FileSystem()
    folder = os.path.join(helper.temp_dir(), helper.random_string(10), helper.random_string(10))
    status = filesystem.create_directory(folder)

    assert status == True
    assert not os.path.exists(os.path.dirname(folder)), folder

def test_delete_directory_if_empty():
    filesystem = FileSystem()
    folder = os.path.join(helper.temp_dir(), helper.random_string(10))
    os.makedirs(folder)

    assert os.path.isdir(folder) == True
    assert os.path.exists(folder) == True

    filesystem.delete_directory_if_empty(folder)

    assert os.path.isdir(folder) == False
    assert os.path.exists(folder) == False

def test_delete_directory_if_empty_when_not_empty():
    filesystem = FileSystem()
    folder = os.path.join(helper.temp_dir(), helper.random_string(10), helper.random_string(10))
    os.makedirs(folder)
    parent_folder = os.path.dirname(folder)

    assert os.path.isdir(folder) == True
    assert os.path.exists(folder) == True
    assert os.path.isdir(parent_folder) == True
    assert os.path.exists(parent_folder) == True

    filesystem.delete_directory_if_empty(parent_folder)

    assert os.path.isdir(folder) == True
    assert os.path.exists(folder) == True
    assert os.path.isdir(parent_folder) == True
    assert os.path.exists(parent_folder) == True

    shutil.rmtree(parent_folder)

def test_get_all_files_success():
    filesystem = FileSystem()
    folder = helper.populate_folder(5)

    files = set()
    files.update(filesystem.get_all_files(folder))
    shutil.rmtree(folder)

    length = len(files)
    assert length == 5, files

def test_get_all_files_by_extension():
    filesystem = FileSystem()
    folder = helper.populate_folder(5)

    files = set()
    files.update(filesystem.get_all_files(folder))
    length = len(files)
    assert length == 5, length

    files = set()
    files.update(filesystem.get_all_files(folder, 'jpg'))
    length = len(files)
    assert length == 3, length

    files = set()
    files.update(filesystem.get_all_files(folder, 'txt'))
    length = len(files)
    assert length == 2, length

    files = set()
    files.update(filesystem.get_all_files(folder, 'gif'))
    length = len(files)
    assert length == 0, length

    shutil.rmtree(folder)

def test_get_all_files_with_only_invalid_file():
    filesystem = FileSystem()
    folder = helper.populate_folder(0, include_invalid=True)

    files = set()
    files.update(filesystem.get_all_files(folder))
    shutil.rmtree(folder)

    length = len(files)
    assert length == 0, length

def test_get_all_files_with_invalid_file():
    filesystem = FileSystem()
    folder = helper.populate_folder(5, include_invalid=True)

    files = set()
    files.update(filesystem.get_all_files(folder))
    shutil.rmtree(folder)

    length = len(files)
    assert length == 5, length

def test_get_all_files_for_loop():
    filesystem = FileSystem()
    folder = helper.populate_folder(5)

    files = set()
    files.update()
    counter = 0
    for file in filesystem.get_all_files(folder):
        counter += 1
    shutil.rmtree(folder)

    assert counter == 5, counter

def test_get_current_directory():
    filesystem = FileSystem()
    assert os.getcwd() == filesystem.get_current_directory()

def test_get_file_name_definition_default():
    filesystem = FileSystem()
    name_template, definition = filesystem.get_file_name_definition()

    assert name_template == '%date-%original_name-%title.%extension', name_template
    assert definition == [[('date', '%Y-%m-%d_%H-%M-%S')], [('original_name', '')], [('title', '')], [('extension', '')]], definition #noqa

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-custom-filename' % gettempdir())
def test_get_file_name_definition_custom(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[File]
date=%Y-%m-%b
name=%date-%original_name.%extension
        """)
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    name_template, definition = filesystem.get_file_name_definition()

    if hasattr(load_config, 'config'):
        del load_config.config

    assert name_template == '%date-%original_name.%extension', name_template
    assert definition == [[('date', '%Y-%m-%b')], [('original_name', '')], [('extension', '')]], definition #noqa

def test_get_file_name_plain():
    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    assert file_name == helper.path_tz_fix('2015-12-05_00-59-26-plain.jpg'), file_name

def test_get_file_name_with_title():
    filesystem = FileSystem()
    media = Photo(helper.get_file('with-title.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    assert file_name == helper.path_tz_fix('2015-12-05_00-59-26-with-title-some-title.jpg'), file_name

def test_get_file_name_with_original_name_exif():
    filesystem = FileSystem()
    media = Photo(helper.get_file('with-filename-in-exif.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    assert file_name == helper.path_tz_fix('2015-12-05_00-59-26-foobar.jpg'), file_name

def test_get_file_name_with_original_name_title_exif():
    filesystem = FileSystem()
    media = Photo(helper.get_file('with-filename-and-title-in-exif.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    assert file_name == helper.path_tz_fix('2015-12-05_00-59-26-foobar-foobar-title.jpg'), file_name

def test_get_file_name_with_uppercase_and_spaces():
    filesystem = FileSystem()
    media = Photo(helper.get_file('Plain With Spaces And Uppercase 123.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    assert file_name == helper.path_tz_fix('2015-12-05_00-59-26-plain-with-spaces-and-uppercase-123.jpg'), file_name

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-filename-custom' % gettempdir())
def test_get_file_name_custom(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[File]
date=%Y-%m-%b
name=%date-%original_name.%extension
        """)
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    if hasattr(load_config, 'config'):
        del load_config.config

    assert file_name == helper.path_tz_fix('2015-12-dec-plain.jpg'), file_name

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-filename-custom-with-title' % gettempdir())
def test_get_file_name_custom_with_title(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[File]
date=%Y-%m-%d
name=%date-%original_name-%title.%extension
        """)
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    media = Photo(helper.get_file('with-title.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    if hasattr(load_config, 'config'):
        del load_config.config

    assert file_name == helper.path_tz_fix('2015-12-05-with-title-some-title.jpg'), file_name

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-filename-custom-with-empty-value' % gettempdir())
def test_get_file_name_custom_with_empty_value(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[File]
date=%Y-%m-%d
name=%date-%original_name-%title.%extension
        """)
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    if hasattr(load_config, 'config'):
        del load_config.config

    assert file_name == helper.path_tz_fix('2015-12-05-plain.jpg'), file_name

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-filename-custom-with-lowercase' % gettempdir())
def test_get_file_name_custom_with_lower_capitalization(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[File]
date=%Y-%m-%d
name=%date-%original_name-%title.%extension
capitalization=lower
        """)
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    if hasattr(load_config, 'config'):
        del load_config.config

    assert file_name == helper.path_tz_fix('2015-12-05-plain.jpg'), file_name

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-filename-custom-with-invalidcase' % gettempdir())
def test_get_file_name_custom_with_invalid_capitalization(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[File]
date=%Y-%m-%d
name=%date-%original_name-%title.%extension
capitalization=garabage
        """)
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    if hasattr(load_config, 'config'):
        del load_config.config

    assert file_name == helper.path_tz_fix('2015-12-05-plain.jpg'), file_name

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-filename-custom-with-uppercase' % gettempdir())
def test_get_file_name_custom_with_upper_capitalization(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[File]
date=%Y-%m-%d
name=%date-%original_name-%title.%extension
capitalization=upper
        """)
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    file_name = filesystem.get_file_name(media.get_metadata())

    if hasattr(load_config, 'config'):
        del load_config.config

    assert file_name == helper.path_tz_fix('2015-12-05-PLAIN.JPG'), file_name

def test_get_folder_path_plain():
    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Unknown Location'), path

def test_get_folder_path_with_title():
    filesystem = FileSystem()
    media = Photo(helper.get_file('with-title.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Unknown Location'), path

def test_get_folder_path_with_location():
    filesystem = FileSystem()
    media = Photo(helper.get_file('with-location.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Sunnyvale'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-original-with-camera-make-and-model' % gettempdir())
def test_get_folder_path_with_camera_make_and_model(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
full_path=%camera_make/%camera_model
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('Canon', 'Canon EOS REBEL T2i'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-original-with-camera-make-and-model-fallback' % gettempdir())
def test_get_folder_path_with_camera_make_and_model_fallback(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
full_path=%camera_make|"nomake"/%camera_model|"nomodel"
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    media = Photo(helper.get_file('no-exif.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('nomake', 'nomodel'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-int-in-component-path' % gettempdir())
def test_get_folder_path_with_int_in_config_component(mock_get_config_file):
    # gh-239
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
date=%Y
full_path=%date
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-combined-date-and-album' % gettempdir())
def test_get_folder_path_with_combined_date_and_album(mock_get_config_file):
    # gh-239
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
date=%Y-%m-%b
custom=%date %album
full_path=%custom
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    media = Photo(helper.get_file('with-album.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == '2015-12-Dec Test Album', path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-combined-date-album-location-fallback' % gettempdir())
def test_get_folder_path_with_album_and_location_fallback(mock_get_config_file):
    # gh-279
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
date=%Y-%m-%b
custom=%album
full_path=%custom|%city
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()

    # Test with no location
    media = Photo(helper.get_file('plain.jpg'))
    path_plain = filesystem.get_folder_path(media.get_metadata())

    # Test with City
    media = Photo(helper.get_file('with-location.jpg'))
    path_city = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_plain == 'Unknown Location', path_plain
    assert path_city == 'Sunnyvale', path_city


def test_get_folder_path_with_int_in_source_path():
    # gh-239
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder('int')

    origin = os.path.join(folder,'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    path = filesystem.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Unknown Location'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-original-default-unknown-location' % gettempdir())
def test_get_folder_path_with_original_default_unknown_location(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write('')
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015-12-Dec','Unknown Location'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-custom-path' % gettempdir())
def test_get_folder_path_with_custom_path(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[MapQuest]
key=czjNKTtFjLydLteUBwdgKAIC8OAbGLUx

[Directory]
date=%Y-%m-%d
location=%country-%state-%city
full_path=%date/%location
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    media = Photo(helper.get_file('with-location.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015-12-05','US-CA-Sunnyvale'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-fallback' % gettempdir())
def test_get_folder_path_with_fallback_folder(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
year=%Y
month=%m
full_path=%year/%month/%album|%"No Album Fool"/%month
        """)
#full_path=%year/%album|"No Album"
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015','12','No Album Fool','12'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-get-folder-path-with-with-more-than-two-levels' % gettempdir())
def test_get_folder_path_with_with_more_than_two_levels(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[MapQuest]
key=czjNKTtFjLydLteUBwdgKAIC8OAbGLUx

[Directory]
year=%Y
month=%m
location=%city, %state
full_path=%year/%month/%location
        """)

    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    media = Photo(helper.get_file('with-location.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config
        
    assert path == os.path.join('2015','12','Sunnyvale, CA'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-get-folder-path-with-with-only-one-level' % gettempdir())
def test_get_folder_path_with_with_only_one_level(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
year=%Y
full_path=%year
        """)

    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    media = Photo(helper.get_file('plain.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015'), path

def test_get_folder_path_with_location_and_title():
    filesystem = FileSystem()
    media = Photo(helper.get_file('with-location-and-title.jpg'))
    path = filesystem.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Sunnyvale'), path

def test_parse_folder_name_default():
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    place_name = {'default': u'CA', 'country': u'US', 'state': u'CA', 'city': u'Sunnyvale'}
    mask = '%city'
    location_parts = re.findall('(%[^%]+)', mask)
    path = filesystem.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'Sunnyvale', path

def test_parse_folder_name_multiple():
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    place_name = {'default': u'CA', 'country': u'US', 'state': u'CA', 'city': u'Sunnyvale'}
    mask = '%city-%state-%country'
    location_parts = re.findall('(%[^%]+)', mask)
    path = filesystem.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'Sunnyvale-CA-US', path

def test_parse_folder_name_static_chars():
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    place_name = {'default': u'CA', 'country': u'US', 'state': u'CA', 'city': u'Sunnyvale'}
    mask = '%city-is-the-city'
    location_parts = re.findall('(%[^%]+)', mask)
    path = filesystem.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'Sunnyvale-is-the-city', path

def test_parse_folder_name_key_not_found():
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    place_name = {'default': u'CA', 'country': u'US', 'state': u'CA'}
    mask = '%city'
    location_parts = re.findall('(%[^%]+)', mask)
    path = filesystem.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'CA', path

def test_parse_folder_name_key_not_found_with_static_chars():
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    place_name = {'default': u'CA', 'country': u'US', 'state': u'CA'}
    mask = '%city-is-not-found'
    location_parts = re.findall('(%[^%]+)', mask)
    path = filesystem.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'CA', path

def test_parse_folder_name_multiple_keys_not_found():
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    place_name = {'default': u'US', 'country': u'US'}
    mask = '%city-%state'
    location_parts = re.findall('(%[^%]+)', mask)
    path = filesystem.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'US', path

def test_process_file_invalid():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('invalid.jpg'), origin)

    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    assert destination is None

def test_process_file_plain():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    origin_checksum = helper.checksum(origin)
    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None
    assert origin_checksum is not None
    assert destination_checksum is not None
    assert origin_checksum_preprocess == origin_checksum
    assert helper.path_tz_fix(os.path.join('2015-12-Dec','Unknown Location','2015-12-05_00-59-26-photo.jpg')) in destination, destination

def test_process_file_with_title():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('with-title.jpg'), origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    origin_checksum = helper.checksum(origin)
    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None
    assert origin_checksum is not None
    assert destination_checksum is not None
    assert origin_checksum_preprocess == origin_checksum
    assert helper.path_tz_fix(os.path.join('2015-12-Dec','Unknown Location','2015-12-05_00-59-26-photo-some-title.jpg')) in destination, destination

def test_process_file_with_int_title():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('metadata-can-be-int.jpg'), origin)

    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert helper.path_tz_fix(os.path.join('2016-11-Nov','Unknown Location','2016-11-24_14-59-31-photo-854304532.jpg')) in destination, destination

def test_process_file_with_location():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('with-location.jpg'), origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    origin_checksum = helper.checksum(origin)
    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None
    assert origin_checksum is not None
    assert destination_checksum is not None
    assert origin_checksum_preprocess == origin_checksum
    assert helper.path_tz_fix(os.path.join('2015-12-Dec','Sunnyvale','2015-12-05_00-59-26-photo.jpg')) in destination, destination

def test_process_file_validate_original_checksum():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    origin_checksum = helper.checksum(origin)
    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None, origin_checksum_preprocess
    assert origin_checksum is not None, origin_checksum
    assert destination_checksum is not None, destination_checksum
    assert origin_checksum_preprocess == origin_checksum, (origin_checksum_preprocess, origin_checksum)


# See https://github.com/jmathai/elodie/issues/330
def test_process_file_no_exif_date_is_correct_gh_330():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('no-exif.jpg'), origin)

    atime = 1330712100
    utime = 1330712900
    os.utime(origin, (atime, utime))

    media = Photo(origin)
    metadata = media.get_metadata()

    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert '/2012-03-Mar/' in destination, destination
    assert '/2012-03-02_18-28-20' in destination, destination

def test_process_file_with_location_and_title():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('with-location-and-title.jpg'), origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    origin_checksum = helper.checksum(origin)
    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None
    assert origin_checksum is not None
    assert destination_checksum is not None
    assert origin_checksum_preprocess == origin_checksum
    assert helper.path_tz_fix(os.path.join('2015-12-Dec','Sunnyvale','2015-12-05_00-59-26-photo-some-title.jpg')) in destination, destination

def test_process_file_with_album():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('with-album.jpg'), origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    origin_checksum = helper.checksum(origin)
    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None
    assert origin_checksum is not None
    assert destination_checksum is not None
    assert origin_checksum_preprocess == origin_checksum
    assert helper.path_tz_fix(os.path.join('2015-12-Dec','Test Album','2015-12-05_00-59-26-photo.jpg')) in destination, destination

def test_process_file_with_album_and_title():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('with-album-and-title.jpg'), origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    origin_checksum = helper.checksum(origin)
    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None
    assert origin_checksum is not None
    assert destination_checksum is not None
    assert origin_checksum_preprocess == origin_checksum
    assert helper.path_tz_fix(os.path.join('2015-12-Dec','Test Album','2015-12-05_00-59-26-photo-some-title.jpg')) in destination, destination

def test_process_file_with_album_and_title_and_location():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('with-album-and-title-and-location.jpg'), origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    origin_checksum = helper.checksum(origin)
    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None
    assert origin_checksum is not None
    assert destination_checksum is not None
    assert origin_checksum_preprocess == origin_checksum
    assert helper.path_tz_fix(os.path.join('2015-12-Dec','Test Album','2015-12-05_00-59-26-photo-some-title.jpg')) in destination, destination

# gh-89 (setting album then title reverts album)
def test_process_video_with_album_then_title():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'movie.mov')
    shutil.copyfile(helper.get_file('video.mov'), origin)

    origin_checksum = helper.checksum(origin)

    origin_checksum_preprocess = helper.checksum(origin)
    media = Video(origin)
    media.set_album('test_album')
    media.set_title('test_title')
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    destination_checksum = helper.checksum(destination)

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

    assert origin_checksum_preprocess is not None
    assert origin_checksum is not None
    assert destination_checksum is not None
    assert origin_checksum_preprocess == origin_checksum
    assert helper.path_tz_fix(os.path.join('2015-01-Jan','test_album','2015-01-19_12-45-11-movie-test_title.mov')) in destination, destination

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-fallback-folder' % gettempdir())
def test_process_file_fallback_folder(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
date=%Y-%m
full_path=%date/%album|"fallback"
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert helper.path_tz_fix(os.path.join('2015-12', 'fallback', '2015-12-05_00-59-26-plain.jpg')) in destination, destination

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-multiple-directories' % gettempdir())
def test_process_twice_more_than_two_levels_of_directories(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
year=%Y
month=%m
day=%d
full_path=%year/%month/%day
        """)

    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert helper.path_tz_fix(os.path.join('2015','12','05', '2015-12-05_00-59-26-plain.jpg')) in destination, destination

    if hasattr(load_config, 'config'):
        del load_config.config

    media_second = Photo(destination)
    media_second.set_title('foo')
    destination_second = filesystem.process_file(destination, temporary_folder, media_second, allowDuplicate=True)

    if hasattr(load_config, 'config'):
        del load_config.config

    assert destination.replace('.jpg', '-foo.jpg') == destination_second, destination_second

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

def test_process_existing_file_without_changes():
    # gh-210
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    assert helper.path_tz_fix(os.path.join('2015-12-Dec', 'Unknown Location', '2015-12-05_00-59-26-plain.jpg')) in destination, destination

    media_second = Photo(destination)
    destination_second = filesystem.process_file(destination, temporary_folder, media_second, allowDuplicate=True)

    assert destination_second is None, destination_second

    shutil.rmtree(folder)
    shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-plugin-throw-error' % gettempdir())
def test_process_file_with_plugin_throw_error(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Plugins]
plugins=ThrowError
        """)

    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    if hasattr(load_config, 'config'):
        del load_config.config

    assert destination is None, destination

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-plugin-runtime-error' % gettempdir())
def test_process_file_with_plugin_runtime_error(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Plugins]
plugins=RuntimeError
        """)
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

    if hasattr(load_config, 'config'):
        del load_config.config

    assert '2015-12-Dec/Unknown Location/2015-12-05_00-59-26-plain.jpg' in destination, destination

def test_set_utime_with_exif_date():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media_initial = Photo(origin)
    metadata_initial = media_initial.get_metadata()

    initial_stat = os.stat(origin)
    initial_time = int(min(initial_stat.st_mtime, initial_stat.st_ctime))
    initial_checksum = helper.checksum(origin)

    assert initial_time != calendar.timegm(metadata_initial['date_taken'])

    filesystem.set_utime_from_metadata(media_initial.get_metadata(), media_initial.get_file_path())
    final_stat = os.stat(origin)
    final_checksum = helper.checksum(origin)

    media_final = Photo(origin)
    metadata_final = media_final.get_metadata()

    shutil.rmtree(folder)

    assert initial_stat.st_mtime != final_stat.st_mtime
    assert final_stat.st_mtime == calendar.timegm(metadata_final['date_taken'])
    assert initial_checksum == final_checksum

@pytest.fixture
def non_utc_timezone(monkeypatch):
    if not hasattr(time, 'tzset'):
        pytest.skip('time.tzset is not available on this platform')
    # POSIX TZ strings have inverted signs, this is UTC+05:00 without DST
    monkeypatch.setenv('TZ', 'TEST-05')
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()

def test_set_utime_with_exif_date_in_non_utc_timezone(non_utc_timezone):
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    filesystem.set_utime_from_metadata(media.get_metadata(), media.get_file_path())
    final_stat = os.stat(origin)

    shutil.rmtree(folder)

    # EXIF DateTimeOriginal of plain.jpg is 2015:12:05 00:59:26 local time
    assert time.localtime(final_stat.st_mtime)[:6] == (2015, 12, 5, 0, 59, 26), time.localtime(final_stat.st_mtime)

def test_process_file_utime_after_reimport_in_non_utc_timezone(non_utc_timezone):
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    # The file name of the first import has the date prefix which is
    #  used to set the utime when it is imported again
    first = filesystem.process_file(origin, folder, Photo(origin), allowDuplicate=True)
    second = filesystem.process_file(first, os.path.join(folder, 'reimport'), Photo(first), allowDuplicate=True)
    first_mtime = os.stat(first).st_mtime
    second_mtime = os.stat(second).st_mtime

    shutil.rmtree(folder)

    # EXIF DateTimeOriginal of plain.jpg is 2015:12:05 00:59:26 local time
    assert time.localtime(first_mtime)[:6] == (2015, 12, 5, 0, 59, 26), time.localtime(first_mtime)
    assert second_mtime == first_mtime, (first_mtime, second_mtime)

def test_set_utime_with_date_before_1970(monkeypatch):
    monkeypatch.setattr(time, 'gmtime', helper.windows_gmtime)
    monkeypatch.setattr(time, 'mktime', helper.windows_mktime)
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'text.txt')
    with open(origin, 'w') as f:
        f.write('{"date_taken":-315576000.0}\nsample text')

    media = Text(origin)
    filesystem.set_utime_from_metadata(media.get_metadata(), media.get_file_path())
    final_stat = os.stat(origin)

    shutil.rmtree(folder)

    assert final_stat.st_mtime == -315576000, final_stat.st_mtime

def test_set_utime_without_exif_date():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder,'photo.jpg')
    shutil.copyfile(helper.get_file('no-exif.jpg'), origin)

    media_initial = Photo(origin)
    metadata_initial = media_initial.get_metadata()

    initial_stat = os.stat(origin)
    initial_time = int(min(initial_stat.st_mtime, initial_stat.st_ctime))
    initial_checksum = helper.checksum(origin)

    assert initial_time == calendar.timegm(metadata_initial['date_taken'])

    filesystem.set_utime_from_metadata(media_initial.get_metadata(), media_initial.get_file_path())
    final_stat = os.stat(origin)
    final_checksum = helper.checksum(origin)

    media_final = Photo(origin)
    metadata_final = media_final.get_metadata()

    shutil.rmtree(folder)

    assert initial_time == final_stat.st_mtime
    assert final_stat.st_mtime == calendar.timegm(metadata_final['date_taken']), (final_stat.st_mtime, calendar.timegm(metadata_final['date_taken']))
    assert initial_checksum == final_checksum

def test_should_exclude_with_no_exclude_arg():
    filesystem = FileSystem()
    result = filesystem.should_exclude('/some/path')
    assert result == False, result

def test_should_exclude_with_non_matching_regex():
    filesystem = FileSystem()
    result = filesystem.should_exclude('/some/path', {re.compile('foobar')})
    assert result == False, result

def test_should_exclude_with_matching_regex():
    filesystem = FileSystem()
    result = filesystem.should_exclude('/some/path', {re.compile('some')})
    assert result == True, result

def test_should_not_exclude_with_multiple_with_non_matching_regex():
    filesystem = FileSystem()
    result = filesystem.should_exclude('/some/path', {re.compile('foobar'), re.compile('dne')})
    assert result == False, result

def test_should_exclude_with_multiple_with_one_matching_regex():
    filesystem = FileSystem()
    result = filesystem.should_exclude('/some/path', {re.compile('foobar'), re.compile('some')})
    assert result == True, result

def test_should_exclude_with_complex_matching_regex():
    filesystem = FileSystem()
    result = filesystem.should_exclude('/var/folders/j9/h192v5v95gd_fhpv63qzyd1400d9ct/T/T497XPQH2R/UATR2GZZTX/2016-04-Apr/London/2016-04-07_11-15-26-valid-sample-title.txt', {re.compile(r'London.*\.txt$')})
    assert result == True, result

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-does-not-exist' % gettempdir())
def test_get_folder_path_definition_default(mock_get_config_file):
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    path_definition = filesystem.get_folder_path_definition()
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == [[('date', '%Y-%m-%b')], [('album', ''), ('location', '%city'), ('"Unknown Location"', '')]], path_definition

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-date-location' % gettempdir())
def test_get_folder_path_definition_date_location(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
date=%Y-%m-%d
location=%country
full_path=%date/%location
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    path_definition = filesystem.get_folder_path_definition()
    expected = [
        [('date', '%Y-%m-%d')], [('location', '%country')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-get-folder-path-definition-location-date' % gettempdir())
def test_get_folder_path_definition_location_date(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
date=%Y-%m-%d
location=%country
full_path=%location/%date
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    path_definition = filesystem.get_folder_path_definition()
    expected = [
        [('location', '%country')], [('date', '%Y-%m-%d')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-cached' % gettempdir())
def test_get_folder_path_definition_cached(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
date=%Y-%m-%d
location=%country
full_path=%date/%location
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    path_definition = filesystem.get_folder_path_definition()
    expected = [
        [('date', '%Y-%m-%d')], [('location', '%country')]
    ]

    assert path_definition == expected, path_definition

    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
date=%uncached
location=%uncached
full_path=%date/%location
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    path_definition = filesystem.get_folder_path_definition()
    expected = [
        [('date', '%Y-%m-%d')], [('location', '%country')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-get-folder-path-definition-with-more-than-two-levels' % gettempdir())
def test_get_folder_path_definition_with_more_than_two_levels(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
year=%Y
month=%m
day=%d
full_path=%year/%month/%day
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    path_definition = filesystem.get_folder_path_definition()
    expected = [
        [('year', '%Y')], [('month', '%m')], [('day', '%d')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-get-folder-path-definition-with-only-one-level' % gettempdir())
def test_get_folder_path_definition_with_only_one_level(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
year=%Y
full_path=%year
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    path_definition = filesystem.get_folder_path_definition()
    expected = [
        [('year', '%Y')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-multi-level-custom' % gettempdir())
def test_get_folder_path_definition_multi_level_custom(mock_get_config_file):
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
year=%Y
month=%M
full_path=%year/%album|%month|%"foo"/%month
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    filesystem = FileSystem()
    path_definition = filesystem.get_folder_path_definition()
    
    expected = [[('year', '%Y')], [('album', ''), ('month', '%M'), ('"foo"', '')], [('month', '%M')]]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition


# Dry-run tests
@mock.patch('elodie.constants.dry_run', True)
@mock.patch('builtins.print')
@mock.patch('elodie.filesystem.shutil.move')
def test_file_operation_move_dry_run(mock_move, mock_print):
    """Test that move operation is logged but not executed in dry-run mode."""
    filesystem = FileSystem()
    result = filesystem._file_operation('move', '/src/file.jpg', '/dst/file.jpg')
    
    assert result == True
    mock_print.assert_called_once_with('[DRY-RUN] Would move: /src/file.jpg -> /dst/file.jpg')
    mock_move.assert_not_called()


@mock.patch('elodie.constants.dry_run', True)
@mock.patch('builtins.print')
@mock.patch('elodie.filesystem.compatability._copyfile')
def test_file_operation_copy_dry_run(mock_copy, mock_print):
    """Test that copy operation is logged but not executed in dry-run mode."""
    filesystem = FileSystem()
    result = filesystem._file_operation('copy', '/src/file.jpg', '/dst/file.jpg')
    
    assert result == True
    mock_print.assert_called_once_with('[DRY-RUN] Would copy: /src/file.jpg -> /dst/file.jpg')
    mock_copy.assert_not_called()


@mock.patch('elodie.constants.dry_run', True)
@mock.patch('builtins.print')
@mock.patch('elodie.filesystem.os.remove')
def test_file_operation_remove_dry_run(mock_remove, mock_print):
    """Test that remove operation is logged but not executed in dry-run mode."""
    filesystem = FileSystem()
    result = filesystem._file_operation('remove', '/tmp/file_original')
    
    assert result == True
    mock_print.assert_called_once_with('[DRY-RUN] Would remove: /tmp/file_original')
    mock_remove.assert_not_called()


@mock.patch('elodie.constants.dry_run', True)
@mock.patch('builtins.print')
@mock.patch('elodie.filesystem.send2trash')
def test_file_operation_send2trash_dry_run(mock_send2trash, mock_print):
    """Test that send2trash operation is logged but not executed in dry-run mode."""
    filesystem = FileSystem()
    result = filesystem._file_operation('send2trash', '/tmp/file.jpg')
    
    assert result == True
    mock_print.assert_called_once_with('[DRY-RUN] Would send2trash: /tmp/file.jpg')
    mock_send2trash.assert_not_called()


@mock.patch('elodie.constants.dry_run', False)
@mock.patch('elodie.filesystem.shutil.move')
def test_file_operation_move_normal_mode(mock_move):
    """Test that move operation is executed normally when not in dry-run mode."""
    filesystem = FileSystem()
    result = filesystem._file_operation('move', '/src/file.jpg', '/dst/file.jpg')
    
    assert result == True
    mock_move.assert_called_once_with('/src/file.jpg', '/dst/file.jpg')


@mock.patch('elodie.constants.dry_run', False)
@mock.patch('elodie.filesystem.compatability._copyfile')
def test_file_operation_copy_normal_mode(mock_copy):
    """Test that copy operation is executed normally when not in dry-run mode."""
    filesystem = FileSystem()
    result = filesystem._file_operation('copy', '/src/file.jpg', '/dst/file.jpg')
    
    assert result == True
    mock_copy.assert_called_once_with('/src/file.jpg', '/dst/file.jpg')


@mock.patch('elodie.constants.dry_run', False)
@mock.patch('elodie.filesystem.os.remove')
def test_file_operation_remove_normal_mode(mock_remove):
    """Test that remove operation is executed normally when not in dry-run mode."""
    filesystem = FileSystem()
    result = filesystem._file_operation('remove', '/tmp/file_original')
    
    assert result == True
    mock_remove.assert_called_once_with('/tmp/file_original')


@mock.patch('elodie.constants.dry_run', True)
@mock.patch('builtins.print')
@mock.patch('elodie.filesystem.FileSystem._file_operation')
@mock.patch('elodie.filesystem.FileSystem.create_directory')
def test_process_file_dry_run_move_operation(mock_create_dir, mock_file_op, mock_print):
    """Test that process_file uses _file_operation for moves in dry-run mode."""
    filesystem = FileSystem()
    
    # Create a temporary test file
    temp_dir = helper.temp_dir()
    src_file = helper.get_file('plain.jpg')
    test_file = os.path.join(temp_dir, 'test_plain.jpg')
    shutil.copyfile(src_file, test_file)
    
    try:
        # Mock the media object
        media = Photo(test_file)
        
        # Mock successful file operation
        mock_file_op.return_value = True
        mock_create_dir.return_value = True
        
        # Call process_file with move=True
        result = filesystem.process_file(test_file, temp_dir, media, move=True)
        
        # Verify that _file_operation was called for the move
        mock_file_op.assert_called()
        
        # Check that one of the calls was a move operation
        move_calls = [call for call in mock_file_op.call_args_list if call[0][0] == 'move']
        assert len(move_calls) > 0, "Expected at least one move operation call"
        
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)


@mock.patch('elodie.constants.dry_run', True)
@mock.patch('builtins.print')
@mock.patch('elodie.filesystem.FileSystem._file_operation')
@mock.patch('elodie.filesystem.FileSystem.create_directory')
def test_process_file_dry_run_copy_operation(mock_create_dir, mock_file_op, mock_print):
    """Test that process_file uses _file_operation for copies in dry-run mode."""
    filesystem = FileSystem()
    
    # Create a temporary test file
    temp_dir = helper.temp_dir()
    src_file = helper.get_file('plain.jpg')
    test_file = os.path.join(temp_dir, 'test_plain_copy.jpg')
    shutil.copyfile(src_file, test_file)
    
    try:
        # Mock the media object
        media = Photo(test_file)
        
        # Mock successful file operation
        mock_file_op.return_value = True
        mock_create_dir.return_value = True
        
        # Call process_file with move=False (copy mode)
        result = filesystem.process_file(test_file, temp_dir, media, move=False)
        
        # Verify that _file_operation was called
        mock_file_op.assert_called()
        
        # Check that _file_operation was called for file operations
        # In copy mode, we expect either a copy operation or move operations for exiftool handling
        operation_calls = [call[0][0] for call in mock_file_op.call_args_list]
        assert len(operation_calls) > 0, "Expected at least one file operation call"
        
        # Verify we have the expected operations (either copy or move for exiftool handling)
        expected_operations = {'copy', 'move'}
        assert any(op in expected_operations for op in operation_calls), f"Expected copy or move operations, got: {operation_calls}"
        
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

@mock.patch('elodie.constants.dry_run', True)
def test_process_file_dry_run_real():
    """Test that process_file in dry-run mode doesn't actually move files."""
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder, 'photo.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)
    
    # Should return destination path like normal mode
    assert destination is not None, "Should return destination path even in dry-run mode"
    
    # But original file should still exist and destination file should not exist
    assert os.path.exists(origin), "Original file should still exist in dry-run mode"
    assert not os.path.exists(destination), "Destination file should not exist in dry-run mode"
    
    # Clean up
    shutil.rmtree(temporary_folder)

# gh-533: importing must not modify the source file in any way.
SOURCE_FILES = [
    ('plain.jpg', Photo),
    ('video.mov', Video),
    ('audio.m4a', Audio),
    ('valid-without-header.txt', Text),
]

def _file_state(file_path):
    file_stat = os.stat(file_path)
    return {
        'ctime': file_stat.st_ctime_ns,
        'mtime': file_stat.st_mtime_ns,
        'inode': file_stat.st_ino,
        'checksum': helper.checksum(file_path),
    }

def _original_files(*folders):
    return [
        os.path.join(dirname, filename)
        for folder in folders
        for dirname, dirnames, filenames in os.walk(folder)
        for filename in filenames
        if filename.endswith('_original')
    ]

def _create_source(folder, file_name):
    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    os.utime(origin, (1000000000, 1000000000))
    return origin

@pytest.mark.parametrize('file_name,media_class', SOURCE_FILES)
def test_process_file_does_not_modify_source(file_name, media_class):
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, file_name)
    state_before = _file_state(origin)

    destination = filesystem.process_file(origin, folder_destination, media_class(origin), allowDuplicate=True)
    state_after = _file_state(origin)
    original_files = _original_files(folder, folder_destination)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert destination is not None
    assert state_after == state_before, (state_before, state_after)
    assert original_files == [], original_files

@pytest.mark.parametrize('file_name,media_class', SOURCE_FILES)
def test_process_file_sets_original_name_on_destination(file_name, media_class):
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, file_name)

    destination = filesystem.process_file(origin, folder_destination, media_class(origin), allowDuplicate=True)
    source_original_name = media_class(origin).get_original_name()
    destination_original_name = media_class(destination).get_original_name()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert source_original_name is None, source_original_name
    assert destination_original_name == file_name, destination_original_name

@pytest.mark.parametrize('file_name,media_class,original_name', [
    ('with-original-name.jpg', Photo, 'originalfilename.jpg'),
    ('with-original-name.txt', Text, 'originalname.txt'),
])
def test_process_file_keeps_existing_original_name(file_name, media_class, original_name):
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, file_name)

    destination = filesystem.process_file(origin, folder_destination, media_class(origin), allowDuplicate=True)
    destination_original_name = media_class(destination).get_original_name()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert destination_original_name == original_name, destination_original_name

@pytest.mark.skipif(helper.is_windows() or os.geteuid() == 0, reason='Requires POSIX permissions enforced for a non-root user')
def test_process_file_with_read_only_source():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, 'plain.jpg')
    os.chmod(origin, 0o444)
    os.chmod(folder, 0o555)
    state_before = _file_state(origin)

    try:
        destination = filesystem.process_file(origin, folder_destination, Photo(origin), allowDuplicate=True)
        state_after = _file_state(origin)
        destination_original_name = Photo(destination).get_original_name()
    finally:
        os.chmod(folder, 0o755)
        shutil.rmtree(folder)
        shutil.rmtree(folder_destination)

    assert state_after == state_before, (state_before, state_after)
    assert destination_original_name == 'plain.jpg', destination_original_name

def test_process_file_sets_destination_mtime_from_date_taken():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, 'plain.jpg')
    media = Photo(origin)
    date_taken = media.get_metadata()['date_taken']

    destination = filesystem.process_file(origin, folder_destination, media, allowDuplicate=True)
    destination_mtime = os.stat(destination).st_mtime

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert destination_mtime == calendar.timegm(date_taken), destination_mtime

@pytest.mark.parametrize('file_name,media_class', [
    ('plain.jpg', Photo),
    ('valid-without-header.txt', Text),
])
def test_process_file_move_sets_original_name(file_name, media_class):
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, file_name)

    destination = filesystem.process_file(origin, folder_destination, media_class(origin), move=True, allowDuplicate=True)
    origin_exists = os.path.exists(origin)
    destination_original_name = media_class(destination).get_original_name()
    original_files = _original_files(folder, folder_destination)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert not origin_exists, origin
    assert destination_original_name == file_name, destination_original_name
    assert original_files == [], original_files

@mock.patch('elodie.constants.dry_run', True)
def test_process_file_dry_run_does_not_modify_source():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, 'plain.jpg')
    state_before = _file_state(origin)

    destination = filesystem.process_file(origin, folder_destination, Photo(origin), allowDuplicate=True)
    state_after = _file_state(origin)
    destination_exists = os.path.exists(destination)
    original_files = _original_files(folder, folder_destination)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert state_after == state_before, (state_before, state_after)
    assert not destination_exists, destination
    assert original_files == [], original_files

def test_process_file_skips_already_imported_source():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, 'plain.jpg')

    first = filesystem.process_file(origin, folder_destination, Photo(origin))
    # The copy now contains the original name so its checksum differs from
    #  the source but the source should still be recognized as imported.
    checksums_differ = helper.checksum(origin) != helper.checksum(first)
    second = filesystem.process_file(origin, folder_destination, Photo(origin))

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert first is not None
    assert checksums_differ
    assert second is None, second

@mock.patch('elodie.constants.dry_run', True)
def test_process_file_dry_run_does_not_create_directories():
    filesystem = FileSystem()
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = _create_source(folder, 'plain.jpg')

    destination = filesystem.process_file(origin, folder_destination, Photo(origin), allowDuplicate=True)
    destination_contents = os.listdir(folder_destination)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert destination is not None
    assert destination_contents == [], destination_contents

# gh-534: folders which combine placeholders with each other or other text
PLACE_NAME = {'default': 'Chiang Mai', 'city': 'Chiang Mai', 'state': 'Chiang Mai Province', 'country': 'Thailand'}

def _get_folder_path_with_config(config_file, directory, file_name='plain.jpg', album=None, camera_make=None):
    with open(config_file, 'w') as f:
        f.write('[Directory]\n' + directory + '\n')
    if hasattr(load_config, 'config'):
        del load_config.config

    filesystem = FileSystem()
    metadata = Photo(helper.get_file(file_name)).get_metadata()
    metadata['album'] = album
    metadata['camera_make'] = camera_make
    with mock.patch('elodie.geolocation.place_name', return_value=PLACE_NAME):
        path = filesystem.get_folder_path(metadata)
        path_definition = filesystem.get_folder_path_definition()

    if hasattr(load_config, 'config'):
        del load_config.config
    return (path, path_definition)

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-combined-placeholders' % gettempdir())
def test_get_folder_path_with_placeholders_combined_in_one_folder(mock_get_config_file):
    path, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value,
        'month=%m\nyear=%Y\nlocation=%country, %city\nfull_path=%year/%month, %location'
    )

    assert path_definition == [[('year', '%Y')], [('%month, %location', '')]], path_definition
    assert path == os.path.join('2015', '12, Thailand, Chiang Mai'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-combined-placeholders-with-dash' % gettempdir())
def test_get_folder_path_with_placeholders_combined_with_dash(mock_get_config_file):
    # Example from the Readme
    path, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value,
        'location=%city, %state\nmonth=%m\nyear=%Y\nfull_path=%year-%month/%location'
    )

    assert path == os.path.join('2015-12', 'Chiang Mai, Chiang Mai Province'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-custom-with-masks' % gettempdir())
def test_get_folder_path_with_custom_using_masks(mock_get_config_file):
    path, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value,
        'month=%m\nyear=%Y\nlocation=%country, %city\ncustom=%month, %location\nfull_path=%year/%custom'
    )

    assert path == os.path.join('2015', '12, Thailand, Chiang Mai'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-combined-placeholders-fallback' % gettempdir())
def test_get_folder_path_with_combined_placeholders_fallback(mock_get_config_file):
    # A combined folder is only used if all of its placeholders have a value
    directory = 'month=%m\nyear=%Y\nfull_path=%year/%album - %month|%month'
    path_with_album, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value, directory, album='Test Album'
    )
    path_without_album, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value, directory
    )

    assert path_with_album == os.path.join('2015', 'Test Album - 12'), path_with_album
    assert path_without_album == os.path.join('2015', '12'), path_without_album

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-combined-placeholders-fallback-string' % gettempdir())
def test_get_folder_path_with_combined_placeholders_fallback_string(mock_get_config_file):
    directory = 'year=%Y\nfull_path=%year/%camera_make %album|"Unknown"'
    path_with_values, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value, directory, album='Test Album', camera_make='Canon'
    )
    path_with_some_values, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value, directory, camera_make='Canon'
    )

    assert path_with_values == os.path.join('2015', 'Canon Test Album'), path_with_values
    assert path_with_some_values == os.path.join('2015', 'Unknown'), path_with_some_values

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-combined-placeholders-partial' % gettempdir())
def test_get_folder_path_with_combined_placeholders_partial_without_fallback(mock_get_config_file):
    # Without a fallback the values which exist are used
    path, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value,
        'year=%Y\nfull_path=%year/%camera_make %album',
        camera_make='Canon'
    )

    assert path == os.path.join('2015', 'Canon'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-fallback-with-spaces' % gettempdir())
def test_get_folder_path_with_spaces_around_fallback(mock_get_config_file):
    path, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value,
        'year=%Y\nlocation=%city\nfull_path=%year/%album | %location',
        album='Test Album'
    )

    assert path_definition == [[('year', '%Y')], [('album', ''), ('location', '%city')]], path_definition
    assert path == os.path.join('2015', 'Test Album'), path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-named-custom-in-fallback' % gettempdir())
def test_get_folder_path_with_named_custom_in_fallback(mock_get_config_file):
    # Unchanged: %custom is used if any of its placeholders has a value
    path, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value,
        'date=%Y\nlocation=%city\ncustom=%date %album\nfull_path=%custom|%location'
    )

    assert path == '2015', path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-partial-placeholder-name' % gettempdir())
def test_get_folder_path_with_partial_placeholder_name(mock_get_config_file):
    # %dat is not %date
    path, path_definition = _get_folder_path_with_config(
        mock_get_config_file.return_value,
        'date=%Y\nfull_path=%dat|"Unknown"'
    )

    assert path == 'Unknown', path

