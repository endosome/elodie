"""
Methods for interacting with information Elodie caches about stored media.
"""

import atexit
import contextlib
import hashlib
import json
import os
import stat
import sys
import tempfile
import time

from math import radians, cos, sqrt
from shutil import copyfile
from time import strftime

from elodie import constants
from elodie import log


#: The shared Db is written to disk after this many changes or seconds, and
#:  at the end of a run. Writing hash.json for each file took seconds per file
#:  with hundreds of thousands of files in the library.
WRITE_EVERY_CHANGES = 100
WRITE_EVERY_SECONDS = 10


def _try_lock(lock_file):
    try:
        if sys.platform == 'win32':
            import msvcrt
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


class Db(object):

    """A class for interacting with the JSON files created by Elodie.

    Each instance loads the databases from disk. Db.shared() is the one
    instance of a run, i.e. an import, which loads them once and writes them
    periodically.
    """

    #: The instance returned by Db.shared()
    _shared = None

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

        self.hash_db_path = constants.hash_db()
        self.location_db_path = constants.location_db()
        # Changes which are not written yet, see update_hash_db()
        self.pending_changes = {'hash': 0, 'location': 0}
        self.last_write = {'hash': time.time(), 'location': time.time()}
        # Written periodically, without fsync, since the last durable write
        self.written_not_durable = {'hash': False, 'location': False}
        # Checksums by path, see move_hashes()
        self.paths = None

    @classmethod
    def shared(cls):
        """Get the Db of the run, which loads the databases once and writes
        them periodically instead of for each file. Its changes are written
        by flush_shared() at the end of the run or when elodie exits.

        :returns: Db
        """
        if (cls._shared is None or
                cls._shared.hash_db_path != constants.hash_db()):
            # The application directory changed, i.e. in tests
            cls.flush_shared()
            cls._shared = cls()
        return cls._shared

    @classmethod
    def flush_shared(cls):
        """Write the changes of the shared Db to disk.

        :returns: bool whether they were written
        """
        if cls._shared is None:
            return True
        try:
            cls._shared.flush()
            return True
        except OSError as e:
            log.error('Could not write the database of elodie: %s' % e)
            return False

    @classmethod
    @contextlib.contextmanager
    def lock(cls):
        """Lock the databases for a run which changes them, i.e. an import.
        The shared Db of a run holds them in memory and writes them
        periodically, a run at the same time would overwrite its changes.
        Another run waits until the lock is released.

        The databases are loaded after the lock is taken and written before
        it is released.
        """
        directory = constants.application_directory()
        if not os.path.exists(directory):
            os.makedirs(directory)
        lock_file = open(os.path.join(directory, 'elodie.lock'), 'a')
        try:
            if not _try_lock(lock_file):
                print('Waiting for another elodie which uses %s to finish...'
                      % directory, file=sys.stderr, flush=True)
                while not _try_lock(lock_file):
                    time.sleep(1)
            # Another run may have changed them
            cls.reset_shared()
            try:
                yield
            finally:
                cls.flush_shared()
        finally:
            # Closing it releases the lock
            lock_file.close()

    @classmethod
    def reset_shared(cls):
        """Write the changes of the shared Db and forget it."""
        cls.flush_shared()
        cls._shared = None

    def flush(self):
        """Write the databases with changes to disk, durably."""
        for name in ('hash', 'location'):
            if self.pending_changes[name] or self.written_not_durable[name]:
                self._update(name, periodically=False, change=False)

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
    def _write(path, data, durable=True):
        """Write a database to another file which then replaces it, so a
        write which is interrupted (i.e. Ctrl-C) does not corrupt it.

        :param bool durable: Also wait until it is on the disk (fsync) so it
            survives a power failure. That takes seconds for a large
            database, the periodic writes of a run skip it.
        """
        # Its own name, a write at the same time does not replace it
        handle, temporary_path = tempfile.mkstemp(
            dir=os.path.dirname(path), prefix=os.path.basename(path) + '.',
            suffix='.tmp')
        try:
            with os.fdopen(handle, 'w') as f:
                json.dump(data, f)
                if durable:
                    f.flush()
                    os.fsync(f.fileno())
            # The permissions of the database, not the ones of mkstemp
            if os.path.exists(path):
                mode = stat.S_IMODE(os.stat(path).st_mode)
            else:
                umask = os.umask(0)
                os.umask(umask)
                mode = 0o666 & ~umask
            os.chmod(temporary_path, mode)
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
        if self.paths is not None:
            self.paths.setdefault(os.path.abspath(value), set()).add(key)
        if(write is True):
            self.update_hash_db()

    def move_hashes(self, old_path, new_path):
        """Change the path of all hashes of a file which was moved.

        :param str old_path:
        :param str new_path:
        """
        if self.paths is None:
            # Built once, looking through all hashes for each moved file is
            #  slow for a large library
            self.paths = {}
            for key, value in self.hash_db.items():
                self.paths.setdefault(os.path.abspath(value), set()).add(key)
        old_path = os.path.abspath(old_path)
        for key in self.paths.pop(old_path, set()):
            if os.path.abspath(self.hash_db.get(key, '')) == old_path:
                self.add_hash(key, new_path)

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
        self.paths = None

    def update_hash_db(self, periodically=False):
        """Write the hash db to disk.

        :param bool periodically: Only write it after WRITE_EVERY_CHANGES
            changes or WRITE_EVERY_SECONDS seconds, flush() writes the rest.
        """
        self._update('hash', periodically)

    def update_location_db(self, periodically=False):
        """Write the location db to disk.

        :param bool periodically: See update_hash_db().
        """
        self._update('location', periodically)

    def _update(self, name, periodically, change=True):
        if change:
            self.pending_changes[name] += 1
        if constants.dry_run:
            # What would be written is reported once, at the end of a run
            if not periodically and self.pending_changes[name]:
                database = self.hash_db if name == 'hash' else self.location_db
                print(f"[DRY-RUN] Would update {name} database with "
                      f"{len(database)} entries")
                self.pending_changes[name] = 0
            return

        if (periodically and
                self.pending_changes[name] < WRITE_EVERY_CHANGES and
                time.time() - self.last_write[name] < WRITE_EVERY_SECONDS):
            return

        # The periodic writes are atomic, only the last one of a run (see
        #  flush()) is durable too since fsync takes seconds for a large
        #  database.
        durable = not periodically
        if name == 'hash':
            self._write(self.hash_db_path, self.hash_db, durable)
        else:
            self._write(self.location_db_path, self.location_db, durable)
        self.pending_changes[name] = 0
        self.last_write[name] = time.time()
        self.written_not_durable[name] = not durable


# The changes of the shared Db are written when elodie exits without
#  flush_shared(), i.e. after an error or Ctrl+C.
atexit.register(Db.flush_shared)
