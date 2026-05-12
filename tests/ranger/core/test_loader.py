from __future__ import (absolute_import, division, print_function)

import pytest

from ranger.core.loader import Loadable


def test_loadable_cancel():
    """Test that Loadable can be cancelled."""
    loadable = Loadable(iter([]), "test")
    assert loadable.is_cancelled() == False
    loadable.cancel()
    assert loadable.is_cancelled() == True


def test_loadable_destroy_cancels():
    """Test that calling destroy() also cancels the loadable."""
    loadable = Loadable(iter([]), "test")
    assert loadable.is_cancelled() == False
    loadable.destroy()
    assert loadable.is_cancelled() == True
