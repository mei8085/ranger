from __future__ import (absolute_import, division, print_function)

import os
import tempfile
import pytest

from ranger.ext.shutil_generatorized import (
    copyfile,
    copytree,
    move,
    OperationCancelled,
)


def test_copyfile_cancelled():
    """Test that copyfile raises OperationCancelled when cancelled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src.txt")
        dst = os.path.join(tmpdir, "dst.txt")
        
        # Create a test file
        with open(src, "w") as f:
            f.write("test content")
        
        # Test with a cancelled callback
        def cancelled():
            return True
        
        with pytest.raises(OperationCancelled):
            # This should raise immediately since cancelled() returns True
            list(copyfile(src, dst, cancelled=cancelled))


def test_copytree_cancelled():
    """Test that copytree raises OperationCancelled when cancelled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "src")
        dst_dir = os.path.join(tmpdir, "dst")
        os.makedirs(src_dir)
        
        # Create a test file
        with open(os.path.join(src_dir, "test.txt"), "w") as f:
            f.write("test content")
        
        # Test with a cancelled callback
        def cancelled():
            return True
        
        with pytest.raises(OperationCancelled):
            # This should raise immediately since cancelled() returns True
            list(copytree(src_dir, dst_dir, cancelled=cancelled))


def test_copyfile_not_cancelled():
    """Test that copyfile works when not cancelled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src.txt")
        dst = os.path.join(tmpdir, "dst.txt")
        
        # Create a test file
        with open(src, "w") as f:
            f.write("test content")
        
        # Test with a never-cancelled callback
        def cancelled():
            return False
        
        # This should complete successfully
        result = list(copyfile(src, dst, cancelled=cancelled))
        
        # Verify file was copied
        assert os.path.exists(dst)
        with open(dst, "r") as f:
            assert f.read() == "test content"


def test_move_cancelled():
    """Test that move raises OperationCancelled when cancelled during copy+delete phase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "src_dir")
        dst_dir = os.path.join(tmpdir, "dst_dir")
        os.makedirs(src_dir)
        os.makedirs(dst_dir)
        
        # Create test files in src_dir
        test_file = os.path.join(src_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        # Test with a cancelled callback
        # Note: move uses os.rename() first (atomic), only falls back to copy+delete
        # when os.rename() fails. We need to test the copy+delete path.
        
        # Force the copy+delete path by making os.rename fail
        original_rename = os.rename
        
        def failing_rename(*args, **kwargs):
            raise OSError("Forcing copy+delete path")
        
        try:
            os.rename = failing_rename
            
            def cancelled():
                return True
            
            with pytest.raises(OperationCancelled):
                list(move(src_dir, dst_dir, cancelled=cancelled))
        finally:
            os.rename = original_rename


def test_move_not_cancelled():
    """Test that move works when not cancelled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "src_dir")
        dst_dir = os.path.join(tmpdir, "dst_dir")
        os.makedirs(src_dir)
        os.makedirs(dst_dir)
        
        # Create test file in src_dir
        test_file = os.path.join(src_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        # Test with a never-cancelled callback
        def cancelled():
            return False
        
        # This should complete successfully
        result = list(move(src_dir, dst_dir, cancelled=cancelled))
        
        # Verify file was moved
        moved_file = os.path.join(dst_dir, "src_dir", "test.txt")
        assert os.path.exists(moved_file)
        assert not os.path.exists(test_file)  # Original should be gone


def test_move_midway_cancelled():
    """Test that move can be cancelled midway during copy+delete phase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "src_dir")
        dst_dir = os.path.join(tmpdir, "dst_dir")
        os.makedirs(src_dir)
        os.makedirs(dst_dir)
        
        # Create multiple test files
        for i in range(5):
            with open(os.path.join(src_dir, f"file{i}.txt"), "w") as f:
                f.write(f"content {i}")
        
        # Force the copy+delete path by making os.rename fail
        original_rename = os.rename
        
        def failing_rename(*args, **kwargs):
            raise OSError("Forcing copy+delete path")
        
        try:
            os.rename = failing_rename
            
            # Create a cancellable callback that triggers after some iterations
            cancel_triggered = [False]
            count = [0]
            
            def cancelled():
                count[0] += 1
                if count[0] > 2:
                    cancel_triggered[0] = True
                    return True
                return False
            
            # Attempt to move, should be cancelled midway
            with pytest.raises(OperationCancelled):
                list(move(src_dir, dst_dir, cancelled=cancelled))
            
            # Verify cancellation was triggered
            assert cancel_triggered[0]
        finally:
            os.rename = original_rename


def test_move_cancelled_stops_processing():
    """Test that move stops processing subsequent files when cancelled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "src_dir")
        dst_dir = os.path.join(tmpdir, "dst_dir")
        os.makedirs(src_dir)
        os.makedirs(dst_dir)
        
        # Create multiple test files with unique content
        for i in range(10):
            with open(os.path.join(src_dir, f"file{i}.txt"), "w") as f:
                f.write(f"content {i}")
        
        # Force the copy+delete path
        original_rename = os.rename
        
        def failing_rename(*args, **kwargs):
            raise OSError("Forcing copy+delete path")
        
        try:
            os.rename = failing_rename
            
            # Track which files were processed
            processed_files = []
            cancel_after = 3
            
            def cancelled():
                return len(processed_files) >= cancel_after
            
            # Wrap move to track processed files
            from ranger.ext.shutil_generatorized import move as original_move
            
            def tracking_move(*args, **kwargs):
                for item in original_move(*args, **kwargs):
                    processed_files.append(item)
                    yield item
            
            # Attempt to move, should be cancelled midway
            with pytest.raises(OperationCancelled):
                list(tracking_move(src_dir, dst_dir, cancelled=cancelled))
            
            # Verify that not all files were processed
            assert len(processed_files) <= cancel_after + 1
        finally:
            os.rename = original_rename


def test_copytree_midway_cancelled_stops_processing():
    """Test that copytree stops processing subsequent files when cancelled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "src_dir")
        dst_dir = os.path.join(tmpdir, "dst_dir")
        os.makedirs(src_dir)
        os.makedirs(dst_dir)
        
        # Create multiple test files with unique content
        for i in range(10):
            with open(os.path.join(src_dir, f"file{i}.txt"), "w") as f:
                f.write(f"content {i}")
        
        # Track which files were processed
        processed_files = []
        cancel_after = 3
        
        def cancelled():
            # Cancel after processing a few files
            return len(processed_files) >= cancel_after
        
        # Wrap copytree to track processed files
        from ranger.ext.shutil_generatorized import copytree as original_copytree
        
        # Create a modified version that tracks files
        def tracking_copytree(*args, **kwargs):
            for item in original_copytree(*args, **kwargs):
                processed_files.append(item)
                yield item
        
        # Attempt to copy, should be cancelled midway
        with pytest.raises(OperationCancelled):
            list(tracking_copytree(src_dir, dst_dir, cancelled=cancelled))
        
        # Verify that not all files were processed
        # The cancellation should stop further processing
        assert len(processed_files) <= cancel_after + 1  # Allow for one extra yield


def test_copyfile_midway_cancelled():
    """Test that copyfile can be cancelled midway through copying."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "large_file.txt")
        dst = os.path.join(tmpdir, "large_file_copy.txt")
        
        # Create a large file (100KB)
        with open(src, "w") as f:
            f.write("x" * 102400)
        
        # Track progress
        iterations = [0]
        cancel_after = 5  # Cancel after 5 iterations
        
        def cancelled():
            iterations[0] += 1
            return iterations[0] >= cancel_after
        
        # Attempt to copy, should be cancelled midway
        with pytest.raises(OperationCancelled):
            list(copyfile(src, dst, cancelled=cancelled))
        
        # Verify cancellation was triggered after some iterations
        assert iterations[0] >= cancel_after
