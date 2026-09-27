"""
Methods for interacting with information Elodie caches about stored media.
"""

import hashlib
import json
import os
import sys

from math import radians, cos, sqrt
from shutil import copyfile
from time import strftime

from elodie import constants
from elodie import log


class Db(object):

    """A class for interacting with the JSON files created by Elodie."""

    def __init__(self):
        # verify that the application directory (~/.elodie) exists,
        #   else create it
        if not os.path.exists(constants.application_directory()):
            os.makedirs(constants.application_directory())

        # If the hash db doesn't exist we create it.
        # Otherwise we only open for reading
        if not os.path.isfile(constants.hash_db()):
            with open(constants.hash_db(), 'a'):
                os.utime(constants.hash_db(), None)

        self.hash_db = self._load(constants.hash_db(), {})

        # If the location db doesn't exist we create it.
        # Otherwise we only open for reading
        if not os.path.isfile(constants.location_db()):
            with open(constants.location_db(), 'a'):
                os.utime(constants.location_db(), None)

        self.location_db = self._load(constants.location_db(), [])

    @staticmethod
    def _load(path, empty):
        """Load a database. One which cannot be read, i.e. after a crash
        while it was written by an older version, is moved aside so it is
        not overwritten and can be recovered.
        """
        with open(path, 'r') as f:
            content = f.read()
        if not content.strip():
            # Created and not written yet
            return empty
        try:
            return json.loads(content)
        except ValueError:
            corrupt_path = '%s-corrupt-%s' % (
                path, strftime('%Y-%m-%d_%H-%M-%S'))
            os.replace(path, corrupt_path)
            log.error('Could not read %s, it was moved to %s and a new one '
                      'is started' % (path, corrupt_path))
            return empty

    @staticmethod
    def _write(path, data):
        """Write a database to another file which then replaces it, so a
        write which is interrupted (i.e. Ctrl-C) does not corrupt it.
        """
        temporary_path = path + '.tmp'
        try:
            with open(temporary_path, 'w') as f:
                json.dump(data, f)
            os.replace(temporary_path, path)
        except BaseException:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise

    def add_hash(self, key, value, write=False):
        """Add a hash to the hash db.

        :param str key:
        :param str value:
        :param bool write: If true, write the hash db to disk.
        """
        self.hash_db[key] = value
        if(write is True):
            self.update_hash_db()

    def move_hashes(self, old_path, new_path):
        """Change the path of all hashes of a file which was moved.

        :param str old_path:
        :param str new_path:
        """
        old_path = os.path.abspath(old_path)
        for key, value in self.hash_db.items():
            if os.path.abspath(value) == old_path:
                self.hash_db[key] = new_path

    # Location database
    # Currently quite simple just a list of long/lat pairs with a name
    # If it gets many entries a lookup might take too long and a better
    # structure might be needed. Some speed up ideas:
    # - Sort it and inter-half method can be used
    # - Use integer part of long or lat as key to get a lower search list
    # - Cache a small number of lookups, photos are likely to be taken in
    #   clusters around a spot during import.
    def add_location(self, latitude, longitude, place, write=False):
        """Add a location to the database.

        :param float latitude: Latitude of the location.
        :param float longitude: Longitude of the location.
        :param str place: Name for the location.
        :param bool write: If true, write the location db to disk.
        """
        data = {}
        data['lat'] = latitude
        data['long'] = longitude
        data['name'] = place
        self.location_db.append(data)
        if(write is True):
            self.update_location_db()

    def backup_hash_db(self):
        """Backs up the hash db."""
        if os.path.isfile(constants.hash_db()):
            mask = strftime('%Y-%m-%d_%H-%M-%S')
            backup_file_name = '%s-%s' % (constants.hash_db(), mask)
            copyfile(constants.hash_db(), backup_file_name)
            return backup_file_name

    def check_hash(self, key):
        """Check whether a hash is present for the given key.

        :param str key:
        :returns: bool
        """
        return key in self.hash_db

    def checksum(self, file_path, blocksize=65536):
        """Create a hash value for the given file.

        See http://stackoverflow.com/a/3431835/1318758.

        :param str file_path: Path to the file to create a hash for.
        :param int blocksize: Read blocks of this size from the file when
            creating the hash.
        :returns: str
        """
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            buf = f.read(blocksize)

            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(blocksize)
            return hasher.hexdigest()

    def get_hash(self, key):
        """Get the hash value for a given key.

        :param str key:
        :returns: str or None
        """
        if(self.check_hash(key) is True):
            return self.hash_db[key]
        return None

    def get_location_name(self, latitude, longitude, threshold_m):
        """Find a name for a location in the database.

        :param float latitude: Latitude of the location.
        :param float longitude: Longitude of the location.
        :param int threshold_m: Location in the database must be this close to
            the given latitude and longitude.
        :returns: str, or None if a matching location couldn't be found.
        """
        # The closest location within the threshold
        closest_d = sys.maxsize
        name = None
        for data in self.location_db:
            # As threshold is quite small use simple math
            # From http://stackoverflow.com/questions/15736995/how-can-i-quickly-estimate-the-distance-between-two-latitude-longitude-points  # noqa
            # convert decimal degrees to radians

            lon1, lat1, lon2, lat2 = list(map(
                radians,
                [longitude, latitude, data['long'], data['lat']]
            ))

            r = 6371000  # radius of the earth in m
            x = (lon2 - lon1) * cos(0.5 * (lat2 + lat1))
            y = lat2 - lat1
            d = r * sqrt(x * x + y * y)
            if d <= threshold_m and d < closest_d:
                name = data['name']
                closest_d = d

        return name

    def get_location_coordinates(self, name):
        """Get the latitude and longitude for a location.

        :param str name: Name of the location.
        :returns: tuple(float), or None if the location wasn't in the database.
        """
        for data in self.location_db:
            if data['name'] == name:
                return (data['lat'], data['long'])

        return None

    def all(self):
        """Generator to get all entries from self.hash_db

        :returns tuple(string)
        """
        for checksum, path in self.hash_db.items():
            yield (checksum, path)

    def reset_hash_db(self):
        self.hash_db = {}

    def update_hash_db(self):
        """Write the hash db to disk."""
        if constants.dry_run:
            print(f"[DRY-RUN] Would update hash database with {len(self.hash_db)} entries")
            return
        self._write(constants.hash_db(), self.hash_db)

    def update_location_db(self):
        """Write the location db to disk."""
        if constants.dry_run:
            print(f"[DRY-RUN] Would update location database with {len(self.location_db)} entries")
            return
        self._write(constants.location_db(), self.location_db)
