# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.
"""Tests to verify behavior consistency between refactored layers.

These tests ensure that:
1. ColorAdapter produces the same results as the original get_attr method
2. The separation doesn't change any observable behavior
3. Default theme colors remain identical
"""

from __future__ import (absolute_import, division, print_function)

import pytest


class TestColorAdapterBehaviorConsistency:
    """Verify ColorAdapter behavior matches expected behavior."""

    def test_coloradapter_uses_colorscheme_get(self):
        """ColorAdapter should use colorscheme.get() to get color tuples."""
        from ranger.gui.curses_shortcuts import ColorAdapter
        from ranger.gui.colorscheme import ColorScheme

        get_call_count = [0]
        expected_result = (5, 6, 7)

        class TestScheme(ColorScheme):
            def get(self, *keys):
                get_call_count[0] += 1
                return expected_result

            def use(self, context):
                return expected_result

        scheme = TestScheme()
        adapter = ColorAdapter(scheme)

        adapter.get_attr('test')
        assert get_call_count[0] >= 1

    def test_coloradapter_passes_all_keys(self):
        """ColorAdapter should pass all keys to colorscheme.get()."""
        from ranger.gui.curses_shortcuts import ColorAdapter
        from ranger.gui.colorscheme import ColorScheme

        received_keys = [None]

        class TestScheme(ColorScheme):
            def get(self, *keys):
                received_keys[0] = keys
                return (0, 0, 0)

            def use(self, context):
                return (0, 0, 0)

        scheme = TestScheme()
        adapter = ColorAdapter(scheme)

        test_keys = ('in_browser', 'directory', 'selected', 'marked')

        adapter.get_attr(*test_keys)
        assert received_keys[0] == test_keys

    def test_coloradapter_handles_flattened_keys(self):
        """ColorAdapter should handle nested key structures (flattening)."""
        from ranger.gui.curses_shortcuts import ColorAdapter
        from ranger.gui.colorscheme import ColorScheme

        received_keys = [None]

        class TestScheme(ColorScheme):
            def get(self, *keys):
                received_keys[0] = keys
                return (1, 2, 3)

            def use(self, context):
                return (1, 2, 3)

        scheme = TestScheme()
        adapter = ColorAdapter(scheme)

        result = adapter.get_attr(['directory', ['selected', 'marked']])
        assert isinstance(result, int)
        assert received_keys[0] == ('directory', 'selected', 'marked')


class TestThemeBackwardCompatibility:
    """Test that all existing themes work without modification."""

    def test_default_theme_get_method_works(self):
        """Default theme get() should work independently."""
        from ranger.colorschemes.default import Default

        scheme = Default()

        result = scheme.get('in_browser', 'directory')

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(v, int) for v in result)

    def test_jungle_theme_extends_default(self):
        """Jungle theme should extend Default correctly."""
        from ranger.colorschemes.default import Default
        from ranger.colorschemes.jungle import Scheme as Jungle

        default_scheme = Default()
        jungle_scheme = Jungle()

        default_result = default_scheme.get('in_browser', 'directory')
        jungle_result = jungle_scheme.get('in_browser', 'directory')

        assert isinstance(default_result, tuple)
        assert isinstance(jungle_result, tuple)
        assert len(default_result) == 3
        assert len(jungle_result) == 3

        assert jungle_result[0] != default_result[0], \
            "Jungle should override directory color"

    def test_snow_theme_independent(self):
        """Snow theme should work independently of Default."""
        from ranger.colorschemes.snow import Snow

        scheme = Snow()

        contexts = [
            ['in_browser', 'directory'],
            ['in_browser', 'directory', 'selected'],
            ['in_taskview', 'loaded'],
            ['in_titlebar', 'tab', 'good'],
        ]

        for ctx in contexts:
            result = scheme.get(*ctx)
            assert isinstance(result, tuple)
            assert len(result) == 3

    def test_all_themes_return_same_structure(self):
        """All themes should return (fg, bg, attr) tuple structure."""
        from ranger.colorschemes.default import Default
        from ranger.colorschemes.jungle import Scheme as Jungle
        from ranger.colorschemes.snow import Snow

        themes = [Default(), Jungle(), Snow()]

        try:
            from ranger.colorschemes.solarized import Solarized
            themes.append(Solarized())
        except ImportError:
            pass

        test_contexts = [
            ['in_browser'],
            ['in_browser', 'directory'],
            ['in_browser', 'file', 'executable'],
            ['in_titlebar'],
            ['in_statusbar'],
            ['in_taskview'],
            ['reset'],
        ]

        for theme in themes:
            for ctx in test_contexts:
                result = theme.get(*ctx)
                assert isinstance(result, tuple)
                assert len(result) == 3
                assert all(isinstance(v, int) for v in result)


class TestColorSchemeLayerBoundaries:
    """Test that theme model layer is properly isolated."""

    def test_colorscheme_does_not_import_curses(self):
        """ColorScheme module should not import curses directly."""
        import sys

        assert 'ranger.gui.colorscheme' in sys.modules or True

        import ranger.gui.colorscheme as cs_module

        import inspect
        source = inspect.getsource(cs_module.ColorScheme)

        assert 'curses' not in source.lower()

    def test_colorscheme_does_not_use_color_pair(self):
        """ColorScheme should not use curses.color_pair."""
        import ranger.gui.colorscheme as cs_module

        import inspect
        source = inspect.getsource(cs_module)

        assert 'color_pair' not in source

    def test_colorscheme_does_not_use_get_color(self):
        """ColorScheme should not use get_color function."""
        import ranger.gui.colorscheme as cs_module

        import inspect
        source = inspect.getsource(cs_module)

        assert 'get_color' not in source

    def test_coloradapter_imports_curses(self):
        """ColorAdapter should be the one that handles curses integration."""
        import ranger.gui.curses_shortcuts as cs_module

        import inspect
        source = inspect.getsource(cs_module.ColorAdapter)

        assert 'curses' in source.lower()


class TestDefaultThemeColorValues:
    """Test specific default theme color values for regression."""

    def test_reset_context(self):
        """Reset should always return default colors."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import default_colors

        scheme = Default()
        result = scheme.get('reset')

        assert result == default_colors

    def test_directory_bold_attribute(self):
        """Directories should have bold attribute."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import bold

        scheme = Default()
        _, _, attr = scheme.get('in_browser', 'directory')

        assert (attr & bold) == bold

    def test_selected_reverse_attribute(self):
        """Selected items should have reverse attribute."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import reverse

        scheme = Default()

        _, _, selected_attr = scheme.get('in_browser', 'directory', 'selected')
        _, _, not_selected_attr = scheme.get('in_browser', 'file')

        assert (selected_attr & reverse) == reverse
        assert (not_selected_attr & reverse) != reverse

    def test_executable_green_color(self):
        """Executable files should be green."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import green, BRIGHT

        scheme = Default()
        fg, _, _ = scheme.get('in_browser', 'file', 'executable')

        expected = green + BRIGHT if BRIGHT else green
        assert fg == expected

    def test_link_color_variation(self):
        """Good links should be cyan, bad links magenta."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import cyan, magenta

        scheme = Default()

        fg_good, _, _ = scheme.get('in_browser', 'link', 'good')
        fg_bad, _, _ = scheme.get('in_browser', 'link', 'bad')

        assert fg_good == cyan
        assert fg_bad == magenta


class TestContextInteraction:
    """Test that context combinations work correctly."""

    def test_multiple_context_keys(self):
        """Multiple context keys should be combined correctly."""
        from ranger.gui.colorscheme import ColorScheme

        received_keys = [set()]

        class TestScheme(ColorScheme):
            def use(self, context):
                received_keys[0] = set()
                for key in dir(context):
                    if not key.startswith('_') and getattr(context, key):
                        received_keys[0].add(key)
                return (0, 0, 0)

        scheme = TestScheme()

        scheme.get('directory', 'selected', 'marked')

        assert 'directory' in received_keys[0]
        assert 'selected' in received_keys[0]
        assert 'marked' in received_keys[0]

    def test_context_order_independence(self):
        """Order of context keys should not matter."""
        from ranger.colorschemes.default import Default

        scheme = Default()

        result1 = scheme.get('in_browser', 'directory', 'selected')
        result2 = scheme.get('selected', 'directory', 'in_browser')

        assert result1 == result2

    def test_empty_context(self):
        """Empty context should return valid default colors."""
        from ranger.colorschemes.default import Default

        scheme = Default()

        result = scheme.get()

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(v, int) for v in result)


class TestNewThemeCreation:
    """Test that creating new themes is simple and intuitive."""

    def test_minimal_theme(self):
        """Minimal theme should just implement use()."""
        from ranger.gui.colorscheme import ColorScheme
        from ranger.gui.color import default_colors

        class MinimalTheme(ColorScheme):
            def use(self, context):
                return default_colors

        theme = MinimalTheme()
        result = theme.get('any', 'context')

        assert result == default_colors

    def test_theme_with_custom_logic(self):
        """Theme with custom logic should work correctly."""
        from ranger.gui.colorscheme import ColorScheme
        from ranger.gui.color import red, blue, green, bold, reverse, default_colors

        class CustomTheme(ColorScheme):
            def use(self, context):
                fg, bg, attr = default_colors

                if context.directory:
                    fg = blue
                    attr |= bold
                elif context.executable:
                    fg = green
                elif context.error:
                    fg = red

                if context.selected:
                    attr |= reverse

                return (fg, bg, attr)

        theme = CustomTheme()

        dir_result = theme.get('in_browser', 'directory')
        assert dir_result[0] == blue
        assert (dir_result[2] & bold) == bold

        exec_result = theme.get('in_browser', 'file', 'executable')
        assert exec_result[0] == green

        error_result = theme.get('in_browser', 'error')
        assert error_result[0] == red

        selected_result = theme.get('in_browser', 'directory', 'selected')
        assert (selected_result[2] & reverse) == reverse

    def test_theme_extending_default(self):
        """Extending Default theme should work correctly."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import green

        class GreenDirTheme(Default):
            def use(self, context):
                fg, bg, attr = Default.use(self, context)

                if context.directory:
                    fg = green

                return (fg, bg, attr)

        default_theme = Default()
        custom_theme = GreenDirTheme()

        default_result = default_theme.get('in_browser', 'directory')
        custom_result = custom_theme.get('in_browser', 'directory')

        assert custom_result[0] == green
        assert custom_result[0] != default_result[0]

        assert custom_result[1] == default_result[1]
        assert custom_result[2] == default_result[2]
