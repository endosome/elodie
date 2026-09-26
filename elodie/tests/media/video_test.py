# -*- coding: utf-8
# Project imports
import os
import sys

import shutil
import tempfile
import time
import datetime

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import helper
from elodie.media.media import Media
from elodie.media.video import Video

os.environ['TZ'] = 'GMT'

def test_video_extensions():
    video = Video()
    extensions = video.extensions

    assert 'avi' in extensions
    assert 'm4v' in extensions
    assert 'mov' in extensions
    assert 'm4v' in extensions
    assert '3gp' in extensions
    assert 'mkv' in extensions
    assert 'webm' in extensions

    valid_extensions = Video.get_valid_extensions()

    assert extensions == valid_extensions, valid_extensions

def test_empty_album():
    video = Video(helper.get_file('video.mov'))
    assert video.get_album() is None

def test_get_camera_make():
    video = Video(helper.get_file('video.mov'))
    print(video.get_metadata())
    make = video.get_camera_make()

    assert make == 'Apple', make

def test_get_camera_model():
    video = Video(helper.get_file('video.mov'))
    model = video.get_camera_model()

    assert model == 'iPhone 5', model

def test_get_coordinate():
    video = Video(helper.get_file('video.mov'))
    coordinate = video.get_coordinate()

    assert coordinate == 38.1893, coordinate

def test_get_coordinate_latitude():
    video = Video(helper.get_file('video.mov'))
    coordinate = video.get_coordinate('latitude')

    assert coordinate == 38.1893, coordinate

def test_get_coordinate_longitude():
    video = Video(helper.get_file('video.mov'))
    coordinate = video.get_coordinate('longitude')

    assert coordinate == -119.9558, coordinate

def test_get_date_taken():
    video = Video(helper.get_file('video.mov'))
    date_taken = video.get_date_taken()

    assert date_taken == (2015, 1, 19, 12, 45, 11, 0, 19, 0), date_taken

def test_get_exiftool_attributes():
    video = Video(helper.get_file('video.mov'))
    exif = video.get_exiftool_attributes()

    assert exif is not None, exif
    assert exif is not False, exif

def test_is_valid():
    video = Video(helper.get_file('video.mov'))

    assert video.is_valid()

def test_is_not_valid():
    video = Video(helper.get_file('text.txt'))

    assert not video.is_valid()

def test_set_album():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    video = Video(origin)
    metadata = video.get_metadata()

    assert metadata['album'] is None, metadata['album']

    status = video.set_album('Test Album')

    assert status == True, status

    video_new = Video(origin)
    metadata_new = video_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata_new['album'] == 'Test Album', metadata_new['album']

def test_set_date_taken():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    video = Video(origin)
    status = video.set_date_taken(datetime.datetime(2013, 9, 30, 7, 6, 5))

    assert status == True, status

    video_new = Video(origin)
    metadata = video_new.get_metadata()

    date_taken = metadata['date_taken']

    shutil.rmtree(folder)

    assert date_taken == (2013, 9, 30, 7, 6, 5, 0, 273, 0), metadata['date_taken']

@pytest.mark.skipif(helper.is_windows(), reason='time.mktime does not support dates before 1970 on Windows')
def test_set_date_taken_before_1970(monkeypatch):
    monkeypatch.setattr(time, 'gmtime', helper.windows_gmtime)
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    video = Video(origin)
    status = video.set_date_taken(datetime.datetime(1960, 1, 1, 12, 0, 0))

    assert status == True, status

    video_new = Video(origin)
    date_taken = video_new.get_date_taken()

    shutil.rmtree(folder)

    assert date_taken == (1960, 1, 1, 12, 0, 0, 4, 1, 0), date_taken

def test_set_location():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    video = Video(origin)
    origin_metadata = video.get_metadata()

    # Verify that original video has different location info that what we
    #   will be setting and checking
    assert not helper.isclose(origin_metadata['latitude'], 11.1111111111), origin_metadata['latitude']
    assert not helper.isclose(origin_metadata['longitude'], 99.9999999999), origin_metadata['longitude']

    status = video.set_location(11.1111111111, 99.9999999999)

    assert status == True, status

    video_new = Video(origin)
    metadata = video_new.get_metadata()

    shutil.rmtree(folder)

    assert helper.isclose(metadata['latitude'], 11.1111111111), metadata['latitude']
    assert helper.isclose(metadata['longitude'], 99.9999999999), metadata['longitude']

def test_set_title():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    video = Video(origin)
    origin_metadata = video.get_metadata()

    status = video.set_title('my video title')

    assert status == True, status

    video_new = Video(origin)
    metadata = video_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata['title'] == 'my video title', metadata['title']

def test_set_title_non_ascii():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    video = Video(origin)
    origin_metadata = video.get_metadata()

    unicode_title = u'形声字 / 形聲字' 
    status = video.set_title(unicode_title)

    assert status == True, status

    video_new = Video(origin)
    metadata = video_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata['title'] == unicode_title, metadata['title']

# gh-457: mkv and webm store the date as Matroska:DateTimeOriginal
@pytest.mark.parametrize('file_name', ['video.mkv', 'video.webm'])
def test_get_date_taken_matroska(file_name):
    video = Video(helper.get_file(file_name))
    date_taken = video.get_date_taken()

    assert video.is_valid()
    assert date_taken == helper.time_convert((2019, 7, 4, 12, 0, 0, 3, 185, 0)), date_taken

@pytest.mark.parametrize('value,expected', [
    ('2019-07-04', '2019:07:04 00:00:00'),
    ('2019:07:04', '2019:07:04 00:00:00'),
    ('2019-07-04T12:30:15', '2019:07:04 12:30:15'),
    ('2019-07-04T12:30', '2019:07:04 12:30:00'),
    ('2019-07-04 12:30:15+02:00', '2019:07:04 12:30:15+02:00'),
    ('2019:07:04 12:00:00Z', '2019:07:04 12:00:00Z'),
    ('2015:01:19 12:45:11-08:00', '2015:01:19 12:45:11-08:00'),
    ('2019', '2019'),
    ('', ''),
])
def test_normalize_date_string(value, expected):
    assert Video().normalize_date_string(value) == expected

