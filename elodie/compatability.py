import os
import shutil
import sys
import tempfile

from elodie import constants


def _decode(string, encoding=sys.getfilesystemencoding()):
    """Return paths given as bytes (i.e. by the command line on some
    systems) as str.
    """
    if isinstance(string, bytes):
        return string.decode(encoding)

    return string

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
    _copy_atomic(src, dst, shutil.copy)


def _copy_atomic(src, dst, copy_function=shutil.copy2):
    """Copy a file to a temporary name next to dst and rename it when it is
    complete, so an interrupted copy (i.e. Ctrl-C or docker stop) never
    leaves an incomplete file at dst.

    :returns: str dst
    """
    directory, name = os.path.split(os.path.abspath(dst))
    handle, temporary_path = tempfile.mkstemp(
        dir=directory, prefix='.%s.' % name, suffix='.elodie-tmp')
    os.close(handle)
    try:
        copy_function(src, temporary_path)
        os.replace(temporary_path, dst)
    except BaseException:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise
    return dst


def _move(src, dst):
    """Move a file. Between file systems it is copied, which is done
    atomically, and removed afterwards.
    """
    return shutil.move(src, dst, copy_function=_copy_atomic)


# If you want cross-platform overwriting of the destination,
# use os.replace() instead of rename().
# https://docs.python.org/3/library/os.html#os.rename
def _rename(src, dst):
    if constants.dry_run:
        print(f"[DRY-RUN] Would rename file: {src} -> {dst}")
        return

    return os.replace(src, dst)
