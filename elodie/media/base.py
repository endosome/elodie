"""
The base module provides a base :class:`Base` class for all objects that
are tracked by Elodie. The Base class provides some base functionality used
by all the media types, but isn't itself used to represent anything. Its
sub-classes (:class:`~elodie.media.audio.Audio`,
:class:`~elodie.media.photo.Photo`, :class:`~elodie.media.video.Video`, and
:class:`~elodie.media.text.Text`)
are used to represent the actual files.

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""

import mimetypes
import os

from elodie import constants

try:        # Py3k compatibility
    basestring
except NameError:
    basestring = (bytes, str)


class Base(object):

    """The base class for all media objects.

    :param str source: The fully qualified path to the video file.
    """

    __name__ = 'Base'

    extensions = ()

    def __init__(self, source=None):
        self.source = source
        self.deferred_writes = None
        self.reset_cache()

    def format_metadata(self, **kwargs):
        """Method to consistently return a populated metadata dictionary.

        :returns: dict
        """

    def get_album(self):
        """Base method for getting an album

        :returns: None
        """
        return None

    def get_rating(self):
        """Base method for getting a rating

        :returns: None
        """
        return None

    def get_file_path(self):
        """Get the full path to the video.

        :returns: string
        """
        return self.source

    def get_coordinate(self, type):
        return None

    def get_extension(self):
        """Get the file extension as a lowercased string.

        :returns: string or None for a non-video
        """
        if(not self.is_valid()):
            return None

        source = self.source
        return os.path.splitext(source)[1][1:].lower()

    def get_camera_make(self):
        return None

    def get_camera_model(self):
        return None

    def get_metadata(self, update_cache=False):
        """Get a dictionary of metadata for any file.

        All keys will be present and have a value of None if not obtained.

        :returns: dict or None for non-text files
        """
        if(not self.is_valid()):
            return None

        if(isinstance(self.metadata, dict) and update_cache is False):
            return self.metadata

        source = self.source

        self.metadata = {
            'date_taken': self.get_date_taken(),
            'camera_make': self.get_camera_make(),
            'camera_model': self.get_camera_model(),
            'latitude': self.get_coordinate('latitude'),
            'longitude': self.get_coordinate('longitude'),
            'album': self.get_album(),
            'rating': self.get_rating(),
            'title': self.get_title(),
            'description': self.get_description(),
            'mime_type': self.get_mimetype(),
            'original_name': self.get_original_name(),
            'base_name': os.path.splitext(os.path.basename(source))[0],
            'extension': self.get_extension(),
            'directory_path': os.path.dirname(source)
        }

        return self.metadata

    def get_mimetype(self):
        """Get the mimetype of the file.

        :returns: str or None for unsupported files.
        """
        if(not self.is_valid()):
            return None

        source = self.source
        mimetype = mimetypes.guess_type(source)
        if(mimetype is None):
            return None

        return mimetype[0]

    def get_original_name(self):
        """Get the original name of the file from before it was imported.
        Does not include the extension.
        Overridden by Media class for files with EXIF.

        :returns: str or None for unsupported files.
        """
        return None

    def get_title(self):
        """Base method for getting the title of a file

        :returns: None
        """
        return None

    def get_description(self):
        """Base method for getting the description of a file

        :returns: None
        """
        return None

    def is_valid(self):
        """Check the file extension against valid file extensions.

        The list of valid file extensions come from self.extensions.

        :returns: bool
        """
        source = self.source
        return os.path.splitext(source)[1][1:].lower() in self.extensions

    def reset_cache(self):
        """Resets any internal cache
        """
        self.metadata = None

    def set_album(self, name):
        """Base method for setting the album of a file

        :returns: None
        """
        return None

    def set_album_from_folder(self):
        """Set the album attribute based on the leaf folder name

        :returns: bool
        """
        metadata = self.get_metadata()

        # If this file has an album already set we do not overwrite EXIF
        if(not isinstance(metadata, dict) or metadata['album'] is not None):
            return False

        folder = os.path.basename(metadata['directory_path'])
        # If folder is empty we skip
        if(len(folder) == 0):
            return False

        self.set_album(folder)
        return True

    def set_metadata_basename(self, new_basename):
        """Update the basename attribute in the metadata dict for this instance.

        This is used for when we update the EXIF title of a media file. Since
        that determines the name of a file if we update the title of a file
        more than once it appends to the file name.

        i.e. 2015-12-31_00-00-00-my-first-title-my-second-title.jpg

        :param str new_basename: New basename of file (with the old title
            removed).
        """
        self.get_metadata()
        self.metadata['base_name'] = new_basename

    def set_metadata(self, **kwargs):
        """Method to manually update attributes in metadata.

        :params dict kwargs: Named parameters to update.
        """
        metadata = self.get_metadata()
        for key in kwargs:
            if(key in metadata):
                self.metadata[key] = kwargs[key]

    def defer_writes(self):
        """Record changes to the metadata instead of writing them to the file.

        They can be written to another file, e.g. a copy of this one, with
        write_deferred().
        """
        self.deferred_writes = []

    def write_deferred(self, file_path):
        """Write the changes recorded since defer_writes() to file_path.

        :param str file_path: Path of the file to write the changes to.
        :returns: bool, True if all changes were written.
        """
        media = self.__class__(file_path)
        status = True
        for setter, args in self.deferred_writes or []:
            status = getattr(media, setter)(*args) is True and status
        return status

    def skip_write(self, setter, args, **kwargs):
        """Check if a setter should skip writing to the file. This is the case
        in dry-run mode or after defer_writes().

        The metadata of this instance is updated instead so the destination
        of the file is determined as if it had been written.

        :param str setter: Name of the setter which is called.
        :param tuple args: Arguments the setter was called with.
        :params dict kwargs: Named parameters of the metadata to update.
        :returns: bool, True if nothing should be written.
        """
        if self.deferred_writes is not None:
            self.deferred_writes.append((setter, args))
        elif not constants.dry_run:
            return False

        self.set_metadata(**kwargs)
        return True

    def set_original_name(self):
        """Stores the original file name into EXIF/metadata.
        :returns: bool
        """
        return False

    @classmethod
    def get_class_by_file(cls, _file, classes):
        """Static method to get a media object by file.
        """
        if not isinstance(_file, basestring) or not os.path.isfile(_file):
            return None

        extension = os.path.splitext(_file)[1][1:].lower()

        if len(extension) > 0:
            for i in classes:
                if(extension in i.extensions):
                    return i(_file)

        return None

    @classmethod
    def get_valid_extensions(cls):
        """Static method to access static extensions variable.

        :returns: tuple(str)
        """
        return cls.extensions


def get_all_subclasses(cls=None):
    """Module method to get all subclasses of Base.
    """
    subclasses = set()

    this_class = Base
    if cls is not None:
        this_class = cls

    subclasses.add(this_class)

    this_class_subclasses = this_class.__subclasses__()
    for child_class in this_class_subclasses:
        subclasses.update(get_all_subclasses(child_class))

    return subclasses
