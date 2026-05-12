from __future__ import (absolute_import, division, print_function)

import os
import pytest

from ranger.container.bookmarks import Bookmarks, DEFAULT_GROUP, HAS_YAML
from ranger.core.shared import FileManagerAware
from ranger.config.commands import bookmark


class NotValidatedBookmarks(Bookmarks):
    def _validate(self, value):
        return True


class MockFM:
    def __init__(self, bookmark_file):
        self.notifications = []
        self.bookmarks = NotValidatedBookmarks(bookmark_file)
        self.bookmarks.load()

    def notify(self, msg, bad=False):
        self.notifications.append((msg, bad))

    def get_last_notification(self):
        if self.notifications:
            return self.notifications[-1]
        return None


@pytest.fixture
def setup_fm(tmpdir):
    bookmark_file = str(tmpdir.join("bookmarkfile"))
    fm = MockFM(bookmark_file)
    FileManagerAware.fm_set(fm)
    yield fm
    FileManagerAware.fm_set(None)


def _run_bookmark_command(fm, cmd_line):
    cmd = bookmark(cmd_line)
    cmd.execute()


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML is not installed")
class TestBookmarkExport:
    def test_export_all_bookmarks_success(self, tmpdir, setup_fm):
        fm = setup_fm
        fm.bookmarks["a"] = "/path/a"
        fm.bookmarks["b"] = "/path/b"
        fm.bookmarks.create_group("work")
        fm.bookmarks.add_to_group("a", "work")

        export_file = str(tmpdir.join("export.yaml"))
        _run_bookmark_command(fm, "bookmark export {0}".format(export_file))

        assert os.path.exists(export_file)
        msg, bad = fm.get_last_notification()
        assert "Exported all bookmarks" in msg
        assert not bad

    def test_export_single_group_success(self, tmpdir, setup_fm):
        fm = setup_fm
        fm.bookmarks["a"] = "/path/a"
        fm.bookmarks["b"] = "/path/b"
        fm.bookmarks.create_group("work")
        fm.bookmarks.add_to_group("a", "work")

        export_file = str(tmpdir.join("export_work.yaml"))
        _run_bookmark_command(fm, "bookmark export {0} work".format(export_file))

        assert os.path.exists(export_file)
        msg, bad = fm.get_last_notification()
        assert "Exported group 'work'" in msg
        assert not bad

    def test_export_missing_filepath_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark export")

        msg, bad = fm.get_last_notification()
        assert "Usage" in msg
        assert bad

    def test_export_invalid_path_error(self, setup_fm):
        fm = setup_fm
        fm.bookmarks["a"] = "/path/a"
        _run_bookmark_command(fm, "bookmark export /invalid/path/that/does/not/exist/file.yaml")

        msg, bad = fm.get_last_notification()
        assert "Export failed" in msg
        assert bad


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML is not installed")
class TestBookmarkImport:
    def test_import_success(self, tmpdir, setup_fm):
        import yaml

        fm = setup_fm
        export_file = str(tmpdir.join("import.yaml"))
        export_data = {
            "work": {"a": "/path/a", "b": "/path/b"},
            DEFAULT_GROUP: {"c": "/path/c"}
        }
        with open(export_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(export_data, f)

        _run_bookmark_command(fm, "bookmark import {0}".format(export_file))

        msg, bad = fm.get_last_notification()
        assert "Imported 3 bookmark(s)" in msg
        assert not bad
        assert "a" in fm.bookmarks
        assert "b" in fm.bookmarks
        assert "c" in fm.bookmarks
        assert fm.bookmarks.get_bookmark_group("a") == "work"
        assert fm.bookmarks.get_bookmark_group("b") == "work"
        assert fm.bookmarks.get_bookmark_group("c") == DEFAULT_GROUP

    def test_import_merge_with_existing(self, tmpdir, setup_fm):
        import yaml

        fm = setup_fm
        fm.bookmarks["z"] = "/path/z"

        export_file = str(tmpdir.join("import.yaml"))
        export_data = {"work": {"a": "/path/a"}}
        with open(export_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(export_data, f)

        _run_bookmark_command(fm, "bookmark import {0}".format(export_file))

        assert "z" in fm.bookmarks
        assert "a" in fm.bookmarks

    def test_import_missing_filepath_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark import")

        msg, bad = fm.get_last_notification()
        assert "Usage" in msg
        assert bad

    def test_import_file_not_found_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark import /nonexistent/file.yaml")

        msg, bad = fm.get_last_notification()
        assert "File not found" in msg
        assert bad

    def test_import_invalid_yaml_error(self, tmpdir, setup_fm):
        fm = setup_fm
        export_file = str(tmpdir.join("bad.yaml"))
        with open(export_file, 'w', encoding='utf-8') as f:
            f.write("not: valid: yaml: [")

        _run_bookmark_command(fm, "bookmark import {0}".format(export_file))

        msg, bad = fm.get_last_notification()
        assert "Import failed" in msg
        assert bad


class TestBookmarkGeneral:
    def test_no_subcommand_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark")

        msg, bad = fm.get_last_notification()
        assert "Usage" in msg
        assert bad

    def test_unknown_subcommand_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark invalid")

        msg, bad = fm.get_last_notification()
        assert "Unknown subcommand" in msg
        assert bad


class TestBookmarkGroups:
    def test_group_create_success(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark group create work")

        msg, bad = fm.get_last_notification()
        assert "Created group: work" in msg
        assert not bad
        assert "work" in fm.bookmarks.list_groups()

    def test_group_create_duplicate_error(self, setup_fm):
        fm = setup_fm
        fm.bookmarks.create_group("work")
        _run_bookmark_command(fm, "bookmark group create work")

        msg, bad = fm.get_last_notification()
        assert "already exists" in msg
        assert bad

    def test_group_create_missing_name_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark group create")

        msg, bad = fm.get_last_notification()
        assert "Usage" in msg
        assert bad

    def test_group_delete_success(self, setup_fm):
        fm = setup_fm
        fm.bookmarks.create_group("work")
        _run_bookmark_command(fm, "bookmark group delete work")

        msg, bad = fm.get_last_notification()
        assert "Deleted group: work" in msg
        assert not bad
        assert "work" not in fm.bookmarks.list_groups()

    def test_group_delete_default_group_protected_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark group delete __default__")

        msg, bad = fm.get_last_notification()
        assert "Cannot delete group (not found or is default)" in msg
        assert bad

    def test_group_delete_nonexistent_group_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark group delete nonexistent_group")

        msg, bad = fm.get_last_notification()
        assert "Cannot delete group (not found or is default)" in msg
        assert bad

    def test_group_list(self, setup_fm):
        fm = setup_fm
        fm.bookmarks.create_group("work")
        fm.bookmarks.create_group("personal")
        _run_bookmark_command(fm, "bookmark group list")

        msg, bad = fm.get_last_notification()
        assert "work" in msg
        assert "personal" in msg
        assert not bad


class TestBookmarkAddRemove:
    def test_add_to_group_success(self, setup_fm):
        fm = setup_fm
        fm.bookmarks["a"] = "/path/a"
        fm.bookmarks.create_group("work")

        _run_bookmark_command(fm, "bookmark add a work")

        msg, bad = fm.get_last_notification()
        assert "Added bookmark 'a' to group 'work'" in msg
        assert not bad
        assert fm.bookmarks.get_bookmark_group("a") == "work"

    def test_add_to_group_nonexistent_bookmark_error(self, setup_fm):
        fm = setup_fm
        fm.bookmarks.create_group("work")

        _run_bookmark_command(fm, "bookmark add z work")

        msg, bad = fm.get_last_notification()
        assert "Bookmark 'z' not found" in msg
        assert bad

    def test_add_to_group_missing_args_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark add a")

        msg, bad = fm.get_last_notification()
        assert "Usage" in msg
        assert bad

    def test_remove_from_group_success(self, setup_fm):
        fm = setup_fm
        fm.bookmarks["a"] = "/path/a"
        fm.bookmarks.create_group("work")
        fm.bookmarks.add_to_group("a", "work")

        _run_bookmark_command(fm, "bookmark remove a work")

        msg, bad = fm.get_last_notification()
        assert "Removed bookmark 'a' from group 'work'" in msg
        assert not bad
        assert fm.bookmarks.get_bookmark_group("a") == DEFAULT_GROUP

    def test_remove_from_group_not_in_group_error(self, setup_fm):
        fm = setup_fm
        fm.bookmarks["a"] = "/path/a"
        fm.bookmarks.create_group("work")

        _run_bookmark_command(fm, "bookmark remove a work")

        msg, bad = fm.get_last_notification()
        assert "Bookmark 'a' not in group 'work'" in msg
        assert bad

    def test_remove_from_group_missing_args_error(self, setup_fm):
        fm = setup_fm
        _run_bookmark_command(fm, "bookmark remove a")

        msg, bad = fm.get_last_notification()
        assert "Usage" in msg
        assert bad


class TestBookmarkList:
    def test_list_all_bookmarks(self, setup_fm):
        fm = setup_fm
        fm.bookmarks["a"] = "/path/a"
        fm.bookmarks["b"] = "/path/b"

        _run_bookmark_command(fm, "bookmark list")

        msg, bad = fm.get_last_notification()
        assert "a" in msg
        assert "/path/a" in msg
        assert "b" in msg
        assert "/path/b" in msg
        assert not bad

    def test_list_group_bookmarks(self, setup_fm):
        fm = setup_fm
        fm.bookmarks["a"] = "/path/a"
        fm.bookmarks["b"] = "/path/b"
        fm.bookmarks.create_group("work")
        fm.bookmarks.add_to_group("a", "work")

        _run_bookmark_command(fm, "bookmark list work")

        msg, bad = fm.get_last_notification()
        assert "Bookmarks in 'work'" in msg
        assert "a" in msg
        assert "b" not in msg
        assert not bad

    def test_list_empty_group(self, setup_fm):
        fm = setup_fm
        fm.bookmarks.create_group("empty")

        _run_bookmark_command(fm, "bookmark list empty")

        msg, bad = fm.get_last_notification()
        assert "No bookmarks in group 'empty'" in msg
        assert not bad
