from __future__ import absolute_import

import os
import sys
import tempfile
from unittest import mock

import pytest

from ranger.core.preview_plugin import (
    PreviewPluginRegistry,
    preview_plugin_registry,
    register_preview_plugin,
    unregister_preview_plugin,
)


class TestPreviewPluginRegistryWithRealFiles:
    def test_render_with_real_file_returns_correct_result(self):
        registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            file_path = kwargs['file_path']
            with open(file_path, 'r') as f:
                content = f.read()
            return (f'Processed: {content}', 0)

        registry.register(json_renderer, file_patterns='json')

        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        try:
            with open(path, 'w') as f:
                f.write('{"test": 1}')

            result = registry.render(path, 80, 24, '/cache/img.jpg', False)
            assert result is not None
            content, code = result
            assert code == 0
            assert 'Processed:' in content
            assert '{"test": 1}' in content
        finally:
            os.unlink(path)

    def test_renderer_receives_correct_arguments(self):
        registry = PreviewPluginRegistry()
        received = {}

        def capturing_renderer(**kwargs):
            received.update(kwargs)
            return ('content', 0)

        registry.register(capturing_renderer, file_patterns='txt')

        fd, path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        try:
            with open(path, 'w') as f:
                f.write('hello')

            registry.render(path, 100, 50, '/cache/test.jpg', True)

            assert received['file_path'] == path
            assert received['width'] == 100
            assert received['height'] == 50
            assert received['image_cache_path'] == '/cache/test.jpg'
            assert received['preview_images'] is True
        finally:
            os.unlink(path)

    def test_plugin_returning_none_allows_next_to_handle(self):
        registry = PreviewPluginRegistry()
        order_called = []

        def first(**kwargs):
            order_called.append('first')
            return None

        def second(**kwargs):
            order_called.append('second')
            return ('handled by second', 0)

        registry.register(first, file_patterns='json', priority=10)
        registry.register(second, file_patterns='json', priority=5)

        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        try:
            with open(path, 'w') as f:
                f.write('{}')

            result = registry.render(path, 80, 24, '/cache/img.jpg', False)
            assert result is not None
            content, code = result
            assert code == 0
            assert content == 'handled by second'
            assert order_called == ['first', 'second']
        finally:
            os.unlink(path)


class TestPreviewPluginExitCodeSemantics:
    def test_exit_code_0_success(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('success content', 0)

        registry.register(renderer, file_patterns='txt')
        result = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 0
        assert content == 'success content'

    def test_exit_code_1_no_preview(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return (None, 1)

        registry.register(renderer, file_patterns='txt')
        result = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 1
        assert content is None

    def test_exit_code_2_plain_text(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return (None, 2)

        registry.register(renderer, file_patterns='txt')
        result = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 2

    def test_exit_code_3_fix_width(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('fixed width', 3)

        registry.register(renderer, file_patterns='txt')
        result = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 3
        assert content == 'fixed width'

    def test_exit_code_4_fix_height(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('fixed height', 4)

        registry.register(renderer, file_patterns='txt')
        result = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 4
        assert content == 'fixed height'

    def test_exit_code_5_fix_both(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return ('cached content', 5)

        registry.register(renderer, file_patterns='txt')
        result = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 5
        assert content == 'cached content'

    def test_exit_code_6_image_cache(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return (None, 6)

        registry.register(renderer, file_patterns='png')
        result = registry.render('/path/to/file.png', 80, 24, '/cache/img.jpg', True)
        assert result is not None
        content, code = result
        assert code == 6
        assert content is None

    def test_exit_code_7_direct_image(self):
        registry = PreviewPluginRegistry()

        def renderer(**kwargs):
            return (None, 7)

        registry.register(renderer, file_patterns='jpg')
        result = registry.render('/path/to/file.jpg', 80, 24, '/cache/img.jpg', True)
        assert result is not None
        content, code = result
        assert code == 7
        assert content is None


class TestPluginPriorityAndFallback:
    def test_plugin_takes_precedence(self):
        registry = PreviewPluginRegistry()

        def python_plugin(**kwargs):
            return ('from python', 0)

        registry.register(python_plugin, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 0
        assert content == 'from python'

    def test_no_plugin_matches_returns_none_for_scope_sh(self):
        registry = PreviewPluginRegistry()

        def json_plugin(**kwargs):
            return ('json content', 0)

        registry.register(json_plugin, file_patterns='json')

        result = registry.render('/path/to/file.txt', 80, 24, '/cache/img.jpg', False)
        assert result is None

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

    def test_higher_priority_plugin_executed_first(self):
        registry = PreviewPluginRegistry()
        order_called = []

        def low(**kwargs):
            order_called.append('low')
            return ('low', 0)

        def high(**kwargs):
            order_called.append('high')
            return ('high', 0)

        registry.register(low, file_patterns='json', priority=0)
        registry.register(high, file_patterns='json', priority=10)

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is not None
        content, code = result
        assert code == 0
        assert content == 'high'
        assert order_called == ['high']

    def test_plugin_exception_does_not_block_scope_sh(self):
        registry = PreviewPluginRegistry()

        def bad_plugin(**kwargs):
            raise RuntimeError('error')

        registry.register(bad_plugin, file_patterns='json')

        result = registry.render('/path/to/file.json', 80, 24, '/cache/img.jpg', False)
        assert result is None


class TestDecoratorRegistration:
    def test_register_using_decorator(self):
        @register_preview_plugin(file_patterns='mytestext')
        def my_renderer(**kwargs):
            return ('my content', 0)

        try:
            renderers = preview_plugin_registry.get_renderers('/path/to/file.mytestext')
            assert my_renderer in renderers

            result = preview_plugin_registry.render(
                '/path/to/file.mytestext', 80, 24, '/cache/img.jpg', False
            )
            assert result is not None
            content, code = result
            assert code == 0
            assert content == 'my content'
        finally:
            unregister_preview_plugin(my_renderer)

    def test_register_with_mime_type(self):
        @register_preview_plugin(mime_types='application/json')
        def json_renderer(**kwargs):
            return ('json from mime', 0)

        try:
            result = preview_plugin_registry.render(
                '/path/to/file.json', 80, 24, '/cache/img.jpg', False
            )
            assert result is not None
            content, code = result
            assert code == 0
            assert content == 'json from mime'
        finally:
            unregister_preview_plugin(json_renderer)

    def test_register_with_multiple_patterns(self):
        @register_preview_plugin(file_patterns=['yaml', 'yml'])
        def yaml_renderer(**kwargs):
            return ('yaml content', 0)

        try:
            result1 = preview_plugin_registry.render(
                '/path/to/file.yaml', 80, 24, '/cache/img.jpg', False
            )
            result2 = preview_plugin_registry.render(
                '/path/to/file.yml', 80, 24, '/cache/img.jpg', False
            )

            assert result1 is not None
            assert result2 is not None
            assert result1[0] == 'yaml content'
            assert result2[0] == 'yaml content'
        finally:
            unregister_preview_plugin(yaml_renderer)
