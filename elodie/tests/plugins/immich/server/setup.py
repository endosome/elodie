#!/usr/bin/env python
"""Set up the Immich of docker-compose.yml for the integration tests and
print the environment variables they read:

    eval "$(python setup.py)"                    # a shell
    python setup.py --env-file >> "$GITHUB_ENV"  # GitHub Actions

It waits for Immich, creates an admin, an external library for
IMMICH_TEST_LIBRARY_PATH and two API keys: one with the permissions the
plugin needs, as listed in its Readme, and one with all of them for the
tests to set up Immich.
"""
import os
import shlex
import sys
import time

import requests

API_URL = os.environ.get(
    'IMMICH_TEST_API_URL',
    'http://127.0.0.1:%s/api' % os.environ.get('IMMICH_TEST_PORT', '2283'))
EXTERNAL_PATH = '/external/library'
ADMIN = {'email': 'admin@example.com', 'password': 'elodie-test',
         'name': 'Admin'}
# The permissions the plugin needs, keep in sync with the Readme
PLUGIN_PERMISSIONS = ['album.read', 'album.create', 'albumAsset.create',
                      'albumAsset.delete', 'asset.read', 'asset.update',
                      'user.read']


def main():
    if not os.environ.get('IMMICH_TEST_LIBRARY_PATH'):
        sys.exit('Set IMMICH_TEST_LIBRARY_PATH like for docker compose')
    session = requests.Session()
    for _ in range(150):
        try:
            if session.get(API_URL + '/server/ping', timeout=5).ok:
                break
        except requests.ConnectionError:
            pass
        time.sleep(2)
    else:
        sys.exit('Immich did not start at %s' % API_URL)

    # Fails if the admin exists already, i.e. when running it twice
    session.post(API_URL + '/auth/admin-sign-up', json=ADMIN)
    response = session.post(API_URL + '/auth/login', json={
        'email': ADMIN['email'], 'password': ADMIN['password']})
    response.raise_for_status()
    token = response.json()['accessToken']
    session.headers['Authorization'] = 'Bearer ' + token

    def api_key(name, permissions):
        response = session.post(API_URL + '/api-keys', json={
            'name': name, 'permissions': permissions})
        response.raise_for_status()
        return response.json()['secret']

    libraries = session.get(API_URL + '/libraries').json()
    library = next((lib for lib in libraries
                    if EXTERNAL_PATH in lib['importPaths']), None)
    if library is None:
        owner = session.get(API_URL + '/users/me').json()['id']
        response = session.post(API_URL + '/libraries', json={
            'ownerId': owner, 'name': 'elodie',
            'importPaths': [EXTERNAL_PATH]})
        response.raise_for_status()
        library = response.json()

    variables = [
        ('IMMICH_TEST_API_URL', API_URL),
        ('IMMICH_TEST_API_KEY', api_key('elodie plugin', PLUGIN_PERMISSIONS)),
        ('IMMICH_TEST_ADMIN_API_KEY', api_key('elodie tests', ['all'])),
        ('IMMICH_TEST_LIBRARY_ID', library['id']),
        ('IMMICH_TEST_EXTERNAL_PATH', EXTERNAL_PATH),
        ('IMMICH_TEST_LIBRARY_PATH',
         os.path.abspath(os.environ['IMMICH_TEST_LIBRARY_PATH'])),
    ]
    for name, value in variables:
        if '--env-file' in sys.argv:
            print('%s=%s' % (name, value))
        else:
            print('export %s=%s' % (name, shlex.quote(value)))


if __name__ == '__main__':
    main()
