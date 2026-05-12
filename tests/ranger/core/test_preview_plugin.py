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


class TestPluginPriorityAndScopeSHFallback(object):
    def test_plugin_takes_precedence_over_scope_sh(self):
        registry = PreviewPluginRegistry()

        def python_plugin(**kwargs):
            return ('from python plugin', 0)

        registry.register(python_plugin, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 0
        assert content == 'from python plugin'

    def test_plugin_returns_none_allows_scope_sh_fallback(self):
        registry = PreviewPluginRegistry()

        def plugin_that_declines(**kwargs):
            return None

        registry.register(plugin_that_declines, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is None

    def test_no_plugins_matches_returns_none_for_scope_sh_fallback(self):
        registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('json content', 0)

        registry.register(json_renderer, file_patterns='json')

        result = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert result is None

    def test_higher_priority_plugin_takes_precedence(self):
        registry = PreviewPluginRegistry()
        order_called = []

        def low_priority(**kwargs):
            order_called.append('low')
            return ('low priority', 0)

        def high_priority(**kwargs):
            order_called.append('high')
            return ('high priority', 0)

        registry.register(low_priority, file_patterns='json', priority=0)
        registry.register(high_priority, file_patterns='json', priority=10)

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 0
        assert content == 'high priority'
        assert order_called == ['high']

    def test_plugin_with_exit_code_1_no_preview(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return (None, 1)

        registry.register(renderer, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 1
        assert content is None

    def test_plugin_with_exit_code_2_plain_text(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return (None, 2)

        registry.register(renderer, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 2

    def test_plugin_with_exit_code_3_fix_width(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('fix width', 3)

        registry.register(renderer, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 3
        assert content == 'fix width'

    def test_plugin_with_exit_code_4_fix_height(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('fix height', 4)

        registry.register(renderer, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 4
        assert content == 'fix height'

    def test_plugin_with_exit_code_5_fix_both(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('fix both', 5)

        registry.register(renderer, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 5
        assert content == 'fix both'

    def test_plugin_with_exit_code_6_image_cache(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return (None, 6)

        registry.register(renderer, file_patterns='png')

        result = registry.render('/path/to/file.png', 80, 24, '/cache/img.jpg', True)
        assert result is not None
        content, code = result
        assert code == 6
        assert content is None

    def test_plugin_with_exit_code_7_direct_image(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return (None, 7)

        registry.register(renderer, file_patterns='jpg')

        result = registry.render('/path/to/file.jpg', 80, 24, '/cache/img.jpg', True)
        assert result is not None
        content, code = result
        assert code == 7
        assert content is None

    def test_multiple_plugins_declines_until_one_handles(self):
        registry = PreviewPluginRegistry()
        order_called = []

        def first(**kwargs):
            order_called.append('first')
            return None

        def second(**kwargs):
            order_called.append('second')
            return None

        def third(**kwargs):
            order_called.append('third')
            return ('handled by third', 0)

        registry.register(first, file_patterns='json', priority=30)
        registry.register(second, file_patterns='json', priority=20)
        registry.register(third, file_patterns='json', priority=10)

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 0
        assert content == 'handled by third'
        assert order_called == ['first', 'second', 'third']

    def test_all_plugins_decline_returns_none_for_scope_sh(self):
        registry = PreviewPluginRegistry()

        def first(**kwargs):
            return None

        def second(**kwargs):
            return None

        registry.register(first, file_patterns='json', priority=10)
        registry.register(second, file_patterns='json', priority=5)

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is None

    def test_plugin_exception_does_not_block_others(self):
        registry = PreviewPluginRegistry()

        def bad_plugin(**kwargs):
            raise RuntimeError('something went wrong')

        def good_plugin(**kwargs):
            return ('good plugin result', 0)

        registry.register(bad_plugin, file_patterns='json', priority=10)
        registry.register(good_plugin, file_patterns='json', priority=5)

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 0
        assert content == 'good plugin result'
