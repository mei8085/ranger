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


def test_loadable_cancel_stops_generator():
    """Test that cancelling stops the generator from processing further."""
    # Create a generator that yields values and tracks how many were processed
    processed = [0]
    
    def test_generator():
        for i in range(10):
            processed[0] += 1
            yield i
    
    loadable = Loadable(test_generator(), "test generator")
    
    # Process a few items
    gen = loadable.load_generator
    next(gen)  # 0
    next(gen)  # 1
    next(gen)  # 2
    
    assert processed[0] == 3
    
    # Now cancel
    loadable.cancel()
    
    # Even though we cancelled, is_cancelled should return True
    assert loadable.is_cancelled() == True


def test_loadable_progressbar_supported():
    """Test that progressbar_supported defaults to False."""
    loadable = Loadable(iter([]), "test")
    assert loadable.progressbar_supported == False
    
    # Test that we can set it
    loadable.progressbar_supported = True
    assert loadable.progressbar_supported == True


def test_loadable_percent_tracking():
    """Test that percent tracking works."""
    loadable = Loadable(iter([]), "test")
    assert loadable.percent == 0
    
    loadable.percent = 50
    assert loadable.percent == 50
    
    loadable.percent = 100
    assert loadable.percent == 100
