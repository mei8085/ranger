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
