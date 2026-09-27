# Project imports
import errno
import os
import stat
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from elodie.compatability import _copyfile, _decode, _move, _rename

def test_decode_returns_str():
    # i.e. paths given as bytes by the command line on some systems
    assert _decode('/tmp/café.jpg') == '/tmp/café.jpg'
    assert _decode('/tmp/café.jpg'.encode('utf-8'), 'utf-8') == '/tmp/café.jpg'

def test_copyfile_and_rename(tmp_path):
    source = tmp_path / 'a.jpg'
    source.write_bytes(b'photo')

    _copyfile(str(source), str(tmp_path / 'b.jpg'))
    _rename(str(tmp_path / 'b.jpg'), str(tmp_path / 'c.jpg'))

    assert sorted(p.name for p in tmp_path.iterdir()) == ['a.jpg', 'c.jpg']
    assert (tmp_path / 'c.jpg').read_bytes() == b'photo'

def test_copyfile_and_rename_dry_run(tmp_path):
    source = tmp_path / 'a.jpg'
    source.write_bytes(b'photo')

    with mock.patch('elodie.constants.dry_run', True), mock.patch('builtins.print'):
        _copyfile(str(source), str(tmp_path / 'b.jpg'))
        _rename(str(source), str(tmp_path / 'c.jpg'))

    assert [p.name for p in tmp_path.iterdir()] == ['a.jpg']

def _interrupted_copy(src, dst, *args, **kwargs):
    # Ctrl-C or docker stop in the middle of a copy
    with open(dst, 'wb') as f:
        f.write(b'pho')
    raise KeyboardInterrupt

def test_copyfile_keeps_permissions(tmp_path):
    source = tmp_path / 'a.jpg'
    source.write_bytes(b'photo')
    os.chmod(str(source), 0o644)

    _copyfile(str(source), str(tmp_path / 'b.jpg'))

    assert stat.S_IMODE(os.stat(str(tmp_path / 'b.jpg')).st_mode) == 0o644

def test_interrupted_copyfile_leaves_no_incomplete_file(tmp_path):
    source = tmp_path / 'a.jpg'
    source.write_bytes(b'photo')
    (tmp_path / 'library').mkdir()

    with mock.patch('shutil.copyfile', side_effect=_interrupted_copy):
        with pytest.raises(KeyboardInterrupt):
            _copyfile(str(source), str(tmp_path / 'library' / 'b.jpg'))

    assert os.listdir(str(tmp_path / 'library')) == []

def test_move_to_another_file_system(tmp_path):
    source = tmp_path / 'a.jpg'
    source.write_bytes(b'photo')
    (tmp_path / 'library').mkdir()

    # rename fails between file systems
    with mock.patch('os.rename', side_effect=OSError(errno.EXDEV, 'Invalid cross-device link')):
        _move(str(source), str(tmp_path / 'library' / 'b.jpg'))

    assert not source.exists()
    assert os.listdir(str(tmp_path / 'library')) == ['b.jpg']
    assert (tmp_path / 'library' / 'b.jpg').read_bytes() == b'photo'

def test_interrupted_move_to_another_file_system_keeps_the_source(tmp_path):
    source = tmp_path / 'a.jpg'
    source.write_bytes(b'photo')
    (tmp_path / 'library').mkdir()

    with mock.patch('os.rename', side_effect=OSError(errno.EXDEV, 'Invalid cross-device link')), \
            mock.patch('shutil.copyfile', side_effect=_interrupted_copy):
        with pytest.raises(KeyboardInterrupt):
            _move(str(source), str(tmp_path / 'library' / 'b.jpg'))

    assert source.read_bytes() == b'photo'
    assert os.listdir(str(tmp_path / 'library')) == []
