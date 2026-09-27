# Project imports
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from elodie.compatability import _copyfile, _decode, _rename

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
