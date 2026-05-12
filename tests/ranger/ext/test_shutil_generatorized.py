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
