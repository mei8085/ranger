from __future__ import absolute_import

import os
import re
import shutil
import tempfile
import unittest

from unittest.mock import MagicMock, PropertyMock


class MockFileObject:
    def __init__(self, path, relative_path):
        self.path = path
        self.relative_path = relative_path
        self.realpath = path


class TestRenamePatternDetectConflicts(unittest.TestCase):
    def setUp(self):
        from ranger.config.commands import rename_pattern
        self.rename_pattern = rename_pattern

    def test_no_conflicts(self):
        temp_dir = tempfile.mkdtemp()
        try:
            file_a = MockFileObject(os.path.join(temp_dir, 'a.txt'), 'a.txt')
            file_b = MockFileObject(os.path.join(temp_dir, 'b.txt'), 'b.txt')

            selections = [file_a, file_b]
            new_names = ['A.txt', 'B.txt']

            result = self.rename_pattern._detect_conflicts(selections, new_names)
            self.assertIsNone(result)
        finally:
            shutil.rmtree(temp_dir)

    def test_multiple_files_target_same_name(self):
        temp_dir = tempfile.mkdtemp()
        try:
            file_a = MockFileObject(os.path.join(temp_dir, 'IMG_001.jpg'), 'IMG_001.jpg')
            file_b = MockFileObject(os.path.join(temp_dir, 'PIC_001.jpg'), 'PIC_001.jpg')

            selections = [file_a, file_b]
            new_names = ['Photo_001.jpg', 'Photo_001.jpg']

            result = self.rename_pattern._detect_conflicts(selections, new_names)
            self.assertIsNotNone(result)
            self.assertIn('Photo_001.jpg', result)
        finally:
            shutil.rmtree(temp_dir)

    def test_target_already_exists_on_disk(self):
        temp_dir = tempfile.mkdtemp()
        try:
            existing_path = os.path.join(temp_dir, 'existing.txt')
            with open(existing_path, 'w') as f:
                f.write('test')

            file_a = MockFileObject(os.path.join(temp_dir, 'a.txt'), 'a.txt')
            file_b = MockFileObject(os.path.join(temp_dir, 'b.txt'), 'b.txt')

            selections = [file_a, file_b]
            new_names = ['existing.txt', 'B.txt']

            result = self.rename_pattern._detect_conflicts(selections, new_names)
            self.assertIsNotNone(result)
            self.assertIn('existing.txt', result)
        finally:
            shutil.rmtree(temp_dir)

    def test_swap_within_selection_no_conflict(self):
        temp_dir = tempfile.mkdtemp()
        try:
            file_a = MockFileObject(os.path.join(temp_dir, 'a.txt'), 'a.txt')
            file_b = MockFileObject(os.path.join(temp_dir, 'b.txt'), 'b.txt')

            selections = [file_a, file_b]
            new_names = ['b.txt', 'a.txt']

            result = self.rename_pattern._detect_conflicts(selections, new_names)
            self.assertIsNone(result)
        finally:
            shutil.rmtree(temp_dir)

    def test_regex_substitution_basic(self):
        pattern = r'IMG_(\d{4})\.jpg'
        template = r'Vacation_\1.jpg'
        regex = re.compile(pattern)

        test_name = 'IMG_1234.jpg'
        match = regex.match(test_name)
        self.assertIsNotNone(match)
        new_name = match.expand(template)
        self.assertEqual(new_name, 'Vacation_1234.jpg')

    def test_regex_substitution_multiple_groups(self):
        pattern = r'(\d{4})-(\d{2})-(\d{2})_report\.txt'
        template = r'Report_\1-\2-\3.txt'
        regex = re.compile(pattern)

        test_name = '2023-05-15_report.txt'
        match = regex.match(test_name)
        self.assertIsNotNone(match)
        new_name = match.expand(template)
        self.assertEqual(new_name, 'Report_2023-05-15.txt')

    def test_regex_no_match_returns_original(self):
        pattern = r'IMG_(\d{4})\.jpg'
        template = r'Vacation_\1.jpg'
        regex = re.compile(pattern)

        test_name = 'other_file.txt'
        match = regex.match(test_name)
        if match:
            new_name = match.expand(template)
        else:
            new_name = test_name
        self.assertEqual(new_name, 'other_file.txt')


class TestUndoRenameBasic(unittest.TestCase):
    def test_undo_operations_storage(self):
        from ranger.config.commands import rename_pattern, undo_rename

        rename_pattern._undo_operations = None
        self.assertIsNone(rename_pattern._undo_operations)

        test_ops = [('/path/new1.txt', '/path/old1.txt'), ('/path/new2.txt', '/path/old2.txt')]
        rename_pattern._undo_operations = test_ops
        self.assertEqual(rename_pattern._undo_operations, test_ops)
        rename_pattern._undo_operations = None


class TestRegexErrorHandling(unittest.TestCase):
    def test_invalid_regex_raises_error(self):
        invalid_pattern = r'[invalid'
        with self.assertRaises(re.error):
            re.compile(invalid_pattern)

    def test_valid_regex_compiles(self):
        valid_pattern = r'\d+'
        regex = re.compile(valid_pattern)
        self.assertIsNotNone(regex)


class TestCycleDetection(unittest.TestCase):
    def setUp(self):
        from ranger.config.commands import rename_pattern
        self.rename_pattern = rename_pattern

    def test_simple_swap_cycle(self):
        remaining = {'a.txt': 'b.txt', 'b.txt': 'a.txt'}
        cycle = self.rename_pattern._find_cycle(remaining)
        self.assertEqual(cycle, {'a.txt', 'b.txt'})

    def test_three_way_cycle(self):
        remaining = {'a.txt': 'b.txt', 'b.txt': 'c.txt', 'c.txt': 'a.txt'}
        cycle = self.rename_pattern._find_cycle(remaining)
        self.assertEqual(cycle, {'a.txt', 'b.txt', 'c.txt'})

    def test_no_cycle_linear_chain(self):
        remaining = {'a.txt': 'b.txt', 'b.txt': 'c.txt'}
        cycle = self.rename_pattern._find_cycle(remaining)
        self.assertEqual(cycle, set())

    def test_no_cycle_standalone(self):
        remaining = {'a.txt': 'new_a.txt', 'b.txt': 'new_b.txt'}
        cycle = self.rename_pattern._find_cycle(remaining)
        self.assertEqual(cycle, set())

    def test_partial_cycle_with_chain(self):
        remaining = {
            'a.txt': 'b.txt',
            'b.txt': 'a.txt',
            'c.txt': 'd.txt',
            'd.txt': 'e.txt'
        }
        cycle = self.rename_pattern._find_cycle(remaining)
        self.assertTrue('a.txt' in cycle and 'b.txt' in cycle)


class TestTwoPhaseRenameOrder(unittest.TestCase):
    def setUp(self):
        from ranger.config.commands import rename_pattern
        self.rename_pattern = rename_pattern

    def _create_instance(self):
        from ranger.api.commands import Command
        cmd_instance = self.rename_pattern(':rename_pattern test')
        return cmd_instance

    def _operations_to_mapping(self, operations):
        result = {}
        phase1_map = {}
        for op in operations:
            op_type, src, dst = op
            if op_type == 'direct':
                result[src] = dst
            elif op_type == 'phase1':
                phase1_map[src] = dst
            elif op_type == 'phase2':
                original = None
                for orig, tmp in phase1_map.items():
                    if tmp == src:
                        original = orig
                        break
                if original:
                    result[original] = dst
        return result

    def test_no_conflict_all_direct(self):
        temp_dir = tempfile.mkdtemp()
        try:
            cmd = self._create_instance()
            rename_map = {'a.txt': 'A.txt', 'b.txt': 'B.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)
            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
            for op in ops:
                self.assertEqual(op[0], 'direct')
        finally:
            shutil.rmtree(temp_dir)

    def test_simple_swap_uses_two_phase(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt'), 'w').close()

            cmd = self._create_instance()
            rename_map = {'a.txt': 'b.txt', 'b.txt': 'a.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            self.assertTrue(any(op[0] == 'phase1' for op in ops))
            self.assertTrue(any(op[0] == 'phase2' for op in ops))

            phase1_count = sum(1 for op in ops if op[0] == 'phase1')
            phase2_count = sum(1 for op in ops if op[0] == 'phase2')
            self.assertEqual(phase1_count, 2)
            self.assertEqual(phase2_count, 2)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)

    def test_three_way_cycle_uses_two_phase(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt'), 'w').close()
            open(os.path.join(temp_dir, 'c.txt'), 'w').close()

            cmd = self._create_instance()
            rename_map = {'a.txt': 'b.txt', 'b.txt': 'c.txt', 'c.txt': 'a.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase1_count = sum(1 for op in ops if op[0] == 'phase1')
            phase2_count = sum(1 for op in ops if op[0] == 'phase2')
            self.assertEqual(phase1_count, 3)
            self.assertEqual(phase2_count, 3)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)

    def test_mixed_cycle_and_direct(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt'), 'w').close()

            cmd = self._create_instance()
            rename_map = {
                'a.txt': 'b.txt',
                'b.txt': 'a.txt',
                'c.txt': 'C.txt'
            }
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase1_count = sum(1 for op in ops if op[0] == 'phase1')
            phase2_count = sum(1 for op in ops if op[0] == 'phase2')
            direct_count = sum(1 for op in ops if op[0] == 'direct')
            self.assertEqual(phase1_count, 2)
            self.assertEqual(phase2_count, 2)
            self.assertEqual(direct_count, 1)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)

    def test_linear_chain_no_cycle(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()

            cmd = self._create_instance()
            rename_map = {'a.txt': 'b.txt', 'b.txt': 'c.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)

    def test_temp_name_conflict_uses_uuid(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt'), 'w').close()
            open(os.path.join(temp_dir, 'a.txt.__ranger_tmp__'), 'w').close()

            cmd = self._create_instance()
            rename_map = {'a.txt': 'b.txt', 'b.txt': 'a.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase1_ops = [op for op in ops if op[0] == 'phase1']
            temp_names = [op[2] for op in phase1_ops]
            for temp_name in temp_names:
                self.assertIn('.__ranger_tmp__', temp_name)
                self.assertTrue(temp_name.endswith('__'))
                hex_part = temp_name.split('.__ranger_tmp__')[1].rstrip('__')
                self.assertTrue(len(hex_part) >= 12)
                self.assertTrue(all(c in '0123456789abcdef' for c in hex_part))
        finally:
            shutil.rmtree(temp_dir)

    def test_existing_temp_files_on_disk_use_uuid(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt'), 'w').close()
            open(os.path.join(temp_dir, 'a.txt.__ranger_tmp__'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt.__ranger_tmp__'), 'w').close()

            cmd = self._create_instance()
            rename_map = {'a.txt': 'b.txt', 'b.txt': 'a.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase2_count = sum(1 for op in ops if op[0] == 'phase2')
            self.assertEqual(phase2_count, 2)

            phase1_count = sum(1 for op in ops if op[0] == 'phase1')
            self.assertEqual(phase1_count, 2)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)

            phase1_temp_names = [op[2] for op in ops if op[0] == 'phase1']
            for temp_name in phase1_temp_names:
                self.assertIn('.__ranger_tmp__', temp_name)
                self.assertTrue(temp_name.endswith('__'))
                hex_part = temp_name.split('.__ranger_tmp__')[1].rstrip('__')
                self.assertTrue(len(hex_part) >= 12)
        finally:
            shutil.rmtree(temp_dir)

    def test_multiple_temp_name_conflicts(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt'), 'w').close()
            open(os.path.join(temp_dir, 'a.txt.__ranger_tmp__'), 'w').close()
            open(os.path.join(temp_dir, 'a.txt.__ranger_tmp__1'), 'w').close()

            cmd = self._create_instance()
            rename_map = {'a.txt': 'b.txt', 'b.txt': 'a.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase1_count = sum(1 for op in ops if op[0] == 'phase1')
            phase2_count = sum(1 for op in ops if op[0] == 'phase2')
            self.assertEqual(phase1_count, 2)
            self.assertEqual(phase2_count, 2)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)

    def test_user_file_with_temp_suffix_direct_rename(self):
        temp_dir = tempfile.mkdtemp()
        try:
            user_file = 'my_file.__ranger_tmp__'
            open(os.path.join(temp_dir, user_file), 'w').close()
            open(os.path.join(temp_dir, 'other.txt'), 'w').close()

            cmd = self._create_instance()
            rename_map = {user_file: 'renamed.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            direct_count = sum(1 for op in ops if op[0] == 'direct')
            self.assertEqual(direct_count, 1)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)

    def test_user_file_with_temp_suffix_in_swap(self):
        temp_dir = tempfile.mkdtemp()
        try:
            user_file_a = 'file_a.__ranger_tmp__'
            user_file_b = 'file_b.__ranger_tmp__'
            open(os.path.join(temp_dir, user_file_a), 'w').close()
            open(os.path.join(temp_dir, user_file_b), 'w').close()

            cmd = self._create_instance()
            rename_map = {user_file_a: user_file_b, user_file_b: user_file_a}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase1_count = sum(1 for op in ops if op[0] == 'phase1')
            phase2_count = sum(1 for op in ops if op[0] == 'phase2')
            self.assertEqual(phase1_count, 2)
            self.assertEqual(phase2_count, 2)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)

    def test_user_file_with_numbered_temp_suffix(self):
        temp_dir = tempfile.mkdtemp()
        try:
            user_file = 'my_data.__ranger_tmp__123'
            open(os.path.join(temp_dir, user_file), 'w').close()
            open(os.path.join(temp_dir, 'normal.txt'), 'w').close()

            cmd = self._create_instance()
            rename_map = {user_file: 'final.txt', 'normal.txt': 'renamed.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            direct_count = sum(1 for op in ops if op[0] == 'direct')
            self.assertEqual(direct_count, 2)

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)

    def test_mixed_user_temp_files_and_internal_temp(self):
        temp_dir = tempfile.mkdtemp()
        try:
            user_temp_file = 'user.__ranger_tmp__'
            normal_file = 'normal.txt'
            open(os.path.join(temp_dir, user_temp_file), 'w').close()
            open(os.path.join(temp_dir, normal_file), 'w').close()

            cmd = self._create_instance()
            rename_map = {user_temp_file: normal_file, normal_file: user_temp_file}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase1_count = sum(1 for op in ops if op[0] == 'phase1')
            phase2_count = sum(1 for op in ops if op[0] == 'phase2')
            self.assertEqual(phase1_count, 2)
            self.assertEqual(phase2_count, 2)

            phase1_temp_names = set(op[2] for op in ops if op[0] == 'phase1')
            for temp_name in phase1_temp_names:
                self.assertIn('.__ranger_tmp__', temp_name)
                self.assertTrue(temp_name.endswith('__'))

            mapping = self._operations_to_mapping(ops)
            self.assertEqual(mapping, rename_map)
        finally:
            shutil.rmtree(temp_dir)


class TestInternalTempNameUniqueness(unittest.TestCase):
    def setUp(self):
        from ranger.config.commands import rename_pattern
        self.rename_pattern = rename_pattern

    def _create_instance(self):
        cmd_instance = self.rename_pattern(':rename_pattern test')
        return cmd_instance

    def test_internal_temp_names_are_unique(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt'), 'w').close()
            open(os.path.join(temp_dir, 'c.txt'), 'w').close()

            cmd = self._create_instance()
            rename_map = {'a.txt': 'b.txt', 'b.txt': 'c.txt', 'c.txt': 'a.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase1_temp_names = [op[2] for op in ops if op[0] == 'phase1']
            self.assertEqual(len(phase1_temp_names), len(set(phase1_temp_names)))

            for temp_name in phase1_temp_names:
                self.assertIn('.__ranger_tmp__', temp_name)
                self.assertTrue(temp_name.endswith('__'))
                hex_part = temp_name.split('.__ranger_tmp__')[1].rstrip('__')
                self.assertTrue(len(hex_part) >= 12)
        finally:
            shutil.rmtree(temp_dir)

    def test_internal_temp_names_tracked_properly(self):
        temp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(temp_dir, 'a.txt'), 'w').close()
            open(os.path.join(temp_dir, 'b.txt'), 'w').close()

            cmd = self._create_instance()
            rename_map = {'a.txt': 'b.txt', 'b.txt': 'a.txt'}
            ops = cmd._resolve_rename_order(rename_map, temp_dir)

            phase1_temp_names = set(op[2] for op in ops if op[0] == 'phase1')
            self.assertEqual(phase1_temp_names, cmd._internal_temp_names)

            for temp_name in phase1_temp_names:
                self.assertIn(temp_name, cmd._internal_temp_names)
        finally:
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()
