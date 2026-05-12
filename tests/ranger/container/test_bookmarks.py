from __future__ import (absolute_import, division, print_function)

import os
import time

import pytest

from ranger.container.bookmarks import Bookmarks, DEFAULT_GROUP, HAS_YAML
from ranger.core.shared import FileManagerAware


class NotValidatedBookmarks(Bookmarks):
    def _validate(self, value):
        return True


class MockFM:
    def __init__(self):
        self.notifications = []

    def notify(self, msg, bad=False):
        self.notifications.append((msg, bad))


@pytest.fixture
def setup_fm():
    fm = MockFM()
    FileManagerAware.fm_set(fm)
    yield fm
    FileManagerAware.fm_set(None)


def testbookmarks(tmpdir, setup_fm):
    # Bookmarks point to directory location and allow fast access to
    # 'favorite' directories. They are persisted to a bookmark file, plain text.
    bookmarkfile = tmpdir.join("bookmarkfile")
    bmstore = NotValidatedBookmarks(str(bookmarkfile))

    # loading an empty bookmark file doesn't crash
    bmstore.load()

    # One can add / remove and check existing of bookmark
    bmstore["h"] = "world"
    assert "h" in bmstore
    del bmstore["h"]

    # Only one letter/digit bookmarks are valid, adding something else fails
    # silently
    bmstore["hello"] = "world"
    assert "hello" not in bmstore

    # The default bookmark is ', remember allows to set it
    bmstore.remember("the milk")
    assert bmstore["'"] == "the milk"

    # We can persist bookmarks to disk and restore them from disk
    bmstore.save()
    secondstore = NotValidatedBookmarks(str(bookmarkfile))
    secondstore.load()
    assert "'" in secondstore
    assert secondstore["'"] == "the milk"

    # We don't unnecessary update when the file on disk does not change
    origupdate = secondstore.update

    class OutOfDateException(Exception):
        pass

    def crash():
        raise OutOfDateException("Don't access me")
    secondstore.update = crash
    secondstore.update_if_outdated()

    # If the modification time change, we try to read the file
    newtime = time.time() - 5
    os.utime(str(bookmarkfile), (newtime, newtime))
    with pytest.raises(OutOfDateException):
        secondstore.update_if_outdated()
    secondstore.update = origupdate
    secondstore.update_if_outdated()


def test_bookmark_symlink(tmpdir, setup_fm):
    # Initialize plain file and symlink paths
    bookmarkfile_link = tmpdir.join("bookmarkfile")
    bookmarkfile_orig = tmpdir.join("bookmarkfile.orig")

    # Create symlink pointing towards the original plain file.
    os.symlink(str(bookmarkfile_orig), str(bookmarkfile_link))

    # Initialize the bookmark file and save the file.
    bmstore = Bookmarks(str(bookmarkfile_link))
    bmstore.save()

    # Once saved, the bookmark file should still be a symlink pointing towards the plain file.
    assert os.path.islink(str(bookmarkfile_link))
    assert not os.path.islink(str(bookmarkfile_orig))


class TestBookmarkGroups:
    def test_default_group(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"

        assert DEFAULT_GROUP in bmstore.groups
        assert "a" in bmstore.groups[DEFAULT_GROUP]
        assert "b" in bmstore.groups[DEFAULT_GROUP]

    def test_create_group(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        assert bmstore.create_group("work")
        assert "work" in bmstore.list_groups()

        assert not bmstore.create_group("work")

    def test_add_to_group(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"

        bmstore.create_group("work")

        assert bmstore.add_to_group("a", "work")
        assert "a" in bmstore.groups["work"]
        assert "a" not in bmstore.groups[DEFAULT_GROUP]

        assert bmstore.add_to_group("b", "work")
        assert "b" in bmstore.groups["work"]

        assert not bmstore.add_to_group("z", "work")

        assert bmstore.add_to_group("a", "new_group")
        assert "a" in bmstore.groups["new_group"]
        assert "a" not in bmstore.groups["work"]

    def test_get_bookmark_group(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"

        bmstore.create_group("work")
        bmstore.add_to_group("a", "work")

        assert bmstore.get_bookmark_group("a") == "work"
        assert bmstore.get_bookmark_group("b") == DEFAULT_GROUP
        assert bmstore.get_bookmark_group("z") is None

    def test_get_group_bookmarks(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"
        bmstore["c"] = "/path/c"

        bmstore.create_group("work")
        bmstore.add_to_group("a", "work")
        bmstore.add_to_group("b", "work")

        work_bookmarks = bmstore.get_group_bookmarks("work")
        assert "a" in work_bookmarks
        assert "b" in work_bookmarks
        assert "c" not in work_bookmarks

        default_bookmarks = bmstore.get_group_bookmarks(DEFAULT_GROUP)
        assert "c" in default_bookmarks

    def test_remove_from_group(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"

        bmstore.create_group("work")
        bmstore.add_to_group("a", "work")

        assert bmstore.remove_from_group("a", "work")
        assert "a" in bmstore.groups[DEFAULT_GROUP]
        assert "a" not in bmstore.groups["work"]

        assert not bmstore.remove_from_group("a", "work")
        assert not bmstore.remove_from_group("a", DEFAULT_GROUP)

    def test_delete_group(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"

        bmstore.create_group("work")
        bmstore.add_to_group("a", "work")
        bmstore.add_to_group("b", "work")

        assert bmstore.delete_group("work")
        assert "work" not in bmstore.list_groups()
        assert "a" in bmstore.groups[DEFAULT_GROUP]
        assert "b" in bmstore.groups[DEFAULT_GROUP]

        assert not bmstore.delete_group(DEFAULT_GROUP)
        assert not bmstore.delete_group("non_existent")

    def test_list_groups(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        groups = bmstore.list_groups()
        assert DEFAULT_GROUP in groups

        bmstore.create_group("work")
        bmstore.create_group("personal")

        groups = bmstore.list_groups()
        assert "work" in groups
        assert "personal" in groups


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML is not installed")
class TestBookmarkYaml:
    def test_export_import_single_group(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"
        bmstore["c"] = "/path/c"

        bmstore.create_group("work")
        bmstore.add_to_group("a", "work")
        bmstore.add_to_group("b", "work")

        export_file = tmpdir.join("export.yaml")
        bmstore.export_to_yaml(group_name="work", filepath=str(export_file))

        bmstore2 = NotValidatedBookmarks(str(tmpdir.join("bookmarkfile2")))
        bmstore2.load()

        imported = bmstore2.import_from_yaml(str(export_file), merge=True)
        assert len(imported) == 2

        assert "a" in bmstore2
        assert "b" in bmstore2
        assert "c" not in bmstore2
        assert "work" in bmstore2.list_groups()
        assert bmstore2.get_bookmark_group("a") == "work"

    def test_export_import_all_groups(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"
        bmstore["c"] = "/path/c"

        bmstore.create_group("work")
        bmstore.add_to_group("a", "work")

        bmstore.create_group("personal")
        bmstore.add_to_group("b", "personal")

        export_file = tmpdir.join("export.yaml")
        bmstore.export_to_yaml(filepath=str(export_file))

        bmstore2 = NotValidatedBookmarks(str(tmpdir.join("bookmarkfile2")))
        bmstore2.load()

        imported = bmstore2.import_from_yaml(str(export_file), merge=True)
        assert len(imported) == 3

        assert "a" in bmstore2
        assert "b" in bmstore2
        assert "c" in bmstore2
        assert "work" in bmstore2.list_groups()
        assert "personal" in bmstore2.list_groups()
        assert bmstore2.get_bookmark_group("a") == "work"
        assert bmstore2.get_bookmark_group("b") == "personal"
        assert bmstore2.get_bookmark_group("c") == DEFAULT_GROUP

    def test_import_merge(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"

        export_file = tmpdir.join("export.yaml")
        bmstore.export_to_yaml(filepath=str(export_file))

        bmstore2 = NotValidatedBookmarks(str(tmpdir.join("bookmarkfile2")))
        bmstore2.load()
        bmstore2["c"] = "/path/c"

        imported = bmstore2.import_from_yaml(str(export_file), merge=True)
        assert len(imported) == 2

        assert "a" in bmstore2
        assert "b" in bmstore2
        assert "c" in bmstore2

    def test_import_replace(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"

        export_file = tmpdir.join("export.yaml")
        bmstore.export_to_yaml(filepath=str(export_file))

        bmstore2 = NotValidatedBookmarks(str(tmpdir.join("bookmarkfile2")))
        bmstore2.load()
        bmstore2["c"] = "/path/c"

        imported = bmstore2.import_from_yaml(str(export_file), merge=False)
        assert len(imported) == 2

        assert "a" in bmstore2
        assert "b" in bmstore2
        assert "c" not in bmstore2

    def test_export_to_string(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"

        yaml_str = bmstore.export_to_yaml()
        assert isinstance(yaml_str, str)
        assert "a" in yaml_str
        assert "/path/a" in yaml_str


class TestBookmarkPersistence:
    def test_save_load_with_groups(self, tmpdir, setup_fm):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"

        bmstore.create_group("work")
        bmstore.add_to_group("a", "work")

        bmstore.save()

        bmstore2 = NotValidatedBookmarks(str(bookmarkfile))
        bmstore2.load()

        assert "a" in bmstore2
        assert "b" in bmstore2

        if HAS_YAML:
            assert bmstore2.get_bookmark_group("a") == "work"
            assert bmstore2.get_bookmark_group("b") == DEFAULT_GROUP

    def test_delete_updates_groups(self, tmpdir):
        bookmarkfile = tmpdir.join("bookmarkfile")
        bmstore = NotValidatedBookmarks(str(bookmarkfile))
        bmstore.load()

        bmstore["a"] = "/path/a"
        bmstore["b"] = "/path/b"

        bmstore.create_group("work")
        bmstore.add_to_group("a", "work")

        del bmstore["a"]

        assert "a" not in bmstore.groups["work"]
        assert "a" not in bmstore
