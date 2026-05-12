# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

import json
import os
from io import open

from ranger import PY3
from ranger.core.shared import FileManagerAware


class SavedSearch(object):
    STATIC = 'static'
    DYNAMIC = 'dynamic'

    def __init__(self, name, search_type, data):
        self.name = name
        self.type = search_type
        self.data = data

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type,
            'data': self.data,
        }

    @classmethod
    def from_dict(cls, dct):
        return cls(
            name=dct['name'],
            search_type=dct['type'],
            data=dct['data'],
        )


class SavedSearches(FileManagerAware):
    autosave = True

    def __init__(self, searchfile, autosave=False):
        self.autosave = autosave
        self.dct = {}
        self.path = searchfile

    def load(self):
        if self.path is None:
            return
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as fobj:
                data = json.load(fobj)
            for item in data:
                saved_search = SavedSearch.from_dict(item)
                self.dct[saved_search.name] = saved_search
        except (IOError, OSError, ValueError, KeyError) as ex:
            self.fm.notify('Saved searches error: {0}'.format(str(ex)), bad=True)

    def save(self):
        if self.path is None:
            return
        try:
            data = [s.to_dict() for s in self.dct.values()]
            path_new = self.path + '.new'
            with open(path_new, 'w', encoding='utf-8') as fobj:
                json.dump(data, fobj, ensure_ascii=False, indent=2)
            try:
                if os.path.exists(self.path):
                    old_perms = os.stat(self.path)
                    os.chown(path_new, old_perms.st_uid, old_perms.st_gid)
                    os.chmod(path_new, old_perms.st_mode)
                if os.path.islink(self.path):
                    target_path = os.path.realpath(self.path)
                    os.rename(path_new, target_path)
                else:
                    os.rename(path_new, self.path)
            except OSError as ex:
                self.fm.notify('Saved searches error: {0}'.format(str(ex)), bad=True)
                return
        except (IOError, OSError) as ex:
            self.fm.notify('Saved searches error: {0}'.format(str(ex)), bad=True)
            return

    def save_static(self, name, paths):
        saved_search = SavedSearch(
            name=name,
            search_type=SavedSearch.STATIC,
            data={'paths': list(paths)},
        )
        self.dct[name] = saved_search
        if self.autosave:
            self.save()

    def save_dynamic(self, name, command_line):
        saved_search = SavedSearch(
            name=name,
            search_type=SavedSearch.DYNAMIC,
            data={'command': command_line},
        )
        self.dct[name] = saved_search
        if self.autosave:
            self.save()

    def get(self, name):
        return self.dct.get(name)

    def delete(self, name):
        if name in self.dct:
            del self.dct[name]
            if self.autosave:
                self.save()
            return True
        return False

    def list(self):
        return sorted(self.dct.keys())

    def __iter__(self):
        return iter(self.dct.values())
