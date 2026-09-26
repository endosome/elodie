import os
import shutil
import sys
import time

from datetime import datetime, timedelta

from elodie import constants


def _decode(string, encoding=sys.getfilesystemencoding()):
    """Return paths given as bytes (i.e. by the command line on some
    systems) as str.
    """
    if isinstance(string, bytes):
        return string.decode(encoding)

    return string

def _gmtime(seconds):
    """Return a UTC time.struct_time for seconds since the epoch.

    Windows cannot handle negative timestamps (dates before 1970) with
    time.gmtime so we compute those with datetime instead.
    """
    if seconds < 0:
        dt = datetime(1970, 1, 1) + timedelta(seconds=seconds)
        return dt.utctimetuple()

    return time.gmtime(seconds)


def _bytes(string):
    return bytes(string, 'utf8')

def _copyfile(src, dst):
    if constants.dry_run:
        print(f"[DRY-RUN] Would copy file: {src} -> {dst}")
        return

    # Do not use copy2(), it will have an issue when copying to a
    #  network/mounted drive.
    # Using copy and manual set_date_from_filename gets the job done.
    # The calling function is responsible for setting the time.
    shutil.copy(src, dst)


# If you want cross-platform overwriting of the destination,
# use os.replace() instead of rename().
# https://docs.python.org/3/library/os.html#os.rename
def _rename(src, dst):
    if constants.dry_run:
        print(f"[DRY-RUN] Would rename file: {src} -> {dst}")
        return

    return os.replace(src, dst)
