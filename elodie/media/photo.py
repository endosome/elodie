"""
The photo module contains the :class:`Photo` class, which is used to track
image objects (JPG, DNG, etc.).

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""

import os
import re
from datetime import datetime
from re import compile

from elodie import dates
from elodie import log
from .media import Media


class Photo(Media):

    """A photo object.

    :param str source: The fully qualified path to the photo file
    """

    __name__ = 'Photo'

    #: Valid extensions for photo files.
    extensions = ('arw', 'avif', 'cr2', 'cr3', 'dng', 'erf', 'gif', 'heic',
                  'heif', 'hif', 'iiq', 'jpeg', 'jpg', 'mrw', 'nef', 'nrw',
                  'orf', 'pef', 'png', 'raf', 'raw', 'rw2', 'srw', 'tif',
                  'tiff', 'webp', 'x3f')

    def __init__(self, source=None):
        super(Photo, self).__init__(source)

        # We only want to parse EXIF once so we store it here
        self.exif = None

    def get_date_taken(self):
        """Get the date which the photo was taken.

        The date of the camera as it is stored in EXIF, which has no time
        zone, see elodie.dates. Without one it is the min() of mtime and
        ctime in the time zone of the computer.

        :returns: time object or None for non-photo files or 0 timestamp
        """
        if(not self.is_valid()):
            return None

        source = self.source
        seconds_since_epoch = min(os.path.getmtime(source), os.path.getctime(source))  # noqa

        exif = self.get_exiftool_attributes() or {}

        # EXIF DateTimeOriginal and EXIF DateTime are both stored
        #   in %Y:%m:%d %H:%M:%S format
        for key in self.exif_map['date_taken']:
            try:
                if(key in exif):
                    if(re.match(r'\d{4}(-|:)\d{2}(-|:)\d{2}', exif[key]) is not None):  # noqa
                        dt, tm = exif[key].split(' ')
                        dt_list = compile(r'-|:').split(dt)
                        dt_list = dt_list + compile(r'-|:').split(tm)
                        dt_list = map(int, dt_list)
                        return dates.wall_clock(datetime(*dt_list))
            except Exception as e:
                # i.e. 0000:00:00 00:00:00, the next key is used
                log.info('Invalid date in %s: %s' % (key, e))

        if(seconds_since_epoch == 0):
            return None

        return dates.local_time(seconds_since_epoch)

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
        if not source:
            return False

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
