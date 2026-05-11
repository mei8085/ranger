# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.
"""pytest configuration and fixtures for testing the gui tests.

This file provides curses mocks for platforms without curses support
(like Windows).
"""

from __future__ import (absolute_import, division, print_function)

import sys
from unittest import mock


try:
    import curses
except ImportError:
    mock_curses_module = mock.MagicMock()

    mock_curses_module.COLOR_BLACK = 0
    mock_curses_module.COLOR_BLUE = 4
    mock_curses_module.COLOR_CYAN = 6
    mock_curses_module.COLOR_GREEN = 2
    mock_curses_module.COLOR_MAGENTA = 5
    mock_curses_module.COLOR_RED = 1
    mock_curses_module.COLOR_WHITE = 7
    mock_curses_module.COLOR_YELLOW = 3

    mock_curses_module.A_NORMAL = 0
    mock_curses_module.A_BOLD = 1 << 13
    mock_curses_module.A_BLINK = 1 << 12
    mock_curses_module.A_REVERSE = 1 << 11
    mock_curses_module.A_UNDERLINE = 1 << 14
    mock_curses_module.A_INVIS = 1 << 15
    mock_curses_module.A_DIM = 1 << 16

    mock_curses_module.error = Exception

    mock_curses_module.color_pair = mock.MagicMock(side_effect=lambda n: n << 8)
    mock_curses_module.init_pair = mock.MagicMock()
    mock_curses_module.tigetnum = mock.MagicMock(return_value=16)
    mock_curses_module.setupterm = mock.MagicMock()

    sys.modules['curses'] = mock_curses_module
