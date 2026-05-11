from __future__ import (absolute_import, division, print_function)

import sys
from unittest.mock import MagicMock


class MockCurses:
    KEY_BACKSPACE = 263
    KEY_DC = 330
    KEY_SDC = 331
    KEY_IC = 331
    KEY_DOWN = 258
    KEY_UP = 259
    KEY_LEFT = 260
    KEY_RIGHT = 261
    KEY_NPAGE = 338
    KEY_PPAGE = 339
    KEY_HOME = 262
    KEY_END = 360
    KEY_BTAB = 353
    KEY_F0 = 264

    class ascii:
        DEL = 127
        ESC = 27


_mock_curses = MockCurses()
sys.modules['curses'] = _mock_curses
sys.modules['curses.ascii'] = _mock_curses.ascii


class MockGrp:
    @staticmethod
    def getgrgid(self, gid):
        mock = MagicMock()
        mock.gr_name = 'users'
        return mock


_mock_grp = MockGrp()
sys.modules['grp'] = _mock_grp


class MockPwd:
    @staticmethod
    def getpwuid(uid):
        mock = MagicMock()
        mock.pw_name = 'testuser'
        return mock


_mock_pwd = MockPwd()
sys.modules['pwd'] = _mock_pwd
