from __future__ import (absolute_import, division, print_function)

import re
import os

import pytest

from ranger.core.shared import FileManagerAware, SettingsAware
from ranger.container.saved_searches import SavedSearch, SavedSearches


class MockFile:
    def __init__(self, path):
        self.path = path


class MockDirectory:
    def __init__(self, files_list):
        self._files = [MockFile(p) for p in files_list]
        self._all_files = list(self._files)
        self.marked_items = []
        self.narrow_filter = None
        self.filter = None
        self.temporary_filter = None
        self.thisfile = self._files[0] if self._files else None

    @property
    def files(self):
        return self._files

    @property
    def files_all(self):
        return self._all_files

    def refilter(self):
        pass

    def temporary_filter_set(self, value):
        pass


class MockTab:
    def __init__(self, last_search_pattern=None):
        self._thisdir = MockDirectory([])
        if last_search_pattern is None:
            self._last_search = None
        else:
            self._last_search = re.compile(last_search_pattern)

    @property
    def thisdir(self):
        return self._thisdir

    @property
    def last_search(self):
        return self._last_search

    def get_selection(self):
        return self._thisdir.marked_items if self._thisdir.marked_items else self._thisdir.files

    def set_visible_files(self, paths):
        self._thisdir = MockDirectory(paths)

    def set_marked_items(self, paths):
        self._thisdir.marked_items = [MockFile(p) for p in paths]


class MockFM:
    def __init__(self, tmpdir):
        self._thistab = MockTab()
        self._searchfile = str(tmpdir.join("saved_searches"))
        self.saved_searches = SavedSearches(self._searchfile)
        self.saved_searches.load()
        self.notifications = []
        self._thisfile = None
        self._narrow_filter_applied = None
        self._cd_path = None
        self._current_directory = MockDirectory([])

    @property
    def thistab(self):
        return self._thistab

    @property
    def thisdir(self):
        return self._thistab._thisdir

    @property
    def thisfile(self):
        return self.thisdir.thisfile

    def notify(self, msg, bad=False):
        self.notifications.append((msg, bad))

    def set_search_method(self, order="search"):
        self._search_method = order

    def cd(self, path):
        self._cd_path = path

    def group_paths_by_dirname(self, paths):
        groups = {}
        for path in paths:
            dirname = os.path.dirname(path)
            basename = os.path.basename(path)
            if dirname not in groups:
                groups[dirname] = []
            groups[dirname].append(basename)
        return groups


@pytest.fixture
def setup_fm(tmpdir, monkeypatch):
    fm = MockFM(tmpdir)
    FileManagerAware.fm_set(fm)
    yield fm
    FileManagerAware.fm_set(None)


class TestSaveSearchStaticMode:
    """Test that :save_search (static) saves the complete filtered view (thisdir.files)."""

    def test_static_saves_all_visible_files_not_selection(self, setup_fm):
        """Static mode should save thisdir.files (all visible), not marked_items (selection)."""
        fm = setup_fm

        all_visible = [
            '/home/docs/report1.pdf',
            '/home/docs/report2.pdf',
            '/home/docs/notes.txt',
            '/home/docs/summary.md',
        ]
        just_selected = [
            '/home/docs/report1.pdf',
        ]

        fm.thistab.set_visible_files(all_visible)
        fm.thistab.set_marked_items(just_selected)

        from ranger.config.commands import save_search

        cmd = save_search("save_search my_results")
        cmd.execute()

        saved = fm.saved_searches.get('my_results')
        assert saved is not None
        assert saved.type == SavedSearch.STATIC

        assert len(saved.data['paths']) == 4
        assert saved.data['paths'] == all_visible
        assert saved.data['paths'] != just_selected

    def test_static_save_notification_includes_file_count(self, setup_fm):
        fm = setup_fm

        fm.thistab.set_visible_files(['/a/1.py', '/a/2.py', '/a/3.py'])

        from ranger.config.commands import save_search

        cmd = save_search("save_search three_files")
        cmd.execute()

        msg, bad = fm.notifications[-1]
        assert bad is False
        assert 'three_files' in msg
        assert '3 files' in msg

    def test_static_save_empty_view_notifies_error(self, setup_fm):
        fm = setup_fm

        fm.thistab.set_visible_files([])

        from ranger.config.commands import save_search

        cmd = save_search("save_search empty_results")
        cmd.execute()

        msg, bad = fm.notifications[-1]
        assert bad is True
        assert 'No files' in msg

        assert fm.saved_searches.get('empty_results') is None

    def test_static_persists_across_fm_instances(self, tmpdir):
        from ranger.config.commands import save_search

        fm1 = MockFM(tmpdir)
        FileManagerAware.fm_set(fm1)
        fm1.thistab.set_visible_files(['/dir/a.py', '/dir/b.py', '/dir/c.py'])
        cmd1 = save_search("save_search persist_test")
        cmd1.execute()
        fm1.saved_searches.save()

        FileManagerAware.fm_set(None)

        fm2 = MockFM(tmpdir)
        FileManagerAware.fm_set(fm2)

        saved = fm2.saved_searches.get('persist_test')
        assert saved is not None
        assert saved.type == SavedSearch.STATIC
        assert len(saved.data['paths']) == 3
        assert '/dir/b.py' in saved.data['paths']

        FileManagerAware.fm_set(None)

    def test_static_tab_completion(self, setup_fm):
        fm = setup_fm

        fm.saved_searches.save_static('alpha', ['/1'])
        fm.saved_searches.save_static('beta', ['/2'])
        fm.saved_searches.save_static('gamma', ['/3'])

        from ranger.config.commands import save_search

        cmd = save_search("save_search al")
        completions = cmd.tab(0)
        assert completions == ['save_search alpha']

        cmd2 = save_search("save_search ")
        completions2 = cmd2.tab(0)
        assert 'save_search alpha' in completions2
        assert 'save_search beta' in completions2
        assert 'save_search gamma' in completions2

    def test_static_requires_name_argument(self, setup_fm):
        fm = setup_fm

        from ranger.config.commands import save_search

        cmd = save_search("save_search")
        cmd.execute()

        msg, bad = fm.notifications[-1]
        assert bad is True
        assert 'Syntax' in msg or 'name' in msg.lower()


class TestSaveSearchDynamicMode:
    """Test that :save_search -d (dynamic) saves the regex pattern from last_search."""

    def test_dynamic_saves_pattern_from_last_search(self, setup_fm):
        """Dynamic mode should save last_search.pattern, not file paths."""
        fm = setup_fm

        pattern = r'^test_.*\.py$'
        fm._thistab = MockTab(last_search_pattern=pattern)

        fm.thistab.set_visible_files(['/a/test_1.py', '/a/test_2.py'])

        from ranger.config.commands import save_search

        cmd = save_search("save_search -d test_pattern")
        cmd.execute()

        saved = fm.saved_searches.get('test_pattern')
        assert saved is not None
        assert saved.type == SavedSearch.DYNAMIC
        assert 'command' in saved.data
        assert saved.data['command'] == pattern

        assert 'paths' not in saved.data

    def test_dynamic_does_not_save_static_paths(self, setup_fm):
        """Dynamic mode should ignore visible files and only save the pattern."""
        fm = setup_fm

        pattern = r'\.txt$'
        fm._thistab = MockTab(last_search_pattern=pattern)
        fm.thistab.set_visible_files(['/a/1.txt', '/a/2.txt'])

        from ranger.config.commands import save_search

        cmd = save_search("save_search -d txt_files")
        cmd.execute()

        saved = fm.saved_searches.get('txt_files')
        assert saved.type == SavedSearch.DYNAMIC
        assert saved.data['command'] == r'\.txt$'

        reloaded = re.compile(saved.data['command'])
        assert reloaded.search('file.txt') is not None
        assert reloaded.search('file.py') is None

    def test_dynamic_without_last_search_notifies_error(self, setup_fm):
        fm = setup_fm

        fm._thistab = MockTab(last_search_pattern=None)

        from ranger.config.commands import save_search

        cmd = save_search("save_search -d no_search")
        cmd.execute()

        msg, bad = fm.notifications[-1]
        assert bad is True
        assert 'No recent search' in msg or 'search' in msg.lower()

        assert fm.saved_searches.get('no_search') is None

    def test_dynamic_persistence(self, tmpdir):
        from ranger.config.commands import save_search

        fm1 = MockFM(tmpdir)
        FileManagerAware.fm_set(fm1)
        pattern = r'foo.*bar'
        fm1._thistab = MockTab(last_search_pattern=pattern)
        cmd1 = save_search("save_search -d dyn_persist")
        cmd1.execute()
        fm1.saved_searches.save()
        FileManagerAware.fm_set(None)

        fm2 = MockFM(tmpdir)
        FileManagerAware.fm_set(fm2)

        saved = fm2.saved_searches.get('dyn_persist')
        assert saved is not None
        assert saved.type == SavedSearch.DYNAMIC
        assert saved.data['command'] == pattern
        assert re.compile(saved.data['command']) is not None

        FileManagerAware.fm_set(None)

    def test_dynamic_type_distinct_from_static(self, setup_fm):
        fm = setup_fm

        pattern = r'test'
        fm._thistab = MockTab(last_search_pattern=pattern)

        from ranger.config.commands import save_search

        cmd_dyn = save_search("save_search -d same_name")
        cmd_dyn.execute()

        fm._thistab = MockTab(last_search_pattern=None)
        fm.thistab.set_visible_files(['/a.py'])

        cmd_static = save_search("save_search same_name")
        cmd_static.execute()

        saved = fm.saved_searches.get('same_name')
        assert saved.type == SavedSearch.STATIC
        assert 'paths' in saved.data
        assert saved.data['paths'] == ['/a.py']


class TestSavedCommand:
    """Test that :saved command properly restores static/dynamic searches."""

    def test_saved_lists_all_searches_when_no_name(self, setup_fm):
        fm = setup_fm

        fm.saved_searches.save_static('s1', ['/a.py'])
        fm.saved_searches.save_dynamic('d1', r'pattern')

        from ranger.config.commands import saved

        class FakePager:
            def __init__(self):
                self.lines = None

            def set_source(self, lines):
                self.lines = list(lines)

        class FakeUI:
            def __init__(self):
                self.opened_pager = FakePager()

            def open_pager(self):
                return self.opened_pager

        fm.ui = FakeUI()

        cmd = saved("saved")
        cmd.execute()

        assert fm.ui.opened_pager.lines is not None
        lines = fm.ui.opened_pager.lines
        assert 'Saved searches' in lines[0]
        assert any('[static] s1' in l for l in lines)
        assert any('[dynamic] d1' in l for l in lines)

    def test_saved_notifies_when_not_found(self, setup_fm):
        fm = setup_fm

        from ranger.config.commands import saved

        cmd = saved("saved nonexistent")
        cmd.execute()

        msg, bad = fm.notifications[-1]
        assert bad is True
        assert 'not found' in msg or 'nonexistent' in msg

    def test_saved_static_uses_narrow_filter(self, setup_fm, monkeypatch):
        import os

        fm = setup_fm

        def fake_exists(path):
            return True

        monkeypatch.setattr(os.path, 'exists', fake_exists)

        fm.saved_searches.save_static('test', [
            '/dir/file_a.py',
            '/dir/file_b.py',
            '/dir/file_c.py',
        ])

        from ranger.config.commands import saved

        cmd = saved("saved test")
        cmd.execute()

        assert fm._cd_path == '/dir'

        assert fm.thisdir.narrow_filter is not None
        assert 'file_a.py' in fm.thisdir.narrow_filter
        assert 'file_b.py' in fm.thisdir.narrow_filter
        assert 'file_c.py' in fm.thisdir.narrow_filter
