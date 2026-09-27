#!/usr/bin/env python

import os
import re
import signal
import sys
import traceback
from datetime import datetime

import click
from send2trash import send2trash

# Verify that external dependencies are present first, so the user gets a
# more user-friendly error instead of an ImportError traceback.
from elodie.dependencies import verify_dependencies
if not verify_dependencies():
    sys.exit(1)

from elodie import constants
from elodie import geolocation
from elodie import log
from elodie.compatability import _decode
from elodie.config import load_config
from elodie.filesystem import FileSystem
from elodie.localstorage import Db
from elodie.media.base import Base, get_all_subclasses
from elodie.media.media import Media
from elodie.media.text import Text
from elodie.media.audio import Audio
from elodie.media.photo import Photo
from elodie.media.video import Video
from elodie.plugins.plugins import Plugins
from elodie.result import Result
from elodie.external.pyexiftool import ExifTool
from elodie.dependencies import get_exiftool

FILESYSTEM = FileSystem()

TIME_FORMATS = ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d')


def import_file(_file, destination, album_from_folder, trash, allow_duplicates, location=None, time=None):
    """Set file metadata and move it to destination.
    """
    FILESYSTEM.skipped_as_duplicate = False
    FILESYSTEM.imported_sidecars = []

    _file = _decode(_file)
    destination = _decode(destination)

    if not os.path.exists(_file):
        log.warn('Could not find %s' % _file)
        log.all('{"source":"%s", "error_msg":"Could not find %s"}' %
                  (_file, _file))
        return
    # A file in the library, i.e. when the source contains the destination,
    #  is not imported into it again.
    elif is_in_directory(_file, destination):
        log.all('{"source": "%s", "destination": "%s", "error_msg": "Source cannot be in destination"}' % (
            _file, destination))
        return


    media = Media.get_class_by_file(_file, get_all_subclasses())
    if not media:
        log.warn('Not a supported file (%s)' % _file)
        log.all('{"source":"%s", "error_msg":"Not a supported file"}' % _file)
        return

    # Changes to the metadata are written to the copy of the file and not
    #  to the source which should not be modified. gh-533
    media.defer_writes()

    if album_from_folder:
        media.set_album_from_folder()

    # Apply location and time updates if provided
    if location and not update_location(media, _file, location):
        return
    if time and not update_time(media, _file, time):
        return

    dest_path = FILESYSTEM.process_file(_file, destination,
        media, allowDuplicate=allow_duplicates, move=False)
    if dest_path:
        log.all('%s -> %s' % (_file, dest_path))
    if trash:
        # Only trash the source if it is safely in the destination: it was
        #  imported now or it had been imported before (a duplicate).
        if not dest_path and not is_imported(_file):
            log.warn('Not moving %s to trash, it was not imported' % _file)
        elif constants.dry_run:
            print(f"[DRY-RUN] Would move to trash: {_file}")
        else:
            modified = FILESYSTEM.get_directory_modified(_file)
            send2trash(_file)
            FILESYSTEM.update_directory_listing(_file, False, modified)

        # Sidecars which were imported with the file follow it to the trash
        #  unless another file still uses them (i.e. IMG_1234.JPG and
        #  IMG_1234.CR3 use IMG_1234.xmp). gh-341
        for sidecar in FILESYSTEM.imported_sidecars:
            if (not os.path.exists(sidecar) or
                    FILESYSTEM.is_sidecar_shared(sidecar, _file)):
                continue
            if constants.dry_run:
                print(f"[DRY-RUN] Would move to trash: {sidecar}")
            else:
                modified = FILESYSTEM.get_directory_modified(sidecar)
                send2trash(sidecar)
                FILESYSTEM.update_directory_listing(sidecar, False, modified)

    return dest_path or None


def is_in_directory(path, directory):
    """Check if path is inside directory, in any of its subfolders.
    """
    path = os.path.realpath(path)
    directory = os.path.realpath(directory)
    try:
        return (path != directory and
                os.path.commonpath([path, directory]) == directory)
    except ValueError:
        # On different drives on Windows
        return False


def report_exception(_file, exception):
    """Report an unexpected error for one file so the others can still
    be processed. The traceback is shown with --debug.
    """
    log.error('Could not process %s: %s: %s' % (
        _file, type(exception).__name__, exception))
    log.info(traceback.format_exc())


def parse_time(time_string):
    """Parse the value of --time.

    :returns: datetime or None if it is not in a supported format
    """
    for time_format in TIME_FORMATS:
        try:
            return datetime.strptime(time_string, time_format)
        except ValueError:
            pass
    return None


def validate_time(context, parameter, value):
    if value is not None and parse_time(value) is None:
        raise click.BadParameter(
            'Use YYYY-mm-dd hh:ii:ss or YYYY-mm-dd, not %s' % value)
    return value


def check_location(location_name):
    """Exit before any file is changed if the location of --location
    cannot be found, it would fail for every file.
    """
    if location_name and get_coordinates(location_name) is None:
        log.error('Could not find the location %s' % location_name)
        sys.exit(1)


def get_coordinates(location_name):
    """Coordinates of a place.

    :returns: tuple(float) or None if it could not be found
    """
    coordinates = geolocation.coordinates_by_name(location_name)
    if (not coordinates or coordinates.get('latitude') is None or
            coordinates.get('longitude') is None):
        return None
    return (coordinates['latitude'], coordinates['longitude'])


def is_imported(_file):
    """Check if an identical copy of _file exists at another path, i.e.
    it was imported before.
    """
    db = Db()
    checksum_file = db.get_hash(db.checksum(_file))
    return (
        checksum_file is not None and
        os.path.isfile(checksum_file) and
        os.path.abspath(checksum_file) != os.path.abspath(_file)
    )

@click.command('batch')
@click.option('--debug', default=False, is_flag=True,
              help='Show more verbose debug output.')
@click.option('--dry-run', default=False, is_flag=True,
              help='Show what would be done without making any changes.')
def _batch(debug, dry_run):
    """Run batch() for all plugins.
    """
    constants.debug = debug
    constants.dry_run = dry_run
    plugins = Plugins()
    if not plugins.run_batch():
        sys.exit(1)
       

@click.command('import')
@click.option('--destination', type=click.Path(file_okay=False),
              required=True, help='Copy imported files into this directory.')
@click.option('--source', type=click.Path(file_okay=False),
              help='Import files from this directory, if specified.')
@click.option('--file', type=click.Path(dir_okay=False),
              help='Import this file, if specified.')
@click.option('--album-from-folder', default=False, is_flag=True,
              help="Use images' folders as their album names.")
@click.option('--trash', default=False, is_flag=True,
              help='After copying files, move the old files to the trash.')
@click.option('--allow-duplicates', default=False, is_flag=True,
              help='Import the file even if it\'s already been imported.')
@click.option('--location', help=('Update the image location. Location '
                                  'should be the name of a place, like "Las '
                                  'Vegas, NV".'))
@click.option('--time', callback=validate_time,
              help=('Update the image time. Time should be in '
                    'YYYY-mm-dd hh:ii:ss or YYYY-mm-dd format.'))
@click.option('--debug', default=False, is_flag=True,
              help='Show more verbose debug output.')
@click.option('--dry-run', default=False, is_flag=True,
              help='Show what would be done without making any changes.')
@click.option('--exclude-regex', default=set(), multiple=True,
              help='Regular expression for directories or files to exclude.')
@click.argument('paths', nargs=-1, type=click.Path())
def _import(destination, source, file, album_from_folder, trash, allow_duplicates, location, time, debug, dry_run, exclude_regex, paths):
    """Import files or directories by reading their EXIF and organizing them accordingly.
    """
    constants.debug = debug
    constants.dry_run = dry_run
    has_errors = False
    result = Result()

    destination = _decode(destination)
    destination = os.path.abspath(os.path.expanduser(destination))

    files = set()
    paths = set(paths)
    if source:
        source = _decode(source)
        paths.add(source)
    if file:
        paths.add(file)

    # if no exclude list was passed in we check if there's a config
    if len(exclude_regex) == 0:
        config = load_config()
        if 'Exclusions' in config:
            exclude_regex = [value for key, value in config.items('Exclusions')]

    exclude_regex_list = set(exclude_regex)

    for path in paths:
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            # Files which are in the library already, i.e. when the source
            #  contains the destination, are skipped.
            files.update(
                f for f in FILESYSTEM.get_all_files(
                    path, None, exclude_regex_list)
                if not is_in_directory(f, destination))
        else:
            if not FILESYSTEM.should_exclude(path, exclude_regex_list, True):
                files.add(path)

    if files:
        check_location(location)

    for current_file in files:
        try:
            dest_path = import_file(current_file, destination,
                                    album_from_folder, trash,
                                    allow_duplicates, location, time)
        except Exception as e:
            report_exception(current_file, e)
            dest_path = None
            FILESYSTEM.skipped_as_duplicate = False
        if dest_path:
            status = True
        elif FILESYSTEM.skipped_as_duplicate:
            status = None  # duplicate, it is in the library already
        else:
            status = False  # error
        result.append((current_file, status))
        has_errors = has_errors or status is False

    result.write()

    if has_errors:
        sys.exit(1)


@click.command('generate-db')
@click.option('--source', type=click.Path(file_okay=False),
              required=True, help='Source of your photo library.')
@click.option('--debug', default=False, is_flag=True,
              help='Show more verbose debug output.')
def _generate_db(source, debug):
    """Regenerate the hash.json database which contains all of the sha256 signatures of media files. The hash.json file is located at ~/.elodie/.
    """
    constants.debug = debug
    result = Result()
    source = os.path.abspath(os.path.expanduser(source))

    if not os.path.isdir(source):
        log.error('Source is not a valid directory %s' % source)
        sys.exit(1)
        
    db = Db()
    db.backup_hash_db()
    db.reset_hash_db()

    for current_file in FILESYSTEM.get_all_files(source):
        result.append((current_file, True))
        db.add_hash(db.checksum(current_file), current_file)
        log.progress()
    
    db.update_hash_db()
    log.progress('', True)
    result.write()

@click.command('verify')
@click.option('--debug', default=False, is_flag=True,
              help='Show more verbose debug output.')
def _verify(debug):
    """Verify that the files in the library were not changed or damaged
    since they were imported (bit rot).
    """
    constants.debug = debug
    result = Result()
    db = Db()
    # A file can have more than one checksum: the one of the source it was
    #  imported from (to find duplicates) and the one of its content after
    #  its metadata was written.
    checksums = {}
    for checksum, file_path in db.all():
        checksums.setdefault(file_path, set()).add(checksum)

    for file_path, file_checksums in checksums.items():
        if not os.path.isfile(file_path):
            result.append((file_path, False))
            log.progress('x')
            continue

        actual_checksum = db.checksum(file_path)
        if actual_checksum in file_checksums:
            result.append((file_path, True))
            log.progress()
        else:
            result.append((file_path, False))
            log.progress('x')

    log.progress('', True)
    result.write()

    if result.error > 0:
        sys.exit(1)


def update_location(media, file_path, location_name):
    """Update location exif metadata of media.

    :returns: bool
    """
    coordinates = get_coordinates(location_name)
    if coordinates is None:
        log.error('Could not find the location %s' % location_name)
        return False

    if not media.set_location(*coordinates):
        log.error('Failed to update location of %s' % file_path)
        log.all('{"source":"%s", "error_msg":"Failed to update location"}' %
                file_path)
        return False
    return True


def update_time(media, file_path, time_string):
    """Update time exif metadata of media.

    :returns: bool
    """
    time = parse_time(time_string)
    if time is None:
        msg = ('Invalid time format. Use YYYY-mm-dd hh:ii:ss or YYYY-mm-dd')
        log.error(msg)
        log.all('{"source":"%s", "error_msg":"%s"}' % (file_path, msg))
        return False

    if not media.set_date_taken(time):
        log.error('Failed to update time of %s' % file_path)
        return False
    return True


def get_library_directory(media, file_path):
    """Get the folder of the library which contains a file, the one it
    was imported into.

    The folders of the file's current metadata are removed from its path.
    If the file is not in them (i.e. the configuration changed since the
    import) as many folders as the folder path definition has are removed.

    :returns: str
    """
    directory = os.path.dirname(os.path.abspath(file_path))
    parts = directory.split(os.sep)
    folder = FILESYSTEM.get_folder_path(media.get_metadata())
    if not folder:
        return directory

    folders = os.path.normpath(folder).split(os.sep)
    if (len(folders) < len(parts) and
            [os.path.normcase(f) for f in parts[-len(folders):]] ==
            [os.path.normcase(f) for f in folders]):
        return os.sep.join(parts[:-len(folders)]) or os.sep

    # '/path/to/file/photo.jpg' -> '/path/to/file' ->
    #  ['path','to','file'] -> ['path','to'] -> '/path/to'
    depth = len(FILESYSTEM.get_folder_path_definition())
    if depth == 0 or depth >= len(parts):
        return directory
    return os.sep.join(parts[:-depth]) or os.sep


def update_file(current_file, album, location, time, title):
    """Update the metadata of a file and move it to its folder in the
    library.

    :returns: bool
    """
    if not os.path.exists(current_file):
        log.warn('Could not find %s' % current_file)
        log.all('{"source":"%s", "error_msg":"Could not find %s"}' %
                  (current_file, current_file))
        return False

    media = Media.get_class_by_file(current_file, get_all_subclasses())
    if not media:
        log.warn('Not a supported file (%s)' % current_file)
        log.all('{"source":"%s", "error_msg":"Not a supported file"}' %
                current_file)
        return False

    # The library is found from the folders of the metadata before the
    #  update.
    destination = get_library_directory(media, current_file)

    if location and not update_location(media, current_file, location):
        return False
    if time and not update_time(media, current_file, time):
        return False
    if album and not media.set_album(album):
        log.error('Failed to update album of %s' % current_file)
        return False

    # Updating a title can be problematic when doing it 2+ times on a file.
    # You would end up with img_001.jpg -> img_001-first-title.jpg ->
    # img_001-first-title-second-title.jpg.
    # To resolve that we have to track the prior title (if there was one.
    # Then we massage the updated_media's metadata['base_name'] to remove
    # the old title.
    # Since FileSystem.get_file_name() relies on base_name it will properly
    #  rename the file by updating the title instead of appending it.
    remove_old_title_from_name = False
    if title:
        # We call get_metadata() to cache it before making any changes
        metadata = media.get_metadata()
        original_title = metadata['title']
        if not media.set_title(title):
            log.error('Failed to update title of %s' % current_file)
            return False
        if original_title:
            # @TODO: We should move this to a shared method since
            # FileSystem.get_file_name() does it too.
            original_title = re.sub(r'\W+', '-', original_title.lower())
            original_base_name = metadata['base_name']
            remove_old_title_from_name = True

    if constants.dry_run:
        # Nothing was written to the file so we use the metadata
        #  which was updated in memory.
        updated_media = media
    else:
        updated_media = Media.get_class_by_file(current_file,
                                                get_all_subclasses())
    # See comments above on why we have to do this when titles
    # get updated.
    if remove_old_title_from_name and len(original_title) > 0:
        updated_media.get_metadata()
        updated_media.set_metadata_basename(
            original_base_name.replace('-%s' % original_title, ''))

    dest_path = FILESYSTEM.process_file(current_file, destination,
        updated_media, move=True, allowDuplicate=True)
    log.info(u'%s -> %s' % (current_file, dest_path))
    log.all('{"source":"%s", "destination":"%s"}' % (current_file,
                                                       dest_path))
    # If the folder we moved the file out of or its parent are empty
    # we delete it.
    FILESYSTEM.delete_directory_if_empty(os.path.dirname(current_file))
    FILESYSTEM.delete_directory_if_empty(
        os.path.dirname(os.path.dirname(current_file)))
    return bool(dest_path)


@click.command('update')
@click.option('--album', help='Update the image album.')
@click.option('--location', help=('Update the image location. Location '
                                  'should be the name of a place, like "Las '
                                  'Vegas, NV".'))
@click.option('--time', callback=validate_time,
              help=('Update the image time. Time should be in '
                    'YYYY-mm-dd hh:ii:ss or YYYY-mm-dd format.'))
@click.option('--title', help='Update the image title.')
@click.option('--debug', default=False, is_flag=True,
              help='Show more verbose debug output.')
@click.option('--dry-run', default=False, is_flag=True,
              help='Show what would be done without making any changes.')
@click.argument('paths', nargs=-1,
                required=True)
def _update(album, location, time, title, paths, debug, dry_run):
    """Update a file's EXIF. Automatically modifies the file's location and file name accordingly.
    """
    constants.debug = debug
    constants.dry_run = dry_run
    if not (album or location or time or title):
        raise click.UsageError(
            'Nothing to update, use --album, --location, --time or --title.')

    has_errors = False
    result = Result()

    files = set()
    for path in paths:
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            files.update(FILESYSTEM.get_all_files(path, None))
        else:
            files.add(path)

    check_location(location)

    for current_file in files:
        try:
            status = update_file(current_file, album, location, time, title)
        except Exception as e:
            report_exception(current_file, e)
            status = False
        result.append((current_file, status))
        has_errors = has_errors or not status

    result.write()

    if has_errors:
        sys.exit(1)


def _terminate(signum, frame):
    raise KeyboardInterrupt


def stop_on_sigterm():
    """Stop on SIGTERM like on Ctrl-C, i.e. on docker stop. Without a
    handler it is ignored when elodie is the first process of a container
    which is killed after a timeout then.
    """
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, _terminate)


@click.group()
def main():
    pass


main.add_command(_import)
main.add_command(_update)
main.add_command(_generate_db)
main.add_command(_verify)
main.add_command(_batch)


if __name__ == '__main__':
    stop_on_sigterm()
    #Initialize ExifTool Subprocess
    exiftool_addedargs = [
       u'-config',
        u'"{}"'.format(constants.exiftool_config)
    ]
    with ExifTool(executable_=get_exiftool(), addedargs=exiftool_addedargs) as et:
        main()
