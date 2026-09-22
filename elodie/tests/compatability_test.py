from __future__ import absolute_import
# Project imports

import os
import shutil
import sys

from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import helper
from elodie.compatability import _decode, _bytes, _copyfile, _rename


def test_decode_returns_str_unchanged():
    # A plain str has no decode() attribute in Python 3 so it is
    # returned as-is.
    value = 'plain-string'
    assert _decode(value) == value


def test_decode_decodes_bytes():
    value = 'a-string-to-encode'
    encoded = value.encode('utf8')
    assert _decode(encoded) == value


def test_bytes_returns_bytes_instance():
    result = _bytes('hello')
    assert isinstance(result, bytes)
    assert result == b'hello'


@patch('elodie.constants.dry_run', True)
def test_copyfile_dry_run_does_not_copy():
    temporary_folder, folder = helper.create_working_folder()

    src = helper.get_file('plain.jpg')
    dst = os.path.join(folder, 'copied.jpg')

    _copyfile(src, dst)

    assert not os.path.isfile(dst)

    shutil.rmtree(folder)


def test_copyfile_copies_file():
    temporary_folder, folder = helper.create_working_folder()

    src = helper.get_file('plain.jpg')
    dst = os.path.join(folder, 'copied.jpg')

    _copyfile(src, dst)

    assert os.path.isfile(src)
    assert os.path.isfile(dst)
    assert helper.checksum(src) == helper.checksum(dst)

    shutil.rmtree(folder)


@patch('elodie.constants.dry_run', True)
def test_rename_dry_run_does_not_rename():
    temporary_folder, folder = helper.create_working_folder()

    src = os.path.join(folder, 'source.jpg')
    dst = os.path.join(folder, 'destination.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), src)

    _rename(src, dst)

    assert os.path.isfile(src)
    assert not os.path.isfile(dst)

    shutil.rmtree(folder)


def test_rename_renames_file():
    temporary_folder, folder = helper.create_working_folder()

    src = os.path.join(folder, 'source.jpg')
    dst = os.path.join(folder, 'destination.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), src)

    _rename(src, dst)

    assert not os.path.isfile(src)
    assert os.path.isfile(dst)

    shutil.rmtree(folder)
