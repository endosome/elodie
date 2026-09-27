# Project imports
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

import helper
from unittest import mock

from elodie.compatability import _copyfile, _decode, _gmtime, _rename

@pytest.mark.parametrize('seconds', [0, 1, 1460027726.0, 1460027726.5])
def test_gmtime_matches_time_gmtime(seconds):
    assert _gmtime(seconds) == time.gmtime(seconds), seconds

@pytest.mark.skipif(helper.is_windows(), reason='time.gmtime does not support negative timestamps on Windows')
@pytest.mark.parametrize('seconds', [-1, -0.5, -1.5, -315576000, -2208988800])
def test_gmtime_negative_matches_time_gmtime(seconds):
    assert _gmtime(seconds) == time.gmtime(seconds), seconds

def test_gmtime_negative_without_os_support(monkeypatch):
    monkeypatch.setattr(time, 'gmtime', helper.windows_gmtime)

    assert _gmtime(-315576000) == (1960, 1, 1, 12, 0, 0, 4, 1, 0)

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
