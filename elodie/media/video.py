"""
The video module contains the :class:`Video` class, which represents video
objects (AVI, MOV, etc.).

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""

# load modules
from datetime import datetime

import os
import re
import time

from elodie.compatability import _gmtime
from .media import Media


class Video(Media):

    """A video object.

    :param str source: The fully qualified path to the video file.
    """

    __name__ = 'Video'

    #: Valid extensions for video files.
    extensions = ('avi', 'm4v', 'mov', 'mp4', 'mpg', 'mpeg', '3gp', 'mts',
                  'mkv', 'webm')

    def __init__(self, source=None):
        super(Video, self).__init__(source)
        self.exif_map['date_taken'] = [
            'QuickTime:CreationDate',
            'QuickTime:CreateDate',
            'QuickTime:CreationDate-und-US',
            'QuickTime:MediaCreateDate',
            'H264:DateTimeOriginal',
            # mkv and webm
            'Matroska:DateTimeOriginal'
        ]
        self.title_key = 'XMP:DisplayName'
        self.latitude_keys = [
            'XMP:GPSLatitude',
            # 'QuickTime:GPSLatitude',
            'Composite:GPSLatitude'
        ]
        self.longitude_keys = [
            'XMP:GPSLongitude',
            # 'QuickTime:GPSLongitude',
            'Composite:GPSLongitude'
        ]
        self.latitude_ref_key = 'EXIF:GPSLatitudeRef'
        self.longitude_ref_key = 'EXIF:GPSLongitudeRef'
        self.set_gps_ref = False

    def get_date_taken(self):
        """Get the date which the video was taken.

        The date comes from the first key of exif_map['date_taken'] with a
        valid date, which are ordered by preference. Without one it is the
        min() of mtime and ctime.

        QuickTime:CreationDate (i.e. from iPhones) is the local time where
        the video was taken, like the date of photos. QuickTime:CreateDate is
        often in UTC. Using the earliest of all dates picked it east of UTC
        and gave videos a different date than the photos taken with them.
        See gh-378 and gh-474.

        :returns: time object or None for non-photo files or 0 timestamp
        """
        if(not self.is_valid()):
            return None

        source = self.source
        seconds_since_epoch = min(os.path.getmtime(source), os.path.getctime(source))  # noqa

        exif = self.get_exiftool_attributes()
        for date_key in self.exif_map['date_taken']:
            if date_key in exif:
                # Example date strings we want to parse
                # 2015:01:19 12:45:11-08:00
                # 2013:09:30 07:06:05
                # The time zone is ignored, the local time is used like
                #  for photos.
                date_string = self.normalize_date_string(str(exif[date_key]))
                date = re.search('([0-9: ]+)([-+][0-9:]+)?', date_string)
                if(date is not None):
                    try:
                        seconds_since_epoch = time.mktime(
                            datetime.strptime(
                                date.group(1).strip(),
                                '%Y:%m:%d %H:%M:%S'
                            ).timetuple()
                        )
                        break
                    except (ValueError, OverflowError):
                        # i.e. 0000:00:00 00:00:00 when the date is not set
                        pass

        if(seconds_since_epoch == 0):
            return None

        return _gmtime(seconds_since_epoch)

    def normalize_date_string(self, value):
        """Convert dates like 2019-07-04, 2019:07:04 or 2019-07-04T12:00:00,
        which audio files use, to 2019:07:04 00:00:00. Other values (i.e.
        only a year) are returned unchanged.

        :param str value: Date from the metadata.
        :returns: str
        """
        match = re.match(
            r'^(\d{4})[-:](\d{2})[-:](\d{2})'
            r'(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?(.*)$',
            value.strip()
        )
        if match is None:
            return value

        year, month, day, hour, minute, second, rest = match.groups()
        return '{}:{}:{} {}:{}:{}{}'.format(
            year, month, day,
            hour or '00', minute or '00', second or '00',
            rest
        )
