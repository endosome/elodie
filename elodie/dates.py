"""
Dates of media files for their names and folders.

EXIF dates are the time of the camera's clock without a time zone. They are
used as they are, like Immich and other photo applications show them, so a
file gets the same name on every computer. Dates stored in UTC, i.e. the
QuickTime dates of videos, are converted to the time zone of the place where
the video was recorded, found from its GPS position, or else to the one of the
computer.

Dates are time.struct_time. Their tm_isdst is 0 like the ones of time.gmtime,
it is not used: to_timestamp() lets mktime find out whether daylight saving
time applies.
"""

import calendar
import time
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# Finds the time zone of a GPS position, optional (see requirements.txt)
try:
    import tzfpy
except ImportError:
    tzfpy = None


def _struct(value):
    return time.struct_time(tuple(value)[:8] + (0,))


def wall_clock(value):
    """The date of a datetime as it is, i.e. of a camera's clock.

    :param datetime value:
    :returns: time.struct_time
    """
    return _struct(value.timetuple())


def local_time(seconds):
    """The date of a timestamp in the time zone of the computer, i.e. for the
    modification time of a file.

    :param float seconds: Seconds since the epoch.
    :returns: time.struct_time
    """
    try:
        return _struct(time.localtime(seconds))
    except (OSError, OverflowError, ValueError):
        # Windows cannot handle timestamps before 1970, UTC is used then
        return _struct((datetime(1970, 1, 1) +
                        timedelta(seconds=seconds)).timetuple())


def from_utc_timestamp(seconds):
    """The date of a timestamp which stores a date as if it was UTC, see
    to_utc_timestamp(). It is the same on every computer.

    :param float seconds:
    :returns: time.struct_time
    """
    return _struct((datetime(1970, 1, 1) +
                    timedelta(seconds=seconds)).timetuple())


def to_utc_timestamp(date):
    """Store a date as a timestamp as if it was UTC, i.e. in the metadata
    of text files. Unlike the local time it is the same on every computer.

    :param time.struct_time date:
    :returns: int
    """
    return calendar.timegm(date)


def to_timestamp(date):
    """Seconds since the epoch of a date in the time zone of the computer,
    the inverse of local_time().

    :param time.struct_time date:
    :returns: float
    """
    try:
        # -1 lets mktime find out whether daylight saving time applies
        return time.mktime(tuple(date)[:8] + (-1,))
    except (OverflowError, ValueError):
        # Windows cannot handle dates before 1970, UTC is used then
        return float(calendar.timegm(date))


def time_zone_at(latitude, longitude):
    """The time zone of a GPS position.

    :returns: zoneinfo.ZoneInfo or None if it cannot be found
    """
    if (tzfpy is None or ZoneInfo is None or
            latitude is None or longitude is None):
        return None
    try:
        name = tzfpy.get_tz(float(longitude), float(latitude))
        return ZoneInfo(name) if name else None
    except Exception:
        return None


def localize(value, latitude=None, longitude=None):
    """Add the time zone to a local date, the one of the GPS position where
    it was taken or else the one of the computer.

    :param datetime value: Local date, without a time zone.
    :returns: datetime with a time zone
    """
    zone = time_zone_at(latitude, longitude)
    if zone is not None:
        return value.replace(tzinfo=zone)
    # The offset of the computer's time zone at that date
    offset = calendar.timegm(value.timetuple()) - to_timestamp(
        wall_clock(value))
    return value.replace(tzinfo=timezone(timedelta(seconds=round(offset))))


def utc_to_local(value, latitude=None, longitude=None):
    """The local date of a UTC date, in the time zone of the GPS position
    where it was recorded or else in the one of the computer.

    :param datetime value: UTC date, without a time zone.
    :returns: time.struct_time
    """
    zone = time_zone_at(latitude, longitude)
    if zone is not None:
        local = value.replace(tzinfo=timezone.utc).astimezone(zone)
        return wall_clock(local.replace(tzinfo=None))
    return local_time(calendar.timegm(value.timetuple()))
