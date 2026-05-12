# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

import string
import re
import os
from io import open

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from ranger import PY3
from ranger.container import fsobject
from ranger.core.shared import FileManagerAware

ALLOWED_KEYS = string.ascii_letters + string.digits + "`'"
DEFAULT_GROUP = 'default'


class Bookmarks(FileManagerAware):
    """Bookmarks is a container which associates keys with bookmarks.

    A key is a string with: len(key) == 1 and key in ALLOWED_KEYS.

    A bookmark is an object with: bookmark == bookmarktype(str(instance))
    Which is true for str or FileSystemObject. This condition is required
    so bookmark-objects can be saved to and loaded from a file.

    Optionally, a bookmark.go() method is used for entering a bookmark.
    """

    last_mtime = None
    autosave = True
    load_pattern = re.compile(r"^[\d\w']:.")

    def __init__(self, bookmarkfile, bookmarktype=str, autosave=False,
                 nonpersistent_bookmarks=()):
        """Initializes Bookmarks.

        <bookmarkfile> specifies the path to the file where
        bookmarks are saved in.
        """
        self.autosave = autosave
        self.dct = {}
        self.groups = {DEFAULT_GROUP: set()}
        self.original_dict = {}
        self.original_groups = {DEFAULT_GROUP: set()}
        self.path = bookmarkfile
        self.bookmarktype = bookmarktype
        self.nonpersistent_bookmarks = set(nonpersistent_bookmarks)

    def load(self):
        """Load the bookmarks from path/bookmarks"""
        result = self._load_dict()
        if result is None or result[0] is None:
            return
        new_dict, new_groups = result
        self._set_dict(new_dict, original=new_dict, groups=new_groups, original_groups=new_groups)

    def enter(self, key):
        """Enter the bookmark with the given key.

        Requires the bookmark instance to have a go() method.
        """

        try:
            return self[key].go()
        except (IndexError, KeyError, AttributeError):
            return False

    def update_if_outdated(self):
        if self.last_mtime != self._get_mtime():
            self.update()

    def remember(self, value):
        """Bookmarks <value> to the key '"""
        self["'"] = value
        if self.autosave:
            self.save()

    def __delitem__(self, key):
        """Delete the bookmark with the given key"""
        if key == '`':
            key = "'"
        if key in self.dct:
            del self.dct[key]
            for group in self.groups:
                if key in self.groups[group]:
                    self.groups[group].remove(key)
                    break
            if self.autosave:
                self.save()

    def __iter__(self):
        return iter(self.dct.items())

    def __getitem__(self, key):
        """Get the bookmark associated with the key"""
        if key == '`':
            key = "'"
        if key in self.dct:
            value = self.dct[key]
            if self._validate(value):
                return value
            else:
                raise KeyError("Cannot open bookmark: `%s'!" % key)
        else:
            raise KeyError("Nonexistent Bookmark: `%s'!" % key)

    def __setitem__(self, key, value):
        """Bookmark <value> to the key <key>.

        key is expected to be a 1-character string and element of ALLOWED_KEYS.
        value is expected to be a filesystemobject.
        """
        if key == '`':
            key = "'"
        if key in ALLOWED_KEYS:
            self.dct[key] = value
            if key not in self.groups[DEFAULT_GROUP]:
                for group in self.groups:
                    if key in self.groups[group]:
                        break
                else:
                    self.groups[DEFAULT_GROUP].add(key)
            if self.autosave:
                self.save()

    def __contains__(self, key):
        """Test whether a bookmark-key is defined"""
        return key in self.dct

    def update_path(self, path_old, file_new):
        """Update bookmarks containing path"""
        self.update_if_outdated()
        changed = False
        for key, bfile in self:
            if bfile.path == path_old:
                self.dct[key] = file_new
                changed = True
            elif bfile.path.startswith(path_old + os.path.sep):
                self.dct[key] = self.bookmarktype(file_new.path + bfile.path[len(path_old):])
                changed = True
        if changed:
            self.save()

    def update(self):
        """Update the bookmarks from the bookmark file.

        Useful if two instances are running which define different bookmarks.
        """
        result = self._load_dict()
        if result is None or result[0] is None:
            return
        real_dict, real_groups = result
        real_dict_copy = real_dict.copy()
        real_groups_copy = {g: set(ks) for g, ks in real_groups.items()}

        for key in set(self.dct) | set(real_dict):
            # set some variables
            if key in self.dct:
                current = self.dct[key]
            else:
                current = None

            if key in self.original_dict:
                original = self.original_dict[key]
            else:
                original = None

            if key in real_dict:
                real = real_dict[key]
            else:
                real = None

            # determine if there have been changes
            if current == original and current != real:
                continue   # another ranger instance has changed the bookmark

            if key not in self.dct:
                del real_dict[key]   # the user has deleted it
                for group in real_groups:
                    real_groups[group].discard(key)
            else:
                real_dict[key] = current   # the user has changed it

        merged_groups = {}
        all_keys = set(real_dict.keys())
        for group_name in set(self.groups.keys()) | set(real_groups.keys()):
            merged_groups[group_name] = set()

        for group_name in merged_groups:
            current_keys = self.groups.get(group_name, set())
            real_keys = real_groups.get(group_name, set())
            for key in current_keys:
                if key in all_keys:
                    merged_groups[group_name].add(key)
            for key in real_keys:
                if key in all_keys and key not in merged_groups[group_name]:
                    merged_groups[group_name].add(key)

        for key in all_keys:
            found = False
            for group in merged_groups:
                if key in merged_groups[group]:
                    found = True
                    break
            if not found:
                merged_groups[DEFAULT_GROUP].add(key)

        self._set_dict(real_dict, original=real_dict_copy,
                       groups=merged_groups, original_groups=real_groups_copy)

    def save(self):
        """Save the bookmarks to the bookmarkfile.

        This is done automatically after every modification if autosave is True.
        """
        self.update()
        if self.path is None:
            return

        path_new = self.path + '.new'
        try:
            with open(path_new, 'w', encoding="utf-8") as fobj:
                has_non_default_groups = any(
                    group != DEFAULT_GROUP and self.groups[group] 
                    for group in self.groups
                )
                if has_non_default_groups and HAS_YAML:
                    group_data = {}
                    for group in self.groups:
                        if group == DEFAULT_GROUP:
                            continue
                        keys_in_group = []
                        for key in sorted(self.groups[group]):
                            if key in ALLOWED_KEYS and key not in self.nonpersistent_bookmarks:
                                keys_in_group.append(key)
                        if keys_in_group:
                            group_data[group] = keys_in_group
                    if group_data:
                        fobj.write("# RANGER_GROUPS_START\n")
                        yaml.safe_dump(group_data, fobj, default_flow_style=False)
                        fobj.write("# RANGER_GROUPS_END\n")

                for key, value in self.dct.items():
                    if key in ALLOWED_KEYS \
                            and key not in self.nonpersistent_bookmarks:
                        if isinstance(value, fsobject.FileSystemObject):
                            value = value.original_path
                        key_value = "{0}:{1}\n".format(key, value)
                        if not PY3 and isinstance(key_value, str):
                            key_value = key_value.decode("utf-8")
                        fobj.write(key_value)
        except OSError as ex:
            self.fm.notify('Bookmarks error: {0}'.format(str(ex)), bad=True)
            return

        try:
            old_perms = os.stat(self.path)
            os.chown(path_new, old_perms.st_uid, old_perms.st_gid)
            os.chmod(path_new, old_perms.st_mode)

            if os.path.islink(self.path):
                target_path = os.path.realpath(self.path)
                os.rename(path_new, target_path)
            else:
                os.rename(path_new, self.path)

        except OSError as ex:
            self.fm.notify('Bookmarks error: {0}'.format(str(ex)), bad=True)
            return

        self._update_mtime()

    def enable_saving_backtick_bookmark(self, boolean):
        """
        Adds or removes the ' from the list of nonpersitent bookmarks
        """
        if boolean:
            if "'" in self.nonpersistent_bookmarks:
                self.nonpersistent_bookmarks.remove("'")  # enable
        else:
            self.nonpersistent_bookmarks.add("'")  # disable

    def _load_dict(self):
        if self.path is None:
            return {}, {DEFAULT_GROUP: set()}

        if not os.path.exists(self.path):
            try:
                with open(self.path, 'w', encoding="utf-8") as fobj:
                    pass
            except OSError as ex:
                self.fm.notify('Bookmarks error: {0}'.format(str(ex)), bad=True)
                return None, None

        try:
            with open(self.path, 'r', encoding="utf-8") as fobj:
                dct = {}
                groups = {DEFAULT_GROUP: set()}
                in_groups_section = False
                groups_yaml_lines = []

                for line in fobj:
                    stripped = line.strip()
                    if stripped == '# RANGER_GROUPS_START':
                        in_groups_section = True
                        continue
                    if stripped == '# RANGER_GROUPS_END':
                        in_groups_section = False
                        if HAS_YAML and groups_yaml_lines:
                            try:
                                groups_data = yaml.safe_load(''.join(groups_yaml_lines))
                                if isinstance(groups_data, dict):
                                    for group_name, keys in groups_data.items():
                                        if group_name and isinstance(keys, list):
                                            groups[group_name] = set()
                                            for key in keys:
                                                if key in ALLOWED_KEYS:
                                                    groups[group_name].add(key)
                            except yaml.YAMLError:
                                pass
                        groups_yaml_lines = []
                        continue

                    if in_groups_section:
                        groups_yaml_lines.append(line)
                        continue

                    if self.load_pattern.match(line):
                        key, value = line[0], line[2:-1]
                        if key in ALLOWED_KEYS:
                            dct[key] = self.bookmarktype(value)

                for key in dct:
                    found = False
                    for group in groups:
                        if key in groups[group]:
                            found = True
                            break
                    if not found:
                        groups[DEFAULT_GROUP].add(key)

        except OSError as ex:
            self.fm.notify('Bookmarks error: {0}'.format(str(ex)), bad=True)
            return None, None

        return dct, groups

    def _set_dict(self, dct, original, groups=None, original_groups=None):
        if original is None:
            original = {}
        if groups is None:
            groups = {DEFAULT_GROUP: set()}
        if original_groups is None:
            original_groups = {DEFAULT_GROUP: set()}

        self.dct.clear()
        self.dct.update(dct)
        self.groups = {DEFAULT_GROUP: set()}
        for group_name, keys in groups.items():
            if group_name == DEFAULT_GROUP:
                self.groups[DEFAULT_GROUP].update(keys)
            else:
                self.groups[group_name] = set(keys)
        self.original_dict = original
        self.original_groups = {g: set(ks) for g, ks in original_groups.items()}
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

    def _validate(self, value):
        return os.path.isdir(str(value))

    def create_group(self, group_name):
        """Create a new bookmark group"""
        if group_name in self.groups:
            return False
        self.groups[group_name] = set()
        if self.autosave:
            self.save()
        return True

    def delete_group(self, group_name):
        """Delete a bookmark group. Bookmarks in the group are moved to default group."""
        if group_name == DEFAULT_GROUP or group_name not in self.groups:
            return False
        bookmarks_in_group = self.groups[group_name].copy()
        for key in bookmarks_in_group:
            self.groups[DEFAULT_GROUP].add(key)
        del self.groups[group_name]
        if self.autosave:
            self.save()
        return True

    def list_groups(self):
        """List all bookmark groups"""
        return list(self.groups.keys())

    def get_bookmark_group(self, key):
        """Get the group name that contains the given bookmark key"""
        if key not in self.dct:
            return None
        for group, bookmarks in self.groups.items():
            if key in bookmarks:
                return group
        return None

    def add_to_group(self, key, group_name):
        """Add a bookmark to a group. Creates the group if it doesn't exist."""
        if key not in self.dct:
            return False
        if group_name not in self.groups:
            self.groups[group_name] = set()
        current_group = self.get_bookmark_group(key)
        if current_group is not None and current_group != group_name:
            self.groups[current_group].remove(key)
        self.groups[group_name].add(key)
        if self.autosave:
            self.save()
        return True

    def remove_from_group(self, key, group_name):
        """Remove a bookmark from a specific group. Moves it to default group."""
        if group_name == DEFAULT_GROUP:
            return False
        if group_name not in self.groups:
            return False
        if key not in self.groups[group_name]:
            return False
        self.groups[group_name].remove(key)
        self.groups[DEFAULT_GROUP].add(key)
        if self.autosave:
            self.save()
        return True

    def get_group_bookmarks(self, group_name):
        """Get all bookmarks in a group as a dict of {key: value}"""
        if group_name not in self.groups:
            return {}
        result = {}
        for key in self.groups[group_name]:
            if key in self.dct:
                result[key] = self.dct[key]
        return result

    def export_to_yaml(self, group_name=None, filepath=None):
        """Export bookmarks to YAML format.

        If group_name is specified, only export bookmarks from that group.
        If filepath is specified, write to that file, otherwise return the YAML string.
        """
        if not HAS_YAML:
            raise ImportError("PyYAML is required for YAML export/import")

        export_data = {}
        if group_name is None:
            for group in self.groups:
                if self.groups[group]:
                    export_data[group] = self._serialize_group(group)
        else:
            if group_name not in self.groups:
                return {}
            export_data[group_name] = self._serialize_group(group_name)

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.safe_dump(export_data, f, default_flow_style=False,
                               allow_unicode=True)
            return filepath
        else:
            return yaml.safe_dump(export_data, default_flow_style=False,
                                 allow_unicode=True)

    def import_from_yaml(self, filepath, merge=True):
        """Import bookmarks from YAML file.

        If merge is True, merge with existing bookmarks.
        If merge is False, replace existing bookmarks completely.
        """
        if not HAS_YAML:
            raise ImportError("PyYAML is required for YAML export/import")

        with open(filepath, 'r', encoding='utf-8') as f:
            import_data = yaml.safe_load(f)

        if import_data is None:
            return []

        if not merge:
            self.dct.clear()
            self.groups = {DEFAULT_GROUP: set()}

        imported_bookmarks = []
        for group_name, group_data in import_data.items():
            if not isinstance(group_data, dict):
                continue
            for key, value in group_data.items():
                if key in ALLOWED_KEYS:
                    self.dct[key] = self.bookmarktype(value)
                    if group_name not in self.groups:
                        self.groups[group_name] = set()
                    current_group = self.get_bookmark_group(key)
                    if current_group and current_group != group_name:
                        self.groups[current_group].discard(key)
                    self.groups[group_name].add(key)
                    imported_bookmarks.append((key, value, group_name))

        for key in self.dct:
            if key not in self.groups[DEFAULT_GROUP]:
                for group in self.groups:
                    if key in self.groups[group]:
                        break
                else:
                    self.groups[DEFAULT_GROUP].add(key)

        if self.autosave:
            self.save()

        return imported_bookmarks

    def _serialize_group(self, group_name):
        """Serialize a group to a dict of {key: path}"""
        result = {}
        for key in self.groups[group_name]:
            if key in self.dct:
                value = self.dct[key]
                if isinstance(value, fsobject.FileSystemObject):
                    result[key] = value.original_path
                else:
                    result[key] = str(value)
        return result
