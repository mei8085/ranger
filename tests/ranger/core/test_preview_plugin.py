from __future__ import absolute_import

import os
import tempfile

import pytest

from ranger.core.preview_plugin import (
    PreviewPluginRegistry,
    preview_plugin_registry,
    register_preview_plugin,
    unregister_preview_plugin,
)


class TestPreviewPluginRegistry(object):
    def test_register_by_extension(self):
        registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('json content', 0)

        registry.register(json_renderer, file_patterns='json')

        renderers = registry.get_renderers('/path/to/file.json')
        assert len(renderers) == 1
        assert renderers[0] is json_renderer

    def test_register_by_extension_with_dot(self):
        registry = PreviewPluginRegistry()

        def py_renderer(**kwargs):
            return ('py content', 0)

        registry.register(py_renderer, file_patterns='.py')

        renderers = registry.get_renderers('/path/to/file.py')
        assert len(renderers) == 1
        assert renderers[0] is py_renderer

    def test_register_by_multiple_extensions(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('content', 0)

        registry.register(renderer, file_patterns=['json', 'yaml', 'yml'])

        assert len(registry.get_renderers('/path/to/file.json')) == 1
        assert len(registry.get_renderers('/path/to/file.yaml')) == 1
        assert len(registry.get_renderers('/path/to/file.yml')) == 1
        assert len(registry.get_renderers('/path/to/file.txt')) == 0

    def test_register_by_extension_pattern(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('content', 0)

        registry.register(renderer, file_patterns='*.json.example')

        renderers = registry.get_renderers('/path/to/test.json.example')
        assert len(renderers) == 1
        assert renderers[0] is renderer

        assert len(registry.get_renderers('/path/to/test.json')) == 0

    def test_register_by_mimetype(self):
        registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('json content', 0)

        registry.register(json_renderer, mime_types='application/json')

        renderers = registry.get_renderers('/path/to/file.json')
        assert len(renderers) == 1
        assert renderers[0] is json_renderer

    def test_register_by_mimetype_pattern(self):
        registry = PreviewPluginRegistry()

        def text_renderer(**kwargs):
            return ('text content', 0)

        registry.register(text_renderer, mime_types='text/*')

        renderers = registry.get_renderers('/path/to/file.txt')
        assert len(renderers) == 1
        assert renderers[0] is text_renderer

    def test_priority(self):
        registry = PreviewPluginRegistry()

        def low_priority(**kwargs):
            return ('low', 0)

        def high_priority(**kwargs):
            return ('high', 0)

        registry.register(low_priority, file_patterns='json', priority=0)
        registry.register(high_priority, file_patterns='json', priority=10)

        renderers = registry.get_renderers('/path/to/file.json')
        assert len(renderers) == 2
        assert renderers[0] is high_priority
        assert renderers[1] is low_priority

    def test_unregister(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('content', 0)

        registry.register(renderer, file_patterns='json')
        assert len(registry.get_renderers('/path/to/file.json')) == 1

        registry.unregister(renderer)
        assert len(registry.get_renderers('/path/to/file.json')) == 0

    def test_unregister_nonexistent(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('content', 0)

        registry.unregister(renderer)

    def test_render_success(self):
        registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('{"test": 1}', 0)

        registry.register(json_renderer, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/image.jpg', True)
        assert result is not None
        content, exit_code = result
        assert content == '{"test": 1}'
        assert exit_code == 0

    def test_render_returns_none_when_no_renderer(self):
        registry = PreviewPluginRegistry()

        result = registry.render('/path/to/file.unknown', 80, 24, '/cache/image.jpg', True)
        assert result is None

    def test_renderer_returns_none_continues(self):
        registry = PreviewPluginRegistry()

        def first_renderer(**kwargs):
            return None

        def second_renderer(**kwargs):
            return ('second', 0)

        registry.register(first_renderer, file_patterns='json', priority=10)
        registry.register(second_renderer, file_patterns='json', priority=5)

        result = registry.render('/path/to/file.json', 80, 24, '/cache/image.jpg', True)
        assert result is not None
        content, exit_code = result
        assert content == 'second'
        assert exit_code == 0

    def test_renderer_exception_handled(self):
        registry = PreviewPluginRegistry()

        def bad_renderer(**kwargs):
            raise ValueError('test error')

        def good_renderer(**kwargs):
            return ('good', 0)

        registry.register(bad_renderer, file_patterns='json', priority=10)
        registry.register(good_renderer, file_patterns='json', priority=5)

        result = registry.render('/path/to/file.json', 80, 24, '/cache/image.jpg', True)
        assert result is not None
        content, exit_code = result
        assert content == 'good'
        assert exit_code == 0


class TestPreviewPluginModule(object):
    def test_register_preview_plugin_decorator(self):
        @register_preview_plugin(file_patterns='testext')
        def my_renderer(**kwargs):
            return ('test content', 0)

        renderers = preview_plugin_registry.get_renderers('/path/to/file.testext')
        assert my_renderer in renderers

        unregister_preview_plugin(my_renderer)

        renderers = preview_plugin_registry.get_renderers('/path/to/file.testext')
        assert my_renderer not in renderers

    def test_renderer_receives_arguments(self):
        registry = PreviewPluginRegistry()
        received_kwargs = {}

        def capturing_renderer(**kwargs):
            received_kwargs.update(kwargs)
            return ('content', 0)

        registry.register(capturing_renderer, file_patterns='json')

        registry.render(
            '/path/to/test.json',
            100,
            50,
            '/cache/img.jpg',
            True,
        )

        assert received_kwargs['file_path'] == '/path/to/test.json'
        assert received_kwargs['width'] == 100
        assert received_kwargs['height'] == 50
        assert received_kwargs['image_cache_path'] == '/cache/img.jpg'
        assert received_kwargs['preview_images'] is True


class TestPreviewPluginIntegration(object):
    def test_renderer_with_different_exit_codes(self):
        registry = PreviewPluginRegistry()

        def exit_code_0(**kwargs):
            return ('success', 0)

        def exit_code_5(**kwargs):
            return ('cached', 5)

        registry.register(exit_code_0, file_patterns='json')
        registry.register(exit_code_5, file_patterns='txt')

        content, code = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert code == 0
        assert content == 'success'

        content, code = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert code == 5
        assert content == 'cached'

    def test_case_insensitive_extension(self):
        registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('json', 0)

        registry.register(json_renderer, file_patterns='json')

        assert len(registry.get_renderers('/path/to/file.JSON')) == 1
        assert len(registry.get_renderers('/path/to/file.Json')) == 1
        assert len(registry.get_renderers('/path/to/file.json')) == 1
