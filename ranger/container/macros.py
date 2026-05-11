# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

import json
import os
from io import open

from ranger import PY3
from ranger.core.shared import FileManagerAware
from ranger.ext.keybinding_parser import parse_keybinding, construct_keybinding


class Macros(FileManagerAware):

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
        new_dict = self._load_dict()
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
        real_dict = self._load_dict()
        if real_dict is None:
            return
        self._set_dict(real_dict)

    def _notify(self, message, bad=False):
        fm = getattr(self, 'fm', None)
        if fm is not None:
            fm.notify(message, bad=bad)

    def save(self):
        if self.path is None:
            return
        path_new = self.path + '.new'
        try:
            data = {}
            for name, keys in self.dct.items():
                data[name] = construct_keybinding(keys)
            with open(path_new, 'w', encoding="utf-8") as fobj:
                json.dump(data, fobj, ensure_ascii=False, indent=2)
        except OSError as ex:
            self._notify('Macros error: {0}'.format(str(ex)), bad=True)
            return

        try:
            target_path = None
            if os.path.islink(self.path):
                target_path = os.path.realpath(self.path)
            elif os.path.lexists(self.path):
                old_perms = os.stat(self.path)
                try:
                    os.chown(path_new, old_perms.st_uid, old_perms.st_gid)
                except (AttributeError, OSError):
                    pass
                try:
                    os.chmod(path_new, old_perms.st_mode)
                except OSError:
                    pass

            if target_path is not None:
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.rename(path_new, target_path)
            else:
                if os.path.exists(self.path):
                    os.remove(self.path)
                os.rename(path_new, self.path)
        except OSError as ex:
            self._notify('Macros error: {0}'.format(str(ex)), bad=True)
            return

        self._update_mtime()

    def _load_dict(self):
        if self.path is None:
            return {}
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, 'r', encoding="utf-8") as fobj:
                data = json.load(fobj)
                dct = {}
                for name, keybinding in data.items():
                    dct[name] = list(parse_keybinding(keybinding))
        except (OSError, ValueError, KeyError) as ex:
            self._notify('Macros error: {0}'.format(str(ex)), bad=True)
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
