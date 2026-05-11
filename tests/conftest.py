from __future__ import (absolute_import, division, print_function)

import sys
from unittest.mock import MagicMock


class MockCursesAscii:
    DEL = 127
    ESC = 27


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
    KEY_MOUSE = 409
    KEY_RESIZE = 410
    KEY_ENTER = 343

    COLOR_BLACK = 0
    COLOR_RED = 1
    COLOR_GREEN = 2
    COLOR_YELLOW = 3
    COLOR_BLUE = 4
    COLOR_MAGENTA = 5
    COLOR_CYAN = 6
    COLOR_WHITE = 7
    A_NORMAL = 0
    A_BOLD = 2097152
    A_REVERSE = 65536
    A_BLINK = 524288
    A_UNDERLINE = 131072
    A_DIM = 1048576
    A_STANDOUT = 65536
    A_ITALIC = 262144
    A_INVIS = 8388608

    ascii = MockCursesAscii()

    class error(Exception):
        pass

    @staticmethod
    def color_pair(n):
        return n * 256

    @staticmethod
    def pair_content(pair_number):
        return pair_number * 256

    @staticmethod
    def init_pair(pair_number, fg, bg):
        pass

    @staticmethod
    def flushinp():
        pass

    @staticmethod
    def setupterm():
        pass

    @staticmethod
    def tigetnum(capname):
        return 16

    @staticmethod
    def use_default_colors():
        pass


_mock_curses = MockCurses()
sys.modules['curses'] = _mock_curses
sys.modules['curses.ascii'] = _mock_curses.ascii


class MockGrp:
    @staticmethod
    def getgrgid(gid):
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


pytest_plugins = []
