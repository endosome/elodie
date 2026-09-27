# Project imports

import os
import sys
import unittest 

from json import dumps
from unittest.mock import patch

import pytest
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

@pytest.mark.parametrize('debug', [True, False])
def test_info_and_warn_are_only_shown_with_debug(capsys, debug):
    with patch('elodie.constants.debug', debug):
        log.info('some info')
        log.warn('some warning')
        log.info_json({'foo': 'bar'})
        log.warn_json({'foo': 'bar'})
    out, err = capsys.readouterr()

    expected = 'some info\nsome warning\n{0}\n{0}\n'.format(dumps({'foo': 'bar'}))
    assert out == (expected if debug else ''), out
    assert err == '', err

@pytest.mark.parametrize('debug', [True, False])
def test_errors_are_shown_on_stderr_in_all_modes(capsys, debug):
    with patch('elodie.constants.debug', debug):
        log.error('some error')
        log.error_json({'foo': 'bar'})
    out, err = capsys.readouterr()

    assert out == '', out
    assert err == 'some error\n{}\n'.format(dumps({'foo': 'bar'})), err

def test_characters_which_cannot_be_printed_are_replaced(capsys):
    # i.e. a terminal without UTF-8
    real_print = print

    def print_ascii(*args, **kwargs):
        ''.join(str(a) for a in args).encode('ascii')
        real_print(*args, **kwargs)

    with patch('builtins.print', side_effect=print_ascii):
        log.error('café')
    out, err = capsys.readouterr()

    assert err == 'caf?\n', err

def test_calls_print_progress_no_new_line():
    expected = 'some other string'
    call_log_and_assert(log.progress, [expected], expected)

def test_calls_print_progress_with_new_line():
    expected = "some other string\n"
    call_log_and_assert(log.progress, [expected, True], with_new_line(expected))
