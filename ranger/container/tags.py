# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

# TODO: add a __getitem__ method to get the tag of a file

from __future__ import (absolute_import, division, print_function)

import copy
import os
import string
from io import open
from os.path import exists, abspath, realpath, expanduser, sep

from ranger.core.shared import FileManagerAware

ALLOWED_KEYS = string.ascii_letters + string.digits + string.punctuation


class Tags(FileManagerAware):
    default_tag = '*'
    last_mtime = None

    def __init__(self, filename):

        # COMPAT: The intent is to get abspath/normpath's behavior of
        # collapsing `symlink/..`, abspath is retained for historical reasons
        # because the documentation states its behavior isn't necessarily in
        # line with normpath's.
        self._filename = realpath(abspath(expanduser(filename)))
        self.original_tags = {}

        self.sync()

    def __contains__(self, item):
        return item in self.tags

    def add(self, *items, **others):
        if len(items) == 0:
            return
        tag = others.get('tag', self.default_tag)
        self.update_if_outdated()
        for item in items:
            self.tags[item] = tag
        self.dump()

    def remove(self, *items):
        if len(items) == 0:
            return
        self.update_if_outdated()
        for item in items:
            try:
                del self.tags[item]
            except KeyError:
                pass
        self.dump()

    def toggle(self, *items, **others):
        if len(items) == 0:
            return
        tag = others.get('tag', self.default_tag)
        tag = str(tag)
        if tag not in ALLOWED_KEYS:
            return
        self.update_if_outdated()
        for item in items:
            try:
                if item in self and tag in (self.tags[item], self.default_tag):
                    del self.tags[item]
                else:
                    self.tags[item] = tag
            except KeyError:
                pass
        self.dump()

    def marker(self, item):
        if item in self.tags:
            return self.tags[item]
        return self.default_tag

    def sync(self):
        tags_dict = self._load_dict()
        self.tags = tags_dict
        self.original_tags = copy.deepcopy(tags_dict)
        self._update_mtime()

    def update_if_outdated(self):
        if self.last_mtime != self._get_mtime():
            self.update()

    def update(self):
        real_tags = self._load_dict()
        real_tags_copy = copy.deepcopy(real_tags)

        for path in set(self.tags) | set(real_tags):
            if path in self.tags:
                current = self.tags[path]
            else:
                current = None

            if path in self.original_tags:
                original = self.original_tags[path]
            else:
                original = None

            if path in real_tags:
                real = real_tags[path]
            else:
                real = None

            if current == original and current != real:
                continue

            if path not in self.tags:
                del real_tags[path]
            else:
                real_tags[path] = current

        self.tags = real_tags
        self.original_tags = real_tags_copy
        self._update_mtime()

    def dump(self):
        path_new = self._filename + '.new'
        try:
            with open(path_new, 'w', encoding="utf-8") as fobj:
                self._compile(fobj)
        except OSError as err:
            self.fm.notify(err, bad=True)
            return

        try:
            if exists(self._filename):
                old_perms = os.stat(self._filename)
                try:
                    os.chown(path_new, old_perms.st_uid, old_perms.st_gid)
                except (OSError, AttributeError):
                    pass
                try:
                    os.chmod(path_new, old_perms.st_mode)
                except OSError:
                    pass

                if os.path.islink(self._filename):
                    target_path = os.path.realpath(self._filename)
                    os.replace(path_new, target_path)
                else:
                    os.replace(path_new, self._filename)
            else:
                os.rename(path_new, self._filename)

        except OSError as err:
            self.fm.notify(err, bad=True)
            return

        self.original_tags = copy.deepcopy(self.tags)
        self._update_mtime()

    def _load_dict(self):
        try:
            with open(
                self._filename, "r", encoding="utf-8", errors="replace"
            ) as fobj:
                tags = self._parse(fobj)
        except (OSError, IOError) as err:
            if exists(self._filename):
                self.fm.notify(err, bad=True)
            tags = {}

        return tags

    def _compile(self, fobj):
        for path, tag in self.tags.items():
            if tag == self.default_tag:
                # COMPAT: keep the old format if the default tag is used
                fobj.write(path + '\n')
            elif tag in ALLOWED_KEYS:
                fobj.write('{0}:{1}\n'.format(tag, path))

    def _parse(self, fobj):
        result = {}
        for line in fobj:
            line = line.rstrip('\n')
            if len(line) > 2 and line[1] == ':':
                tag, path = line[0], line[2:]
                if tag in ALLOWED_KEYS:
                    result[path] = tag
            else:
                result[line] = self.default_tag

        return result

    def _get_mtime(self):
        try:
            return os.stat(self._filename).st_mtime
        except (OSError, FileNotFoundError):
            return None

    def _update_mtime(self):
        self.last_mtime = self._get_mtime()

    def update_path(self, path_old, path_new):
        self.update_if_outdated()
        changed = False
        items = list(self.tags.items())
        for path, tag in items:
            pnew = None
            if path == path_old:
                pnew = path_new
            elif path.startswith(path_old + sep):
                pnew = path_new + path[len(path_old):]
            if pnew:
                # pylint: disable=unnecessary-dict-index-lookup
                del self.tags[path]
                self.tags[pnew] = tag
                changed = True
        if changed:
            self.dump()

    def __nonzero__(self):
        return True
    __bool__ = __nonzero__


class TagsDummy(Tags):
    """A dummy Tags class for use with `ranger --clean`.

    It acts like there are no tags and avoids writing any changes.
    """

    def __init__(self, filename):  # pylint: disable=super-init-not-called
        self.tags = {}

    def __contains__(self, item):
        return False

    def add(self, *items, **others):
        pass

    def remove(self, *items):
        pass

    def toggle(self, *items, **others):
        pass

    def marker(self, item):
        return self.default_tag

    def sync(self):
        pass

    def update_if_outdated(self):
        pass

    def update(self):
        pass

    def dump(self):
        pass

    def _compile(self, fobj):
        pass

    def _parse(self, fobj):
        pass
