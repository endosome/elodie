"""
General file system methods.

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""

import sys

from json import dumps

from elodie import constants

def all(message):
    _print(message)
    

def info(message):
    _print_debug(message)


def info_json(payload):
    _print_debug(dumps(payload))


def progress(message='.', new_line=False):
    if not new_line:
        print(message, end="")
    else:
        print(message)


def warn(message):
    _print_debug(message)


def warn_json(payload):
    _print_debug(dumps(payload))


def error(message):
    # Errors are shown in all modes, on stderr. Problems which are handled,
    #  i.e. an invalid date which is skipped, are logged with info().
    _print(message, file=sys.stderr)


def error_json(payload):
    _print(dumps(payload), file=sys.stderr)


def _print_debug(string):
    # Print if debug == True or if running with nosetests
    # Commenting out because this causes failures in other tests
    #  which verify that output is correct.
    # Use the line below if you want output printed during tests.
    # if(constants.debug is True or 'nose' in sys.modules.keys()):
    if(constants.debug is True):
        _print(string)

def _print(s, file=None):
    s = str(s)
    try:
        print(s, file=file)
    except UnicodeEncodeError:
        for c in s:
            try:
                print(c, end='', file=file)
            except UnicodeEncodeError:
                print('?', end='', file=file)
        print(file=file)
