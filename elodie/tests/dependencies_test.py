import re
import unittest.mock as mock

import pytest

from elodie.dependencies import get_exiftool
from elodie.dependencies import get_exiftool_version
from elodie.dependencies import is_exiftool_version_supported
from elodie.dependencies import verify_dependencies


@mock.patch('elodie.dependencies.shutil')
@mock.patch('elodie.dependencies.os')
def test_exiftool(mock_os, mock_shutil):
    mock_shutil.which.return_value = '/path/to/exiftool'
    assert get_exiftool() == '/path/to/exiftool'

    mock_shutil.which.return_value = None
    mock_os.path.isfile.return_value = True
    mock_os.path.access.return_value = True
    assert get_exiftool() == '/usr/local/bin/exiftool'

    mock_os.path.isfile.return_value = False
    assert get_exiftool() is None


@pytest.mark.parametrize('version,expected', [
    ('13.49', True),
    ('13.59', True),
    ('14.00', True),
    # ExifTool versions are decimal numbers, 13.5 is newer than 13.49
    ('13.5', True),
    ('13.48', False),
    ('12.76', False),
    ('9.99', False),
    # Unknown versions are allowed
    (None, True),
    ('unknown', True),
])
def test_is_exiftool_version_supported(version, expected):
    assert is_exiftool_version_supported(version) is expected


def test_get_exiftool_version():
    version = get_exiftool_version(get_exiftool())

    assert re.fullmatch(r'\d+\.\d+', version), version
    # The installed ExifTool is supported
    assert is_exiftool_version_supported(version), version


def test_get_exiftool_version_of_missing_executable():
    assert get_exiftool_version('/path/to/missing/exiftool') is None


@mock.patch(
    'elodie.dependencies.get_exiftool_version', return_value='13.47'
)
@mock.patch(
    'elodie.dependencies.get_exiftool', return_value='/path/to/exiftool'
)
def test_verify_dependencies_with_old_exiftool(
        mock_get_exiftool, mock_get_exiftool_version, capsys):
    assert verify_dependencies() is False
    assert '13.49' in capsys.readouterr().err


@mock.patch(
    'elodie.dependencies.get_exiftool_version', return_value='13.59'
)
@mock.patch(
    'elodie.dependencies.get_exiftool', return_value='/path/to/exiftool'
)
def test_verify_dependencies_with_supported_exiftool(
        mock_get_exiftool, mock_get_exiftool_version, capsys):
    assert verify_dependencies() is True
    assert capsys.readouterr().err == ''


@mock.patch('elodie.dependencies.get_exiftool', return_value=None)
def test_verify_dependencies_without_exiftool(mock_get_exiftool, capsys):
    assert verify_dependencies() is False
    assert "don't have exiftool installed" in capsys.readouterr().err
