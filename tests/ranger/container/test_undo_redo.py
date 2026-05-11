from __future__ import (absolute_import, division, print_function)

import os
import tempfile
import shutil

from ranger.container.history_undo import (
    UndoRedoStack,
    DeleteAction,
    RenameAction,
    MoveAction,
    UndoStackEmpty,
    RedoStackEmpty,
)


def create_temp_file(path):
    with open(path, 'w') as f:
        f.write('test content')


def create_temp_dir(path):
    os.makedirs(path)


class TestUndoRedoStack:
    def test_push_and_pop(self):
        stack = UndoRedoStack(maxlen=10)
        assert not stack.can_undo()
        assert not stack.can_redo()

        class MockAction:
            def __init__(self, name):
                self.name = name
                self.description = name
                self.done = False

            def do(self):
                self.done = True

            def undo(self):
                self.done = False

            def can_merge_with(self, other):
                return False

            def merge_with(self, other):
                pass

        action1 = MockAction('action1')
        stack.push(action1)
        assert stack.can_undo()
        assert not stack.can_redo()

        desc = stack.undo()
        assert desc == 'action1'
        assert not stack.can_undo()
        assert stack.can_redo()

        desc = stack.redo()
        assert desc == 'action1'
        assert stack.can_undo()
        assert not stack.can_redo()

    def test_undo_empty(self):
        stack = UndoRedoStack()
        try:
            stack.undo()
            assert False
        except UndoStackEmpty:
            assert True

    def test_redo_empty(self):
        stack = UndoRedoStack()
        try:
            stack.redo()
            assert False
        except RedoStackEmpty:
            assert True

    def test_max_length(self):
        stack = UndoRedoStack(maxlen=2)

        class MockAction:
            def __init__(self, name):
                self.name = name
                self.description = name

            def do(self):
                pass

            def undo(self):
                pass

            def can_merge_with(self, other):
                return False

            def merge_with(self, other):
                pass

        stack.push(MockAction('1'))
        stack.push(MockAction('2'))
        stack.push(MockAction('3'))

        assert stack.undo() == '3'
        assert stack.undo() == '2'
        try:
            stack.undo()
            assert False
        except UndoStackEmpty:
            assert True

    def test_redo_cleared_on_new_action(self):
        stack = UndoRedoStack()

        class MockAction:
            def __init__(self, name):
                self.name = name
                self.description = name

            def do(self):
                pass

            def undo(self):
                pass

            def can_merge_with(self, other):
                return False

            def merge_with(self, other):
                pass

        stack.push(MockAction('1'))
        stack.push(MockAction('2'))
        stack.undo()
        assert stack.can_redo()
        stack.push(MockAction('3'))
        assert not stack.can_redo()


class TestRenameAction:
    def test_rename_undo_redo(self):
        temp_dir = tempfile.mkdtemp()
        try:
            src = os.path.join(temp_dir, 'file1.txt')
            dest = os.path.join(temp_dir, 'file2.txt')
            create_temp_file(src)

            action = RenameAction(src, dest)
            action.do()
            assert os.path.exists(dest)
            assert not os.path.exists(src)

            action.undo()
            assert os.path.exists(src)
            assert not os.path.exists(dest)

            action.do()
            assert os.path.exists(dest)
            assert not os.path.exists(src)
        finally:
            shutil.rmtree(temp_dir)

    def test_rename_merge(self):
        temp_dir = tempfile.mkdtemp()
        try:
            file_a = os.path.join(temp_dir, 'file_a.txt')
            file_b = os.path.join(temp_dir, 'file_b.txt')
            file_c = os.path.join(temp_dir, 'file_c.txt')
            create_temp_file(file_a)

            action1 = RenameAction(file_a, file_b)
            action2 = RenameAction(file_b, file_c)

            assert action1.can_merge_with(action2)
            action1.merge_with(action2)

            action1.do()
            assert os.path.exists(file_c)
            assert not os.path.exists(file_a)
            assert not os.path.exists(file_b)

            action1.undo()
            assert os.path.exists(file_a)
            assert not os.path.exists(file_c)
        finally:
            shutil.rmtree(temp_dir)

    def test_stack_with_rename_merge(self):
        temp_dir = tempfile.mkdtemp()
        try:
            file_a = os.path.join(temp_dir, 'file_a.txt')
            file_b = os.path.join(temp_dir, 'file_b.txt')
            file_c = os.path.join(temp_dir, 'file_c.txt')
            file_d = os.path.join(temp_dir, 'file_d.txt')
            create_temp_file(file_a)

            stack = UndoRedoStack()

            action1 = RenameAction(file_a, file_b)
            action1.do()
            stack.push(action1)
            assert os.path.exists(file_b)

            action2 = RenameAction(file_b, file_c)
            action2.do()
            stack.push(action2)
            assert os.path.exists(file_c)
            assert not os.path.exists(file_b)

            action3 = RenameAction(file_c, file_d)
            action3.do()
            stack.push(action3)
            assert os.path.exists(file_d)

            assert stack.undo().startswith('rename:')
            assert os.path.exists(file_a)
            assert not os.path.exists(file_d)
        finally:
            shutil.rmtree(temp_dir)


class TestDeleteAction:
    def test_delete_undo_redo(self):
        temp_dir = tempfile.mkdtemp()
        trash_dir = os.path.join(temp_dir, 'trash')
        try:
            test_file = os.path.join(temp_dir, 'test_file.txt')
            create_temp_file(test_file)

            action = DeleteAction([test_file], trash_dir)
            action.do()
            assert not os.path.exists(test_file)

            action.undo()
            assert os.path.exists(test_file)

            action.do()
            assert not os.path.exists(test_file)
        finally:
            shutil.rmtree(temp_dir)

    def test_delete_multiple_files(self):
        temp_dir = tempfile.mkdtemp()
        trash_dir = os.path.join(temp_dir, 'trash')
        try:
            files = []
            for i in range(3):
                path = os.path.join(temp_dir, 'file{0}.txt'.format(i))
                create_temp_file(path)
                files.append(path)

            action = DeleteAction(files, trash_dir)
            action.do()

            for f in files:
                assert not os.path.exists(f)

            action.undo()

            for f in files:
                assert os.path.exists(f)
        finally:
            shutil.rmtree(temp_dir)


class TestMoveAction:
    def test_move_undo_redo(self):
        temp_dir = tempfile.mkdtemp()
        try:
            src_dir = os.path.join(temp_dir, 'src')
            dest_dir = os.path.join(temp_dir, 'dest')
            create_temp_dir(src_dir)
            create_temp_dir(dest_dir)

            test_file = os.path.join(src_dir, 'test_file.txt')
            create_temp_file(test_file)

            action = MoveAction([test_file], dest_dir)
            action.do()

            assert os.path.exists(os.path.join(dest_dir, 'test_file.txt'))
            assert not os.path.exists(test_file)

            action.undo()

            assert os.path.exists(test_file)
            assert not os.path.exists(os.path.join(dest_dir, 'test_file.txt'))

            action.do()

            assert os.path.exists(os.path.join(dest_dir, 'test_file.txt'))
            assert not os.path.exists(test_file)
        finally:
            shutil.rmtree(temp_dir)
