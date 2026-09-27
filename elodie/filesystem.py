"""
General file system methods.

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""

import calendar
import filecmp
import os
import re
import shutil
import time
from stat import S_IWUSR
from send2trash import send2trash

from elodie import compatability
from elodie import constants
from elodie import geolocation
from elodie import log
from elodie.config import load_config
from elodie.localstorage import Db
from elodie.media.base import Base, get_all_subclasses
from elodie.plugins.plugins import Plugins

class FileSystem(object):
    """A class for interacting with the file system."""

    def __init__(self):
        # The default folder path is along the lines of 2017-06-17_01-04-14-dsc_1234-some-title.jpg
        self.default_file_name_definition = {
            'date': '%Y-%m-%d_%H-%M-%S',
            'name': '%date-%original_name-%title.%extension',
        }
        # The default folder path is along the lines of 2015-01-Jan/Chicago
        self.default_folder_path_definition = {
            'date': '%Y-%m-%b',
            'location': '%city',
            'full_path': '%date/%album|%location|"{}"'.format(
                            geolocation.__DEFAULT_LOCATION__
                         ),
        }
        self.cached_file_name_definition = None
        self.cached_folder_path_definition = None
        # Set by process_file() if the file was not imported because it was
        #  imported before, so it can be told apart from errors. gh-507
        self.skipped_as_duplicate = False
        # Sidecar files (i.e. edits in .xmp or .aae files) are imported with
        #  the file they belong to. gh-341
        self.default_sidecar_extensions = ('aae', 'xmp')
        # Set by process_file() to the sidecar files it imported
        self.imported_sidecars = []
        # Folder listings to find sidecar files, see list_directory()
        self.directory_listings = {}
        # Python3 treats the regex \s differently than Python2.
        # It captures some additional characters like the unicode checkmark \u2713.
        # See build failures in Python3 here.
        #  https://travis-ci.org/jmathai/elodie/builds/483012902
        self.whitespace_regex = '[ \t\n\r\f\v]+'

        # Instantiate a plugins object
        self.plugins = Plugins()

    def _file_operation(self, operation_type, src, dst=None):
        """Perform file operation with dry-run support."""
        if constants.dry_run:
            if dst:
                print(f"[DRY-RUN] Would {operation_type}: {src} -> {dst}")
            else:
                print(f"[DRY-RUN] Would {operation_type}: {src}")
            return True  # Simulate success
        
        # Perform actual operation. The cached listings of the directories
        #  are updated if nothing else changed them in the meantime.
        src_modified = self.get_directory_modified(src)
        if operation_type == 'move':
            dst_modified = self.get_directory_modified(dst)
            shutil.move(src, dst)
            self.update_directory_listing(src, False, src_modified)
            if os.path.dirname(src) == os.path.dirname(dst):
                # Renamed, the listing was updated for the removal
                dst_modified = self.get_directory_modified(dst)
            self.update_directory_listing(dst, True, dst_modified)
        elif operation_type == 'copy':
            dst_modified = self.get_directory_modified(dst)
            compatability._copyfile(src, dst)
            self.update_directory_listing(dst, True, dst_modified)
        elif operation_type == 'remove':
            os.remove(src)
            self.update_directory_listing(src, False, src_modified)
        elif operation_type == 'send2trash':
            send2trash(src)
            self.update_directory_listing(src, False, src_modified)
        return True

    def create_directory(self, directory_path):
        """Create a directory if it does not already exist.

        :param str directory_name: A fully qualified path of the
            to create.
        :returns: bool
        """
        try:
            if os.path.exists(directory_path):
                return True
            elif constants.dry_run:
                print(f"[DRY-RUN] Would create directory: {directory_path}")
                return True  # Simulate success
            else:
                os.makedirs(directory_path)
                return True
        except OSError:
            # OSError is thrown for cases like no permission
            pass

        return False

    def delete_directory_if_empty(self, directory_path):
        """Delete a directory only if it's empty.

        Instead of checking first using `len([name for name in
        os.listdir(directory_path)]) == 0`, we catch the OSError exception.

        :param str directory_name: A fully qualified path of the directory
            to delete.
        """
        try:
            os.rmdir(directory_path)
            return True
        except OSError:
            pass

        return False

    def get_all_files(self, path, extensions=None, exclude_regex_list=set()):
        """Recursively get all files which match a path and extension.

        :param str path string: Path to start recursive file listing
        :param tuple(str) extensions: File extensions to include (whitelist)
        :returns: generator
        """
        # If extensions is None then we get all supported extensions
        if not extensions:
            extensions = set()
            subclasses = get_all_subclasses(Base)
            for cls in subclasses:
                extensions.update(cls.extensions)

        # Create a list of compiled regular expressions to match against the file path
        compiled_regex_list = [re.compile(regex) for regex in exclude_regex_list]
        for dirname, dirnames, filenames in os.walk(path):
            for filename in filenames:
                # If file extension is in `extensions` 
                # And if file path is not in exclude regexes
                # Then append to the list
                filename_path = os.path.join(dirname, filename)
                if (
                        os.path.splitext(filename)[1][1:].lower() in extensions and
                        not self.should_exclude(filename_path, compiled_regex_list, False)
                    ):
                    yield filename_path

    def is_same_file(self, path, other_path):
        """Check if two paths are the same file, also if they are written
        differently: relative, through a symlink, as a hard link or with
        different case on a case-insensitive file system (Windows, macOS).

        :param str path: Path of a file.
        :param str other_path: Path of a file, which may not exist.
        :returns: bool
        """
        if os.path.exists(path) and os.path.exists(other_path):
            try:
                return os.path.samefile(path, other_path)
            except OSError:
                pass

        return (
            os.path.normcase(os.path.abspath(path)) ==
            os.path.normcase(os.path.abspath(other_path))
        )

    def get_current_directory(self):
        """Get the current working directory.

        :returns: str
        """
        return os.getcwd()

    def get_file_name(self, metadata):
        """Generate file name for a photo or video using its metadata.

        Originally we hardcoded the file name to include an ISO date format.
        We use an ISO8601-like format for the file name prefix. Instead of
        colons as the separator for hours, minutes and seconds we use a hyphen.
        https://en.wikipedia.org/wiki/ISO_8601#General_principles

        PR #225 made the file name customizable and fixed issues #107 #110 #111.
        https://github.com/jmathai/elodie/pull/225

        :param media: A Photo or Video instance
        :type media: :class:`~elodie.media.photo.Photo` or
            :class:`~elodie.media.video.Video`
        :returns: str or None for non-photo or non-videos
        """
        if(metadata is None):
            return None

        # Get the name template and definition.
        # Name template is in the form %date-%original_name-%title.%extension
        # Definition is in the form
        #  [
        #    [('date', '%Y-%m-%d_%H-%M-%S')],
        #    [('original_name', '')], [('title', '')], // contains a fallback
        #    [('extension', '')]
        #  ]
        name_template, definition = self.get_file_name_definition()

        name = name_template
        for parts in definition:
            this_value = None
            for this_part in parts:
                part, mask = this_part
                if part in ('date', 'day', 'month', 'year'):
                    this_value = time.strftime(mask, metadata['date_taken'])
                    break
                elif part in ('location', 'city', 'state', 'country'):
                    place_name = geolocation.place_name(
                        metadata['latitude'],
                        metadata['longitude']
                    )

                    location_parts = re.findall('(%[^%]+)', mask)
                    this_value = self.parse_mask_for_location(
                        mask,
                        location_parts,
                        place_name,
                    )
                    break
                elif part in ('album', 'extension', 'title'):
                    if metadata[part]:
                        this_value = re.sub(self.whitespace_regex, '-', metadata[part].strip())
                        break
                elif part in ('original_name'):
                    # First we check if we have metadata['original_name'].
                    # We have to do this for backwards compatibility because
                    #   we original did not store this back into EXIF.
                    if metadata[part]:
                        this_value = os.path.splitext(metadata['original_name'])[0]
                    else:
                        # We didn't always store original_name so this is 
                        #  for backwards compatability.
                        # We want to remove the hardcoded date prefix we used 
                        #  to add to the name.
                        # This helps when re-running the program on file 
                        #  which were already processed.
                        this_value = re.sub(
                            r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-',
                            '',
                            metadata['base_name']
                        )
                        if(len(this_value) == 0):
                            this_value = metadata['base_name']

                    # Lastly we want to sanitize the name
                    this_value = re.sub(self.whitespace_regex, '-', this_value.strip())
                elif part.startswith('"') and part.endswith('"'):
                    this_value = part[1:-1]
                    break

            # Here we replace the placeholder with it's corresponding value.
            # Check if this_value was not set so that the placeholder
            #  can be removed completely.
            # For example, %title- will be replaced with ''
            # Else replace the placeholder (i.e. %title) with the value.
            if this_value is None:
                name = re.sub(
                    #'[^a-z_]+%{}'.format(part),
                    '[^a-zA-Z0-9_]+%{}'.format(part),
                    '',
                    name,
                )
            else:
                name = re.sub(
                    '%{}'.format(part),
                    this_value,
                    name,
                )

        config = load_config()

        if('File' in config and 'capitalization' in config['File'] and config['File']['capitalization'] == 'upper'):
            return name.upper()
        else:
            return name.lower()

    def get_file_name_definition(self):
        """Returns a list of folder definitions.

        Each element in the list represents a folder.
        Fallback folders are supported and are nested lists.
        Return values take the following form.
        [
            ('date', '%Y-%m-%d'),
            [
                ('location', '%city'),
                ('album', ''),
                ('"Unknown Location", '')
            ]
        ]

        :returns: list
        """
        # If we've done this already then return it immediately without
        # incurring any extra work
        if self.cached_file_name_definition is not None:
            return self.cached_file_name_definition

        config = load_config()

        # If File is in the config we assume name and its
        #  corresponding values are also present
        config_file = self.default_file_name_definition
        if('File' in config):
            config_file = config['File']

        # Find all subpatterns of name that map to the components of the file's
        #  name.
        #  I.e. %date-%original_name-%title.%extension => ['date', 'original_name', 'title', 'extension'] #noqa
        path_parts = re.findall(
                         r'(\%[a-z_]+)',
                         config_file['name']
                     )

        if not path_parts or len(path_parts) == 0:
            return (config_file['name'], self.default_file_name_definition)

        self.cached_file_name_definition = []
        for part in path_parts:
            if part in config_file:
                part = part[1:]
                self.cached_file_name_definition.append(
                    [(part, config_file[part])]
                )
            else:
                this_part = []
                for p in part.split('|'):
                    p = p[1:]
                    this_part.append(
                        (p, config_file[p] if p in config_file else '')
                    )
                self.cached_file_name_definition.append(this_part)

        self.cached_file_name_definition = (config_file['name'], self.cached_file_name_definition)
        return self.cached_file_name_definition

    def get_folder_path_definition(self):
        """Returns a list of folder definitions.

        Each element in the list represents a folder.
        Fallback folders are supported and are nested lists.
        A folder which combines placeholders with each other or with other
        text (i.e. %year-%month) is kept as is and evaluated like %custom.
        Return values take the following form.
        [
            ('date', '%Y-%m-%d'),
            [
                ('location', '%city'),
                ('album', ''),
                ('"Unknown Location", '')
            ],
            [('%month, %location', '')]
        ]

        :returns: list
        """
        # If we've done this already then return it immediately without
        # incurring any extra work
        if self.cached_folder_path_definition is not None:
            return self.cached_folder_path_definition

        config = load_config()

        # If Directory is in the config we assume full_path and its
        #  corresponding values (date, location) are also present
        config_directory = self.default_folder_path_definition
        if('Directory' in config):
            config_directory = config['Directory']

        # Find all subpatterns of full_path that map to directories.
        #  I.e. %foo/%bar => ['foo', 'bar']
        #  I.e. %foo/%bar|%example|"something" => ['foo', 'bar|example|"something"']
        path_parts = re.findall(
                         r'(\%[^/]+)',
                         config_directory['full_path']
                     )

        if not path_parts or len(path_parts) == 0:
            return self.default_folder_path_definition

        self.cached_folder_path_definition = []
        for part in path_parts:
            this_part = []
            for p in part.split('|'):
                p = p.strip()
                # The % is optional for fallback strings (%"foo" or "foo").
                name = p[1:] if p.startswith('%') else p
                if '%' in name and not self.is_fallback_string(name):
                    # Placeholders combined with each other or other text,
                    #  i.e. %year-%month or %month, %location. gh-534
                    this_part.append((p, ''))
                else:
                    mask = ''
                    if name in config_directory:
                        mask = config_directory[name]
                    this_part.append((name, mask))
            self.cached_folder_path_definition.append(this_part)

        return self.cached_folder_path_definition

    def is_fallback_string(self, part):
        """Check if a part of a folder is a fallback string (i.e. "foo").

        :param str part: Part of the folder path definition.
        :returns: bool
        """
        return len(part) > 1 and part.startswith('"') and part.endswith('"')

    def is_combined_part(self, part):
        """Check if a part of a folder path definition combines placeholders
        with each other or other text (i.e. %year-%month).

        :param str part: Part of the folder path definition.
        :returns: bool
        """
        return '%' in part and not self.is_fallback_string(part)

    def get_folder_path_mask(self, part):
        """Returns the mask of a placeholder used within %custom or combined
        with other placeholders in a folder (i.e. %year-%month).

        :param str part: Name of the placeholder (i.e. month from %month).
        :returns: str
        """
        config = load_config()
        config_directory = self.default_folder_path_definition
        if 'Directory' in config:
            config_directory = config['Directory']

        if part in config_directory:
            return config_directory[part]
        elif part in ('city', 'state', 'country'):
            return '%{}'.format(part)
        return ''

    def get_folder_path(self, metadata, path_parts=None):
        """Given a media's metadata this function returns the folder path as a string.

        :param dict metadata: Metadata dictionary.
        :returns: str
        """
        if path_parts is None:
            path_parts = self.get_folder_path_definition()
        path = []
        for path_part in path_parts:
            # We support fallback values so that
            #  'album|city|"Unknown Location"
            #  %album|%city|"Unknown Location" results in
            #  My Album - when an album exists
            #  Sunnyvale - when no album exists but a city exists
            #  Unknown Location - when neither an album nor location exist
            # A folder which combines placeholders (i.e. %album - %month) is
            #  only used if all of them have a value. If no fallback does we
            #  use the first one which has any value. gh-534
            partial_path = None
            for this_part in path_part:
                part, mask = this_part
                if self.is_combined_part(part):
                    this_path, values = self.parse_combined_part(
                        part, metadata)
                    complete = all(values)
                else:
                    this_path = self.get_dynamic_path(part, mask, metadata)
                    complete = True
                if this_path and complete:
                    path.append(this_path.strip())
                    # We break as soon as we have a value to append
                    # Else we continue for fallbacks
                    break
                if this_path and partial_path is None:
                    partial_path = this_path
            else:
                if partial_path:
                    path.append(partial_path.strip())
        return os.path.join(*path)

    def get_dynamic_path(self, part, mask, metadata):
        """Parse a specific folder's name given a mask and metadata.

        :param part: Name of the part as defined in the path (i.e. date from %date)
        :param mask: Mask representing the template for the path (i.e. %city %state
        :param metadata: Metadata dictionary.
        :returns: str
        """

        # Each part has its own custom logic and we evaluate a single part and return
        #  the evaluated string.
        if part == 'custom':
            return self.parse_custom_mask(mask, metadata)[0]
        elif self.is_combined_part(part):
            return self.parse_combined_part(part, metadata)[0]
        elif part == 'date':
            config = load_config()
            # If Directory is in the config we assume full_path and its
            #  corresponding values (date, location) are also present
            config_directory = self.default_folder_path_definition
            if('Directory' in config):
                config_directory = config['Directory']
            date_mask = ''
            if 'date' in config_directory:
                date_mask = config_directory['date']
            return time.strftime(date_mask, metadata['date_taken'])
        elif part in ('day', 'month', 'year'):
            return time.strftime(mask, metadata['date_taken'])
        elif part in ('location', 'city', 'state', 'country'):
            place_name = geolocation.place_name(
                metadata['latitude'],
                metadata['longitude']
            )

            location_parts = re.findall('(%[^%]+)', mask)
            parsed_folder_name = self.parse_mask_for_location(
                mask,
                location_parts,
                place_name,
            )
            return parsed_folder_name
        elif part in ('album', 'camera_make', 'camera_model'):
            if metadata[part]:
                return metadata[part]
        elif self.is_fallback_string(part):
            # Fallback string
            return part[1:-1]

        return ''

    def parse_custom_mask(self, mask, metadata):
        """Replace each placeholder in a mask (i.e. %month, %location) with
        its value using the mask of the placeholder.

        :param str mask: Mask with placeholders and other text.
        :param dict metadata: Metadata dictionary.
        :returns: tuple of the folder name and the list of values.
        """
        values = []

        def replace(match):
            value = self.get_dynamic_path(
                match.group(1),
                self.get_folder_path_mask(match.group(1)),
                metadata
            )
            values.append(value)
            return value

        folder = re.sub(r'%([a-z_]+)', replace, mask)
        return (folder, values)

    def parse_combined_part(self, part, metadata):
        """Evaluate a folder which combines placeholders (i.e. %year-%month).

        :param str part: Part of the folder path definition.
        :param dict metadata: Metadata dictionary.
        :returns: tuple of the folder name, which is '' if none of the
            placeholders has a value so a fallback is used, and the list of
            values.
        """
        folder, values = self.parse_custom_mask(part, metadata)
        if values and not any(values):
            folder = ''
        return (folder, values)

    def parse_mask_for_location(self, mask, location_parts, place_name):
        """Takes a mask for a location and interpolates the actual place names.

        Given these parameters here are the outputs.

        mask=%city
        location_parts=[('%city','%city','city')]
        place_name={'city': u'Sunnyvale'}
        output=Sunnyvale

        mask=%city-%state
        location_parts=[('%city-','%city','city'), ('%state','%state','state')]
        place_name={'city': u'Sunnyvale', 'state': u'California'}
        output=Sunnyvale-California

        mask=%country
        location_parts=[('%country','%country','country')]
        place_name={'default': u'Sunnyvale', 'city': u'Sunnyvale'}
        output=Sunnyvale


        :param str mask: The location mask in the form of %city-%state, etc
        :param list location_parts: A list of tuples in the form of
            [('%city-', '%city', 'city'), ('%state', '%state', 'state')]
        :param dict place_name: A dictionary of place keywords and names like
            {'default': u'California', 'state': u'California'}
        :returns: str
        """
        found = False
        folder_name = mask
        for loc_part in location_parts:
            # We assume the search returns a tuple of length 2.
            # If not then it's a bad mask in config.ini.
            # loc_part = '%country-random'
            # component_full = '%country-random'
            # component = '%country'
            # key = 'country
            component_full, component, key = re.search(
                '((%([a-z]+))[^%]*)',
                loc_part
            ).groups()

            if(place_name.get(key)):
                found = True
                replace_target = component
                replace_with = place_name[key]
            else:
                replace_target = component_full
                replace_with = ''

            folder_name = folder_name.replace(
                replace_target,
                replace_with,
            )

        if(not found and folder_name == ''):
            folder_name = (place_name.get('default') or
                           geolocation.__DEFAULT_LOCATION__)

        return folder_name

    def process_checksum(self, _file, allow_duplicate):
        db = Db()
        checksum = db.checksum(_file)

        # If duplicates are not allowed then we check if we've seen this file
        #  before via checksum. We also check that the file exists at the
        #   location we believe it to be.
        # If we find a checksum match but the file doesn't exist where we
        #  believe it to be then we write a debug log and proceed to import.
        checksum_file = db.get_hash(checksum)
        if(allow_duplicate is False and checksum_file is not None):
            if(os.path.isfile(checksum_file)):
                log.info('%s already at %s.' % (
                    _file,
                    checksum_file
                ))
                self.skipped_as_duplicate = True
                return None
            else:
                log.info('%s matched checksum but file not found at %s.' % (  # noqa
                    _file,
                    checksum_file
                ))
        return checksum

    def process_file(self, _file, destination, media, **kwargs):
        self.skipped_as_duplicate = False
        self.imported_sidecars = []
        move = False
        if('move' in kwargs):
            move = kwargs['move']

        allow_duplicate = False
        if('allowDuplicate' in kwargs):
            allow_duplicate = kwargs['allowDuplicate']

        metadata = media.get_metadata()

        if(not media.is_valid()):
            print('%s is not a valid media file. Skipping...' % _file)
            return

        checksum = self.process_checksum(_file, allow_duplicate)
        if(checksum is None):
            log.info('Original checksum returned None for %s. Skipping...' %
                     _file)
            if self.skipped_as_duplicate:
                # The sidecar may contain newer edits so we do not replace
                #  the one in the library but let the user know.
                for sidecar, full_name_style in self.find_sidecars(_file):
                    print('Sidecar %s was not imported since %s was imported before' % (sidecar, _file))  # noqa
            return

        # Run `before()` for every loaded plugin and if any of them raise an exception
        #  then we skip importing the file and log a message.
        plugins_run_before_status = self.plugins.run_all_before(_file, destination)
        if(plugins_run_before_status == False):
            log.warn('At least one plugin pre-run failed for %s' % _file)
            return

        directory_name = self.get_folder_path(metadata)
        dest_directory = os.path.join(destination, directory_name)
        file_name = self.get_file_name(metadata)
        dest_path = os.path.join(dest_directory, file_name)        

        # If source and destination are identical then
        #  we should not write the file. gh-210
        if self.is_same_file(_file, dest_path):
            print('Final source and destination path should not be identical')
            return

        self.create_directory(dest_directory)

        if(move is True):
            # When moving we write the original name to the file itself
            #  since it does not remain at the source.
            if not constants.dry_run:
                media.set_original_name()

            stat = os.stat(_file)
            # Move the processed file into the destination directory
            self._file_operation('move', _file, dest_path)

            if not constants.dry_run:
                os.utime(dest_path, (stat.st_atime, stat.st_mtime))
            else:
                print(f"[DRY-RUN] Would set utime for: {dest_path}")

            self.imported_sidecars = self.process_sidecars(
                _file, dest_path, move=True)
        else:
            # Copy the source as is so it is not modified in any way,
            #  not even its ctime. gh-533
            self._file_operation('copy', _file, dest_path)

            # Write the metadata to the copy and then set the utime on it
            #  based on metadata.
            if not constants.dry_run:
                self.write_metadata_to_copy(media, _file, dest_path)
                self.set_utime_from_metadata(metadata, dest_path)
            else:
                print(f"[DRY-RUN] Would set utime from metadata for: {dest_path}")

            self.imported_sidecars = self.process_sidecars(
                _file, dest_path, move=False)

        db = Db()
        db.add_hash(checksum, dest_path)
        db.update_hash_db()

        # Run `after()` for every loaded plugin and if any of them raise an exception
        #  then we skip importing the file and log a message.
        plugins_run_after_status = self.plugins.run_all_after(_file, destination, dest_path, metadata)
        if(plugins_run_after_status == False):
            log.warn('At least one plugin pre-run failed for %s' % _file)
            return


        return dest_path

    def get_sidecar_extensions(self):
        """Get the extensions of sidecar files which are imported with the
        file they belong to. Set in the [Sidecars] section of config.ini,
        an empty list disables it.

        :returns: set of lowercase extensions without a dot
        """
        config = load_config()
        if 'Sidecars' in config and 'extensions' in config['Sidecars']:
            return {
                extension.strip().lstrip('.').lower()
                for extension in config['Sidecars']['extensions'].split(',')
                if extension.strip()
            }
        return set(self.default_sidecar_extensions)

    def list_directory(self, directory):
        """List the files of a directory, indexed by their lowercase name
        without the extension: {'img_1234': ['IMG_1234.CR3', 'IMG_1234.xmp'],
        'img_1234.cr3': ['IMG_1234.CR3.xmp']}. The index is cached until the
        directory changes since it is needed for each file in it, looking up
        a name must not depend on the number of files in the directory.

        :param str directory: Path of the directory.
        :returns: dict of lists of file names, sorted
        """
        try:
            modified = os.stat(directory).st_mtime_ns
        except OSError:
            return {}
        cached = self.directory_listings.get(directory)
        if cached is None or cached[0] != modified:
            index = {}
            for entry in sorted(os.listdir(directory)):
                base = os.path.splitext(entry)[0].lower()
                index.setdefault(base, []).append(entry)
            cached = (modified, index)
            self.directory_listings[directory] = cached
        return cached[1]

    def get_directory_modified(self, path):
        """Get the modification time of the directory of a file, to pass to
        update_directory_listing() after changing the file.

        :param str path: Path of the file.
        :returns: int in nanoseconds or None
        """
        try:
            return os.stat(os.path.dirname(path)).st_mtime_ns
        except OSError:
            return None

    def update_directory_listing(self, path, exists, modified_before):
        """Update the cached listing of the directory of a file which was
        added or removed by us, so it does not have to be read again for the
        next file, i.e. when each file is moved to the trash after its
        import.

        The listing is only updated if it was current right before our
        change. Otherwise another program changed the directory as well, i.e.
        a sidecar was added while importing, and the listing is read again
        the next time.

        :param str path: Path of the file.
        :param bool exists: Whether the file was added or removed.
        :param int modified_before: Modification time of the directory
            before the change, from get_directory_modified().
        """
        directory, name = os.path.split(path)
        cached = self.directory_listings.get(directory)
        if cached is None:
            return
        try:
            modified = os.stat(directory).st_mtime_ns
        except OSError:
            del self.directory_listings[directory]
            return
        if cached[0] != modified_before:
            del self.directory_listings[directory]
            return
        index = cached[1]
        base = os.path.splitext(name)[0].lower()
        entries = index.get(base, [])
        if exists and name not in entries:
            index[base] = sorted(entries + [name])
        elif not exists and name in entries:
            entries.remove(name)
            if not entries:
                del index[base]
        self.directory_listings[directory] = (modified, index)

    def find_sidecars(self, file_path):
        """Find the sidecar files of a file in the same directory with the
        same name, ignoring case: IMG_1234.xmp or IMG_1234.CR3.xmp for
        IMG_1234.CR3.

        :param str file_path: Path of the file.
        :returns: list of tuples of the path of the sidecar file and whether
            its name includes the extension of the file (IMG_1234.CR3.xmp)
        """
        extensions = self.get_sidecar_extensions()
        if not extensions:
            return []

        directory, name = os.path.split(file_path)
        index = self.list_directory(directory)
        stem = os.path.splitext(name)[0].lower()
        candidates = [(entry, True) for entry in index.get(name.lower(), [])]
        candidates += [(entry, False) for entry in index.get(stem, [])]
        sidecars = []
        for entry, full_name_style in sorted(candidates):
            if os.path.splitext(entry)[1][1:].lower() not in extensions:
                continue
            path = os.path.join(directory, entry)
            if os.path.isfile(path):
                sidecars.append((path, full_name_style))
        return sidecars

    def is_sidecar_shared(self, sidecar, file_path):
        """Check if another supported file than file_path uses the sidecar,
        i.e. IMG_1234.xmp for IMG_1234.CR3 and IMG_1234.JPG.

        :param str sidecar: Path of the sidecar file.
        :param str file_path: Path of the file it was imported with.
        :returns: bool
        """
        supported_extensions = set()
        for cls in get_all_subclasses(Base):
            supported_extensions.update(cls.extensions)

        # IMG_1234 for IMG_1234.xmp or IMG_1234.CR3 for IMG_1234.CR3.xmp
        sidecar_base = os.path.splitext(os.path.basename(sidecar))[0].lower()
        directory = os.path.dirname(sidecar)
        index = self.list_directory(directory)
        # IMG_1234.JPG for IMG_1234.xmp, IMG_1234.CR3 for IMG_1234.CR3.xmp
        candidates = index.get(sidecar_base, []) + [
            entry
            for entry in index.get(os.path.splitext(sidecar_base)[0], [])
            if entry.lower() == sidecar_base
        ]
        for entry in candidates:
            extension = os.path.splitext(entry)[1][1:].lower()
            if extension not in supported_extensions:
                continue
            path = os.path.join(directory, entry)
            if os.path.isfile(path) and not self.is_same_file(path, file_path):
                return True
        return False

    def get_sidecar_name(self, file_name, sidecar, full_name_style):
        """Name of a sidecar file for a file named file_name in the library.
        Its extension has the case of the file's extension.

        :param str file_name: Name of the file in the library.
        :param str sidecar: Path of the sidecar file.
        :param bool full_name_style: The name includes the extension of the
            file (IMG_1234.CR3.xmp).
        :returns: str
        """
        extension = os.path.splitext(sidecar)[1][1:]
        if os.path.splitext(file_name)[1].isupper():
            extension = extension.upper()
        else:
            extension = extension.lower()
        base = file_name if full_name_style else os.path.splitext(file_name)[0]
        return '{}.{}'.format(base, extension)

    def process_sidecars(self, _file, dest_path, move):
        """Copy or move the sidecar files of _file next to dest_path so
        edits (i.e. in .xmp or .aae files) stay with the file. gh-341

        A sidecar which another file still uses (i.e. by IMG_1234.CR3 and
        IMG_1234.JPG) is copied instead of moved. A different file which
        exists at the destination is not replaced.

        :param str _file: Path of the file which was imported.
        :param str dest_path: Path of the file in the library.
        :param bool move: Move the sidecar files instead of copying them.
        :returns: list of paths of the sidecar files which were imported
        """
        imported = []
        for sidecar, full_name_style in self.find_sidecars(_file):
            dest_sidecar = os.path.join(
                os.path.dirname(dest_path),
                self.get_sidecar_name(
                    os.path.basename(dest_path), sidecar, full_name_style)
            )
            if self.is_same_file(sidecar, dest_sidecar):
                continue

            keep_source = move and self.is_sidecar_shared(sidecar, _file)
            if os.path.exists(dest_sidecar):
                if not filecmp.cmp(dest_sidecar, sidecar, shallow=False):
                    print('Sidecar %s was not imported since a different file exists at %s' % (sidecar, dest_sidecar))  # noqa
                    continue
                # The same sidecar was imported with another file already
                if move and not keep_source:
                    self._file_operation('remove', sidecar)
                imported.append(sidecar)
                continue

            stat = os.stat(sidecar)
            operation = 'move' if move and not keep_source else 'copy'
            self._file_operation(operation, sidecar, dest_sidecar)
            if not constants.dry_run:
                os.utime(dest_sidecar, (stat.st_atime, stat.st_mtime))
            imported.append(sidecar)
        return imported

    def write_metadata_to_copy(self, media, source, dest_path):
        """Write changes to the metadata of the source file which were
        deferred (e.g. import with --location) and its name to its copy.

        If the file already had an original name it is kept.

        :param media: The media object of the source file.
        :param str source: Path of the source file.
        :param str dest_path: Path of the copy.
        """
        # The copy has the permissions of the source which may be read-only.
        dest_mode = os.stat(dest_path).st_mode
        if not dest_mode & S_IWUSR:
            os.chmod(dest_path, dest_mode | S_IWUSR)

        if not media.write_deferred(dest_path):
            log.error('Could not write all metadata to %s' % dest_path)

        media.__class__(dest_path).set_original_name(os.path.basename(source))

    def set_utime_from_metadata(self, metadata, file_path):
        """ Set the modification time on the file based on the file name.
        """

        # Initialize date taken to what's returned from the metadata function.
        # If the folder and file name follow a time format of
        #   YYYY-MM-DD_HH-MM-SS-IMG_0001.JPG then we override the date_taken
        date_taken = metadata['date_taken']
        base_name = metadata['base_name']
        year_month_day_match = re.search(
            r'^(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})',
            base_name
        )
        if(year_month_day_match is not None):
            (year, month, day, hour, minute, second) = year_month_day_match.groups()  # noqa
            date_taken = time.strptime(
                '{}-{}-{} {}:{}:{}'.format(year, month, day, hour, minute, second),  # noqa
                '%Y-%m-%d %H:%M:%S'
            )

            # The date in the file name was generated from date_taken
            #  which is in UTC (see get_file_name) so we use timegm here too.
            if not constants.dry_run:
                os.utime(file_path, (time.time(), calendar.timegm(date_taken)))
            else:
                print(f"[DRY-RUN] Would set utime from date pattern for: {file_path}")
        else:
            # date_taken is a UTC struct_time (see get_date_taken) so we
            #  use timegm, the inverse of gmtime, rather than mktime which
            #  would treat it as local time.
            # This also avoids mktime failing for dates before 1970 on Windows.
            date_taken_in_seconds = calendar.timegm(date_taken)
            if not constants.dry_run:
                os.utime(file_path, (time.time(), (date_taken_in_seconds)))
            else:
                print(f"[DRY-RUN] Would set utime from metadata for: {file_path}")

    def should_exclude(self, path, regex_list=set(), needs_compiled=False):
        if(len(regex_list) == 0):
            return False

        if(needs_compiled):
            compiled_list = []
            for regex in regex_list:
                compiled_list.append(re.compile(regex))
            regex_list = compiled_list

        return any(regex.search(path) for regex in regex_list)
