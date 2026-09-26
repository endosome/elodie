# Project imports
import importlib.util
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

os.environ['TZ'] = 'GMT'

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

    assert helper.path_tz_fix(os.path.join('2016-01-Jan','Houston','2016-01-04_05-28-15-audio.m4a')) in dest_path, dest_path

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

    expected_date = time.strftime('%Y-%m-%d_%H-%M-%S', time.gmtime(1584273600))
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

    expected_date = time.strftime('%Y-%m-%d_%H-%M-%S', time.gmtime(1584273600))
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

@pytest.mark.parametrize('name', [asset['name'] for asset in helper.ASSETS['assets']])
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

def test_import_destination_in_source():
    temporary_folder, folder = helper.create_working_folder()
    folder_destination = '{}/destination'.format(folder)
    os.mkdir(folder_destination)

    origin = '%s/plain.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    helper.reset_dbs()
    dest_path = elodie.import_file(origin, folder_destination, False, False, False)
    helper.restore_dbs()

    shutil.rmtree(folder)

    assert dest_path is None, dest_path

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
    temporary_folder_destination, folder_destination = helper.create_working_folder()

    # use a good and bad
    origin_invalid = '%s/invalid.jpg' % folder
    shutil.copyfile(helper.get_file('invalid.jpg'), origin_invalid)

    origin_valid = '%s/valid.jpg' % folder
    shutil.copyfile(helper.get_file('plain.jpg'), origin_valid)

    helper.reset_dbs()
    runner = CliRunner()
    result = runner.invoke(elodie._update, ['--album', 'test', origin_invalid, origin_valid])
    helper.restore_dbs()

    shutil.rmtree(folder)
    shutil.rmtree(folder_destination)

    assert result.exit_code == 1, result.exit_code

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
    result = runner.invoke(elodie._update, ['--location', 'foobar', '/does/not/exist'])
    assert "Could not find /does/not/exist\n" not in result.output, result.output
    result = runner.invoke(elodie._update, ['--location', 'foobar', '--debug', '/does/not/exist'])
    assert "Could not find /does/not/exist\n" in result.output, result.output
