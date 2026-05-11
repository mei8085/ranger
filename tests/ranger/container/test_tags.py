from __future__ import (absolute_import, division, print_function)

import os
import time
from os.path import sep

import pytest

from ranger.container.tags import Tags, TagsDummy
from ranger.core.shared import FileManagerAware


class MockFM(object):
    def notify(self, msg, bad=False):
        pass


FileManagerAware.fm_set(MockFM())


def test_tags_basic(tmpdir):
    tagfile = tmpdir.join("tags")
    tags = Tags(str(tagfile))

    assert tags.tags == {}
    assert not "/path/to/file1" in tags

    tags.add("/path/to/file1")
    assert "/path/to/file1" in tags
    assert tags.marker("/path/to/file1") == "*"

    tags.add("/path/to/file2", tag="a")
    assert tags.marker("/path/to/file2") == "a"

    tags.remove("/path/to/file1")
    assert "/path/to/file1" not in tags

    tags.toggle("/path/to/file3")
    assert "/path/to/file3" in tags
    tags.toggle("/path/to/file3")
    assert "/path/to/file3" not in tags

    tags.toggle("/path/to/file4", tag="b")
    assert tags.marker("/path/to/file4") == "b"
    tags.toggle("/path/to/file4", tag="b")
    assert "/path/to/file4" not in tags


def test_tags_persistence(tmpdir):
    tagfile = tmpdir.join("tags")
    tags1 = Tags(str(tagfile))

    tags1.add("/path/to/file1")
    tags1.add("/path/to/file2", tag="a")

    tags2 = Tags(str(tagfile))
    assert "/path/to/file1" in tags2
    assert tags2.marker("/path/to/file1") == "*"
    assert tags2.marker("/path/to/file2") == "a"


def test_tags_sync_via_modification(tmpdir):
    tagfile = tmpdir.join("tags")
    tags1 = Tags(str(tagfile))
    tags2 = Tags(str(tagfile))

    tags1.add("/path/to/file1")

    assert "/path/to/file1" not in tags2

    time.sleep(0.01)
    tags2.add("/path/to/file2")

    assert "/path/to/file1" in tags2


def test_tags_update_if_outdated(tmpdir):
    tagfile = tmpdir.join("tags")
    tags1 = Tags(str(tagfile))
    tags1.add("/path/to/file1")

    tags2 = Tags(str(tagfile))
    assert "/path/to/file1" in tags2

    origupdate = tags2.update

    class OutOfDateException(Exception):
        pass

    def crash():
        raise OutOfDateException("Don't access me")

    tags2.update = crash

    tags2.update_if_outdated()

    newtime = time.time() - 5
    os.utime(str(tagfile), (newtime, newtime))

    with pytest.raises(OutOfDateException):
        tags2.update_if_outdated()
    tags2.update = origupdate
    tags2.update_if_outdated()
    assert "/path/to/file1" in tags2


def test_tags_merge_strategy(tmpdir):
    tagfile = tmpdir.join("tags")
    tags1 = Tags(str(tagfile))
    tags2 = Tags(str(tagfile))

    tags1.add("/path/to/file1")
    tags1.add("/path/to/file2")

    tags2.update_if_outdated()
    tags2.add("/path/to/file3")
    tags2.remove("/path/to/file2")

    assert "/path/to/file1" in tags2
    assert "/path/to/file2" not in tags2
    assert "/path/to/file3" in tags2

    tags1.add("/path/to/file4")
    time.sleep(0.01)

    tags2.add("/path/to/file5")
    assert "/path/to/file4" in tags2
    assert "/path/to/file1" in tags2
    assert "/path/to/file2" not in tags2
    assert "/path/to/file3" in tags2
    assert "/path/to/file5" in tags2


def test_tags_update_path(tmpdir):
    tagfile = tmpdir.join("tags")
    tags = Tags(str(tagfile))

    old_base = sep.join(["", "old", "path"])
    new_base = sep.join(["", "new", "path"])
    file1 = sep.join([old_base, "file1"])
    file2 = sep.join([old_base, "subdir", "file2"])
    file3 = sep.join(["", "other", "path", "file3"])
    new_file1 = sep.join([new_base, "file1"])
    new_file2 = sep.join([new_base, "subdir", "file2"])

    tags.add(file1)
    tags.add(file2)
    tags.add(file3)

    tags.update_path(old_base, new_base)

    assert file1 not in tags
    assert new_file1 in tags
    assert file2 not in tags
    assert new_file2 in tags
    assert file3 in tags


def test_tags_format(tmpdir):
    tagfile = tmpdir.join("tags")
    tags = Tags(str(tagfile))

    tags.add("/path/to/file1")
    tags.add("/path/to/file2", tag="a")
    tags.add("/path/to/file3", tag="b")

    with open(str(tagfile), "r") as f:
        content = f.read()

    assert "/path/to/file1\n" in content
    assert "a:/path/to/file2\n" in content
    assert "b:/path/to/file3\n" in content


def test_tags_dummy():
    tags = TagsDummy("/some/file")

    assert tags.tags == {}
    assert not "/path/to/file" in tags

    tags.add("/path/to/file1")
    assert "/path/to/file1" not in tags

    tags.remove("/path/to/file1")

    tags.toggle("/path/to/file2")
    assert "/path/to/file2" not in tags

    assert tags.marker("/path/to/file3") == "*"

    tags.sync()
    tags.dump()
    tags.update_if_outdated()
    tags.update()
