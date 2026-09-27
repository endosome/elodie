# Dates of files are the time of the camera's clock, the same on every
#  computer, see elodie/dates.py. The other tests run in GMT where local time
#  and UTC are the same, these run in other time zones.
import os
import shutil
import sys
import time
import unittest.mock as mock
from datetime import datetime

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.realpath(__file__))))

import helper
from elodie import dates
from elodie.external.pyexiftool import ExifTool
from elodie.filesystem import FileSystem
from elodie.media.photo import Photo
from elodie.media.text import Text
from elodie.media.video import Video

pytestmark = pytest.mark.skipif(not hasattr(time, 'tzset'), reason='time.tzset() is not available on Windows')

TIME_ZONES = ['Europe/Warsaw', 'America/New_York', 'Asia/Tokyo', 'UTC']


def copy_with_tags(name, fixture, *tags):
    temporary_folder, folder = helper.create_working_folder()
    path = os.path.join(folder, name)
    shutil.copyfile(helper.get_file(fixture), path)
    if tags:
        ExifTool().execute(b'-overwrite_original', *[t.encode() for t in tags] + [path.encode()])
    return temporary_folder, path


@pytest.mark.parametrize('zone', TIME_ZONES)
def test_photo_is_named_by_the_time_of_the_camera(zone):
    # Taken at 00:30 on July 1st, it must not end up in June where the
    #  computer is east of UTC
    temporary_folder, path = copy_with_tags('midnight.jpg', 'plain.jpg', '-EXIF:DateTimeOriginal=2021:07:01 00:30:00')
    library = os.path.join(temporary_folder, 'library')

    with helper.time_zone(zone):
        date_taken = Photo(path).get_date_taken()
        dest_path = FileSystem().process_file(path, library, Photo(path))
        modified = time.localtime(os.path.getmtime(dest_path))

    assert date_taken[:6] == (2021, 7, 1, 0, 30, 0), date_taken
    assert os.path.relpath(dest_path, library) == os.path.join('2021-07-Jul', 'Unknown Location', '2021-07-01_00-30-00-midnight.jpg'), dest_path
    # The modification time is the date in the time zone of the computer
    assert modified[:6] == (2021, 7, 1, 0, 30, 0), modified

@pytest.mark.parametrize('zone', TIME_ZONES)
def test_photo_without_a_date_is_named_by_its_local_modification_time(zone):
    temporary_folder, path = copy_with_tags('no-date.jpg', 'no-exif.jpg')
    with helper.time_zone(zone):
        os.utime(path, (0, time.mktime((2021, 7, 1, 0, 30, 0, 0, 0, -1))))
        date_taken = Photo(path).get_date_taken()

    assert date_taken[:6] == (2021, 7, 1, 0, 30, 0), date_taken

@pytest.mark.parametrize('zone', TIME_ZONES)
def test_video_with_a_time_zone_is_named_by_its_local_time(zone):
    # i.e. QuickTime:CreationDate of iPhones
    temporary_folder, path = copy_with_tags(
        'clip.mov', 'video.mov', '-QuickTime:CreationDate=2021:07:01 00:30:00+02:00', '-QuickTime:CreateDate=2021:06:30 22:30:00')

    with helper.time_zone(zone):
        date_taken = Video(path).get_date_taken()

    assert date_taken[:6] == (2021, 7, 1, 0, 30, 0), date_taken

@pytest.mark.parametrize('zone', TIME_ZONES)
def test_video_in_utc_is_named_by_the_time_where_it_was_taken(zone):
    # i.e. QuickTime:CreateDate of Android phones, taken at 20:00 in New York
    temporary_folder, path = copy_with_tags(
        'clip.mov', 'video.mov', '-QuickTime:CreationDate=', '-QuickTime:CreateDate=2021:07:02 00:00:00',
        '-QuickTime:MediaCreateDate=2021:07:02 00:00:00', '-XMP:GPSLatitude=40.7128', '-XMP:GPSLongitude=-74.006')

    with helper.time_zone(zone):
        date_taken = Video(path).get_date_taken()

    assert date_taken[:6] == (2021, 7, 1, 20, 0, 0), date_taken

@pytest.mark.parametrize('zone,expected', [
    ('Europe/Warsaw', (2021, 7, 2, 2, 0, 0)),
    ('America/New_York', (2021, 7, 1, 20, 0, 0)),
    ('UTC', (2021, 7, 2, 0, 0, 0)),
])
def test_video_in_utc_without_a_position_uses_the_time_zone_of_the_computer(zone, expected):
    temporary_folder, path = copy_with_tags(
        'clip.mov', 'video.mov', '-QuickTime:CreationDate=', '-QuickTime:CreateDate=2021:07:02 00:00:00',
        '-QuickTime:MediaCreateDate=2021:07:02 00:00:00', '-GPS:all=', '-Keys:GPSCoordinates=',
        '-XMP:GPSLatitude=', '-XMP:GPSLongitude=', '-UserData:GPSCoordinates=')

    with helper.time_zone(zone):
        video = Video(path)
        assert video.get_coordinate('latitude') is None
        date_taken = video.get_date_taken()

    assert date_taken[:6] == expected, date_taken

def test_video_in_utc_without_the_time_zone_finder():
    # tzfpy is optional, the time zone of the computer is used without it
    temporary_folder, path = copy_with_tags(
        'clip.mov', 'video.mov', '-QuickTime:CreationDate=', '-QuickTime:CreateDate=2021:07:02 00:00:00',
        '-QuickTime:MediaCreateDate=2021:07:02 00:00:00', '-XMP:GPSLatitude=40.7128', '-XMP:GPSLongitude=-74.006')

    with helper.time_zone('Europe/Warsaw'), mock.patch.object(dates, 'tzfpy', None):
        date_taken = Video(path).get_date_taken()

    assert date_taken[:6] == (2021, 7, 2, 2, 0, 0), date_taken

@pytest.mark.parametrize('zone', TIME_ZONES)
def test_text_date_is_kept_in_every_time_zone(zone):
    temporary_folder, path = copy_with_tags('notes.txt', 'valid-without-header.txt')

    with helper.time_zone(zone):
        Text(path).set_date_taken(datetime(2021, 7, 1, 0, 30, 0))
        date_taken = Text(path).get_date_taken()

    assert date_taken[:6] == (2021, 7, 1, 0, 30, 0), date_taken

@pytest.mark.parametrize('media_class,name,fixture', [(Photo, 'a.jpg', 'plain.jpg'), (Text, 'a.txt', 'valid.txt')])
def test_set_date_taken_in_dry_run_uses_the_date_as_it_is(media_class, name, fixture):
    temporary_folder, path = copy_with_tags(name, fixture)
    with helper.time_zone('Europe/Warsaw'), mock.patch('elodie.constants.dry_run', True):
        media = media_class(path)
        media.set_date_taken(datetime(2021, 7, 1, 0, 30, 0))

    assert media.get_metadata()['date_taken'][:6] == (2021, 7, 1, 0, 30, 0)

@pytest.mark.parametrize('date,utc', [
    # Daylight saving time is found out by mktime whatever tm_isdst says
    ((2021, 7, 1, 12, 0, 0), (2021, 7, 1, 10, 0, 0)),
    ((2021, 1, 1, 12, 0, 0), (2021, 1, 1, 11, 0, 0)),
])
def test_to_timestamp_with_daylight_saving_time(date, utc):
    with helper.time_zone('Europe/Warsaw'):
        seconds = dates.to_timestamp(dates.wall_clock(datetime(*date)))

    assert time.gmtime(seconds)[:6] == utc

def test_dates_before_1970_where_the_computer_cannot_handle_them(monkeypatch):
    # i.e. Windows, UTC is used then
    def fail(*args):
        raise OSError('timestamp out of range')
    monkeypatch.setattr(time, 'localtime', fail)
    monkeypatch.setattr(time, 'mktime', lambda t: (_ for _ in ()).throw(OverflowError('out of range')))

    assert dates.local_time(-315576000)[:6] == (1960, 1, 1, 12, 0, 0)
    assert dates.to_timestamp((1960, 1, 1, 12, 0, 0, 0, 0, 0)) == -315576000

@pytest.mark.parametrize('latitude,longitude,expected', [
    (52.23, 21.01, 'Europe/Warsaw'),
    (40.7128, -74.006, 'America/New_York'),
    (30.0, -30.0, 'Etc/GMT+2'),   # at sea
    (None, 21.01, None),
])
def test_time_zone_at(latitude, longitude, expected):
    zone = dates.time_zone_at(latitude, longitude)
    assert (zone.key if zone else None) == expected
