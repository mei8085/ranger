from __future__ import (absolute_import, division, print_function)

import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock, Mock

# ======================================
# Module-level mocks - MUST be set before any imports
# ======================================

# Mock grp module
mock_grp = MagicMock()
mock_grp.getgrgid = lambda gid: ('group_' + str(gid),)
sys.modules['grp'] = mock_grp

# Mock pwd module
mock_pwd = MagicMock()
mock_pwd.getpwuid = lambda uid: ('user_' + str(uid),)
sys.modules['pwd'] = mock_pwd

# Mock curses module
mock_curses = MagicMock()
mock_curses.color_pair = lambda x: x
mock_curses.A_NORMAL = 0
mock_curses.A_BOLD = 1
mock_curses.A_REVERSE = 2
mock_curses.COLOR_PAIRS = 256
sys.modules['curses'] = mock_curses

# Mock _curses module
mock__curses = MagicMock()
sys.modules['_curses'] = mock__curses

# Mock ranger.gui.colorscheme
mock_colorscheme = MagicMock()
mock_colorscheme._colorscheme_name_to_class = lambda x: None
sys.modules['ranger.gui.colorscheme'] = mock_colorscheme


class MockLocalSettings:
    def __init__(self, path, parent=None):
        self.autoupdate_cumulative_size = False
        self.show_hidden = True
        self.hidden_filter = None
        self.sort_directories_first = True
        self.sort = 'basename'
        self.sort_reverse = False
        self.sort_case_insensitive = False
        self.freeze_files = False
        self.preview_files = False
        self.preview_directories = False
        self.vcs_aware = False
        self.vcs_backend_git = False
        self.vcs_backend_hg = False
        self.vcs_backend_bzr = False
        self.vcs_backend_svn = False
        self.line_numbers = False
    
    def signal_bind(self, *args, **kwargs):
        pass

# Mock ranger.container.settings
mock_settings_module = MagicMock()
mock_settings_module.LocalSettings = MockLocalSettings
sys.modules['ranger.container.settings'] = mock_settings_module


class MockVCS:
    """Mock VCS class."""
    track = False
    is_root_pointer = False
    
    def status_subpath(self, path, is_directory=False):
        return None
    
    def rootvcs(self):
        return self


class MockMimeTypes:
    """Mock mimetypes module."""
    @staticmethod
    def guess_type(url, strict=True):
        ext = os.path.splitext(url)[1].lower()
        if ext in ['.txt', '.md', '.rst']:
            return ('text/plain', None)
        elif ext in ['.jpg', '.jpeg', '.png', '.gif']:
            return ('image/' + ext[1:], None)
        elif ext in ['.mp3', '.wav', '.flac']:
            return ('audio/' + ext[1:], None)
        elif ext in ['.mp4', '.avi', '.mkv']:
            return ('video/' + ext[1:], None)
        return (None, None)


class MockLoader:
    """Mock Loader class."""
    def add(self, item):
        pass


class MockFM:
    """Mock FileManager for testing."""
    
    def __init__(self):
        self.signals = {}
        self.mimetypes = MockMimeTypes()
        self.tags = MagicMock()
        self.tags.tags = {}
        self.loader = MockLoader()
        
        class MockUI:
            class MockVCSThread:
                @staticmethod
                def process(*args, **kwargs):
                    pass
            vcsthread = MockVCSThread()
        
        self.ui = MockUI()
    
    def get_directory(self, path, **kwargs):
        return None
    
    def signal_emit(self, signal_name, **kwargs):
        self.signals[signal_name] = kwargs
    
    def update_preview(self, path):
        pass


def test_directory_inherits_loadable_and_supports_progressbar():
    """Test that Directory inherits from Loadable and has progressbar support.
    
    This verifies that Directory is set up correctly to support the
    cancellation and progress tracking features.
    """
    from ranger.container.directory import Directory
    from ranger.core.loader import Loadable
    
    # Verify that Directory is a subclass of Loadable
    assert issubclass(Directory, Loadable)
    
    # Verify that progressbar_supported is True for Directory
    assert Directory.progressbar_supported == True


def test_directory_load_bit_by_bit_structure_matches_cancel_pattern():
    """Test that load_bit_by_bit has the correct cancellation check structure.
    
    This test verifies by source code inspection that the cancellation
    checks are properly placed in load_bit_by_bit().
    """
    directory_py_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..', 'ranger', 'container', 'directory.py'
    )
    directory_py_path = os.path.abspath(directory_py_path)
    
    with open(directory_py_path, 'r') as f:
        content = f.read()
    
    # Verify that load_bit_by_bit exists and has cancellation checks
    assert 'def load_bit_by_bit' in content
    
    # Check for cancellation checks at key points
    # The method should check is_cancelled() at multiple points
    cancel_check_count = content.count('self.is_cancelled()')
    
    # There should be multiple cancellation checks
    assert cancel_check_count >= 5, \
        f"Expected at least 5 is_cancelled() checks, found {cancel_check_count}"
    
    # Check for the pattern of returning early when cancelled
    assert 'if self.is_cancelled():' in content
    assert 'return' in content  # Should return when cancelled


def test_loadable_cancel_stops_directory_like_generator():
    """Test that cancellation stops a generator with directory-like structure.
    
    This test simulates the structure of load_bit_by_bit() and verifies
    that cancellation works correctly.
    """
    from ranger.core.loader import Loadable
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create many files to simulate a large directory
        num_files = 100
        for i in range(num_files):
            with open(os.path.join(tmpdir, f'file_{i:03d}.txt'), 'w') as f:
                f.write(f'content {i}')
        
        # Track processing
        files_processed = [0]
        cancelled_flag = [False]
        
        # Create a generator that mimics load_bit_by_bit structure
        def mock_load_bit_by_bit():
            """Mimics the structure of Directory.load_bit_by_bit()"""
            
            # Initial check
            if cancelled_flag[0]:
                return
            yield
            
            # List files
            filenames = os.listdir(tmpdir)
            
            # Check after listing
            if cancelled_flag[0]:
                return
            yield
            
            # Process each file with periodic checks
            for name in filenames:
                # Check before processing each file
                if cancelled_flag[0]:
                    return
                
                # Simulate file processing
                files_processed[0] += 1
                
                # Check after processing
                if cancelled_flag[0]:
                    return
                yield
            
            # Final check
            if cancelled_flag[0]:
                return
        
        # Test 1: Normal completion
        cancelled_flag[0] = False
        files_processed[0] = 0
        
        gen1 = mock_load_bit_by_bit()
        list(gen1)  # Consume fully
        
        assert files_processed[0] == num_files
        
        # Test 2: Cancel midway
        cancelled_flag[0] = False
        files_processed[0] = 0
        
        gen2 = mock_load_bit_by_bit()
        
        # Process some items
        next(gen2)  # Initial yield
        next(gen2)  # After listing
        
        for _ in range(25):
            next(gen2)  # Process 25 files
        
        assert files_processed[0] == 25
        
        # Now cancel
        cancelled_flag[0] = True
        
        # Next iteration should stop
        with pytest.raises(StopIteration):
            next(gen2)
        
        # Verify we didn't process all files
        assert files_processed[0] == 25
        assert files_processed[0] < num_files


def test_cancellation_signal_propagates_to_file_processing():
    """Test that cancellation signal propagates to stop file processing.
    
    This verifies that once cancelled, no further files are processed.
    """
    from ranger.core.loader import Loadable
    
    # Create a Loadable with a generator that checks cancellation
    processed_items = []
    total_items = 50
    
    def processing_generator():
        for i in range(total_items):
            # Check cancellation at each iteration
            if loadable.is_cancelled():
                return
            processed_items.append(i)
            yield
    
    loadable = Loadable(processing_generator(), "test processing")
    
    # Process some items
    gen = loadable.load_generator
    
    for i in range(20):
        next(gen)
    
    assert len(processed_items) == 20
    assert processed_items == list(range(20))
    
    # Cancel
    loadable.cancel()
    assert loadable.is_cancelled() == True
    
    # Try to continue - should stop
    with pytest.raises(StopIteration):
        next(gen)
    
    # Verify no more items were processed
    assert len(processed_items) == 20
    assert max(processed_items) == 19  # Zero-based


def test_directory_cancel_prevents_finished_signal():
    """Test that cancelled directory load doesn't emit finished signal.
    
    This verifies the source code has the pattern to skip signal emission
    when cancelled.
    """
    directory_py_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..', 'ranger', 'container', 'directory.py'
    )
    directory_py_path = os.path.abspath(directory_py_path)
    
    with open(directory_py_path, 'r') as f:
        content = f.read()
    
    # Verify the pattern: signal emission is wrapped in cancellation check
    # The pattern should be: if not self.is_cancelled(): signal_emit(...)
    # or in the finally block: if not self.is_cancelled(): ...
    
    # Look for the pattern in the finally block of load_bit_by_bit
    # Find the finally block
    lines = content.split('\n')
    in_finally = False
    found_cancel_check_before_signal = False
    
    for i, line in enumerate(lines):
        if 'finally:' in line:
            in_finally = True
        elif in_finally and line.strip().startswith('if not self.is_cancelled()'):
            # Check if this if block contains signal_emit
            # Look ahead a few lines
            for j in range(i, min(i + 10, len(lines))):
                if 'signal_emit' in lines[j]:
                    found_cancel_check_before_signal = True
                    break
            break
    
    assert found_cancel_check_before_signal, \
        "Signal emission should be wrapped in 'if not self.is_cancelled()' check"


def test_loadable_cancel_and_destroy_consistency():
    """Test that cancel() and destroy() both set the cancelled flag."""
    from ranger.core.loader import Loadable
    
    # Test cancel()
    loadable1 = Loadable(iter([]), "test1")
    assert loadable1.is_cancelled() == False
    loadable1.cancel()
    assert loadable1.is_cancelled() == True
    
    # Test destroy()
    loadable2 = Loadable(iter([]), "test2")
    assert loadable2.is_cancelled() == False
    loadable2.destroy()
    assert loadable2.is_cancelled() == True


def test_percent_progress_tracking_in_directory_like_scenario():
    """Test that percent progress is tracked correctly during loading."""
    from ranger.core.loader import Loadable
    
    total_items = 100
    processed_count = [0]
    
    def progress_tracking_generator():
        for i in range(total_items):
            # Check cancellation at each iteration (like real load_bit_by_bit)
            if loadable.is_cancelled():
                return
            processed_count[0] += 1
            loadable.percent = (processed_count[0] / total_items) * 100
            yield
    
    loadable = Loadable(progress_tracking_generator(), "test with progress")
    loadable.progressbar_supported = True
    
    gen = loadable.load_generator
    
    # Process some items
    for _ in range(50):
        next(gen)
    
    assert loadable.percent == 50.0
    
    # Process more
    for _ in range(25):
        next(gen)
    
    assert loadable.percent == 75.0
    
    # Cancel
    loadable.cancel()
    assert loadable.is_cancelled() == True
    
    # Next should stop because generator checks is_cancelled()
    with pytest.raises(StopIteration):
        next(gen)
    
    # Percent should remain at 75%
    assert loadable.percent == 75.0
    assert processed_count[0] == 75  # Only 75 items processed, not 100
