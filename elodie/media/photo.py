"""
The photo module contains the :class:`Photo` class, which is used to track
image objects (JPG, DNG, etc.).

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""
from __future__ import print_function
from __future__ import absolute_import

import os
import re
import time
from datetime import datetime
from re import compile

from elodie import log
from elodie.compatability import _gmtime
from .media import Media


class Photo(Media):

    """A photo object.

    :param str source: The fully qualified path to the photo file
    """

    __name__ = 'Photo'

    #: Valid extensions for photo files.
    extensions = ('arw', 'cr2', 'dng', 'gif', 'heic', 'jpeg', 'jpg', 'nef',
                  'png', 'rw2', 'webp')

    def __init__(self, source=None):
        super(Photo, self).__init__(source)

        # We only want to parse EXIF once so we store it here
        self.exif = None

    def get_date_taken(self):
        """Get the date which the photo was taken.

        The date value returned is defined by the min() of mtime and ctime.

        :returns: time object or None for non-photo files or 0 timestamp
        """
        if(not self.is_valid()):
            return None

        source = self.source
        seconds_since_epoch = min(os.path.getmtime(source), os.path.getctime(source))  # noqa

        exif = self.get_exiftool_attributes()
        if not exif:
            return seconds_since_epoch

        # We need to parse a string from EXIF into a timestamp.
        # EXIF DateTimeOriginal and EXIF DateTime are both stored
        #   in %Y:%m:%d %H:%M:%S format
        # we split on a space and then r':|-' -> convert to int -> .timetuple()
        #   the conversion in the local timezone
        # EXIF DateTime is already stored as a timestamp
        # Sourced from https://github.com/photo/frontend/blob/master/src/libraries/models/Photo.php#L500  # noqa
        for key in self.exif_map['date_taken']:
            try:
                if(key in exif):
                    if(re.match(r'\d{4}(-|:)\d{2}(-|:)\d{2}', exif[key]) is not None):  # noqa
                        dt, tm = exif[key].split(' ')
                        dt_list = compile(r'-|:').split(dt)
                        dt_list = dt_list + compile(r'-|:').split(tm)
                        dt_list = map(int, dt_list)
                        time_tuple = datetime(*dt_list).timetuple()
                        seconds_since_epoch = time.mktime(time_tuple)
                        break
            except BaseException as e:
                log.error(e)
                pass

        if(seconds_since_epoch == 0):
            return None

        return _gmtime(seconds_since_epoch)

    def is_valid(self):
        """Check the file extension against valid file extensions.

        The list of valid file extensions come from self.extensions. This
        also checks whether the file is an image (gh-4) using exiftool, which
        knows far more formats than image libraries, i.e. the raw files of
        new cameras (gh-507). exiftool reads each file once, see
        get_exiftool_attributes().

        :returns: bool
        """
        source = self.source

        extension = os.path.splitext(source)[1][1:].lower()
        if extension not in self.extensions:
            return False

        try:
            exif = self.get_exiftool_attributes()
        except ValueError:
            # exiftool is not running
            return False

        if not exif:
            return False

        return str(exif.get('File:MIMEType', '')).startswith('image/')
