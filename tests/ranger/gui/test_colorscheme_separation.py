# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.
"""Tests for the colorscheme and rendering adapter separation.

Verifies that:
1. ColorScheme (theme model layer) is independent from curses
2. ColorAdapter (rendering layer) correctly converts colors to curses attributes
3. Default theme behavior is preserved
4. The separation enables easier addition of new themes
"""

from __future__ import (absolute_import, division, print_function)


class TestColorSchemeIndependence:
    """Verify ColorScheme is decoupled from curses rendering."""

    def test_colorscheme_has_no_get_attr(self):
        """ColorScheme should NOT have get_attr method (moved to ColorAdapter)."""
        from ranger.gui.colorscheme import ColorScheme

        assert not hasattr(ColorScheme, 'get_attr'), \
            "ColorScheme should not have get_attr - it was moved to ColorAdapter"

    def test_colorscheme_has_get_method(self):
        """ColorScheme should have get method returning (fg, bg, attr) tuple."""
        from ranger.gui.colorscheme import ColorScheme

        assert hasattr(ColorScheme, 'get'), \
            "ColorScheme should have get method"

    def test_colorscheme_no_curses_imports_in_module(self):
        """ColorScheme module should NOT directly depend on curses for core logic."""
        import ranger.gui.colorscheme as colorscheme_module

        assert 'curses' not in colorscheme_module.__name__

        import inspect
        source = inspect.getsource(colorscheme_module.ColorScheme)
        assert 'curses' not in source, \
            "ColorScheme class should not reference curses directly"

    def test_colorscheme_get_returns_tuple(self):
        """ColorScheme.get should return a 3-tuple of integers."""
        from ranger.gui.colorscheme import ColorScheme

        class TestScheme(ColorScheme):
            def use(self, context):
                return (1, 2, 3)

        scheme = TestScheme()
        result = scheme.get('test')

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(v, int) for v in result)
        assert result == (1, 2, 3)

    def test_colorscheme_use_is_abstract(self):
        """use() method should be marked as abstract."""
        from ranger.gui.colorscheme import ColorScheme

        assert hasattr(ColorScheme.use, '__isabstractmethod__')
        assert ColorScheme.use.__isabstractmethod__ is True

    def test_colorscheme_context_usage(self):
        """ColorScheme should use Context for determining colors."""
        from ranger.gui.colorscheme import ColorScheme
        from ranger.gui.context import Context

        class SchemeWithContext(ColorScheme):
            def use(self, context):
                fg = 1 if context.directory else 2
                bg = 3 if context.selected else 4
                attr = 5 if context.marked else 6
                return (fg, bg, attr)

        scheme = SchemeWithContext()

        result1 = scheme.get('directory', 'selected')
        assert result1 == (1, 3, 6)

        result2 = scheme.get('marked', 'directory')
        assert result2 == (1, 4, 5)

        result3 = scheme.get()
        assert result3 == (2, 4, 6)


class TestColorAdapterRendering:
    """Verify ColorAdapter correctly converts theme colors to curses attributes."""

    def test_coloradapter_exists(self):
        """ColorAdapter class should exist in curses_shortcuts module."""
        from ranger.gui.curses_shortcuts import ColorAdapter

        assert ColorAdapter is not None

    def test_coloradapter_has_get_attr(self):
        """ColorAdapter should have get_attr method."""
        from ranger.gui.curses_shortcuts import ColorAdapter

        assert hasattr(ColorAdapter, 'get_attr'), \
            "ColorAdapter should have get_attr method"

    def test_coloradapter_requires_colorscheme(self):
        """ColorAdapter should be initialized with a colorscheme."""
        from ranger.gui.curses_shortcuts import ColorAdapter
        from ranger.gui.colorscheme import ColorScheme

        class TestScheme(ColorScheme):
            def use(self, context):
                return (1, 2, 3)

        scheme = TestScheme()
        adapter = ColorAdapter(scheme)

        assert adapter._colorscheme is scheme

    def test_coloradapter_uses_flatten(self):
        """ColorAdapter.get_attr should handle nested key lists."""
        from ranger.gui.curses_shortcuts import ColorAdapter
        from ranger.gui.colorscheme import ColorScheme

        class TestScheme(ColorScheme):
            def __init__(self):
                super(TestScheme, self).__init__()
                self.received_keys = []

            def use(self, context):
                self.received_keys = [
                    key for key in dir(context)
                    if not key.startswith('_') and getattr(context, key)
                ]
                return (0, 0, 0)

        scheme = TestScheme()
        adapter = ColorAdapter(scheme)

        adapter.get_attr(['directory', ['selected', 'marked']])

        assert 'directory' in scheme.received_keys
        assert 'selected' in scheme.received_keys
        assert 'marked' in scheme.received_keys

    def test_coloradapter_caches_results(self):
        """ColorAdapter.get_attr should cache results for performance."""
        from ranger.gui.curses_shortcuts import ColorAdapter
        from ranger.gui.colorscheme import ColorScheme

        call_count = [0]

        class CountingScheme(ColorScheme):
            def use(self, context):
                call_count[0] += 1
                return (1, 2, 3)

        scheme = CountingScheme()
        adapter = ColorAdapter(scheme)

        adapter.get_attr('test')
        first_count = call_count[0]

        adapter.get_attr('test')
        second_count = call_count[0]

        assert second_count == first_count, \
            "get_attr should cache results - use() should not be called twice"


class TestDefaultThemeBehavior:
    """Verify default theme behavior is preserved after refactoring."""

    def test_default_scheme_inherits_from_colorscheme(self):
        """Default colorscheme should inherit from ColorScheme."""
        from ranger.colorschemes.default import Default
        from ranger.gui.colorscheme import ColorScheme

        assert issubclass(Default, ColorScheme)

    def test_default_scheme_returns_valid_tuple(self):
        """Default scheme should return valid (fg, bg, attr) tuples."""
        from ranger.colorschemes.default import Default

        scheme = Default()

        test_contexts = [
            ['reset'],
            ['in_browser'],
            ['in_browser', 'directory', 'selected'],
            ['in_browser', 'file', 'executable'],
            ['in_titlebar'],
            ['in_statusbar'],
            ['in_taskview'],
        ]

        for ctx in test_contexts:
            result = scheme.get(*ctx)
            assert isinstance(result, tuple)
            assert len(result) == 3
            assert all(isinstance(v, int) for v in result)

    def test_default_scheme_reset_context(self):
        """Reset context should return default colors."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import default_colors

        scheme = Default()
        result = scheme.get('reset')

        assert result == default_colors

    def test_default_scheme_directory_color(self):
        """Directory in browser should have blue foreground with bold."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import blue, bold, BRIGHT

        scheme = Default()
        fg, bg, attr = scheme.get('in_browser', 'directory')

        expected_fg = blue + BRIGHT if BRIGHT else blue
        expected_attr = bold

        assert fg == expected_fg
        assert (attr & bold) == expected_attr

    def test_default_scheme_selected_context(self):
        """Selected items should have reverse attribute."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import reverse

        scheme = Default()

        _, _, attr_selected = scheme.get('in_browser', 'directory', 'selected')
        _, _, attr_not_selected = scheme.get('in_browser', 'file')

        assert (attr_selected & reverse) == reverse
        assert (attr_not_selected & reverse) != reverse

    def test_default_scheme_executable_color(self):
        """Executable files should have green foreground."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import green, bold, BRIGHT

        scheme = Default()
        fg, bg, attr = scheme.get('in_browser', 'file', 'executable')

        expected_fg = green + BRIGHT if BRIGHT else green
        expected_attr = bold

        assert fg == expected_fg
        assert (attr & bold) == expected_attr

    def test_default_scheme_link_color(self):
        """Good links should be cyan, bad links magenta."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import cyan, magenta

        scheme = Default()

        fg_good, _, _ = scheme.get('in_browser', 'link', 'good')
        fg_bad, _, _ = scheme.get('in_browser', 'link', 'bad')

        assert fg_good == cyan
        assert fg_bad == magenta


class TestJungleThemeBehavior:
    """Verify Jungle theme inherits correctly from Default."""

    def test_jungle_inherits_from_default(self):
        """Jungle should inherit from Default colorscheme."""
        from ranger.colorschemes.jungle import Scheme as Jungle
        from ranger.colorschemes.default import Default
        from ranger.gui.colorscheme import ColorScheme

        assert issubclass(Jungle, Default)
        assert issubclass(Jungle, ColorScheme)

    def test_jungle_override_directory_color(self):
        """Jungle should override directory color (to green)."""
        from ranger.colorschemes.jungle import Scheme as Jungle
        from ranger.colorschemes.default import Default
        from ranger.gui.color import green, blue, BRIGHT

        default_scheme = Default()
        jungle_scheme = Jungle()

        default_fg, _, _ = default_scheme.get('in_browser', 'directory')
        jungle_fg, _, _ = jungle_scheme.get('in_browser', 'directory')

        expected_jungle = green
        expected_default = blue + BRIGHT if BRIGHT else blue

        assert jungle_fg == expected_jungle
        assert default_fg == expected_default
        assert jungle_fg != default_fg


class TestSnowThemeBehavior:
    """Verify Snow theme works independently."""

    def test_snow_inherits_from_colorscheme(self):
        """Snow should inherit from ColorScheme directly."""
        from ranger.colorschemes.snow import Snow
        from ranger.gui.colorscheme import ColorScheme
        from ranger.colorschemes.default import Default

        assert issubclass(Snow, ColorScheme)
        assert not issubclass(Snow, Default)

    def test_snow_returns_valid_tuple(self):
        """Snow scheme should return valid color tuples."""
        from ranger.colorschemes.snow import Snow

        scheme = Snow()

        test_contexts = [
            ['reset'],
            ['in_browser'],
            ['in_browser', 'directory', 'selected'],
            ['in_titlebar', 'tab', 'good'],
            ['in_taskview'],
        ]

        for ctx in test_contexts:
            result = scheme.get(*ctx)
            assert isinstance(result, tuple)
            assert len(result) == 3
            assert all(isinstance(v, int) for v in result)


class TestThemeExtensionEase:
    """Verify adding new themes is now easier with the separation."""

    def test_can_create_new_theme_simply(self):
        """Creating a new theme should only require ColorScheme inheritance."""
        from ranger.gui.colorscheme import ColorScheme
        from ranger.gui.color import red, blue, bold, reverse, default_colors

        class MySimpleTheme(ColorScheme):
            def use(self, context):
                if context.reset:
                    return default_colors
                fg, bg, attr = default_colors
                if context.directory:
                    fg = red
                    attr |= bold
                if context.selected:
                    attr |= reverse
                return (fg, bg, attr)

        scheme = MySimpleTheme()

        result1 = scheme.get('in_browser', 'directory')
        assert result1[0] == red
        assert (result1[2] & bold) == bold

        result2 = scheme.get('in_browser', 'directory', 'selected')
        assert (result2[2] & reverse) == reverse

        result3 = scheme.get('reset')
        assert result3 == default_colors

    def test_can_extend_default_theme_easily(self):
        """Extending Default theme should be simple."""
        from ranger.colorschemes.default import Default
        from ranger.gui.color import green

        class MyExtendedTheme(Default):
            def use(self, context):
                fg, bg, attr = Default.use(self, context)

                if context.directory and not context.selected:
                    fg = green

                return (fg, bg, attr)

        scheme = MyExtendedTheme()

        default_scheme = Default()
        default_fg, _, _ = default_scheme.get('in_browser', 'directory')
        my_fg, _, _ = scheme.get('in_browser', 'directory')

        assert my_fg == green
        assert my_fg != default_fg

    def test_new_theme_no_curses_knowledge_needed(self):
        """Theme developer should not need to know curses API."""
        from ranger.gui.colorscheme import ColorScheme
        from ranger.gui.color import (
            black, white, red, green, blue, cyan, magenta, yellow,
            bold, reverse, underline, dim,
            default, default_colors,
        )

        class ThemedTheme(ColorScheme):
            def use(self, context):
                fg, bg, attr = default_colors

                if context.directory:
                    fg = blue
                    attr |= bold
                elif context.executable:
                    fg = green
                    attr |= bold
                elif context.link:
                    fg = cyan
                elif context.media:
                    fg = magenta

                if context.selected:
                    attr |= reverse

                return (fg, bg, attr)

        scheme = ThemedTheme()

        assert callable(scheme.get)
        result = scheme.get('in_browser', 'directory')

        assert isinstance(result, tuple)
        assert len(result) == 3


class TestIntegrationWithCursesShortcuts:
    """Verify CursesShortcuts works with the new architecture."""

    def test_cursesshortcuts_has_color_adapter_attribute(self):
        """CursesShortcuts should have _color_adapter attribute."""
        from ranger.gui.curses_shortcuts import CursesShortcuts

        cs = CursesShortcuts()

        assert hasattr(cs, '_color_adapter')

    def test_cursesshortcuts_color_methods_exist(self):
        """CursesShortcuts should have color and color_at methods."""
        from ranger.gui.curses_shortcuts import CursesShortcuts

        cs = CursesShortcuts()

        assert hasattr(cs, 'color')
        assert hasattr(cs, 'color_at')
        assert hasattr(cs, 'color_reset')

    def test_cursesshortcuts_get_color_adapter_method(self):
        """CursesShortcuts should have _get_color_adapter method."""
        from ranger.gui.curses_shortcuts import CursesShortcuts

        cs = CursesShortcuts()

        assert hasattr(cs, '_get_color_adapter')
        assert callable(cs._get_color_adapter)


class TestContextKeys:
    """Verify context keys work correctly with the separation."""

    def test_all_context_keys_are_accessible(self):
        """All context keys should be settable and accessible."""
        from ranger.gui.context import Context, CONTEXT_KEYS

        ctx = Context(CONTEXT_KEYS[:5])

        for key in CONTEXT_KEYS[:5]:
            assert getattr(ctx, key) is True

        for key in CONTEXT_KEYS[5:10]:
            assert getattr(ctx, key) is False

    def test_context_initializes_all_keys_to_false(self):
        """Context class should have all keys defaulting to False."""
        from ranger.gui.context import Context, CONTEXT_KEYS

        ctx = Context([])

        for key in CONTEXT_KEYS:
            assert getattr(Context, key) is False

    def test_context_accepts_dynamic_keys(self):
        """Context should accept any keys passed to it."""
        from ranger.gui.context import Context

        ctx = Context(['custom_key_1', 'custom_key_2'])

        assert ctx.custom_key_1 is True
        assert ctx.custom_key_2 is True


class TestColorModuleIndependence:
    """Verify color constants module works independently."""

    def test_color_constants_defined(self):
        """Color module should define color and attribute constants."""
        from ranger.gui.color import (
            black, red, green, yellow, blue, magenta, cyan, white, default,
            normal, bold, blink, reverse, underline, invisible, dim,
            default_colors,
        )

        assert isinstance(black, int)
        assert isinstance(red, int)
        assert isinstance(green, int)
        assert isinstance(yellow, int)
        assert isinstance(blue, int)
        assert isinstance(magenta, int)
        assert isinstance(cyan, int)
        assert isinstance(white, int)
        assert isinstance(default, int)

        assert isinstance(normal, int)
        assert isinstance(bold, int)
        assert isinstance(blink, int)
        assert isinstance(reverse, int)
        assert isinstance(underline, int)
        assert isinstance(invisible, int)
        assert isinstance(dim, int)

        assert isinstance(default_colors, tuple)
        assert len(default_colors) == 3

    def test_color_get_color_function(self):
        """Color module should have get_color function."""
        from ranger.gui.color import get_color

        assert callable(get_color)


class TestModuleImports:
    """Verify modules can be imported correctly."""

    def test_import_colorscheme_module(self):
        """Should be able to import colorscheme module."""
        import ranger.gui.colorscheme

        assert hasattr(ranger.gui.colorscheme, 'ColorScheme')
        assert hasattr(ranger.gui.colorscheme, 'ColorSchemeError')

    def test_import_curses_shortcuts_module(self):
        """Should be able to import curses_shortcuts module."""
        import ranger.gui.curses_shortcuts

        assert hasattr(ranger.gui.curses_shortcuts, 'CursesShortcuts')
        assert hasattr(ranger.gui.curses_shortcuts, 'ColorAdapter')

    def test_import_default_theme(self):
        """Should be able to import default theme."""
        import ranger.colorschemes.default

        assert hasattr(ranger.colorschemes.default, 'Default')

    def test_import_all_bundled_themes(self):
        """Should be able to import all bundled themes."""
        from ranger.colorschemes.default import Default
        from ranger.colorschemes.jungle import Scheme as Jungle
        from ranger.colorschemes.snow import Snow

        assert Default is not None
        assert Jungle is not None
        assert Snow is not None

        from ranger.colorschemes.solarized import Solarized
        assert Solarized is not None
