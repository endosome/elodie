"""
The video module contains the :class:`Video` class, which represents video
objects (AVI, MOV, etc.).

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""

# load modules
from datetime import datetime, timezone

import os
import re

from elodie import dates
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

    #: Dates which are in UTC by the QuickTime specification. Phones store
    #:  UTC there, some cameras local time, like ExifTool and Immich they
    #:  are treated as UTC.
    utc_date_keys = ('QuickTime:CreateDate', 'QuickTime:MediaCreateDate')

    def get_date_taken(self):
        """Get the date which the video was taken.

        The date comes from the first key of exif_map['date_taken'] with a
        valid date, which are ordered by preference. Without one it is the
        min() of mtime and ctime in the time zone of the computer.

        A date with a time zone, i.e. QuickTime:CreationDate of iPhones, is
        the local time where the video was taken and is used as it is, like
        the dates of photos. A date in UTC is converted to the time zone
        where it was taken, found from its GPS position, or else to the one
        of the computer, see elodie.dates. Using the earliest of all dates
        gave videos a different date than the photos taken with them. See
        gh-378 and gh-474.

        :returns: time object or None for non-photo files or 0 timestamp
        """
        if(not self.is_valid()):
            return None

        source = self.source
        seconds_since_epoch = min(os.path.getmtime(source), os.path.getctime(source))  # noqa

        exif = self.get_exiftool_attributes() or {}
        for date_key in self.exif_map['date_taken']:
            if date_key not in exif:
                continue
            # Example date strings we want to parse
            # 2015:01:19 12:45:11-08:00
            # 2013:09:30 07:06:05
            # 2019:07:04 12:00:00Z
            date_string = self.normalize_date_string(str(exif[date_key]))
            match = re.match(
                r'(\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2})(?:\.\d+)?'
                r'\s*(Z|[-+]\d{2}:?\d{2})?',
                date_string.strip())
            if match is None:
                continue
            try:
                date = datetime.strptime(match.group(1), '%Y:%m:%d %H:%M:%S')
            except ValueError:
                # i.e. 0000:00:00 00:00:00 when the date is not set
                continue

            offset = match.group(2)
            is_utc = (offset in ('Z', '+00:00', '-00:00', '+0000') or
                      (offset is None and date_key in self.utc_date_keys))
            if not is_utc:
                return dates.wall_clock(date)
            return dates.utc_to_local(
                date,
                self.get_coordinate('latitude'),
                self.get_coordinate('longitude'))

        if(seconds_since_epoch == 0):
            return None

        return dates.local_time(seconds_since_epoch)

    def get_date_taken_tags(self, time):
        """Get the tags to write for a date taken, like phones write them:
        QuickTime:CreationDate is the local time with its time zone, the
        dates which are in UTC by the specification are in UTC. The time zone
        is the one of the GPS position or else the one of the computer.

        :param datetime time: The local date without a time zone.
        :returns: dict
        """
        local = dates.localize(time, self.get_coordinate('latitude'),
                               self.get_coordinate('longitude'))
        offset = local.strftime('%z')
        offset = '{}:{}'.format(offset[:3], offset[3:])
        utc = local.astimezone(timezone.utc)

        tags = {}
        for key in self.exif_map['date_taken']:
            if key in self.utc_date_keys:
                tags[key] = utc.strftime('%Y:%m:%d %H:%M:%S')
            elif key.startswith('QuickTime:CreationDate'):
                tags[key] = time.strftime('%Y:%m:%d %H:%M:%S') + offset
            else:
                tags[key] = time.strftime('%Y:%m:%d %H:%M:%S')
        return tags

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
