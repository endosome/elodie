# Project imports
import importlib.util
import json
import unittest.mock as mock
import os
import sys
import shutil
import subprocess
import time

from click.testing import CliRunner
import pytest
# assert_raises replaced with pytest.raises
from tempfile import gettempdir

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))))

import helper
elodie_path = os.path.abspath('{}/../../elodie.py'.format(os.path.dirname(os.path.realpath(__file__))))
spec = importlib.util.spec_from_file_location('elodie', elodie_path)
elodie = importlib.util.module_from_spec(spec)
spec.loader.exec_module(elodie)

from elodie.config import load_config
from elodie.localstorage import Db
from elodie.media.audio import Audio
from elodie.media.media import Media
from elodie.media.photo import Photo
from elodie.media.text import Text
from elodie.media.video import Video
from elodie.plugins.plugins import Plugins
from elodie.plugins.googlephotos.googlephotos import GooglePhotos
from elodie.external.pyexiftool import ExifTool


def test_import_file_text():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert helper.path_tz_fix(os.path.join('2016-04-Apr','Rainham','2016-04-07_11-15-26-valid-sample-title.txt')) in dest_path, dest_path

def test_import_file_audio():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/audio.m4a' % folder
    shutil.copyfile(helper.get_file('audio.m4a'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    # Recorded at 05:28:15 UTC in Houston, see audio_test.test_get_date_taken
    assert helper.path_tz_fix(os.path.join('2016-01-Jan','Houston','2016-01-03_23-28-15-audio.m4a')) in dest_path, dest_path

def test_import_file_photo():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert helper.path_tz_fix(os.path.join('2015-12-Dec','Unknown Location','2015-12-05_00-59-26-plain.jpg')) in dest_path, dest_path

def test_import_file_video():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert helper.path_tz_fix(os.path.join('2015-01-Jan','Pinecrest','2015-01-19_12-45-11-video.mov')) in dest_path, dest_path

def test_import_file_path_utf8_encoded_ascii_checkmark():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = str(folder)+u'/unicode\u2713filename.txt'
    # encode the unicode string to ascii
    origin = origin.encode('utf-8')

    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert helper.path_tz_fix(os.path.join('2016-04-Apr','Rainham',u'2016-04-07_11-15-26-unicode\u2713filename-sample-title.txt')) in dest_path, dest_path

def test_import_file_path_unicode_checkmark():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = str(folder)+u'/unicode\u2713filename.txt'

    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert helper.path_tz_fix(os.path.join('2016-04-Apr','Rainham',u'2016-04-07_11-15-26-unicode\u2713filename-sample-title.txt')) in dest_path, dest_path

def test_import_file_path_utf8_encoded_ascii_latin_nbsp():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = str(folder)+u'/unicode'+chr(160)+u'filename.txt'
    # encode the unicode string to ascii
    origin = origin.encode('utf-8')

    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert helper.path_tz_fix(os.path.join('2016-04-Apr','Rainham',u'2016-04-07_11-15-26-unicode\xa0filename-sample-title.txt')) in dest_path, dest_path

def test_import_file_path_unicode_latin_nbsp():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = str(folder)+u'/unicode'+chr(160)+u'filename.txt'

    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert helper.path_tz_fix(os.path.join('2016-04-Apr','Rainham',u'2016-04-07_11-15-26-unicode\xa0filename-sample-title.txt')) in dest_path, dest_path
    
def test_import_file_allow_duplicate_false():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    dest_path1 = elodie.import_file(origin, folder_destination, False, False, False)
    dest_path2 = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path1 is not None
    assert dest_path2 is None

def test_import_file_allow_duplicate_true():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    dest_path1 = elodie.import_file(origin, folder_destination, False, False, True)
    dest_path2 = elodie.import_file(origin, folder_destination, False, False, True)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path1 is not None
    assert dest_path2 is not None
    assert dest_path1 == dest_path2

def test_import_file_send_to_trash_false():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    dest_path1 = elodie.import_file(origin, folder_destination, False, False, False)
    assert os.path.isfile(origin), origin
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path1 is not None

@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='The trash can only be isolated on Linux')
def test_import_file_send_to_trash_true():
    # This moves a file to the trash for real. send2trash reads the location
    #  of the trash when it is imported, so we run elodie in a new process
    #  with HOME and XDG_DATA_HOME in a temporary folder. Otherwise the file
    #  would end up in the trash of the user running the tests. gh-230
    temporary_folder, folder = helper.create_working_folder()
    home = os.path.join(temporary_folder, 'home')
    source = os.path.join(temporary_folder, 'source')
    destination = os.path.join(temporary_folder, 'destination')
    os.makedirs(home)
    os.makedirs(source)

    origin = os.path.join(source, 'valid.txt')
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    environment = dict(os.environ, HOME=home, XDG_DATA_HOME=os.path.join(home, 'share'))
    result = subprocess.run(
        [sys.executable, elodie_path, 'import', '--trash', '--destination', destination, origin],
        env=environment, capture_output=True, text=True
    )

    trashed_file = os.path.join(home, 'share', 'Trash', 'files', 'valid.txt')
    trash_info = os.path.join(home, 'share', 'Trash', 'info', 'valid.txt.trashinfo')
    origin_exists = os.path.exists(origin)
    trashed_file_exists = os.path.isfile(trashed_file)
    trash_info_contents = open(trash_info).read() if os.path.isfile(trash_info) else None
    imported_files = [
        filename
        for dirname, dirnames, filenames in os.walk(destination)
        for filename in filenames
    ]

    shutil.rmtree(temporary_folder)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not origin_exists, origin
    assert trashed_file_exists, result.stdout + result.stderr
    assert trash_info_contents is not None and 'Path={}'.format(origin) in trash_info_contents, trash_info_contents
    assert len(imported_files) == 1, imported_files

@mock.patch.object(elodie, 'send2trash')
def test_import_file_send_to_trash_after_complete_import(mock_send2trash):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, True, False)
    helper.restore_dbs()

    destination_original_name = Photo(dest_path).get_original_name()
    destination_files = [
        filename
        for dirname, dirnames, filenames in os.walk(folder_destination)
        for filename in filenames
    ]

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    mock_send2trash.assert_called_once_with(origin)
    assert destination_original_name == 'plain.jpg', destination_original_name
    assert destination_files == [os.path.basename(dest_path)], destination_files

@mock.patch.object(elodie, 'send2trash')
def test_import_file_send_to_trash_not_when_import_fails(mock_send2trash):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    helper.reset_dbs()
    with mock.patch.object(elodie.FILESYSTEM, 'process_file', return_value=None):
        dest_path = elodie.import_file(origin, folder_destination, False, True, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path is None, dest_path
    mock_send2trash.assert_not_called()

@mock.patch.object(elodie, 'send2trash')
def test_import_file_send_to_trash_duplicate(mock_send2trash):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    helper.reset_dbs()
    dest_path1 = elodie.import_file(origin, folder_destination, False, False, False)
    dest_path2 = elodie.import_file(origin, folder_destination, False, True, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path1 is not None
    assert dest_path2 is None, dest_path2
    mock_send2trash.assert_called_once_with(origin)

@mock.patch.object(elodie, 'send2trash')
def test_import_file_send_to_trash_not_when_source_is_destination(mock_send2trash):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    helper.reset_dbs()
    dest_path1 = elodie.import_file(origin, folder_destination, False, False, False)
    # Importing a file which is already in the library into the same library
    dest_path2 = elodie.import_file(dest_path1, folder_destination, False, True, False)
    helper.restore_dbs()

    dest_path1_exists = os.path.isfile(dest_path1)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path2 is None, dest_path2
    assert dest_path1_exists, dest_path1
    mock_send2trash.assert_not_called()

@mock.patch('elodie.constants.dry_run', False)
def test_import_dry_run_does_not_create_destination():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    destination = os.path.join(folder_destination, 'library')

    shutil.copyfile(helper.get_file('plain.jpg'), '%s/plain.jpg' % folder)
    shutil.copyfile(helper.get_file('valid.txt'), '%s/valid.txt' % folder)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', destination, '--dry-run', folder])
    destination_exists = os.path.exists(destination)
    source_contents = sorted(os.listdir(folder))

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert result.exit_code == 0, result.output
    assert '[DRY-RUN] Would create directory' in result.output, result.output
    assert not destination_exists, destination
    assert source_contents == ['plain.jpg', 'valid.txt'], source_contents

@mock.patch('elodie.constants.dry_run', False)
def test_update_dry_run_does_not_create_directories():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)

    def directories():
        return sorted(
            dirname for dirname, dirnames, filenames in os.walk(folder_destination)
        )

    directories_before = directories()
    runner = CliRunner()
    result = runner.invoke(elodie._update, ['--album', 'test', '--dry-run', dest_path])
    directories_after = directories()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert result.exit_code == 0, result.output
    assert '[DRY-RUN] Would create directory' in result.output, result.output
    assert directories_after == directories_before, directories_after

def _files_state(folder):
    return sorted(
        (
            os.path.join(dirname, filename),
            helper.checksum(os.path.join(dirname, filename)),
            os.stat(os.path.join(dirname, filename)).st_ctime_ns,
        )
        for dirname, dirnames, filenames in os.walk(folder)
        for filename in filenames
    )

def _dry_run_destination(output, operation, source):
    prefix = '[DRY-RUN] Would %s: %s -> ' % (operation, source)
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    return None

@mock.patch('elodie.constants.dry_run', False)
@pytest.mark.parametrize('file_name,options', [
    ('plain.jpg', ['--album', 'Test Album']),
    ('plain.jpg', ['--time', '2019-07-04 12:00:00']),
    ('plain.jpg', ['--title', 'Test Title']),
    ('valid.txt', ['--album', 'Test Album']),
    ('valid.txt', ['--time', '2019-07-04 12:00:00']),
    ('valid.txt', ['--title', 'Test Title']),
])
def test_update_dry_run_does_not_modify_files(file_name, options):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)

    state_before = _files_state(folder_destination)
    runner = CliRunner()
    result_dry_run = runner.invoke(elodie._update, options + ['--dry-run', dest_path])
    state_after = _files_state(folder_destination)
    dry_run_destination = _dry_run_destination(result_dry_run.output, 'move', dest_path)

    # The dry run should report the destination the update then uses
    result = runner.invoke(elodie._update, options + [dest_path])
    dry_run_destination_exists = os.path.isfile(dry_run_destination)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert result_dry_run.exit_code == 0, result_dry_run.output
    assert state_after == state_before, (state_before, state_after)
    assert dry_run_destination is not None, result_dry_run.output
    assert dry_run_destination != dest_path, dry_run_destination
    assert result.exit_code == 0, result.output
    assert dry_run_destination_exists, dry_run_destination

@mock.patch('elodie.constants.dry_run', False)
@pytest.mark.parametrize('file_name,options', [
    ('plain.jpg', ['--album-from-folder']),
    ('plain.jpg', ['--time', '2019-07-04 12:00:00']),
    ('valid.txt', ['--album-from-folder']),
    ('valid.txt', ['--time', '2019-07-04 12:00:00']),
])
def test_import_dry_run_does_not_modify_source(file_name, options):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    source_folder = os.path.join(folder, 'Trip')
    os.mkdir(source_folder)
    origin = os.path.join(source_folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)

    state_before = _files_state(folder)
    runner = CliRunner()
    result_dry_run = runner.invoke(elodie._import, ['--destination', folder_destination, '--dry-run'] + options + [source_folder])
    state_after = _files_state(folder)
    dry_run_destination = _dry_run_destination(result_dry_run.output, 'copy', origin)

    # The dry run should report the destination the import then uses
    result = runner.invoke(elodie._import, ['--destination', folder_destination] + options + [source_folder])
    dry_run_destination_exists = os.path.isfile(dry_run_destination)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert result_dry_run.exit_code == 0, result_dry_run.output
    assert state_after == state_before, (state_before, state_after)
    assert dry_run_destination is not None, result_dry_run.output
    assert result.exit_code == 0, result.output
    assert dry_run_destination_exists, dry_run_destination

@pytest.mark.parametrize('file_name', ['no-exif.jpg', 'valid-without-header.txt'])
def test_import_album_from_folder_keeps_date_from_modification_time(file_name):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    source_folder = os.path.join(folder, 'Trip')
    os.mkdir(source_folder)
    origin = os.path.join(source_folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    os.utime(origin, (1584273600, 1584273600))

    dest_path = elodie.import_file(origin, folder_destination, True, False, False)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    expected_date = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(1584273600))
    assert os.path.basename(dest_path).startswith(expected_date), dest_path
    assert '/Trip/' in dest_path, dest_path

@mock.patch('elodie.constants.dry_run', False)
@pytest.mark.parametrize('file_name', ['no-exif.jpg', 'valid-without-header.txt'])
def test_update_album_keeps_date_from_modification_time(file_name):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    os.utime(origin, (1584273600, 1584273600))
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)

    runner = CliRunner()
    result = runner.invoke(elodie._update, ['--album', 'Test Album', dest_path])
    updated_files = [
        os.path.join(dirname, filename)
        for dirname, dirnames, filenames in os.walk(folder_destination)
        for filename in filenames
    ]

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    expected_date = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(1584273600))
    assert result.exit_code == 0, result.output
    assert len(updated_files) == 1, updated_files
    assert '/Test Album/' in updated_files[0], updated_files
    assert os.path.basename(updated_files[0]).startswith(expected_date), updated_files

def _create_backup_of_edited_source(folder, file_name):
    # Simulate an edit made with exiftool which leaves a backup behind
    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    shutil.copyfile(origin, origin + '_original')
    if file_name.endswith('.txt'):
        with open(origin, 'a') as f:
            f.write('edited\n')
    else:
        Photo(origin).set_title('edited')
    return origin

@mock.patch.object(elodie.geolocation, 'coordinates_by_name', return_value={'latitude': 33.6609, 'longitude': -95.5556})
@pytest.mark.parametrize('file_name', ['plain.jpg', 'valid.txt'])
@pytest.mark.parametrize('options,metadata_key,expected', [
    ({}, None, None),
    ({'time': '2019-07-04 12:00:00'}, 'date_taken', helper.time_convert((2019, 7, 4, 12, 0, 0, 3, 185, 0))),
    ({'location': 'Paris, Texas'}, 'latitude', 33.6609),
    ({'album_from_folder': True}, 'album', 'Trip'),
])
def test_import_file_writes_metadata_to_copy_only(mock_coordinates, file_name, options, metadata_key, expected):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    source_folder = os.path.join(folder, 'Trip')
    os.mkdir(source_folder)
    origin = _create_backup_of_edited_source(source_folder, file_name)
    backup_checksum = helper.checksum(origin + '_original')
    source_stat = os.stat(origin)
    source_checksum = helper.checksum(origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(
        origin, folder_destination, options.get('album_from_folder', False),
        False, False, options.get('location'), options.get('time'))
    helper.restore_dbs()

    source_stat_after = os.stat(origin)
    source_checksum_after = helper.checksum(origin)
    backup_checksum_after = helper.checksum(origin + '_original')
    source_folder_contents = sorted(os.listdir(source_folder))
    destination_files = [
        filename
        for dirname, dirnames, filenames in os.walk(folder_destination)
        for filename in filenames
    ]
    destination_metadata = Media.get_class_by_file(dest_path, [Photo, Text]).get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    # The source and the backup of the user's edit are left alone
    assert source_checksum_after == source_checksum
    assert source_stat_after.st_ctime_ns == source_stat.st_ctime_ns
    assert source_stat_after.st_ino == source_stat.st_ino
    assert backup_checksum_after == backup_checksum
    assert source_folder_contents == [file_name, file_name + '_original'], source_folder_contents
    # The copy is of the edited file and has the updated metadata
    assert destination_files == [os.path.basename(dest_path)], destination_files
    assert helper.checksum(helper.get_file(file_name)) != source_checksum
    assert destination_metadata['original_name'] == file_name, destination_metadata
    if metadata_key == 'latitude':
        assert helper.isclose(destination_metadata['latitude'], expected), destination_metadata
    elif metadata_key:
        assert destination_metadata[metadata_key] == expected, destination_metadata

def test_import_file_with_time_is_duplicate_when_imported_again():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    helper.reset_dbs()
    dest_path1 = elodie.import_file(origin, folder_destination, False, False, False, None, '2019-07-04 12:00:00')
    # The same source file, it should not be imported a second time
    dest_path2 = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path1 is not None
    assert dest_path2 is None, dest_path2

@mock.patch('elodie.constants.dry_run', False)
@pytest.mark.parametrize('file_name', ['plain.jpg', 'valid.txt'])
def test_update_keeps_existing_backup(file_name):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    # A backup of the file in the library made by the user
    shutil.copyfile(dest_path, dest_path + '_original')
    backup_checksum = helper.checksum(dest_path + '_original')

    runner = CliRunner()
    result = runner.invoke(elodie._update, ['--album', 'Test Album', dest_path])
    backup_checksum_after = helper.checksum(dest_path + '_original')
    backup_files = [
        filename
        for dirname, dirnames, filenames in os.walk(folder_destination)
        for filename in filenames
        if filename.endswith('_original')
    ]

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert result.exit_code == 0, result.output
    assert backup_checksum_after == backup_checksum
    assert backup_files == [os.path.basename(dest_path) + '_original'], backup_files

@mock.patch('elodie.constants.dry_run', False)
@pytest.mark.parametrize('file_name,media_class', [
    ('plain.jpg', Photo),
    ('valid.txt', Text),
])
def test_update_title_twice(file_name, media_class):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)

    runner = CliRunner()
    result1 = runner.invoke(elodie._update, ['--title', 'First Title', dest_path])
    files_after_first = [
        os.path.join(dirname, filename)
        for dirname, dirnames, filenames in os.walk(folder_destination)
        for filename in filenames
    ]
    result2 = runner.invoke(elodie._update, ['--title', 'Second Title', files_after_first[0]])
    files_after_second = [
        os.path.join(dirname, filename)
        for dirname, dirnames, filenames in os.walk(folder_destination)
        for filename in filenames
    ]
    title = media_class(files_after_second[0]).get_title()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert result1.exit_code == 0, result1.output
    assert result2.exit_code == 0, result2.output
    assert len(files_after_first) == 1, files_after_first
    assert os.path.basename(files_after_first[0]).endswith('-first-title' + os.path.splitext(file_name)[1]), files_after_first
    assert len(files_after_second) == 1, files_after_second
    # The second title replaces the first one in the file name
    assert os.path.basename(files_after_second[0]).endswith('-second-title' + os.path.splitext(file_name)[1]), files_after_second
    assert 'first-title' not in files_after_second[0], files_after_second
    assert os.path.dirname(files_after_second[0]) == os.path.dirname(dest_path), files_after_second
    assert title == 'Second Title', title

@mock.patch('elodie.constants.dry_run', False)
@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-update-combined-placeholders' % gettempdir())
def test_update_time_with_placeholders_combined_in_one_folder(mock_get_config_file):
    # update finds the root of the library by the number of folders gh-534
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write("""
[Directory]
month=%m
year=%Y
location=%city
full_path=%year/%month, %location
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    elodie.FILESYSTEM.cached_folder_path_definition = None

    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    try:
        dest_path = elodie.import_file(origin, folder_destination, False, False, False)
        runner = CliRunner()
        result = runner.invoke(elodie._update, ['--time', '2019-07-04 12:00:00', dest_path])
        files = [
            os.path.relpath(os.path.join(dirname, filename), folder_destination)
            for dirname, dirnames, filenames in os.walk(folder_destination)
            for filename in filenames
        ]
    finally:
        if hasattr(load_config, 'config'):
            del load_config.config
        elodie.FILESYSTEM.cached_folder_path_definition = None
        shutil.rmtree(folder)
        shutil.rmtree(folder_destination)

    assert os.path.relpath(dest_path, folder_destination).startswith(os.path.join('2015', '12, ')), dest_path
    assert result.exit_code == 0, result.output
    assert len(files) == 1, files
    assert files[0].startswith(os.path.join('2019', '07, ')), files

@pytest.mark.parametrize('metadata_line,expected_in_path', [
    ('{"album": 2020}', os.path.join('', '2020', '')),
    ('{"title": 2020}', '-note-2020.txt'),
    ('{"original_name": 12345}', '-12345.txt'),
])
def test_import_file_text_with_number_in_metadata(metadata_line, expected_in_path):
    # gh-400
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/note.txt' % folder
    with open(origin, 'w') as f:
        f.write(metadata_line + '\nsample text')

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path is not None
    assert expected_in_path in dest_path, dest_path

def test_import_file_with_very_large_image():
    # Image libraries refuse to open images this large, which crashed import
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/panorama.png' % folder
    helper.create_png(origin, 20000, 10000)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    dest_path_exists = dest_path is not None and os.path.isfile(dest_path)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path_exists, dest_path

@pytest.mark.parametrize('file_name', [
    'video.mkv', 'video.webm', 'audio.mp3', 'audio.flac', 'audio.ogg', 'audio.opus', 'photo.webp'
])
def test_import_file_new_formats(file_name):
    # gh-457
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path is not None
    assert os.path.join('2019-07-Jul', 'Unknown Location', '2019-07-04_') in dest_path, dest_path

def test_import_summary_invalid_file_is_error_not_duplicate():
    # gh-507
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    shutil.copyfile(helper.get_file('invalid.jpg'), os.path.join(folder, 'invalid.jpg'))
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))

    runner = CliRunner()
    result_first = runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    result_second = runner.invoke(elodie._import, ['--destination', folder_destination, folder])

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert 'Success                        1' in result_first.output, result_first.output
    assert 'Error                          1' in result_first.output, result_first.output
    assert 'Duplicate, not imported        0' in result_first.output, result_first.output
    assert 'Success                        0' in result_second.output, result_second.output
    assert 'Error                          1' in result_second.output, result_second.output
    assert 'Duplicate, not imported        1' in result_second.output, result_second.output

@pytest.mark.parametrize('name', [asset['name'] for asset in helper.ASSETS['assets'] if asset['name'].startswith('raw-')])
def test_import_raw_file(name):
    # gh-507: includes raw files of new cameras which image libraries cannot read
    file_path = helper.get_asset(name)
    expected_folder = time.strftime('%Y-%m-%b', helper.get_asset_date_taken(name))

    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    origin = os.path.join(folder, name)
    shutil.copyfile(file_path, origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path is not None
    assert os.path.join(expected_folder, 'Unknown Location') in dest_path, dest_path

@pytest.mark.parametrize('file_name', ['photo.tif', 'photo.tiff', 'photo.heif', 'photo.hif', 'photo.avif'])
def test_import_file_tiff_heif_avif(file_name):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = os.path.join(folder, file_name)
    shutil.copyfile(helper.get_file(file_name), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path is not None
    assert os.path.join('2020-06-Jun', 'Unknown Location', '2020-06-15_10-30-00-photo') in dest_path, dest_path

@pytest.mark.skipif(helper.is_windows(), reason='Symlinks need extra permissions on Windows')
def test_import_same_file_through_symlink_does_not_stop_the_run():
    # gh-210
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)

    link = os.path.join(temporary_folder_destination, 'link')
    os.symlink(folder_destination, link)
    linked_path = dest_path.replace(folder_destination, link, 1)
    other = os.path.join(folder, 'with-title.jpg')
    shutil.copyfile(helper.get_file('with-title.jpg'), other)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--allow-duplicates', linked_path, other])

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exception is None or isinstance(result.exception, SystemExit), result.exception
    # The file is in the library, it is not imported into it again
    assert 'Source cannot be in destination' in result.output, result.output
    assert 'Success                        1' in result.output, result.output
    assert 'Error                          1' in result.output, result.output

@mock.patch.object(elodie, 'send2trash')
def test_import_file_send_to_trash_with_sidecars(mock_send2trash):
    # gh-341: imported sidecars follow their file to the trash, a shared one
    #  only with the last file which uses it
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'IMG_1.jpg'))
    shutil.copyfile(helper.get_file('photo.png'), os.path.join(folder, 'IMG_1.png'))
    for name in ('IMG_1.xmp', 'IMG_1.jpg.xmp', 'orphan.xmp'):
        with open(os.path.join(folder, name), 'w') as f:
            f.write(name)
    trashed = []

    def trash(path):
        trashed.append(os.path.basename(path))
        os.remove(path)
    mock_send2trash.side_effect = trash

    helper.reset_dbs()
    dest_jpg = elodie.import_file(os.path.join(folder, 'IMG_1.jpg'), folder_destination, False, True, False)
    trashed_after_jpg = list(trashed)
    dest_png = elodie.import_file(os.path.join(folder, 'IMG_1.png'), folder_destination, False, True, False)
    helper.restore_dbs()
    left_in_source = sorted(os.listdir(folder))
    library_sidecars = sorted(
        name for dirname, dirnames, names in os.walk(folder_destination) for name in names if name.endswith('.xmp')
    )

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert dest_jpg is not None and dest_png is not None
    # IMG_1.xmp is still used by IMG_1.png after IMG_1.jpg was imported
    assert sorted(trashed_after_jpg) == ['IMG_1.jpg', 'IMG_1.jpg.xmp'], trashed_after_jpg
    assert sorted(trashed) == ['IMG_1.jpg', 'IMG_1.jpg.xmp', 'IMG_1.png', 'IMG_1.xmp'], trashed
    assert left_in_source == ['orphan.xmp'], left_in_source
    assert len(library_sidecars) == 3, library_sidecars

def test_import_destination_in_source():
    # The files of the source are imported, also the ones next to the
    #  destination
    temporary_folder, folder = helper.create_working_folder()
    folder_destination = '{}/destination'.format(folder)
    os.mkdir(folder_destination)

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)

    assert dest_path is not None and dest_path.startswith(folder_destination + os.sep), dest_path

def test_import_file_in_destination_is_not_imported_again():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)

    dest_path_again = elodie.import_file(dest_path, folder_destination, False, False, True)
    library = sorted(os.path.join(d, f) for d, _, fs in os.walk(folder_destination) for f in fs)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert dest_path_again is None, dest_path_again
    assert library == [dest_path], library

def test_import_source_which_contains_the_destination_skips_the_library():
    # i.e. elodie import --destination ~/Pictures/library ~/Pictures run
    #  again after new photos were added: the library is not imported
    #  into itself, also not with --allow-duplicates
    temporary_folder, folder = helper.create_working_folder()
    folder_destination = os.path.join(folder, 'library')
    os.makedirs(os.path.join(folder, 'phone'))
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'phone', 'plain.jpg'))

    runner = CliRunner()
    first = runner.invoke(elodie._import, ['--destination', folder_destination, '--allow-duplicates', folder])
    shutil.copyfile(helper.get_file('with-title.jpg'), os.path.join(folder, 'phone', 'with-title.jpg'))
    second = runner.invoke(elodie._import, ['--destination', folder_destination, '--allow-duplicates', folder])
    library = sorted(f for d, _, fs in os.walk(folder_destination) for f in fs)

    shutil.rmtree(folder)

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    # Both files of the source are imported again, none of the library
    assert 'Success                        2' in second.output, second.output
    assert 'Error                          0' in second.output, second.output
    # The copy of plain.jpg which the hash database knows is used again
    assert library == ['2015-12-05_00-59-26-plain.jpg',
                       '2015-12-05_00-59-26-with-title-some-title.jpg'], library

def test_import_destination_in_source_gh_287():
    temporary_folder, folder = helper.create_working_folder()
    folder_destination = '{}-destination'.format(folder)
    os.mkdir(folder_destination)

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)

    assert dest_path is not None, dest_path

def test_import_invalid_file_exit_code():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    # use a good and bad
    origin_invalid = '%s/invalid.jpg' % folder
    shutil.copyfile(helper.get_file('invalid.jpg'), origin_invalid)

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    helper.reset_dbs()
    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--allow-duplicates', origin_invalid, origin_valid])
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert result.exit_code == 1, result.exit_code

def test_import_file_with_single_exclude():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--exclude-regex', origin_valid[0:5], '--allow-duplicates', origin_valid])

    assert 'Success                        0' in result.output, result.output
    assert 'Error                          0' in result.output, result.output

def test_import_file_with_multiple_exclude():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--exclude-regex', 'does not exist in path', '--exclude-regex', origin_valid[0:5], '--allow-duplicates', origin_valid])

    assert 'Success                        0' in result.output, result.output
    assert 'Error                          0' in result.output, result.output

def test_import_file_with_non_matching_exclude():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--exclude-regex', 'does not exist in path', '--allow-duplicates', origin_valid])

    assert 'Success                        1' in result.output, result.output
    assert 'Error                          0' in result.output, result.output

def test_import_directory_with_matching_exclude():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--source', folder, '--exclude-regex', folder[1:5], '--allow-duplicates'])

    assert 'Success                        0' in result.output, result.output
    assert 'Error                          0' in result.output, result.output

def test_import_directory_with_non_matching_exclude():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--source', folder, '--exclude-regex', 'non-matching', '--allow-duplicates'])

    assert 'Success                        1' in result.output, result.output
    assert 'Error                          0' in result.output, result.output

def test_import_file_with_location():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/no-exif.jpg' % folder
    shutil.copyfile(helper.get_file('no-exif.jpg'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False, 'New York, NY', None)
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    # Should be organized under New York instead of Unknown Location
    assert 'New York' in dest_path, dest_path
    assert 'Unknown Location' not in dest_path, dest_path

def test_import_file_with_location_and_time():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/no-exif.jpg' % folder
    shutil.copyfile(helper.get_file('no-exif.jpg'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False, 'San Francisco, CA', '2022-12-25 10:00:00')
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    # Should be organized under San Francisco and 2022-12-Dec
    assert '2022-12-Dec' in dest_path, dest_path
    assert 'San Francisco' in dest_path, dest_path
    assert '2022-12-25_10-00-00' in dest_path, dest_path

def test_import_file_with_time():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/no-exif.jpg' % folder
    shutil.copyfile(helper.get_file('no-exif.jpg'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False, None, '2023-07-15 14:30:00')
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    # Should be organized under 2023-07-Jul based on specified time
    # Expected: 2023-07-Jul/Unknown Location/2023-07-15_14-30-00-no-exif.jpg
    assert '2023-07-Jul' in dest_path, dest_path
    assert '2023-07-15_14-30-00' in dest_path, dest_path

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-import-file-with-single-config-exclude' % gettempdir())
def test_import_file_with_single_config_exclude(mock_get_config_file):
    config_string = """
    [Exclusions]
    name1=valid
            """
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write(config_string)

    if hasattr(load_config, 'config'):
        del load_config.config

    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--allow-duplicates', origin_valid, '--debug'])

    if hasattr(load_config, 'config'):
        del load_config.config

    assert 'Success                        0' in result.output, result.output
    assert 'Error                          0' in result.output, result.output

@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-import-file-with-multiple-config-exclude' % gettempdir())
def test_import_file_with_multiple_config_exclude(mock_get_config_file):
    config_string = """
    [Exclusions]
    name1=notvalidatall
    name2=valid
            """
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write(config_string)

    if hasattr(load_config, 'config'):
        del load_config.config

    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--allow-duplicates', origin_valid, '--debug'])

    if hasattr(load_config, 'config'):
        del load_config.config

    assert 'Success                        0' in result.output, result.output
    assert 'Error                          0' in result.output, result.output

def test_update_location_on_audio():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/audio.m4a' % folder
    shutil.copyfile(helper.get_file('audio.m4a'), origin)

    audio = Audio(origin)
    metadata = audio.get_metadata()

    helper.reset_dbs()
    status = elodie.update_location(audio, origin, 'Sunnyvale, CA')
    helper.restore_dbs()

    audio_processed = Audio(origin)
    metadata_processed = audio_processed.get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert status == True, status
    assert metadata['latitude'] != metadata_processed['latitude'], metadata_processed['latitude']
    assert helper.isclose(metadata_processed['latitude'], 37.37188), metadata_processed['latitude']
    assert helper.isclose(metadata_processed['longitude'], -122.03751), metadata_processed['longitude']

def test_update_location_on_photo():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    metadata = photo.get_metadata()

    helper.reset_dbs()
    status = elodie.update_location(photo, origin, 'Sunnyvale, CA')
    helper.restore_dbs()

    photo_processed = Photo(origin)
    metadata_processed = photo_processed.get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert status == True, status
    assert metadata['latitude'] != metadata_processed['latitude']
    assert helper.isclose(metadata_processed['latitude'], 37.37188), metadata_processed['latitude']
    assert helper.isclose(metadata_processed['longitude'], -122.03751), metadata_processed['longitude']

def test_update_location_on_text():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/text.txt' % folder
    shutil.copyfile(helper.get_file('text.txt'), origin)

    text = Text(origin)
    metadata = text.get_metadata()

    helper.reset_dbs()
    status = elodie.update_location(text, origin, 'Sunnyvale, CA')
    helper.restore_dbs()

    text_processed = Text(origin)
    metadata_processed = text_processed.get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert status == True, status
    assert metadata['latitude'] != metadata_processed['latitude']
    assert helper.isclose(metadata_processed['latitude'], 37.37188), metadata_processed['latitude']
    assert helper.isclose(metadata_processed['longitude'], -122.03751), metadata_processed['longitude']

def test_update_location_on_video():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    video = Video(origin)
    metadata = video.get_metadata()

    helper.reset_dbs()
    status = elodie.update_location(video, origin, 'Sunnyvale, CA')
    helper.restore_dbs()

    video_processed = Video(origin)
    metadata_processed = video_processed.get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert status == True, status
    assert metadata['latitude'] != metadata_processed['latitude']
    assert helper.isclose(metadata_processed['latitude'], 37.37188), metadata_processed['latitude']
    assert helper.isclose(metadata_processed['longitude'], -122.03751), metadata_processed['longitude']

def test_update_location_with_exiftool_fallback():
    """Test update_location uses ExifTool when MapQuest key is not available."""
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/photo.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    metadata = photo.get_metadata()

    helper.reset_dbs()
    
    # Mock MapQuest key as None to force ExifTool usage
    with mock.patch('elodie.geolocation.get_key', return_value=None):
        status = elodie.update_location(photo, origin, 'Sunnyvale, California')
    
    helper.restore_dbs()

    photo_processed = Photo(origin)
    metadata_processed = photo_processed.get_metadata()

    shutil.rmtree(folder)

    assert status == True, status
    assert metadata['latitude'] != metadata_processed['latitude']
    # ExifTool returns 37.3688, -122.0365 for Sunnyvale, California
    # This is different from MapQuest which returns 37.37188, -122.03751
    assert helper.isclose(metadata_processed['latitude'], 37.3688), metadata_processed['latitude']
    assert helper.isclose(metadata_processed['longitude'], -122.0365), metadata_processed['longitude']

def test_update_time_on_audio():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/audio.m4a' % folder
    shutil.copyfile(helper.get_file('audio.m4a'), origin)

    audio = Audio(origin)
    metadata = audio.get_metadata()

    helper.reset_dbs()
    status = elodie.update_time(audio, origin, '2000-01-01 12:00:00')
    helper.restore_dbs()

    audio_processed = Audio(origin)
    metadata_processed = audio_processed.get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert status == True, status
    assert metadata['date_taken'] != metadata_processed['date_taken']
    assert metadata_processed['date_taken'] == helper.time_convert((2000, 1, 1, 12, 0, 0, 5, 1, 0)), metadata_processed['date_taken']

def test_update_time_on_photo():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    photo = Photo(origin)
    metadata = photo.get_metadata()

    helper.reset_dbs()
    status = elodie.update_time(photo, origin, '2000-01-01 12:00:00')
    helper.restore_dbs()

    photo_processed = Photo(origin)
    metadata_processed = photo_processed.get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert status == True, status
    assert metadata['date_taken'] != metadata_processed['date_taken']
    assert metadata_processed['date_taken'] == helper.time_convert((2000, 1, 1, 12, 0, 0, 5, 1, 0)), metadata_processed['date_taken']

def test_update_time_on_text():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/text.txt' % folder
    shutil.copyfile(helper.get_file('text.txt'), origin)

    text = Text(origin)
    metadata = text.get_metadata()

    helper.reset_dbs()
    status = elodie.update_time(text, origin, '2000-01-01 12:00:00')
    helper.restore_dbs()

    text_processed = Text(origin)
    metadata_processed = text_processed.get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert status == True, status
    assert metadata['date_taken'] != metadata_processed['date_taken']
    assert metadata_processed['date_taken'] == helper.time_convert((2000, 1, 1, 12, 0, 0, 5, 1, 0)), metadata_processed['date_taken']

def test_update_time_on_video():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/video.mov' % folder
    shutil.copyfile(helper.get_file('video.mov'), origin)

    video = Video(origin)
    metadata = video.get_metadata()

    helper.reset_dbs()
    status = elodie.update_time(video, origin, '2000-01-01 12:00:00')
    helper.restore_dbs()

    video_processed = Video(origin)
    metadata_processed = video_processed.get_metadata()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert status == True, status
    assert metadata['date_taken'] != metadata_processed['date_taken']
    assert metadata_processed['date_taken'] == helper.time_convert((2000, 1, 1, 12, 0, 0, 5, 1, 0)), metadata_processed['date_taken']

def test_update_with_directory_passed_in():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    origin = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    runner2 = CliRunner()
    result = runner2.invoke(elodie._update, ['--album', 'test', folder_destination])
    helper.restore_dbs()

    updated_file_path = "{}/2016-04-Apr/test/2016-04-07_11-15-26-valid-sample-title.txt".format(folder_destination)
    updated_file_exists = os.path.isfile(updated_file_path)

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert updated_file_exists, updated_file_path

def test_update_invalid_file_exit_code():
    temporary_folder, folder = helper.create_working_folder()
    # In a library, update moves a file within it. Outside of one the file
    #  went into the parent folders of the test, /tmp/2015-12-Dec.
    library_folder = os.path.join(folder, 'library', '2015-12-Dec', 'Unknown Location')
    os.makedirs(library_folder)

    # use a good and bad
    origin_invalid = os.path.join(library_folder, 'invalid.jpg')
    shutil.copyfile(helper.get_file('invalid.jpg'), origin_invalid)

    origin_valid = os.path.join(library_folder, '2015-12-05_00-59-26-valid.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    runner = CliRunner()
    result = runner.invoke(elodie._update, ['--album', 'test', origin_invalid, origin_valid])
    library = _library_files(os.path.join(folder, 'library'))

    assert result.exit_code == 1, result.exit_code
    assert library == [os.path.join('2015-12-Dec', 'Unknown Location', 'invalid.jpg'),
                       os.path.join('2015-12-Dec', 'test', '2015-12-05_00-59-26-valid.jpg')], library

def test_regenerate_db_invalid_source():
    runner = CliRunner()
    result = runner.invoke(elodie._generate_db, ['--source', '/invalid/path'])
    assert result.exit_code == 1, result.exit_code

def test_regenerate_valid_source():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    runner = CliRunner()
    result = runner.invoke(elodie._generate_db, ['--source', folder])
    db = Db()
    helper.restore_dbs()

    shutil.rmtree(folder)

    assert result.exit_code == 0, result.exit_code
    assert '3c19a5d751cf19e093b7447297731124d9cc987d3f91a9d1872c3b1c1b15639a' in db.hash_db, db.hash_db

def test_regenerate_valid_source_with_invalid_files():
    temporary_folder, folder = helper.create_working_folder()

    origin_valid = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin_valid)
    origin_invalid = '%s/invalid.invalid' % folder
    shutil.copyfile(helper.get_file('invalid.invalid'), origin_invalid)

    helper.reset_dbs()
    runner = CliRunner()
    result = runner.invoke(elodie._generate_db, ['--source', folder])
    db = Db()
    helper.restore_dbs()

    shutil.rmtree(folder)

    assert result.exit_code == 0, result.exit_code
    assert '3c19a5d751cf19e093b7447297731124d9cc987d3f91a9d1872c3b1c1b15639a' in db.hash_db, db.hash_db
    assert 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' not in db.hash_db, db.hash_db

def test_verify_ok():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    runner = CliRunner()
    runner.invoke(elodie._generate_db, ['--source', folder])
    result = runner.invoke(elodie._verify)
    helper.restore_dbs()

    shutil.rmtree(folder)

    assert 'Success                        1' in result.output, result.output
    assert 'Error                          0' in result.output, result.output

def test_verify_error():
    temporary_folder, folder = helper.create_working_folder()

    origin = '%s/valid.txt' % folder
    shutil.copyfile(helper.get_file('valid.txt'), origin)

    helper.reset_dbs()
    runner = CliRunner()
    runner.invoke(elodie._generate_db, ['--source', folder])
    with open(origin, 'w') as f:
        f.write('changed text')
    result = runner.invoke(elodie._verify)
    helper.restore_dbs()

    shutil.rmtree(folder)

    assert origin in result.output, result.output
    assert 'Error                          1' in result.output, result.output
    assert result.exit_code == 1, result.exit_code

@pytest.mark.skip(reason="Google Photos tests are disabled: they upload to a real account with shared credentials and fail when Google's quota for concurrent writes is exceeded (HTTP 429)")
@pytest.mark.xdist_group('googlephotos')
@mock.patch('elodie.config.get_config_file', return_value='%s/config.ini-cli-batch-plugin-googlephotos' % gettempdir())
def test_cli_batch_plugin_googlephotos(mock_get_config_file):
    auth_file = helper.get_file('plugins/googlephotos/auth_file.json')
    secrets_file = helper.get_file('plugins/googlephotos/secrets_file.json')
    config_string = """
    [Plugins]
    plugins=GooglePhotos

    [PluginGooglePhotos]
    auth_file={}
    secrets_file={}
            """
    config_string_fmt = config_string.format(
        auth_file,
        secrets_file
    )
    with open(mock_get_config_file.return_value, 'w') as f:
        f.write(config_string_fmt)

    if hasattr(load_config, 'config'):
        del load_config.config

    final_file_path_1 = helper.get_file('plain.jpg')
    final_file_path_2 = helper.get_file('no-exif.jpg')
    sample_metadata_1 = Photo(final_file_path_1).get_metadata()
    sample_metadata_2 = Photo(final_file_path_2).get_metadata()
    gp = GooglePhotos()
    gp.after('', '', final_file_path_1, sample_metadata_1)
    gp.after('', '', final_file_path_2, sample_metadata_1)

    runner = CliRunner()
    result = runner.invoke(elodie._batch)

    if hasattr(load_config, 'config'):
        del load_config.config

    assert "elodie/tests/files/plain.jpg uploaded successfully.\"}\n" in result.output, result.output
    assert "elodie/tests/files/no-exif.jpg uploaded successfully.\"}\n" in result.output, result.output

def test_cli_debug_import():
    runner = CliRunner()
    # import
    result = runner.invoke(elodie._import, ['--destination', '/does/not/exist', '/does/not/exist'])
    assert "Could not find /does/not/exist\n" not in result.output, result.output
    result = runner.invoke(elodie._import, ['--destination', '/does/not/exist', '--debug', '/does/not/exist'])
    assert "Could not find /does/not/exist\n" in result.output, result.output

def test_cli_debug_update():
    runner = CliRunner()
    # update
    result = runner.invoke(elodie._update, ['--album', 'foobar', '/does/not/exist'])
    assert "Could not find /does/not/exist\n" not in result.output, result.output
    result = runner.invoke(elodie._update, ['--album', 'foobar', '--debug', '/does/not/exist'])
    assert "Could not find /does/not/exist\n" in result.output, result.output

@mock.patch.object(elodie, 'send2trash')
def test_import_send_to_trash_reads_source_folder_once(mock_send2trash):
    # Each trashed file changes the folder, the cached listing is updated
    #  instead of reading it again for each file.
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    for i in range(5):
        shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'IMG_%d.jpg' % i))
        ExifTool().execute(b'-overwrite_original', ('-EXIF:DateTimeOriginal=2019:05:26 10:33:2%d' % i).encode(), os.path.join(folder, 'IMG_%d.jpg' % i).encode())
    mock_send2trash.side_effect = os.remove
    elodie.FILESYSTEM.directory_listings = {}

    runner = CliRunner()
    with mock.patch('elodie.filesystem.os.listdir', wraps=os.listdir) as listdir:
        result = runner.invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])
        source_listings = [c for c in listdir.call_args_list if c.args and c.args[0] == folder]
    left = os.listdir(folder)

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exit_code == 0, result.output
    assert left == [], left
    assert len(source_listings) == 1, source_listings

@mock.patch.object(elodie, 'send2trash')
def test_import_send_to_trash_finds_sidecar_added_during_import(mock_send2trash):
    # A sidecar added by another program while importing is imported with its
    #  photo although the folder changes when each file is trashed.
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photos = []
    for i in range(2):
        photo = os.path.join(folder, 'IMG_%d.jpg' % i)
        shutil.copyfile(helper.get_file('plain.jpg'), photo)
        ExifTool().execute(b'-overwrite_original', ('-EXIF:DateTimeOriginal=2019:05:26 10:33:2%d' % i).encode(), photo.encode())
        photos.append(photo)
    mock_send2trash.side_effect = os.remove
    process_file = elodie.FILESYSTEM.process_file
    added = []

    def process_file_then_add_sidecar(_file, *args, **kwargs):
        dest_path = process_file(_file, *args, **kwargs)
        if not added:
            # The sidecar of the file which is imported next
            other = photos[1] if _file == photos[0] else photos[0]
            time.sleep(0.01)
            with open(os.path.splitext(other)[0] + '.xmp', 'w') as f:
                f.write('edits')
            added.append(other)
            time.sleep(0.01)
        return dest_path

    runner = CliRunner()
    with mock.patch.object(elodie.FILESYSTEM, 'process_file', side_effect=process_file_then_add_sidecar):
        result = runner.invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])
    left = os.listdir(folder)
    library_sidecars = [
        name for dirname, dirnames, names in os.walk(folder_destination)
        for name in names if name.endswith('.xmp')
    ]

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exit_code == 0, result.output
    assert left == [], left
    assert len(library_sidecars) == 1, library_sidecars

def test_batch_exits_with_an_error_when_a_plugin_fails():
    # i.e. for cron to notice that a sync failed
    runner = CliRunner()
    with mock.patch.object(elodie.Plugins, 'run_batch', return_value=False):
        failed = runner.invoke(elodie._batch)
    with mock.patch.object(elodie.Plugins, 'run_batch', return_value=True):
        succeeded = runner.invoke(elodie._batch)

    assert failed.exit_code == 1, failed.output
    assert succeeded.exit_code == 0, succeeded.output

@mock.patch.object(elodie, 'send2trash')
def test_import_send_to_trash_with_two_photos_of_the_same_name(mock_send2trash):
    # Photos of two cameras taken in the same second get the same name. The
    #  second must not replace the first, else the first is lost when its
    #  original is moved to the trash.
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    for camera in ('a', 'b'):
        os.makedirs(os.path.join(folder, camera))
        path = os.path.join(folder, camera, 'IMG_0001.jpg')
        shutil.copyfile(helper.get_file('plain.jpg'), path)
        ExifTool().execute(b'-overwrite_original', ('-XMP:Description=camera %s' % camera).encode(), path.encode())
    mock_send2trash.side_effect = os.remove

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])
    library = sorted(
        os.path.join(d, f) for d, _, files in os.walk(folder_destination) for f in files)
    descriptions = sorted(Photo(p).get_description() for p in library)
    left = [f for d, _, files in os.walk(folder) for f in files]

    assert result.exit_code == 0, result.output
    assert descriptions == ['camera a', 'camera b'], library
    assert left == [], left

def _library_files(folder):
    return sorted(
        os.path.relpath(os.path.join(dirname, filename), folder)
        for dirname, dirnames, filenames in os.walk(folder)
        for filename in filenames
    )

class _Config(object):
    """Use a config.ini with this content."""
    def __init__(self, name, content):
        self.path = os.path.join(gettempdir(), 'config.ini-%s' % name)
        self.content = content

    def __enter__(self):
        with open(self.path, 'w') as f:
            f.write(self.content)
        self.patch = mock.patch('elodie.config.get_config_file', return_value=self.path)
        self.patch.start()
        self._reset()

    def __exit__(self, *args):
        self.patch.stop()
        self._reset()
        os.remove(self.path)

    def _reset(self):
        if hasattr(load_config, 'config'):
            del load_config.config
        elodie.FILESYSTEM.cached_folder_path_definition = None

def test_update_keeps_file_in_library_when_a_folder_of_its_path_is_empty():
    # %album of a photo without an album is no folder, the photo is one
    #  folder deep instead of two. It was moved out of the library.
    temporary_folder, folder = helper.create_working_folder()
    library = os.path.join(temporary_folder, 'library')
    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    with _Config('update-empty-folder', '[Directory]\ndate=%Y\nfull_path=%date/%album\n'):
        dest_path = elodie.import_file(origin, library, False, False, False)
        result = CliRunner().invoke(elodie._update, ['--title', 'first', dest_path])
        second = CliRunner().invoke(elodie._update, ['--album', 'Trip', os.path.join(library, '2015', '2015-12-05_00-59-26-plain-first.jpg')])

    files = _library_files(temporary_folder)

    assert os.path.relpath(dest_path, library) == os.path.join('2015', '2015-12-05_00-59-26-plain.jpg'), dest_path
    assert result.exit_code == 0, result.output
    assert second.exit_code == 0, second.output
    assert files == sorted([os.path.join('library', '2015', 'Trip', '2015-12-05_00-59-26-plain-first.jpg'),
                            os.path.join(os.path.basename(folder), 'plain.jpg')]), files

def test_update_which_does_not_change_the_path_of_the_file():
    temporary_folder, folder = helper.create_working_folder()
    library = os.path.join(temporary_folder, 'library')
    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    with _Config('update-same-path', '[Directory]\ndate=%Y\nfull_path=%date\n'):
        dest_path = elodie.import_file(origin, library, False, False, False)
        result = CliRunner().invoke(elodie._update, ['--album', 'Trip', dest_path])
    verify = CliRunner().invoke(elodie._verify)

    files = _library_files(library)
    album = Photo(dest_path).get_album()

    assert result.exit_code == 0, result.output
    assert 'Success                        1' in result.output, result.output
    assert files == [os.path.relpath(dest_path, library)], files
    assert album == 'Trip', album
    # The hash database has the checksum of the changed file
    assert verify.exit_code == 0, verify.output

def test_verify_files_after_import_and_update():
    # The metadata written to the copy changes its checksum
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    runner = CliRunner()
    runner.invoke(elodie._import, ['--destination', folder_destination, '--time', '2019-07-04', folder])
    verify_import = runner.invoke(elodie._verify)
    dest_path = os.path.join(folder_destination, _library_files(folder_destination)[0])
    runner.invoke(elodie._update, ['--title', 'new title', dest_path])
    verify_update = runner.invoke(elodie._verify)
    # The source is still known after the update
    import_again = runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    files = _library_files(folder_destination)

    assert verify_import.exit_code == 0, verify_import.output
    assert 'Success                        1' in verify_import.output, verify_import.output
    assert verify_update.exit_code == 0, verify_update.output
    assert 'Success                        1' in verify_update.output, verify_update.output
    assert 'Error                          0' in verify_update.output, verify_update.output
    assert 'Duplicate, not imported        1' in import_again.output, import_again.output
    assert len(files) == 1 and 'new-title' in files[0], files

def test_import_duplicates_only_exits_without_error():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))

    runner = CliRunner()
    first = runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    second = runner.invoke(elodie._import, ['--destination', folder_destination, folder])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert 'Duplicate, not imported        1' in second.output, second.output

def test_update_without_anything_to_update_is_an_error():
    temporary_folder, folder = helper.create_working_folder()
    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    result = CliRunner().invoke(elodie._update, [origin])

    assert result.exit_code == 2, result.output
    assert 'Nothing to update' in result.output, result.output
    assert os.listdir(folder) == ['plain.jpg']

@pytest.mark.parametrize('command', ['import', 'update'])
@pytest.mark.parametrize('value', ['2015-01-01 10:00', 'yesterday', '01-01-2015'])
def test_invalid_time_changes_nothing(command, value):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    if command == 'import':
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--time', value, origin])
    else:
        result = CliRunner().invoke(elodie._update, ['--time', value, origin])

    assert result.exit_code == 2, result.output
    assert 'Invalid value for \'--time\'' in result.output, result.output
    assert os.listdir(folder) == ['plain.jpg']
    assert _library_files(folder_destination) == []
    assert helper.checksum(origin) == helper.checksum(helper.get_file('plain.jpg'))

@pytest.mark.parametrize('value,expected', [
    ('2015-01-01', (2015, 1, 1, 0, 0, 0)),
    ('2015-01-01 10:20:30', (2015, 1, 1, 10, 20, 30)),
    ('2015-01-01 10:00', None),
    ('2015-13-01', None),
    ('', None),
])
def test_parse_time(value, expected):
    parsed = elodie.parse_time(value)
    assert (parsed.timetuple()[:6] if parsed else None) == expected, parsed

@mock.patch.object(elodie.geolocation, 'coordinates_by_name', return_value=None)
@pytest.mark.parametrize('command', ['import', 'update'])
def test_location_which_is_not_found_changes_nothing(mock_coordinates, command):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    if command == 'import':
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--location', 'Nowhere', origin])
    else:
        result = CliRunner().invoke(elodie._update, ['--location', 'Nowhere', origin])

    assert result.exit_code == 1, result.output
    assert 'Could not find the location Nowhere' in result.output, result.output
    assert os.listdir(folder) == ['plain.jpg']
    assert _library_files(folder_destination) == []
    assert helper.checksum(origin) == helper.checksum(helper.get_file('plain.jpg'))

@mock.patch.object(elodie.geolocation, 'coordinates_by_name', return_value={})
def test_update_location_which_is_not_found(mock_coordinates):
    photo = Photo(helper.get_file('plain.jpg'))
    assert elodie.update_location(photo, photo.get_file_path(), 'Nowhere') is False

def test_update_unsupported_file_is_an_error():
    temporary_folder, folder = helper.create_working_folder()
    origin = os.path.join(folder, 'file.unsupported')
    with open(origin, 'w') as f:
        f.write('text')

    result = CliRunner().invoke(elodie._update, ['--title', 'title', origin])

    assert result.exit_code == 1, result.output
    assert 'Error                          1' in result.output, result.output

@mock.patch('elodie.constants.dry_run', False)
def test_update_does_not_move_file_when_metadata_cannot_be_written():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    origin = os.path.join(folder, 'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)

    with mock.patch.object(Photo, 'set_album', return_value=False):
        result = CliRunner().invoke(elodie._update, ['--album', 'Trip', dest_path])

    assert result.exit_code == 1, result.output
    assert 'Failed to update album' in result.output, result.output
    assert _library_files(folder_destination) == [os.path.relpath(dest_path, folder_destination)]

@pytest.mark.parametrize('command', ['import', 'update'])
def test_unexpected_error_for_one_file_does_not_stop_the_run(command):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    for name in ('plain.jpg', 'with-title.jpg'):
        shutil.copyfile(helper.get_file(name), os.path.join(folder, name))
    if command == 'update':
        # The files in the library are updated
        CliRunner().invoke(elodie._import, ['--destination', folder_destination, folder])
        folder = os.path.join(folder_destination, '2015-12-Dec', 'Unknown Location')
    broken = [f for f in os.listdir(folder) if 'plain' in f][0]
    process_file = elodie.FILESYSTEM.process_file

    def fail_for_broken(_file, *args, **kwargs):
        if os.path.basename(_file) == broken:
            raise RuntimeError('broken file')
        return process_file(_file, *args, **kwargs)

    with mock.patch.object(elodie.FILESYSTEM, 'process_file', side_effect=fail_for_broken):
        if command == 'import':
            result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, folder])
        else:
            result = CliRunner().invoke(elodie._update, ['--title', 'new', folder])

    assert result.exit_code == 1, result.output
    assert not isinstance(result.exception, RuntimeError), result.exception
    assert 'Could not process %s: RuntimeError: broken file' % os.path.join(folder, broken) in result.output, result.output
    assert 'Success                        1' in result.output, result.output
    assert 'Error                          1' in result.output, result.output

@pytest.mark.parametrize('path,directory,expected', [
    ('/a/b/c.jpg', '/a/b', True),
    ('/a/b/c/d.jpg', '/a/b', True),
    ('/a/bc/d.jpg', '/a/b', False),
    ('/a/c.jpg', '/a/b', False),
    ('/a/b', '/a/b', False),
    ('/a/b/../c.jpg', '/a/b', False),
])
def test_is_in_directory(path, directory, expected):
    assert elodie.is_in_directory(path, directory) is expected

@pytest.mark.skipif(helper.is_windows(), reason='SIGTERM cannot be sent to the own process on Windows')
def test_sigterm_stops_like_ctrl_c():
    import signal
    previous = signal.getsignal(signal.SIGTERM)
    try:
        elodie.stop_on_sigterm()
        with pytest.raises(KeyboardInterrupt):
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(5)
    finally:
        signal.signal(signal.SIGTERM, previous)

@pytest.mark.skipif(helper.is_windows(), reason='SIGTERM cannot be sent to a process on Windows')
def test_sigterm_stops_an_import():
    # i.e. docker stop: elodie is stopped at once, not killed after a timeout
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))
    # Blocks the import after it started until SIGTERM
    script = (
        'import runpy, sys, time, elodie.filesystem as f\n'
        'f.FileSystem.process_file = lambda *a, **k: (print("started", flush=True), time.sleep(60))\n'
        'sys.argv = sys.argv[1:]\n'
        'runpy.run_path(sys.argv[0], run_name="__main__")\n'
    )
    process = subprocess.Popen(
        [sys.executable, '-c', script, elodie_path, 'import', '--destination', folder_destination, folder],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        cwd=os.path.dirname(elodie_path))
    try:
        assert process.stdout.readline().strip() == 'started'
        start = time.time()
        process.terminate()
        output, _ = process.communicate(timeout=30)
    finally:
        process.kill()

    assert time.time() - start < 10
    assert process.returncode == 1, (process.returncode, output)
    assert 'Aborted!' in output, output

@pytest.mark.skipif(helper.is_windows(), reason='Ctrl+C cannot be sent to a process group on Windows')
def test_ctrl_c_stops_an_import():
    # A terminal sends SIGINT to elodie and ExifTool. Here ExifTool exits
    #  before elodie stops it, which raised BrokenPipeError.
    import signal
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))
    script = (
        'import runpy, signal, sys, time, elodie.filesystem as f\n'
        'from elodie.external.pyexiftool import ExifTool\n'
        'def interrupted(signum, frame):\n'
        '    ExifTool()._process.wait()\n'
        '    raise KeyboardInterrupt\n'
        'def process_file(*a, **k):\n'
        '    signal.signal(signal.SIGINT, interrupted)\n'
        '    print("started", flush=True)\n'
        '    time.sleep(60)\n'
        'f.FileSystem.process_file = process_file\n'
        'sys.argv = sys.argv[1:]\n'
        'runpy.run_path(sys.argv[0], run_name="__main__")\n'
    )
    process = subprocess.Popen(
        [sys.executable, '-c', script, elodie_path, 'import', '--destination', folder_destination, folder],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        cwd=os.path.dirname(elodie_path), start_new_session=True)
    try:
        assert process.stdout.readline().strip() == 'started'
        os.killpg(process.pid, signal.SIGINT)
        output, _ = process.communicate(timeout=30)
    finally:
        process.kill()

    assert process.returncode == 1, (process.returncode, output)
    assert 'Aborted!' in output, output
    assert 'Traceback' not in output, output

# gh-474: the video of an Apple Live Photo is imported next to its photo with
#  the same name.
def _files_in(folder):
    return sorted(
        os.path.relpath(os.path.join(dirname, name), folder)
        for dirname, dirnames, names in os.walk(folder)
        for name in names
    )

def _set_video_date(video, date):
    # The video follows its photo whatever its own metadata says
    ExifTool().execute(
        b'-overwrite_original',
        ('-QuickTime:CreationDate=%s' % date).encode(),
        video.encode(),
    )

def test_import_live_photo():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder)
    _set_video_date(video, '2018:01:01 12:00:00+02:00')
    # Same name as a Live Photo but the video belongs to another photo, which
    #  was taken a day later.
    other_photo, other_video = helper.create_live_photo(folder, name='IMG_5555', content_identifier='SOMETHING-ELSE')
    ExifTool().execute(b'-overwrite_original', b'-EXIF:DateTimeOriginal=2019:05:27 11:00:00', other_photo.encode())

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    library = _files_in(folder_destination)
    source = sorted(os.listdir(folder))

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exit_code == 0, result.output
    assert 'Success                        4' in result.output, result.output
    # The video goes next to the photo although its own location differs
    pair = [f for f in library if 'img_1234' in f]
    assert [os.path.splitext(f)[1] for f in pair] == ['.heic', '.mov'], library
    assert os.path.splitext(pair[0])[0] == os.path.splitext(pair[1])[0], library
    # The other video is imported on its own with its own date
    other = sorted(os.path.basename(f) for f in library if 'img_5555' in f)
    assert other == ['2019-05-26_10-33-20-img_5555.mov', '2019-05-27_11-00-00-img_5555.heic'], library
    assert source == ['IMG_1234.HEIC', 'IMG_1234.MOV', 'IMG_5555.HEIC', 'IMG_5555.MOV'], source

@mock.patch.object(elodie, 'send2trash')
def test_import_live_photo_send_to_trash(mock_send2trash):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder)
    _set_video_date(video, '2018:01:01 12:00:00+02:00')
    with open(os.path.join(folder, 'IMG_1234.AAE'), 'w') as f:
        f.write('edits')
    trashed = []

    def trash(path):
        trashed.append(os.path.basename(path))
        os.remove(path)
    mock_send2trash.side_effect = trash

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])
    library = _files_in(folder_destination)

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exit_code == 0, result.output
    assert sorted(trashed) == ['IMG_1234.AAE', 'IMG_1234.HEIC', 'IMG_1234.MOV'], trashed
    # The photo is trashed before its video
    assert trashed.index('IMG_1234.HEIC') < trashed.index('IMG_1234.MOV'), trashed
    assert [os.path.splitext(f)[1] for f in library] == ['.aae', '.heic', '.mov'], library
    assert len(set(os.path.splitext(f)[0] for f in library)) == 1, library

def test_import_live_photo_video_next_to_photo_imported_before():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder)
    _set_video_date(video, '2018:01:01 12:00:00+02:00')
    # Import the photo without its video first
    only_photo_folder = os.path.join(temporary_folder, 'only-photo')
    os.makedirs(only_photo_folder)
    shutil.copyfile(photo, os.path.join(only_photo_folder, 'IMG_1234.HEIC'))

    runner = CliRunner()
    runner.invoke(elodie._import, ['--destination', folder_destination, only_photo_folder])
    result = runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    library = _files_in(folder_destination)

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert 'Success                        1' in result.output, result.output
    assert 'Duplicate, not imported        1' in result.output, result.output
    assert [os.path.splitext(f)[1] for f in library] == ['.heic', '.mov'], library
    assert os.path.splitext(library[0])[0] == os.path.splitext(library[1])[0], library

def test_import_live_photo_video_on_its_own_when_photo_is_not_imported():
    # The video must not be lost when its photo is excluded
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--exclude-regex', r'\.HEIC$', folder])
    library = _files_in(folder_destination)

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exit_code == 0, result.output
    assert [os.path.splitext(f)[1] for f in library] == ['.mov'], library

@mock.patch('elodie.constants.dry_run', True)
def test_import_live_photo_dry_run():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, '--dry-run', folder])
    library = _files_in(folder_destination)
    source = sorted(os.listdir(folder))

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exit_code == 0, result.output
    assert library == [], library
    assert source == ['IMG_1234.HEIC', 'IMG_1234.MOV'], source
    assert 'Would copy' in result.output and 'IMG_1234.MOV' in result.output, result.output

def test_update_live_photo_moves_video_with_photo():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)
    runner = CliRunner()
    runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    photo_dest = [
        os.path.join(folder_destination, f)
        for f in _files_in(folder_destination) if f.endswith('.heic')
    ][0]

    # Only the photo is given
    result = runner.invoke(elodie._update, ['--album', 'Holidays', '--title', 'Beach', photo_dest])
    library = _files_in(folder_destination)
    video_album = None
    if len(library) == 2:
        video_album = Video(os.path.join(folder_destination, library[1])).get_metadata()['album']

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exit_code == 0, result.output
    assert len(library) == 2, library
    assert all('/Holidays/' in f and f.endswith(('-beach.heic', '-beach.mov')) for f in library), library
    assert os.path.splitext(library[0])[0] == os.path.splitext(library[1])[0], library
    assert video_album == 'Holidays', video_album

def test_sort_photos_first():
    files = {'b/IMG_1.MOV', 'a/IMG_2.mp4', 'b/IMG_1.HEIC', 'a/notes.txt'}
    assert elodie.sort_photos_first(files) == ['a/notes.txt', 'b/IMG_1.HEIC', 'a/IMG_2.mp4', 'b/IMG_1.MOV']

def test_import_live_photo_video_shared_by_two_photos():
    # i.e. the original and a copy of the photo, both with the
    #  ContentIdentifier of the video
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder)
    copy = os.path.join(folder, 'IMG_1234.HEIF')
    shutil.copyfile(photo, copy)
    # Not identical, otherwise it is a duplicate
    ExifTool().execute(b'-overwrite_original', b'-EXIF:DateTimeOriginal=2019:05:26 10:33:21', copy.encode())
    has_content_identifier = elodie.FILESYSTEM.get_content_identifier(Photo(copy)) == helper.LIVE_PHOTO_CONTENT_IDENTIFIER

    runner = CliRunner()
    result = runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    library = _files_in(folder_destination)

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert has_content_identifier
    assert result.exit_code == 0, result.output
    assert 'Success                        3' in result.output, result.output
    # The video is imported once, with the first photo
    assert sorted(os.path.splitext(f)[1] for f in library) == ['.heic', '.heif', '.mov'], library


def test_import_live_photo_again_is_duplicate():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)

    runner = CliRunner()
    runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    library_before = _files_in(folder_destination)
    result = runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    library_after = _files_in(folder_destination)

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert 'Duplicate, not imported        2' in result.output, result.output
    assert 'Success                        0' in result.output, result.output
    assert library_after == library_before, library_after

@mock.patch('elodie.constants.dry_run', False)
def test_update_live_photo_dry_run():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)
    runner = CliRunner()
    runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    library_before = _files_in(folder_destination)
    photo_dest = os.path.join(folder_destination, [f for f in library_before if f.endswith('.heic')][0])

    result = runner.invoke(elodie._update, ['--album', 'Holidays', '--dry-run', photo_dest])
    library_after = _files_in(folder_destination)

    shutil.rmtree(temporary_folder)
    shutil.rmtree(temporary_folder_destination)

    assert result.exit_code == 0, result.output
    assert library_after == library_before, library_after
    assert 'Holidays' in result.output and '.mov' in result.output, result.output

def _fail_for(extension, function):
    # Fails for the files with this extension, calls function for others
    def side_effect(_file, *args, **kwargs):
        if _file.upper().endswith(extension):
            return None
        return function(_file, *args, **kwargs)
    return side_effect

@mock.patch.object(elodie, 'send2trash')
def test_import_live_photo_keeps_video_with_photo_which_is_not_imported(mock_send2trash):
    # The pair stays in the source so it is imported together the next time,
    #  also with --trash
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)

    with mock.patch.object(elodie.FILESYSTEM, 'process_file',
                           side_effect=_fail_for('.HEIC', elodie.FILESYSTEM.process_file)):
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])
    library = _files_in(folder_destination)
    source = sorted(os.listdir(folder))

    assert result.exit_code == 1, result.output
    assert 'Error                          2' in result.output, result.output
    assert 'since its photo' in result.output, result.output
    assert library == [], library
    assert source == ['IMG_1234.HEIC', 'IMG_1234.MOV'], source
    mock_send2trash.assert_not_called()

@mock.patch.object(elodie, 'send2trash')
def test_import_live_photo_keeps_photo_when_video_is_not_imported(mock_send2trash):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)

    with mock.patch.object(elodie.FILESYSTEM, 'process_file',
                           side_effect=_fail_for('.MOV', elodie.FILESYSTEM.process_file)):
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])
    source = sorted(os.listdir(folder))

    assert result.exit_code == 1, result.output
    assert 'Success                        1' in result.output, result.output
    assert 'Error                          1' in result.output, result.output
    assert source == ['IMG_1234.HEIC', 'IMG_1234.MOV'], source
    mock_send2trash.assert_not_called()

def test_import_live_photo_video_when_only_the_photo_is_given():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder)

    result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, photo])
    library = _files_in(folder_destination)

    assert result.exit_code == 0, result.output
    # The video is reported as well
    assert 'Success                        2' in result.output, result.output
    assert [os.path.splitext(f)[1] for f in library] == ['.heic', '.mov'], library

def test_update_live_photo_keeps_video_with_photo_which_is_not_updated():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)
    runner = CliRunner()
    runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    library_before = _files_in(folder_destination)
    photo_dest = os.path.join(folder_destination, [f for f in library_before if f.endswith('.heic')][0])

    with mock.patch.object(Photo, 'set_album', return_value=False):
        result = runner.invoke(elodie._update, ['--album', 'Holidays', photo_dest])
    library_after = _files_in(folder_destination)
    video_album = Video(os.path.join(folder_destination, [f for f in library_after if f.endswith('.mov')][0])).get_album()

    assert result.exit_code == 1, result.output
    assert 'Error                          2' in result.output, result.output
    assert library_after == library_before, library_after
    assert video_album is None, video_album

def test_verify_live_photo_after_import_and_update():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)
    runner = CliRunner()
    runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    photo_dest = os.path.join(folder_destination, [f for f in _files_in(folder_destination) if f.endswith('.heic')][0])
    runner.invoke(elodie._update, ['--title', 'Beach', photo_dest])

    result = runner.invoke(elodie._verify)

    assert result.exit_code == 0, result.output
    assert 'Success                        2' in result.output, result.output

@mock.patch.object(elodie, 'send2trash')
def test_import_live_photo_with_apple_double_files(mock_send2trash):
    # Copied by a Mac to a USB drive: the AppleDouble files ._IMG_1234.MOV
    #  were imported as videos and ._IMG_1234.HEIC were errors
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)
    helper.create_apple_double(os.path.join(folder, '._IMG_1234.HEIC'))
    helper.create_apple_double(os.path.join(folder, '._IMG_1234.MOV'))
    trashed = []
    mock_send2trash.side_effect = lambda path: trashed.append(os.path.basename(path))

    result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])
    library = _files_in(folder_destination)

    assert result.exit_code == 0, result.output
    assert 'Success                        2' in result.output, result.output
    assert 'Error                          0' in result.output, result.output
    assert [os.path.splitext(f)[1] for f in library] == ['.heic', '.mov'], library
    # With their AppleDouble files, they stayed behind
    assert sorted(trashed) == ['._IMG_1234.HEIC', '._IMG_1234.MOV', 'IMG_1234.HEIC', 'IMG_1234.MOV'], trashed

def test_import_apple_double_file_given_explicitly():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    path = helper.create_apple_double(os.path.join(folder, '._IMG_1234.MOV'))

    result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, path])

    assert result.exit_code == 1, result.output
    assert 'Error                          1' in result.output, result.output
    assert _files_in(folder_destination) == []

@mock.patch('elodie.localstorage.WRITE_EVERY_SECONDS', 3600)
def test_import_loads_and_writes_the_hash_db_once():
    # For each file the databases were loaded and hash.json was written,
    #  which took seconds per file for a large library
    from elodie.localstorage import Db
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    for i in range(5):
        with open(os.path.join(folder, 'photo%d.jpg' % i), 'wb') as f:
            f.write(open(helper.get_file('plain.jpg'), 'rb').read() + str(i).encode())

    with mock.patch.object(Db, '_load', wraps=Db._load) as load, \
            mock.patch.object(Db, '_write', wraps=Db._write) as write:
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, folder])
    hash_db_writes = [c for c in write.call_args_list if c[0][0].endswith('hash.json')]
    with open(Db().hash_db_path) as f:
        hash_db = json.load(f)

    assert 'Success                        5' in result.output, result.output
    # hash.json and location.json
    assert load.call_count == 2, load.call_args_list
    assert len(hash_db_writes) == 1, hash_db_writes
    # The checksums of the sources and of the copies
    assert len(set(hash_db.values())) == 5, hash_db

@mock.patch('elodie.localstorage.WRITE_EVERY_CHANGES', 1000)
@mock.patch('elodie.localstorage.WRITE_EVERY_SECONDS', 3600)
@mock.patch.object(elodie, 'send2trash')
def test_import_duplicate_in_the_same_run_before_the_hash_db_is_written(mock_send2trash):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'a.jpg'))
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'b.jpg'))

    result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])

    assert 'Success                        1' in result.output, result.output
    assert 'Duplicate, not imported        1' in result.output, result.output
    # The duplicate is in the library so both are moved to the trash
    assert mock_send2trash.call_count == 2, mock_send2trash.call_args_list

@mock.patch('elodie.constants.dry_run', False)
def test_import_dry_run_reports_the_hash_db_update_once():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    for i in range(3):
        with open(os.path.join(folder, 'photo%d.jpg' % i), 'wb') as f:
            f.write(open(helper.get_file('plain.jpg'), 'rb').read() + str(i).encode())

    result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--dry-run', folder])

    assert result.output.count('[DRY-RUN] Would update hash database with 3 entries') == 1, result.output

@pytest.mark.skipif(helper.is_windows(), reason='Ctrl+C cannot be sent to a process group on Windows')
def test_ctrl_c_keeps_the_files_imported_before_in_the_hash_db():
    # The hash db is written periodically, what was imported before Ctrl+C
    #  is written when elodie exits
    import signal
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    for name in ('a.jpg', 'b.jpg', 'c.jpg'):
        with open(os.path.join(folder, name), 'wb') as f:
            f.write(open(helper.get_file('plain.jpg'), 'rb').read() + name.encode())
    # Removed after the test also when it fails
    application_directory = helper.create_working_folder()[1]
    script = (
        'import runpy, sys, time, elodie.filesystem as f\n'
        'process_file = f.FileSystem.process_file\n'
        'def blocking(self, _file, *a, **k):\n'
        '    if _file.endswith("c.jpg"):\n'
        '        print("started", flush=True)\n'
        '        time.sleep(60)\n'
        '    return process_file(self, _file, *a, **k)\n'
        'f.FileSystem.process_file = blocking\n'
        'sys.argv = sys.argv[1:]\n'
        'runpy.run_path(sys.argv[0], run_name="__main__")\n'
    )
    process = subprocess.Popen(
        [sys.executable, '-c', script, elodie_path, 'import', '--destination', folder_destination, folder],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
        cwd=os.path.dirname(elodie_path), env=dict(os.environ, ELODIE_APPLICATION_DIRECTORY=application_directory))
    try:
        _wait_for_line(process.stdout, 'started')
        os.killpg(process.pid, signal.SIGINT)
        output, _ = process.communicate(timeout=30)
    finally:
        process.kill()
    with open(os.path.join(application_directory, 'hash.json')) as f:
        hash_db = json.load(f)
    shutil.rmtree(application_directory)

    assert process.returncode == 1, output
    # a.jpg and b.jpg, with the checksums of the sources and of the copies
    assert len(set(hash_db.values())) == 2, hash_db

def _wait_for_line(stream, text):
    # Fails if the process ends before, instead of waiting forever
    lines = []
    for line in iter(stream.readline, ''):
        if line.strip() == text:
            return
        lines.append(line)
    pytest.fail('%s was not printed: %s' % (text, ''.join(lines)))

def _run_elodie(args, application_directory, **kwargs):
    return subprocess.Popen(
        [sys.executable, elodie_path] + args, cwd=os.path.dirname(elodie_path),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env=dict(os.environ, ELODIE_APPLICATION_DIRECTORY=application_directory), **kwargs)

def test_imports_at_the_same_time_keep_all_files_in_the_hash_db():
    # Each run holds the hash db in memory and writes it periodically, the
    #  last one replaced the files of the other
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    # Removed after the test also when it fails
    application_directory = helper.create_working_folder()[1]
    photo = open(helper.get_file('plain.jpg'), 'rb').read()
    for source in ('a', 'b'):
        os.makedirs(os.path.join(folder, source))
        for i in range(10):
            with open(os.path.join(folder, source, '%s%d.jpg' % (source, i)), 'wb') as f:
                f.write(photo + ('%s%d' % (source, i)).encode())

    processes = [_run_elodie(['import', '--destination', folder_destination, os.path.join(folder, source)],
                             application_directory) for source in ('a', 'b')]
    outputs = [p.communicate(timeout=120) for p in processes]
    with open(os.path.join(application_directory, 'hash.json')) as f:
        hash_db = json.load(f)
    shutil.rmtree(application_directory)

    assert [p.returncode for p in processes] == [0, 0], outputs
    assert len(set(hash_db.values())) == 20, hash_db

@pytest.mark.skipif(helper.is_windows(), reason='The lock is tested with flock')
@pytest.mark.parametrize('command', ['import', 'update', 'generate-db'])
def test_commands_which_change_the_databases_wait_for_another_run(command):
    from elodie.localstorage import Db
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))
    # update moves a file within its library
    library_file = os.path.join(folder_destination, '2015-12-Dec', 'Unknown Location', '2015-12-05_00-59-26-plain.jpg')
    if command == 'update':
        os.makedirs(os.path.dirname(library_file))
        shutil.move(os.path.join(folder, 'plain.jpg'), library_file)
    # Removed after the test also when it fails
    application_directory = helper.create_working_folder()[1]
    args = {
        'import': ['import', '--destination', folder_destination, folder],
        'update': ['update', '--album', 'Trip', library_file],
        'generate-db': ['generate-db', '--source', folder],
    }[command]
    hash_db = os.path.join(application_directory, 'hash.json')

    def state():
        return (_library_files(folder), _library_files(folder_destination),
                os.path.exists(hash_db) and os.path.getsize(hash_db))
    before = state()
    with mock.patch.dict(os.environ, {'ELODIE_APPLICATION_DIRECTORY': application_directory}):
        with Db.lock():
            process = _run_elodie(args, application_directory)
            waiting = process.stderr.readline()
            while_locked = state()
    output, _ = process.communicate(timeout=60)
    after = state()
    shutil.rmtree(application_directory)

    assert 'Waiting for another elodie' in waiting, waiting
    assert while_locked == before, (before, while_locked)
    assert process.returncode == 0, output
    assert 'Success                        1' in output, output
    assert after != before, after
    if command == 'update':
        assert after[1] == [os.path.join('2015-12-Dec', 'Trip', '2015-12-05_00-59-26-plain.jpg')], after

@pytest.mark.skipif(helper.is_windows(), reason='The lock is tested with flock')
def test_verify_does_not_wait_for_another_run():
    # It only reads the hash db
    from elodie.localstorage import Db
    # Removed after the test also when it fails
    application_directory = helper.create_working_folder()[1]

    with mock.patch.dict(os.environ, {'ELODIE_APPLICATION_DIRECTORY': application_directory}):
        with Db.lock():
            process = _run_elodie(['verify'], application_directory)
            output, errors = process.communicate(timeout=60)
    shutil.rmtree(application_directory)

    assert process.returncode == 0, (output, errors)
    assert 'Waiting' not in errors, errors

def test_interrupted_generate_db_keeps_the_hash_db():
    # It is replaced by the files of the library only when all were read
    from elodie.localstorage import Db
    temporary_folder, folder = helper.create_working_folder()
    for i in range(3):
        with open(os.path.join(folder, 'photo%d.jpg' % i), 'wb') as f:
            f.write(open(helper.get_file('plain.jpg'), 'rb').read() + str(i).encode())
    db = Db()
    db.add_hash('imported', '/library/photo.jpg', True)
    checksum = Db.checksum
    calls = []

    def interrupted(self, path, *args):
        calls.append(path)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return checksum(self, path, *args)
    with mock.patch.object(Db, 'checksum', interrupted):
        result = CliRunner().invoke(elodie._generate_db, ['--source', folder])
    with open(db.hash_db_path) as f:
        hash_db = json.load(f)

    assert result.exit_code == 1, result.output
    assert hash_db == {'imported': '/library/photo.jpg'}, hash_db

@mock.patch('elodie.localstorage.WRITE_EVERY_CHANGES', 1000)
@mock.patch('elodie.localstorage.WRITE_EVERY_SECONDS', 3600)
def test_import_reports_when_the_hash_db_cannot_be_written():
    from elodie.localstorage import Db
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))

    with mock.patch.object(Db, '_write', side_effect=OSError(28, 'No space left on device')):
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, folder])

    assert result.exit_code == 1, result.output
    assert not isinstance(result.exception, OSError), result.exception
    assert 'Could not write the database of elodie' in result.output, result.output
    assert 'Success                        1' in result.output, result.output

def test_ctrl_c_before_the_first_update_keeps_the_file_in_the_hash_db():
    # Interrupted after the first file was copied and added, before its
    #  update: nothing was pending so nothing was written
    from elodie.localstorage import Db
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))

    with mock.patch.object(Db, 'update_hash_db', side_effect=KeyboardInterrupt):
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, folder])
    library = _library_files(folder_destination)
    with open(Db().hash_db_path) as f:
        hash_db = json.load(f)

    assert result.exit_code == 1, result.output
    assert len(library) == 1, library
    assert set(hash_db.values()) == {os.path.join(folder_destination, library[0])}, hash_db

def _hang_up_import(ignore_sighup):
    import signal
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    for name in ('a.jpg', 'b.jpg', 'c.jpg'):
        with open(os.path.join(folder, name), 'wb') as f:
            f.write(open(helper.get_file('plain.jpg'), 'rb').read() + name.encode())
    # Removed after the test also when it fails
    application_directory = helper.create_working_folder()[1]
    # c.jpg waits a few seconds after it was announced
    script = (
        'import runpy, sys, time, elodie.filesystem as f\n'
        'process_file = f.FileSystem.process_file\n'
        'def slow(self, _file, *a, **k):\n'
        '    if _file.endswith("c.jpg"):\n'
        '        print("started", flush=True)\n'
        '        time.sleep(3)\n'
        '    return process_file(self, _file, *a, **k)\n'
        'f.FileSystem.process_file = slow\n'
        'sys.argv = sys.argv[1:]\n'
        'runpy.run_path(sys.argv[0], run_name="__main__")\n'
    )
    process = subprocess.Popen(
        [sys.executable, '-c', script, elodie_path, 'import', '--destination', folder_destination, folder],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.path.dirname(elodie_path),
        env=dict(os.environ, ELODIE_APPLICATION_DIRECTORY=application_directory),
        # nohup starts it with SIGHUP ignored
        preexec_fn=(lambda: signal.signal(signal.SIGHUP, signal.SIG_IGN)) if ignore_sighup else None)
    try:
        _wait_for_line(process.stdout, 'started')
        process.send_signal(signal.SIGHUP)
        output, _ = process.communicate(timeout=60)
    finally:
        process.kill()
    with open(os.path.join(application_directory, 'hash.json')) as f:
        hash_db = json.load(f)
    shutil.rmtree(application_directory)
    return process.returncode, output, hash_db

@pytest.mark.skipif(helper.is_windows(), reason='There is no SIGHUP on Windows')
def test_closed_terminal_stops_an_import_and_keeps_the_hash_db():
    # The terminal or SSH session of a long import was closed, SIGHUP killed
    #  elodie before the hash db was written
    returncode, output, hash_db = _hang_up_import(ignore_sighup=False)

    assert returncode == 1, output
    assert 'Aborted!' in output, output
    # a.jpg and b.jpg
    assert len(set(hash_db.values())) == 2, hash_db

@pytest.mark.skipif(helper.is_windows(), reason='There is no SIGHUP on Windows')
def test_import_with_nohup_continues_after_the_terminal_was_closed():
    returncode, output, hash_db = _hang_up_import(ignore_sighup=True)

    assert returncode == 0, output
    assert 'Success                        3' in output, output
    assert len(set(hash_db.values())) == 3, hash_db

@pytest.mark.skipif(helper.is_windows(), reason='SIGKILL is not available on Windows')
def test_hard_kill_keeps_the_files_of_the_periodic_writes_in_the_hash_db():
    # Nothing is written when elodie is killed (kill -9, power failure),
    #  the files of the periodic writes of the run must be in the hash db
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    for name in ('a.jpg', 'b.jpg', 'c.jpg'):
        with open(os.path.join(folder, name), 'wb') as f:
            f.write(open(helper.get_file('plain.jpg'), 'rb').read() + name.encode())
    # Removed after the test also when it fails
    application_directory = helper.create_working_folder()[1]
    # A write after each file: its checksum and the one of its copy
    script = (
        'import runpy, sys, time, elodie.filesystem as f, elodie.localstorage as l\n'
        'l.WRITE_EVERY_CHANGES = 2\n'
        'process_file = f.FileSystem.process_file\n'
        'def blocking(self, _file, *a, **k):\n'
        '    if _file.endswith("c.jpg"):\n'
        '        print("started", flush=True)\n'
        '        time.sleep(60)\n'
        '    return process_file(self, _file, *a, **k)\n'
        'f.FileSystem.process_file = blocking\n'
        'sys.argv = sys.argv[1:]\n'
        'runpy.run_path(sys.argv[0], run_name="__main__")\n'
    )
    process = subprocess.Popen(
        [sys.executable, '-c', script, elodie_path, 'import', '--destination', folder_destination, folder],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.path.dirname(elodie_path),
        env=dict(os.environ, ELODIE_APPLICATION_DIRECTORY=application_directory))
    try:
        _wait_for_line(process.stdout, 'started')
        process.kill()
        process.communicate(timeout=30)
    finally:
        process.kill()
    with open(os.path.join(application_directory, 'hash.json')) as f:
        content = f.read()
    shutil.rmtree(application_directory)
    hash_db = json.loads(content) if content.strip() else {}

    assert process.returncode == -9, process.returncode
    # a.jpg and b.jpg
    assert len(set(hash_db.values())) == 2, hash_db


# Motion Photos of Google and Samsung contain a video, Ultra HDR photos and the
#  photos of an iPhone a gain map. Writing metadata must keep them.
MOTION_PHOTO_PARTS = {
    'motion-photo-google-pixel-9-pro-xl-ultra-hdr.jpg': ['MotionPhotoVideo', 'MPImage2', 'DirectoryItemLength'],
    'motion-photo-samsung-galaxy-a34-mpv2.jpg': ['MotionPhotoVideo', 'EmbeddedVideoFile', 'DirectoryItemLength'],
    'motion-photo-samsung-galaxy-s20-versionless.heic': ['EmbeddedVideoFile'],
    'motion-photo-samsung-galaxy-s20fe-mpv2.heif': ['MotionPhotoVideo', 'DirectoryItemLength'],
    'motion-photo-samsung-galaxy-s20fe-mpv2.jpg': ['MotionPhotoVideo', 'EmbeddedVideoFile', 'DirectoryItemLength'],
    'motion-photo-samsung-galaxy-s23-ultra-mpv3.heic': ['MotionPhotoVideo', 'DirectoryItemLength'],
    'motion-photo-samsung-galaxy-tab-s9-mpv3.heic': ['MotionPhotoVideo', 'DirectoryItemLength'],
    'motion-photo-samsung-galaxy-tab-s9-mpv3.jpg': ['MotionPhotoVideo', 'EmbeddedVideoFile', 'DirectoryItemLength'],
    'live-photo-apple-iphone-15.heic': ['AuxiliaryImageType'],
}

def _embedded_parts(path):
    """The parts of a file which writing metadata must keep: its embedded
    video, gain map, image data and the lengths by which they are found.
    ExifTool is called directly for the exact bytes."""
    import hashlib
    from elodie.dependencies import get_exiftool
    parts = {}
    for tag in ('MotionPhotoVideo', 'EmbeddedVideoFile', 'MPImage2'):
        data = subprocess.run([get_exiftool(), '-b', '-' + tag, path], capture_output=True).stdout
        if data:
            parts[tag] = '%d bytes, sha256 %s' % (len(data), hashlib.sha256(data).hexdigest())
    info = json.loads(subprocess.run(
        [get_exiftool(), '-j', '-G1', '-api', 'ImageHashType=SHA256', '-ImageDataHash',
         '-XMP-GContainer:DirectoryItemLength', '-AuxiliaryImageType', path], capture_output=True).stdout)[0]
    for key, value in info.items():
        if key != 'SourceFile':
            parts[key.split(':')[-1]] = value
    return parts

@pytest.mark.parametrize('name', sorted(MOTION_PHOTO_PARTS))
@mock.patch.object(elodie.geolocation, 'coordinates_by_name', return_value={'latitude': 52.2297, 'longitude': 21.0122})
def test_writing_metadata_keeps_the_video_and_gain_map_of_a_photo(mock_coordinates, name):
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    origin = os.path.join(folder, name)
    shutil.copyfile(helper.get_asset(name), origin)
    before = _embedded_parts(origin)

    # The original name is written on import
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    after_import = _embedded_parts(dest_path)
    result = CliRunner().invoke(elodie._update, ['--album', 'Trip', '--title', 'Beach', '--time', '2020-06-01 12:00:00',
                                                 '--location', 'Warsaw', dest_path])
    library = _library_files(folder_destination)
    updated = os.path.join(folder_destination, library[0]) if len(library) == 1 else None
    after_update = _embedded_parts(updated) if updated else None

    for part in MOTION_PHOTO_PARTS[name] + ['ImageDataHash']:
        assert part in before, (part, before)
    assert after_import == before, after_import
    assert result.exit_code == 0, result.output
    assert Photo(updated).get_album() == 'Trip', library
    assert after_update == before, after_update

def test_import_and_update_an_apple_live_photo_of_an_iphone():
    # gh-474: a real pair, the video begins before the photo
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_asset('live-photo-apple-iphone-15.heic'), os.path.join(folder, 'IMG_4821.HEIC'))
    shutil.copyfile(helper.get_asset('live-photo-apple-iphone-15.mov'), os.path.join(folder, 'IMG_4821.MOV'))

    imported = CliRunner().invoke(elodie._import, ['--destination', folder_destination, folder])
    library = _library_files(folder_destination)
    photo = os.path.join(folder_destination, [f for f in library if f.endswith('.heic')][0])
    updated = CliRunner().invoke(elodie._update, ['--album', 'Sardinia', photo])
    library_after_update = _library_files(folder_destination)
    # Only the video is given
    video = os.path.join(folder_destination, [f for f in library_after_update if f.endswith('.mov')][0])
    updated_by_video = CliRunner().invoke(elodie._update, ['--album', 'Alghero', video])
    library_after_video_update = _library_files(folder_destination)

    assert imported.exit_code == 0, imported.output
    assert 'Success                        2' in imported.output, imported.output
    assert [os.path.splitext(f)[1] for f in library] == ['.heic', '.mov'], library
    assert os.path.splitext(library[0])[0] == os.path.splitext(library[1])[0], library
    assert os.path.basename(library[0]).startswith('2024-09-06_18-08-07-img_4821'), library
    assert updated.exit_code == 0, updated.output
    assert [os.path.dirname(f).split(os.sep)[-1] for f in library_after_update] == ['Sardinia', 'Sardinia'], library_after_update
    assert updated_by_video.exit_code == 0, updated_by_video.output
    assert [os.path.dirname(f).split(os.sep)[-1] for f in library_after_video_update] == ['Alghero', 'Alghero'], library_after_video_update

def test_update_live_photo_given_only_the_video():
    # The video was moved on its own by its own date, the pair was split
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder)
    _set_video_date(video, '2018:01:01 12:00:00+02:00')
    runner = CliRunner()
    runner.invoke(elodie._import, ['--destination', folder_destination, folder])
    video_dest = os.path.join(folder_destination, [f for f in _files_in(folder_destination) if f.endswith('.mov')][0])

    result = runner.invoke(elodie._update, ['--album', 'Holidays', video_dest])
    library = _files_in(folder_destination)
    albums = [Media.get_class_by_file(os.path.join(folder_destination, f), [Photo, Video]).get_album() for f in library]

    assert result.exit_code == 0, result.output
    # Both are reported
    assert 'Success                        2' in result.output, result.output
    assert [os.path.splitext(f)[1] for f in library] == ['.heic', '.mov'], library
    assert all(os.sep + 'Holidays' + os.sep in f for f in library), library
    assert os.path.splitext(library[0])[0] == os.path.splitext(library[1])[0], library
    assert albums == ['Holidays', 'Holidays'], albums

def test_update_video_with_the_name_of_another_photo():
    # The same name but the video of another photo: only the video changes
    temporary_folder, folder = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder, content_identifier='SOMETHING-ELSE')
    library = os.path.join(folder, 'library', '2019-05-May', 'Unknown Location')
    os.makedirs(library)
    photo_in_library = os.path.join(library, '2019-05-26_10-33-20-img_1234.heic')
    video_in_library = os.path.join(library, '2019-05-26_10-33-20-img_1234.mov')
    shutil.move(photo, photo_in_library)
    shutil.move(video, video_in_library)

    result = CliRunner().invoke(elodie._update, ['--album', 'Holidays', video_in_library])
    files = _files_in(os.path.join(folder, 'library'))

    assert result.exit_code == 0, result.output
    assert 'Success                        1' in result.output, result.output
    assert os.path.join('2019-05-May', 'Unknown Location', '2019-05-26_10-33-20-img_1234.heic') in files, files
    assert any(f.startswith(os.path.join('2019-05-May', 'Holidays')) and f.endswith('.mov') for f in files), files

@mock.patch.object(elodie, 'send2trash')
def test_import_send_to_trash_with_the_apple_double_file(mock_send2trash):
    # macOS wrote ._<name> next to the file on a USB drive
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))
    helper.create_apple_double(os.path.join(folder, '._plain.jpg'))
    shutil.copyfile(helper.get_file('with-title.jpg'), os.path.join(folder, 'with-title.jpg'))
    # Not an AppleDouble file although it has the name of one
    with open(os.path.join(folder, '._with-title.jpg'), 'w') as f:
        f.write('notes')
    shutil.copyfile(helper.get_file('invalid.jpg'), os.path.join(folder, 'invalid.jpg'))
    helper.create_apple_double(os.path.join(folder, '._invalid.jpg'))
    trashed = []
    mock_send2trash.side_effect = lambda path: trashed.append(os.path.basename(path))

    CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--trash', folder])

    # invalid.jpg was not imported, its AppleDouble file stays with it
    assert sorted(trashed) == ['._plain.jpg', 'plain.jpg', 'with-title.jpg'], trashed

@mock.patch('elodie.constants.dry_run', False)
def test_import_send_to_trash_with_the_apple_double_file_dry_run():
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('plain.jpg'), os.path.join(folder, 'plain.jpg'))
    helper.create_apple_double(os.path.join(folder, '._plain.jpg'))

    result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--trash', '--dry-run', folder])

    assert '[DRY-RUN] Would move to trash: %s' % os.path.join(folder, '._plain.jpg') in result.output, result.output
    assert sorted(os.listdir(folder)) == ['._plain.jpg', 'plain.jpg']

def test_import_and_update_a_live_photo_with_a_jpeg():
    # Older iPhones or with the setting Most Compatible store the photo of a
    #  Live Photo as JPEG
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder, photo_extension='JPG', jpeg=True)
    _set_video_date(video, '2018:01:01 12:00:00+02:00')

    imported = CliRunner().invoke(elodie._import, ['--destination', folder_destination, folder])
    library = _files_in(folder_destination)
    video_dest = os.path.join(folder_destination, [f for f in library if f.endswith('.mov')][0])
    updated = CliRunner().invoke(elodie._update, ['--album', 'Holidays', video_dest])
    library_after_update = _files_in(folder_destination)

    assert imported.exit_code == 0, imported.output
    assert 'Success                        2' in imported.output, imported.output
    assert [os.path.splitext(f)[1] for f in library] == ['.jpg', '.mov'], library
    assert os.path.splitext(library[0])[0] == os.path.splitext(library[1])[0], library
    assert updated.exit_code == 0, updated.output
    assert all(os.sep + 'Holidays' + os.sep in f for f in library_after_update), library_after_update

def _import_photo_before(folder_destination, photo):
    # The photo was imported before without its video, from another folder
    #  (the pairing of the Live Photo imports the video next to it too)
    photos_folder = helper.create_working_folder()[1]
    shutil.copyfile(photo, os.path.join(photos_folder, os.path.basename(photo)))
    CliRunner().invoke(elodie._import, ['--destination', folder_destination, photos_folder])

@pytest.mark.parametrize('how', ['folder', 'file'])
def test_import_live_photo_video_later_on_its_own(how):
    # Only the video of a Live Photo whose photo was imported before: it was
    #  named and filed by its own date, the pair was split
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder)
    _set_video_date(video, '2018:01:01 12:00:00+02:00')
    _import_photo_before(folder_destination, photo)

    if how == 'folder':
        # i.e. the photos are excluded
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--exclude-regex', r'\.HEIC$', folder])
    else:
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, video])
    library = _files_in(folder_destination)

    assert result.exit_code == 0, result.output
    assert 'Success                        1' in result.output, result.output
    assert [os.path.splitext(f)[1] for f in library] == ['.heic', '.mov'], library
    assert os.path.splitext(library[0])[0] == os.path.splitext(library[1])[0], library

def test_import_live_photo_video_on_its_own_when_its_photo_was_not_imported():
    # The photo next to it was changed since the one in the library was
    #  imported: it is not in the library, the video is imported by its own
    #  date as when there is no photo
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    photo, video = helper.create_live_photo(folder)
    _set_video_date(video, '2018:01:01 12:00:00+02:00')
    _import_photo_before(folder_destination, photo)
    ExifTool().execute(b'-overwrite_original', b'-XMP:Title=Changed', photo.encode())

    result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, video])
    library = _files_in(folder_destination)

    assert result.exit_code == 0, result.output
    videos = [f for f in library if f.endswith('.mov')]
    assert len(videos) == 1 and os.path.basename(videos[0]).startswith('2018-01-01'), library

def test_live_photo_video_is_read_once_for_its_pairing_and_import():
    # Its metadata was read to pair it and again to import or update it,
    #  an ExifTool call for each Live Photo of a large import
    import collections
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    helper.create_live_photo(folder)
    reads = collections.Counter()
    get_metadata = ExifTool.get_metadata

    def counted(self, filename):
        reads[os.path.splitext(filename)[1].lower()] += 1
        return get_metadata(self, filename)
    with mock.patch.object(ExifTool, 'get_metadata', counted):
        imported = CliRunner().invoke(elodie._import, ['--destination', folder_destination, folder])
        reads_of_import = dict(reads)
        reads.clear()
        photo = os.path.join(folder_destination, [f for f in _files_in(folder_destination) if f.endswith('.heic')][0])
        updated = CliRunner().invoke(elodie._update, ['--album', 'Holidays', photo])
        reads_of_update = dict(reads)

    assert 'Success                        2' in imported.output, imported.output
    assert 'Success                        2' in updated.output, updated.output
    # The source, its copy has the same metadata; the file before and after
    #  it was updated
    assert reads_of_import == {'.heic': 1, '.mov': 1}, reads_of_import
    assert reads_of_update['.mov'] == 2, reads_of_update

def _count_exiftool_calls():
    import collections
    counts = collections.Counter()
    get_metadata, set_tags = ExifTool.get_metadata, ExifTool.set_tags

    def read(self, filename):
        counts['read'] += 1
        return get_metadata(self, filename)

    def write(self, tags, filename):
        counts['write'] += 1
        return set_tags(self, tags, filename)
    return counts, mock.patch.multiple(ExifTool, get_metadata=read, set_tags=write)

@mock.patch.object(elodie.geolocation, 'coordinates_by_name', return_value={'latitude': 52.2297, 'longitude': 21.0122})
@pytest.mark.parametrize('file_name', ['plain.jpg', 'photo.heic', 'video.mov'])
@pytest.mark.parametrize('options', [[], ['--album-from-folder', '--time', '2020-06-01 12:00:00', '--location', 'Warsaw']])
def test_import_reads_and_writes_a_file_once(mock_coordinates, file_name, options):
    # The copy was read again and written for each change: ExifTool rewrites
    #  the whole file for each write, which takes long for large videos
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file(file_name), os.path.join(folder, file_name))
    counts, patched = _count_exiftool_calls()

    with patched:
        result = CliRunner().invoke(elodie._import, ['--destination', folder_destination] + options + [folder])

    assert 'Success                        1' in result.output, result.output
    assert dict(counts) == {'read': 1, 'write': 1}, dict(counts)

@mock.patch.object(elodie.geolocation, 'coordinates_by_name', return_value={'latitude': 52.2297, 'longitude': 21.0122})
def test_import_video_with_location_and_time_has_the_time_zone_of_the_location(mock_coordinates):
    # The time zone of the date of a video is the one of its position, the
    #  new one when both are given, not the one of the file (California)
    temporary_folder, folder = helper.create_working_folder()
    temporary_folder_destination, folder_destination = helper.create_working_folder()
    shutil.copyfile(helper.get_file('video.mov'), os.path.join(folder, 'video.mov'))

    result = CliRunner().invoke(elodie._import, ['--destination', folder_destination, '--location', 'Warsaw',
                                                 '--time', '2020-06-01 12:00:00', folder])
    video = os.path.join(folder_destination, _library_files(folder_destination)[0])
    tags = json.loads(subprocess.run([ExifTool().executable, '-j', '-G', '-QuickTime:CreationDate', '-QuickTime:CreateDate', video],
                                     capture_output=True).stdout)[0]

    assert result.exit_code == 0, result.output
    assert tags['QuickTime:CreationDate'] == '2020:06:01 12:00:00+02:00', tags
    assert tags['QuickTime:CreateDate'] == '2020:06:01 10:00:00', tags
