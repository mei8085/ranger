from __future__ import (absolute_import, division, print_function)

import os

import pytest

from ranger.container.saved_searches import SavedSearch, SavedSearches


def test_saved_search_creation():
    search = SavedSearch(
        name='test',
        search_type=SavedSearch.STATIC,
        data={'paths': ['/foo/bar', '/foo/baz']},
    )
    assert search.name == 'test'
    assert search.type == SavedSearch.STATIC
    assert search.data == {'paths': ['/foo/bar', '/foo/baz']}


def test_saved_search_to_dict():
    search = SavedSearch(
        name='dynamic_test',
        search_type=SavedSearch.DYNAMIC,
        data={'command': 'foo.*bar'},
    )
    dct = search.to_dict()
    assert dct['name'] == 'dynamic_test'
    assert dct['type'] == SavedSearch.DYNAMIC
    assert dct['data']['command'] == 'foo.*bar'


def test_saved_search_from_dict():
    dct = {
        'name': 'from_dict',
        'type': SavedSearch.STATIC,
        'data': {'paths': ['/a/b', '/c/d']},
    }
    search = SavedSearch.from_dict(dct)
    assert search.name == 'from_dict'
    assert search.type == SavedSearch.STATIC
    assert search.data['paths'] == ['/a/b', '/c/d']


def test_saved_searches_basic(tmpdir):
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    store.load()

    store.save_static('static1', ['/foo/file1.py', '/foo/file2.py'])
    assert 'static1' in [s.name for s in store]
    assert store.get('static1') is not None
    assert store.get('static1').type == SavedSearch.STATIC
    assert store.list() == ['static1']

    store.save_dynamic('dyn1', 'test.*pattern')
    assert sorted(store.list()) == ['dyn1', 'static1']
    dyn = store.get('dyn1')
    assert dyn.type == SavedSearch.DYNAMIC
    assert dyn.data['command'] == 'test.*pattern'


def test_saved_searches_persistence(tmpdir):
    searchfile = tmpdir.join("saved_searches")

    store1 = SavedSearches(str(searchfile))
    store1.save_static('persist_test', ['/a/b', '/c/d'])
    store1.save_dynamic('persist_dyn', 'hello')
    store1.save()

    store2 = SavedSearches(str(searchfile))
    store2.load()

    assert sorted(store2.list()) == ['persist_dyn', 'persist_test']

    static = store2.get('persist_test')
    assert static.type == SavedSearch.STATIC
    assert static.data['paths'] == ['/a/b', '/c/d']

    dyn = store2.get('persist_dyn')
    assert dyn.type == SavedSearch.DYNAMIC
    assert dyn.data['command'] == 'hello'


def test_saved_searches_delete(tmpdir):
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    store.save_static('to_delete', ['/foo'])
    store.save_dynamic('keep', 'bar')
    assert sorted(store.list()) == ['keep', 'to_delete']

    assert store.delete('to_delete') is True
    assert store.list() == ['keep']

    assert store.delete('nonexistent') is False


def test_saved_searches_empty_file(tmpdir):
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))
    store.load()
    assert store.list() == []


def test_saved_searches_iteration(tmpdir):
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    store.save_static('a', ['/1'])
    store.save_static('b', ['/2'])
    store.save_dynamic('c', 'pattern')

    names = sorted([s.name for s in store])
    assert names == ['a', 'b', 'c']


def test_static_search_saves_complete_file_set(tmpdir):
    """Static search should save the complete filtered result set, not just selection.

    This test verifies that save_static takes a list of paths and
    stores all of them (simulating what save_search command does
    when it collects thisdir.files - the complete filtered view).
    """
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    all_filtered_files = [
        '/home/user/docs/report1.pdf',
        '/home/user/docs/report2.pdf',
        '/home/user/docs/notes.txt',
        '/home/user/docs/summary.md',
    ]

    store.save_static('pdf_docs', all_filtered_files)

    saved = store.get('pdf_docs')
    assert saved is not None
    assert saved.type == SavedSearch.STATIC
    assert saved.data['paths'] == all_filtered_files
    assert len(saved.data['paths']) == 4

    store.save()
    store2 = SavedSearches(str(searchfile))
    store2.load()
    reloaded = store2.get('pdf_docs')
    assert reloaded.data['paths'] == all_filtered_files


def test_static_search_distinct_from_selection(tmpdir):
    """Static search saves the complete filtered set, not just a partial selection.

    The command logic uses thisdir.files (all visible) vs marked_items (selection).
    Here we verify that save_static accepts and stores the complete set.
    """
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    all_filtered = ['/a/1.py', '/a/2.py', '/a/3.py', '/a/4.py']
    just_selected = ['/a/2.py']

    store.save_static('all_filtered', all_filtered)
    store.save_static('just_selected_manual', just_selected)

    all_result = store.get('all_filtered')
    sel_result = store.get('just_selected_manual')

    assert len(all_result.data['paths']) == 4
    assert len(sel_result.data['paths']) == 1

    assert all_result.data['paths'][0] == '/a/1.py'
    assert all_result.data['paths'][3] == '/a/4.py'

    store.save()
    store2 = SavedSearches(str(searchfile))
    store2.load()
    assert store2.get('all_filtered').data['paths'] == all_filtered
    assert store2.get('just_selected_manual').data['paths'] == just_selected


def test_dynamic_search_saves_pattern_for_reexecution(tmpdir):
    """Dynamic search stores a regex pattern that can be re-executed later.

    This is distinct from static which stores concrete paths.
    The command extracts this from thistab.last_search.pattern.
    """
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    pattern = r'^test_.*\.py$'
    store.save_dynamic('test_files', pattern)

    saved = store.get('test_files')
    assert saved is not None
    assert saved.type == SavedSearch.DYNAMIC
    assert saved.data['command'] == pattern

    import re
    assert re.compile(saved.data['command']) is not None

    store.save()
    store2 = SavedSearches(str(searchfile))
    store2.load()
    reloaded = store2.get('test_files')
    assert reloaded.type == SavedSearch.DYNAMIC
    assert reloaded.data['command'] == pattern


def test_static_vs_dynamic_types_are_distinct(tmpdir):
    """Verify static and dynamic searches use different type tags."""
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    store.save_static('my_static', ['/a.py', '/b.py'])
    store.save_dynamic('my_dynamic', 'test')

    static = store.get('my_static')
    dynamic = store.get('my_dynamic')

    assert static.type == SavedSearch.STATIC
    assert dynamic.type == SavedSearch.DYNAMIC
    assert static.type != dynamic.type

    assert 'paths' in static.data
    assert 'command' in dynamic.data
    assert 'command' not in static.data
    assert 'paths' not in dynamic.data


def test_static_and_dynamic_can_coexist(tmpdir):
    """A name can't hold both, but different names can have different types."""
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    store.save_static('same_name', ['/a.py'])
    store.save_dynamic('same_name', 'pattern')

    saved = store.get('same_name')
    assert saved.type == SavedSearch.DYNAMIC
    assert saved.data['command'] == 'pattern'
    assert 'paths' not in saved.data

    store.save_static('other_name', ['/x.py'])
    store.save_dynamic('another', 'foo')

    types = {s.name: s.type for s in store}
    assert types['same_name'] == SavedSearch.DYNAMIC
    assert types['other_name'] == SavedSearch.STATIC
    assert types['another'] == SavedSearch.DYNAMIC


def test_dynamic_pattern_persistence_and_regex_validity(tmpdir):
    """Dynamic searches should store valid regex patterns that can be recompiled."""
    searchfile = tmpdir.join("saved_searches")
    store1 = SavedSearches(str(searchfile))

    patterns = [
        r'foo',
        r'^test.*\.py$',
        r'[a-z]+\d{2,4}',
        r'(?i)case.*insensitive',
    ]

    for i, pattern in enumerate(patterns):
        store1.save_dynamic('dyn_%d' % i, pattern)
    store1.save()

    store2 = SavedSearches(str(searchfile))
    store2.load()

    import re
    for i, pattern in enumerate(patterns):
        saved = store2.get('dyn_%d' % i)
        assert saved.type == SavedSearch.DYNAMIC
        assert saved.data['command'] == pattern
        compiled = re.compile(saved.data['command'])
        assert compiled is not None


def test_static_preserves_order_of_filtered_results(tmpdir):
    """Static search should preserve the order of files as displayed in the view."""
    searchfile = tmpdir.join("saved_searches")
    store = SavedSearches(str(searchfile))

    filtered_order = [
        '/dir/zebra.txt',
        '/dir/yak.txt',
        '/dir/xray.txt',
        '/dir/walrus.txt',
    ]

    store.save_static('reverse_alpha', filtered_order)
    store.save()

    store2 = SavedSearches(str(searchfile))
    store2.load()
    reloaded = store2.get('reverse_alpha')

    assert reloaded.data['paths'] == filtered_order
    assert reloaded.data['paths'][0] == '/dir/zebra.txt'
    assert reloaded.data['paths'][3] == '/dir/walrus.txt'
