# Test for pyexiftool non-ASCII filename handling
import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import helper
from elodie.external.pyexiftool import ExifTool, fsencode

def test_fsencode_with_non_ascii_characters():
    # gh-379: on systems whose file system encoding cannot represent a name
    #  (i.e. cp1252 on Windows) it is encoded as UTF-8 instead of failing.
    #  This only covers the encoding, not whether ExifTool opens the file on
    #  such a system.
    from elodie.external import pyexiftool
    name = "/tmp/test_фото_сад/тест_файл.jpg"

    assert pyexiftool.fsencode(name) == name.encode('utf-8')
    assert pyexiftool._fscodec('cp1252')(name) == name.encode('utf-8')
    # Names it can represent use the encoding
    assert pyexiftool._fscodec('cp1252')('/tmp/café.jpg') == b'/tmp/caf\xe9.jpg'
    assert pyexiftool.fsencode(b'/tmp/bytes') == b'/tmp/bytes'

def test_exiftool_with_non_ascii_file():
    """Test that ExifTool can process files with non-ASCII characters in paths.
    
    This is an integration test that reproduces the specific JSON parsing error
    from issue #379.
    """
    # Create a temporary file with non-ASCII characters in the path
    test_dir = os.path.join(tempfile.mkdtemp(), "фото_сад_café")
    test_file = os.path.join(test_dir, "тест_файл_été.jpg")
    
    # Get a real test image using helper function
    source_file = helper.get_file('with-album.jpg')
    
    assert source_file, "Test image file not found - helper.get_file('with-album.jpg') returned None"
    
    try:
        os.makedirs(test_dir, exist_ok=True)
        shutil.copy2(source_file, test_file)
        
        # Use the test-session ExifTool process from conftest.py.
        result = ExifTool().execute_json(test_file)
        assert result[0]['SourceFile'] == test_file
        # The metadata of the file was read
        assert result[0].get('XMP:Album') == 'Test Album', result[0]
            
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
        shutil.rmtree(os.path.dirname(test_dir))
def test_exiftool_loads_the_config_of_elodie():
    # ExifTool only loads a config given as its first argument. Elodie's
    #  config defines the XMP-elodie:Album tag which with-album.jpg has, it
    #  cannot be changed without it.
    temporary_folder, folder = helper.create_working_folder()
    origin = os.path.join(folder, 'photo.jpg')
    shutil.copyfile(helper.get_file('with-album.jpg'), origin)

    ExifTool().set_tags({'XMP-elodie:Album': ''}, origin)
    metadata = ExifTool().get_metadata(origin)

    shutil.rmtree(folder)

    assert 'XMP:Album' not in metadata, metadata.get('XMP:Album')

@pytest.mark.parametrize('addedargs,expected', [
    (['-config', '"/path/to/config"'], ['-config', '/path/to/config', '-stay_open']),
    (['-config', '/path/to/config', '-api', 'x'], ['-config', '/path/to/config', '-stay_open']),
    ([], ['-stay_open', 'True', '-@']),
])
def test_exiftool_config_is_the_first_argument(addedargs, expected):
    # A new instance, ExifTool() returns the one which is running
    exiftool = object.__new__(ExifTool)
    exiftool.__init__(executable_='exiftool', addedargs=addedargs)
    with patch('elodie.external.pyexiftool.subprocess.Popen') as popen:
        exiftool.start()
    args = popen.call_args[0][0]

    assert args[1:4] == expected, args
    # The other arguments stay common arguments after -common_args
    common_args = args[args.index('-common_args') + 1:]
    assert common_args == ['-G', '-n'] + addedargs[2:], args

def _new_exiftool(executable):
    # Another instance than the one of the tests (ExifTool is a singleton)
    exiftool = ExifTool.__new__(ExifTool)
    ExifTool.__init__(exiftool, executable_=executable)
    exiftool.start()
    return exiftool

def _crashing_exiftool(folder):
    # Exits without an answer the first time it is started, then it is
    #  exiftool: i.e. it crashed on a file
    from elodie.dependencies import get_exiftool
    path = os.path.join(folder, 'crashing-exiftool')
    with open(path, 'w') as f:
        f.write('#!/bin/sh\n'
                'if [ ! -e "%s/crashed" ]; then touch "%s/crashed"; read line; exit 7; fi\n'
                'exec "%s" "$@"\n' % (folder, folder, get_exiftool()))
    os.chmod(path, 0o755)
    return path

@pytest.mark.skipif(helper.is_windows(), reason='SIGINT cannot be sent to a process on Windows')
def test_terminate_when_exiftool_exited_already():
    # i.e. Ctrl+C reaches ExifTool before elodie stops it, it raised
    #  BrokenPipeError
    import signal
    from elodie.dependencies import get_exiftool
    exiftool = _new_exiftool(get_exiftool())
    exiftool._process.send_signal(signal.SIGINT)
    exiftool._process.wait()

    exiftool.terminate()

    assert not exiftool.running

@pytest.mark.skipif(helper.is_windows(), reason='Uses a shell script as exiftool')
def test_execute_when_exiftool_exits_during_a_command(tmp_path):
    # It read from the closed output forever at 100% CPU
    from elodie.external.pyexiftool import ExifToolError
    exiftool = _new_exiftool(_crashing_exiftool(str(tmp_path)))
    try:
        with pytest.raises(ExifToolError, match='ExifTool exited with 7 while it ran: -ver'):
            exiftool.execute(b'-ver')
        # A new one runs the next commands
        version = exiftool.execute(b'-ver')
    finally:
        exiftool.terminate()

    assert version.strip().startswith(b'13.'), version

@pytest.mark.skipif(helper.is_windows(), reason='Uses a shell script as exiftool')
def test_execute_after_exiftool_was_killed():
    from elodie.dependencies import get_exiftool
    exiftool = _new_exiftool(get_exiftool())
    exiftool._process.kill()
    exiftool._process.wait()
    try:
        version = exiftool.execute(b'-ver')
    finally:
        exiftool.terminate()

    assert version.strip().startswith(b'13.'), version

def _is_running(pid):
    # An exited process which was not reaped yet (a zombie) does not run. It
    #  stays when the process which inherits it does not reap it, i.e. when
    #  the tests run as the first process of a container.
    try:
        with open('/proc/%d/stat' % pid) as f:
            return f.read().rsplit(')', 1)[1].split()[0] != 'Z'
    except (FileNotFoundError, ProcessLookupError):
        # It ended before or while it was read
        return False

@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='Only Linux can end a process with its parent')
def test_exiftool_exits_when_elodie_is_killed():
    # With -stay_open ExifTool does not exit at the end of its input, it
    #  kept running after kill -9 and checked its input 100 times a second
    import signal
    import subprocess
    import time
    code = ('import sys, time; sys.path.insert(0, {root!r})\n'
            'from elodie.external.pyexiftool import ExifTool\n'
            'from elodie.dependencies import get_exiftool\n'
            'exiftool = ExifTool(executable_=get_exiftool())\n'
            'exiftool.start()\n'
            'print(exiftool._process.pid, flush=True)\n'
            'time.sleep(60)\n').format(
                root=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    elodie = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True)
    pid = int(elodie.stdout.readline())

    elodie.kill()
    elodie.wait()
    running = True
    for i in range(100):
        if not _is_running(pid):
            running = False
            break
        time.sleep(0.1)
    if running:
        os.kill(pid, signal.SIGKILL)

    assert not running, 'ExifTool still runs 10 s after elodie was killed'
