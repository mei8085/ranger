from __future__ import (absolute_import, division, print_function)

import pytest
from unittest.mock import MagicMock, patch, call

from ranger.container.macros import Macros
from ranger.config.commands import (
    macro_start,
    macro_stop,
    macro_play,
    macro_delete,
    macro_list,
)
from ranger.core.shared import FileManagerAware, SettingsAware


class MacrosContainer(Macros):
    pass


class TestMacroCommands:
    def setup_method(self):
        self.mock_fm = MagicMock()
        self.mock_fm.notify = MagicMock()
        self.mock_fm.ui = MagicMock()
        self.mock_fm.ui.handle_keys = MagicMock()
        self.mock_fm.ui.handle_key = MagicMock()

        self.mock_settings = MagicMock()
        self.mock_settings.__class__ = MagicMock
        self.mock_settings.__getitem__ = MagicMock(return_value=True)

        FileManagerAware.fm_set(self.mock_fm)
        SettingsAware.settings_set(self.mock_settings)

    def teardown_method(self):
        FileManagerAware.fm_set(None)

    def test_macro_start_no_args(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_start = MagicMock(return_value=True)

        cmd = macro_start("macro_start")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_start.assert_not_called()
        self.mock_fm.notify.assert_called_once()
        args, kwargs = self.mock_fm.notify.call_args
        assert "Usage" in args[0]
        assert kwargs.get("bad") is True

    def test_macro_start_with_name(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_start = MagicMock(return_value=True)

        cmd = macro_start("macro_start my_macro")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_start.assert_called_once_with("my_macro")
        self.mock_fm.notify.assert_not_called()

    def test_macro_start_while_recording(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_start = MagicMock(return_value=False)

        cmd = macro_start("macro_start another")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_start.assert_called_once_with("another")

    def test_macro_stop_executes(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_stop = MagicMock(return_value="test")

        cmd = macro_stop("macro_stop")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_stop.assert_called_once()

    def test_macro_stop_no_args_needed(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_stop = MagicMock(return_value="test")

        cmd = macro_stop("macro_stop extra_args_ignored")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_stop.assert_called_once()

    def test_macro_play_no_args(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_play = MagicMock(return_value=True)

        cmd = macro_play("macro_play")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_play.assert_not_called()
        self.mock_fm.notify.assert_called_once()
        args, kwargs = self.mock_fm.notify.call_args
        assert "Usage" in args[0]
        assert kwargs.get("bad") is True

    def test_macro_play_with_name(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_play = MagicMock(return_value=True)

        cmd = macro_play("macro_play my_macro")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_play.assert_called_once_with("my_macro")

    def test_macro_play_nonexistent_macro(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_play = MagicMock(return_value=False)

        cmd = macro_play("macro_play nonexistent")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_play.assert_called_once_with("nonexistent")

    def test_macro_play_while_recording(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        macros.start_recording("test")
        macros.record_key(ord('a'))
        self.mock_fm.macros = macros
        self.mock_fm.macro_play = MagicMock(return_value=False)

        cmd = macro_play("macro_play test")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_play.assert_called_once_with("test")

    def test_macro_delete_no_args(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_delete = MagicMock(return_value=True)

        cmd = macro_delete("macro_delete")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_delete.assert_not_called()
        self.mock_fm.notify.assert_called_once()
        args, kwargs = self.mock_fm.notify.call_args
        assert "Usage" in args[0]
        assert kwargs.get("bad") is True

    def test_macro_delete_with_name(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_delete = MagicMock(return_value=True)

        cmd = macro_delete("macro_delete to_delete")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_delete.assert_called_once_with("to_delete")

    def test_macro_delete_nonexistent(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_delete = MagicMock(return_value=False)

        cmd = macro_delete("macro_delete nonexistent")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_delete.assert_called_once_with("nonexistent")

    def test_macro_list_executes(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_list = MagicMock(return_value=[])

        cmd = macro_list("macro_list")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_list.assert_called_once()

    def test_macro_list_with_extra_args(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros
        self.mock_fm.macro_list = MagicMock(return_value=[])

        cmd = macro_list("macro_list extra_args_ignored")
        cmd.fm = self.mock_fm
        cmd.execute()

        self.mock_fm.macro_list.assert_called_once()

    def test_macro_play_tab_completion_with_macros(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        macros.start_recording("my_macro")
        macros.record_key(ord('a'))
        macros.stop_recording()
        macros.start_recording("another_macro")
        macros.record_key(ord('b'))
        macros.stop_recording()
        self.mock_fm.macros = macros

        cmd = macro_play("macro_play ")
        cmd.fm = self.mock_fm
        completions = cmd.tab(1)

        assert completions is not None
        completion_list = list(completions)
        assert "macro_play another_macro" in completion_list
        assert "macro_play my_macro" in completion_list

    def test_macro_play_tab_completion_with_prefix(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        macros.start_recording("alpha")
        macros.record_key(ord('a'))
        macros.stop_recording()
        macros.start_recording("beta")
        macros.record_key(ord('b'))
        macros.stop_recording()
        macros.start_recording("alice")
        macros.record_key(ord('c'))
        macros.stop_recording()
        self.mock_fm.macros = macros

        cmd = macro_play("macro_play al")
        cmd.fm = self.mock_fm
        completions = cmd.tab(1)

        assert completions is not None
        completion_list = list(completions)
        assert "macro_play alice" in completion_list
        assert "macro_play alpha" in completion_list
        assert "macro_play beta" not in completion_list

    def test_macro_play_tab_completion_no_macros(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros

        cmd = macro_play("macro_play ")
        cmd.fm = self.mock_fm
        completions = cmd.tab(1)

        assert list(completions) == []

    def test_macro_delete_tab_completion(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        macros.start_recording("to_delete")
        macros.record_key(ord('a'))
        macros.stop_recording()
        macros.start_recording("keep")
        macros.record_key(ord('b'))
        macros.stop_recording()
        self.mock_fm.macros = macros

        cmd = macro_delete("macro_delete to")
        cmd.fm = self.mock_fm
        completions = cmd.tab(1)

        assert completions is not None
        completion_list = list(completions)
        assert "macro_delete to_delete" in completion_list
        assert "macro_delete keep" not in completion_list

    def test_macro_start_error_message_format(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros

        cmd = macro_start("macro_start")
        cmd.fm = self.mock_fm
        cmd.execute()

        call_args = self.mock_fm.notify.call_args
        message = call_args[0][0]
        assert "macro_start" in message.lower()
        assert "<name>" in message

    def test_macro_play_error_message_format(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros

        cmd = macro_play("macro_play")
        cmd.fm = self.mock_fm
        cmd.execute()

        call_args = self.mock_fm.notify.call_args
        message = call_args[0][0]
        assert "macro_play" in message.lower()
        assert "<name>" in message

    def test_macro_delete_error_message_format(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros

        cmd = macro_delete("macro_delete")
        cmd.fm = self.mock_fm
        cmd.execute()

        call_args = self.mock_fm.notify.call_args
        message = call_args[0][0]
        assert "macro_delete" in message.lower()
        assert "<name>" in message

    def test_command_to_actions_mapping(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        macros = MacrosContainer(str(macrofile))
        self.mock_fm.macros = macros

        self.mock_fm.macro_start = MagicMock(return_value=True)
        self.mock_fm.macro_stop = MagicMock(return_value="test")
        self.mock_fm.macro_play = MagicMock(return_value=True)
        self.mock_fm.macro_delete = MagicMock(return_value=True)
        self.mock_fm.macro_list = MagicMock(return_value=[])

        macro_start("macro_start test", quantifier=1).execute()
        self.mock_fm.macro_start.assert_called_once_with("test")

        macro_stop("macro_stop").execute()
        self.mock_fm.macro_stop.assert_called_once()

        macro_play("macro_play test").execute()
        self.mock_fm.macro_play.assert_called_once_with("test")

        macro_delete("macro_delete test").execute()
        self.mock_fm.macro_delete.assert_called_once_with("test")

        macro_list("macro_list").execute()
        self.mock_fm.macro_list.assert_called_once()


class TestMacroCommandFullFlow:
    def setup_method(self):
        self.notify_calls = []
        self.handle_keys_calls = []
        self.handle_key_calls = []

    def teardown_method(self):
        FileManagerAware.fm_set(None)

    def _create_fm_and_macros(self, macrofile):
        from ranger.core.actions import Actions

        notify_calls = []
        handle_keys_calls = []
        handle_key_calls = []

        class TestableUI:
            def __init__(self):
                self.handle_keys_calls = []
                self.handle_key_calls = []

            def handle_keys(self, *keys):
                self.handle_keys_calls.append(keys)
                for key in keys:
                    self.handle_key_calls.append(key)

            def handle_key(self, key):
                pass

        class TestableFM(Actions):
            def __init__(self):
                self.ui = TestableUI()
                self._notify_calls = []

            def notify(self, message, bad=False):
                self._notify_calls.append((message, bad))

        test_fm = TestableFM()
        macros = MacrosContainer(str(macrofile))
        test_fm.macros = macros
        FileManagerAware.fm_set(test_fm)

        return test_fm, macros, notify_calls, handle_keys_calls, handle_key_calls

    def test_macro_play_calls_handle_keys(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        test_fm, macros, nc, hkc, hkc2 = self._create_fm_and_macros(macrofile)

        macros.start_recording("test_macro")
        macros.record_key(ord('j'))
        macros.record_key(ord('k'))
        macros.record_key(ord('j'))
        macros.stop_recording()

        cmd = macro_play("macro_play test_macro")
        cmd.fm = test_fm
        cmd.execute()

        assert len(test_fm.ui.handle_keys_calls) == 1
        assert test_fm.ui.handle_keys_calls[0] == (ord('j'), ord('k'), ord('j'))

    def test_full_command_flow_record_and_play(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        test_fm, macros, nc, hkc, hkc2 = self._create_fm_and_macros(macrofile)

        start_cmd = macro_start("macro_start workflow")
        start_cmd.fm = test_fm
        start_cmd.execute()

        macros.record_key(ord('j'))
        macros.record_key(ord('j'))
        macros.record_key(ord('j'))

        stop_cmd = macro_stop("macro_stop")
        stop_cmd.fm = test_fm
        stop_cmd.execute()

        play_cmd = macro_play("macro_play workflow")
        play_cmd.fm = test_fm
        play_cmd.execute()

        assert len(test_fm.ui.handle_keys_calls) == 1
        assert test_fm.ui.handle_keys_calls[0] == (ord('j'), ord('j'), ord('j'))

    def test_full_command_flow_delete_macro(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        test_fm, macros, nc, hkc, hkc2 = self._create_fm_and_macros(macrofile)

        start_cmd = macro_start("macro_start temp")
        start_cmd.fm = test_fm
        start_cmd.execute()
        macros.record_key(ord('a'))

        stop_cmd = macro_stop("macro_stop")
        stop_cmd.fm = test_fm
        stop_cmd.execute()

        assert "temp" in macros

        delete_cmd = macro_delete("macro_delete temp")
        delete_cmd.fm = test_fm
        delete_cmd.execute()

        assert "temp" not in macros

    def test_command_error_when_not_recording(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        test_fm, macros, nc, hkc, hkc2 = self._create_fm_and_macros(macrofile)

        cmd = macro_stop("macro_stop")
        cmd.fm = test_fm
        cmd.execute()

        assert len(test_fm._notify_calls) == 1
        assert "not recording" in test_fm._notify_calls[0][0].lower()
        assert test_fm._notify_calls[0][1] is True

    def test_command_success_notification(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        test_fm, macros, nc, hkc, hkc2 = self._create_fm_and_macros(macrofile)

        start_cmd = macro_start("macro_start test")
        start_cmd.fm = test_fm
        start_cmd.execute()

        assert len(test_fm._notify_calls) == 1
        assert "recording" in test_fm._notify_calls[0][0].lower()
        assert "test" in test_fm._notify_calls[0][0]
        assert test_fm._notify_calls[0][1] is False

        macros.record_key(ord('a'))

        stop_cmd = macro_stop("macro_stop")
        stop_cmd.fm = test_fm
        stop_cmd.execute()

        assert len(test_fm._notify_calls) == 2
        assert "saved" in test_fm._notify_calls[1][0].lower()
        assert "test" in test_fm._notify_calls[1][0]
        assert test_fm._notify_calls[1][1] is False

    def test_command_nested_recording_error(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        test_fm, macros, nc, hkc, hkc2 = self._create_fm_and_macros(macrofile)

        cmd1 = macro_start("macro_start first")
        cmd1.fm = test_fm
        cmd1.execute()

        cmd2 = macro_start("macro_start second")
        cmd2.fm = test_fm
        cmd2.execute()

        assert len(test_fm._notify_calls) == 2
        assert "already recording" in test_fm._notify_calls[1][0].lower()
        assert test_fm._notify_calls[1][1] is True

    def test_command_list_with_macros(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        test_fm, macros, nc, hkc, hkc2 = self._create_fm_and_macros(macrofile)

        macros.start_recording("macro1")
        macros.record_key(ord('a'))
        macros.stop_recording()
        macros.start_recording("macro2")
        macros.record_key(ord('b'))
        macros.stop_recording()

        cmd = macro_list("macro_list")
        cmd.fm = test_fm
        cmd.execute()

        assert len(test_fm._notify_calls) == 1
        assert "macro1" in test_fm._notify_calls[0][0]
        assert "macro2" in test_fm._notify_calls[0][0]

    def test_command_list_empty(self, tmpdir):
        macrofile = tmpdir.join("macros.json")
        test_fm, macros, nc, hkc, hkc2 = self._create_fm_and_macros(macrofile)

        cmd = macro_list("macro_list")
        cmd.fm = test_fm
        cmd.execute()

        assert len(test_fm._notify_calls) == 1
        assert "no macros" in test_fm._notify_calls[0][0].lower()
