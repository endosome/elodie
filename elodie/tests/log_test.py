from __future__ import absolute_import
# Project imports

import os
import sys
import unittest 

from json import dumps
from unittest.mock import patch
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from elodie import constants
from elodie import log


def call_log_and_assert(func, args, expected):
    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        func(*args)
        output = out.getvalue()
        assert output == expected, (expected, func, output)
    finally:
        sys.stdout = saved_stdout

def with_new_line(string):
    return "{}\n".format(string)

@patch('elodie.log')
@patch('elodie.constants.debug', True)
def test_calls_print_debug_true(fake_log):
    expected = 'some string'
    fake_log.info.return_value = expected
    fake_log.warn.return_value = expected
    fake_log.error.return_value = expected
    for func in [log.info, log.warn, log.error]:
        call_log_and_assert(func, [expected], with_new_line(expected))

    expected_json = {'foo':'bar'}
    fake_log.info.return_value = expected_json
    fake_log.warn.return_value = expected_json
    fake_log.error.return_value = expected_json
    for func in [log.info_json, log.warn_json, log.error_json]:
        call_log_and_assert(func, [expected_json], with_new_line(dumps(expected_json)))

@patch('elodie.log')
@patch('elodie.constants.debug', False)
def test_calls_print_debug_false(fake_log):
    expected = 'some other string'
    fake_log.info.return_value = expected
    fake_log.warn.return_value = expected
    fake_log.error.return_value = expected
    for func in [log.info, log.warn, log.error]:
        call_log_and_assert(func, [expected], '')

    expected_json = {'foo':'bar'}
    fake_log.info.return_value = expected_json
    fake_log.warn.return_value = expected_json
    fake_log.error.return_value = expected_json
    for func in [log.info_json, log.warn_json, log.error_json]:
        call_log_and_assert(func, [expected_json], '')

@patch('elodie.log')
def test_calls_print_progress_no_new_line(fake_log):
    expected = 'some other string'
    fake_log.info.return_value = expected
    fake_log.warn.return_value = expected
    fake_log.error.return_value = expected
    call_log_and_assert(log.progress, [expected], expected)

@patch('elodie.log')
def test_calls_print_progress_with_new_line(fake_log):
    expected = "some other string\n"
    fake_log.info.return_value = expected
    fake_log.warn.return_value = expected
    fake_log.error.return_value = expected
    call_log_and_assert(log.progress, [expected, True], with_new_line(expected))

def test_print_falls_back_to_char_by_char_on_unicode_encode_error():
    # Some terminals cannot print certain unicode characters and raise a
    # UnicodeEncodeError. In that case _print should retry printing the
    # string one character at a time, replacing anything it still can't
    # print with '?'.
    good_char = 'a'
    bad_char = '✓'
    string = good_char + bad_char

    def fake_print(s, end='\n'):
        if bad_char in s:
            raise UnicodeEncodeError('ascii', s, 0, 1, 'test')
        sys.stdout.write('{}{}'.format(s, end))

    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        with patch('builtins.print', side_effect=fake_print):
            log._print(string)
        output = out.getvalue()
    finally:
        sys.stdout = saved_stdout

    assert output == 'a?', output
