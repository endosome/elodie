# Project imports
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

import helper
from elodie.compatability import _gmtime

@pytest.mark.parametrize('seconds', [0, 1, 1460027726.0, 1460027726.5])
def test_gmtime_matches_time_gmtime(seconds):
    assert _gmtime(seconds) == time.gmtime(seconds), seconds

@pytest.mark.skipif(helper.is_windows(), reason='time.gmtime does not support negative timestamps on Windows')
@pytest.mark.parametrize('seconds', [-1, -0.5, -1.5, -315576000, -2208988800])
def test_gmtime_negative_matches_time_gmtime(seconds):
    assert _gmtime(seconds) == time.gmtime(seconds), seconds

def test_gmtime_negative_without_os_support(monkeypatch):
    monkeypatch.setattr(time, 'gmtime', helper.windows_gmtime)

    assert _gmtime(-315576000) == (1960, 1, 1, 12, 0, 0, 4, 1, 0)
