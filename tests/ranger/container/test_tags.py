from __future__ import (absolute_import, division, print_function)

import os
import threading
import time
from os.path import sep

import pytest

from ranger.container.tags import Tags, TagsDummy, FileLock
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

    assert "/path/to/file1" in tags2

    tags2.add("/path/to/file2")

    assert "/path/to/file2" in tags1


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


def test_tags_read_auto_sync_contains(tmpdir):
    tagfile = tmpdir.join("tags")
    tags1 = Tags(str(tagfile))
    tags2 = Tags(str(tagfile))

    tags1.add("/path/to/file1")

    assert "/path/to/file1" in tags2


def test_tags_read_auto_sync_marker(tmpdir):
    tagfile = tmpdir.join("tags")
    tags1 = Tags(str(tagfile))
    tags2 = Tags(str(tagfile))

    tags1.add("/path/to/file1", tag="a")

    assert tags2.marker("/path/to/file1") == "a"


def test_tags_read_auto_sync_multiple_changes(tmpdir):
    tagfile = tmpdir.join("tags")
    tags1 = Tags(str(tagfile))
    tags2 = Tags(str(tagfile))

    tags1.add("/path/to/file1")
    tags1.add("/path/to/file2", tag="a")

    assert "/path/to/file1" in tags2
    assert tags2.marker("/path/to/file2") == "a"

    tags1.remove("/path/to/file1")
    tags1.add("/path/to/file2", tag="b")

    assert "/path/to/file1" not in tags2
    assert tags2.marker("/path/to/file2") == "b"


def test_file_lock_basic(tmpdir):
    lockfile = str(tmpdir.join("testfile"))
    lock = FileLock(lockfile)

    with lock.acquire(exclusive=True):
        assert os.path.exists(lockfile + ".lock")

    assert not os.path.exists(lockfile + ".lock")


def test_file_lock_shared(tmpdir):
    lockfile = str(tmpdir.join("testfile"))
    lock1 = FileLock(lockfile)
    lock2 = FileLock(lockfile)

    acquired = []

    def acquire_shared(lock_obj, result_list, index):
        with lock_obj.acquire(exclusive=False, timeout=2):
            result_list.append(index)
            time.sleep(0.1)

    t1 = threading.Thread(target=acquire_shared, args=(lock1, acquired, 1))
    t2 = threading.Thread(target=acquire_shared, args=(lock2, acquired, 2))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(acquired) == 2
    assert 1 in acquired
    assert 2 in acquired


def test_file_lock_exclusive_blocks(tmpdir):
    lockfile = str(tmpdir.join("testfile"))
    lock1 = FileLock(lockfile)
    lock2 = FileLock(lockfile)

    acquired_order = []
    release_event = threading.Event()

    def acquire_exclusive_hold(lock_obj, event, order_list, index):
        with lock_obj.acquire(exclusive=True, timeout=5):
            order_list.append(("acquired", index))
            event.wait(timeout=1)
        order_list.append(("released", index))

    def acquire_exclusive_wait(lock_obj, order_list, index):
        time.sleep(0.05)
        with lock_obj.acquire(exclusive=True, timeout=5):
            order_list.append(("acquired", index))
        order_list.append(("released", index))

    t1 = threading.Thread(
        target=acquire_exclusive_hold, args=(lock1, release_event, acquired_order, 1)
    )
    t2 = threading.Thread(
        target=acquire_exclusive_wait, args=(lock2, acquired_order, 2)
    )

    t1.start()
    t2.start()

    time.sleep(0.2)
    release_event.set()

    t1.join()
    t2.join()

    assert ("acquired", 1) in acquired_order
    assert ("acquired", 2) in acquired_order
    assert acquired_order.index(("acquired", 1)) < acquired_order.index(("acquired", 2))


def test_tags_concurrent_writes(tmpdir):
    tagfile = tmpdir.join("tags")
    num_threads = 5
    num_writes_per_thread = 10
    errors = []

    def write_tags(thread_id):
        try:
            tags = Tags(str(tagfile))
            for i in range(num_writes_per_thread):
                path = "/path/to/thread_{}_file_{}".format(thread_id, i)
                tags.add(path, tag=str(thread_id))
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=write_tags, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, "Errors during concurrent writes: {}".format(errors)

    final_tags = Tags(str(tagfile))
    for i in range(num_threads):
        for j in range(num_writes_per_thread):
            path = "/path/to/thread_{}_file_{}".format(i, j)
            assert path in final_tags, "Missing tag: {}".format(path)
            assert final_tags.marker(path) == str(i)


def test_tags_concurrent_read_write(tmpdir):
    tagfile = tmpdir.join("tags")
    errors = []
    stop_event = threading.Event()

    def writer():
        try:
            tags = Tags(str(tagfile))
            for i in range(50):
                if stop_event.is_set():
                    break
                tags.add("/path/to/file_{}".format(i))
                time.sleep(0.01)
        except Exception as e:
            errors.append(("writer", e))

    def reader(reader_id):
        try:
            tags = Tags(str(tagfile))
            for i in range(100):
                if stop_event.is_set():
                    break
                _ = "/path/to/file_{}".format(i) in tags
                _ = tags.marker("/path/to/file_{}".format(i))
                time.sleep(0.005)
        except Exception as e:
            errors.append(("reader_{}".format(reader_id), e))

    writer_thread = threading.Thread(target=writer)
    reader_threads = []
    for i in range(3):
        t = threading.Thread(target=reader, args=(i,))
        reader_threads.append(t)

    writer_thread.start()
    for t in reader_threads:
        t.start()

    writer_thread.join()
    stop_event.set()
    for t in reader_threads:
        t.join()

    assert len(errors) == 0, "Errors during concurrent read/write: {}".format(errors)


def test_tags_lock_timeout(tmpdir):
    lockfile = str(tmpdir.join("testfile"))
    lock1 = FileLock(lockfile)
    lock2 = FileLock(lockfile)

    release_event = threading.Event()
    timeout_error = []

    def hold_lock():
        with lock1.acquire(exclusive=True, timeout=5):
            release_event.wait(timeout=2)

    def try_lock():
        try:
            with lock2.acquire(exclusive=True, timeout=0.5):
                pass
        except RuntimeError as e:
            timeout_error.append(e)

    t1 = threading.Thread(target=hold_lock)
    t2 = threading.Thread(target=try_lock)

    t1.start()
    time.sleep(0.1)
    t2.start()
    t2.join()
    release_event.set()
    t1.join()

    assert len(timeout_error) == 1
    assert "Timeout" in str(timeout_error[0])
