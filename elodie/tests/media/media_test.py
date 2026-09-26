# Project imports
import os
import sys

import hashlib
import random
import re
import shutil
import string
import tempfile
import time
import unittest.mock as mock
from datetime import datetime

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import helper
from elodie.media.audio import Audio
from elodie.media.media import Media
from elodie.media.photo import Photo
from elodie.media.text import Text
from elodie.media.video import Video

os.environ['TZ'] = 'GMT'

def test_get_file_path():
    media = Media(helper.get_file('plain.jpg'))
    path = media.get_file_path()

    assert 'plain.jpg' in path, path

def test_get_class_by_file_photo():
    media = Media.get_class_by_file(helper.get_file('plain.jpg'), [Photo, Video])

    assert media.__name__ == 'Photo'

def test_get_class_by_file_video():
    media = Media.get_class_by_file(helper.get_file('video.mov'), [Photo, Video])

    assert media.__name__ == 'Video'

def test_get_class_by_file_unsupported():
    media = Media.get_class_by_file(helper.get_file('text.txt'), [Photo, Video])

    assert media is None

def test_get_class_by_file_ds_store():
    media = Media.get_class_by_file(helper.get_file('.DS_Store'),
                                    [Photo, Video, Audio])
    assert media is None

def test_get_class_by_file_invalid_type():
    media = Media.get_class_by_file(None,
                                    [Photo, Video, Audio])
    assert media is None

    media = Media.get_class_by_file(False,
                                    [Photo, Video, Audio])
    assert media is None

    media = Media.get_class_by_file(True,
                                    [Photo, Video, Audio])
    assert media is None

def test_get_original_name():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/%s' % (folder, 'with-original-name.jpg')
    file = helper.get_file('with-original-name.jpg')
    
    shutil.copyfile(file, origin)

    media = Media.get_class_by_file(origin, [Photo])
    original_name = media.get_original_name()

    assert original_name == 'originalfilename.jpg', original_name

def test_get_original_name_invalid_file():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/%s' % (folder, 'invalid.jpg')
    file = helper.get_file('invalid.jpg')
    
    shutil.copyfile(file, origin)

    media = Media.get_class_by_file(origin, [Photo])
    original_name = media.get_original_name()

    assert original_name is None, original_name

def test_set_original_name_when_exists():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/%s' % (folder, 'with-original-name.jpg')
    file = helper.get_file('with-original-name.jpg')
    
    shutil.copyfile(file, origin)

    media = Media.get_class_by_file(origin, [Photo])
    result = media.set_original_name()

    assert result is None, result

def test_set_original_name_when_does_not_exist():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/%s' % (folder, 'plain.jpg')
    file = helper.get_file('plain.jpg')
    
    shutil.copyfile(file, origin)

    media = Media.get_class_by_file(origin, [Photo])
    metadata_before = media.get_metadata()
    result = media.set_original_name()
    metadata_after = media.get_metadata()

    assert metadata_before['original_name'] is None, metadata_before
    assert metadata_after['original_name'] == 'plain.jpg', metadata_after
    assert result is True, result

def test_set_original_name_with_arg():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/%s' % (folder, 'plain.jpg')
    file = helper.get_file('plain.jpg')
    
    shutil.copyfile(file, origin)

    new_name = helper.random_string(15)

    media = Media.get_class_by_file(origin, [Photo])
    metadata_before = media.get_metadata()
    result = media.set_original_name(new_name)
    metadata_after = media.get_metadata()

    assert metadata_before['original_name'] is None, metadata_before
    assert metadata_after['original_name'] == new_name, metadata_after
    assert result is True, result

def test_set_original_name():
    files = ['plain.jpg', 'audio.m4a', 'photo.nef', 'video.mov']

    for file in files:
        ext = os.path.splitext(file)[1]

        temporary_folder, folder = helper.create_working_folder()

        random_file_name = '%s%s' % (helper.random_string(10), ext)
        origin = '%s/%s' % (folder, random_file_name)
        file_path = helper.get_file(file)
        if file_path is False:
            file_path = helper.download_file(file, folder)

        shutil.copyfile(file_path, origin)

        media = Media.get_class_by_file(origin, [Audio, Media, Photo, Video])
        metadata = media.get_metadata()
        media.set_original_name()
        metadata_updated = media.get_metadata()

        shutil.rmtree(folder)

        assert metadata['original_name'] is None, metadata['original_name']
        assert metadata_updated['original_name'] == random_file_name, metadata_updated['original_name']

def test_get_description_with_description():
    media = Media.get_class_by_file(helper.get_file('with-description.jpg'), [Photo])
    description = media.get_description()

    assert description == 'some description', description

def test_get_description_without_description():
    media = Media.get_class_by_file(helper.get_file('plain.jpg'), [Photo])
    description = media.get_description()

    assert description is None, description

def test_get_description_invalid_file():
    media = Media.get_class_by_file(helper.get_file('invalid.jpg'), [Photo])
    description = media.get_description()

    assert description is None, description

def test_set_description():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Media.get_class_by_file(origin, [Photo])
    original_metadata = media.get_metadata()

    status = media.set_description('My photo description')

    assert status == True, status

    # Create new media object to verify the description was set
    media_new = Media.get_class_by_file(origin, [Photo])
    metadata = media_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata['description'] == 'My photo description', metadata['description']

def test_set_description_non_ascii():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Media.get_class_by_file(origin, [Photo])
    unicode_description = u'形声字 / 形聲字 description'

    status = media.set_description(unicode_description)

    assert status == True, status

    # Create new media object to verify the description was set
    media_new = Media.get_class_by_file(origin, [Photo])
    metadata = media_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata['description'] == unicode_description, metadata['description']

def test_set_description_with_none():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Media.get_class_by_file(origin, [Photo])
    
    status = media.set_description(None)

    shutil.rmtree(folder)

    assert status is None, status

def test_get_rating_with_rating():
    media = Media.get_class_by_file(helper.get_file('with-rating.jpg'), [Photo])
    rating = media.get_rating()

    assert rating == 5, rating

def test_get_rating_without_rating():
    media = Media.get_class_by_file(helper.get_file('no-exif.jpg'), [Photo])
    rating = media.get_rating()

    assert rating is None, rating

def test_get_rating_invalid_file():
    media = Media.get_class_by_file(helper.get_file('invalid.jpg'), [Photo])
    rating = media.get_rating()

    assert rating is None, rating

def test_set_rating():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('no-exif.jpg'), origin)

    media = Media.get_class_by_file(origin, [Photo])
    original_metadata = media.get_metadata()

    status = media.set_rating(3)

    assert status == True, status

    # Create new media object to verify the rating was set
    media_new = Media.get_class_by_file(origin, [Photo])
    metadata = media_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata['rating'] == 3, metadata['rating']

def test_set_rating_remove_with_empty_string():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('with-rating.jpg'), origin)

    media = Media.get_class_by_file(origin, [Photo])
    original_metadata = media.get_metadata()
    
    # Verify it has a rating first
    assert original_metadata['rating'] == 5, original_metadata['rating']

    # Remove the rating with empty string
    status = media.set_rating('')

    assert status == True, status

    # Create new media object to verify the rating was removed
    media_new = Media.get_class_by_file(origin, [Photo])
    metadata = media_new.get_metadata()

    shutil.rmtree(folder)

    assert metadata['rating'] is None, metadata['rating']

def is_valid():
    media = Media()

    assert not media.is_valid()

DRY_RUN_SETTERS = [
    ('set_album', ('Test Album',), 'album', 'Test Album'),
    ('set_date_taken', (datetime(2019, 7, 4, 12, 0, 0),), 'date_taken', helper.time_convert((2019, 7, 4, 12, 0, 0, 3, 185, 0))),
    ('set_location', (11.1111111111, 99.9999999999), 'latitude', 11.1111111111),
    ('set_original_name', ('original.name',), 'original_name', 'original.name'),
]

@mock.patch('elodie.constants.dry_run', True)
@pytest.mark.parametrize('file_name,media_class,setter,args,key,expected', [
    ('plain.jpg', Photo) + setter for setter in DRY_RUN_SETTERS + [('set_title', ('Test Title',), 'title', 'Test Title')]
] + [
    ('valid.txt', Text) + setter for setter in DRY_RUN_SETTERS
])
def test_set_metadata_dry_run(file_name, media_class, setter, args, key, expected):
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    checksum_before = helper.checksum(origin)

    media = media_class(origin)
    status = getattr(media, setter)(*args)
    value_in_memory = media.get_metadata()[key]
    value_in_file = media_class(origin).get_metadata()[key]
    checksum_after = helper.checksum(origin)
    folder_contents = os.listdir(folder)

    shutil.rmtree(folder)

    assert status == True, status
    assert value_in_memory == expected, value_in_memory
    assert value_in_file != expected, value_in_file
    assert checksum_after == checksum_before
    assert folder_contents == [file_name], folder_contents

# Files without a date in their metadata use their modification time as the
#  date taken. Writing metadata must not change it.
KEEP_DATE_SETTERS = [
    ('set_album', ('Test Album',), 'album', 'Test Album'),
    ('set_location', (11.1111111111, 99.9999999999), 'latitude', 11.1111111111),
    ('set_original_name', ('original.name',), 'original_name', 'original.name'),
]

@pytest.mark.parametrize('file_name,media_class,setter,args,key,expected', [
    ('no-exif.jpg', Photo) + setter for setter in KEEP_DATE_SETTERS + [('set_title', ('Test Title',), 'title', 'Test Title')]
] + [
    ('valid-without-header.txt', Text) + setter for setter in KEEP_DATE_SETTERS
])
def test_set_metadata_keeps_date_taken_from_modification_time(file_name, media_class, setter, args, key, expected):
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    os.utime(origin, (1584273600, 1584273600))

    date_taken_before = media_class(origin).get_date_taken()
    status = getattr(media_class(origin), setter)(*args)
    media = media_class(origin)
    value = media.get_metadata()[key]
    date_taken_after = media.get_date_taken()
    mtime_after = os.stat(origin).st_mtime

    shutil.rmtree(folder)

    assert status == True, status
    assert value == expected or helper.isclose(value, expected), value
    assert date_taken_before == time.gmtime(1584273600), date_taken_before
    assert date_taken_after == date_taken_before, date_taken_after
    assert mtime_after == 1584273600, mtime_after

@pytest.mark.parametrize('file_name,media_class', [
    ('plain.jpg', Photo),
    ('valid.txt', Text),
])
def test_set_metadata_does_not_leave_backup(file_name, media_class):
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)

    status = media_class(origin).set_album('Test Album')
    album = media_class(origin).get_album()
    folder_contents = os.listdir(folder)

    shutil.rmtree(folder)

    assert status == True, status
    assert album == 'Test Album', album
    assert folder_contents == [file_name], folder_contents

def test_set_metadata_keeps_existing_backup():
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)
    shutil.copyfile(helper.get_file('with-title.jpg'), origin + '_original')
    backup_checksum = helper.checksum(origin + '_original')

    status = Photo(origin).set_album('Test Album')
    album = Photo(origin).get_album()
    backup_checksum_after = helper.checksum(origin + '_original')

    shutil.rmtree(folder)

    assert status == True, status
    assert album == 'Test Album', album
    assert backup_checksum_after == backup_checksum

@pytest.mark.parametrize('file_name,media_class', [
    ('plain.jpg', Photo),
    ('valid.txt', Text),
])
def test_defer_writes(file_name, media_class):
    temporary_folder, folder = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    copy = os.path.join(folder, 'copy-' + file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    shutil.copyfile(origin, copy)
    checksum = helper.checksum(origin)

    media = media_class(origin)
    media.defer_writes()
    status = media.set_album('Test Album')
    album_in_memory = media.get_metadata()['album']
    checksum_after = helper.checksum(origin)
    write_status = media.write_deferred(copy)
    album_in_copy = media_class(copy).get_album()
    album_in_source = media_class(origin).get_album()

    shutil.rmtree(folder)

    assert status == True, status
    assert album_in_memory == 'Test Album', album_in_memory
    assert checksum_after == checksum
    assert write_status == True, write_status
    assert album_in_copy == 'Test Album', album_in_copy
    assert album_in_source != 'Test Album', album_in_source

