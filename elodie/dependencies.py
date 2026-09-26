"""
Helpers for checking for an interacting with external dependencies. These are
things that Elodie requires, but aren't installed automatically for the user.
"""

import os
import sys
import shutil
import subprocess
from decimal import Decimal, InvalidOperation


#: Error to print when exiftool can't be found.
EXIFTOOL_ERROR = u"""
It looks like you don't have exiftool installed, which Elodie requires.
Please take a look at the installation steps in the readme:

https://github.com/jmathai/elodie#install-everything-you-need
""".lstrip()

#: Oldest ExifTool version which Elodie supports. 13.49 fixed writing to
#: HEIC Motion Photos, older versions made them unreadable by Google Photos.
#: 13.13 added the geolocation feature.
MINIMUM_EXIFTOOL_VERSION = '13.49'

#: Error to print when exiftool is too old.
EXIFTOOL_VERSION_ERROR = u"""
Elodie requires exiftool {minimum} or higher, but {path} is version {version}.
Older versions write HEIC Motion Photos which Google Photos can't display.
Please update it, see the installation steps in the readme:

https://github.com/endosome/elodie#install-exiftool
""".lstrip()


def get_exiftool():
    """Get path to executable exiftool binary.

    We wrap this since we call it in a few places and we do a fallback.

    :returns: str or None
    """
    path = shutil.which('exiftool')
    # If exiftool wasn't found we try to brute force the homebrew location
    if path is None:
        path = '/usr/local/bin/exiftool'
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            return None
    return path


def verify_dependencies():
    """Verify that external dependencies are installed.

    Prints a message to stderr and returns False if any dependencies are
    missing or too old.

    :returns: bool
    """
    exiftool = get_exiftool()
    if exiftool is None:
        print(EXIFTOOL_ERROR, file=sys.stderr)
        return False

    version = get_exiftool_version(exiftool)
    if not is_exiftool_version_supported(version):
        print(EXIFTOOL_VERSION_ERROR.format(
            minimum=MINIMUM_EXIFTOOL_VERSION,
            path=exiftool,
            version=version,
        ), file=sys.stderr)
        return False

    return True


def get_exiftool_version(exiftool):
    """Get the version of an exiftool executable.

    :param str exiftool: Path of the exiftool executable.
    :returns: str (i.e. '13.59') or None if it can't be determined
    """
    try:
        result = subprocess.run(
            [exiftool, '-ver'],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    version = result.stdout.strip()
    return version or None


def is_exiftool_version_supported(version):
    """Check a version against MINIMUM_EXIFTOOL_VERSION.

    ExifTool versions are decimal numbers, 13.5 would be newer than 13.49.

    :param str version: Version from get_exiftool_version.
    :returns: bool, True if the version is unknown
    """
    try:
        return Decimal(version) >= Decimal(MINIMUM_EXIFTOOL_VERSION)
    except (InvalidOperation, TypeError):
        return True
