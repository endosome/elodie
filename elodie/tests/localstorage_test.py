# Project imports
import os
import unittest.mock as mock

import pytest
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from . import helper
from elodie.localstorage import Db
from elodie import constants


def test_init_writes_files():
    db = Db()

    assert os.path.isfile(constants.hash_db()) == True
    assert os.path.isfile(constants.location_db()) == True

def test_add_hash_default_do_not_write():
    db = Db()

    random_key = helper.random_string(10)
    random_value = helper.random_string(12)

    # Test with default False value as 3rd param
    db.add_hash(random_key, random_value)

    assert db.check_hash(random_key) == True, 'Lookup for hash did not return True'

    # Instnatiate new db class to confirm random_key does not exist
    db2 = Db()
    assert db2.check_hash(random_key) == False
    
def test_add_hash_explicit_do_not_write():
    db = Db()

    random_key = helper.random_string(10)
    random_value = helper.random_string(12)

    # Test with explicit False value as 3rd param
    db.add_hash(random_key, random_value, False)

    assert db.check_hash(random_key) == True, 'Lookup for hash did not return True'

    # Instnatiate new db class to confirm random_key does not exist
    db2 = Db()
    assert db2.check_hash(random_key) == False
    
def test_add_hash_explicit_write():
    db = Db()

    random_key = helper.random_string(10)
    random_value = helper.random_string(12)

    # Test with explicit True value as 3rd param
    db.add_hash(random_key, random_value, True)

    assert db.check_hash(random_key) == True, 'Lookup for hash did not return True'

    # Instnatiate new db class to confirm random_key exists
    db2 = Db()
    assert db2.check_hash(random_key) == True

def test_backup_hash_db():
    db = Db()
    backup_file_name = db.backup_hash_db()
    file_exists = os.path.isfile(backup_file_name)
    os.remove(backup_file_name)
    
    assert file_exists, backup_file_name
    
def test_check_hash_exists():
    db = Db()

    random_key = helper.random_string(10)
    random_value = helper.random_string(12)

    # Test with explicit False value as 3rd param
    db.add_hash(random_key, random_value, False)

    assert db.check_hash(random_key) == True, 'Lookup for hash did not return True'
    
def test_check_hash_does_not_exist():
    db = Db()

    random_key = helper.random_string(10)

    assert db.check_hash(random_key) == False, 'Lookup for hash that should not exist returned True'

def test_get_hash_exists():
    db = Db()

    random_key = helper.random_string(10)
    random_value = helper.random_string(12)

    # Test with explicit False value as 3rd param
    db.add_hash(random_key, random_value, False)

    assert db.get_hash(random_key) == random_value, 'Lookup for hash that exists did not return value'
    
def test_get_hash_does_not_exist():
    db = Db()

    random_key = helper.random_string(10)

    assert db.get_hash(random_key) is None, 'Lookup for hash that should not exist did not return None'

def test_get_all():
    db = Db()
    db.reset_hash_db()

    random_keys = []
    random_values = []
    for _ in range(10):
        random_keys.append(helper.random_string(10))
        random_values.append(helper.random_string(12))
        db.add_hash(random_keys[-1:][0], random_values[-1:][0], False)

    counter = 0
    for key, value in db.all():
        assert key in random_keys, key
        assert value in random_values, value
        counter += 1

    assert counter == 10, counter

def test_get_all_empty():
    db = Db()
    db.reset_hash_db()

    counter = 0
    for key, value in db.all():
        counter += 1

    # there's a final iteration because of the generator
    assert counter == 0, counter

def test_reset_hash_db():
    db = Db()

    random_key = helper.random_string(10)
    random_value = helper.random_string(12)

    # Test with explicit False value as 3rd param
    db.add_hash(random_key, random_value, False)
    
    assert random_key in db.hash_db, random_key
    db.reset_hash_db()
    assert random_key not in db.hash_db, random_key


def test_update_hash_db():
    db = Db()

    random_key = helper.random_string(10)
    random_value = helper.random_string(12)

    # Test with default False value as 3rd param
    db.add_hash(random_key, random_value)

    assert db.check_hash(random_key) == True, 'Lookup for hash did not return True'

    # Instnatiate new db class to confirm random_key does not exist
    db2 = Db()
    assert db2.check_hash(random_key) == False

    db.update_hash_db()

    # Instnatiate new db class to confirm random_key exists
    db3 = Db()
    assert db3.check_hash(random_key) == True

def test_checksum():
    db = Db()

    src = helper.get_file('plain.jpg')
    checksum = db.checksum(src)

    assert checksum == 'd5eb755569ddbc8a664712d2d7d6e0fa1ddfcdb378475e4a6758dc38d5ea9a16', 'Checksum for plain.jpg did not match'

def test_add_location():
    db = Db()

    latitude, longitude, name = helper.get_test_location()

    db.add_location(latitude, longitude, name)
    retrieved_name = db.get_location_name(latitude, longitude, 5)

    assert name == retrieved_name

def test_get_location_name():
    db = Db()

    latitude, longitude, name = helper.get_test_location()
    db.add_location(latitude, longitude, name)

    
    # 1 meter
    retrieved_name = db.get_location_name(latitude, longitude, 1)

    assert name == retrieved_name

def test_get_location_name_within_threshold():
    db = Db()

    latitude, longitude, name = helper.get_test_location()
    db.add_location(latitude, longitude, name)

    print(latitude)
    new_latitude = helper.random_coordinate(latitude, 4)
    new_longitude = helper.random_coordinate(longitude, 4)
    print(new_latitude)

    # 10 miles
    retrieved_name = db.get_location_name(new_latitude, new_longitude, 1600*10)

    assert name == retrieved_name, 'Name (%r) did not match retrieved name (%r)' % (name, retrieved_name)

def test_get_location_name_outside_threshold():
    db = Db()

    latitude, longitude, name = helper.get_test_location()
    db.add_location(latitude, longitude, name)

    new_latitude = helper.random_coordinate(latitude, 1)
    new_longitude = helper.random_coordinate(longitude, 1)

    # 800 meters
    retrieved_name = db.get_location_name(new_latitude, new_longitude, 800)

    assert retrieved_name is None

def test_get_location_coordinates_exists():
    db = Db()
    
    latitude, longitude, name = helper.get_test_location()

    name = '%s-%s' % (name, helper.random_string(10))
    latitude = helper.random_coordinate(latitude, 1)
    longitude = helper.random_coordinate(longitude, 1)

    db.add_location(latitude, longitude, name)

    location = db.get_location_coordinates(name)

    assert location is not None
    assert location[0] == latitude
    assert location[1] == longitude

def test_get_location_coordinates_does_not_exists():
    db = Db()
    
    latitude, longitude, name = helper.get_test_location()

    name = '%s-%s' % (name, helper.random_string(10))
    latitude = helper.random_coordinate(latitude, 1)
    longitude = helper.random_coordinate(longitude, 1)

    location = db.get_location_coordinates(name)

    assert location is None

def test_get_location_name_returns_the_closest_location():
    # The closest location within the threshold, whatever the order of the
    #  locations in the database
    db = Db()
    db.location_db = []
    db.add_location(37.0005, -122.0, 'Near')    # 55 m
    db.add_location(37.1000, -122.0, 'Far')     # 11 km, outside
    db.add_location(37.0100, -122.0, 'Medium')  # 1.1 km

    assert db.get_location_name(37.0, -122.0, 3000) == 'Near'
    db.location_db.reverse()
    assert db.get_location_name(37.0, -122.0, 3000) == 'Near'

def test_unreadable_hash_db_is_moved_aside():
    # i.e. cut off by a crash while it was written. It must not be
    #  overwritten, it can be recovered.
    with open(constants.hash_db(), 'w') as f:
        f.write('{"abc": "/photos/a.jpg", "de')

    with mock.patch('elodie.log.error') as error:
        db = Db()
    corrupt = [f for f in os.listdir(constants.application_directory()) if f.startswith('hash.json-corrupt-')]

    assert db.hash_db == {}
    assert len(corrupt) == 1, corrupt
    with open(os.path.join(constants.application_directory(), corrupt[0])) as f:
        assert f.read() == '{"abc": "/photos/a.jpg", "de'
    assert 'hash.json-corrupt-' in error.call_args[0][0]

def test_empty_db_files_are_not_unreadable():
    # Created and not written yet
    open(constants.hash_db(), 'w').close()
    open(constants.location_db(), 'w').close()

    with mock.patch('elodie.log.error') as error:
        db = Db()

    assert (db.hash_db, db.location_db) == ({}, [])
    assert error.call_count == 0
    assert sorted(os.listdir(constants.application_directory())) == ['config.ini', 'hash.json', 'location.json']

def test_interrupted_write_keeps_the_hash_db():
    # i.e. Ctrl-C while writing
    db = Db()
    db.add_hash('abc', '/photos/a.jpg', True)

    db.add_hash('def', '/photos/b.jpg')
    with mock.patch('json.dump', side_effect=KeyboardInterrupt()):
        with pytest.raises(KeyboardInterrupt):
            db.update_hash_db()

    assert Db().hash_db == {'abc': '/photos/a.jpg'}
    assert not os.path.exists(constants.hash_db() + '.tmp')

def _read_json(path):
    import json
    with open(path) as f:
        content = f.read()
    return json.loads(content) if content.strip() else None

@mock.patch('elodie.localstorage.WRITE_EVERY_CHANGES', 3)
@mock.patch('elodie.localstorage.WRITE_EVERY_SECONDS', 3600)
def test_update_hash_db_periodically_after_changes():
    db = Db()
    written = []
    for i in range(4):
        db.add_hash('key%d' % i, 'value')
        db.update_hash_db(periodically=True)
        written.append(len(_read_json(constants.hash_db()) or {}))
    db.flush()

    # Written with the 3rd change, the 4th by flush()
    assert written == [0, 0, 3, 3], written
    assert len(_read_json(constants.hash_db())) == 4

@mock.patch('elodie.localstorage.WRITE_EVERY_CHANGES', 1000)
@mock.patch('elodie.localstorage.WRITE_EVERY_SECONDS', 0)
def test_update_hash_db_periodically_after_seconds():
    db = Db()
    db.add_hash('key', 'value')
    db.update_hash_db(periodically=True)

    assert _read_json(constants.hash_db()) == {'key': 'value'}

@mock.patch('elodie.localstorage.WRITE_EVERY_CHANGES', 3)
@mock.patch('elodie.localstorage.WRITE_EVERY_SECONDS', 3600)
def test_update_location_db_periodically():
    db = Db()
    db.add_location(1.0, 2.0, 'Somewhere')
    db.update_location_db(periodically=True)
    before_flush = _read_json(constants.location_db())
    db.flush()

    assert before_flush is None, before_flush
    assert _read_json(constants.location_db()) == [{'lat': 1.0, 'long': 2.0, 'name': 'Somewhere'}]

def test_flush_without_changes_does_not_write():
    db = Db()
    with mock.patch.object(Db, '_write') as write:
        db.flush()

    write.assert_not_called()

@mock.patch('elodie.localstorage.WRITE_EVERY_CHANGES', 1)
def test_only_the_last_write_of_a_run_is_durable():
    # fsync takes seconds for a large database, periodic writes skip it
    db = Db()
    with mock.patch('elodie.localstorage.os.fsync') as fsync:
        db.add_hash('key1', 'value')
        db.update_hash_db(periodically=True)
        db.add_hash('key2', 'value')
        db.update_hash_db(periodically=True)
        periodic_fsyncs = fsync.call_count
        # Nothing is pending but it is not on the disk durably yet
        db.flush()
        flush_fsyncs = fsync.call_count
        db.flush()

    assert periodic_fsyncs == 0, periodic_fsyncs
    assert flush_fsyncs == 1, flush_fsyncs
    assert fsync.call_count == 1, fsync.call_count
    assert _read_json(constants.hash_db()) == {'key1': 'value', 'key2': 'value'}

@mock.patch('elodie.constants.dry_run', True)
@mock.patch('elodie.localstorage.WRITE_EVERY_CHANGES', 1)
def test_update_hash_db_periodically_dry_run(capsys):
    db = Db()
    db.add_hash('key', 'value')
    db.update_hash_db(periodically=True)
    db.add_hash('other', 'value')
    db.update_hash_db(periodically=True)
    db.flush()
    db.flush()

    assert _read_json(constants.hash_db()) is None
    # Reported once, at the end
    assert capsys.readouterr().out.count('Would update hash database with 2 entries') == 1

def test_shared_is_loaded_once():
    with mock.patch.object(Db, '_load', wraps=Db._load) as load:
        db1 = Db.shared()
        db2 = Db.shared()

    assert db1 is db2
    # hash.json and location.json
    assert load.call_count == 2, load.call_args_list

def test_shared_changes_with_application_directory(monkeypatch, tmp_path):
    db1 = Db.shared()
    db1.add_hash('key', 'value')
    db1.update_hash_db(periodically=True)
    first_hash_db = constants.hash_db()

    monkeypatch.setenv('ELODIE_APPLICATION_DIRECTORY', str(tmp_path))
    db2 = Db.shared()

    assert db1 is not db2
    assert db2.hash_db_path == str(tmp_path / 'hash.json')
    # The changes of the previous one were written
    assert _read_json(first_hash_db) == {'key': 'value'}

def test_shared_is_written_when_elodie_exits():
    # i.e. after an error or Ctrl+C, without flush_shared()
    import subprocess
    code = (
        'import sys; sys.path.insert(0, {root!r})\n'
        'from elodie.localstorage import Db\n'
        'db = Db.shared()\n'
        'db.add_hash("key", "value")\n'
        'db.update_hash_db(periodically=True)\n'
        'raise KeyboardInterrupt\n'
    ).format(root=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                            env=dict(os.environ, ELODIE_APPLICATION_DIRECTORY=constants.application_directory()))

    assert result.returncode != 0
    assert _read_json(constants.hash_db()) == {'key': 'value'}

def test_move_hashes():
    db = Db()
    db.add_hash('source', '/library/a.jpg')
    db.add_hash('content', '/library/a.jpg')
    db.add_hash('other', '/library/b.jpg')

    db.move_hashes('/library/a.jpg', '/library/c.jpg')
    # A hash added after the index was built
    db.add_hash('new', '/library/c.jpg')
    db.move_hashes('/library/c.jpg', '/library/d.jpg')

    assert db.hash_db == {'source': '/library/d.jpg', 'content': '/library/d.jpg',
                          'new': '/library/d.jpg', 'other': '/library/b.jpg'}, db.hash_db

def test_move_hashes_does_not_look_through_all_hashes_for_each_file():
    # For a large library update was slow
    db = Db()
    for i in range(1000):
        db.add_hash('key%d' % i, '/library/%d.jpg' % i)
    db.move_hashes('/library/0.jpg', '/library/moved-0.jpg')

    with mock.patch('elodie.localstorage.os.path.abspath', wraps=os.path.abspath) as abspath:
        for i in range(1, 11):
            db.move_hashes('/library/%d.jpg' % i, '/library/moved-%d.jpg' % i)

    assert abspath.call_count < 100, abspath.call_count
    assert db.get_hash('key5') == '/library/moved-5.jpg'

def test_writes_at_the_same_time_do_not_fail():
    # They used the same temporary file, hash.json.tmp, one could replace
    #  the other's and fail
    import threading
    errors = []

    def write(n):
        db = Db()
        db.add_hash('key%d' % n, 'value')
        for i in range(30):
            try:
                db.update_hash_db()
            except Exception as e:
                errors.append(e)
    threads = [threading.Thread(target=write, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    directory = os.path.dirname(constants.hash_db())
    assert errors == [], errors
    assert [f for f in os.listdir(directory) if f.endswith('.tmp')] == []

def test_write_keeps_the_permissions_of_the_database():
    import stat
    db = Db()
    db.add_hash('key', 'value', True)
    os.chmod(constants.hash_db(), 0o640)

    db.add_hash('other', 'value', True)

    assert stat.S_IMODE(os.stat(constants.hash_db()).st_mode) == 0o640

def test_flush_shared_reports_a_write_error(capsys):
    db = Db.shared()
    db.add_hash('key', 'value')
    db.update_hash_db(periodically=True)

    with mock.patch.object(Db, '_write', side_effect=OSError(28, 'No space left on device')):
        written = Db.flush_shared()

    assert written is False
    assert 'Could not write the database of elodie' in capsys.readouterr().err
    # Written the next time
    assert Db.flush_shared() is True
    assert _read_json(constants.hash_db()) == {'key': 'value'}

def test_lock_loads_the_databases_again_and_writes_them():
    db = Db.shared()
    # Changed by another run
    other = Db()
    other.add_hash('other', 'value', True)

    with Db.lock():
        locked = Db.shared()
        locked.add_hash('key', 'value')
        locked.update_hash_db(periodically=True)

    assert locked is not db
    assert _read_json(constants.hash_db()) == {'other': 'value', 'key': 'value'}

def test_lock_is_released_after_an_error():
    from elodie.localstorage import _try_lock
    with pytest.raises(KeyboardInterrupt):
        with Db.lock():
            raise KeyboardInterrupt

    with open(os.path.join(constants.application_directory(), 'elodie.lock'), 'a') as lock_file:
        assert _try_lock(lock_file)
