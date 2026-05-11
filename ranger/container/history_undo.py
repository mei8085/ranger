# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

from abc import ABCMeta, abstractmethod
from collections import deque

import os
import shutil


class UndoStackEmpty(Exception):
    pass


class RedoStackEmpty(Exception):
    pass


class UndoableAction(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.description = ""

    @abstractmethod
    def do(self):
        pass

    @abstractmethod
    def undo(self):
        pass

    @abstractmethod
    def can_merge_with(self, other):
        return False

    @abstractmethod
    def merge_with(self, other):
        pass


class DeleteAction(UndoableAction):
    def __init__(self, paths, trash_dir):
        super(DeleteAction, self).__init__()
        self._original_paths = [os.path.abspath(p) for p in paths]
        self._trash_dir = trash_dir
        self._backup_paths = []
        self.description = "delete: {0}".format(", ".join(self._original_paths))

    def do(self):
        if not os.path.exists(self._trash_dir):
            os.makedirs(self._trash_dir)

        for i, path in enumerate(self._original_paths):
            basename = os.path.basename(path)
            backup_path = os.path.join(self._trash_dir, basename)

            if os.path.exists(backup_path):
                base, ext = os.path.splitext(basename)
                counter = 1
                while True:
                    new_basename = "{0}_{1}{2}".format(base, counter, ext)
                    backup_path = os.path.join(self._trash_dir, new_basename)
                    if not os.path.exists(backup_path):
                        break
                    counter += 1

            if os.path.isdir(path) and not os.path.islink(path):
                shutil.move(path, backup_path)
            else:
                shutil.move(path, backup_path)

            self._backup_paths.append(backup_path)

    def undo(self):
        for i, backup_path in enumerate(self._backup_paths):
            original_path = self._original_paths[i]
            if os.path.exists(backup_path):
                original_dir = os.path.dirname(original_path)
                if not os.path.exists(original_dir):
                    os.makedirs(original_dir)
                shutil.move(backup_path, original_path)

    def can_merge_with(self, other):
        return False

    def merge_with(self, other):
        pass


class RenameAction(UndoableAction):
    def __init__(self, src, dest):
        super(RenameAction, self).__init__()
        self._src = os.path.abspath(src)
        self._dest = os.path.abspath(dest)
        self.description = "rename: {0} -> {1}".format(
            os.path.basename(self._src),
            os.path.basename(self._dest)
        )

    def do(self):
        dest_dir = os.path.dirname(self._dest)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        os.rename(self._src, self._dest)

    def undo(self):
        src_dir = os.path.dirname(self._src)
        if src_dir and not os.path.exists(src_dir):
            os.makedirs(src_dir)
        os.rename(self._dest, self._src)

    def can_merge_with(self, other):
        if not isinstance(other, RenameAction):
            return False
        if self._dest == other._src:
            return True
        return False

    def merge_with(self, other):
        self._dest = other._dest
        self.description = "rename: {0} -> {1}".format(
            os.path.basename(self._src),
            os.path.basename(self._dest)
        )


class MoveAction(UndoableAction):
    def __init__(self, src_paths, dest_dir):
        super(MoveAction, self).__init__()
        self._src_paths = [os.path.abspath(p) for p in src_paths]
        self._dest_dir = os.path.abspath(dest_dir)
        self._dest_paths = []
        self.description = "move: {0} -> {1}".format(
            ", ".join(os.path.basename(p) for p in self._src_paths),
            self._dest_dir
        )

    def do(self):
        for src_path in self._src_paths:
            basename = os.path.basename(src_path)
            dest_path = os.path.join(self._dest_dir, basename)

            if os.path.exists(dest_path):
                base, ext = os.path.splitext(basename)
                counter = 1
                while True:
                    new_basename = "{0}_{1}{2}".format(base, counter, ext)
                    dest_path = os.path.join(self._dest_dir, new_basename)
                    if not os.path.exists(dest_path):
                        break
                    counter += 1

            shutil.move(src_path, dest_path)
            self._dest_paths.append(dest_path)

    def undo(self):
        for i, dest_path in enumerate(self._dest_paths):
            if os.path.exists(dest_path):
                src_path = self._src_paths[i]
                src_dir = os.path.dirname(src_path)
                if not os.path.exists(src_dir):
                    os.makedirs(src_dir)
                shutil.move(dest_path, src_path)

    def can_merge_with(self, other):
        return False

    def merge_with(self, other):
        pass


class CopyAction(UndoableAction):
    def __init__(self, src_paths, dest_dir):
        super(CopyAction, self).__init__()
        self._src_paths = [os.path.abspath(p) for p in src_paths]
        self._dest_dir = os.path.abspath(dest_dir)
        self._dest_paths = []
        self.description = "copy: {0} -> {1}".format(
            ", ".join(os.path.basename(p) for p in self._src_paths),
            self._dest_dir
        )

    def do(self):
        from ranger.ext.shutil_generatorized import copy2, copytree

        for src_path in self._src_paths:
            basename = os.path.basename(src_path)
            dest_path = os.path.join(self._dest_dir, basename)

            if os.path.exists(dest_path):
                base, ext = os.path.splitext(basename)
                counter = 1
                while True:
                    new_basename = "{0}_{1}{2}".format(base, counter, ext)
                    dest_path = os.path.join(self._dest_dir, new_basename)
                    if not os.path.exists(dest_path):
                        break
                    counter += 1

            if os.path.isdir(src_path) and not os.path.islink(src_path):
                copytree(src_path, dest_path)
            else:
                copy2(src_path, dest_path)

            self._dest_paths.append(dest_path)

    def undo(self):
        for dest_path in self._dest_paths:
            if os.path.isdir(dest_path) and not os.path.islink(dest_path):
                shutil.rmtree(dest_path)
            elif os.path.exists(dest_path):
                os.remove(dest_path)

    def can_merge_with(self, other):
        return False

    def merge_with(self, other):
        pass


class UndoRedoStack(object):
    def __init__(self, maxlen=50):
        self._undo_stack = deque(maxlen=maxlen)
        self._redo_stack = deque()
        self.maxlen = maxlen

    def push(self, action):
        if self._undo_stack:
            last_action = self._undo_stack[-1]
            if last_action.can_merge_with(action):
                last_action.merge_with(action)
                return
        self._undo_stack.append(action)
        self._redo_stack.clear()

    def can_undo(self):
        return len(self._undo_stack) > 0

    def can_redo(self):
        return len(self._redo_stack) > 0

    def undo(self):
        if not self._undo_stack:
            raise UndoStackEmpty()
        action = self._undo_stack.pop()
        action.undo()
        self._redo_stack.append(action)
        return action.description

    def redo(self):
        if not self._redo_stack:
            raise RedoStackEmpty()
        action = self._redo_stack.pop()
        action.do()
        self._undo_stack.append(action)
        return action.description

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
