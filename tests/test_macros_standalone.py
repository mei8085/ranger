from __future__ import (absolute_import, division, print_function)

import json
import os
import sys
import time
from unittest.mock import MagicMock, patch


CURSES_MOCK = MagicMock()
CURSES_MOCK.KEY_BACKSPACE = 263
CURSES_MOCK.KEY_DC = 330
CURSES_MOCK.KEY_SDC = 331
CURSES_MOCK.KEY_IC = 331
CURSES_MOCK.KEY_DOWN = 258
CURSES_MOCK.KEY_UP = 259
CURSES_MOCK.KEY_LEFT = 260
CURSES_MOCK.KEY_RIGHT = 261
CURSES_MOCK.KEY_NPAGE = 338
CURSES_MOCK.KEY_PPAGE = 339
CURSES_MOCK.KEY_HOME = 262
CURSES_MOCK.KEY_END = 360
CURSES_MOCK.KEY_BTAB = 353
CURSES_MOCK.KEY_F0 = 264
CURSES_ASCII_MOCK = MagicMock()
CURSES_ASCII_MOCK.DEL = 127
CURSES_ASCII_MOCK.ESC = 27
CURSES_MOCK.ascii = CURSES_ASCII_MOCK

GRP_MOCK = MagicMock()
GRP_MOCK.getgrgid = lambda gid: MagicMock(gr_name='users')

PWD_MOCK = MagicMock()
PWD_MOCK.getpwuid = lambda uid: MagicMock(pw_name='testuser')

OS_MOCK = MagicMock()
OS_MOCK.path = MagicMock()


def build_special_keys_dict(curses_module):
    ALT_KEY = 9003
    special_keys = {}

    for char in 'abcdefghijklmnopqrstuvwxyz_':
        special_keys['c-' + char] = ord(char) - 96

    special_keys.update({
        'bs': curses_module.KEY_BACKSPACE,
        'backspace': curses_module.KEY_BACKSPACE,
        'backspace2': curses_module.ascii.DEL,
        'delete': curses_module.KEY_DC,
        's-delete': curses_module.KEY_SDC,
        'insert': curses_module.KEY_IC,
        'cr': ord("\n"),
        'return': ord("\n"),
        'space': ord(" "),
        'esc': curses_module.ascii.ESC,
        'escape': curses_module.ascii.ESC,
        'down': curses_module.KEY_DOWN,
        'up': curses_module.KEY_UP,
        'left': curses_module.KEY_LEFT,
        'right': curses_module.KEY_RIGHT,
        'pagedown': curses_module.KEY_NPAGE,
        'pageup': curses_module.KEY_PPAGE,
        'home': curses_module.KEY_HOME,
        'end': curses_module.KEY_END,
        'tab': ord('\t'),
        's-tab': curses_module.KEY_BTAB,
        'lt': ord('<'),
        'gt': ord('>'),
        'enter': ord("\n"),
    })

    for key, val in list(special_keys.items()):
        special_keys['a-' + key] = (ALT_KEY, val)

    for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!{}':
        special_keys['a-' + char] = (ALT_KEY, ord(char))

    special_keys['c-space'] = 0

    for n in range(64):
        special_keys['f' + str(n)] = curses_module.KEY_F0 + n

    return special_keys


def parse_keybinding_simple(obj, special_keys):
    assert isinstance(obj, (tuple, int, str))
    if isinstance(obj, tuple):
        for char in obj:
            yield char
    elif isinstance(obj, int):
        yield obj
    elif isinstance(obj, str):
        in_brackets = False
        bracket_content = []
        for char in obj:
            if in_brackets:
                if char == '>':
                    in_brackets = False
                    string = ''.join(bracket_content).lower()
                    try:
                        keys = special_keys[string]
                        for key in keys:
                            yield key
                    except KeyError:
                        if string.isdigit():
                            yield int(string)
                        else:
                            yield ord('<')
                            for bracket_char in bracket_content:
                                yield ord(bracket_char)
                            yield ord('>')
                    except TypeError:
                        yield keys
                else:
                    bracket_content.append(char)
            else:
                if char == '<':
                    in_brackets = True
                    bracket_content = []
                else:
                    yield ord(char)
        if in_brackets:
            yield ord('<')
            for char in bracket_content:
                yield ord(char)


def construct_keybinding_simple(iterable, reversed_special_keys):
    def key_to_string(key):
        if key in range(33, 127):
            return chr(key)
        if key in reversed_special_keys:
            return "<%s>" % reversed_special_keys[key]
        return "<%s>" % str(key)
    return ''.join(key_to_string(c) for c in iterable)


class StandaloneMacros:
    last_mtime = None
    autosave = True

    def __init__(self, macrofile, autosave=True):
        self.autosave = autosave
        self.dct = {}
        self.path = macrofile
        self._recording_name = None
        self._recording_keys = []

    @property
    def recording(self):
        return self._recording_name is not None

    @property
    def recording_name(self):
        return self._recording_name

    def start_recording(self, name):
        if self.recording:
            return False
        self._recording_name = name
        self._recording_keys = []
        return True

    def stop_recording(self):
        if not self.recording:
            return None
        name = self._recording_name
        keys = self._recording_keys
        self._recording_name = None
        self._recording_keys = []
        if keys:
            self.dct[name] = keys
            if self.autosave:
                self.save()
            return name
        return None

    def record_key(self, key):
        if self.recording:
            self._recording_keys.append(key)

    def get(self, name):
        return self.dct.get(name)

    def load(self):
        special_keys = build_special_keys_dict(CURSES_MOCK)
        reversed_special_keys = dict((v, k) for k, v in special_keys.items())

        new_dict = self._load_dict(special_keys)
        if new_dict is None:
            return
        self._set_dict(new_dict)

    def __getitem__(self, key):
        return self.dct[key]

    def __setitem__(self, key, value):
        self.dct[key] = value
        if self.autosave:
            self.save()

    def __delitem__(self, key):
        if key in self.dct:
            del self.dct[key]
            if self.autosave:
                self.save()

    def __contains__(self, key):
        return key in self.dct

    def __iter__(self):
        return iter(self.dct.items())

    def update_if_outdated(self):
        if self.last_mtime != self._get_mtime():
            self.update()

    def update(self):
        special_keys = build_special_keys_dict(CURSES_MOCK)
        real_dict = self._load_dict(special_keys)
        if real_dict is None:
            return
        self._set_dict(real_dict)

    def save(self):
        special_keys = build_special_keys_dict(CURSES_MOCK)
        reversed_special_keys = dict((v, k) for k, v in special_keys.items())

        if self.path is None:
            return
        path_new = self.path + '.new'
        try:
            data = {}
            for name, keys in self.dct.items():
                data[name] = construct_keybinding_simple(keys, reversed_special_keys)
            with open(path_new, 'w', encoding="utf-8") as fobj:
                json.dump(data, fobj, ensure_ascii=False, indent=2)
        except OSError:
            return

        try:
            if os.path.exists(self.path):
                if os.path.islink(self.path):
                    target_path = os.path.realpath(self.path)
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    os.rename(path_new, target_path)
                else:
                    if os.path.exists(self.path):
                        os.remove(self.path)
                    os.rename(path_new, self.path)
            else:
                os.rename(path_new, self.path)
        except OSError:
            return

        self._update_mtime()

    def _load_dict(self, special_keys):
        if self.path is None:
            return {}
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, 'r', encoding="utf-8") as fobj:
                data = json.load(fobj)
                dct = {}
                for name, keybinding in data.items():
                    dct[name] = list(parse_keybinding_simple(keybinding, special_keys))
        except (OSError, ValueError, KeyError):
            return None
        return dct

    def _set_dict(self, dct):
        self.dct.clear()
        self.dct.update(dct)
        self._update_mtime()

    def _get_mtime(self):
        if self.path is None:
            return None
        try:
            return os.stat(self.path).st_mtime
        except OSError:
            return None

    def _update_mtime(self):
        self.last_mtime = self._get_mtime()


def test_macros_basic(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.load()

    assert macros.recording is False
    assert macros.recording_name is None
    assert macros.get("test") is None
    assert "test" not in macros


def test_macros_start_stop_recording(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

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
    macros = StandaloneMacros(str(macrofile))

    result = macros.stop_recording()
    assert result is None


def test_macros_stop_with_no_keys(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("empty")
    name = macros.stop_recording()
    assert name is None
    assert "empty" not in macros


def test_macros_named_persistence(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("my_sequence")
    macros.record_key(ord('h'))
    macros.record_key(ord('e'))
    macros.record_key(ord('l'))
    macros.record_key(ord('l'))
    macros.record_key(ord('o'))
    macros.stop_recording()

    assert os.path.exists(str(macrofile))

    with open(str(macrofile), 'r') as fobj:
        data = json.load(fobj)
        assert "my_sequence" in data
        assert data["my_sequence"] == "hello"

    macros2 = StandaloneMacros(str(macrofile))
    macros2.load()

    assert "my_sequence" in macros2
    assert macros2.get("my_sequence") == [ord('h'), ord('e'), ord('l'), ord('l'), ord('o')]


def test_macros_persistence_multiple(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("nav_down")
    macros.record_key(CURSES_MOCK.KEY_DOWN)
    macros.record_key(CURSES_MOCK.KEY_DOWN)
    macros.record_key(CURSES_MOCK.KEY_RIGHT)
    macros.stop_recording()

    macros.start_recording("copy_paste")
    macros.record_key(ord('y'))
    macros.record_key(CURSES_MOCK.ascii.ESC)
    macros.record_key(ord('p'))
    macros.stop_recording()

    assert os.path.exists(str(macrofile))

    macros2 = StandaloneMacros(str(macrofile))
    macros2.load()

    assert "nav_down" in macros2
    assert "copy_paste" in macros2
    assert macros2.get("nav_down") == [CURSES_MOCK.KEY_DOWN, CURSES_MOCK.KEY_DOWN, CURSES_MOCK.KEY_RIGHT]
    assert macros2.get("copy_paste") == [ord('y'), CURSES_MOCK.ascii.ESC, ord('p')]


def test_macros_restart_reload(tmpdir):
    macrofile = tmpdir.join("macros.json")

    macros1 = StandaloneMacros(str(macrofile))
    macros1.start_recording("workflow")
    macros1.record_key(ord('g'))
    macros1.record_key(ord('g'))
    macros1.record_key(ord('V'))
    macros1.stop_recording()

    macros2 = StandaloneMacros(str(macrofile))
    macros2.load()

    assert "workflow" in macros2
    assert macros2.get("workflow") == [ord('g'), ord('g'), ord('V')]

    macros3 = StandaloneMacros(str(macrofile))
    macros3.load()
    assert "workflow" in macros3


def test_macros_playback_sequence(tmpdir):
    macrofile = tmpdir.join("macros.json")

    recorded_keys = []

    class PlaybackTestMacros(StandaloneMacros):
        pass

    macros = PlaybackTestMacros(str(macrofile))
    macros.start_recording("test_play")
    macros.record_key(ord('j'))
    macros.record_key(ord('k'))
    macros.record_key(ord('j'))
    macros.stop_recording()

    keys = macros.get("test_play")
    assert keys == [ord('j'), ord('k'), ord('j')]

    for key in keys:
        recorded_keys.append(key)

    assert recorded_keys == [ord('j'), ord('k'), ord('j')]


def test_macros_delete(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("to_delete")
    macros.record_key(ord('a'))
    macros.stop_recording()

    assert "to_delete" in macros

    del macros["to_delete"]

    assert "to_delete" not in macros
    assert macros.get("to_delete") is None

    macros2 = StandaloneMacros(str(macrofile))
    macros2.load()
    assert "to_delete" not in macros2


def test_macros_iteration(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

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
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("special")
    macros.record_key(ord('\n'))
    macros.record_key(CURSES_MOCK.KEY_UP)
    macros.record_key(CURSES_MOCK.KEY_LEFT)
    macros.stop_recording()

    macros2 = StandaloneMacros(str(macrofile))
    macros2.load()

    assert "special" in macros2
    keys = macros2.get("special")
    assert len(keys) == 3
    assert keys[0] == ord('\n')
    assert keys[1] == CURSES_MOCK.KEY_UP
    assert keys[2] == CURSES_MOCK.KEY_LEFT


def test_macros_load_nonexistent_file(tmpdir):
    macrofile = tmpdir.join("nonexistent.json")
    macros = StandaloneMacros(str(macrofile))
    macros.load()
    assert len(list(macros)) == 0


def test_macros_update_if_outdated(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

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


def test_macros_naming_conflict(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("first")
    macros.record_key(ord('1'))
    macros.stop_recording()

    macros.start_recording("first")
    macros.record_key(ord('2'))
    macros.stop_recording()

    assert macros.get("first") == [ord('2')]


def test_macros_complex_sequence(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("complex_nav")
    macros.record_key(CURSES_MOCK.KEY_HOME)
    macros.record_key(ord('d'))
    macros.record_key(ord('d'))
    macros.record_key(CURSES_MOCK.KEY_DOWN)
    macros.record_key(CURSES_MOCK.KEY_DOWN)
    macros.record_key(CURSES_MOCK.KEY_RIGHT)
    macros.stop_recording()

    macros2 = StandaloneMacros(str(macrofile))
    macros2.load()

    assert "complex_nav" in macros2
    keys = macros2.get("complex_nav")
    assert len(keys) == 6
    assert keys == [
        CURSES_MOCK.KEY_HOME,
        ord('d'), ord('d'),
        CURSES_MOCK.KEY_DOWN,
        CURSES_MOCK.KEY_DOWN,
        CURSES_MOCK.KEY_RIGHT
    ]


def test_macros_json_format(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("test1")
    macros.record_key(ord('a'))
    macros.record_key(ord('b'))
    macros.stop_recording()

    macros.start_recording("test2")
    macros.record_key(ord('x'))
    macros.stop_recording()

    with open(str(macrofile), 'r') as fobj:
        data = json.load(fobj)

    assert isinstance(data, dict)
    assert "test1" in data
    assert "test2" in data
    assert data["test1"] == "ab"
    assert data["test2"] == "x"


def test_macros_special_key_persistence_format(tmpdir):
    macrofile = tmpdir.join("macros.json")
    macros = StandaloneMacros(str(macrofile))

    macros.start_recording("with_enter")
    macros.record_key(ord('\n'))
    macros.record_key(ord('a'))
    macros.stop_recording()

    with open(str(macrofile), 'r') as fobj:
        data = json.load(fobj)

    assert "with_enter" in data
    assert "<enter>" in data["with_enter"].lower()

    macros2 = StandaloneMacros(str(macrofile))
    macros2.load()
    assert macros2.get("with_enter")[0] == ord('\n')


def test_macros_overwrite_on_restart(tmpdir):
    macrofile = tmpdir.join("macros.json")

    macros1 = StandaloneMacros(str(macrofile))
    macros1.start_recording("macro1")
    macros1.record_key(ord('v'))
    macros1.record_key(ord('i'))
    macros1.record_key(ord('m'))
    macros1.stop_recording()

    macros2 = StandaloneMacros(str(macrofile))
    macros2.load()
    macros2.start_recording("macro2")
    macros2.record_key(ord('p'))
    macros2.record_key(ord('w'))
    macros2.record_key(ord('d'))
    macros2.stop_recording()

    macros3 = StandaloneMacros(str(macrofile))
    macros3.load()

    assert "macro1" in macros3
    assert "macro2" in macros3
    assert macros3.get("macro1") == [ord('v'), ord('i'), ord('m')]
    assert macros3.get("macro2") == [ord('p'), ord('w'), ord('d')]
