from __future__ import (absolute_import, division, print_function)

import pytest
from unittest.mock import MagicMock, call

from ranger.container.macros import Macros
from ranger.core.actions import Actions
from ranger.core.shared import FileManagerAware, SettingsAware


class MockUI:
    def __init__(self):
        self.handle_keys_calls = []
        self.handle_key_calls = []

    def handle_keys(self, *keys):
        self.handle_keys_calls.append(keys)
        for key in keys:
            self.handle_key_calls.append(key)

    def handle_key(self, key):
        pass


class TestableActions(Actions):
    def __init__(self):
        self.notify_calls = []

    def notify(self, message, bad=False):
        self.notify_calls.append((message, bad))


class TestableMacros(Macros):
    pass


class TestMacroPlaybackChain:
    def setup_method(self):
        self.mock_fm = MagicMock()
        self.mock_ui = MockUI()
        self.mock_fm.ui = self.mock_ui

        self.mock_settings = MagicMock()
        self.mock_settings.__class__ = MagicMock
        self.mock_settings.__getitem__ = MagicMock(return_value=True)

        FileManagerAware.fm_set(self.mock_fm)
        SettingsAware.settings_set(self.mock_settings)

    def teardown_method(self):
        FileManagerAware.fm_set(None)

    def test_macro_play_calls_handle_keys_with_correct_keys(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        macros.start_recording("test_macro")
        macros.record_key(ord('j'))
        macros.record_key(ord('k'))
        macros.record_key(ord('j'))
        macros.stop_recording()

        result = actions.macro_play("test_macro")

        assert result is True
        assert len(self.mock_ui.handle_keys_calls) == 1
        assert self.mock_ui.handle_keys_calls[0] == (ord('j'), ord('k'), ord('j'))

    def test_macro_play_nonexistent_macro(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))
        macros.load()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("nonexistent")

        assert result is False
        assert len(self.mock_ui.handle_keys_calls) == 0
        assert len(actions.notify_calls) == 1
        assert "not found" in actions.notify_calls[0][0].lower()
        assert actions.notify_calls[0][1] is True

    def test_macro_play_while_recording(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("test_macro")
        macros.record_key(ord('a'))

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("test_macro")

        assert result is False
        assert len(self.mock_ui.handle_keys_calls) == 0
        assert len(actions.notify_calls) == 1
        assert "recording" in actions.notify_calls[0][0].lower()
        assert actions.notify_calls[0][1] is True

    def test_macro_play_empty_macro(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("empty")
        macros.stop_recording()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("empty")

        assert result is False
        assert len(self.mock_ui.handle_keys_calls) == 0

    def test_macro_play_multiple_times(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("nav_down")
        macros.record_key(ord('j'))
        macros.record_key(ord('j'))
        macros.stop_recording()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        actions.macro_play("nav_down")
        actions.macro_play("nav_down")
        actions.macro_play("nav_down")

        assert len(self.mock_ui.handle_keys_calls) == 3
        assert self.mock_ui.handle_keys_calls == [
            (ord('j'), ord('j')),
            (ord('j'), ord('j')),
            (ord('j'), ord('j')),
        ]

    def test_macro_play_after_restart(self, tmpdir):
        macrofile = tmpdir.join("macros.json")

        macros1 = TestableMacros(str(macrofile))
        macros1.start_recording("workflow")
        macros1.record_key(ord('g'))
        macros1.record_key(ord('g'))
        macros1.record_key(ord('V'))
        macros1.stop_recording()

        macros2 = TestableMacros(str(macrofile))
        macros2.load()

        self.mock_fm.macros = macros2
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("workflow")

        assert result is True
        assert len(self.mock_ui.handle_keys_calls) == 1
        assert self.mock_ui.handle_keys_calls[0] == (ord('g'), ord('g'), ord('V'))

    def test_macro_play_with_special_keys(self, tmpdir):
        import curses

        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("special_nav")
        macros.record_key(curses.KEY_UP)
        macros.record_key(curses.KEY_DOWN)
        macros.record_key(curses.KEY_LEFT)
        macros.record_key(curses.KEY_RIGHT)
        macros.stop_recording()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("special_nav")

        assert result is True
        assert self.mock_ui.handle_keys_calls[0] == (
            curses.KEY_UP,
            curses.KEY_DOWN,
            curses.KEY_LEFT,
            curses.KEY_RIGHT,
        )

    def test_macro_play_with_mixed_keys(self, tmpdir):
        import curses

        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("complex")
        macros.record_key(ord(':'))
        macros.record_key(ord('q'))
        macros.record_key(ord('\n'))
        macros.stop_recording()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("complex")

        assert result is True
        assert self.mock_ui.handle_keys_calls[0] == (ord(':'), ord('q'), ord('\n'))

    def test_macro_start_stop_and_play(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        macros.start_recording("my_seq")
        macros.record_key(ord('h'))
        macros.record_key(ord('e'))
        macros.record_key(ord('l'))
        macros.record_key(ord('l'))
        macros.record_key(ord('o'))
        macros.stop_recording()

        result = actions.macro_play("my_seq")

        assert result is True
        assert self.mock_ui.handle_keys_calls[0] == (
            ord('h'), ord('e'), ord('l'), ord('l'), ord('o')
        )

    def test_macro_play_deleted_macro(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("to_delete")
        macros.record_key(ord('a'))
        macros.stop_recording()

        assert "to_delete" in macros
        del macros["to_delete"]

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("to_delete")

        assert result is False
        assert len(self.mock_ui.handle_keys_calls) == 0

    def test_macro_play_overwritten_macro(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("test")
        macros.record_key(ord('1'))
        macros.stop_recording()

        macros.start_recording("test")
        macros.record_key(ord('2'))
        macros.record_key(ord('3'))
        macros.stop_recording()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("test")

        assert result is True
        assert self.mock_ui.handle_keys_calls[0] == (ord('2'), ord('3'))

    def test_macro_play_persistence_after_restart(self, tmpdir):
        macrofile = tmpdir.join("macros.json")

        macros1 = TestableMacros(str(macrofile))
        macros1.start_recording("persistent")
        macros1.record_key(ord('y'))
        macros1.record_key(ord('y'))
        macros1.record_key(ord('p'))
        macros1.stop_recording()

        macros2 = TestableMacros(str(macrofile))
        macros2.load()

        self.mock_fm.macros = macros2
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("persistent")

        assert result is True
        assert self.mock_ui.handle_keys_calls[0] == (ord('y'), ord('y'), ord('p'))

    def test_macro_play_empty_sequence_not_saved(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("empty")
        macros.stop_recording()

        assert "empty" not in macros
        assert macros.get("empty") is None

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("empty")

        assert result is False
        assert len(self.mock_ui.handle_keys_calls) == 0

    def test_macro_play_multiple_macros(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("macro_a")
        macros.record_key(ord('a'))
        macros.record_key(ord('a'))
        macros.stop_recording()

        macros.start_recording("macro_b")
        macros.record_key(ord('b'))
        macros.record_key(ord('b'))
        macros.record_key(ord('b'))
        macros.stop_recording()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        actions.macro_play("macro_a")
        actions.macro_play("macro_b")
        actions.macro_play("macro_a")

        assert self.mock_ui.handle_keys_calls == [
            (ord('a'), ord('a')),
            (ord('b'), ord('b'), ord('b')),
            (ord('a'), ord('a')),
        ]

    def test_macro_play_parameters_passed_to_handle_keys(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("test")
        macros.record_key(ord('x'))
        macros.record_key(ord('y'))
        macros.record_key(ord('z'))
        macros.stop_recording()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        actions.macro_play("test")

        assert len(self.mock_ui.handle_keys_calls) == 1
        keys_tuple = self.mock_ui.handle_keys_calls[0]
        assert isinstance(keys_tuple, tuple)
        assert len(keys_tuple) == 3
        assert keys_tuple == (ord('x'), ord('y'), ord('z'))

    def test_macro_play_notify_on_success(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = TestableMacros(str(macrofile))

        macros.start_recording("success")
        macros.record_key(ord('a'))
        macros.stop_recording()

        self.mock_fm.macros = macros
        actions = TestableActions()
        actions.fm = self.mock_fm

        result = actions.macro_play("success")

        assert result is True
        assert len(actions.notify_calls) == 0
