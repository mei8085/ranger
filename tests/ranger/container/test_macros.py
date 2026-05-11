from __future__ import (absolute_import, division, print_function)

import os
import time

import pytest

from ranger.container.macros import Macros


class TestableMacros(Macros):
    def _validate(self, value):
        return True


def test_macros_basic(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    macros.load()

    assert macros.recording is False
    assert macros.recording_name is None
    assert macros.get("test") is None
    assert "test" not in macros


def test_macros_start_stop_recording(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    result = macros.start_recording("test")
    assert result is True
    assert macros.recording is True
    assert macros.recording_name == "test"

    macros.record_key(ord('a'))
    macros.record_key(ord('b'))
    macros.record_key(ord('c'))

    result = macros.start_recording("another")
    assert result is False

    name = macros.stop_recording()
    assert name == "test"
    assert macros.recording is False
    assert macros.recording_name is None

    assert "test" in macros
    assert macros.get("test") == [ord('a'), ord('b'), ord('c')]


def test_macros_stop_without_recording(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    result = macros.stop_recording()
    assert result is None


def test_macros_stop_with_no_keys(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    macros.start_recording("empty")
    name = macros.stop_recording()
    assert name is None
    assert "empty" not in macros


def test_macros_persistence(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    macros.start_recording("test")
    macros.record_key(ord('a'))
    macros.record_key(ord('b'))
    macros.stop_recording()

    macros.start_recording("another")
    macros.record_key(ord('x'))
    macros.record_key(ord('y'))
    macros.record_key(ord('z'))
    macros.stop_recording()

    assert os.path.exists(str(macrofile))

    macros2 = TestableMacros(str(macrofile))
    macros2.load()

    assert "test" in macros2
    assert "another" in macros2
    assert macros2.get("test") == [ord('a'), ord('b')]
    assert macros2.get("another") == [ord('x'), ord('y'), ord('z')]


def test_macros_delete(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    macros.start_recording("to_delete")
    macros.record_key(ord('a'))
    macros.stop_recording()

    assert "to_delete" in macros

    del macros["to_delete"]

    assert "to_delete" not in macros
    assert macros.get("to_delete") is None

    macros2 = TestableMacros(str(macrofile))
    macros2.load()
    assert "to_delete" not in macros2


def test_macros_iteration(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    macros.start_recording("a")
    macros.record_key(ord('1'))
    macros.stop_recording()

    macros.start_recording("b")
    macros.record_key(ord('2'))
    macros.stop_recording()

    items = list(macros)
    assert len(items) == 2
    names = [name for name, _ in items]
    assert "a" in names
    assert "b" in names


def test_macros_special_keys(tmpdir):
    import curses
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    macros.start_recording("special")
    macros.record_key(ord('\n'))
    macros.record_key(curses.KEY_UP)
    macros.record_key(curses.KEY_LEFT)
    macros.stop_recording()

    macros2 = TestableMacros(str(macrofile))
    macros2.load()

    assert "special" in macros2
    keys = macros2.get("special")
    assert len(keys) == 3
    assert keys[0] == ord('\n')
    assert keys[1] == curses.KEY_UP
    assert keys[2] == curses.KEY_LEFT


def test_macros_load_nonexistent_file(tmpdir):
    macrofile = tmpdir.join("nonexistent.json")
    macros = TestableMacros(str(macrofile))
    macros.load()
    assert len(list(macros)) == 0


def test_macros_update_if_outdated(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = TestableMacros(str(macrofile))

    macros.start_recording("test")
    macros.record_key(ord('a'))
    macros.stop_recording()

    orig_update = macros.update
    update_called = [False]

    def track_update():
        update_called[0] = True
        orig_update()

    macros.update = track_update

    macros.update_if_outdated()
    assert update_called[0] is False

    newtime = time.time() - 5
    os.utime(str(macrofile), (newtime, newtime))

    macros.update_if_outdated()
    assert update_called[0] is True


def test_macros_symlink(tmpdir):
    macrofile_link = tmpdir.join("macros.json")
    macrofile_orig = tmpdir.join("macros.json.orig")

    os.symlink(str(macrofile_orig), str(macrofile_link))

    macros = TestableMacros(str(macrofile_link))
    macros.start_recording("test")
    macros.record_key(ord('a'))
    macros.stop_recording()

    assert os.path.islink(str(macrofile_link))
    assert not os.path.islink(str(macrofile_orig))

    with open(str(macrofile_orig), 'r') as fobj:
        content = fobj.read()
        assert "test" in content
