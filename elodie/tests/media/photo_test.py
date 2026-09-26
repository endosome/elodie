# -*- coding: utf-8
# Project imports
import os
import sys

from datetime import datetime
import shutil
import tempfile
import time
import unittest.mock as mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import helper
from elodie.media.media import Media
from elodie.media.photo import Photo

os.environ['TZ'] = 'GMT'

def test_photo_extensions():
    photo = Photo()
    extensions = photo.extensions

    assert 'arw' in extensions
    assert 'cr2' in extensions
    assert 'dng' in extensions
    assert 'gif' in extensions
    assert 'heic' in extensions
    assert 'jpg' in extensions
    assert 'jpeg' in extensions
    assert 'nef' in extensions
    assert 'png' in extensions
    assert 'rw2' in extensions
    assert 'webp' in extensions
    for extension in ('avif', 'cr3', 'erf', 'heif', 'hif', 'iiq', 'mrw', 'nrw',
                      'orf', 'pef', 'raf', 'raw', 'srw', 'tif', 'tiff', 'x3f'):
        assert extension in extensions, extension

    valid_extensions = Photo.get_valid_extensions()

    assert extensions == valid_extensions, valid_extensions

def test_empty_album():
    photo = Photo(helper.get_file('plain.jpg'))
    assert photo.get_album() is None

def test_has_album():
    photo = Photo(helper.get_file('with-album.jpg'))
    album = photo.get_album()

    assert album == 'Test Album', album

def test_is_valid():
    photo = Photo(helper.get_file('plain.jpg'))

    assert photo.is_valid()

def test_is_not_valid():
    photo = Photo(helper.get_file('text.txt'))

    assert not photo.is_valid()

def test_get_metadata_of_invalid_photo():
    photo = Photo(helper.get_file('invalid.jpg'))
    metadata = photo.get_metadata()

    assert metadata is None

def test_get_coordinate_default():
    photo = Photo(helper.get_file('with-location.jpg'))
    coordinate = photo.get_coordinate()

    assert helper.isclose(coordinate,37.3667027222), coordinate

def test_get_coordinate_latitude():
    photo = Photo(helper.get_file('with-location.jpg'))
    coordinate = photo.get_coordinate('latitude')

    assert helper.isclose(coordinate,37.3667027222), coordinate

def test_get_coordinate_latitude_minus():
    photo = Photo(helper.get_file('with-location-inv.jpg'))
    coordinate = photo.get_coordinate('latitude')

    assert helper.isclose(coordinate,-37.3667027222), coordinate

def test_get_coordinate_longitude():
    photo = Photo(helper.get_file('with-location.jpg'))
    coordinate = photo.get_coordinate('longitude')

    assert helper.isclose(coordinate,-122.033383611), coordinate

def test_get_coordinate_longitude_plus():
    photo = Photo(helper.get_file('with-location-inv.jpg'))
    coordinate = photo.get_coordinate('longitude')

    assert helper.isclose(coordinate,122.033383611), coordinate

def test_get_coordinates_without_exif():
    photo = Photo(helper.get_file('no-exif.jpg'))
    latitude = photo.get_coordinate('latitude')
    longitude = photo.get_coordinate('longitude')

    assert latitude is None, latitude
    assert longitude is None, longitude

def test_get_coordinates_with_zero_coordinate():
    photo = Photo(helper.get_file('with-location-zero-coordinate.jpg'))
    latitude = photo.get_coordinate('latitude')
    longitude = photo.get_coordinate('longitude')

    assert helper.isclose(latitude,51.55325), latitude
    assert helper.isclose(longitude,-0.00417777777778), longitude

def test_get_coordinates_with_null_coordinate():
    photo = Photo(helper.get_file('with-null-coordinates.jpg'))
    latitude = photo.get_coordinate('latitude')
    longitude = photo.get_coordinate('longitude')

    assert latitude is None, latitude
    assert longitude is None, longitude

def test_get_date_taken():
    photo = Photo(helper.get_file('plain.jpg'))
    date_taken = photo.get_date_taken()

    #assert date_taken == (2015, 12, 5, 0, 59, 26, 5, 339, 0), date_taken
    assert date_taken == helper.time_convert((2015, 12, 5, 0, 59, 26, 5, 339, 0)), date_taken

def test_get_date_taken_without_exif():
    source = helper.get_file('no-exif.jpg')
    photo = Photo(source)
    date_taken = photo.get_date_taken()

    date_taken_from_file = time.gmtime(min(os.path.getmtime(source), os.path.getctime(source)))

    assert date_taken == date_taken_from_file, date_taken

def test_get_camera_make():
    photo = Photo(helper.get_file('with-location.jpg'))
    make = photo.get_camera_make()

    assert make == 'Canon', make

def test_get_camera_make_not_set():
    photo = Photo(helper.get_file('no-exif.jpg'))
    make = photo.get_camera_make()

    assert make is None, make

def test_get_camera_model():
    photo = Photo(helper.get_file('with-location.jpg'))
    model = photo.get_camera_model()

    assert model == 'Canon EOS REBEL T2i', model

def test_get_camera_model_not_set():
    photo = Photo(helper.get_file('no-exif.jpg'))
    model = photo.get_camera_model()

    assert model is None, model

def test_get_title_when_exif_value_is_int():
    photo = Photo(helper.get_file('metadata-can-be-int.jpg'))
    title = photo.get_title()

    assert title == '854304532', title

def test_is_valid():
    photo = Photo(helper.get_file('with-location.jpg'))

    assert photo.is_valid()

def test_is_not_valid():
    photo = Photo(helper.get_file('text.txt'))

    assert not photo.is_valid()

def test_is_valid_when_imghdr_fails():
    photo = Photo(helper.get_file('imghdr-error.jpg'))

    assert photo.is_valid()


def test_set_album():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    metadata = photo.get_metadata()

    assert metadata['album'] is None, metadata['album']

    status = photo.set_album('Test Album')

    assert status == True, status

    photo_new = Photo(origin)
    metadata_new = photo_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata_new['album'] == 'Test Album', metadata_new['album']

def test_set_date_taken_with_missing_datetimeoriginal():
    # When datetimeoriginal (or other key) is missing we have to add it gh-74
    # https://github.com/jmathai/elodie/issues/74
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('no-exif.jpg'), origin)

    photo = Photo(origin)
    status = photo.set_date_taken(datetime(2013, 9, 30, 7, 6, 5))

    assert status == True, status

    photo_new = Photo(origin)
    metadata = photo_new.get_metadata()

    date_taken = metadata['date_taken']

    shutil.rmtree(folder)

    #assert date_taken == (2013, 9, 30, 7, 6, 5, 0, 273, 0), metadata['date_taken']
    assert date_taken == helper.time_convert((2013, 9, 30, 7, 6, 5, 0, 273, 0)), metadata['date_taken']

def test_set_date_taken():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    status = photo.set_date_taken(datetime(2013, 9, 30, 7, 6, 5))

    assert status == True, status

    photo_new = Photo(origin)
    metadata = photo_new.get_metadata()

    date_taken = metadata['date_taken']

    shutil.rmtree(folder)

    #assert date_taken == (2013, 9, 30, 7, 6, 5, 0, 273, 0), metadata['date_taken']
    assert date_taken == helper.time_convert((2013, 9, 30, 7, 6, 5, 0, 273, 0)), metadata['date_taken']

@pytest.mark.skipif(helper.is_windows(), reason='time.mktime does not support dates before 1970 on Windows')
def test_set_date_taken_before_1970(monkeypatch):
    monkeypatch.setattr(time, 'gmtime', helper.windows_gmtime)
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    status = photo.set_date_taken(datetime(1960, 1, 1, 12, 0, 0))

    assert status == True, status

    photo_new = Photo(origin)
    date_taken = photo_new.get_date_taken()

    shutil.rmtree(folder)

    assert date_taken == (1960, 1, 1, 12, 0, 0, 4, 1, 0), date_taken

def test_set_location():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    origin_metadata = photo.get_metadata()

    # Verify that original photo has different location info that what we
    #   will be setting and checking
    assert not helper.isclose(origin_metadata['latitude'], 11.1111111111), origin_metadata['latitude']
    assert not helper.isclose(origin_metadata['longitude'], 99.9999999999), origin_metadata['longitude']

    status = photo.set_location(11.1111111111, 99.9999999999)

    assert status == True, status

    photo_new = Photo(origin)
    metadata = photo_new.get_metadata()

    shutil.rmtree(folder)

    assert helper.isclose(metadata['latitude'], 11.1111111111), metadata['latitude']
    assert helper.isclose(metadata['longitude'], 99.9999999999), metadata['longitude']

def test_set_location_minus():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    origin_metadata = photo.get_metadata()

    # Verify that original photo has different location info that what we
    #   will be setting and checking
    assert not helper.isclose(origin_metadata['latitude'], 11.1111111111), origin_metadata['latitude']
    assert not helper.isclose(origin_metadata['longitude'], 99.9999999999), origin_metadata['longitude']

    status = photo.set_location(-11.1111111111, -99.9999999999)

    assert status == True, status

    photo_new = Photo(origin)
    metadata = photo_new.get_metadata()

    shutil.rmtree(folder)

    assert helper.isclose(metadata['latitude'], -11.1111111111), metadata['latitude']
    assert helper.isclose(metadata['longitude'], -99.9999999999), metadata['longitude']

def test_set_title():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    origin_metadata = photo.get_metadata()

    status = photo.set_title('my photo title')

    assert status == True, status

    photo_new = Photo(origin)
    metadata = photo_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata['title'] == 'my photo title', metadata['title']

def test_set_title_non_ascii():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    origin_metadata = photo.get_metadata()

    unicode_title = u'形声字 / 形聲字'

    status = photo.set_title(unicode_title)
    assert status == True, status

    photo_new = Photo(origin)
    metadata = photo_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata['title'] == unicode_title, metadata['title']

# Photo files of each supported type and the date they were taken. Camera raw
#  files are downloaded from elodie-test-assets, see helper.get_asset().
PHOTO_TYPE_FILES = [
    ('photo.heic', (2019, 5, 26, 10, 33, 20, 6, 146, 0)),
    ('photo.png', (2015, 1, 18, 12, 1, 1, 6, 18, 0)),
    ('photo.webp', (2019, 7, 4, 12, 0, 0, 3, 185, 0)),
    ('photo.tif', (2020, 6, 15, 10, 30, 0, 0, 167, 0)),
    ('photo.tiff', (2020, 6, 15, 10, 30, 0, 0, 167, 0)),
    ('photo.heif', (2020, 6, 15, 10, 30, 0, 0, 167, 0)),
    ('photo.hif', (2020, 6, 15, 10, 30, 0, 0, 167, 0)),
    ('photo.avif', (2020, 6, 15, 10, 30, 0, 0, 167, 0)),
] + [
    (asset['name'], None) for asset in helper.ASSETS['assets']
]

def _get_photo_type_file(file_name, date):
    if date is not None:
        return (helper.get_file(file_name), helper.time_convert(date))

    return (helper.get_asset(file_name), helper.get_asset_date_taken(file_name))

@pytest.mark.parametrize('file_name,date', PHOTO_TYPE_FILES)
def test_various_types_get(file_name, date):
    photo_file, date = _get_photo_type_file(file_name, date)
    temporary_folder, folder = helper.create_working_folder()
    origin = os.path.join(folder, file_name)
    shutil.copyfile(photo_file, origin)

    photo = Photo(origin)
    metadata = photo.get_metadata()

    shutil.rmtree(temporary_folder)

    assert metadata is not None, '{} is not a valid photo'.format(file_name)
    assert metadata['date_taken'] == date, '{} date {}'.format(file_name, metadata['date_taken'])

@pytest.mark.parametrize('file_name,date', PHOTO_TYPE_FILES)
def test_various_types_set(file_name, date):
    photo_file, date = _get_photo_type_file(file_name, date)
    temporary_folder, folder = helper.create_working_folder()
    origin = os.path.join(folder, file_name)
    shutil.copyfile(photo_file, origin)

    photo = Photo(origin)
    origin_metadata = photo.get_metadata()
    status = photo.set_location(11.1111111111, 99.9999999999)

    photo_new = Photo(origin)
    metadata = photo_new.get_metadata()

    shutil.rmtree(temporary_folder)

    assert origin_metadata is not None, '{} is not a valid photo'.format(file_name)
    assert status == True, status
    assert metadata['date_taken'] == date, '{} date {}'.format(file_name, metadata['date_taken'])
    assert helper.isclose(metadata['latitude'], 11.1111111111), '{} lat {}'.format(file_name, metadata['latitude'])
    assert helper.isclose(metadata['longitude'], 99.9999999999), '{} lon {}'.format(file_name, metadata['longitude'])

def _count_exiftool_reads():
    """Patch ExifTool.get_metadata to count how often files are read."""
    # Use the class media.py uses since other tests reload pyexiftool
    from elodie.media import media
    ExifTool = media.ExifTool
    calls = []
    real_get_metadata = ExifTool.get_metadata

    def counting_get_metadata(self, filename):
        calls.append(filename)
        return real_get_metadata(self, filename)

    return (mock.patch.object(ExifTool, 'get_metadata', counting_get_metadata), calls)

def test_is_valid_reads_file_once():
    # is_valid() is called for each attribute of the file
    patcher, calls = _count_exiftool_reads()
    with patcher:
        photo = Photo(helper.get_file('plain.jpg'))
        photo.get_metadata()
        photo.get_album()
        photo.get_title()
        photo.get_date_taken()
        valid = photo.is_valid()

    assert valid == True, valid
    assert len(calls) == 1, calls

def test_is_valid_after_reset_cache():
    patcher, calls = _count_exiftool_reads()
    with patcher:
        photo = Photo(helper.get_file('plain.jpg'))
        valid = photo.is_valid()
        photo.reset_cache()
        valid_after_reset = photo.is_valid()

    assert valid == True, valid
    assert valid_after_reset == True, valid_after_reset
    assert len(calls) == 2, calls

def test_is_valid_does_not_read_file_with_other_extension():
    patcher, calls = _count_exiftool_reads()
    with patcher:
        valid = Photo(helper.get_file('text.txt')).is_valid()

    assert valid == False, valid
    assert calls == [], calls

def test_is_valid_with_very_large_image():
    # 200 million pixels, image libraries refuse to open images this large
    temporary_folder, folder = helper.create_working_folder()
    origin = os.path.join(folder, 'panorama.png')
    helper.create_png(origin, 20000, 10000)

    valid = Photo(origin).is_valid()

    shutil.rmtree(temporary_folder)

    assert valid == True, valid

@pytest.mark.parametrize('name,source', [
    ('text.nef', b'This is not an image.'),
    ('text.heic', b'This is not an image.'),
    ('random.dng', bytes(range(256)) * 8),
    ('empty.jpg', b''),
    ('video.jpg', 'video.mov'),
    ('audio.png', 'audio.mp3'),
])
def test_is_valid_when_exiftool_does_not_identify_image(name, source):
    temporary_folder, folder = helper.create_working_folder()
    origin = os.path.join(folder, name)
    if isinstance(source, bytes):
        with open(origin, 'wb') as f:
            f.write(source)
    else:
        shutil.copyfile(helper.get_file(source), origin)

    valid = Photo(origin).is_valid()

    shutil.rmtree(temporary_folder)

    assert valid == False, valid

def test_is_valid_when_exiftool_not_running():
    photo = Photo(helper.get_file('plain.jpg'))
    with mock.patch.object(photo, 'get_exiftool_attributes', side_effect=ValueError('ExifTool instance not running.')):
        valid = photo.is_valid()

    assert valid == False, valid
